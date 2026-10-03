# A bounded pilot, with unknown market demand

Buyer hypothesis: an API/platform maintainer reviewing JSON contracts for an
internal service with stable consumer expectations. Existing oasdiff and Pact
workflows establish the practical job; they do not prove willingness to pay for
this package. Actual customers, adoption, revenue and willingness to pay are
unknown.

Pilot boundary: 2 services, at most 30 operations, nonrecursive contracts in the
supported subset, 4 weeks, schemas supplied without sensitive real payloads.
Export effective request/response schemas into the embedded manifest, review
BLOCK outputs, and turn selected wire witnesses into provider/consumer tests.
Keep oasdiff for full OpenAPI diffs and Pact for behavior verification. UNKNOWN
goes to manual review and cannot release automatically.

Measure on actual reviewers: minutes from flagged change to confirmed test
fixture; count of certified witnesses accepted into regression suites; fraction
UNKNOWN; false release decisions independently checked; setup/maintenance
hours. A possible economic mechanism is reducing manual example construction
and variance-direction confusion, rather than claiming general defect prevention.

Example assumption, not measured benefit: if 20 monthly changes each save 5
reviewer minutes at $60/hour, gross time value is $100/month. Subtract adapter,
UNKNOWN triage and maintenance time; if those exceed 100 minutes, the time case
fails. No market-size/revenue extrapolation follows from synthetic benchmarks.
The pilot should stop if contracts routinely exceed the subset, fixtures do not
help reviewers, or independent verification finds a false certified decision.
Potential paid work would be bounded schema export/CI integration and support;
no hosted service, SLA, billing flow or commercial customer is implemented.
