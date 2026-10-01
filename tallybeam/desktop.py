"""Windows tray launcher for the locally hosted dashboard."""
from __future__ import annotations

import json
import threading
import webbrowser
from importlib.resources import files
from urllib.request import urlopen

from .app import Handler, LocalHTTPServer


def existing_dashboard(port=8765):
    """Open an already running copy only after checking its identity."""
    url = f"http://127.0.0.1:{port}"
    try:
        with urlopen(f"{url}/api/health", timeout=1) as response:
            health = json.load(response)
        if health.get("ok") is True and health.get("service") == "tallybeam":
            return url
    except (OSError, ValueError, TypeError):
        pass
    return None


def main():
    from PIL import Image
    from pystray import Icon, Menu, MenuItem

    try:
        server = LocalHTTPServer(("127.0.0.1", 8765), Handler)
    except OSError:
        existing = existing_dashboard()
        if existing:
            webbrowser.open(existing)
            return
        server = LocalHTTPServer(("127.0.0.1", 0), Handler)

    url = f"http://127.0.0.1:{server.server_port}"
    with (files("tallybeam") / "static" / "tray.png").open("rb") as image_file:
        image = Image.open(image_file).copy()

    threading.Thread(target=server.serve_forever, daemon=True).start()

    def quit_app(icon, _item):
        server.shutdown()
        icon.stop()

    icon = Icon(
        "Tallybeam", image, "Tallybeam",
        Menu(MenuItem("Open dashboard", lambda _icon, _item: webbrowser.open(url), default=True),
             MenuItem("Quit Tallybeam", quit_app)),
    )

    def ready(current_icon):
        current_icon.visible = True
        webbrowser.open(url)

    try:
        icon.run(setup=ready)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
