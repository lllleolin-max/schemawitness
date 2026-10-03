# Supported contract and failure boundaries

Dialect: JSON Schema 2020-12. Absence of `$schema` assumes this dialect; any
different explicit value returns UNKNOWN. The implementation intentionally
supports less than the complete dialect and checks reachable schemas.

Supported assertions: boolean schemas; `type` (including unions); `enum`;
`const`; inclusive/exclusive numeric bounds; `minLength`/`maxLength` in Unicode
code points; `properties`, `required`, schema/boolean `additionalProperties`;
homogeneous `items`, `minItems`/`maxItems`; `allOf`; nonrecursive same-document
JSON Pointer `$ref`, including `$defs`. `$ref` siblings are intersected.

URI-fragment separators may be percent encoded. Decoding occurs exactly once
semantically before JSON Pointer tilde handling: `%252F` names a literal `%2F`
key, whereas `~1` names a slash inside one key. UTF-8 names and `~0` tilde names
are supported. The independent dependency receives a canonical lookup URI
through a resolver adapter; the original schema and literal data are unchanged.
Encountered references are independently resolved before a proof is returned,
so a backend lookup failure cannot produce an inclusion certificate. Actual
search/console paths for both encodings are regression-tested.

Annotations ignored for validation: title, description, default, examples,
deprecated, readOnly, writeOnly, `$comment`. This does not implement OpenAPI
readOnly/writeOnly field projection; callers must supply the effective
directional schema. Missing properties/items/additionalProperties mean true.
An optional impossible property can never appear; a required impossible
property makes the object branch empty. `items:false` permits the empty array.
Other type branches are unaffected by object/array/string/numeric keywords.

Unsupported assertions/vocabularies return UNKNOWN with a JSON Pointer and
code, including anyOf/oneOf/not/if, pattern, format, multipleOf, tuple arrays,
contains, uniqueItems, propertyNames, patternProperties, dependencies,
min/maxProperties, unevaluated keywords, `$id`, anchors and external/dynamic
references. Recursive references return `recursive_reference`. Unused `$defs`
do not assert anything; their syntax is still checked by the metaschema.
Invalid supported keyword values and dangling pointers return INVALID.

Numeric schema literals are exact ints/Decimal, with default maximum 256
coefficient digits and absolute decimal exponent 1024; exceeding these gives
UNKNOWN, never rounding. These are implementation resource limits, **not** a
claim that the normative numeric universe stops there. Inclusion rules reason
over unbounded mathematical integers and real numbers; decimal witnesses are
constructed exactly. `1`, `1.0`, and `1e0` are equal numbers and all integers;
booleans are different. jsonschema is used independently on the original
schemas, with its integer type predicate extended to exact Decimal integers.
Integral Decimal instances are represented by equivalent mathematical ints
inside that validator to preserve integer semantics when it switches dialect
classes while resolving references. No schema assertions/data are transformed.
No floating-point epsilon is used to prove inclusion. Search boundary offsets
are finite decimal rationals.

`independent_validate` is a membership helper for validated supported schemas
and transported JSON values. Its `valid` is true/false only after successful
evaluation; a dependency failure returns `valid:null` with
`independent_validator_failure`. Callers must use explicit true/false tests.
compare emits UNKNOWN and no witness/proof if independent lookup/evaluation
fails. Unsupported/invalid schemas still follow the explicit compiler statuses;
valid encoded pointers are supported and do not use this failure fallback.

Defaults: 1 MB documents/witness wires, 2,000 expanded schema nodes, expansion depth 32,
2,000 generated candidates, 128 units per candidate container/string; 32 child
variants, 8 MB cumulative candidate encoding size including child variants.
`Limits` exposes these budgets to the SDK. Search truncation/reasons and
metrics are explicit. Raising a limit trades CPU/memory for additional
counterexamples; it does not convert a bounded search into a proof. CLI exposes
candidate/instance limits and proof/search ablations.

Wire encoding enforces byte/depth budgets incrementally, before allocating a
complete oversized output, including strings and repeated nested containers.
Before deduplication, a capped exact size estimator memoizes shared containers
and rejects oversized candidates without expanding their complete key tree.
Source candidate validation memoizes repeated container/schema pairs so shared
array fillers do not cause exponentially repeated checks before serialization.
These are application budgets, not OS memory/wall-clock limits.

The proof is intentionally sufficient, not complete. Equivalent finite
non-enum shapes and some structurally redundant constraints may remain UNKNOWN.
UNKNOWN blocks the release workflow and should prompt a broader checker,
contract tests, or human review. Generated examples may contain synthetic
values unrelated to actual provider traffic.
