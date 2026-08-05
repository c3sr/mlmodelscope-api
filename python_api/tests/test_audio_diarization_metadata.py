import pathlib
import sys
import unittest
from unittest.mock import Mock


PYTHON_API = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_API))

from db import ensure_pyannote_diarization_model


class AudioDiarizationMetadataTest(unittest.TestCase):
    def test_returns_existing_model_without_writing(self):
        cursor = Mock()
        cursor.fetchone.return_value = {"id": 42}
        connection = Mock()

        model_id = ensure_pyannote_diarization_model(cursor, connection)

        self.assertEqual(model_id, 42)
        self.assertEqual(cursor.execute.call_count, 1)
        connection.commit.assert_not_called()

    def test_inserts_model_for_pytorch_framework(self):
        cursor = Mock()
        cursor.fetchone.side_effect = [None, {"id": 3}, {"id": 43}]
        connection = Mock()

        model_id = ensure_pyannote_diarization_model(cursor, connection)

        self.assertEqual(model_id, 43)
        self.assertEqual(cursor.execute.call_count, 3)
        insert_sql = cursor.execute.call_args_list[2].args[0]
        insert_values = cursor.execute.call_args_list[2].args[1]
        self.assertIn("INSERT INTO models", insert_sql)
        self.assertIn("audio_diarization", insert_values)
        connection.commit.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
