# Architecture

Tallybeam runs entirely on the local machine. The Python standard-library HTTP server binds to `127.0.0.1` and serves the prebuilt React dashboard and JSON API. The React, TypeScript, Tailwind and Recharts source is under `frontend/`; `npm run build` writes static assets into `tallybeam/static/`. Python can run those committed assets without Node installed. The optional Rust program in `rust-indexer/` only accelerates local file discovery.

Local collectors read Claude Code, Codex CLI, Gemini CLI and OpenCode usage metadata. OpenCode SQLite files are opened read-only. V1 `message` and V2 `session_message` data are selected by the table with more rows, so migration residue in the other table is not counted twice. Session metadata resolves from both `session` and `session_v2`; child sessions contribute tokens but not runtime. An explicit `OPENCODE_DB_PATH` limits OpenCode collection to one database. CSV imports are saved to `~/.tallybeam/tallybeam.sqlite3`. No prompts, responses, API keys or cookies are stored or returned by the API.

The server keeps a short in-memory snapshot of normalized usage events. `/api/usage` aggregates that snapshot into day or hour buckets, model/provider totals, heatmap data and runtime. `/api/cache-miss/sessions` and `/api/cache-miss/session/{id}` expose only token counters and timestamps for the drilldown. The frontend fetches JSON from the same origin, so no remote service or CORS setting is needed.

The source layout follows the reference dashboard's component, hook and i18n organization while separating the Python runtime and optional Rust indexer:

```text
tallybeam/
├── frontend/src/components/     dashboard cards, charts and dialogs
├── frontend/src/hooks/          API hooks
├── frontend/src/lib/i18n/       English and Chinese labels
├── tallybeam/                   Python collectors, aggregation and server
├── tallybeam/static/            committed production UI bundle
├── rust-indexer/                optional Rust file discovery
├── tests/                       collector and aggregation tests
└── docs/                        architecture and metric definitions
```
