from dataclasses import dataclass, field

class Jsonable :
    def _read_prop(self, key : str, content : dict, default) :
        if key in content :
            return content[key]
        return default

    def to_json(self) -> dict :
        pass

    def from_json(self, content : dict) -> None :
        pass
