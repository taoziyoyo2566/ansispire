import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
import io
import sys
import os

# Add parent dir to path to import sink
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import sink

class TestSink(unittest.TestCase):
    def test_append(self):
        m = mock_open()
        with patch("builtins.open", m), patch("os.makedirs"):
            sink._append({"test": "data"})
        
        m().write.assert_called_once()
        written_data = m().write.call_args[0][0]
        self.assertIn('"test":"data"', written_data)

    def test_handler_get_healthz(self):
        mock_server = MagicMock()
        mock_request = MagicMock()
        mock_client_address = ("127.0.0.1", 12345)
        
        with patch.object(sink.Handler, "handle"), patch.object(sink.Handler, "parse_request"):
            handler = sink.Handler(mock_request, mock_client_address, mock_server)
        
        handler.request_version = "HTTP/1.1"
        handler.wfile = io.BytesIO()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        
        handler.path = "/healthz"
        handler.do_GET()
        
        handler.send_response.assert_called_with(200)
        self.assertEqual(handler.wfile.getvalue(), b"ok")

    def test_handler_get_404(self):
        mock_server = MagicMock()
        mock_request = MagicMock()
        with patch.object(sink.Handler, "handle"), patch.object(sink.Handler, "parse_request"):
            handler = sink.Handler(mock_request, ("127.0.0.1", 12345), mock_server)
        handler.request_version = "HTTP/1.1"
        handler.send_response = MagicMock()
        handler.end_headers = MagicMock()
        
        handler.path = "/notfound"
        handler.do_GET()
        handler.send_response.assert_called_with(404)

    def test_handler_post_event(self):
        mock_server = MagicMock()
        mock_request = MagicMock()
        with patch.object(sink.Handler, "handle"), patch.object(sink.Handler, "parse_request"):
            handler = sink.Handler(mock_request, ("127.0.0.1", 12345), mock_server)
        handler.request_version = "HTTP/1.1"
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.headers = {"Content-Length": "15"}
        handler.rfile = io.BytesIO(b'{"key":"value"}')
        handler.path = "/event"
        
        with patch("sink._append") as mock_append:
            handler.do_POST()
        
        handler.send_response.assert_called_with(204)
        mock_append.assert_called_once()
        record = mock_append.call_args[0][0]
        self.assertEqual(record["payload"], {"key": "value"})

    def test_handler_post_invalid_json(self):
        mock_server = MagicMock()
        mock_request = MagicMock()
        with patch.object(sink.Handler, "handle"), patch.object(sink.Handler, "parse_request"):
            handler = sink.Handler(mock_request, ("127.0.0.1", 12345), mock_server)
        handler.request_version = "HTTP/1.1"
        handler.send_response = MagicMock()
        handler.end_headers = MagicMock()
        handler.headers = {"Content-Length": "7"}
        handler.rfile = io.BytesIO(b'invalid')
        handler.path = "/event"
        
        with patch("sink._append") as mock_append:
            handler.do_POST()
        
        self.assertEqual(mock_append.call_args[0][0]["payload"], "invalid")

if __name__ == "__main__":
    unittest.main()
