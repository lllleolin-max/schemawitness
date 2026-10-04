# Changelog

## 0.2.0

- Optional `BatchLimits` shares expansion/proof/search/backend work across an
  API review and bounds input, pair-cache storage and retained result payloads.
- A per-call, direction-specific full-document cache preserves original scalar
  types and decimal/float wire spelling. Results and operation provenance are
  detached; no persistent cache or network reference support was added.
- Complete manifest shape/unique-ID validation precedes comparison. Malformed
  maps with excessive fields are rejected before allocating a full key set.
- Budget exhaustion returns typed UNKNOWN/BLOCK while preserving each remaining
  operation/direction. Original `compare` and default per-direction review
  behavior remain supported.
- Added offline SDK/benchmark workflows and budget/identity/resource/oracle
  tests. Distinct and small synthetic inputs can be slower and use more memory;
  no general production performance gain or independent review is claimed.

## 0.1.1

Existing exact-wire membership, encoded local-reference and ordinary-console
verification corrections are recorded in `docs/ITERATIONS.md`. Historical
failure evidence and reports are retained without assigning new scores.
