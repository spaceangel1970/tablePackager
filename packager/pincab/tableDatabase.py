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
import requests # Ensure this is at the top of your file

class TableDatabase:
    def __init__(self, logger, baseModel) -> None:
        self.__baseModel = baseModel
        self.__logger = logger
        
        # Regex patterns
        self.__re_extract_year = re.compile(r'.*, (?P<year>\d+)')
        self.__re_extract_trade_name = re.compile(r'.*\[Trade Name: (?P<name>.+)\]')
        
        self.__manufacturer_db = Manufacturer(baseModel.config)
        
        # --- FIXED PATHS ---
        # Instead of getting db_path from config (which points to Program Files), 
        # we construct the path using the new package_path property in AppData
        self.__dbPath = os.path.join(self.__baseModel.package_path, 'puplookup.csv')
        self.__manufacturer_dbPath = os.path.join(self.__baseModel.package_path, 'manufacturers.csv')

        self.__lock = threading.Lock()
        self.__data = {}
        self.__statistics = Statistics()
        
        # Ensure files exist before loading
        if not os.path.exists(self.__dbPath):
            # Create an empty file if it doesn't exist
            with open(self.__dbPath, 'w', encoding='utf-8') as f:
                pass
                
        self.load()

    def update_csv(self, data):
        """Helper to save the database safely to the AppData path"""
        with self.__lock:
            try:
                with open(self.__dbPath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(data)
                self.__logger.info(f"Database successfully updated at: {self.__dbPath}")
            except Exception as e:
                self.__logger.error(f"Error writing database to {self.__dbPath}: {e}")

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

    def _safe_int(self, value):
        """Safely converts value to int, returning 0 if conversion fails."""
        try:
            # If it's a string like "123", this works.
            # If it's a URL or empty, it will trigger the except block.
            return int(value)
        except (ValueError, TypeError):
            return 0

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
                reader = csv.DictReader(f)
                # Standardize headers to lowercase/stripped to handle CSV variants
                field_map = {k.strip().lower().replace(' ', ''): k for k in reader.fieldnames} if reader.fieldnames else {}

                def get_row_val(row_dict, key_name, default_val=''):
                    key_lower = key_name.lower().replace(' ', '')
                    actual_key = field_map.get(key_lower)
                    val = row_dict.get(actual_key) if actual_key else row_dict.get(key_name)
                    return val.strip() if val is not None else default_val

                for row in reader:
                    filename = get_row_val(row, 'GameFileName')
                    if not filename:
                        filename = get_row_val(row, 'filename')

                    if filename:
                        filename_clean = os.path.splitext(filename)[0]
                        self.__data[filename_clean] = {
                            'Table Name': get_row_val(row, 'GameName', filename_clean),
                            'Theme': get_row_val(row, 'GameTheme', 'Unknown'),
                            'Manufacturer': get_row_val(row, 'Manufact', 'Unknown'),
                            'Year': get_row_val(row, 'GameYear', 'Unknown'),
                            'Description(s)': get_row_val(row, 'GameTheme', 'No description available'),
                            'IPDB Number': self._safe_int(get_row_val(row, 'IPDBNum', 0)),
                            'Player(s)': get_row_val(row, 'NumPlayers', 'Unknown'),
                            'Type': get_row_val(row, 'GameType', 'Unknown'),
                            'Fun Rating': 'N/A',
                            'Notes': 'N/A',
                            'Design by': get_row_val(row, 'DesignedBy', 'Unknown'),
                            'Art by': get_row_val(row, 'Author', 'Unknown'),
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
    
    def update_all_pincab_file_from_list(self) -> None:
        """
        Downloads the latest puplookup.csv from VPS and refreshes local data.
        """
        url = "https://virtualpinballspreadsheet.github.io/vps-db/db/puplookup.csv"
        self.logger.info(f"Updating database from: {url}")
        
        try:
            # 1. Download the file silently
            response = requests.get(url, timeout=15)
            response.raise_for_status() # Check for HTTP errors
            
            # 2. Silently overwrite the local file
            with open(self.__dbPath, 'wb') as f:
                f.write(response.content)
            
            self.logger.info("Database file successfully updated.")
            
            # 3. Trigger the internal reload
            self.load()
            
        except Exception as e:
            self.logger.error(f"Failed to update database: {e}")
            # Optional: Fallback to existing data if download fails
            self.load()

    def search_url(self, url: str) -> dict:
        return None

    def extract_pincab_info_from_title(self, pincab_title: str) -> (str, str, int):
        return Site_Cab.extract_pincab_info_from_title(pincab_title, self.__manufacturer_db)

    def extract_pincab_info_from_rom_filename(self, rom_filename: str) -> (str, str, int):
        return Site_Cab.extract_pincab_info_from_rom_filename(rom_filename)

    def search_pincab_urls_filter(self, pincab_name: str, urls: list) -> list:
        return Site_Cab.search_pincab_urls_filter(pincab_name, urls)