import threading
import unittest

from tallybeam.app import Handler, LocalHTTPServer
from tallybeam.desktop import existing_dashboard


class DesktopTests(unittest.TestCase):
    def test_health_identity_and_exclusive_port(self):
        server = LocalHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            self.assertEqual(existing_dashboard(server.server_port), f"http://127.0.0.1:{server.server_port}")
            with self.assertRaises(OSError):
                LocalHTTPServer(("127.0.0.1", server.server_port), Handler)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
