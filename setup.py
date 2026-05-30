import sys
from cx_Freeze import setup, Executable
import os.path
import shutil

#https://fraoustin.fr/old/python_cx_freeze.html
#https://stackoverflow.com/questions/57184971/available-bdist-msi-options-when-creating-msi-with-cx-freeze

from packager.tablePackager import version
from packager.help.genHelp import *

# Use sys.base_prefix to find the root of the Python installation (especially for uv/venv)
PYTHON_INSTALL_DIR = sys.base_prefix
TCL_DIR = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tcl8.6')
TK_DIR = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tk8.6')

if os.path.exists(TCL_DIR):
    os.environ['TCL_LIBRARY'] = TCL_DIR
if os.path.exists(TK_DIR):
    os.environ['TK_LIBRARY'] = TK_DIR

shortcut_table = [
    ("DesktopShortcut",        # Shortcut
     "DesktopFolder",          # Directory_
     "Table Packager",           # Name
     "TARGETDIR",              # Component_
     "[TARGETDIR]tablePackager.exe",# Target
     None,                     # Arguments
     None,                     # Description
     None,                     # Hotkey
     None,                     # Icon
     None,                     # IconIndex
     None,                     # ShowCmd
     'TARGETDIR'               # WkDir
     )
    ]



# force clean
if os.path.exists('build'):
    shutil.rmtree('build', ignore_errors=True)

print('Generate packager/help/help.html')
gen_help('./README.md','packager/help',version)
gen_about('./about.md','packager/help',version)

# Helper to find DLLs (some installs use tk86t.dll, others tk86.dll)
def find_dll(name):
    for folder in ['DLLs', 'Library/bin']:
        path = os.path.join(PYTHON_INSTALL_DIR, folder, name)
        if os.path.exists(path):
            return path
    return None

tk_dll = find_dll('tk86t.dll') or find_dll('tk86.dll')
tcl_dll = find_dll('tcl86t.dll') or find_dll('tcl86.dll')

include_files = []
if os.path.exists('post_install.py'):
    include_files.append('post_install.py')
if tk_dll: include_files.append(tk_dll)
if tcl_dll: include_files.append(tcl_dll)

# Include application data files and preserve directory structure
include_files.append(('packager/images', 'packager/images'))
include_files.append(('packager/help', 'packager/help'))
include_files.append(('packager/database', 'packager/database'))

arch = "x86" if sys.maxsize <= 2**32 else "x64"

setup(name='tablePackager',
      version=version,
      description='Pincab Table Packager',
      options={ 'build_exe': { 'include_msvcr' : True,
                               'include_files': include_files},
                'bdist_msi': {'target_name': f'tablePackager-{version}-{arch}.msi',
                              'data': {'Shortcut': shortcut_table},
                              'install_icon' : 'packager/images/tablePackager_128x128.ico',
                              'upgrade_code': '{006d3301-d595-49e5-81d0-4a906aa48bb8}', # required for msi upgrade
                              'all_users': True,
                             },
      },
      url='https://github.com/Hagrou/tablePackager',
      license="GPL 3.0",
      executables=[ Executable(script='packager/tablePackager.py',
                               base='Win32GUI',
                               icon='packager/images/tablePackager_128x128.ico')]
)
