from packager.tools.toolbox import *
from packager.model.package import Package
from pathlib import Path
import shutil
import os

class UltraDMD:
    def __init__(self, logger, baseModel):
        self.__baseModel = baseModel
        self.__logger = logger

    @property
    def baseModel(self):
        return self.__baseModel

    @property
    def logger(self):
        return self.__logger

    def extract(self, table_name: str, package: Package) -> None:
        if not os.path.exists(self.baseModel.visual_pinball_path):
            raise ValueError('Visual Pinball not found(%s)' % self.baseModel.visual_pinball_path)

        tablePath = Path(self.baseModel.visual_pinball_path + "/tables")
        self.logger.info("* UltraDMD files")

        for ultraDMDItem in tablePath.glob('**/*.UltraDMD'):
            ultraDMDDir = str(Path(ultraDMDItem).name)
            ultraDMDStem = str(Path(ultraDMDItem).stem)
            score = searchSentenceInString(ultraDMDStem, table_name)
            
            # Auto-proceed if score > 0.2
            if score > 0.2:
                self.logger.info(f"+ Auto-detected and adding UltraDMD: '{ultraDMDDir}' (score={score:.2f})")
                
                package.set_field('visual pinball/info/ultraDMD', ultraDMDDir)
                
                # Recursively add all files within the UltraDMD folder
                for file in Path(ultraDMDItem).glob('**/*'):
                    if file.is_file():
                        rel_path = file.relative_to(ultraDMDItem)
                        dst_field = f"UltraDMD/{ultraDMDDir}"
                        if str(rel_path.parent) != '.':
                            dst_field += f"/{str(rel_path.parent).replace('\\', '/')}"
                        package.add_file(str(file), dst_field)
                
                # 2. Slicing DmdDevice.ini logic
                vpinmame_base = os.path.abspath(os.path.join(self.baseModel.visual_pinball_path, 'VPinMAME'))
                dmd_ini_path = os.path.join(vpinmame_base, 'DmdDevice.ini')
                if os.path.exists(dmd_ini_path):
                    try:
                        with open(dmd_ini_path, 'r', encoding='utf-8', errors='ignore') as f:
                            ini_lines = f.readlines()
                        target_header = f"[{ultraDMDStem.lower().strip()}]"
                        captured_lines = []
                        inside_block = False
                        for line in ini_lines:
                            clean = line.strip().lower()
                            if clean.startswith('[') and clean.endswith(']'):
                                if inside_block: break
                                if clean == target_header: inside_block = True
                            if inside_block: captured_lines.append(line)
                        if captured_lines:
                            vpm_dest_dir = os.path.join(package.directory, package.name, 'VPinMAME')
                            os.makedirs(vpm_dest_dir, exist_ok=True)
                            with open(os.path.join(vpm_dest_dir, 'DmdDevice.ini'), 'w', encoding='utf-8') as f_out:
                                f_out.writelines(captured_lines)
                            package.set_field('visual pinball/info/has_custom_dmd', 'Yes')
                            self.logger.info(f"++ Sliced DmdDevice.ini settings for UltraDMD: {ultraDMDStem}")
                    except Exception as e:
                        self.logger.error(f"[UltraDMD/DMD LOG] Error slicing DmdDevice.ini: {e}")

    def deploy(self, package: Package) -> None:
        if not os.path.exists(self.baseModel.visual_pinball_path):
            raise ValueError('Visual Pinball not found(%s)' % self.baseModel.visual_pinball_path)

        if not Path(self.baseModel.tmp_path + "/" + package.name).exists():
            raise ValueError('Package Tree not found (%s)' % (self.baseModel.tmp_path + "/" + package.name))

        if not package.exists_field('visual pinball/info/ultraDMD'):
            self.logger.info("* No Ultra DMD files")
            return True

        self.logger.info("* Ultra DMD files")
        ultraDMD = package.get_field('visual pinball/info/ultraDMD')

        dest_name = ultraDMD if ultraDMD.lower().endswith('.ultradmd') else f"{ultraDMD}.UltraDMD"

        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/UltraDMD/" + ultraDMD,
                 self.baseModel.visual_pinball_path + "/tables/" + dest_name)
        return True

    def delete(self, table_name: str, dir_name: str = None) -> None:
        if not os.path.exists(self.baseModel.visual_pinball_path):
            raise ValueError('Visual Pinball not found(%s)' % self.baseModel.visual_pinball_path)

        tablePath = Path(self.baseModel.visual_pinball_path + "/tables")
        self.logger.info("* UltraDMD files")

        if dir_name is None:
            for ultraDMDItem in tablePath.glob('**/*.UltraDMD'):
                ultraDMDDir = str(Path(ultraDMDItem).name)
                score = searchSentenceInString(str(Path(ultraDMDItem).stem), table_name)
                if score > 0.2:
                    self.logger.info("- Remove Ultra DMD dir '%s'" % ultraDMDDir)
                    shutil.rmtree(ultraDMDItem)
        else:
            self.logger.info("- Remove Ultra DMD dir '%s'" % dir_name)
            dest_name = dir_name if dir_name.lower().endswith('.ultradmd') else f"{dir_name}.UltraDMD"
            delPath = self.baseModel.visual_pinball_path + '/tables/' + dest_name
            if os.path.exists(delPath):
                shutil.rmtree(delPath)