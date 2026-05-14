import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
import os
import sys
from datetime import datetime, timezone

# Add parent dir to path to import relay
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import relay

class TestRelay(unittest.TestCase):
    def test_load_cursor_exists(self):
        with patch("builtins.open", mock_open(read_data='{"last_ts": "2023-01-01T00:00:00Z"}')):
            self.assertEqual(relay.load_cursor(), "2023-01-01T00:00:00Z")

    def test_load_cursor_missing(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            self.assertEqual(relay.load_cursor(), relay.EPOCH)

    def test_save_cursor(self):
        m = mock_open()
        with patch("builtins.open", m), patch("os.makedirs"), patch("os.replace"):
            relay.save_cursor("2023-01-01T00:00:00Z")
        
        # Check that the timestamp was written at some point
        all_writes = "".join(call.args[0] for call in m().write.call_args_list)
        self.assertIn("2023-01-01T00:00:00Z", all_writes)

    @patch("urllib.request.urlopen")
    def test_fetch_page(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'[{"id": 1}]'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp
        
        res = relay.fetch_page(1)
        self.assertEqual(res, [{"id": 1}])

    @patch("relay.forward")
    @patch("relay.fetch_page")
    @patch("relay.save_cursor")
    def test_tick_new_events(self, mock_save, mock_fetch, mock_forward):
        relay.SEM_TOKEN = "dummy"
        mock_fetch.side_effect = [
            [{"created": "2023-01-01T00:00:02Z"}, {"created": "2023-01-01T00:00:01Z"}],
            []
        ]
        
        cursor = "2023-01-01T00:00:00Z"
        new_cursor = relay.tick(cursor)
        
        self.assertEqual(new_cursor, "2023-01-01T00:00:02Z")
        self.assertEqual(mock_forward.call_count, 2)
        mock_save.assert_called_once_with("2023-01-01T00:00:02Z")

    @patch("relay.forward")
    @patch("relay.fetch_page")
    def test_tick_no_new_events(self, mock_fetch, mock_forward):
        relay.SEM_TOKEN = "dummy"
        mock_fetch.return_value = [{"created": "2023-01-01T00:00:00Z"}]
        
        cursor = "2023-01-01T00:00:00Z"
        new_cursor = relay.tick(cursor)
        
        self.assertEqual(new_cursor, cursor)
        mock_forward.assert_not_called()

if __name__ == "__main__":
    unittest.main()
