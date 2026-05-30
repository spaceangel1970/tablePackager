import json
import traceback
from tkinter import messagebox
from packager.model.package import *

from packager.tools.observer import Observable
from packager.tools.toolbox import *


class InstalledTablesModel(Observable):
    def __init__(self, baseModel):
        super().__init__()
        self.__baseModel = baseModel
        self.__tables = []
        self.__selectedTable = []

    @property
    def baseModel(self):
        return self.__baseModel

    @property
    def logger(self):
        return self.__baseModel.logger

    @property
    def tables(self):
        return self.__tables

    def update(self, app_choices=None):
        self.__tables = []
        
        # Determine platforms to scan. Defaults match UI start-up state (VP=True, FP=False).
        scan_visual = app_choices['visual_pinball'].get() if app_choices else True
        scan_future = app_choices['futurPinball'].get() if app_choices else False

        if scan_visual:
            self.logger.info("Scanning for Visual Pinball tables...")
            base_path = Path(self.baseModel.visual_pinball_path)
            
            tables_path = base_path / "Tables"
            if not tables_path.exists():
                tables_path = base_path / "tables" # Fallback to lowercase

            if tables_path.exists():
                for vpx_file in tables_path.glob('**/*.vpx'):
                    self.__tables.append({'type': 'vpx', 'name': vpx_file.stem})
                for vpt_file in tables_path.glob('**/*.vpt'):
                    self.__tables.append({'type': 'vpt', 'name': vpt_file.stem})
            else:
                self.logger.error(f"Target Visual Pinball tables folder missing at: {tables_path}")

        if scan_future:
            self.logger.info("Scanning for Future Pinball tables...")
            fp_path = self.baseModel.config.get('future_pinball_path')
            if fp_path:
                fp_base_path = Path(fp_path)
                fp_tables_path = fp_base_path / "Tables"

                if fp_tables_path.exists():
                    for fpt_file in fp_tables_path.glob('**/*.fpt'):
                        self.__tables.append({'type': 'fpt', 'name': fpt_file.stem})
                else:
                    self.logger.error(f"Target Future Pinball tables folder missing at: {fp_tables_path}")
            else:
                self.logger.warning('Future Pinball path not configured, skipping scan.')

        self.__tables.sort(key=lambda table: table['name'].upper())
        self.notify_all(self, events=['<<UPDATE TABLES>>'], tables=self.__tables)  # update listeners

    def selectTable(self, selection):
        self.__selectedTable = []
        for index in selection:
            self.__selectedTable.append(self.__tables[index])
        self.notify_all(self, events=['<<TABLE SELECTED>>'], tables=self.__selectedTable)  # update listeners

    def unSelectTable(self):
        self.__selectedTable = []
        self.notify_all(self, events=['<<TABLE UNSELECTED>>'])  # update listeners

    def extract_tables(self, table_choice) -> None:
        self.notify_all(self, events=['<<DISABLE_ALL>>', '<<BEGIN_ACTION>>'],
                        tables=self.__selectedTable)  # update listeners
        extract_thread = AsynRun(self.extract_tables_begin, self.extract_tables_end, context=table_choice)
        extract_thread.start()

    def extract_tables_begin(self, context=None) -> bool:
        to_overwrite = False
        if not self.__selectedTable:  # empty selection
            raise ValueError('No selected table')

        self.baseModel.logger.info("Begin Extraction")
        for table in self.__selectedTable:
            try:
                # check if table is already a package
                if Path(self.baseModel.package_path + '/' + table['name'] + self.baseModel.package_extension).exists():
                    if (is_read_only_file(
                            self.baseModel.package_path + '/' + table['name'] + self.baseModel.package_extension)):
                        result = messagebox.showerror("Extraction",
                                                      "A protected table package already exist.");
                        continue
                    to_overwrite = True
                clean_dir(self.baseModel.tmp_path)
                self.logger.info("--[Working on '%s']------------------" % (table['name']))

                package = Package(self.baseModel, table['name'])
                package.new(self.baseModel.tmp_path)
                # TODO: besoin de copier les manifests ici pour la comparer les infos de fichiers
                manifest_check_path = os.path.normpath(os.path.join(self.baseModel.installed_path, table['name'] + '.manifest.json'))
                if os.path.exists(manifest_check_path):
                    self.logger.info(f"++ Found existing manifest for merge at: {manifest_check_path}")
                    package.merge(installed=True)
                else:
                    self.logger.info(f"-- No existing manifest found at {self.baseModel.installed_path}, starting fresh.")

                if context['visual_pinball'].get():
                    self.baseModel.visualPinball.extract(package)
                    self.baseModel.vpinMame.extract(package)
                    self.baseModel.ultraDMD.extract(table['name'], package)
                    self.baseModel.flexDMD.extract(table['name'], package)
                    if context['pinupSystem'].get():
                        self.baseModel.pinupSystem.extract(package, 'visual pinball')
                if context['pinballX'].get():
                    self.baseModel.pinballX.extract(table['name'], package)
                if context['futurPinball'].get():
                    self.logger.warning("extract from futurPinball is not yet implemented")
                    if context['pinupSystem'].get():
                        self.logger.warning("extract from pinupSystem is not yet implemented")
                package.save()
                package.pack()  # zip package

                if to_overwrite:
                    os.remove(self.baseModel.package_path + '/' + table['name'] + self.baseModel.package_extension)

                shutil.move(self.baseModel.tmp_path + '/' + table['name'] + self.baseModel.package_extension,
                            self.baseModel.package_path)

            except Exception as e:
                import traceback
                traceback.print_exc()  # <-- Indented 4 spaces to the right
                # messagebox.showerror('Backup Package', str(e))
                return False
        clean_dir(self.baseModel.tmp_path)
        return True

    def extract_tables_end(self, context=None, success=True):
        self.logger.info("--[Done]------------------")
        self.notify_all(self, events=['<<END_ACTION>>', '<<ENABLE_ALL>>'],
                        tables=self.__selectedTable)  # update listeners
        self.baseModel.packagedTablesModel.update()

    def delete_tables(self, viewer):
        self.notify_all(self, events=['<<DISABLE_ALL>>', '<<BEGIN_ACTION>>'])  # update listeners
        tables = ', '.join(p['name'] for p in self.__selectedTable)
        del_confirmed = messagebox.askokcancel("Delete Table(s)",
                                               "Are you sure you want to delete table(s) '%s'" % tables,
                                               parent=viewer)
        if not del_confirmed:
            self.notify_all(self, events=['<<END_ACTION>>', '<<ENABLE_ALL>>'])  # update listeners
            return

        delete_table_thread = AsynRun(self.delete_tables_begin, self.delete_tables_end)
        delete_table_thread.start()

    def delete_tables_begin(self, context=None):
        if not self.__selectedTable:  # empty selection
            raise ValueError('No selected table')

        self.logger.info("--[Delete Table(s)]------------------")
        for table in self.__selectedTable:
            self.logger.info("--[Working on '%s']------------------" % (table['name']))

            ultraDMD = ''
            flexDMD = ''
            rom_list = []
            isPackage = False
            manifest = Manifest(table['name'], self.baseModel.package_version)
            try:
                manifest.open(self.baseModel.installed_path, installed=True)
                isPackage = True
                if manifest.exists_field('visual pinball/info/romName'):
                    rom_list = manifest.get_field('visual pinball/info/romName')
                if manifest.exists_field('visual pinball/info/ultraDMD'):
                    ultraDMD = manifest.get_field('visual pinball/info/ultraDMD')
                if manifest.exists_field('visual pinball/info/flexDMD'):
                    flexDMD = manifest.get_field('visual pinball/info/flexDMD')
            except:
                rom_list = self.baseModel.visualPinball.get_rom_name(table['name'])  # use package.manifest if exists

            self.baseModel.visualPinball.delete(table['name'])

            self.baseModel.vpinMame.delete(table['name'], rom_list)
            if isPackage:
                if ultraDMD != '':
                    self.baseModel.ultraDMD.delete(table['name'], dir_name=ultraDMD)  # use package.manifest if exists
                if flexDMD != '':
                    self.baseModel.flexDMD.delete(table['name'], dir_name=flexDMD)  # use package.manifest if exists
            else:
                self.baseModel.ultraDMD.delete(table['name'])  # use package.manifest if exists
                self.baseModel.flexDMD.delete(table['name'])  # use package.manifest if exists
            self.baseModel.pinballX.delete(table['name'])
            self.baseModel.pinupSystem.delete(table['name'], 'visual pinball')
            self.logger.warning("delete on futurPinball is not yet implemented")
            if isPackage:
                os.unlink(self.baseModel.installed_path + '/' + manifest.filename)

        return True

    def delete_tables_end(self, context=None, success=True):
        self.logger.info("--[Done]------------------")
        
        # 1. Reset our internal tracking selection states completely
        self.__selectedTable = []
        
        # 2. Tell the UI to unlock all buttons and finish processing actions
        self.notify_all(self, events=['<<TABLE UNSELECTED>>', '<<END_ACTION>>', '<<ENABLE_ALL>>'])
        
        # 3. FORCE the main UI loop to safely execute a refresh out-of-thread
        # This acts exactly like a delayed automatic tap on your green reload button!
        import tkinter
        tkinter._default_root.after_idle(self.update)