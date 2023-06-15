import unittest
from ..record import *

class TestRecordModels(unittest.TestCase) :
    def test_single_record(self) :
        record = FileRecord()
        record.path.value = "test path"
        out_dict = record.to_json()

        self.assertEqual(record.kind.value, RecordKind.FileSource)
        self.assertEqual(out_dict[record.path._prop_key], "test path")


if __name__ == "__main__" :
    unittest.main()