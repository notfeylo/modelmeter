"""Regression tests for the local HTTP trust boundary and static asset root."""
import socket
import threading
import unittest
from datetime import datetime, timedelta, timezone

from tallybeam.app import Handler, LocalHTTPServer, import_counter
from tallybeam.collector import number, timestamp


class LocalHTTPSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = LocalHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=3)
        cls.server.server_close()

    def request(self, target, *, host=None, extra=b"", method="GET", body=b""):
        host = f"127.0.0.1:{self.port}" if host is None else host
        message = (f"{method} {target} HTTP/1.1\r\nHost: {host}\r\n".encode()
                   + extra + f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode() + body)
        with socket.create_connection(("127.0.0.1", self.port), timeout=3) as connection:
            connection.sendall(message)
            response = bytearray()
            while chunk := connection.recv(65536):
                response.extend(chunk)
        return bytes(response)

    def test_valid_local_host_serves_health_and_assets(self):
        self.assertIn(b" 200 ", self.request("/api/health").split(b"\r\n", 1)[0])
        page = self.request("/")
        self.assertIn(b" 200 ", page.split(b"\r\n", 1)[0])
        self.assertIn(b"frame-ancestors 'none'", page)
        self.assertIn(b"object-src 'none'", page)

    def test_rejects_dns_rebinding_hosts(self):
        for host in ("attacker.example", f"attacker.example:{self.port}", "127.0.0.1", f"localhost:{self.port}"):
            with self.subTest(host=host):
                self.assertIn(b" 403 ", self.request("/api/health", host=host).split(b"\r\n", 1)[0])
        duplicate = self.request("/api/health", extra=b"Host: attacker.example\r\n")
        self.assertIn(b" 403 ", duplicate.split(b"\r\n", 1)[0])

    def test_rejects_cross_site_requests_before_processing(self):
        body = b"{}"
        headers = b"Origin: http://attacker.example\r\nContent-Type: application/json\r\n"
        response = self.request("/api/refresh", method="POST", extra=headers, body=body)
        self.assertIn(b" 403 ", response.split(b"\r\n", 1)[0])
        response = self.request("/api/health", extra=b"Sec-Fetch-Site: cross-site\r\n")
        self.assertIn(b" 403 ", response.split(b"\r\n", 1)[0])

    def test_rejects_windows_path_traversal(self):
        for target in (r"/assets/..\..\app.py", r"/assets/..\index.html",
                       "/assets/%2e%2e%5c%2e%2e%5capp.py", "/assets/../index.html"):
            with self.subTest(target=target):
                self.assertIn(b" 404 ", self.request(target).split(b"\r\n", 1)[0])

    def test_post_requires_one_unambiguous_content_length(self):
        response = self.request("/api/refresh", method="POST", extra=b"Content-Length: 2\r\nContent-Type: application/json\r\n", body=b"{}")
        self.assertIn(b" 400 ", response.split(b"\r\n", 1)[0])
        response = self.request("/api/refresh", method="POST", extra=b"Transfer-Encoding: chunked\r\nContent-Type: application/json\r\n", body=b"{}")
        self.assertIn(b" 400 ", response.split(b"\r\n", 1)[0])

    def test_import_counters_reject_invalid_or_unsafe_values(self):
        self.assertEqual(import_counter("123"), 123)
        for value in (-1, True, 1.5, float("inf"), "1e300", "9" * 200,
                      9_007_199_254_740_992):
            with self.subTest(value=str(value)[:30]), self.assertRaises(ValueError):
                import_counter(value)
        self.assertEqual(number(float("inf")), 0)
        self.assertIsNone(timestamp("0001-01-01T00:00:00Z"))
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        self.assertIsNone(timestamp(future))


if __name__ == "__main__":
    unittest.main()
