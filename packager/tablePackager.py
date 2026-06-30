import logging
import os
import sys
import tempfile
import tkinter.messagebox

# Major.minor.fix; Minor number++ when package format/info change
version = '1.2.3'
package_version = '1.2.3'

from packager.view.mainWindow import *
from packager.model.baseModel import *
from packager.tools.logHandler import *


def main():
    # 1. Determine the Base Path for data (AppData vs Local)
    app_name = "TablePackager"
    if getattr(sys, 'frozen', False):
        # Use AppData/Roaming for installed applications
        data_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), app_name)
    else:
        # Use local folder for development
        data_dir = os.getcwd()

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # 2. Setup Logging in AppData
    log_path = os.path.join(data_dir, 'tablePackager.log')
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
        handlers=[
            logging.FileHandler(log_path, mode='w', encoding='utf-8'),
            logging.StreamHandler()
        ])
    logger = logging.getLogger(__name__)

    logHandler = QueueHandler()
    formatter = logging.Formatter('%(asctime)s: %(message)s')
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)

    logger.info(f'Starting. Data Directory: {data_dir}')

    # 3. Handle post_install logic safely
    # We check if post_install.py exists in the EXE directory (the bundle dir)
    bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
    post_install_script = os.path.join(bundle_dir, 'post_install.py')
    
    if os.path.exists(post_install_script):
        logger.info('Run post_install script')
        with open(post_install_script, 'r') as f:
            exec(f.read())
        os.remove(post_install_script)

    try:
        logger.info('Started')
        # 4. Pass the data_dir to your model
        # You will need to update BaseModel to accept this new argument
        base_model = BaseModel(logger, version, package_version, data_dir=data_dir)
        main_window = MainWindow(base_model, logHandler)
        base_model.installedTablesModel.update()
        base_model.packagedTablesModel.update()
        main_window.main_loop()
    except Exception as e:
        logger.error(e)
        tkinter.messagebox.showerror(title='Critical', message=str(e))

if __name__ == '__main__':
    main()

    def get_app_data_dir():
        # Defines the folder: 
        app_name = "TablePackager"
        if getattr(sys, 'frozen', False):
            # Use APPDATA for installed apps
            base_dir = os.environ.get('APPDATA')
        else:
            # Use local folder for development/testing
            base_dir = os.getcwd()
            
        data_dir = os.path.join(base_dir, app_name)
        
        # Create the directory if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        return data_dir