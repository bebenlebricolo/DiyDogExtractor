from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from .jsonable import Jsonable, JsonProperty, JsonOptionalProperty
from typing import Optional, Literal

class RecordKind(Enum) :
    FileSource = "FileSource"
    CloudRecord = "CloudRecord"

class Record(Jsonable):
    kind : JsonProperty[RecordKind]

    def __init__(self) :
        self.kind = JsonProperty[RecordKind]('kind', RecordKind.FileSource)

    def to_json(self) -> dict:
        return {
            self.kind._prop_key : self.kind.value.value,
        }

class RecordBuilder :
    @staticmethod
    def from_json(content : dict) -> Optional[Record] :
        record : Optional[Record] = None
        kind_value = content[Record.kind._prop_key]
        match  kind_value:
            case RecordKind.FileSource :
                record = FileRecord()
                record.from_json(content)
            case RecordKind.CloudRecord :
                record = CloudRecord()
                record.from_json(content)
            case _:
                raise Exception("Unknown kind ! Kind property was set to : {}".format(kind_value))
        return record

class FileRecord(Record) :
    path : JsonOptionalProperty[str]

    def __init__(self) :
        super().__init__()
        self.path = JsonOptionalProperty[str]('path')

    def from_json(self, content: dict) -> None:
        self.path.value = self.path.get_node(content)

    def to_json(self) -> dict:
        out = super().to_json()
        out.update({
            self.kind._prop_key : self.kind.value.value,
            self.path._prop_key : self.path.value
        })
        return out

class CloudRecord(Record):
    id : JsonOptionalProperty[str]
    version : JsonOptionalProperty[str]

    def __init__(self):
        super().__init__()
        self.id = JsonOptionalProperty[str]('id')
        self.version = JsonOptionalProperty[str]('version')

    def from_json(self, content: dict) -> None:
        self.id.value = self.id.get_node(content)
        self.version.value = self.version.get_node(content)

    def to_json(self) -> dict:
        out = super().to_json()
        out.update({
                self.kind._prop_key : self.kind.value.value,
                self.id._prop_key : self.id.value,
                self.version._prop_key : self.version.value
            })
        return out