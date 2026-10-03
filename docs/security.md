# Security design and verification

## Trust boundaries

The desktop shell loads a Python dashboard server bound to `127.0.0.1`. The browser version uses the same local server. Loopback binding prevents direct access from another computer, but it does not by itself stop a malicious webpage from targeting local services. [Stanford's DNS rebinding research](https://crypto.stanford.edu/dns/) specifically calls for server-side `Host` validation. Modelmeter accepts only the exact `127.0.0.1:<listening-port>` host, rejects duplicate or foreign origins, and rejects browser requests labeled cross-site or same-site. JSON writes additionally require one valid content length and the expected content type. No CORS permission is granted. These checks run before reading usage data or changing settings.

The static route uses an exact allowlist for the entry page, logo, and single-segment asset filenames. It rejects Windows backslashes, encoded traversal strings, extra separators, and unsupported extensions. This prevents a URL path from reaching other files through the package resource loader.

The frontend displays model, provider, and session names as React text. Dynamic chart CSS accepts only safe identifier keys and fixed-format color tokens, and renders a text child in `<style>` instead of injecting raw HTML. The local server sets a Content Security Policy for scripts and frames, and sends `nosniff`, frame-denial, resource-policy, and referrer-policy headers. These are layered defenses consistent with [OWASP's XSS guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet) and [Tauri's CSP guidance](https://tauri.app/security/csp/).

The Tauri shell generates a fresh random startup nonce and passes it to its Python child through the process environment. It opens the webview only after the process on the selected port proves that it received that nonce. Navigation stays restricted to that exact port. This narrows the chance of a different local process winning the port race. The nonce is an identity check for startup, not an authentication system for other local processes.

Imported counters must be nonnegative integers inside a bounded range. Recorded timestamps must be within the supported period, and malformed local log structures are skipped. Small local configuration files have size limits. The local model connectors never follow HTTP redirects away from their loopback endpoints. Usage questions sent to an explicitly selected Ollama model contain aggregate counters and the question, not transcripts.

## Verification

Security regression tests cover hostile and duplicate `Host` headers, cross-site requests, Windows path traversal, ambiguous request framing, and malformed counters. The normal Python, frontend, Rust, wheel, installer, and installed desktop checks run before release. `npm audit` and `cargo audit` check dependency advisories. GitHub Actions use read-only repository permissions and full commit hashes for third-party actions.

These checks reduce known risk; they cannot prove the absence of every vulnerability. Modelmeter cannot protect data from malware already running with the same user's filesystem permissions. The Windows installer is currently unsigned, so users should verify its release hash before running it. Report new findings privately through [the security policy](../SECURITY.md).
