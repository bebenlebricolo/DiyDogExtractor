import unittest
from ..record import *

class TestRecordModels(unittest.TestCase) :
    def test_single_record(self) :
        record = FileRecord()
        record.path.value = "test path"
        out_dict = record.to_json()

        self.assertEqual(record.kind.value, RecordKind.FileSource)
        self.assertEqual(out_dict[record.path._prop_key], "test path")

        parsed = Record()
        parsed.from_json(out_dict)

        # Types are different
        self.assertNotEqual(parsed, record)
        record.__class__ = Record
        # Casting records, now should work
        self.assertEqual(parsed, record)

    def test_FileRecord(self):
        record = FileRecord()
        record.path.value = "test path"
        out_dict = record.to_json()

        expected_json = {
            Record._static_kind_key : RecordKind.FileSource.value,
            "path" : record.path.value
        }

        # Direct dictionary comparison
        self.assertEqual(out_dict, expected_json)
        parsed = FileRecord()
        parsed.from_json(expected_json)

        # Parsed version should match original one, while coming from direct json content
        self.assertEqual(record, parsed)

    def test_CloudRecord(self):
        record = CloudRecord()
        record.id.value = "test id"
        record.version.value = "pseudo object version"
        out_dict = record.to_json()

        expected_json = {
            Record._static_kind_key : RecordKind.CloudRecord.value,
            "id" : record.id.value,
            "version" : record.version.value
        }

        # Direct dictionary comparison
        self.assertEqual(out_dict, expected_json)
        parsed = CloudRecord()
        parsed.from_json(expected_json)

        # Parsed version should match original one, while coming from direct json content
        self.assertEqual(record, parsed)

    def test_RecordBuilder(self) :
        file_record_json =  {
            Record._static_kind_key : RecordKind.FileSource.value,
            "path" : "Some path on the disk"
        }

        cloud_record_json = {
            Record._static_kind_key : RecordKind.CloudRecord.value,
            "id" : "Some record id",
            "version" : "Some record version"
        }

        wrong_record_json_1 = {
            Record._static_kind_key : "Some unexpected key",
            "id" : "something",
            "version" : "something else"
        }

        # Should produce a valid object
        built_file_record = RecordBuilder.from_json(file_record_json)
        self.assertIsNotNone(built_file_record)
        produced_file_record_json = built_file_record.to_json() #type: ignore
        self.assertEqual(produced_file_record_json, file_record_json)

        # Should produce a valid object
        built_cloud_record = RecordBuilder.from_json(cloud_record_json)
        self.assertIsNotNone(built_cloud_record)
        produced_cloud_record_json = built_cloud_record.to_json() #type: ignore
        self.assertEqual(produced_cloud_record_json, cloud_record_json)

        # Should be rejected
        wrong_record_1 = RecordBuilder.from_json(wrong_record_json_1)
        self.assertIsNone(wrong_record_1)


if __name__ == "__main__" :
    unittest.main()