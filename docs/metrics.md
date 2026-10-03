# Metrics

- **Total tokens** sums each source's recorded input, output, reasoning, cache-read and cache-write counters. It is usage metadata, not a billing balance.
- **Active tokens** are input, output and reasoning tokens excluding cache counters.
- **Usage records** counts normalized nonzero token records. A tool may emit more than one record per response, so this is not a count of user messages or completed responses.
- **Runtime** uses OpenCode's `time.created` and `time.completed` interval when both exist. Child session runtime is omitted to avoid double counting. Other source formats do not currently provide compatible intervals, so their runtime remains unavailable.
- **Deduplicated runtime** merges overlapping intervals for the selected scope. It is no greater than raw runtime and can be smaller when sessions overlap.
- **Cache hit rate** is `cache_read / (input + cache_read + cache_write)`. Cache writes are included in the denominator because a write is not a hit.
- **Model filter** selects recorded events with the exact model identifier before totals, day buckets, provider share, and cache analysis are calculated. The available-model list comes from all local records, including records outside the current time range.
- **Provider filter** groups recorded source IDs under OpenAI, Anthropic, Google, xAI, Antigravity, or the original provider ID when it is not recognized. It then recomputes all charts and narrows the model list to that provider's recorded models. A provider with no records shows zero rather than borrowing another provider's data.
- **Activity heatmap** uses local timestamps of nonzero recorded token events. Every positive token bucket gets a visible cell, including a single token. It cannot show an interaction whose tool wrote no usage metadata.
- **Estimated cache miss tokens** compares consecutive nonzero assistant usage records within the same session and cache namespace. A pair is counted only when the previous record had `cache_read > 0`, the model and provider are unchanged, and no recorded OpenCode compaction occurred between them. `expected = previous total`; `miss = max(0, expected - current cache_read)`. Provider caches and billing are not directly observable, so this is an estimate rather than a charge or proof of provider behavior.

No machine learning or retrieval system is used to fill missing counters. Those methods cannot recover an exact token count from a file edit, prompt, or output artifact. The app reports recorded counts and labels the cache reuse calculation as an estimate.

The optional Python insight panel uses aggregate counter retrieval for answers and a validated neural model for an advisory current-day forecast. Neither output is added to any measured total, quota, or heatmap bucket. See [local intelligence](intelligence.md).

Seven-day trend data uses one-hour buckets with missing hours filled as zero. Longer trend ranges use daily buckets. The heatmap uses two-hour buckets through 90 days and daily buckets beyond that. Date buckets follow the computer's local timezone.
