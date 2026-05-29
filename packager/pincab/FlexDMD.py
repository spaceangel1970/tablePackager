import os
import shutil
import re
from pathlib import Path
from tkinter import messagebox

from packager.model.package import Package
from packager.tools.toolbox import *


class FlexDMD:
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
        self.logger.info("* FlexDMD files")

        # 1. FlexDMD Detection Logic
        for flexDMDItem in tablePath.glob('**/*.FlexDMD'):
            flexDMDDir = str(Path(flexDMDItem).name)
            flexDMDStem = str(Path(flexDMDItem).stem)
            score = searchSentenceInString(flexDMDStem, table_name)
            if score > 0.2:
                self.logger.info(f"+ Auto-detected and adding FlexDMD: '{flexDMDDir}' (score={score:.2f})")
                package.set_field('visual pinball/info/flexDMD', flexDMDDir)
                for file in Path(flexDMDItem).glob('**/*'):
                    if file.is_file():
                        rel_path = file.relative_to(flexDMDItem)
                        dst_field = f"FlexDMD/{flexDMDDir}"
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
                        target_header = f"[{flexDMDStem.lower().strip()}]"
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
                            self.logger.info(f"++ Sliced DmdDevice.ini settings for FlexDMD: {flexDMDStem}")
                    except Exception as e:
                        self.logger.error(f"[FlexDMD/DMD LOG] Error slicing DmdDevice.ini: {e}")

        if not package.exists_field('visual pinball/info/has_custom_dmd'):
            package.set_field('visual pinball/info/has_custom_dmd', 'No')

    def deploy(self, package: Package) -> None:
        if not os.path.exists(self.baseModel.visual_pinball_path):
            raise ValueError('Visual Pinball not found(%s)' % self.baseModel.visual_pinball_path)

        if not Path(self.baseModel.tmp_path + "/" + package.name).exists():
            raise ValueError('Package Tree not found (%s)' % (self.baseModel.tmp_path + "/" + package.name))

        if not package.exists_field('visual pinball/info/flexDMD'):
            self.logger.info("* No FlexDMD files")
            return True

        self.logger.info("* FlexDMD files")
        flexDMD = package.get_field('visual pinball/info/flexDMD')

        dest_name = flexDMD if flexDMD.lower().endswith('.flexdmd') else f"{flexDMD}.FlexDMD"

        copytree(self.logger,
             self.baseModel.tmp_path + "/" + package.name + "/FlexDMD/" + flexDMD,
             self.baseModel.visual_pinball_path + "/tables/" + dest_name)
        return True

    def delete(self, table_name: str, dir_name: str = None) -> None:
        if not os.path.exists(self.baseModel.visual_pinball_path):
            raise ValueError('Visual Pinball not found(%s)' % self.baseModel.visual_pinball_path)

        tablePath = Path(self.baseModel.visual_pinball_path + "/tables")
        self.logger.info("* FlexDMD files")

        if dir_name is None:
            for flexDMDItem in tablePath.glob('**/*.FlexDMD'):
                flexDMDDir = str(Path(flexDMDItem).name)
                score = searchSentenceInString(str(Path(flexDMDItem).stem), table_name)
                self.logger.info(
                    "+ Looking for FlexDMD '%s' (score=%02f)" % (flexDMDDir, score))
                if score > 0.2:
                    self.logger.info("- Remove FlexDMD dir '%s'" % flexDMDDir)
                    shutil.rmtree(flexDMDItem)
        else:
            self.logger.info("- Remove FlexDMD dir '%s'" % dir_name)
            dest_name = dir_name if dir_name.lower().endswith('.flexdmd') else f"{dir_name}.FlexDMD"
            delPath = self.baseModel.visual_pinball_path + '/tables/' + dest_name
            if os.path.exists(delPath):
                shutil.rmtree(delPath)
