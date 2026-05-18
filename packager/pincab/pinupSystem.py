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

        # --- FIXED CODE: COPIES RAW PUP PACK WITHOUT MANIFEST ERRORS ---
        try:
            import shutil
            
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
                        self.logger.info(f"++ Found active local PuP folder matching ROM: '{rom}'")
                        
                        destination_pup_dir = os.path.join(package.directory, package.name, 'media', 'PuP', rom)
                        
                        self.logger.info(f"+ Copying raw PuP folder contents quietly -> 'media/PuP/{rom}/'")
                        
                        if os.path.exists(destination_pup_dir):
                            shutil.rmtree(destination_pup_dir)
                        
                        # Mirror the loose folders directly into the zip staging zone
                        shutil.copytree(target_pup_folder, destination_pup_dir)
                        
                        self.logger.info(f"++ Raw PuP pack files mirrored safely to package staging workspace.")
                        
        except Exception as e:
            self.logger.error(f"Error copying local loose PuP folder assets: {e}")
    def deploy(self, package: Package, product: str) -> None:
        self.logger.info("* Deploy PinUp Media")

        if not os.path.exists(self.pinupSystem_path):
            self.logger.warning('PinupSystem not found(%s)' % self.pinupSystem_path)
            return

        if not Path(self.baseModel.tmp_path + "/" + package.name).exists():
            raise ValueError('Path not found (%s)' % self.baseModel.tmp_path + "/" + package.name)

        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/Audio",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/Audio')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/AudioLaunch",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/AudioLaunch')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/BackGlass",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/BackGlass')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/DMD",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/DMD')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/DMDVideos",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/DMDVideos')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/HighScores",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/HighScores')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/Instruction Cards",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/GameHelp')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/PlayField",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/PlayField')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/Topper",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/Topper')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/TopperVideos",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/Topper')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/Wheel",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/Wheel')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/ScreenGrabs",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/ScreenGrabs')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/TableVideos",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/TableVideos')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/Flyers Inside",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/GameInfo')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/Flyers Front",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/GameInfo')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/Flyers Back",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/GameInfo')
        copytree(self.logger,
                 self.baseModel.tmp_path + "/" + package.name + "/Media/Loading",
                 self.baseModel.pinupSystem_path + "/POPMedia/" + self.get_product_path(product) + '/Loading')

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
