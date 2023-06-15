import unittest
import json
from ..jsonable import *
from typing import Literal

class Payload(JsonElement):
    payload1 : JsonProperty[str]
    payload2 : JsonProperty[str]
    payload3 : JsonProperty[str]

    def __init__(self) :
        self.payload1 = JsonProperty('payload1')
        self.payload2 = JsonProperty('payload2')
        self.payload3 = JsonProperty('payload3')

class MyObject(JsonElement) :
    name : JsonProperty[str]
    id : JsonProperty[str]
    data : JsonProperty[Payload]

    def __init__(self) :
        self.name = JsonProperty('name')
        self.id = JsonProperty('id')
        self.data = JsonProperty('data')

    def from_json(self, content: dict) -> None:
        self.name.try_read(content, "")
        self.id.try_read(content, "123456789")
        self.data.try_read(content, None)


class TestJsonable(unittest.TestCase) :
    def test_json_object(self):
        test_object = {
            "name" : "test name",
            "id" : "test id",
            "data" : {
                "payload1" : "fake 1",
                "payload2" : "fake 2",
                "payload3" : "fake 3"
            }
        }

        my_object = MyObject()
        my_object.from_json(test_object)

if __name__ == "__main__" :
    unittest.main()