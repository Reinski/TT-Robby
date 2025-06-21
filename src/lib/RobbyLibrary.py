# Copyright (c) 2025 Reiner Nikulski
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
import Shot as S
from Shot import Shot

class RobbyLibrary:
    """RobbyLibrary contains a collection of shots that can be played by the machine and a collection of programs using these Shots."""
    
    def __init__(self):
        self.__shotsdata: dict[str, dict] = {}
        self.__programs: dict[str, dict] = {}

    def add_program(self, key: str, name: str, description: str = "", json_data: str = "") -> None:
        """Add a program to the library with a given name.
        The key is used to identify the program in the library and is the only field that cannot be changed."""
        #TODO: implement programs as a separate class
        # I wanted to have it combined with the shots library, because programs are relying on the predefined shots.
        # They should just reference them, so that the shots can be altered without changing the programs.
        # Thought behind this is that a program is a reflection of a practice rather that the technical data.
        if key in self.__programs:
            raise ValueError(f"Program with key '{key}' already exists in the library.")
        self.__programs[key] = {'key': key, 'name': name, 'description': description, 'json_data': json_data, 'shots_cycle': []}

    def add_shot(self, key: str, shot: Shot, name: str, description: str = "", json_data: str = "") -> None:
        """Add a shot to the library with a given name.
        The key is used to identify the shot in the library and is the only field that cannot be changed.
        Args:
            key (str): The unique identifier for the shot.
            shot (Shot): The shot to add to the library.
            name (str): The name of the shot.
            description (str, optional): A description of the shot. Defaults to an empty string.
            json_data (str, optional): JSON data provided by clients for additional features, associated with the shot. Defaults to an empty string."""
        if key in self.__shotsdata:
            raise ValueError(f"Shot with key '{key}' already exists in the library.")
        self.__shotsdata[key] = {'key': key, 'name': name, 'shot': shot, 'description': description, 'json_data': json_data}

    def get_shot(self, key: str) -> Shot:
        """Get a shot by its index."""
        return self.__shotsdata[key]['shot']
    
    def get_shot_data(self, key: str) -> dict:
        """Get full shot data by its index."""
        return self.__shotsdata[key]

    def count(self) -> int:
        """Return the number of shots in the library."""
        return len(self.__shotsdata)
    
    def get_all_entries(self) -> dict[str, dict]:
        """Get a deep copy of the shots data in the library.
        This is memory and performance intensive, but allows modifications without changeing the originals in the library. 
        If this is not necessary, use the .entries property, which returns a direct reference.
        """
        shots = {}
        for shot_data in self.__shotsdata.values():
            shots[shot_data['key']] = {
                'key': shot_data['key'],
                'name': shot_data['name'],
                'description': shot_data['description'],
                'json_data': shot_data['json_data'],
                'shot': S.create_from_shot(shot_data['shot'])
            }
        return shots
    
    def getConfigData(self) -> dict:
        shots_config = {'shots': []}
        for shot_data in self.__shotsdata.values():
            cfg = {
                'key': shot_data['key'],
                'name': shot_data['name'],
                'description': shot_data['description'],
                'json_data': shot_data['json_data'],
                'shot': shot_data['shot'].getConfigData()
            }
            shots_config['shots'].append(cfg)
        return shots_config
    
    def load_from_config(self, config: dict):
        if 'shots' in config:
            for shot_cfg in config['shots']:
                shot = S.create_from_config(shot_cfg['shot'])
                self.add_shot(shot_cfg['key'], shot, shot_cfg['name'], shot_cfg.get('description', ""), shot_cfg.get('json_data', ""))
            
    entries = property(lambda self: self.__shots)
    """Get the shots in the library. This is a direct reference to the internal data structure, so modifications will change the library!
    If you want to modify the shots without changing the library, use the get_all_shotsdata() method instead.
    """