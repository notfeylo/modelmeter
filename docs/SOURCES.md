# Data source notes

Tallybeam's provider claims are intentionally narrow.

- [Gemini CLI session management](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/session-management.md) documents saved sessions with token usage in `~/.gemini/tmp/<project_hash>/chats/`.
- [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) explains that limits vary by model and project, and are shown in Google AI Studio. A Gemini CLI session is not an account quota API.
- [xAI Usage Explorer](https://docs.x.ai/console/usage) provides token usage in the xAI Console. Tallybeam imports an export; it does not claim an API token can retrieve all Grok consumer usage.
- [xAI Management API guide](https://docs.x.ai/developers/management-api-guide) distinguishes management keys from inference keys.
- [OpenAI organization usage API](https://platform.openai.com/docs/api-reference/usage/completions) concerns API organization usage, which is separate from a Codex subscription. Tallybeam currently reads Codex CLI session telemetry instead.
- [Anthropic usage report](https://docs.anthropic.com/en/api/admin-api/usage-cost/get-messages-usage-report) concerns organization API usage and requires an Admin API key. Tallybeam currently reads Claude Code session telemetry instead.

The visual references in the brief informed the activity map, token breakdown, trend, and session detail structure. No code or assets were copied from the reference repositories.
