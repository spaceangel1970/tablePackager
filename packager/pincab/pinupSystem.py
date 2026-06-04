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
        if product == 'future pinball':
            return 'Future Pinball'
        return 'Visual Pinball X'

    def extract_file(self, package: Package, product: str, media, dataPath, extension='', search_name=None) -> None:
        name_to_search = search_name if search_name else package.name

        # Ensure we search for the base name without extensions (fixes Wheel/media detection) (handle dot or no dot)
        if name_to_search.lower().endswith(('.vpx', '.vpt', '.fpt')):
            name_to_search = os.path.splitext(name_to_search)[0]
        elif name_to_search.lower().endswith(('vpx', 'vpt', 'fpt')):
            name_to_search = name_to_search[:-3]
        
        name_to_search = name_to_search.strip()

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

                        self.logger.info(f"+ Indexing raw PuP folder contents -> 'media/PuP/{rom}/'")
                        for file_path in Path(target_pup_folder).glob('**/*'):
                            if file_path.is_file():
                                rel_path = file_path.relative_to(Path(target_pup_folder))
                                # Use the standard manifest system to track files for UI visibility
                                package.add_file(file_path, 'media/PuP', dst_file=f"{rom}/{rel_path.as_posix()}")
                        self.logger.info(f"++ Raw PuP pack files indexed and mirrored safely.")
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
        media_mappings = [
            ("Audio", "Audio"),
            ("AudioLaunch", "AudioLaunch"),
            ("BackGlass", "BackGlass"),
            ("DMD", "DMD"),
            ("DMDVideos", "DMDVideos"),
            ("HighScores", "HighScores"),
            ("Instruction Cards", "GameHelp"),
            ("PlayField", "PlayField"),
            ("Topper", "Topper"),
            ("TopperVideos", "Topper"),
            ("Wheel", "Wheel"),
            ("ScreenGrabs", "ScreenGrabs"),
            ("TableVideos", "TableVideos"),
            ("Flyers Inside", "GameInfo"),
            ("Flyers Front", "GameInfo"),
            ("Flyers Back", "GameInfo"),
            ("Loading", "Loading")
        ]

        pop_media_base = os.path.join(self.pinupSystem_path, "POPMedia", self.get_product_path(product))

        for src_sub, dest_sub in media_mappings:
            src_path = os.path.join(package_base_path, "media", src_sub)
            if os.path.exists(src_path):
                dest_path = os.path.join(pop_media_base, dest_sub)
                copytree(self.logger, src_path, dest_path)

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