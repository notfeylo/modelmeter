# Data source notes

Modelmeter's provider claims are intentionally narrow.

- [Gemini CLI session management](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/session-management.md) documents saved sessions with token usage in `~/.gemini/tmp/<project_hash>/chats/`.
- [Gemini CLI configuration](https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md) documents `GEMINI_CLI_HOME` as the user storage root.
- [Claude Code environment variables](https://code.claude.com/docs/en/env-vars) documents `CLAUDE_CONFIG_DIR` as the configuration and session-history root.
- [Codex source](https://github.com/openai/codex/blob/main/codex-rs/core/src/session_rollout_init_error.rs) identifies the `sessions` subfolder of Codex home. Modelmeter also checks `CODEX_HOME/sessions` when that variable is set.
- [Codex rollout source](https://github.com/openai/codex/blob/main/codex-rs/rollout/src/lib.rs) identifies both `sessions` and `archived_sessions` subfolders. Modelmeter reads both and deduplicates matching usage records.
- [Antigravity agent settings](https://antigravity.google/docs/agent-settings) describes a local app data area for artifacts and knowledge items, not a documented token-counter log. Modelmeter does not infer token counts from those files.
- [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) explains that limits vary by model and project, and are shown in Google AI Studio. A Gemini CLI session is not an account quota API.
- [xAI Usage Explorer](https://docs.x.ai/console/usage) provides token usage in the xAI Console. Modelmeter imports an export; it does not claim an API token can retrieve all Grok consumer usage.
- [xAI Management API guide](https://docs.x.ai/developers/management-api-guide) distinguishes management keys from inference keys.
- [OpenAI organization usage API](https://platform.openai.com/docs/api-reference/usage/completions) concerns API organization usage, which is separate from a Codex subscription. Modelmeter currently reads Codex CLI session telemetry instead.
- [Anthropic usage report](https://docs.anthropic.com/en/api/admin-api/usage-cost/get-messages-usage-report) concerns organization API usage and requires an Admin API key. Modelmeter currently reads Claude Code session telemetry instead.

The visual references in the brief informed the activity map, token breakdown, trend, and session detail structure. No code or assets were copied from the reference repositories.
