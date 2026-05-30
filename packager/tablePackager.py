import logging
import os
import sys
import tempfile
import tkinter.messagebox

# Major.minor.fix; Minor number++ when package format/info change
version = '1.2.0'
package_version = '1.2'

from packager.view.mainWindow import *
from packager.model.baseModel import *
from packager.tools.logHandler import *


# https://datastudio.google.com/reporting/13ua5g7jmoyHovP4hrqk48HBYGeQbpJ1Z/page/55yX

def main():
    # Ensure the working directory is set to the application directory
    # This handles both PyInstaller (_MEIPASS) and cx_Freeze/standard execution
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            os.chdir(sys._MEIPASS)
        else:
            os.chdir(os.path.dirname(sys.executable))
    # ----------------------------

    log_path = os.path.join(tempfile.gettempdir(), 'tablePackager.log')
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

    logger.info('Starting')
    # run once after installation
    if os.path.exists('post_install.py'):
        logger.info('Run post_install script')
        exec(open('post_install.py').read())
        os.remove('post_install.py')

    try:
        logger.info('Started')
        base_model = BaseModel(logger, version, package_version)
        main_window = MainWindow(base_model, logHandler)
        base_model.installedTablesModel.update()
        base_model.packagedTablesModel.update()
        main_window.main_loop()
    except Exception as e:
        logger.error(e)
        tkinter.messagebox.showerror(title='Critical', message=e)

if __name__ == '__main__':
    main()