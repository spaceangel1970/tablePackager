import os
import shutil
from pathlib import Path
from packager.tools.toolbox import *
from packager.model.package import Package


class PinUpSystem:
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
    def pinupSystem_path(self):
        return self.__baseModel.pinupSystem_path

    def get_product_path(self, product: str) -> str:
        if product == 'visual pinball':
            return 'Visual Pinball X'
        return 'Visual Pinball X'

    def extract_file(self, package: Package, product: str, media, dataPath, extension='', search_name=None) -> None:
        name_to_search = search_name if search_name else package.name
        for file in Path(
                self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/' + media)\
                .glob('**/%s%s*' % (name_to_search, extension)):
            package.add_file(file, dataPath)  # Add vpx file

    def extract(self, package: Package, product: str, search_name: str = None) -> None:
        if not os.path.exists(self.pinupSystem_path):
            self.logger.warning('PinupSystem not found(%s)' % self.pinupSystem_path)
            return

        self.logger.info("* PinupSystem files")
        self.extract_file(package, product, 'Audio', 'media/Audio', search_name=search_name)
        self.extract_file(package, product, 'AudioLaunch', 'media/AudioLaunch', search_name=search_name)
        self.extract_file(package, product, 'BackGlass', 'media/Backglass', search_name=search_name)
        self.extract_file(package, product, 'DMD', 'media/DMD', search_name=search_name)
        self.extract_file(package, product, 'DMDVideos', 'media/DMDVideos', search_name=search_name)
        self.extract_file(package, product, 'HighScores', 'media/HighScores', search_name=search_name)
        self.extract_file(package, product, 'GameHelp', 'media/Instruction Cards', search_name=search_name)
        self.extract_file(package, product, 'PlayField', 'media/PlayField', search_name=search_name)
        self.extract_file(package, product, 'Topper', 'media/Topper', search_name=search_name)
        self.extract_file(package, product, 'Wheel', 'media/Wheel', search_name=search_name)
        self.extract_file(package, product, 'ScreenGrabs', 'media/ScreenGrabs', search_name=search_name)
        self.extract_file(package, product, 'TableVideos', 'media/TableVideos', search_name=search_name)

        self.extract_file(package, product, 'GameInfo', 'media/Flyers Front', search_name=search_name) # TOTO:check
       # self.extract_file(package, product, 'GameInfo', 'media/Flyers Back', extension='.back', search_name=search_name)
        self.extract_file(package, product, 'Loading', 'media/Loading', search_name=search_name)

        # --- RAW PUP PACK EXTRACTION WITHOUT MANIFEST ERRORS ---
        try:
            rom_field = package.get_field('visual pinball/info/romName')
            rom_names = []
            
            if rom_field:
                if isinstance(rom_field, list):
                    rom_names = [str(r).strip() for r in rom_field if r]
                else:
                    clean_rom = str(rom_field).replace('[', '').replace(']', '').replace("'", "").replace('"', '')
                    rom_names = [r.strip() for r in clean_rom.split(',') if r.strip()]
            
            pup_videos_base = os.path.join(self.pinupSystem_path, 'PUPVideos')
            
            if os.path.exists(pup_videos_base) and rom_names:
                for rom in rom_names:
                    if rom.lower() == "yourgame":
                        continue
                        
                    target_pup_folder = os.path.join(pup_videos_base, rom)
                    if os.path.exists(target_pup_folder) and os.path.isdir(target_pup_folder):
                        # Skip if the folder contains no actual media files
                        has_files = False
                        for _root, _dirs, files in os.walk(target_pup_folder):
                            if files:
                                has_files = True
                                break

                        if not has_files:
                            self.logger.info(f"-- Skipping local PuP folder for ROM '{rom}' (empty)")
                            continue

                        self.logger.info(f"++ Found active local PuP folder matching ROM: '{rom}'")

                        destination_pup_dir = os.path.join(package.directory, package.name, 'media', 'PuP', rom)

                        self.logger.info(f"+ Copying raw PuP folder contents quietly -> 'media/PuP/{rom}/'")

                        if os.path.exists(destination_pup_dir):
                            shutil.rmtree(destination_pup_dir)

                        shutil.copytree(target_pup_folder, destination_pup_dir)
                        self.logger.info(f"++ Raw PuP pack files mirrored safely to package staging workspace.")
                        
        except Exception as e:
            self.logger.error(f"Error copying local loose PuP folder assets: {e}")

    def deploy(self, package: Package, product: str) -> None:
        self.logger.info("* Deploy PinUp Media")

        if not os.path.exists(self.pinupSystem_path):
            self.logger.warning('PinupSystem not found(%s)' % self.pinupSystem_path)
            return

        package_base_path = os.path.normpath(os.path.join(self.baseModel.tmp_path, package.name))
        if not os.path.exists(package_base_path):
            raise ValueError('Path not found (%s)' % package_base_path)

        # 1. --- STANDARD POPMEDIA FRONTEND ASSETS ---
        copytree(self.logger, package_base_path + "/media/Audio", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/Audio')
        copytree(self.logger, package_base_path + "/media/AudioLaunch", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/AudioLaunch')
        copytree(self.logger, package_base_path + "/media/BackGlass", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/BackGlass')
        copytree(self.logger, package_base_path + "/media/DMD", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/DMD')
        copytree(self.logger, package_base_path + "/media/DMDVideos", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/DMDVideos')
        copytree(self.logger, package_base_path + "/media/HighScores", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/HighScores')
        copytree(self.logger, package_base_path + "/media/Instruction Cards", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/GameHelp')
        copytree(self.logger, package_base_path + "/media/PlayField", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/PlayField')
        copytree(self.logger, package_base_path + "/media/Topper", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/Topper')
        copytree(self.logger, package_base_path + "/media/TopperVideos", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/Topper')
        copytree(self.logger, package_base_path + "/media/Wheel", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/Wheel')
        copytree(self.logger, package_base_path + "/media/ScreenGrabs", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/ScreenGrabs')
        copytree(self.logger, package_base_path + "/media/TableVideos", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/TableVideos')
        copytree(self.logger, package_base_path + "/media/Flyers Inside", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/GameInfo')
        copytree(self.logger, package_base_path + "/media/Flyers Front", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/GameInfo')
        copytree(self.logger, package_base_path + "/media/Flyers Back", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/GameInfo')
        copytree(self.logger, package_base_path + "/media/Loading", self.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/Loading')

        # 2. --- FIXED CODE: SAFE SURGICAL MERGE FOR PUP VIDEOS PACKS ---
        pup_stage_dir = os.path.join(package_base_path, "media", "PuP")
        if os.path.exists(pup_stage_dir) and os.path.isdir(pup_stage_dir):
            self.logger.info("* Processing active PuP-Pack video directory merge allocations...")
            global_pup_videos_base = os.path.normpath(os.path.join(self.pinupSystem_path, 'PUPVideos'))

            for rom_folder in os.listdir(pup_stage_dir):
                source_rom_path = os.path.join(pup_stage_dir, rom_folder)
                target_rom_path = os.path.join(global_pup_videos_base, rom_folder)

                if os.path.isdir(source_rom_path):
                    os.makedirs(target_rom_path, exist_ok=True)
                    self.logger.info(f"++ Merging structural pack layout files into destination: PUPVideos/{rom_folder}")

                    # Walk through the archive pack and selectively drop/merge files natively
                    for root, dirs, files in os.walk(source_rom_path):
                        rel_path = os.path.relpath(root, start=source_rom_path)
                        dest_sub_dir = os.path.normpath(os.path.join(target_rom_path, rel_path))
                        os.makedirs(dest_sub_dir, exist_ok=True)

                        for f in files:
                            s_file = os.path.join(root, f)
                            d_file = os.path.join(dest_sub_dir, f)

                            # CRITICAL MERGE RULES:
                            # 1. If the file doesn't exist on the target machine, copy it.
                            # 2. Always overwrite layout files ('pupimages.txt', 'playlist.pup') so the new layout applies.
                            # 3. Overwrite media files if the incoming asset file is newer.
                            if (not os.path.exists(d_file) or 
                                    f.lower() in ['pupimages.txt', 'playlist.pup', 'pup_screen_options.bat'] or 
                                    os.path.getmtime(s_file) > os.path.getmtime(d_file)):
                                try:
                                    shutil.copy2(s_file, d_file)
                                except Exception as file_err:
                                    self.logger.error(f"   [PuP Merge Warning] Skip locked/unavailable file: {f}. Error: {file_err}")

    def delete(self, table_name: str, product: str):
        self.logger.info("* Delete PinUp Media")

        if not os.path.exists(self.pinupSystem_path):
            self.logger.warning('PinupSystem not found(%s)' % self.pinupSystem_path)
            return
        pop_media = self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product)
        if not Path(pop_media).exists():
            raise ValueError('Path not found (%s)' % pop_media + "/" + table_name)

        for file in Path(pop_media).glob('**/%s.*' % table_name):
            self.logger.info("- delete file %s" % file)
            os.remove(file)