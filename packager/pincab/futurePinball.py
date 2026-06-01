import os
import shutil
import re
import configparser
import tempfile
from pathlib import Path
from packager.tools.toolbox import *
from packager.model.package import Package

try:
    import olefile
except ImportError:
    olefile = None


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

    def is_pup_pack_empty(self, pup_path: str) -> bool:
        """Checks if a PUP pack folder is effectively empty or missing."""
        if not os.path.exists(pup_path):
            return True
        for root, dirs, files in os.walk(pup_path):
            if files: 
                return False
        return True

    def extract_pup_folder_name(self, fpt_file: Path) -> str:
        """
        Scans the Future Pinball (.fpt) binary/text content for the 
        uPPack_folder or PuPPack_folder variable definition in the script.
        Uses olefile to extract the script from the OLE stream for accuracy.
        """
        if not fpt_file.exists():
            return None

        # Try OLE extraction first (the standard way for Future Pinball .fpt files)
        if olefile:
            try:
                if olefile.isOleFile(str(fpt_file)):
                    with olefile.OleFileIO(str(fpt_file)) as ole:
                        # List all streams to find the script stream (can be under subfolders)
                        for stream in ole.listdir():
                            stream_path = "/".join(stream)
                            if "script" in stream_path.lower():
                                self.logger.info(f"    + Extracting script from OLE stream: {stream_path}")
                                try:
                                    script_data = ole.openstream(stream_path).read()
                                    # Future Pinball scripts are encoded in UTF-16LE
                                    content = script_data.decode('utf-16-le', errors='ignore')

                                    # Robust regex for uPPack_folder or PuPPack_folder (handles tabs and spaces)
                                    pattern = r"(?i)[uP]*PPack_folder\s*=\s*[\"']([^\"']+)[\"']"
                                    match = re.search(pattern, content)

                                    if match:
                                        folder_name = match.group(1).strip()
                                        self.logger.info(f"    > Found PUP folder in OLE script: {folder_name}")
                                        return folder_name
                                except Exception as e:
                                    self.logger.debug(f"    ! Failed to read OLE stream {stream_path}: {e}")
            except Exception as e:
                self.logger.debug(f"    ! OLE script extraction failed: {e}")
        else:
            self.logger.warning("    ! 'olefile' module not found. Run 'pip install olefile' for reliable script extraction.")

        try:
            with open(fpt_file, 'rb') as f:
                binary_content = f.read()
            
            self.logger.info(f"    + Scanning table script ({len(binary_content)} bytes): {fpt_file.name}")
            
            # Regex to find: uPPack_folder = "FolderName"
            # Handles variations like uPPack_folder or PuPPack_folder and optional whitespace/tabs
            pattern = r"(?i)[uP]*PPack_folder\s*=\s*[\"']([^\"']+)[\"']"

            # Attempt 1: Standard latin-1 (covers ASCII/UTF-8 embedded in binary)
            content = binary_content.decode('latin-1', errors='ignore')
            match = re.search(pattern, content)
            
            if not match:
                # Attempt 2: UTF-16LE (Future Pinball often stores script streams as Wide Characters)
                try:
                    content_utf16 = binary_content.decode('utf-16le', errors='ignore')
                    match = re.search(pattern, content_utf16)
                except Exception:
                    pass

            if not match and len(binary_content) > 1:
                # Attempt 3: UTF-16LE offset by 1 (binary streams aren't always 2-byte aligned)
                try:
                    content_utf16_off = binary_content[1:].decode('utf-16le', errors='ignore')
                    match = re.search(pattern, content_utf16_off)
                except Exception:
                    pass

            if match:
                folder_name = match.group(1).strip()
                self.logger.info(f"    > Found uPPack_folder in script: {folder_name}")
                return folder_name
        except Exception as e:
            self.logger.error(f"Failed to scan Future Pinball script for PUP folder: {e}")
            
        return None

    def extract(self, package: Package) -> None:
        """
        Extracts Future Pinball assets into the package.
        """
        self.logger.info("* Starting Future Pinball assets extraction")
        fp_path = self.future_pinball_path
        self.logger.info(f"  > Configured Future Pinball Path: {fp_path}")

        # Load override mapping from FP_mapping.ini
        mapping = {}
        mapping_file = Path("FP_mapping.ini")
        if mapping_file.exists():
            try:
                config = configparser.ConfigParser()
                config.read(mapping_file)
                # Flexible matching: apply mapping if section name is part of the package name
                for section in config.sections():
                    if section.lower() in package.name.lower():
                        mapping = config[section]
                        self.logger.info(f"  + Applied mapping section [{section}] to '{package.name}' from FP_mapping.ini")
                        break
            except Exception as e:
                self.logger.debug(f"  ! Failed to read FP_mapping.ini: {e}")

        if not fp_path or not os.path.exists(fp_path):
            self.logger.warning(f"  ! Future Pinball path not found or not configured: {fp_path}")
            return

        # Tables location: Future Pinball typically stores tables in a 'Tables' subfolder
        tables_dir = Path(fp_path) / "Tables"
        if 'TableFile' in mapping:
            table_filename = mapping['TableFile']
            self.logger.info(f"  + Table file identified via mapping: {table_filename}")
        else:
            table_filename = f"{package.name}.fpt"

        table_file = tables_dir / table_filename

        if table_file.exists():
            self.logger.info(f"  + Found Table: {table_file.name}")
            package.add_file(table_file, 'future pinball/Tables')

            # Extract BAM CFG file if it exists
            cfg_filename = table_file.stem + '.cfg'
            cfg_file = Path(fp_path) / "BAM" / "cfg" / cfg_filename
            if cfg_file.exists():
                self.logger.info(f"    + BAM configuration file found: {cfg_filename}")
                package.add_file(cfg_file, 'future pinball/BAM', dst_file=f'cfg/{cfg_filename}')
            else:
                self.logger.info(f"    - No BAM configuration file found for: {table_file.stem}")

            # Determine the correct PUP Pack folder
            pup_folder = mapping.get('PupPack')
            if pup_folder:
                self.logger.info(f"    + Using mapped PUP pack override: {pup_folder} (skipping script scan)")
            else:
                # Only scan the script if no mapping exists
                pup_folder = self.extract_pup_folder_name(table_file)
                if pup_folder:
                    self.logger.info(f"    + Script-defined PUP folder: {pup_folder}")

            if not pup_folder:
                pup_folder = package.name
                self.logger.info(f"    + No script folder found, defaulting to: {pup_folder}")
                
            # Resolve PinUpSystem path from model or config
            pinup_path = getattr(self.baseModel, 'pinupSystem_path', '') or self.baseModel.config.get('pinup_system_path', '')
            if pinup_path:
                self.logger.info(f"    > Resolved PinUpSystem path: {pinup_path}")

            # Check both Future Pinball local PUPVideos and the central PinUpSystem PUPVideos
            pup_locations = [
                Path(fp_path) / "PUPVideos" / pup_folder,
                Path(pinup_path) / "PUPVideos" / pup_folder
            ]

            for pup_path in [p for p in pup_locations if p]:
                self.logger.info(f"    > Checking: {pup_path}")
                if pup_path.exists() and pup_path.is_dir():
                    if not self.is_pup_pack_empty(str(pup_path)):
                        self.logger.info(f"    + Valid PUP Pack found! Archiving...")
                        for file_path in pup_path.glob('**/*'):
                            if file_path.is_file():
                                rel_path = file_path.relative_to(pup_path)
                                package.add_file(file_path, 'future pinball/PUPVideos', 
                                                 dst_file=f"{pup_folder}/" + str(rel_path).replace('\\', '/'))
                        break
                    else:
                        self.logger.info(f"    - Folder exists but is empty.")

            # --- SESSION LOG CAPTURE ---
            log_path = os.path.join(tempfile.gettempdir(), 'tablePackager.log')
            if os.path.exists(log_path):
                self.logger.info(f"* Bundling session log: {log_path}")
                package.add_file(log_path, 'future pinball/logs', dst_file='Log.txt')

        self.logger.info("--------------------------------------------------")

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