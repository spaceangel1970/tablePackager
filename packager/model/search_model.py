import json
from tkinter import messagebox
from packager.model.package import *
from packager.pincab.site_cab import *
from packager.tools.observer import Observable
from packager.tools.toolbox import *


class Search_Model(Observable):
    def __init__(self, baseModel):
        super().__init__()
        self.__baseModel = baseModel
        self.__pinball_machine = []
        self.__selected_pinball_machine = []

    @property
    def baseModel(self):
        return self.__baseModel

    @property
    def logger(self):
        return self.__baseModel.logger

    @property
    def pinball_machine(self):
        return self.__pinball_machine

    def update(self, contains:str='', only_with_vpx:bool=True) -> None:
        # ... (debug print lines) ...
        print("update (%s)" % contains)
        self.__pincab = []
        
        # 1. Normalize search term to lowercase once
        search_term = contains.lower()
        
        for key, pincab in self.baseModel.database.data.items():
            selector: bool = True

            # 2. Use 'in' for partial matching and .lower() for case-insensitivity
            if contains != '':
                selector = selector and (search_term in key.lower())
                
            if only_with_vpx:
                selector = selector and len(pincab['Urls']) >= 1
            if selector:
                self.__pincab.append(key)
        
        self.notify_all(self, events=['<<UPDATE TABLES>>'],
                        pinball_machines=self.__pincab,
                        nb_result=len(self.__pincab),
                        total=len(self.baseModel.database.data))

    def select_pinball_machine(self, pinball_machine:dict) -> None:
        pinball_machine_data=self.baseModel.database.data[pinball_machine]
        self.notify_all(self, events=['<<PINBALL SELECTED>>'], pinball_machine=pinball_machine_data)  # update listeners

    def unselect_pinball_machine(self):
        self.__selected_pinball_machine = []
        self.notify_all(self, events=['<<PINBALL UNSELECTED>>'])  # update listeners

    def update_db(self):
        pass

    def update_database(self) -> None:
        self.notify_all(self, events=['<<DISABLE_ALL>>', '<<BEGIN_ACTION>>'])  # update listeners
        extract_thread = AsynRun(self.update_database_begin, self.update_database_end)
        extract_thread.start()

    def update_database_begin(self, context=None) -> bool:
        self.logger.info('Update Pinball Database')
        
        try:
            # This triggers your new method in TableDatabase.py
            # which downloads the CSV from the VPS GitHub repository.
            self.baseModel.database.update_all_pincab_file_from_list()
            
            self.logger.info('Database successfully updated from Virtual Pinball Spreadsheet')
            
        except Exception as e:
            self.logger.error(f"Failed to update database: {e}")
            messagebox.showerror('Update Pinball Database Error', str(e))
            return False

        return True

    def update_database_end(self, context=None, success=True):
        self.logger.info("--[Done]------------------")
        self.notify_all(self, events=['<<END_ACTION>>', '<<ENABLE_ALL>>'])
