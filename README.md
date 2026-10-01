# Tallybeam

![Tallybeam logo](tallybeam/static/logo.svg)

A local dashboard for token usage across AI coding tools. It reads usage metadata from Claude Code, Codex CLI, and Gemini CLI sessions, and accepts CSV usage exports for Grok/xAI or other providers. It shows activity, trends, token breakdowns, model and provider shares, sessions, and any Codex rate-limit windows found in local telemetry.

## Run

Requires Python 3.10 or newer. No Python package dependencies are needed to run from source.

```powershell
python -m tallybeam.app
```

Open `http://127.0.0.1:8765`. Use `--port 9000` to choose a port or `--no-browser` to keep the browser closed.

### Optional Rust indexer

Rust speeds up file discovery in large session folders. The Python collector works without it.

```powershell
cargo build --release --manifest-path rust-indexer/Cargo.toml
$env:TALLYBEAM_INDEXER = (Resolve-Path rust-indexer/target/release/tallybeam-indexer.exe)
python -m tallybeam.app
```

On macOS or Linux use the `tallybeam-indexer` binary without `.exe`.

## Connections and what each can show

| Source | Connection | Token usage | Remaining/reset |
| --- | --- | --- | --- |
| Claude Code | Existing local sessions in `~/.claude/projects` | Yes | Subscription quota unavailable from local records |
| Codex CLI | Existing local sessions in `~/.codex/sessions` | Yes | Rate-limit percent and reset when recorded by Codex |
| Gemini CLI | Existing local sessions in `~/.gemini/tmp/*/chats` | Yes | Account quota unavailable from local records |
| Grok / xAI | CSV import | Yes, if supplied | Unavailable unless your own export contains it; not currently imported |

Tallybeam does **not** ask for account passwords, scrape browser cookies, or claim that an API key can reveal a personal subscription balance. API billing, coding-tool subscription limits, and token counts are different measures. Missing provider data is shown as unavailable.

## CSV import

Choose a CSV in **Connections**. Required headers: `provider,model,timestamp,input,output`. Optional headers: `cache_read,cache_write,session,id`. Use ISO 8601 timestamps and provider names `Claude`, `Codex`, `Gemini`, `Grok`, or `Other`. Reimporting rows with the same `id` replaces them; otherwise each row gets a file and row based ID. The browser sends the parsed data only to the local server. Imported usage is saved in `~/.tallybeam/tallybeam.sqlite3`.

Example:

```csv
provider,model,timestamp,input,output,cache_read,cache_write,session,id
Grok,grok-4,2026-10-01T12:00:00Z,1000,300,0,0,project-a,request-1
```

## Privacy

- The server binds to `127.0.0.1` only. There is no cloud account or telemetry.
- The collector parses local session files and keeps only usage metadata in memory. Prompts and responses are never served to the browser or saved by Tallybeam.
- Local-source toggles are stored in `~/.tallybeam/config.json`.
- `POST /api/import` accepts up to 5,000 rows and 2 MB per import. Browser requests from other origins are rejected.

## Develop and verify

```powershell
python -m unittest discover -s tests -v
node --check tallybeam/static/app.js
cargo test --manifest-path rust-indexer/Cargo.toml
```

The interface uses plain JavaScript and CSS with no build step. The Python server has no runtime dependencies. The optional Rust binary discovers candidate session files and never reads their contents.

## Known limits

- Local CLI session history can be deleted or rotated by its owner; Tallybeam can only show retained records.
- Token counts may differ from billing usage due to cache, tools, and provider accounting. Tallybeam uses the metadata stored by each tool.
- Gemini and Grok web/app usage is not automatically available through these local session sources.
- Source formats can change across tool versions. Please open an issue with a redacted sample of the usage metadata when a parser stops working.

## License

MIT. See [LICENSE](LICENSE).
