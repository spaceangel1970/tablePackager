import os
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from packager.tools.toolbox import *
from packager.model.package import Package


class VPinMame:
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

    def extract(self, package: Package) -> None:  # TODO: give the choice of product
        romName = package.get_field('visual pinball/info/romName')
        if romName == '':  # nothing to do
            package.set_field('visual pinball/info/has_custom_dmd', 'No')
            package.set_field('visual pinball/info/has_alias', 'No')
            return
            
        self.logger.info("* VPinMame files '%s'" % romName)
        if type(romName) is not list:
            romList = [romName]
        else:
            romList = romName
            
        vpinmame_base = os.path.abspath(os.path.join(self.visual_pinball_path, 'VPinMAME'))
        custom_dmd_processed = False
        alias_processed = False
        
        # The primary target ROM (the alias name the table runs under)
        primary_table_rom = romList[0].strip() if romList else ''
        
        # Convert romList to a standard list we can safely append parent ROMs to dynamically
        working_rom_list = list(romList)
        
        for rom in working_rom_list:
            if rom == 'yourgame' or rom.strip() == '':
                continue
                
            # 1. --- DIRECTORY COPIER (altcolor & altsound) ---
            for category in ['altcolor', 'altsound']:
                source_folder = os.path.join(vpinmame_base, category, rom)
                
                if os.path.exists(source_folder) and os.path.isdir(source_folder):
                    # Always route physical assets to the table's primary active alias folder name 
                    # so Freezy/Serum/Pinsound can natively read them on the deployment machine.
                    dest_folder = os.path.join(package.directory, package.name, 'VPinMAME', category, primary_table_rom)
                    os.makedirs(dest_folder, exist_ok=True)
                    
                    for root, dirs, files in os.walk(source_folder):
                        rel_path = os.path.relpath(root, start=source_folder)
                        target_dir = os.path.normpath(os.path.join(dest_folder, rel_path))
                        os.makedirs(target_dir, exist_ok=True)
                        for f in files:
                            shutil.copy2(os.path.join(root, f), os.path.join(target_dir, f))
                            
                    self.logger.info(f"++ Successfully cloned {category}/{rom} folder tree mapped to [{primary_table_rom}].")

            # 2. --- VPMAlias.txt SNIPPET EXTRACTOR & PARENT ROM EXTRACTION ---
            alias_txt_path = os.path.join(vpinmame_base, 'VPMAlias.txt')
            if os.path.exists(alias_txt_path):
                try:
                    with open(alias_txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                        alias_lines = f.readlines()
                    
                    captured_alias_lines = []
                    target_rom_lower = rom.lower().strip()
                    
                    for line in alias_lines:
                        if not line.strip() or line.strip().startswith(';'):
                            continue
                        
                        parts = line.split(',')
                        if len(parts) >= 2:
                            alias_part = parts[0].strip().lower()
                            parent_rom_part = parts[1].strip()  # Keep original case for file matching
                            
                            # Strict Port 0 Match
                            if alias_part == target_rom_lower:
                                captured_alias_lines.append(line)
                                
                                # Inject Port 1 (Main ROM) into scanning queue if it's missing
                                if parent_rom_part and parent_rom_part not in working_rom_list:
                                    self.logger.info(f"++ Found parent ROM mapping: [{parent_rom_part}] linked from alias [{rom}]")
                                    working_rom_list.append(parent_rom_part)
                                break
                    
                    if captured_alias_lines:
                        self.logger.info(f"++ Slicing out exact active VPMAlias routing line for [{rom}]")
                        dest_alias_dir = os.path.join(package.directory, package.name, 'VPinMAME')
                        os.makedirs(dest_alias_dir, exist_ok=True)
                        dest_alias_file = os.path.normpath(os.path.join(dest_alias_dir, 'VPMAlias.txt'))
                        
                        with open(dest_alias_file, 'w', encoding='utf-8') as f_out:
                            f_out.writelines(captured_alias_lines)
                        
                        self.logger.info(f"++ Cleanly wrote exact single line to staging folder.")
                        alias_processed = True
                        
                except Exception as e:
                    self.logger.error(f"[Alias LOG] Error handling alias extraction: {str(e)}")

            # 3. --- FLAT FILE CHECKS (cfg, nvram, roms, memcard) ---
            for standard_dir, virtual_target in [
                ('cfg', 'VPinMAME/cfg'),
                ('nvram', 'VPinMAME/nvram'),
                ('roms', 'VPinMAME/roms'),
                ('memcard', 'VPinMAME/memcard')
            ]:
                search_path = os.path.join(vpinmame_base, standard_dir)
                if os.path.exists(search_path):
                    for standard_file in Path(search_path).glob('*%s*' % rom):
                        if standard_file.is_file():
                            package.add_file(standard_file, virtual_target)
                            self.logger.info(f"++ Backed up physical VPinMAME asset: {standard_dir}/{standard_file.name}")

            # 4. --- DMDDEVICE.INI PRECISE BLOCK EXTRACTOR ---
            dmd_ini_path = os.path.join(vpinmame_base, 'DmdDevice.ini')
            if os.path.exists(dmd_ini_path):
                try:
                    with open(dmd_ini_path, 'r', encoding='utf-8', errors='ignore') as f:
                        ini_lines = f.readlines()
                    
                    captured_lines = []
                    inside_rom_block = False
                    target_header = f"[{rom.lower()}]"
                    
                    for line in ini_lines:
                        clean_line = line.strip().lower()
                        
                        if clean_line.startswith('[') and clean_line.endswith(']'):
                            if inside_rom_block:
                                break
                            if clean_line == target_header:
                                inside_rom_block = True
                        
                        if inside_rom_block:
                            # If we are reading a parent ROM block but we have an active alias game running,
                            # dynamically rename the INI block header to use the table's primary active alias.
                            if rom.lower() != primary_table_rom.lower() and clean_line == target_header:
                                captured_lines.append(f"[{primary_table_rom.lower()}]\n")
                            else:
                                captured_lines.append(line)
                    
                    if captured_lines:
                        self.logger.info(f"++ Slicing out custom DMD profile details for [{rom}] mapped to [{primary_table_rom}]")
                        dest_ini_dir = os.path.join(package.directory, package.name, 'VPinMAME')
                        os.makedirs(dest_ini_dir, exist_ok=True)
                        dest_ini_file = os.path.normpath(os.path.join(dest_ini_dir, 'DmdDevice.ini'))
                        
                        with open(dest_ini_file, 'w', encoding='utf-8') as f_out:
                            f_out.writelines(captured_lines)
                        
                        self.logger.info(f"++ Cleanly wrote sliced DmdDevice.ini directly to staging folder.")
                        custom_dmd_processed = True
                        
                except Exception as e:
                    self.logger.error(f"[DMD LOG] Error handling custom profile extraction: {str(e)}")

            # 5. --- B2STABLESETTINGS.XML BLOCK EXTRACTOR ---
            b2s_xml_path = os.path.join(self.visual_pinball_path, 'tables', 'B2STableSettings.xml')
            if os.path.exists(b2s_xml_path):
                try:
                    with open(b2s_xml_path, 'r', encoding='utf-8', errors='ignore') as f:
                        xml_lines = f.readlines()
                    
                    captured_b2s_lines = []
                    inside_b2s_block = False
                    start_tag = f"<{rom.lower()}>"
                    end_tag = f"</{rom.lower()}>"
                    
                    for line in xml_lines:
                        clean_line = line.strip().lower()
                        
                        if start_tag in clean_line:
                            inside_b2s_block = True
                        
                        if inside_b2s_block:
                            if rom.lower() != primary_table_rom.lower():
                                modified_line = line.replace(f"<{rom}>", f"<{primary_table_rom}>")
                                modified_line = modified_line.replace(f"</{rom}>", f"</{primary_table_rom}>")
                                modified_line = modified_line.replace(f"<{rom.lower()}>", f"<{primary_table_rom.lower()}>")
                                modified_line = modified_line.replace(f"</{rom.lower()}>", f"</{primary_table_rom.lower()}>")
                                captured_b2s_lines.append(modified_line)
                            else:
                                captured_b2s_lines.append(line)
                            
                        if end_tag in clean_line:
                            inside_b2s_block = False
                            break
                    
                    if captured_b2s_lines:
                        self.logger.info(f"++ Slicing out custom B2S XML profile settings for [{rom}] mapped to [{primary_table_rom}]")
                        dest_b2s_dir = os.path.join(package.directory, package.name, 'visual pinball', 'tables')
                        os.makedirs(dest_b2s_dir, exist_ok=True)
                        dest_b2s_file = os.path.normpath(os.path.join(dest_b2s_dir, 'B2STableSettings.xml'))
                        
                        with open(dest_b2s_file, 'w', encoding='utf-8') as f_out:
                            f_out.write("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n")
                            f_out.write("<B2STableSettings>\n")
                            f_out.writelines(captured_b2s_lines)
                            f_out.write("</B2STableSettings>\n")
                        
                        self.logger.info(f"++ Cleanly wrote structured B2S configuration block to staging folder.")
                        
                except Exception as e:
                    self.logger.error(f"[B2S XML LOG] Error handling custom XML block profile extraction: {str(e)}")

        # 6. --- TABLE DIRECTORY .RES OVERRIDE DETECTOR ---
        try:
            tables_dir = os.path.join(self.visual_pinball_path, 'tables')
            res_filename = f"{package.name}.res"
            target_res_path = os.path.join(tables_dir, res_filename)

            if os.path.exists(target_res_path) and os.path.isfile(target_res_path):
                self.logger.info(f"++ Found custom table override screen profile: {res_filename}")
                package.add_file(Path(target_res_path), 'visual pinball/tables')
                self.logger.info(f"++ Safely staged .res file via package index mapping.")
        except Exception as e:
            self.logger.error(f"[RES Checker Log] Failed scanning for table .res asset: {str(e)}")

        # Update and save the package metadata tree presence flags
        package.set_field('visual pinball/info/has_custom_dmd', 'Yes' if custom_dmd_processed else 'No')
        package.set_field('visual pinball/info/has_alias', 'Yes' if alias_processed else 'No')

    def deploy(self, package: Package) -> None:
        self.logger.info("* VPinMame files")
        package_stage_path = os.path.join(self.baseModel.tmp_path, package.name)
        if not Path(package_stage_path).exists():
            raise ValueError('path not found (%s)' % package_stage_path)

        # Handle regular VPinMAME folder drops
        vpm_stage = os.path.join(package_stage_path, "VPinMAME")
        if os.path.exists(vpm_stage):
            for item in os.listdir(vpm_stage):
                s = os.path.join(vpm_stage, item)
                d = os.path.normpath(os.path.join(self.baseModel.visual_pinball_path, "VPinMAME", item))
                if os.path.isdir(s):
                    copytree(self.logger, s, d)
                elif os.path.isfile(s):
                    if item == 'DmdDevice.ini':
                        self.merge_dmd_ini(s, d)
                    elif item == 'VPMAlias.txt':
                        self.merge_alias_file(s, d)

        # Handle tables folder additions (B2STableSettings snippet insertion & generic files like .res)
        tables_stage = os.path.join(package_stage_path, "visual pinball", "tables")
        if os.path.exists(tables_stage):
            for item in os.listdir(tables_stage):
                s = os.path.join(tables_stage, item)
                d = os.path.normpath(os.path.join(self.visual_pinball_path, "tables", item))
                if os.path.isfile(s):
                    if item == 'B2STableSettings.xml':
                        self.merge_b2s_xml(s, d)
                    else:
                        shutil.copy2(s, d)
                        self.logger.info(f"++ Deployed table asset: {item}")

    def merge_alias_file(self, source_snippet, target_global_file):
        """Merges new alias rules into the destination global file without losing existing entries."""
        try:
            if not os.path.exists(source_snippet):
                return
                
            with open(source_snippet, 'r', encoding='utf-8') as f:
                new_lines = f.readlines()
                
            if not os.path.exists(target_global_file):
                with open(target_global_file, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                return
                
            with open(target_global_file, 'r', encoding='utf-8', errors='ignore') as f:
                existing_lines = f.readlines()
                
            existing_keys = set()
            for line in existing_lines:
                if line.strip() and not line.strip().startswith(';'):
                    parts = line.split(',')
                    if parts:
                        existing_keys.add(parts[0].strip().lower())
                        
            lines_to_append = []
            for line in new_lines:
                if line.strip() and not line.strip().startswith(';'):
                    parts = line.split(',')
                    if parts and parts[0].strip().lower() not in existing_keys:
                        lines_to_append.append(line)
                        
            if lines_to_append:
                with open(target_global_file, 'a', encoding='utf-8') as f:
                    if not existing_lines[-1].endswith('\n'):
                        f.write('\n')
                    f.writelines(lines_to_append)
                self.logger.info("++ Successfully merged snippet rules into global VPMAlias.txt configuration.")
        except Exception as e:
            self.logger.error(f"[Alias Merge Error] Failed merging entries: {str(e)}")

    def merge_dmd_ini(self, source_snippet, target_global_file):
        """Surgically inserts or updates a single table block profile within the master global DmdDevice.ini."""
        try:
            if not os.path.exists(source_snippet):
                return

            with open(source_snippet, 'r', encoding='utf-8') as f:
                snippet_lines = f.readlines()

            target_header = ""
            for line in snippet_lines:
                if line.strip().startswith('[') and line.strip().endswith(']'):
                    target_header = line.strip().lower()
                    break

            if not target_header:
                return

            if not os.path.exists(target_global_file):
                shutil.copy2(source_snippet, target_global_file)
                self.logger.info("++ Global DmdDevice.ini missing on target. Created file from snippet profile.")
                return

            with open(target_global_file, 'r', encoding='utf-8', errors='ignore') as f:
                global_lines = f.readlines()

            header_index = -1
            for idx, line in enumerate(global_lines):
                if line.strip().lower() == target_header:
                    header_index = idx
                    break

            if header_index != -1:
                end_index = len(global_lines)
                for idx in range(header_index + 1, len(global_lines)):
                    if global_lines[idx].strip().startswith('[') and global_lines[idx].strip().endswith(']'):
                        end_index = idx
                        break
                
                updated_content = global_lines[:header_index] + snippet_lines + global_lines[end_index:]
                with open(target_global_file, 'w', encoding='utf-8') as f:
                    f.writelines(updated_content)
                self.logger.info(f"++ Successfully overwritten existing custom DMD block settings for {target_header} inside global INI.")
            else:
                if global_lines and not global_lines[-1].endswith('\n'):
                    global_lines.append('\n')
                global_lines.extend(snippet_lines)
                
                with open(target_global_file, 'w', encoding='utf-8') as f:
                    f.writelines(global_lines)
                self.logger.info(f"++ Successfully appended new custom DMD parameters for {target_header} to global DmdDevice.ini matrix.")

        except Exception as e:
            self.logger.error(f"[DMD INI Merge Error] Failed processing machine layout insertion: {str(e)}")

    def merge_b2s_xml(self, source_snippet, target_global_file):
        """Surgically merges or updates a specific table node inside B2STableSettings.xml using a structural XML parser."""
        try:
            if not os.path.exists(source_snippet):
                return

            # Parse incoming snippet tree element structure
            snippet_tree = ET.parse(source_snippet)
            snippet_root = snippet_tree.getroot()
            
            # Find the active single game sub-node inside the snippet framework (e.g., <clas1812abc>)
            incoming_game_node = None
            for child in snippet_root:
                incoming_game_node = child
                break
                
            if incoming_game_node is None:
                return  # Empty snippet profile
                
            rom_tag_name = incoming_game_node.tag

            # If global file path layout completely lacks a master document, generate it clean from our template source
            if not os.path.exists(target_global_file):
                shutil.copy2(source_snippet, target_global_file)
                self.logger.info("++ Global B2STableSettings.xml was missing. Initialized file using template snippet.")
                return

            # Parse the destination machine's true live configuration matrix
            global_tree = ET.parse(target_global_file)
            global_root = global_tree.getroot()

            # Look for an existing node with the exact same case-insensitive tag name
            existing_node = None
            for child in global_root:
                if child.tag.lower() == rom_tag_name.lower():
                    existing_node = child
                    break

            if existing_node is not None:
                # Node profile exists! Clear it out and re-inject our synchronized backup nodes safely
                global_root.remove(existing_node)
                global_root.append(incoming_game_node)
                self.logger.info(f"++ Surgically updated custom XML attributes for node: <{rom_tag_name}>")
            else:
                # Brand new game layout addition. Safe to append right to the root stack
                global_root.append(incoming_game_node)
                self.logger.info(f"++ Injected brand new custom configuration layout node: <{rom_tag_name}>")

            # Write tree updates cleanly back to the global destination file path
            global_tree.write(target_global_file, encoding='utf-8', xml_declaration=True)

        except Exception as e:
            self.logger.error(f"[B2S XML Merge Error] Error merging XML profiles structure natively: {str(e)}")

    def delete(self, tableName: str, rom_list: list) -> None:
        if rom_list is None:
            return

        self.logger.info("* VPinMame files '%s'" % ' '.join(rom_list))

        for rom in rom_list:
            for rom_file in Path(self.visual_pinball_path + '/VPinMAME').glob('**/*%s.*' % rom):
                if rom_file.is_file():
                    self.logger.info("- remove %s file" % rom_file)
                    os.remove(rom_file)
                elif rom_file.is_dir() and ("altcolor" in str(rom_file) or "altsound" in str(rom_file)):
                    self.logger.info("- remove %s folder tree" % rom_file)
                    shutil.rmtree(rom_file, ignore_errors=True)