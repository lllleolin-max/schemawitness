# Security and reporting

No schemas or instances are uploaded. References are same-document only;
external references return UNKNOWN and the independent validator has a
retrieval registry that denies network access. No regex/expression execution,
plugins or provider calls are supported. Input files are read-only.

Do not submit secrets in schemas, enums or reports: a concrete witness may
repeat enum/const data and errors include operation IDs/schema paths. Treat
fixtures as sensitive if the schema contains sensitive constants. File paths
are chosen by the CLI user; this is not a filesystem or process sandbox.

Use configured size/expansion/search budgets and a resource-limited separate
process for hostile input. No wall-clock limit or authenticated schema identity
is promised. Keep jsonschema/referencing dependencies patched within their
supported major version and rerun the independent oracle after upgrades.

`BatchLimits` is opt-in and shares application work across one SDK review.
Its work units do not account for every internal jsonschema step, Fraction
operation, equality check or Python allocation. Input validation, identity
hashing, serialization and detached copies have separately bounded inputs and
storage, but their cost is outside the work ledger. Cache byte bounds describe
serialized payloads and fingerprints, not Python heap or process RSS. Output
UNKNOWN/provenance envelopes also remain outside the result-payload byte cap.
This remains an in-process checker; use an externally limited worker for
untrusted input. Shape validation scans caller-owned mappings/IDs before the
aggregate input traversal; the library cannot bound memory already allocated
by its caller. Do not mutate a shared manifest concurrently with a review.

Configured schema depth is distinct from interpreter stack capacity. Expected
RecursionError at batch-owned input traversal, identity hashing, result
conversion, serialization or detached copying closes the batch as UNKNOWN/BLOCK
without a certificate for the interrupted check. An oversized result transport
returns `batch_result_depth_limit`. These guards do not catch unexpected core
comparison errors or other RuntimeError exceptions and do not make this an OS
resource sandbox.

The pair digest is a cache identity, not a signature or source authorization.
The cache is discarded when review returns and never serves a different call.
It stores the original-document/direction result after all existing validation
and evidence checks; unsupported assertions or backend failure remain UNKNOWN.

Report security defects via the repository's private vulnerability reporting
feature when available; otherwise open an issue with a minimal nonsensitive
reproducer. Do not include credentials, real customer payloads or private URLs.
There is currently no guaranteed response SLA.
