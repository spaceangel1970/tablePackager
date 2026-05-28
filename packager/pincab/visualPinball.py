import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import tkinter
import re
import copy
import xml.etree.ElementTree as ET
from packager.tools.toolbox import *
from packager.model.package import Package


class VisualPinball:
    def __init__(self, logger, baseModel):
        self.__baseModel = baseModel
        self.__logger = logger

    @property
    def logger(self):
        return self.__logger

    @property
    def baseModel(self):
        return self.__baseModel

    @property
    def visual_pinball_path(self):
        return self.baseModel.visual_pinball_path

    def get_rom_name(self, table_name: str) -> list:
        if not os.path.exists(self.visual_pinball_path):
            raise ValueError('Visual Pinball not found(%s)' % self.visual_pinball_path)

        vpx_file = Path(self.visual_pinball_path + '/tables/' + table_name + '.vpx')
        vpt_file = Path(self.visual_pinball_path + '/tables/' + table_name + '.vpt')

        if os.path.exists(vpx_file):
            vp_file = vpx_file
        elif os.path.exists(vpt_file):
            vp_file = vpt_file
        else:
            raise ValueError('table not found (%s) (vpt or vpx)' % self.visual_pinball_path + '/tables/' + package.name)
        return self.extract_rom_name(vp_file)
    
    def is_pup_pack_empty(self, pup_path: str) -> bool:
        """Checks if a PUP pack folder is effectively empty or missing."""
        if not os.path.exists(pup_path):
            return True
        # Using os.walk to check for any files
        for root, dirs, files in os.walk(pup_path):
            if files: 
                return False
        return True

    def extract(self, package: Package) -> None:
        if not os.path.exists(self.visual_pinball_path):
            raise ValueError('Visual Pinball not found(%s)' % self.visual_pinball_path)

        # --- DYNAMIC STRUCTURAL ADAPTER INJECTION ---
        if hasattr(package, 'manifest') and hasattr(package.manifest, 'content'):
            if "visual pinball" in package.manifest.content:
                # Force Music to be a list if it's missing or currently a dict
                if "Music" not in package.manifest.content["visual pinball"] or \
                   not isinstance(package.manifest.content["visual pinball"]["Music"], list):
                    package.manifest.content["visual pinball"]["Music"] = []

        self.logger.info("* Visual Pinball X files")
        vpx_file = Path(self.visual_pinball_path + '/tables/' + package.name + '.vpx')
        ini_file = Path(self.visual_pinball_path + '/tables/' + package.name + '.ini')
        pov_file = Path(self.visual_pinball_path + '/tables/' + package.name + '.pov')
        vpt_file = Path(self.visual_pinball_path + '/tables/' + package.name + '.vpt')
        directb2s_file = Path(self.visual_pinball_path + "/tables/" + vpx_file.stem + '.directb2s')

        if os.path.exists(vpx_file):
            vp_file = vpx_file
        elif os.path.exists(vpt_file):
            vp_file = vpt_file
        else:
            raise ValueError('table not found (%s) (vpt or vpx)' % self.visual_pinball_path + '/tables/' + package.name)

        rom = self.extract_rom_name(vp_file)
        script_names = self.extract_table_name(vp_file)

        rom_candidates = []
        if isinstance(rom, list):
            rom_candidates.extend(rom)
        elif rom:
            rom_candidates.append(rom)

        if script_names:
            for table_name in script_names:
                if table_name and table_name not in rom_candidates:
                    rom_candidates.append(table_name)

        if not rom_candidates:
            self.logger.info("- no rom or table name found in vp file")
        else:
            self.logger.info(f"+ rom/table names are {rom_candidates}")
            package.set_field('visual pinball/info/romName', rom_candidates)

        package.add_file(vp_file, 'visual pinball/tables')  # Add vpx file
        if not directb2s_file.exists():  # Add directb2s file
            self.logger.warning("* no directb2s found")
        else:
            package.add_file(directb2s_file, 'visual pinball/tables')

        if ini_file.exists():
            package.add_file(ini_file, 'visual pinball/tables')
        else:
            if pov_file.exists():
                self.logger.warning("* extract and overwrite pov file")
                self.extract_pov_file(package, vp_file)
            else:
                self.logger.warning("* no pov/ini file found, extract pov file")
                self.extract_pov_file(package, vp_file)

            if pov_file.exists():
                package.add_file(pov_file, 'visual pinball/tables')

        self._extract_b2s_table_settings(package, rom_candidates)

        # Logic for PUP packs
        pup_pack_path = os.path.join(self.visual_pinball_path, "PUPVideos", package.name)
        
        if not self.is_pup_pack_empty(pup_pack_path):
            self.logger.info(f"+ Found valid PUP pack: {package.name}")
            package.add_folder(pup_pack_path, 'visual pinball/PUPVideos')
        else:
            self.logger.info(f"- Ignoring PUP pack: {package.name} (Folder is empty or missing)")

        # --- DYNAMIC MUSIC SCANNING ENGINE ---
        self.logger.info("--------------------------------------------------")
        self.logger.info("* [AUDIO SCAN] Checking table script for external music...")
        
        found_music_tracks = self.extract_music_assets(vp_file)
        music_base_dir = os.path.join(self.visual_pinball_path, "Music")
        
        if found_music_tracks:
            # Re-verify the list type before looping
            vp_data = package.manifest.content['visual pinball']
            if not isinstance(vp_data.get('Music'), list):
                vp_data['Music'] = []
            
            self.logger.info(f"+ Found {len(found_music_tracks)} track references...")
            
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            clean_iso_timestamp = f"{now.year:04d}-{now.month:02d}-{now.day:02d}T{now.hour:02d}:{now.minute:02d}:{now.second:02d}.{now.microsecond:06d}+0000"
            
            packed_count = 0
            vp_data = package.manifest.content['visual pinball']
            
            for track_path in found_music_tracks:
                safe_track_path = track_path.replace('\\', '/')
                full_music_path = Path(os.path.normpath(os.path.join(music_base_dir, track_path)))
                
                if full_music_path.exists() and full_music_path.is_file():
                    self.logger.info(f"  -> BUNDLING: '{track_path}'")
                    
                    relative_dest_dir = os.path.dirname(safe_track_path)
                    file_size = full_music_path.stat().st_size
                    
                    # TRACK FOLDERS TO AVOID DUPLICATE UI NODES
            added_folders = set()
            
            for track_path in found_music_tracks:
                safe_track_path = track_path.replace('\\', '/')
                full_music_path = Path(os.path.normpath(os.path.join(music_base_dir, track_path)))
                
                if full_music_path.exists() and full_music_path.is_file():
                    # 1. HANDLE FOLDER METADATA (So the UI knows it's a folder)
                    folder_name = os.path.dirname(safe_track_path)
                    if folder_name and folder_name not in added_folders:
                        vp_data['Music'].append({
                            'folder': {
                                'path': f"visual pinball/Music/{folder_name}",
                                'name': folder_name
                            }
                        })
                        added_folders.add(folder_name)

                    # 2. HANDLE FILE METADATA
                    archive_dest_path = f"visual pinball/Music/{safe_track_path}"
                    
                    vp_data['Music'].append({
                        'file': {
                            'name': full_music_path.name,
                            'path': archive_dest_path, 
                            'size': full_music_path.stat().st_size,
                            'lastmod': clean_iso_timestamp,
                            'author(s)': '', 'version': '', 'url': '', 'md5': ''
                        }
                    })

                    # 3. FIX THE PHYSICAL EXTRACTION PATH
                    physical_dest = os.path.join(self.baseModel.tmp_path, package.name, "visual pinball", "Music", safe_track_path)
                    os.makedirs(os.path.dirname(physical_dest), exist_ok=True)
                    
                    try:
                        shutil.copy2(str(full_music_path), physical_dest)
                        packed_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to copy '{full_music_path}' to '{physical_dest}': {e}")
                                    
                    packed_count += 1
                else:
                    self.logger.warning(f"  ! MISSING ON DISK: '{track_path}' (Expected in: {music_base_dir})")
            
            self.logger.info(f"* Successfully archived {packed_count} of {len(found_music_tracks)} music tracks.")
        else:
            self.logger.info("- No external background music (.mp3/.ogg) found in this table.")
            
        self.logger.info("--------------------------------------------------")

        
    def _merge_b2s_xml(self, source_xml: str, target_xml: str):
        if not os.path.exists(target_xml):
            shutil.copy2(source_xml, target_xml)
            return

        try:
            source_tree = ET.parse(source_xml)
            target_tree = ET.parse(target_xml)
            
            source_root = source_tree.getroot()
            target_root = target_tree.getroot()

            for new_entry in source_root:
                existing = target_root.find(new_entry.tag)
                if existing is not None:
                    target_root.remove(existing)
                target_root.append(new_entry)

            target_tree.write(target_xml, encoding='utf-8', xml_declaration=True)
            self.logger.info(f"* Successfully merged {source_xml} into {target_xml}")
        except Exception as e:
            self.logger.error(f"Failed to merge B2S XML: {e}")

    def deploy(self, package: Package) -> None:
        if not os.path.exists(self.visual_pinball_path):
            raise ValueError('Visual Pinball not found(%s)' % self.visual_pinball_path)

        source_base = os.path.join(self.baseModel.tmp_path, package.name, "visual pinball")
        if not os.path.exists(source_base):
            raise ValueError('Package Tree not found')

        # 1. Define Target Mappings
        mappings = [
            ("tables", os.path.join(self.visual_pinball_path, "tables")),
            ("Music", os.path.join(self.visual_pinball_path, "Music"))
        ]

        # 2. Perform Merged Copy (Individual file handling avoids folder-level overwrite)
        for src_sub, dest_dir in mappings:
            src_dir = os.path.join(source_base, src_sub)
            if os.path.exists(src_dir):
                self.logger.info(f"* Deploying {src_sub} to {dest_dir} (Merge Mode)...")
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                
                for item in os.listdir(src_dir):
                    # Skip the XML file here so we can merge it separately below
                    if item == "B2STableSettings.xml":
                        continue
                        
                    s = os.path.join(src_dir, item)
                    d = os.path.join(dest_dir, item)
                    
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
        
        # 3. SPECIAL HANDLING: B2STableSettings.xml Merge
        pkg_b2s = os.path.join(source_base, "tables", "B2STableSettings.xml")
        live_b2s = os.path.join(self.visual_pinball_path, "tables", "B2STableSettings.xml")

        if os.path.exists(pkg_b2s):
            self.logger.info("* Performing XML Merge for B2STableSettings...")
            self._merge_b2s_xml(pkg_b2s, live_b2s)

        return True

    def _merge_b2s_xml(self, source_xml: str, target_xml: str):
        # Everything here must be indented by at least 4 spaces
        if not os.path.exists(target_xml):
            shutil.copy2(source_xml, target_xml)
            return

        try:
            source_tree = ET.parse(source_xml)
            target_tree = ET.parse(target_xml)
            
            source_root = source_tree.getroot()
            target_root = target_tree.getroot()

            for new_entry in source_root:
                existing = target_root.find(new_entry.tag)
                if existing is not None:
                    target_root.remove(existing)
                target_root.append(new_entry)

            target_tree.write(target_xml, encoding='utf-8', xml_declaration=True)
            self.logger.info(f"* Successfully merged {source_xml} into {target_xml}")
        except Exception as e:
            self.logger.error(f"Failed to merge B2S XML: {e}")

    def delete(self, table_name: str) -> None:
        if not os.path.exists(self.visual_pinball_path):
            raise ValueError('Visual Pinball not found(%s)' % self.visual_pinball_path)

        self.logger.info("* Visual Pinball X files")
        vpx_file = Path(self.visual_pinball_path + '/tables/' + table_name + '.vpx')
        pov_file = Path(self.visual_pinball_path + '/tables/' + table_name + '.pov')
        ini_file = Path(self.visual_pinball_path + '/tables/' + table_name + '.ini')
        vpt_file = Path(self.visual_pinball_path + '/tables/' + table_name + '.vpt')
        directb2s_file = Path(self.visual_pinball_path + "/tables/" + vpx_file.stem + '.directb2s')

        if vpx_file.exists():
            self.logger.info("- remove %s file" % vpx_file)
            os.remove(vpx_file)
        if vpt_file.exists():
            self.logger.info("- remove %s file" % vpt_file)
            os.remove(vpt_file)
        if pov_file.exists():
            self.logger.info("- remove %s file" % pov_file)
            os.remove(pov_file)
        if ini_file.exists():
            self.logger.info("- remove %s file" % ini_file)
            os.remove(ini_file)
        if directb2s_file.exists():
            self.logger.info("- remove %s file" % directb2s_file)
            os.remove(directb2s_file)

            # --- B2S TABLE SETTINGS ---
        b2s_settings_file = Path(self.visual_pinball_path + "/tables/" + vpx_file.stem + '.xml')
        if b2s_settings_file.exists():
            self.logger.info(f"+ Found B2STableSettings.xml: {b2s_settings_file.name}")
            package.add_file(b2s_settings_file, 'visual pinball/tables')
        else:
            self.logger.info("- No B2STableSettings.xml found for this table")
            
        # Clean local music folders matched directly to table strings
        found_music_tracks = self.extract_music_assets(vpx_file if vpx_file.exists() else vpt_file)
        music_base_dir = os.path.join(self.visual_pinball_path, "Music")
        for track_path in found_music_tracks:
            full_music_path = Path(os.path.normpath(os.path.join(music_base_dir, track_path)))
            if full_music_path.exists() and full_music_path.is_file():
                self.logger.info("- remove music track asset %s" % full_music_path)
                os.remove(full_music_path)

    def extract_rom_name(self, vpt_file: Path) -> list:
        active_roms = []
        try:
            with open(vpt_file, 'rb') as f:
                content = f.read()
            text_content = content.decode('utf-8', errors='ignore')
            
            p_pattern = r"^[ \t]*(?!')(?:(?:Public|Private)\s+)?(?:Dim)?\s*pGameName\s*=\s*[\"']([a-zA-Z0-9_]+)[\"']"
            standard_pattern = r"^[ \t]*(?!')(?:(?:Public|Private)\s+)?(?:Const|Dim)?\s*(?:cGameName|RomSet|GameName)\s*=\s*[\"']([a-zA-Z0-9_]+)[\"']"
            
            def process_matches(regex_pattern):
                for match in re.finditer(regex_pattern, text_content, re.IGNORECASE | re.MULTILINE):
                    rom_name = match.group(1).strip()
                    if rom_name not in active_roms:
                        active_roms.append(rom_name)

            process_matches(p_pattern)
            process_matches(standard_pattern)
                        
        except Exception as e:
            self.logger.error(f"Fallback byte-scanner error: {str(e)}")

        active_roms = [r for r in active_roms if r.lower() != "yourgame"]
        return active_roms

    def extract_music_assets(self, vpt_file: Path) -> list:
        discovered_tracks = []
        if not vpt_file.exists():
            return discovered_tracks
            
        try:
            with open(vpt_file, 'rb') as f:
                content = f.read()
            text_content = content.decode('utf-8', errors='ignore')
            
            music_pattern = r"^[ \t]*(?!')[^'\r\n]*[\"']([^\"'\r\n]+\.(?:mp3|ogg))[\"']"
            
            for match in re.finditer(music_pattern, text_content, re.IGNORECASE | re.MULTILINE):
                track_path = match.group(1).strip()
                track_path = track_path.replace('\\', '/')
                track_path = track_path.lstrip('/')
                if track_path and track_path not in discovered_tracks:
                    discovered_tracks.append(track_path)
                    
        except Exception as e:
            self.logger.error(f"Audio script scanner initialization error: {e}")
            
        return discovered_tracks

    def extract_table_name(self, vpt_file: Path) -> list:
        return extract_string_from_binary_file(vpt_file, br'TableName[ ]*=[ ]*"([a-zA-Z0-9_]+)"')

    def extract_pov_file(self, package: Package, vp_file: Path) -> None:
        cmd_line = ["%s/VPinballX.exe" % self.visual_pinball_path, "-pov", vp_file]
        self.logger.info("%s/VPinballX.exe -pov %s" % (self.visual_pinball_path, vp_file))
        subprocess.call(cmd_line)

    def _extract_b2s_table_settings(self, package: Package, rom_names: list) -> None:
        if not rom_names:
            self.logger.info("- No ROM names to search for in B2STableSettings.xml")
            return

        global_b2s_path = os.path.join(self.visual_pinball_path, 'tables', 'B2STableSettings.xml')
        if not os.path.exists(global_b2s_path):
            self.logger.info("- No global B2STableSettings.xml found to extract from")
            return

        try:
            tree = ET.parse(global_b2s_path)
            root = tree.getroot()
            snippet_root = ET.Element('B2STableSettings')
            added = False
            
            # Normalize to lowercase for robust alias matching
            rom_names_lower = {str(name).strip().lower() for name in rom_names if name}

            for child in root:
                # Direct match check
                if child.tag.lower() in rom_names_lower:
                    snippet_root.append(copy.deepcopy(child))
                    self.logger.info(f"+ Found B2STableSettings entry for: {child.tag}")
                    added = True

            if added:
                # Use a reliable temporary path
                tmp_dir = tempfile.gettempdir()
                tmp_xml_path = os.path.join(tmp_dir, f"B2S_{package.name}.xml")
                
                # Write with XML declaration
                ET.ElementTree(snippet_root).write(tmp_xml_path, encoding='utf-8', xml_declaration=True)
                
                # Double-verify it exists before telling the packager
                if os.path.exists(tmp_xml_path):
                    self.logger.info(f"+ Explicitly adding {tmp_xml_path} to ZIP")
                    package.add_file(tmp_xml_path, 'visual pinball/tables', dst_file='B2STableSettings.xml')
                else:
                    self.logger.error("! Failed to create temp XML file for ZIP packaging.")
            else:
                self.logger.info(f"- No matching B2STableSettings entry for aliases: {rom_names_lower}")

        except Exception as e:
            self.logger.error(f"[B2S XML EXTRACT ERROR] {str(e)}")