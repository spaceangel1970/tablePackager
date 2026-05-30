import os
import shutil
from pathlib import Path
from packager.tools.toolbox import *
from packager.model.package import Package


class FuturePinball:
    """Handler for Future Pinball table extraction, deployment, and deletion."""
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
    def future_pinball_path(self):
        """Returns the base path for Future Pinball from configuration."""
        try:
            return self.baseModel.config.get('future_pinball_path')
        except KeyError:
            return ''

    def extract(self, package: Package) -> None:
        """
        Extracts Future Pinball assets into the package.
        """
        self.logger.info("* Future Pinball files extraction")
        fp_path = self.future_pinball_path
        if not fp_path or not os.path.exists(fp_path):
            self.logger.warning('Future Pinball path not found or not configured')
            return

        # Tables location: Future Pinball typically stores tables in a 'Tables' subfolder
        tables_dir = Path(fp_path) / "Tables"
        table_file = tables_dir / f"{package.name}.fpt"

        if table_file.exists():
            self.logger.info(f"  + {table_file.name}")
            package.add_file(table_file, 'futurPinball/Tables')
        else:
            self.logger.debug(f"  - {package.name}.fpt not found in {tables_dir}")

    def deploy(self, package: Package) -> None:
        """
        Deploys Future Pinball assets from a package to the system.
        """
        self.logger.info("* Deploy Future Pinball files")
        if not self.future_pinball_path or not os.path.exists(self.future_pinball_path):
            self.logger.warning('Future Pinball path not found or not configured')
            return

        pass

    def delete(self, table_name: str) -> None:
        """
        Removes Future Pinball assets from the system for a given table.
        """
        self.logger.info("* Delete Future Pinball files")
        fp_path = self.future_pinball_path
        if not fp_path or not os.path.exists(fp_path):
            return

        table_file = Path(fp_path) / "Tables" / f"{table_name}.fpt"
        if table_file.exists():
            self.logger.info(f"- remove {table_file} file")
            os.remove(table_file)