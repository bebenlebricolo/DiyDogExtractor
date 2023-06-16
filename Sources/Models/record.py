from pathlib import Path
from enum import Enum
from typing import Optional

from .jsonable import Jsonable, JsonProperty, JsonOptionalProperty

class RecordKind(Enum) :
    FileSource = "FileSource"
    CloudRecord = "CloudRecord"
    Unknown = "Unknown"

    @staticmethod
    def can_convert(key : str) -> bool :
        return key in [RecordKind.FileSource.value,
                       RecordKind.CloudRecord.value]


class Record(Jsonable):
    kind : JsonProperty[RecordKind]
    # Static kind key is needed by the RecordBuilder in order to instantiate a new Record derived class while parsing Json,
    # when the type of Record to be created is not known yet (so the Record.kind object is not yet configured; because the __init__ method
    # has not yet been called)
    _static_kind_key = 'kind'

    def __init__(self, kind : RecordKind = RecordKind.FileSource) :
        self.kind = JsonProperty[RecordKind](Record._static_kind_key, kind)

    def to_json(self) -> dict:
        return {
            self.kind._prop_key : self.kind.value.value,
        }

    def from_json(self, content: dict) -> None:
        self.kind.value = RecordKind[content[self.kind._prop_key]]

    def __eq__(self, other: object) -> bool:
        return self.kind.value == other.kind.value # type: ignore

class FileRecord(Record) :
    path : JsonOptionalProperty[str]

    def __init__(self, path : Optional[str] = None) :
        super().__init__(kind=RecordKind.FileSource)
        self.path = JsonOptionalProperty[str]('path')
        self.path.value = path

    def from_json(self, content: dict) -> None:
        # Don't need to call Record.from_json() at this point because the __init__ of this class already set the self.kind (RecordKind) value
        self.path.value = self.path.get_node(content)

    def to_json(self) -> dict:
        out = super().to_json()
        out.update({
            self.kind._prop_key : self.kind.value.value,
            self.path._prop_key : self.path.value
        })
        return out

    def __eq__(self, other: object) -> bool:
        if not type(self) == type(other) :
            return False
        identical = super().__eq__(other)
        identical &= self.path.value == other.path.value #type: ignore
        return identical

class CloudRecord(Record):
    id : JsonOptionalProperty[str]
    version : JsonOptionalProperty[str]

    def __init__(self, id : Optional[str] = None, version : Optional[str] = None):
        super().__init__(RecordKind.CloudRecord)
        self.id = JsonOptionalProperty[str]('id')
        self.id.value = id
        self.version = JsonOptionalProperty[str]('version')
        self.version.value = version

    def from_json(self, content: dict) -> None:
        # Don't need to call Record.from_json() at this point because the __init__ of this class already set the self.kind (RecordKind) value
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

    def __eq__(self, other: object) -> bool:
        if not type(self) == type(other) :
            return False
        identical = super().__eq__(other)
        identical &= self.id.value == other.id.value            #type: ignore
        identical &= self.version.value == other.version.value  #type: ignore
        return identical


class RecordBuilder :
    @staticmethod
    def from_json(content : dict) -> Optional[Record] :
        record : Optional[Record] = None
        kind_str = content[Record._static_kind_key]
        if not RecordKind.can_convert(kind_str) :
            return None

        kind_enum = RecordKind[kind_str]
        match  kind_enum:
            case RecordKind.FileSource :
                record = FileRecord()
                record.from_json(content)
            case RecordKind.CloudRecord :
                record = CloudRecord()
                record.from_json(content)
            case _:
                raise Exception("Should not reach here !")
        return record

