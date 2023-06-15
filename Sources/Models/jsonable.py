from dataclasses import dataclass, field
from typing import TypeVar, Generic, Optional, Any, get_args

class Jsonable :
    """Jsonable traits"""
    def _read_prop(self, key : str, content : dict, default) :
        if key in content :
            return content[key]
        return default

    def to_json(self) -> dict :
        return {}

    def from_json(self, content : dict) -> None :
        pass


# Base Json interface
@dataclass
class JsonElement(Jsonable):
    _prop_key : str = ""

    def get_node(self, content : dict) -> Any :
        if self._prop_key in content :
            return content[self._prop_key]
        return None


TVal = TypeVar("TVal")

@dataclass
class JsonProperty(JsonElement, Generic[TVal]):
    _prop_key : str = ""
    _prop_value : Optional[TVal] = None
    _generic_type_repr : str = ""

    def __init__(self, key : str, value : Optional[TVal] = None) :
        self._prop_key = key
        self._prop_value = value
        self._generic_type_repr = str(TVal)

    def read(self, content : dict) :
        raw_value = self.get_node(content)
        if type(self._prop_value) in [int, float, bool, str]:
            self._prop_value = raw_value

        # otherwise, this is implementation defined and we don't have enough data to do proper specialization
        # -> Would have been nice to to a _prop_value.from_json() if we happen to know that it's a Jsonable object

    def try_read(self, content : dict, default : Optional[TVal]) :
        if self._prop_key in content :
            self.read(content)
        else :
            self._prop_value = default

@dataclass
class JsonArray(Jsonable) :
    data : Optional[list[Any]] = None

    def read(self, content : dict) :
        raise NotImplementedError("Should be overridden before use")

    def try_read(self, content : dict, default : Any) :
        raise NotImplementedError("Should be overridden before use")