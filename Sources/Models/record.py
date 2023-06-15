from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from .jsonable import Jsonable, JsonProperty, JsonElement
from typing import Optional, Literal

class RecordKind(Enum) :
    FileSource = "FileSource"
    CloudRecord = "CloudRecord"

@dataclass
class Record(JsonElement, Jsonable):
    #kind : JsonProperty[Literal['kind'], str] = field(default_factory=JsonProperty)
    pass
class RecordBuilder :
    pass
    # @staticmethod
    # def from_json(content : dict) -> Optional[Record] :
    #     record : Optional[Record] = None
    #     kind_value = content[Record.kind._prop_key]
    #     match  kind_value:
    #         case RecordKind.FileSource :
    #             record = FileRecord()
    #             record.from_json(content)
    #         case RecordKind.CloudRecord :
    #             record = CloudRecord()
    #             record.from_json(content)
    #         case _:
    #             raise Exception("Unknown kind ! Kind property was set to : {}".format(kind_value))
    #     return record

@dataclass
class FileRecord(Record, JsonElement) :
    pass
    # path : JsonProperty[Literal['path'],str] = field(default_factory=JsonProperty)

    # def from_json(self, content: dict) -> None:
    #     self.path.try_read(content, "")

    # def to_json(self) -> dict:
    #     return {
    #         self.path._prop_key : self.path._prop_value
    #}

@dataclass
class CloudRecord(Record, JsonElement):
    pass
    # id : JsonProperty[Literal['id'], str] = field(default_factory=JsonProperty)
    # version : JsonProperty[Literal['version'], str] = field(default_factory=JsonProperty)

    # def from_json(self, content: dict) -> None:
    #     return super().from_json(content)

    # def to_json(self) -> dict:
    #     return super().to_json()