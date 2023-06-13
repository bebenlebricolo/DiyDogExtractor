from dataclasses import dataclass, field
from .jsonable import Jsonable


@dataclass
class Coordinates(Jsonable) :
    x : float = 0.0
    y : float = 0.0

    def to_json(self) -> dict:
        return {
            "x" : self.x,
            "y" : self.y
        }

    def from_json(self, content) -> None:
        self.x = self._read_prop("x", content, 0.0)
        self.y = self._read_prop("y", content, 0.0)

@dataclass
class TextBlock(Coordinates) :
    text : str = ""
    transformation_matrix = None
    current_matrix = None

    def to_json(self) -> dict :
        parent_dict = super().to_json()
        parent_dict.update({
            "text" : self.text,
            "tm" : self.transformation_matrix,
            "cm" : self.current_matrix,
            }
        )
        return parent_dict

    def from_json(self, content : dict) -> None :
        super().from_json(content)
        self.text = self._read_prop("text", content, "")
        self.transformation_matrix = self._read_prop("tm", content, [0,0,0,0,0,0])
        self.current_matrix = self._read_prop("cm", content, [0,0,0,0,0,0])

@dataclass
class TextElement(Coordinates) :
    text : str = ""

    def to_json(self) -> dict:
        parent_dict = super().to_json()
        parent_dict.update({
            "text" : self.text
        })
        return parent_dict

    def from_json(self, content) -> None:
        super().from_json(content)
        self.text = self._read_prop("text", content, "")

@dataclass
class PageBlocks(Jsonable) :
    elements : list[TextElement] = field(default_factory=list)
    index : int = 0

    def reset(self) :
        self.__init__()

    def to_json(self) -> dict:
        elements_list = []
        for block  in self.elements :
            elements_list.append(block.to_json())
        return {
            "index" : self.index,
            "elements" : elements_list
        }

    def from_json(self, content) -> None:
        self.elements.clear()
        self.index = self._read_prop("index", content, 0)
        if "elements" in content :
            for block in content["elements"] :
                new_block = TextElement()
                new_block.from_json(block)
                self.elements.append(new_block)
