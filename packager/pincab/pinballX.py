import os
import shutil
from packager.tools.toolbox import *
from packager.model.package import Package
from pathlib import Path


class PinballX:
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
    def pinballX_path(self):
        return self.__baseModel.pinballX_path

    def get_product_path(self, product: str) -> str:
        if product == 'visual pinball':
            return 'Visual Pinball'
        return 'Visual Pinball'

    def extract(self, table_name, package):
        if not os.path.exists(self.pinballX_path):
            self.logger.warning('PinballX not found (%s)' % self.pinballX_path)
            return

        self.logger.info("* Pinball X files")
        for file in Path(self.pinballX_path).glob('**/*%s*' % table_name):
            if "Flyer Images\\Back" in str(file.parent):
                if is_suffix(file, '.back'):
                    package.add_file(file, 'media/Flyers Back', dst_file=file.stem + file.suffix)
                else:
                    package.add_file(file, 'media/Flyers Back', dst_file=file.stem + ".back" + file.suffix)
            elif "Flyer Images\\Front" in str(file.parent):
                if is_suffix(file, '.front'):
                    package.add_file(file, 'media/Flyers Front', dst_file=file.stem + file.suffix)
                else:
                    package.add_file(file, 'media/Flyers Front', dst_file=file.stem + ".front" + file.suffix)
            elif "Flyer Images\\Inside1" in str(file.parent):
                if is_suffix(file, '.inside1'):
                    package.add_file(file, 'media/Flyers Inside', dst_file=file.stem + file.suffix)
                else:
                    package.add_file(file, 'media/Flyers Inside', dst_file=file.stem + ".inside1" + file.suffix)
            elif "Flyer Images\\Inside2" in str(file.parent):
                if is_suffix(file, '.inside2'):
                    package.add_file(file, 'media/Flyers Inside', dst_file=file.stem + file.suffix)
                else:
                    package.add_file(file, 'media/Flyers Inside', dst_file=file.stem + ".inside2" + file.suffix)
            elif "Flyer Images\\Inside3" in str(file.parent):
                if is_suffix(file, '.inside3'):
                    package.add_file(file, 'media/Flyers Inside', dst_file=file.stem + file.suffix)
                else:
                    package.add_file(file, 'media/Flyers Inside', dst_file=file.stem + ".inside3" + file.suffix)
            elif "Flyer Images\\Inside4" in str(file.parent):
                if is_suffix(file, '.inside4'):
                    package.add_file(file, 'media/Flyers Inside', dst_file=file.stem + file.suffix)
                else:
                    package.add_file(file, 'media/Flyers Inside', dst_file=file.stem + ".inside4" + file.suffix)
            elif "Flyer Images\\Inside5" in str(file.parent):
                if is_suffix(file, '.inside5'):
                    package.add_file(file, 'media/Flyers Inside', dst_file=file.stem + file.suffix)
                else:
                    package.add_file(file, 'media/Flyers Inside', dst_file=file.stem + ".inside5" + file.suffix)
            elif "Flyer Images\\Inside6" in str(file.parent):
                if is_suffix(file, '.inside6'):
                    package.add_file(file, 'media/Flyers Inside', dst_file=file.stem + file.suffix)
                else:
                    package.add_file(file, 'media/Flyers Inside', dst_file=file.stem + ".inside6" + file.suffix)
            elif "High Scores\\Visual Pinball" in str(file.parent):
                package.add_file(file, 'media/HighScores')
            elif "Instruction Cards" in str(file.parent):
                package.add_file(file, 'media/Instruction Cards')
            elif "Backglass Images" in str(file.parent):
                package.add_file(file, 'media/Backglass')
            elif "DMD Images" in str(file.parent):
                package.add_file(file, 'media/DMD')
            elif "DMD Videos" in str(file.parent):
                package.add_file(file, 'media/DMDVideos')
            elif "Launch Audio" in str(file.parent):
                package.add_file(file, 'media/AudioLaunch')
            elif "Real DMD Color Videos" in str(file.parent):
                package.add_file(file, 'media/DMD')
            elif "Table Audio" in str(file.parent):
                package.add_file(file, 'media/Audio')
            elif "Table Videos" in str(file.parent):
                package.add_file(file, 'media/TableVideos')
            elif "Topper Images" in str(file.parent):
                package.add_file(file, 'media/Topper')
            elif "Topper Videos" in str(file.parent):
                package.add_file(file, 'media/TopperVideos')
            elif "Table Images" in str(file.parent):
                package.add_file(file, 'media/PlayField')
            elif "Wheel Images" in str(file.parent):
                package.add_file(file, 'media/Wheel')
            elif "Backglass Videos" in str(file.parent):
                package.add_file(file, 'media/Backglass')
            elif "Screen Grabs Backglass" in str(file.parent):
                package.add_file(file, 'media/Backglass')
            elif "Screen Grabs" in str(file.parent):
                package.add_file(file, 'media/ScreenGrabs')
                
            # --- NEW INTERCEPT ROUTINES FOR AUTOMATED ALTCOLOR PACKAGING ---
            elif "VPinMAME\\altcolor" in str(file):
                if os.path.isdir(file):
                    # Targets the root ROM directory structure directly
                    dest_path = os.path.join(package.directory, package.name, 'VPinMAME', 'altcolor', file.name)
                    os.makedirs(dest_path, exist_ok=True)
                    
                    # Mirror raw folder tree quietly to staging
                    for root, dirs, files in os.walk(file):
                        rel_p = os.path.relpath(root, start=str(file))
                        target_dir = os.path.normpath(os.path.join(dest_path, rel_p))
                        os.makedirs(target_dir, exist_ok=True)
                        for f in files:
                            shutil.copy2(os.path.join(root, f), os.path.join(target_dir, f))
                    self.logger.info(f"++ Raw altcolor pack folder mirrored safely to package workspace.")
                continue

            # --- NEW INTERCEPT ROUTINES FOR AUTOMATED ALTSOUND PACKAGING ---
            elif "VPinMAME\\altsound" in str(file):
                if os.path.isdir(file):
                    dest_path = os.path.join(package.directory, package.name, 'VPinMAME', 'altsound', file.name)
                    os.makedirs(dest_path, exist_ok=True)
                    
                    for root, dirs, files in os.walk(file):
                        rel_p = os.path.relpath(root, start=str(file))
                        target_dir = os.path.normpath(os.path.join(dest_path, rel_p))
                        os.makedirs(target_dir, exist_ok=True)
                        for f in files:
                            shutil.copy2(os.path.join(root, f), os.path.join(target_dir, f))
                    self.logger.info(f"++ Raw altsound pack folder mirrored safely to package workspace.")
                continue
                
            else:
                self.logger.error("New Case! [%s]" % file)
                break

    def deploy(self, package: Package) -> None:
        self.logger.info("* Deploy Pinball X")

        if not os.path.exists(self.pinballX_path):
            self.logger.warning('PinballX not found (%s)' % self.pinballX_path)
            return

        package_base_path = os.path.join(self.baseModel.tmp_path, package.name)
        if not os.path.exists(package_base_path):
            raise ValueError('Path not found (%s)' % package_base_path)

        media_mappings = [
            ("Flyers Back", "Media/Flyer Images/Back/"),
            ("Flyers Inside", "Media/Flyer Images/Inside1/"),
            ("Flyers Front", "Media/Flyer Images/Front/"),
            ("Instruction Cards", "Media/Instruction Cards/"),
            ("HighScores", "High Scores/Visual Pinball/"),
            ("Wheel", "Media/Visual Pinball/Wheel Images/"),
            ("Audio", "Media/Visual Pinball/Table Audio/"),
            ("AudioLaunch", "Media/Visual Pinball/Launch Audio/"),
            ("BackGlass", "Media/Visual Pinball/Backglass Images/"),
            ("DMD", "Media/Visual Pinball/DMD Images/"),
            ("DMDVideos", "Media/Visual Pinball/DMD Videos/"),
            ("PlayField", "Media/Visual Pinball/Table Images"),
            ("Topper", "Media/Visual Pinball/Topper Images"),
            ("TopperVideos", "Media/Visual Pinball/Topper Videos"),
            ("TableVideos", "Media/Visual Pinball/Table Videos"),
            ("ScreenGrabs", "Media/Visual Pinball/Screen Grabs"),
        ]

        for src_sub, dest_sub in media_mappings:
            src_path = os.path.join(package_base_path, "media", src_sub)
            if os.path.exists(src_path):
                dest_path = os.path.join(self.pinballX_path, dest_sub)
                copytree(self.logger, src_path, dest_path)

    def delete(self, table_name: str) -> None:
        if not os.path.exists(self.pinballX_path):
            self.logger.warning('PinballX not found (%s)' % self.pinballX_path)
            return

        self.logger.info("* Pinball X files")
        for file in Path(self.pinballX_path).glob('**/%s.*' % table_name):
            self.logger.info("- delete file %s" % file)
            os.remove(file)