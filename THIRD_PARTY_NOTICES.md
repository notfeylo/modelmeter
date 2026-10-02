# Third-party notices

The dashboard layout, chart components, styling patterns, and cache lifecycle presentation are adapted from [heimoshuiyu/opencode-token-dashboard](https://github.com/heimoshuiyu/opencode-token-dashboard), commit `0b4242fd7bba6c84e28c68464a6dd65eac05b7f3`. Its README identifies the project as MIT licensed. Copyright remains with its original contributors. Tallybeam changes the branding and font, connects the interface to its Python local-source collectors, and omits the upstream prompt-content view.

Space Grotesk is distributed through `@fontsource-variable/space-grotesk`; other frontend dependencies and licenses are recorded in `frontend/package-lock.json`.

The Windows application bundles Python, the PyInstaller bootloader, and a Tauri desktop shell that uses the installed Microsoft WebView2 runtime. Pillow is used to generate the icon at build time. Their licenses and source are available from [Python](https://www.python.org/downloads/), [PyInstaller](https://github.com/pyinstaller/pyinstaller), [Tauri](https://github.com/tauri-apps/tauri), [WebView2](https://learn.microsoft.com/microsoft-edge/webview2/), and [Pillow](https://github.com/python-pillow/Pillow). The build script and Tallybeam source needed to rebuild the installer are included in this repository.

## MIT license for adapted upstream code

Copyright (c) contributors to `heimoshuiyu/opencode-token-dashboard`.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
