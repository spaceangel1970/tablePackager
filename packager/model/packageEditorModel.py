import logging
import tkinter

from packager.model.baseModel import *
from packager.model.package import Package
from packager.tools.observer import Observable
from packager.tools.toolbox import *


class PackageEditorModel(Observable):
    def __init__(self, baseModel: object):
        super().__init__()
        self.__baseModel = baseModel
        self.__currentPackage = {}
        self.__package = None

    @property
    def baseModel(self) -> object:
        return self.__baseModel

    @property
    def logger(self):
        return self.__baseModel.logger

    @property
    def currentPackage(self):
        return self.__currentPackage

    @property
    def package(self) -> Package:
        return self.__package

    @currentPackage.setter
    def currentPackage(self, package):
        self.__currentPackage = package

    def edit_package(self, package):
        self.currentPackage = package
        self.notify_all(self, events=['<<DISABLE_ALL>>', '<<BEGIN_ACTION>>'])  # update listeners
        unpack_thread = AsynRun(self.edit_package_begin, self.edit_package_end)
        unpack_thread.start()

    def edit_package_begin(self, context=None):
        self.logger.info("--[Edit Package '%s']------------------" % (self.currentPackage['name']))
        try:
            self.__package = Package(self.baseModel, self.currentPackage['name'])
            self.package.unpack()
            self.package.open(self.baseModel.tmp_path)
        except Exception as e:
            tkinter.messagebox.showerror('Edit Package', str(e))
            return False
        return True

    def edit_package_end(self, context=None, success=True):
        def dispatch_ui():
            if success:
                self.logger.info("* Unpack Done")
                self.notify_all(self, events=['<<END_ACTION>>', '<<VIEW EDITOR>>'])  # update listeners
            else:
                self.logger.error("* Unpack failed")
                self.notify_all(self, events=['<<END_ACTION>>'])  # update listeners
        tkinter._default_root.after_idle(dispatch_ui)

    def new_package(self, name='New_Table_Package'):
        self.currentPackage = {'name': name}
        self.logger.info("--[New Package '%s']------------------" % (name))
        self.notify_all(self, events=['<<DISABLE_ALL>>', '<<BEGIN_ACTION>>'])  # update listeners
        self.__package = Package(self.baseModel, name)
        self.package.new(self.baseModel.tmp_path)
        self.notify_all(self, events=['<<END_ACTION>>', '<<VIEW EDITOR>>'])  # update listeners

    def save_package(self, info):
        self.logger.info("--[Save Package]-----------------------")
        self.notify_all(self, events=['<<BEGIN_ACTION>>', '<<HIDE EDITOR>>'])  # update listeners
        pack_thread = AsynRun(self.pack_package_begin, self.pack_package_end, context=info)
        pack_thread.start()

    def pack_package_begin(self, context=None):
        for key, val in context.items():
            self.package.set_field(key, val)

        # --- SESSION LOG CAPTURE ---
        # Ensure manual builds and edits also include the process log for debugging
        log_path = self.baseModel.log_path
        if os.path.exists(log_path):
            self.logger.info("* Capturing session log snapshot")
            # Flush log handlers to ensure all entries are committed to disk
            for handler in logging.root.handlers:
                if hasattr(handler, 'flush'): handler.flush()
            
            snap_path = os.path.join(self.baseModel.tmp_path, 'Log_Snapshot.txt')
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f_in:
                    log_data = f_in.read(10 * 1024 * 1024) # Limit snapshot to 10MB
                with open(snap_path, 'w', encoding='utf-8') as f_out:
                    f_out.write(log_data)
                
                # Determine log category based on package content
                log_dst = 'visual pinball/logs'
                if self.package.get_field('future pinball/Tables'):
                    log_dst = 'future pinball/logs'
                self.package.add_file(snap_path, log_dst, dst_file='Log.txt')
            except Exception as e:
                self.logger.warning(f"Could not capture log snapshot: {e}")

        self.package.save()
        self.package.pack()

        setReadWriteFile(self.baseModel.package_path + '/' + self.package.name + self.baseModel.package_extension)
        shutil.copy(self.baseModel.tmp_path + '/' + self.package.name + self.baseModel.package_extension,
                    self.baseModel.package_path)
        if self.package.get_field('info/protected') == 'True':
            self.logger.warning("Protect package with Read Only file status")
            setReadOnlyFile(self.baseModel.package_path + '/' + self.package.name + self.baseModel.package_extension)
        clean_dir(self.baseModel.tmp_path)
        return True

    def pack_package_end(self, context=None, success=True):
        self.logger.info("--[Edition '%s' Done]------------------" % (self.package.name))
        self.notify_all(self, events=['<<END_ACTION>>', '<<PACKAGE UNSELECTED>>', '<<ENABLE_ALL>>'])  # update listeners
        self.baseModel.packagedTablesModel.update()

    def rename_package(self, new_package_name):
        self.logger.info("--[Rename Package to '%s']----------" % new_package_name)
        self.notify_all(self, events=['<<DISABLE_ALL>>'])  # update listeners
        rename_thread = AsynRun(self.rename_package_begin, self.rename_package_end,
                                context={'newPackageName': new_package_name})
        rename_thread.start()

    def rename_package_begin(self, context=None):
        try:
            self.package.rename_package(context['newPackageName'])
            return True
        except Exception as e:
            tkinter.messagebox.showerror('rename package Error', str(e))
            return False

    def rename_package_end(self, context=None, success=True):
        def dispatch_ui():
            if success:
                self.logger.info("--[Rename '%s' Done]------------------" % (self.package.name))
            else:
                self.logger.error("--[Rename '%s' Failed]------------------" % (self.package.name))
            self.notify_all(self, events=['<<UPDATE_EDITOR>>', '<<ENABLE_ALL>>'])  # update listeners
            self.baseModel.packagedTablesModel.update()
        tkinter._default_root.after_idle(dispatch_ui)

    def cancel_edition(self):
        if not self.__currentPackage:  # empty selection
            raise ValueError('No selected package')
        self.logger.info("--[Edition '%s' Canceled]------------------" % (self.package.name))
        clean_dir(self.baseModel.tmp_path)
        self.notify_all(self, events=['<<END_ACTION>>', '<<PACKAGE UNSELECTED>>', '<<HIDE EDITOR>>',
                                      '<<ENABLE_ALL>>'])  # update listeners

    def update_package(self, selection=None):
        # Optimization: Do NOT call self.package.update() here.
        # Reloading from disk overwrites in-memory manifest changes that haven't been saved yet.
        self.notify_all(self, events=['<<UPDATE_EDITOR>>'], selection_set=selection)  # update listeners

    def add_ultradmd(self, viewer, dataPath, src_dir):
        self.logger.info("* UltraDMD files")

        ultra_dmd_dir = str(Path(src_dir).name)
        self.package.set_field('visual pinball/info/ultraDMD', ultra_dmd_dir)
        for file in Path(src_dir).glob('**/*'):
            if file.is_file():
                rel_path = file.relative_to(src_dir)
                dst_field = f"UltraDMD/{ultra_dmd_dir}"
                if str(rel_path.parent) != '.':
                    parent_path = str(rel_path.parent).replace('\\', '/')
                    dst_field += f"/{parent_path}"
                self.package.add_file(str(file), dst_field)
        self.update_package()

    def add_flexdmd(self, viewer, dataPath, src_dir):
        self.logger.info("* FlexDMD files")

        flex_dmd_dir = str(Path(src_dir).name)
        self.package.set_field('visual pinball/info/flexDMD', flex_dmd_dir)
        for file in Path(src_dir).glob('**/*'):
            if file.is_file():
                rel_path = file.relative_to(src_dir)
                dst_field = f"FlexDMD/{flex_dmd_dir}"
                if str(rel_path.parent) != '.':
                    parent_path = str(rel_path.parent).replace('\\', '/')
                    dst_field += f"/{parent_path}"
                self.package.add_file(str(file), dst_field)
        self.update_package()

    def add_music_folder(self, viewer, dataPath, src_dir):
        self.logger.info("* Music files")

        music_folder_name = str(Path(src_dir).name)
        # No specific manifest field to set for the music folder itself,
        # as music files are typically listed directly or within subfolders.
        for file in Path(src_dir).glob('**/*'):
            if file.is_file():
                rel_path = file.relative_to(src_dir)
                # dst_field is the category path (e.g., 'visual pinball/Music')
                # If the user selected a folder named 'Music', avoid redundant nesting (Music/Music)
                if music_folder_name.lower() == 'music':
                    final_dst = rel_path.as_posix()
                else:
                    final_dst = f"{music_folder_name}/{rel_path.as_posix()}"
                
                self.package.add_file(str(file), dataPath, dst_file=final_dst)
        self.update_package()

    def add_pup_pack_folder(self, viewer, dataPath, src_dir):
        self.logger.info("* PuP Pack files")

        pup_folder_name = str(Path(src_dir).name)
        # You might want to set a manifest field here if you need to track the main PUP folder name
        # e.g., self.package.set_field('media/PuP/main_folder', pup_folder_name)
        for file in Path(src_dir).glob('**/*'):
            if file.is_file():
                rel_path = file.relative_to(src_dir)
                # If the folder name matches generic PuP container keywords, avoid redundant nesting inside media/PuP
                if pup_folder_name.lower() in ['pup', 'pup pack', 'pupvideos']:
                    final_dst = rel_path.as_posix()
                else:
                    final_dst = f"{pup_folder_name}/{rel_path.as_posix()}"
                
                self.package.add_file(str(file), dataPath, dst_file=final_dst)
        self.update_package()

    def scan_pup_for_table(self):
        table_name = self.package.get_field('info/table name')
        if not table_name:
            table_name = self.package.name

        self.logger.info('Starting PuP scan for package table: %s' % table_name)
        added = self.baseModel.bundle_pup_for_table(table_name, self.package)
        self.update_package()
        return added

    def add_file(self, viewer, data_path, srcFile, required_name):
        rename_it = False
        try:
            filename = Path(srcFile).name
            target_file = filename

            # Music, FlexDMD, UltraDMD, and PuP assets must keep their original names for script compatibility.
            # Other POPMedia assets (media/ excluding PuP) must always be renamed to match the package name
            # for proper front-end linking.
            if any(k in data_path for k in ['Music', 'FlexDMD', 'UltraDMD', 'PuP']):
                rename_it = False
            else:
                if type(required_name) is list:
                    if len(required_name) == 0:
                        tkinter.messagebox.showwarning("Renaming File",
                                                       "No information found for filename",
                                                       parent=viewer)
                    else:
                        rename_it = [name for name in required_name if name.upper() == Path(filename).stem.upper()] == []
                        required_name = required_name[0]
                else:
                    rename_it = Path(filename).stem.upper() != required_name.upper()

            if rename_it:
                new_name = build_target_filename(filename, required_name)
                if not tkinter.messagebox.askokcancel("Renaming File",
                                                      "The name of the file must be the same as package name. New name file will be %s." % new_name,
                                                      parent=viewer):
                    self.logger.info('* add file canceled')
                    return
                target_file = new_name

            filename = Path(target_file).name
            if self.package.exists_file(data_path, filename):
                if not tkinter.messagebox.askokcancel('File already in Package', 'overwrite it?', parent=viewer):
                    self.logger.info('* add file canceled')
                    return

            self.package.add_file(srcFile, data_path, dst_file=target_file)
            if Path(target_file).suffix == '.vpx' or Path(target_file).suffix == '.vpt':
                rom_name = self.baseModel.visualPinball.extract_rom_name(srcFile)  # Bug?
                self.logger.info('+ updating rom name [%s]' % rom_name)
                self.package.set_field('visual pinball/info/romName', rom_name)
                self.package.save()
            self.update_package()

        except Exception as e:
            tkinter.messagebox.showerror('Add File Error', str(e), parent=viewer)

    def del_file(self, viewer, dataPath, srcFile):
        try:
            self.package.remove_file(srcFile, dataPath)
            self.update_package()
        except Exception as e:
            tkinter.messagebox.showerror('Delete File Error', str(e), parent=viewer)

    def get_fileInfo(self, viewer, dataPath, srcFile):
        return self.package.manifest.get_file(dataPath, srcFile)

    def up_file(self, viewer, data_path, src_file):
        dst_data_path = self.package.manifest.prev_file_data_path(data_path, src_file)
        if dst_data_path != '':
            self.package.move_file(src_file, data_path, dst_data_path)
            self.update_package(selection=(dst_data_path, src_file))

    def down_file(self, viewer, data_path, src_file):
        dst_data_path = self.package.manifest.next_file_data_path(data_path, src_file)
        if dst_data_path != '':
            self.package.move_file(src_file, data_path, dst_data_path)
            self.update_package(selection=(dst_data_path, src_file))

    def get_first_image(self):
        return self.package.manifest.get_first_image()
