import os
import shutil
from pathlib import Path
import subprocess
import tkinter
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

        self.logger.info("* Visual Pinball X files")
        vpx_file = Path(self.visual_pinball_path + '/tables/' + package.name + '.vpx')
        ini_file = Path(self.visual_pinball_path + '/tables/' + package.name + '.ini')
        pov_file = Path(self.visual_pinball_path + '/tables/' + package.name + '.pov')
        vpt_file = Path(self.visual_pinball_path + '/tables/' + package.name + '.vpt')
        directb2s_file = Path(self.visual_pinball_path + "/tables/" + vpx_file.stem + '.directb2s')
        music_file = Path(
            self.visual_pinball_path + "/Music/" + vpx_file.stem + '.mp3')  # TODO: store music into media/Audio?

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

        if music_file.exists():
            package.add_file(music_file, 'media/Audio')

    def deploy(self, package: Package) -> None:
        self.logger.info("* Visual Pinball X files")
        if not os.path.exists(self.visual_pinball_path):
            raise ValueError('Visual Pinball not found(%s)' % self.visual_pinball_path)

        if not Path(self.baseModel.tmp_path + "/" + package.name).exists():
            raise ValueError('Package Tree not found (%s)' % (self.baseModel.tmp_path + "/" + package.name))

        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/visual pinball/tables",
                 self.baseModel.visual_pinball_path + "/tables")
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
        music_file = Path(
            self.visual_pinball_path + "/Music/" + vpx_file.stem + '.mp3')  # TODO: store music into media/Audio?

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
        if music_file.exists():
            self.logger.info("- remove %s file" % music_file)
            os.remove(music_file)

    def extract_rom_name(self, vpt_file: Path) -> list:
        import re
        
        active_roms = []
        
        try:
            # Read the raw file bytes directly
            with open(vpt_file, 'rb') as f:
                content = f.read()
                
            # Decode to text, ignoring non-text binary bytes cleanly
            text_content = content.decode('utf-8', errors='ignore')
            
            # --- FAILSAFE COMMENT-AWARE REGEX ENGINE ---
            # 1. ^[ \t]* checks for whitespace or tabs at the start of a row
            # 2. (?!') Lookahead instantly skips the match if the line is commented out with a single quote
            # 3. Matches and extracts the alpha-numeric target name safely inside single or double quotes
            
            p_pattern = r"^[ \t]*(?!')(?:(?:Public|Private)\s+)?(?:Dim)?\s*pGameName\s*=\s*[\"']([a-zA-Z0-9_]+)[\"']"
            standard_pattern = r"^[ \t]*(?!')(?:(?:Public|Private)\s+)?(?:Const|Dim)?\s*(?:cGameName|RomSet|GameName)\s*=\s*[\"']([a-zA-Z0-9_]+)[\"']"
            
            # Helper to run match extractions on active code lines only
            def process_matches(regex_pattern):
                # re.MULTILINE links the '^' anchor to the start of every text line break inside the table string
                for match in re.finditer(regex_pattern, text_content, re.IGNORECASE | re.MULTILINE):
                    rom_name = match.group(1).strip()
                    if rom_name not in active_roms:
                        active_roms.append(rom_name)

            # Look for active pGameName definitions first (Highest Priority for PinUp System paths)
            process_matches(p_pattern)
            
            # Look for active fallback hardware definitions next (Standard Priority)
            process_matches(standard_pattern)
                        
        except Exception as e:
            self.logger.error(f"Fallback byte-scanner error: {str(e)}")

        # Clean out "yourgame" generic code placeholders
        active_roms = [r for r in active_roms if r.lower() != "yourgame"]

        return active_roms

    def extract_table_name(self, vpt_file: Path) -> list:
        return extract_string_from_binary_file(vpt_file, br'TableName[ ]*=[ ]*"([a-zA-Z0-9_]+)"')

    def extract_pov_file(self, package: Package, vp_file: Path) -> None:
        cmd_line = ["%s/VPinballX.exe" % self.visual_pinball_path, "-pov", vp_file]
        self.logger.info("%s/VPinballX.exe -pov %s" % (self.visual_pinball_path, vp_file))
        subprocess.call(cmd_line)