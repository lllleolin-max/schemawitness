# Calculus, search, transport, release review

1. Exact JSON roundtrip canonicalizes SDK input. A tree preflight checks numeric
   literals/resource limits. The independent 2020-12 metaschema checks syntax.
2. The compiler expands bounded local references and intersections into a
   product shape: disjoint type atoms (integer and noninteger numeric branches),
   finite enumeration, intervals, string/array lengths, per-property constraints,
   required keys, additional-property and item constraints.
   It records encountered URI spellings; an independent referencing lookup of
   those original-document targets runs before any inclusion certificate.
3. A sufficient recursive inclusion calculus can emit COMPATIBLE. If it cannot,
   a separate boundary-guided search generates source-valid candidate values.
4. Every proposed witness is serialized exactly and reparsed. An independent
   jsonschema validator checks the original source and target assertions after
   transport. Only source-valid/target-invalid evidence emits BREAKING.
5. Release review checks both directions for every manifest operation and
   allows release only if every directional result is proven COMPATIBLE.

The independent resolver adapter changes only a local reference URI passed to
lookup: decode its fragment, then re-encode it with literal pointer separators.
The dependency resolves the original target and jsonschema applies its original
assertions. This preserves literal percent/Unicode names and every const/enum
value, including a node used simultaneously as literal data and a reference
target. The adapter travels with the resolver during validator evolution;
integral-instance representation preserves integer semantics across classes.
It uses jsonschema's private `_resolver` constructor seam plus referencing's
documented resolver methods. Dependency changes can affect that seam; actual
installed-version tests and structured UNKNOWN failure handling cover it.

## Why the proof rules are sound

Types are disjoint; type-specific keywords affect only their own branch. Empty
branches have no obligations. Intersections combine type sets, enum equality,
tighter intervals, required unions and the intersection of each field's
effective schema. A property absent from a `properties` map uses that schema's
additionalProperties constraint: this matters when intersecting closed shapes.

For finite source enum, exhaustively filter source-valid values and check every
one against the target's normalized constraints. For a non-enum source, each
nonempty atom must be allowed by the target. Numeric and string/array bounds
must be within target bounds (integer bounds use exact ceil/floor). Nonempty
arrays require item inclusion, except an empty-only source. Objects require
every target-required name in the source-required set, every named effective
property included, and inclusion of the generic additional-property branch.
Empty-source, universal-target and identical-normal-form rules are immediate.
These rules never infer compatibility from a candidate count.

The finite oracle independently enumerates scalar/array/object values over a
small grid, executes every schema pair and falsifies unsound positive proofs.
It is useful testing evidence, not a mathematical proof of all implementations.
The witness verifier also does not turn an unsupported schema into a supported
proof. No universal JSON Schema implication solver is claimed.

## Complexity and operations

Without refs, normalization is proportional to the expanded schema plus
property intersections. Reused references can cause repeated expansion;
max_nodes/depth bound this work. Inclusion traverses the expanded product tree,
with enum equality/filtering and effective-field unions. The straightforward
enum intersection is quadratic in enum lengths. Candidate search is capped by
the global generation budget, with child variant caps; independent validation
cost scales with candidate size and expanded assertions. Its order is
deterministic, independent of property-map input order. Manifests process
operations sequentially; per-operation budgets do not constitute an OS sandbox
or a wall-clock timeout. Run hostile inputs in a separately limited worker.

The `--no-proof` ablation retains counterexamples but leaves safe widening
UNKNOWN; `--no-search` retains proofs but leaves failing inclusion UNKNOWN.
Keeping them separate makes both kinds of evidence operationally meaningful.
