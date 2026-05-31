import os
import re
import configparser
from pathlib import Path
from packager.model.package import Package

try:
    import olefile
except ImportError:
    olefile = None

class FuturePinball:
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
        """Returns the base path for Future Pinball from the base model."""
        return getattr(self.baseModel, 'future_pinball_path', '')

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
        uPPack_folder variable definition in the script.
        """
        if not fpt_file.exists():
            return None
            
        self.logger.info(f"    + Scanning table script: {fpt_file.name}")

        # Try OLE extraction first (standard for FP .fpt files)
        if olefile:
            try:
                if olefile.isOleFile(str(fpt_file)):
                    with olefile.OleFileIO(str(fpt_file)) as ole:
                        # Search all internal streams for the table script
                        for entry in ole.listdir():
                            path = "/".join(entry)
                            if "script" in path.lower():
                                self.logger.info(f"    + Scanning OLE stream: {path}")
                                try:
                                    with ole.openstream(path) as s:
                                        script_data = s.read()
                                        # FP scripts are almost always UTF-16LE encoded
                                        content = script_data.decode('utf-16-le', errors='ignore')
                                        
                                        # Robust regex for uPPack_folder or PuPPack_folder
                                        pattern = r"(?i)[uP]+ack_folder\s*=\s*[\"']([^\"']+)[\"']"
                                        match = re.search(pattern, content)
                                        if match:
                                            folder_name = match.group(1).strip()
                                            self.logger.info(f"    > Found PUP folder in script: {folder_name}")
                                            return folder_name
                                except Exception as stream_err:
                                    self.logger.debug(f"    ! Error reading OLE stream {path}: {stream_err}")
            except Exception as e:
                self.logger.debug(f"    ! OLE extraction failed: {e}")
        else:
            self.logger.warning("    ! 'olefile' module not found. Falling back to binary scan.")

        # Fallback binary scanner (e.g. if OLE is non-standard or missing)
        try:
            with open(fpt_file, 'rb') as f:
                binary_content = f.read()
            
            self.logger.info(f"    + Scanning table script ({len(binary_content)} bytes): {fpt_file.name}")
            pattern = r"(?i)[uP]+ack_folder\s*=\s*[\"']([^\"']+)[\"']"
            
            # Try Latin-1
            match = re.search(pattern, binary_content.decode('latin-1', errors='ignore'))
            
            if not match:
                # Try UTF-16LE (Modern FP)
                match = re.search(pattern, binary_content.decode('utf-16le', errors='ignore'))

            if not match and len(binary_content) > 1:
                # Try UTF-16LE with 1-byte offset
                match = re.search(pattern, binary_content[1:].decode('utf-16le', errors='ignore'))

            if match:
                folder_name = match.group(1).strip()
                self.logger.info(f"    > Found PUP folder in binary scan: {folder_name}")
                return folder_name
        except Exception as e:
            self.logger.error(f"    ! Binary scan failed: {e}")
            
        return None

    def extract(self, package: Package) -> None:
        """Extracts Future Pinball files and associated PUP packs."""
        if not os.path.exists(self.future_pinball_path):
            return

        # Only execute logic if 'future pinball' is checked/present in the manifest
        if not (hasattr(package, 'manifest') and 
                hasattr(package.manifest, 'content') and 
                "future pinball" in package.manifest.content):
            return

        # Load override mapping from FP_mapping.ini if present
        mapping = {}
        mapping_file = Path("FP_mapping.ini")
        if mapping_file.exists():
            try:
                config = configparser.ConfigParser()
                config.read(mapping_file)
                # Flexible matching: check if any section name is contained within the package name
                for section in config.sections():
                    if section.lower() in package.name.lower():
                        mapping = config[section]
                        break
            except Exception:
                pass

        self.logger.info("* Starting Future Pinball assets extraction")
        if 'TableFile' in mapping:
            table_filename = mapping['TableFile']
            self.logger.info(f"  + Table file identified via mapping: {table_filename}")
        else:
            table_filename = package.name + '.fpt'

        fpt_file = Path(os.path.join(self.future_pinball_path, 'Tables', table_filename))
        
        if not fpt_file.exists():
            self.logger.warning(f"! Future Pinball table file not found: {fpt_file.name}")
            return

        package.add_file(fpt_file, 'future pinball/Tables')

        # Determine the correct PUP Pack folder
        pup_folder = mapping.get('PupPack')
        if pup_folder:
            self.logger.info(f"  + Using mapped PUP pack override: {pup_folder} (skipping script scan)")
        else:
            # Only scan the script if no mapping exists
            pup_folder = self.extract_pup_folder_name(fpt_file)
            if pup_folder:
                self.logger.info(f"  + Script-defined PUP folder: {pup_folder}")

        if not pup_folder:
            self.logger.info(f"  - No mapping or script folder found, falling back to: {package.name}")
            pup_folder = package.name
            
        # Resolve the PinUpSystem path to check for central PUP packs
        pinup_path = getattr(self.baseModel, 'pinupSystem_path', '') or self.baseModel.config.get('pinup_system_path', '')

        # Search priority: 1. Future Pinball/PUPVideos  2. PinUpSystem/PUPVideos
        potential_paths = [
            os.path.join(self.future_pinball_path, "PUPVideos", pup_folder),
            os.path.join(pinup_path, "PUPVideos", pup_folder) if pinup_path else None
        ]

        for pup_path in [p for p in potential_paths if p]:
            if not self.is_pup_pack_empty(pup_path):
                self.logger.info(f"+ Found PUP pack at: {pup_path}")
                for file_path in Path(pup_path).glob('**/*'):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(Path(pup_path))
                        # Use the base category as the manifest key to ensure it appears in the Preview UI
                        # Prepend the pup_folder to the destination file path to preserve the directory structure
                        package.add_file(file_path, "future pinball/PUPVideos", 
                                         dst_file=f"{pup_folder}/" + str(rel_path).replace('\\', '/'))
                return

        self.logger.info(f"- No PUP pack found for folder: {pup_folder}")