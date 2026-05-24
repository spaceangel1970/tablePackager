import os
import shutil
from pathlib import Path
import subprocess
import tkinter
import re
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
        if not rom:
            self.logger.info("- no rom found in vp file")
        else:
            self.logger.info("+ rom name is '%s' (the first is normally active)" % rom)
            package.set_field('visual pinball/info/romName', rom)

        package.add_file(vp_file, 'visual pinball/tables')  # Add vpx file
        if not directb2s_file.exists():  # Add directb2s file
            self.logger.warning("* no directb2s found")
        else:
            package.add_file(directb2s_file, 'visual pinball/tables')

        if ini_file.exists():
            package.add_file(ini_file, 'visual pinball/tables')
        else:
            if pov_file.exists():
                overwrite_pov = tkinter.messagebox.askokcancel("Overwrite POV file ?",
                                                               "Do you want to update the existing Visual Pinball table configuration file ?")
                if overwrite_pov:
                    self.logger.warning("* extract and overwrite pov file")
                    self.extract_pov_file(package, vp_file)
            else:
                self.logger.warning("* no pov/ini file found, extract pov file")
                self.extract_pov_file(package, vp_file)

            if pov_file.exists():
                package.add_file(pov_file, 'visual pinball/tables')

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

    def deploy(self, package: Package) -> None:
        self.logger.info("* Visual Pinball X files")
        if not os.path.exists(self.visual_pinball_path):
            raise ValueError('Visual Pinball not found(%s)' % self.visual_pinball_path)

        if not Path(self.baseModel.tmp_path + "/" + package.name).exists():
            raise ValueError('Package Tree not found (%s)' % (self.baseModel.tmp_path + "/" + package.name))

        # Deploy tables assets
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/visual pinball/tables",
                 self.baseModel.visual_pinball_path + "/tables")
                 
        # Deploy music assets dynamically if packed inside the archive structure
        archive_music_path = os.path.join(self.baseModel.tmp_path, package.name, "visual pinball", "Music")
        if os.path.exists(archive_music_path):
            self.logger.info("* Deploying audio tracking assets to local directory...")
            copytree(self.logger, archive_music_path, os.path.join(self.baseModel.visual_pinball_path, "Music"))
            
        return True

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