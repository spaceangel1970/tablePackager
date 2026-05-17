import os
import json


class Config:
    def __init__(self):
        # Explicit paths mapping directly to your active Documents project space
        self.__data = {
            'working_dir': 'C:/Users/DAVID/Documents/tablePackager',
            'visual_pinball_path': 'C:/vPinball/VisualPinball',
            'pinballX_path': 'C:/pinballX',
            'pinupSystem_path': 'C:/vPinball/PinUPSystem',
            'db_path': 'C:/vPinball/PinUPSystem/puplookup.csv',
            'manufacturer_path': 'C:/Users/DAVID/Documents/tablePackager/packager/database/manufacturer.json',
            'font': ('Helvetica', 10)
        }
        self.load()

    def get(self, var_name):
        if var_name == 'package_extension':
            return '.zip'
        return self.__data[var_name]

    def set(self, var_name, value):
        self.__data[var_name] = value

    def load(self):
        working_dir = self.get('working_dir')
        if not os.path.exists(working_dir):
            os.makedirs(working_dir, exist_ok=True)

        path = working_dir + '/config.json'
        if not os.path.exists(path):  # no config? write it with default values
            self.save()
            return
        try:
            with open(path) as data_file:
                loaded_data = json.load(data_file)
                for key, value in loaded_data.items():
                    self.__data[key] = value
        except Exception as e:
            print(f"Warning: Could not load config.json ({e}). Using default setup.")
            self.save()

    def save(self):
        try:
            with open(self.get('working_dir') + '/config.json', 'w') as outfile:
                json.dump(self.__data, outfile, indent=2)
        except IOError as e:
            raise Exception("Config write error %s" % str(e))