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

Report security defects via the repository's private vulnerability reporting
feature when available; otherwise open an issue with a minimal nonsensitive
reproducer. Do not include credentials, real customer payloads or private URLs.
There is currently no guaranteed response SLA.
