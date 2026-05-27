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
            flexDMDDir = str(Path(flexDMDItem).stem)
            score = searchSentenceInString(flexDMDDir, table_name)
            if score > 0.2:
                # ... (Keep your existing FlexDMD extraction logic here)
                # ...
                package.set_field('visual pinball/info/flexDMD', flexDMDDir)
                for file in flexDMDItem.glob('**/*'):
                    if file.is_file():
                        package.add_file(file, f'FlexDMD/{flexDMDDir}')

        # 2. UltraDMD / DmdDevice.ini Logic (MOVED OUTSIDE)
        # This now runs for every table, but only executes if the folder is found
        try:
            rom_field = package.get_field('visual pinball/info/romName')
            roms = rom_field if isinstance(rom_field, list) else [rom_field]
            vpinmame_base = os.path.abspath(os.path.join(self.baseModel.visual_pinball_path, 'VPinMAME'))
            
            for rom in roms:
                if rom and os.path.isdir(os.path.join(vpinmame_base, f"{rom}.UltraDMD")):
                    dmd_ini_path = os.path.join(vpinmame_base, 'DmdDevice.ini')
                    if os.path.exists(dmd_ini_path):
                        # ... (Include your header matching and file writing logic here)
                        self.logger.info(f"UltraDMD detected for {rom}, extracting settings...")
                        # ...
        except Exception as e:
            self.logger.error(f"[DMD LOG] Error extracting DmdDevice.ini: {str(e)}")

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

        copytree(self.logger,
             self.baseModel.tmp_path + "/" + package.name + "/FlexDMD",
             self.baseModel.visual_pinball_path + "/tables/" + flexDMD + ".FlexDMD")
        return True

    def delete(self, table_name: str, dir_name: str = None) -> None:
        if not os.path.exists(self.baseModel.visual_pinball_path):
            raise ValueError('Visual Pinball not found(%s)' % self.baseModel.visual_pinball_path)

        tablePath = Path(self.baseModel.visual_pinball_path + "/tables")
        self.logger.info("* FlexDMD files")

        if dir_name is None:
            for flexDMDItem in tablePath.glob('**/*.FlexDMD'):
                flexDMDDir = str(Path(flexDMDItem).stem)
                score = searchSentenceInString(flexDMDDir, table_name)
                self.logger.info(
                    "+ Looking for FlexDMD '%s' (score=%02f)" % (Path(flexDMDItem).stem, score))
                if score > 0.2:
                    result = messagebox.askokcancel(
                        "Delete FlexDMD",
                        "Found %s.FlexDMD directory, delete it ?" % Path(flexDMDItem).stem)
                    if result:
                        self.logger.info("- Remove FlexDMD dir '%s'" % flexDMDDir)
                        shutil.rmtree(flexDMDItem)
        else:
            self.logger.info("- Remove FlexDMD dir '%s'" % dir_name)
            delPath = self.baseModel.visual_pinball_path + '/tables/' + dir_name + '.FlexDMD'
            shutil.rmtree(delPath)
