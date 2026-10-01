"""Native Windows window for the locally hosted dashboard."""
from __future__ import annotations

import ctypes
import sys
import threading
import time
from importlib.resources import files

from .app import Handler, LocalHTTPServer


WINDOW_TITLE = "Tallybeam"
MUTEX_NAME = "Local\\TallybeamDesktop"


def create_server(preferred_port=8765):
    """Keep desktop and command-line instances independent when needed."""
    try:
        return LocalHTTPServer(("127.0.0.1", preferred_port), Handler)
    except OSError:
        return LocalHTTPServer(("127.0.0.1", 0), Handler)


def _focus_existing_window():
    user32 = ctypes.windll.user32
    user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
    user32.FindWindowW.restype = ctypes.c_void_p
    user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    for _ in range(20):
        handle = user32.FindWindowW(None, WINDOW_TITLE)
        if handle:
            user32.ShowWindow(handle, 9)  # SW_RESTORE
            user32.SetForegroundWindow(handle)
            return
        time.sleep(0.1)


def _single_instance_handle():
    """Return a live Windows mutex handle, or focus the existing app."""
    if sys.platform != "win32":
        return None, True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        _focus_existing_window()
        _close_mutex(handle)
        return None, False
    return handle, True


def _close_mutex(handle):
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle(handle)


def main():
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMainWindow
    from PySide6.QtWebEngineWidgets import QWebEngineView

    mutex, should_launch = _single_instance_handle()
    if not should_launch:
        return

    server = None
    try:
        server = create_server()
        threading.Thread(target=server.serve_forever, daemon=True).start()

        app = QApplication(sys.argv)
        app.setApplicationName(WINDOW_TITLE)
        window = QMainWindow()
        window.setWindowTitle(WINDOW_TITLE)
        window.setWindowIcon(QIcon(str(files("tallybeam") / "static" / "tray.png")))
        view = QWebEngineView(window)
        window.setCentralWidget(view)
        window.setMinimumSize(800, 560)
        available = window.screen().availableGeometry()
        window.resize(min(1280, available.width()), min(900, available.height()))
        window.show()
        view.load(QUrl(f"http://127.0.0.1:{server.server_port}/"))
        app.exec()
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if mutex is not None:
            _close_mutex(mutex)


if __name__ == "__main__":
    main()
