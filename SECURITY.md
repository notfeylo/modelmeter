# Security policy

The latest Modelmeter release is the supported version. Upgrade to 0.7.1 or later before testing a suspected vulnerability in the local dashboard server.

Report a vulnerability through the repository's **Security → Advisories → Report a vulnerability** flow. Include the affected version, impact, and a minimal reproduction. Please do not post exploit details, local file contents, account data, or credentials in a public issue. If the private reporting option is unavailable, open a public issue asking for a private contact channel without including the exploit.

Modelmeter reads local usage files and runs a local HTTP service. Treat its dashboard and exported data as private to the computer's user account. It does not provide isolation from another malicious process already running as that same user. See [security design and verification](docs/security.md).
