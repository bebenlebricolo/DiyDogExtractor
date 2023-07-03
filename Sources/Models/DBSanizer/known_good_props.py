import json
from dataclasses import dataclass, field
from enum import Enum

from typing import cast, Optional, Generic, TypeVar
from ..jsonable import Jsonable, JsonOptionalProperty, JsonProperty

class PropKind(Enum):
    Yeast = "yeasts"
    Hop = "hops"
    Malt = "malts"
    Styles = "styles"

class BaseProperty(Jsonable):
    name : JsonProperty[str]
    url : JsonProperty[str]

    def __init__(self, name : Optional[str] = None, url : Optional[str] = None) -> None:
        self.name = JsonProperty("name", "")
        self.url = JsonProperty("url", "")

        if name :
            self.name.value = name
        if url :
            self.url.value = url


    def to_json(self) -> dict:
        return {
            self.name._prop_key : self.name.value,
            self.url._prop_key : self.url.value
        }

    def from_json(self, content: dict) -> None:
        self.name.value = self.name.try_read(content, "")
        self.url.value = self.url.try_read(content, "")

    @staticmethod
    def build_derived(kind : PropKind) :
        match kind :
            case PropKind.Yeast :
                return YeastProp()
            case PropKind.Hop :
                return HopProp()
            case PropKind.Malt :
                return MaltProp()
            case PropKind.Styles :
                return StylesProp()
            case _:
                raise Exception("Whoops ! Wrong type !")

class HopProp(BaseProperty) :
    pass

class MaltProp(BaseProperty) :
    aliases : JsonOptionalProperty[list[str]]
    manufacturer : JsonOptionalProperty[str]

    def __init__(self, name: str | None = None, url: str | None = None, aliases : Optional[list[str]] = None, manufacturer : Optional[str] = None) -> None:
        super().__init__(name, url)

        self.aliases = JsonOptionalProperty("aliases", None)
        self.manufacturer = JsonOptionalProperty("manufacturer", None)

        if aliases :
            self.aliases.value = aliases
        if manufacturer :
            self.manufacturer.value = manufacturer

    def to_json(self) -> dict:
        out_dict = super().to_json()
        out_dict.update({
            self.aliases._prop_key : self.aliases.value,
            self.manufacturer._prop_key : self.manufacturer.value
        })
        return out_dict

    def from_json(self, content: dict) -> None:
        super().from_json(content)
        aliases_node = self.aliases.get_node(content)
        if aliases_node:
            self.aliases.value = []
            for elem in aliases_node:
                self.aliases.value.append(elem)

        self.manufacturer.value = self.manufacturer.read(content)


class YeastProp(MaltProp) :
    pass

class StylesProp(BaseProperty) :
    category : JsonProperty[str]

    def __init__(self, name: str | None = None, url: str | None = None, category : Optional[str] = None) -> None:
        super().__init__(name, url)
        self.category = JsonProperty("category", "")

        if category :
            self.category.value = category

    def to_json(self) -> dict:
        out_dict = super().to_json()
        out_dict.update({
            self.category._prop_key : self.category.value
        })
        return out_dict

    def from_json(self, content: dict) -> None:
        super().from_json(content)
        self.category.try_read(content, "")

