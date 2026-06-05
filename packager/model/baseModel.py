import sys
import os
import csv
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os
from packager.model.config import *
from packager.model.installedTablesModel import *
from packager.pincab.visualPinball import *
from packager.pincab.vpinMame import VPinMame
from packager.pincab.pinballX import PinballX
from packager.pincab.pinupSystem import PinUpSystem
from packager.pincab.ultraDMD import UltraDMD
from packager.pincab.FlexDMD import FlexDMD
from packager.pincab.tableDatabase import TableDatabase
from packager.model.packageEditorModel import PackageEditorModel
from packager.model.packagedTablesModel import *
from packager.model.search_model import *
from packager.pincab.pupScanner import PupScanner
from packager.pincab.futurePinball import FuturePinball

class BaseModel:
    # Update the constructor to accept the passed data_dir
    def __init__(self, logger: logging, version: str, package_version: str, data_dir: str) -> None:
        self.__logger = logger
        
        # Determine the base directory logic
        if Path(os.getcwd()).name == 'packager':  # running from IDE
            self.__base_dir = ''
        else:  # running from exe
            self.__base_dir = 'lib/packager/'

        self.__config = Config()
        self.__version = version
        self.__package_version = package_version
        
        # --- PATH UPDATES ---
        # Instead of using self.__config.get('working_dir'), which likely points to Program Files,
        # we now join the paths with your new data_dir (the AppData path)
        self.__tmp_path = os.path.join(data_dir, 'tmp')
        self.__package_path = os.path.join(data_dir, 'packages')
        self.__installed_path = os.path.join(data_dir, 'installed')
        
        # Ensure these directories exist in AppData
        for path in [self.__tmp_path, self.__package_path, self.__installed_path]:
            os.makedirs(path, exist_ok=True)
            
        # ... (rest of your initializations)
        self.__installedTablesModel = InstalledTablesModel(self)
        self.__packagedTablesModel = PackagedTablesModel(self)
        self.__packageEditorModel = PackageEditorModel(self)
        self.__searchModel = Search_Model(self)
        self.__visualPinball = VisualPinball(self.logger, self)
        self.__pinupSystem = PinUpSystem(self.logger, self)
        self.__vpinMame = VPinMame(self.logger, self)
        self.__pinballX = PinballX(self.logger, self)
        self.__ultraDMD = UltraDMD(self.logger, self)
        self.__flexDMD = FlexDMD(self.logger, self)
        self.__futurePinball = FuturePinball(self.logger, self)
        self.__database = TableDatabase(self.logger, self)
        self.__pupScanner = PupScanner(self.logger, self)

    @property
    def config(self):
        return self.__config

    @property
    def base_dir(self) -> str:
        return self.__base_dir

    @property
    def version(self) -> str:
        return self.__version

    @property
    def package_version(self) -> str:
        return self.__package_version

    @property
    def search_model(self):
        return self.__searchModel

    @property
    def config(self) -> Config:
        return self.__config

    @property
    def logger(self) -> logging:
        return self.__logger

    @property
    def btEditImage(self):
        return self.__btEditImage

    @property
    def installedTablesModel(self):
        return self.__installedTablesModel

    @property
    def packagedTablesModel(self):
        return self.__packagedTablesModel

    @property
    def packageEditorModel(self):
        return self.__packageEditorModel

    @property
    def visual_pinball_path(self):
        return self.__config.get('visual_pinball_path')

    @property
    def pinballX_path(self):
        return self.__config.get('pinballX_path')

    @property
    def pinupSystem_path(self):
        return self.__config.get('pinupSystem_path')

    @property
    def tmp_path(self) -> str:
        return self.__tmp_path

    @property
    def package_path(self):
        if not os.path.exists(self.__package_path):
            os.makedirs(self.__package_path, exist_ok=True)
        return self.__package_path

    @property
    def installed_path(self):
        if not os.path.exists(self.__installed_path):
            os.makedirs(self.__installed_path, exist_ok=True)
        return self.__installed_path

    @property
    def package_extension(self):
        return self.__config.get('package_extension')

    @property
    def visualPinball(self):
        return self.__visualPinball

    @property
    def futurePinball(self):
        return self.__futurePinball

    @property
    def vpinMame(self):
        return self.__vpinMame

    @property
    def pinballX(self):
        return self.__pinballX

    @property
    def pinupSystem(self):
        return self.__pinupSystem

    @property
    def ultraDMD(self):
        return self.__ultraDMD

    @property
    def flexDMD(self):
        return self.__flexDMD

    @property
    def database(self):
        return self.__database

    @property
    def pupScanner(self):
        return self.__pupScanner

    def bundle_pup_for_table(self, table_name: str, package_obj) -> list:
        """Find PuP packs related to a table, create archives and add them to the given package.

        - `table_name`: name of the table to search for
        - `package_obj`: instance of `Package` to which the created pup archive(s) will be added

        Returns list of filenames added to the package.
        """
        self.logger.info('Scanning PuP packs for table: %s' % table_name)
        added = []
        matches = self.pupScanner.find_for_table(table_name)
        if not matches:
            self.logger.info('No PuP packs found for table %s' % table_name)
            return added

        # Ensure package has a PuP directory
        pup_dir = os.path.join(package_obj.directory, package_obj.name, 'media', 'PuP')
        os.makedirs(pup_dir, exist_ok=True)

        for match in matches:
            src_archive = self.pupScanner.create_pup_archive(match)
            if src_archive == '':
                continue
            dst_name = os.path.basename(src_archive)
            try:
                package_obj.add_file(src_archive, 'media/PuP')
                added.append('media/PuP/' + dst_name)
            except Exception as e:
                self.logger.error('Error adding PuP pack to package: %s' % e)

        if added:
            package_obj.save()
        return added
