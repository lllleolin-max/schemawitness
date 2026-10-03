# Contributing

Create a Python 3.11+ virtual environment, `python -m pip install -e . build`,
then run `python -m unittest discover -s tests -v`, `python examples/workflow.py`
and `python benchmarks/compare.py`. Build a wheel using `python -m build --wheel`
and rerun tests against the installed wheel before submitting changes.

New proof rules need a written soundness argument and independently evaluated
adversarial values; no-sample is never a proof. New witness strategies must
retain post-serialization independent validation. Unsupported assertions need
precise UNKNOWN diagnostics until implemented. Preserve mathematical integer,
boolean equality, reference sibling and exact decimal semantics.

Add a failing-before/passing-after regression for each bug and describe limits.
Do not add fabricated users or overstate competitor gaps. Keep synthetic
fixtures explicitly labeled. Public SDK/CLI result fields and exit-code changes
must be documented. MIT contributions only; no real private API contracts.
