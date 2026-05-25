import csv
import re
import os
from pathlib import Path

from packager.model.package import Package


class PupScanner:
    """Scan puplookup CSV for PuP-Pack entries and bundle PinUp media into packages."""
    def __init__(self, logger, baseModel):
        self.logger = logger
        self.baseModel = baseModel

    def _resolve_db_path(self) -> str:
        db_path = self.baseModel.config.get('db_path')
        if db_path and Path(db_path).exists():
            return db_path

        fallback = os.path.join(self.baseModel.pinupSystem_path, 'puplookup.csv')
        if Path(fallback).exists():
            self.logger.info('Using fallback PuP lookup database: %s' % fallback)
            return fallback

        self.logger.warning('PuP lookup database not found (%s)' % db_path)
        return ''

    def scan_list(self) -> list:
        """Return a list of game names from the puplookup DB that reference PuP/Pup packs."""
        db_path = self._resolve_db_path()
        if not db_path:
            return []

        self.logger.info('Scanning PuP lookup database: %s' % db_path)
        results = []

        pup_pattern = re.compile(r'(?i)pup[- ]?pack')
        with open(db_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None)
            for row in reader:
                try:
                    game_name = row[1]
                except IndexError:
                    continue
                if not game_name:
                    continue
                if pup_pattern.search(game_name):
                    results.append(game_name.strip())

        # unique & sorted
        return sorted(list(dict.fromkeys(results)))

    def _sanitize(self, name: str) -> str:
        # make a filesystem-friendly package name
        name = name.strip()
        name = re.sub(r'\s+', '_', name)
        name = re.sub(r'[^A-Za-z0-9_\-\.]+', '', name)
        return name[:120]

    def _package_has_files(self, package: Package) -> bool:
        """Return True if the package manifest contains any staged files."""
        try:
            content = package.manifest.content
        except Exception:
            return False

        def scan(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == 'file':
                        return True
                    if scan(v):
                        return True
            elif isinstance(node, list):
                for item in node:
                    if isinstance(item, dict) and 'file' in item:
                        return True
                    if scan(item):
                        return True
            return False

        return scan(content)

    def scan_and_bundle(self) -> list:
        """Scan puplookup for Pup packs and create packages containing PinUp media.

        Returns list of created package filenames.
        """
        created = []
        names = self.scan_list()
        if not names:
            self.logger.info("No PuP packs found in lookup database")
            return created

        if not os.path.exists(self.baseModel.pinupSystem_path):
            self.logger.warning('PinupSystem not found(%s)' % self.baseModel.pinupSystem_path)
            return created

        for game in names:
            try:
                package_name = self._sanitize(game)
                search_name = self._base_table_name(game)
                self.logger.info("Creating package for PuP pack: %s -> %s (search %s)" % (game, package_name, search_name))
                package = Package(self.baseModel, package_name)
                package.new(self.baseModel.tmp_path)

                # extract PinUp media using the actual base table name so files are found correctly
                self.baseModel.pinupSystem.extract(package, 'visual pinball', search_name=search_name)

                # If extraction produced no files, skip creating the pup package
                if not self._package_has_files(package):
                    self.logger.info(f"Skipping empty PuP package for '{game}' ({package_name}) — no files staged")
                    continue

                package.save()
                package.pack()

                src = os.path.join(self.baseModel.tmp_path, package_name + self.baseModel.package_extension)
                dst = self.baseModel.package_path
                if os.path.exists(src):
                    if os.path.exists(os.path.join(dst, package_name + self.baseModel.package_extension)):
                        self.logger.info('Overwrite existing package %s' % package_name)
                        os.remove(os.path.join(dst, package_name + self.baseModel.package_extension))
                    os.replace(src, os.path.join(dst, package_name + self.baseModel.package_extension))
                    created.append(package_name + self.baseModel.package_extension)
            except Exception as e:
                self.logger.error('Error bundling PuP pack %s: %s' % (game, e))

        return created

    def find_for_table(self, table_name: str) -> list:
        """Return pup-pack entries by checking the lookup DB and local file system folders."""
        # 1. Safely grab the ROM metadata field from the current package manifest
        rom_field = None
        if hasattr(self.baseModel, 'packageEditorModel') and self.baseModel.packageEditorModel.package:
            rom_field = self.baseModel.packageEditorModel.package.get_field('visual pinball/info/romName')
        
        # 2. Extract and sanitize search terms (ROM names)
        search_terms = []
        if rom_field:
            if isinstance(rom_field, list):
                search_terms = [str(r).strip().lower() for r in rom_field if r]
            else:
                clean_rom = str(rom_field).replace('[', '').replace(']', '').replace("'", "").replace('"', '')
                search_terms = [r.strip().lower() for r in clean_rom.split(',') if r.strip()]
            
        if table_name:
            search_terms.append(table_name.lower())

        # Filter out generic template text
        search_terms = [term for term in search_terms if term != "yourgame"]

        if not search_terms:
            self.logger.info("No active table titles or ROM identifiers found to check.")
            return []

        self.logger.info(f"Target lookup tokens: {search_terms}")
        results = []

        # 3. FIRST PASS: Scan the puplookup database if it exists
        db_path = self._resolve_db_path()
        if db_path:
            self.logger.info('Scanning PuP lookup database for table matches: %s' % db_path)
            try:
                with open(db_path, newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    next(reader, None)  # Skip header row
                    for row in reader:
                        try:
                            game_name = row[1]
                        except IndexError:
                            continue
                        if not game_name:
                            continue

                        base_name = self._base_table_name(game_name)
                        game_name_lower = game_name.lower()
                        base_name_lower = base_name.lower()
                        
                        for term in search_terms:
                            if term in game_name_lower or term in base_name_lower:
                                results.append(game_name.strip())
                                break
            except Exception as e:
                self.logger.error(f"Error reading lookup database: {e}")

        # 4. SECOND PASS: Scan the local PUPVideos folder directly on your drive
        pup_videos_path = os.path.join(self.baseModel.pinupSystem_path, 'PUPVideos')
        if os.path.exists(pup_videos_path):
            self.logger.info(f"Checking local file system path: {pup_videos_path}")
            try:
                local_folders = [f for f in os.listdir(pup_videos_path) if os.path.isdir(os.path.join(pup_videos_path, f))]
                
                for folder in local_folders:
                    folder_lower = folder.lower()
                    for term in search_terms:
                        if term == folder_lower or term in folder_lower:
                            self.logger.info(f"++ Direct Hit Found! Located local folder path: '{folder}'")
                            results.append(folder)
                            break
            except Exception as e:
                self.logger.error(f"Error reading local PUPVideos path: {e}")

        return sorted(list(dict.fromkeys(results)))

    def _base_table_name(self, game_name: str) -> str:
        """Extract the base table name from a Pup pack title."""
        if not game_name:
            return ''
        name = re.sub(r'(?i)\s*[-–—]\s*puP[- ]?pack.*$', '', game_name).strip()
        name = re.sub(r'(?i)\s*puP[- ]?pack.*$', '', name).strip()
        return name

    def create_pup_archive(self, game_name: str) -> str:
        """Create a pup package for the given game and return the path to the created archive (in tmp)."""
        try:
            package_name = self._sanitize(game_name)
            search_name = self._base_table_name(game_name)
            package = Package(self.baseModel, package_name)
            package.new(self.baseModel.tmp_path)
            self.baseModel.pinupSystem.extract(package, 'visual pinball', search_name=search_name)
            # If extraction produced no files, return empty — nothing to archive
            if not self._package_has_files(package):
                self.logger.info(f"create_pup_archive: no files staged for '{game_name}', skipping archive")
                return ''

            package.save()
            package.pack()
            src = os.path.join(self.baseModel.tmp_path, package_name + self.baseModel.package_extension)
            if os.path.exists(src):
                return src
        except Exception as e:
            self.logger.error('create_pup_archive error %s: %s' % (game_name, e))
        return ''