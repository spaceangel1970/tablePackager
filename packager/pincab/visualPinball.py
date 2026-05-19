from packager.tools.toolbox import *
from packager.model.package import Package
import subprocess
import tkinter


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
        if rom == '':
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

    """
    def extract_ultraDMD(self, vpt_file):  # TODO: deprecated?
        str = extract_string_from_binary_file(vpt_file, br'cAssetsFolder[ ]*=[ ]*"([a-zA-Z0-9_]+)"')
        str = extract_string_from_binary_file(vpt_file, br'TableName[ ]*=[ ]*"([a-zA-Z0-9_]+)"')
    """

    def extract_rom_name(self, vpt_file: Path) -> list:
        import re
        
        active_roms = []
        escaped_roms = []
        
        try:
            # Read the raw file bytes directly
            with open(vpt_file, 'rb') as f:
                content = f.read()
                
            # Decode to text, ignoring non-text binary bytes cleanly
            text_content = content.decode('utf-8', errors='ignore')
            
            # This universal pattern catches: standard variables, Const, Dim, wide spaces, and tabs
            # Grabs the game name inside the quotes
            pattern = r'(?:(?:Public|Private)\s+)?(?:Const|Dim)?\s*(?:cGameName|RomSet|GameName)\s*=\s*"([a-zA-Z0-9_]+)"'
            
            # Find every single line matching our target variables
            for match in re.finditer(pattern, text_content, re.IGNORECASE):
                rom_name = match.group(1).strip()
                
                # Check if this line was commented out in VBScript
                # Look backwards from the start of the match to check for a single quote mark
                line_start = text_content.rfind('\n', 0, match.start())
                if line_start == -1:
                    line_start = 0
                
                line_prefix = text_content[line_start:match.start()]
                
                if "'" in line_prefix:
                    if rom_name not in escaped_roms:
                        escaped_roms.append(rom_name)
                else:
                    if rom_name not in active_roms:
                        active_roms.append(rom_name)
                        
        except Exception as e:
            self.logger.error(f"Fallback byte-scanner error: {str(e)}")

        # Clean out "yourgame" generic placeholders if they slipped in
        active_roms = [r for r in active_roms if r.lower() != "yourgame"]
        escaped_roms = [r for r in escaped_roms if r.lower() != "yourgame"]

        # Keep your framework's expected return format exactly intact
        final_list = active_roms + escaped_roms
        return final_list

    def extract_table_name(self, vpt_file: Path) -> list:
        return extract_string_from_binary_file(vpt_file, br'TableName[ ]*=[ ]*"([a-zA-Z0-9_]+)"')

    def extract_pov_file(self, package: Package, vp_file: Path) -> None:
        cmd_line = ["%s/VPinballX.exe" % self.visual_pinball_path, "-pov", vp_file]
        self.logger.info("%s/VPinballX.exe -pov %s" % (self.visual_pinball_path, vp_file))
        subprocess.call(cmd_line)
