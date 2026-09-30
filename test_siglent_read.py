"""Offline tests: every socket connection is mocked; no lab equipment is used."""

import contextlib
import io
import json
import socket
import unittest
from unittest.mock import MagicMock, patch

import siglent_read as reader


class SiglentReaderTests(unittest.TestCase):
    def setUp(self):
        self.network = patch.object(reader.socket, "create_connection")
        self.connect = self.network.start()
        self.addCleanup(self.network.stop)
        self.connect.side_effect = AssertionError("unexpected connection attempt")

    def fake_socket(self, chunks):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.recv.side_effect = chunks
        return connection

    def test_voltage_formats(self):
        for reply, expected in (
            ("C1:PAVA MIN,3.120000E+00V", 3.12),
            ("C1:PARAMETER_VALUE MIN,-8.0E-02V", -0.08),
            ("MIN,3120mV", 3.12),
            ("3120000uV", 3.12),
            ("MIN,120µV", 0.00012),
            ("MIN,120nV", 0.00000012),
            (" 3.12 \r\n", 3.12),
            ("MIN,+3.12V,OK", 3.12),
        ):
            with self.subTest(reply=reply):
                self.assertAlmostEqual(reader.parse_voltage(reply, "MIN"), expected)

    def test_invalid_measurements(self):
        for reply in ("", "NaN", "INF", "1e999V", "9.9e37V", "UNDEF",
                      "C2:PAVA MIN,3.12V", "C1:PAVA RMS,3.12V", "MIN,3.12S",
                      "MIN,3.12V,INVALID", "MIN,3.12V,junk"):
            with self.subTest(reply=reply), self.assertRaises(ValueError):
                reader.parse_voltage(reply, "MIN")

    def test_fragmented_replies_and_exact_queries(self):
        connections = [self.fake_socket([f"C1:PAVA {name},3.".encode(), b"12V\r\n"])
                       for name in reader.MEASUREMENTS]
        self.connect.side_effect = connections
        result = reader.read_measurements("example.invalid", 5025)
        self.assertEqual(result, {"min_v": 3.12, "mean_v": 3.12,
                                  "rms_v": 3.12, "droop_mv": 0.0})
        for connection, name in zip(connections, reader.MEASUREMENTS):
            connection.sendall.assert_called_once_with(f"C1:PAVA? {name}\n".encode())
        self.connect.assert_called_with(("example.invalid", 5025), timeout=3.0)

    def test_transport_errors(self):
        for chunks in ([b""], [b"MIN,3.12V", b""], [b"x" * 1024] * 4,
                       [b"MIN,3.12V\nextra"], [b"\xff\n"], [socket.timeout("timed out")]):
            self.connect.side_effect = None
            self.connect.return_value = self.fake_socket(chunks)
            with self.subTest(chunks=chunks), self.assertRaisesRegex(RuntimeError, "C1:PAVA"):
                reader.query("example.invalid", 5025, "MIN")

    def test_total_response_deadline(self):
        self.connect.side_effect = None
        self.connect.return_value = self.fake_socket([b"M"])
        with patch.object(reader.time, "monotonic", side_effect=[0, 4]):
            with self.assertRaisesRegex(RuntimeError, "deadline exceeded"):
                reader.query("example.invalid", 5025, "MIN")

    def test_cli_text_json_and_mean_based_droop(self):
        for flags in ([], ["--json"]):
            output = io.StringIO()
            with patch.object(reader, "query", side_effect=[3.12, 3.19, 3.19]) as query:
                with contextlib.redirect_stdout(output):
                    self.assertEqual(reader.main(["--host", "example.invalid", "--port", "5000"] + flags), 0)
                query.assert_any_call("example.invalid", 5000, "MIN")
            if flags:
                values = json.loads(output.getvalue())
                self.assertEqual(set(values), {"min_v", "mean_v", "rms_v", "droop_mv"})
                self.assertAlmostEqual(values["droop_mv"], 70)
            else:
                self.assertEqual(output.getvalue(),
                                 "MIN=3.120 V  MEAN=3.190 V  RMS=3.190 V  DROOP=70 mV\n")

    def test_cli_error_has_no_partial_output(self):
        self.connect.side_effect = ConnectionRefusedError("connection refused")
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            self.assertEqual(reader.main([]), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("192.168.1.170:5025, C1:PAVA? MIN", error.getvalue())

    def test_invalid_port_does_not_connect(self):
        for port in ("0", "65536", "abc"):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                reader.main(["--port", port])
        self.connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
