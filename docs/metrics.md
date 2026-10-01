# Metrics

- **Total tokens** sums each source's recorded input, output, reasoning, cache-read and cache-write counters. It is usage metadata, not a billing balance.
- **Active tokens** are input, output and reasoning tokens excluding cache counters.
- **Responses** counts normalized assistant usage records. It is a request activity proxy; tools differ in how they emit records.
- **Runtime** uses OpenCode's `time.created` and `time.completed` interval when both exist. Child session runtime is omitted to avoid double counting. Other source formats do not currently provide compatible intervals, so their runtime remains unavailable.
- **Deduplicated runtime** merges overlapping intervals for the selected scope. It is no greater than raw runtime and can be smaller when sessions overlap.
- **Cache hit rate** is `cache_read / (input + cache_read + cache_write)`. Cache writes are included in the denominator because a write is not a hit.
- **Estimated cache miss tokens** compares consecutive nonzero assistant usage records within the same session and cache namespace. A pair is counted only when the previous record had `cache_read > 0`, the model and provider are unchanged, and no recorded OpenCode compaction occurred between them. `expected = previous total`; `miss = max(0, expected - current cache_read)`. Provider caches and billing are not directly observable, so this is an estimate rather than a charge or proof of provider behavior.

Seven-day trend data uses one-hour buckets with missing hours filled as zero. Longer trend ranges use daily buckets. The heatmap uses two-hour buckets through 90 days and daily buckets beyond that. Date buckets follow the computer's local timezone.
