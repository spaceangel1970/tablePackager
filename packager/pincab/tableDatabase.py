import logging
import json
from io import StringIO
import csv
import os
import re
import threading
from packager.model.config import Config
from packager.tools.toolbox import *
from packager.pincab.site_cab import *
from packager.pincab.manufacturer import Manufacturer
from packager.pincab.statistics import Statistics
from packager.tools.exception import *

class TableDatabase:
    def __init__(self, logger, baseModel) -> None:
        self.__baseModel = baseModel
        self.__logger = logger
        # Fixed: Using raw strings (r'...') to eliminate the syntax warnings
        self.__re_extract_year = re.compile(r'.*, (?P<year>\d+)')
        self.__re_extract_trade_name = re.compile(r'.*\[Trade Name: (?P<name>.+)\]')
        self.__manufacturer_db = Manufacturer(baseModel.config)
        self.__dbPath = baseModel.config.get('db_path')
        self.__manufacturer_dbPath = baseModel.config.get('manufacturer_path')

        self.__lock = threading.Lock()
        self.__data = {}
        self.__statistics = Statistics()
        self.load()

    @property
    def logger(self):
        return self.__logger

    @property
    def baseModel(self):
        return self.__baseModel

    @property
    def data(self):
        return self.__data

    @property
    def statistics(self):
        return self.__statistics

    def clear(self):
        if os.path.exists(self.__dbPath) and os.path.isfile(self.__dbPath):
            os.remove(self.__dbPath)
        self.__data = {}

    def save(self, database: dict = None) -> None:
        pass

    def load(self) -> None:
        """
        Load VPS puplookup.csv database directly using exact PinUp Popper headers
        """
        self.logger.info("Reading VPS puplookup.csv Database")
        self.__data = {}

        if not os.path.exists(self.__dbPath):
            self.logger.warning(f"Database file missing at {self.__dbPath}")
            return

        try:
            with open(self.__dbPath, mode='r', encoding='utf-8-sig') as f:
                # Explicitly pass a standard comma delimiter to bypass Sniffer glitches
                reader = csv.DictReader(f, delimiter=',')
                
                for row in reader:
                    # Map the exact PinUp Popper column names from your log file
                    filename = row.get('GameFileName', '').strip()
                    
                    if filename:
                        # Strip out the trailing .vpx extension if it's baked into the CSV filename field
                        filename_clean = os.path.splitext(filename)[0]
                        
                        self.__data[filename_clean] = {
                            'Name': row.get('GameName', filename_clean),
                            'Table Name': row.get('GameName', filename_clean),
                            'Manufacturer': row.get('Manufact', 'Unknown'),
                            'Year': row.get('GameYear', 'Unknown'),
                            'Date Manufactured': row.get('GameYear', 'Unknown'),
                            'Theme': row.get('GameTheme', ''),
                            'IPDB Number': row.get('IPDBNum', -1),
                            'Urls': []
                        }
            self.logger.info(f"Successfully loaded {len(self.__data)} table indices from CSV configuration.")
        except Exception as e:
            self.logger.error(f"Failed to read puplookup.csv: {e}")

    def reload(self) -> None:
        self.load()

    def search(self, file_type: Pinfile_type, name: str = None, ipdb: str = None) -> dict:
        """
        Lookup game metadata using the clean table file stem
        """
        if not self.__data or not name:
            return None

        # Strip .vpx extension if the calling view includes it
        clean_name = os.path.splitext(name)[0]

        if clean_name in self.__data:
            return self.__data[clean_name]

        # Case-insensitive safety check fallback
        for key, value in self.__data.items():
            if key.upper() == clean_name.upper():
                return value
        return None

    def search_url(self, url: str) -> dict:
        return None

    def extract_pincab_info_from_title(self, pincab_title: str) -> (str, str, int):
        return Site_Cab.extract_pincab_info_from_title(pincab_title, self.__manufacturer_db)

    def extract_pincab_info_from_rom_filename(self, rom_filename: str) -> (str, str, int):
        return Site_Cab.extract_pincab_info_from_rom_filename(rom_filename)

    def search_pincab_urls_filter(self, pincab_name: str, urls: list) -> list:
        return Site_Cab.search_pincab_urls_filter(pincab_name, urls)