import os
import shutil
from pathlib import Path
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
        # Look for a .res file matching the package name inside the tables directory
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
                d = os.path.join(self.baseModel.visual_pinball_path, "VPinMAME", item)
                if os.path.isdir(s):
                    copytree(self.logger, s, d)
                elif os.path.isfile(s):
                    if item == 'DmdDevice.ini':
                        shutil.copy2(s, d)
                    elif item == 'VPMAlias.txt':
                        self.merge_alias_file(s, d)

        # Handle tables folder additions (B2STableSettings snippet insertion & generic files like .res)
        tables_stage = os.path.join(package_stage_path, "visual pinball", "tables")
        if os.path.exists(tables_stage):
            for item in os.listdir(tables_stage):
                s = os.path.join(tables_stage, item)
                d = os.path.join(self.visual_pinball_path, "tables", item)
                if os.path.isfile(s):
                    if item == 'B2STableSettings.xml':
                        self.merge_b2s_xml(s, d)
                    else:
                        # Direct file drops for any supplementary tracked items (like our newly added .res file)
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

    def merge_b2s_xml(self, source_snippet, target_global_file):
        """Gracefully merges or modifies specific ROM configuration nodes inside B2STableSettings.xml."""
        try:
            if not os.path.exists(source_snippet):
                return

            # Read the incoming snippet block configuration rules
            with open(source_snippet, 'r', encoding='utf-8') as f:
                snippet_content = f.read()

            # Locate inner elements inside the root structural framework
            start_idx = snippet_content.find('<B2STableSettings>') + len('<B2STableSettings>')
            end_idx = snippet_content.rfind('</B2STableSettings>')
            if start_idx == -1 or end_idx == -1:
                return  # Malformed block profile snippet frame
            
            inner_snippet = snippet_content[start_idx:end_idx].strip()
            if not inner_snippet:
                return

            # Isolate the explicit sub-node name (e.g., "<clas1812abc>")
            first_bracket = inner_snippet.find('<')
            next_bracket = inner_snippet.find('>')
            if first_bracket == -1 or next_bracket == -1:
                return
            rom_tag = inner_snippet[first_bracket:next_bracket+1]  # returns "<clas1812abc>"
            rom_close_tag = rom_tag.replace('<', '</')

            # Handle blank/unconfigured target setups natively
            if not os.path.exists(target_global_file):
                shutil.copy2(source_snippet, target_global_file)
                return

            with open(target_global_file, 'r', encoding='utf-8', errors='ignore') as f:
                global_content = f.read()

            # If node settings already exist inside the cabinet machine, overwrite them cleanly
            if rom_tag.lower() in global_content.lower():
                g_start = global_content.lower().find(rom_tag.lower())
                g_end = global_content.lower().find(rom_close_tag.lower()) + len(rom_close_tag)
                
                if g_start != -1 and g_end != -1:
                    updated_content = global_content[:g_start] + inner_snippet + "\n  " + global_content[g_end:]
                    with open(target_global_file, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    self.logger.info(f"++ Successfully updated existing custom B2S XML profile fields for {rom_tag}")
            else:
                # Node configuration layout is brand new; append it directly above the master closing footer block
                insert_idx = global_content.rfind('</B2STableSettings>')
                if insert_idx != -1:
                    updated_content = global_content[:insert_idx] + "  " + inner_snippet + "\n" + global_content[insert_idx:]
                    with open(target_global_file, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    self.logger.info(f"++ Successfully injected new custom B2S XML block parameters for {rom_tag}")

        except Exception as e:
            self.logger.error(f"[B2S XML Merge Error] Failed inserting target parameters: {str(e)}")

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