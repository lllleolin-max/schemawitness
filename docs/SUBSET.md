# Supported contract and failure boundaries

Dialect: JSON Schema 2020-12. Absence of `$schema` assumes this dialect; any
different explicit value returns UNKNOWN. The implementation intentionally
supports less than the complete dialect and checks reachable schemas.

Supported assertions: boolean schemas; `type` (including unions); `enum`;
`const`; inclusive/exclusive numeric bounds; `minLength`/`maxLength` in Unicode
code points; `properties`, `required`, schema/boolean `additionalProperties`;
homogeneous `items`, `minItems`/`maxItems`; `allOf`; nonrecursive same-document
JSON Pointer `$ref`, including `$defs`. `$ref` siblings are intersected.

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
booleans are different. jsonschema is used independently, with only its integer
type predicate extended to exact Decimal integers. No floating-point epsilon
is used to prove inclusion. Search boundary offsets are finite decimal rationals.

Defaults: 1 MB documents/witness wires, 2,000 expanded schema nodes, expansion depth 32,
2,000 generated candidates, 128 units per candidate container/string; 32 child
variants. `Limits` exposes these budgets to the SDK. Search truncation and
metrics are explicit. Raising a limit trades CPU/memory for additional
counterexamples; it does not convert a bounded search into a proof. CLI exposes
candidate/instance limits and proof/search ablations.

Wire encoding enforces byte/depth budgets incrementally, before allocating a
complete oversized output, including strings and repeated nested containers.
Source candidate validation memoizes repeated container/schema pairs so shared
array fillers do not cause exponentially repeated checks before serialization.
These are application budgets, not OS memory/wall-clock limits.

The proof is intentionally sufficient, not complete. Equivalent finite
non-enum shapes and some structurally redundant constraints may remain UNKNOWN.
UNKNOWN blocks the release workflow and should prompt a broader checker,
contract tests, or human review. Generated examples may contain synthetic
values unrelated to actual provider traffic.
