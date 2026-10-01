import threading
import unittest

from tallybeam.app import Handler, LocalHTTPServer
from tallybeam.desktop import create_server


class DesktopTests(unittest.TestCase):
    def test_health_identity_and_exclusive_port(self):
        server = LocalHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            desktop_server = create_server(server.server_port)
            self.assertNotEqual(desktop_server.server_port, server.server_port)
            desktop_server.server_close()
            with self.assertRaises(OSError):
                LocalHTTPServer(("127.0.0.1", server.server_port), Handler)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
