# Shared batch work and cache scope

`review(manifest, batch_limits=BatchLimits(...))` opts in. Defaults are 100,000
work units, 100,000 input nodes, 8,000,000 input bytes, 2,000 cache entries,
8,000,000 cache bytes and 16,000,000 result-payload bytes. Work may be zero;
other bounds are positive integers. Original per-direction `Limits` still
apply, including schema expansion, numeric literals and candidate budgets.
The CLI's existing 1,000,000-byte input-file cap remains in effect; SDK input
uses the explicit aggregate budget. The CLI opts in with `--batch-max-work`.

Before core work, the full batch shape and unique operation IDs are validated.
The opt-in raw JSON traversal counts values and object keys, repeated container
occurrences, cycles and depth. Its depth cap is `Limits.max_depth * 2 + 4` for
the manifest wrappers. Numeric literals use the existing digit/exponent limits
before decimal-string conversion. Non-JSON/cyclic/nonfinite input is INVALID;
input resource exhaustion returns complete UNKNOWN/BLOCK operation results.
Input bytes count exact ASCII JSON from `dumps`, including escaped Unicode.
An input-limit result records zero input counters because traversal did not
complete; it does not imply an empty caller-owned input.

Legal increases to `Limits.max_depth` are preserved, but do not guarantee that
Python can recurse that far. Stack exhaustion during the batch's input scan,
typed identity, result conversion or detached copy returns
`batch_recursion_limit`, complete directional UNKNOWN results and BLOCK. The
input-scan case makes no core calls. An interrupted later check drops its
certificate; earlier completed checks retain theirs. The core comparison call
is outside these narrow tree-transform guards, so unexpected engine errors are
not hidden as budget exhaustion.

Serialized result payloads use a depth of `2 * Limits.max_depth + 8`, allowing
the configured nested witness plus its result envelope. They continue to count
the same exact bytes against cache/result storage budgets. Expected transport
depth exhaustion returns `batch_result_depth_limit`; no truncated witness is
certified. Input and result payload depth bounds do not raise the interpreter's
stack limit or guarantee support for arbitrarily deep schemas.

Work charges one unit **before** each:

- cache lookup (including identity calculation) and successful store attempt;
- compiler expansion and recursive sufficient-proof entry;
- search entry and proposed candidate attempt, including rejected/duplicate
  candidates and nested child search;
- independent metaschema check, reference-root creation, each encountered
  reference lookup, and source/target membership call.

`work_by_kind` reports these categories; `work_used` never exceeds `max_work`.
Core comparison counts include a call stopped inside its preflight; they do not
promise a completed certificate. Cache hits still consume lookup work. Once
any bound halts a review, even a remaining cached pair receives UNKNOWN. The
partially evaluated direction retains no proof, wire or membership certificate.
Completed earlier results remain unchanged and counts cover every direction.
Per-result `batch.evaluated` means a completed retained result (which can itself
be UNKNOWN/INVALID), rather than a core-call attempt; top-level core-call and
work counters retain attempts interrupted before completion.

Cache bytes sum exact serialized result payload bytes plus the two 64-character
fingerprints and direction text. Result bytes sum serialized completed result
payloads for each occurrence, before operation provenance is attached. These
are accounting bounds, **not** Python heap or whole-output-byte bounds. UNKNOWN
fallback and provenance/report envelopes, key-set objects, serialization
temporaries and deep copies have overhead. Operation count is bounded by the
existing `Limits.max_nodes`; total caller-supplied strings/trees are subject to
the aggregate input bounds after shape checking. Shape/ID validation, hashing,
JSON emission, copying and backend internals are not separately charged per
instruction. There is no OS memory/CPU/wall-clock sandbox.

Cache identity includes full original documents, direction, sorted object keys
and ordered arrays, with distinct scalar types and exact JSON wire spelling.
Decimal trailing zeros/exponents and negative zero are preserved; bool and int
cannot collide. Float means the caller's existing Python wire spelling. The
cache does not normalize an invalid schema into a valid one, and never removes
metaschema, reference preflight or witness validation from a cache miss.
Results are deep-copied per operation. Later calls get a fresh cache. Concurrent
caller mutation during one call is unsupported.

## Executed synthetic observations

Observed locally with ordinary LF-archive-installed wheels on Windows/Python
3.14.3, jsonschema 4.26.0 / referencing 0.37.0. These are authored inputs, not
customer traffic. The baseline is 63eb34a (0.1.1); first implementation aab4ec0
and shape-resource correction dfe86cb. Core comparison bytes are the same
between those two implementation commits except malformed shape short-circuit.

Each of 100 operations has request/response old `{type:string,minLength:500}`
and new `{const:"x"}`; distinct mode increments minLength. Per-direction limits
are 20 candidates and 16 instance units, intentionally retaining UNKNOWN for
the unsearchable old string direction and BREAKING with wire `"x"` in response.

| Complete review | Old repeated | Shared repeated | Old distinct | Shared distinct |
| --- | ---: | ---: | ---: | ---: |
| Actual comparisons | 200 | 2 | 200 | 200 |
| Compiler expansions | 400 | 4 | 400 | 400 |
| Proof/search entries, each | 200 | 2 | 200 | 200 |
| Independent membership calls | 200 | 2 | 200 | 200 |
| Median ms, three samples | 93.091 | 21.267 | 86.588 | 119.375 |
| Whole-review Python traced peak, first run B | 1,466,503 | 1,856,611 | 1,321,781 | 3,283,186 |

Shared repeated work is 224 units with 198 hits and two entries; distinct work
is 2,600 units with zero hits and 200 entries. At an 80-unit budget, 100 distinct
operations make seven core calls (the last stops early), retain three BREAKING
and 197 UNKNOWN checks, and BLOCK. No remaining direction becomes ALLOW.

A separate memory probe measured retained cache object graphs of 6,045 B for
two entries and 353,507 B for 200 entries. This is reachable object size at
return (the retained cache only grows), not a cache-only allocation peak.
That run's whole-review traced peaks were 1,842,304 / 4,375,598 B; its Windows
process lifetime peak RSS was 38,789,120 / 44,273,664 B, including imports,
previous samples and tracemalloc. RSS cannot be attributed to the cache alone.
Small one-operation complete reviews were also slower: old/shared repeated
0.87/2.12 ms and distinct 1.06/1.13 ms. Timing/heap samples vary by environment.
Input precheck, hashing and detached copying add work; cache benefit requires
repeated pairs. There is no general speed or memory improvement claim.

The shape-resource regression used a malformed operation with 100,003 keys.
The first implementation allocated a 4,195,768 B key set before rejection;
the correction first checks field count and used 1,176 B. Caller input was
constructed before measurement. Both results are INVALID, with no core check.

Run `python benchmarks/batch_work.py --batch-work 100000 --out new-result.json`
for actual counts, complete-entry timings, whole-review tracemalloc, retained
cache size and Windows RSS. Omitting the shared option preserves the original
behavior; use a new output name per run. `--operations 1` exposes overhead and
`--batch-work 80` exposes aggregate exhaustion. These bounds are application
contracts; hostile inputs still need an externally limited worker.
