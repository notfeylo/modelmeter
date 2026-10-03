# Local discovery and usage intelligence

Modelmeter separates **installed**, **used**, and **limit known**. These are different facts.

## Discovery

The Python discovery module asks a running Ollama service for `/api/tags` and a running LM Studio service for `/api/v0/models`, both on loopback with short timeouts. It also checks the current user's Ollama manifests, LM Studio model folder, and Hugging Face model cache. Results are bounded to 500 models. No remote model catalog is bundled or downloaded, and no whole-drive crawl runs. The inventory is cached for one minute and can be rescanned in Connections. A model in this list is installed or cached; it has **zero implied token usage**.

Obsidian vault paths come from its local vault registry. Modelmeter samples recent Claude Code and Codex session headers for a working directory inside a vault and labels an observed link. It does not read vault notes, infer an agent link from a note, or add note text to token usage. A missing link means none was seen in the sampled sessions.

## Recorded counts and limits

Claude Code, Codex CLI, Gemini CLI, and OpenCode usage comes from recorded response metadata, including chat-only turns when those tools write token counters. A file edit is not required. Browser chats and any tool interaction that writes no accessible usage record remain outside the measured totals. The heatmap shows every bucket with a positive recorded counter; the dashboard polls visible windows every 30 seconds and scans changed source files.

Codex 5-hour usage and reset are displayed only when present in its local rate-limit records. Claude Code can pass its reported 5-hour and weekly windows through the optional status-line companion. That snapshot expires from the dashboard after ten minutes. Other observed providers appear with **limit unavailable** until a supported source actually supplies a limit. A downloaded local model does not have a cloud subscription reset. Modelmeter does not read account cookies or extrapolate provider balances from token totals.

## Python intelligence

`tallybeam/intelligence.py` builds an evidence index from 90 days of recorded provider, model, and day totals. Asking a question retrieves matching aggregate facts and returns their IDs and exact counters. If the user explicitly selects an installed Ollama model, the retrieved facts and question are sent only to that local Ollama server for a short explanation. The generated answer is labeled and the supporting facts remain visible. It can still make a language error, so the counters and cited evidence remain authoritative.

The small neural regressor has one hidden layer and trains from local daily totals. It predicts the current day's usage based on prior daily usage and weekly rhythm. It is **advisory**, never a measured token count or quota. The final seven complete days are held out and compared with a previous-week baseline. If the neural prediction does not beat that baseline, or there is too little history, Modelmeter shows no forecast. It retrains from current local aggregates when insights refresh; it does not update the collector or rewrite historical counts.

This is a bounded local retrieval-and-generation feature, not a way to reconstruct missing provider telemetry. For precise totals, the provider or tool must record counters or supply a usage export.
