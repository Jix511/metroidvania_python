import json
import tempfile
import unittest
from pathlib import Path

from systems.json_storage import (JsonStorageError, backup_path_for,
    load_json_with_recovery, save_json_atomic)


def valid_document(data):
    return isinstance(data, dict) and isinstance(data.get('value'), int)


class JsonStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / 'save.json'

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_atomic_save_creates_primary_and_backup(self):
        save_json_atomic(self.path, {'value': 7}, valid_document)

        self.assertEqual(json.loads(self.path.read_text(encoding='utf-8')), {'value': 7})
        backup = backup_path_for(self.path)
        self.assertEqual(json.loads(backup.read_text(encoding='utf-8')), {'value': 7})

    def test_corrupt_primary_is_recovered_from_backup(self):
        save_json_atomic(self.path, {'value': 9}, valid_document)
        self.path.write_text('{broken', encoding='utf-8')

        data, recovered = load_json_with_recovery(self.path, valid_document)

        self.assertTrue(recovered)
        self.assertEqual(data, {'value': 9})
        self.assertEqual(json.loads(self.path.read_text(encoding='utf-8')), data)

    def test_invalid_primary_schema_uses_backup(self):
        save_json_atomic(self.path, {'value': 11}, valid_document)
        self.path.write_text('{"value": "wrong"}', encoding='utf-8')

        data, recovered = load_json_with_recovery(self.path, valid_document)

        self.assertTrue(recovered)
        self.assertEqual(data, {'value': 11})

    def test_two_corrupt_copies_raise_storage_error(self):
        self.path.write_text('{broken', encoding='utf-8')
        backup_path_for(self.path).write_text('[]', encoding='utf-8')

        with self.assertRaises(JsonStorageError):
            load_json_with_recovery(self.path, valid_document)


if __name__ == '__main__':
    unittest.main()
