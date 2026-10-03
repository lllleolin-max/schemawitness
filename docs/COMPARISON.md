# Primary sources and executable distinction

Primary-source verification date: 2026-10-03.

- [JSON Schema 2020-12 Core](https://json-schema.org/draft/2020-12/json-schema-core)
  defines references as applicators and permits siblings; the
  [Validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
  defines numeric/integer semantics and explicitly leaves precision unbounded.
- [oasdiff breaking changes](https://www.oasdiff.com/docs/breaking-changes) and
  [request required-property rule](https://www.oasdiff.com/checks/request-property-became-required)
  already implement directional API compatibility rules. Its current
  [release notes](https://www.oasdiff.com/whats-new) describe substantial schema
  and reference handling. SchemaWitness does not replace its broad OpenAPI
  change catalog or claim it lacks counterexample features.
- [Pact specification](https://docs.pact.io/implementation_guides/pact_specification)
  and [provider verification](https://docs.pact.io/implementation_guides/javascript/docs/provider)
  provide established consumer-driven executable contracts. SchemaWitness
  generates schema-level fixtures; it does not execute a provider or discover
  consumers' real expectations.
- [python-jsonschema validation API](https://python-jsonschema.readthedocs.io/en/stable/validate/)
  supplies the independent 2020-12 validator and type-checker extension API.

The engineering combination is a sound sufficient inclusion result, a separate
bounded witness result, exact post-wire independent validation, and a fail-closed
multi-operation review. The claim is falsifiable: any COMPATIBLE with a source
value invalid under the target, or any emitted non-discriminatory wire value,
is a defect. This is not a scientific novelty or incumbent superiority claim.

Run `python benchmarks/compare.py`: 12 disclosed synthetic cases compare an
executed root-only directional diff with the full engine, search-only and
proof-only. The shallow baseline correctly handles required root properties
and simple numeric changes; it ignores nested assertions/references, equates
Python bool/number enum membership and assumes no detected changes are safe.
That deliberately limited baseline models shallow manual review, not oasdiff.
The corpus includes cases where it succeeds and fails, safe widening, empty
schemas, exact decimals and unsupported assertions. It is not representative
traffic or a statistical estimate of production error rates. Timings are actual
wall time on the current run, not a cross-machine performance promise.

Expected result counts are checked by the benchmark itself. Exact measured
outputs and review evidence are recorded in ITERATIONS.md at the frozen build.
