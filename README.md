# SchemaWitness

Review a schema change with a concrete wire counterexample or a sufficient
inclusion proof. Request compatibility means **old ⊆ new**; response
compatibility means **new ⊆ old**. A search that finds nothing returns UNKNOWN.

中文：供 API 维护者在修改 JSON 契约前检查兼容性；如果破坏兼容，给出可保存为回归测试的具体 JSON 反例。请求检查旧输入是否仍被接受，响应检查新输出是否仍符合旧契约；不确定结果必须继续审查。

For API maintainers who need reviewable JSON regression fixtures when a nested
contract changes. This library checks a useful JSON Schema 2020-12 subset,
including same-document references, `$ref` siblings, intersection, objects,
arrays, numeric intervals and finite enums. It does not parse OpenAPI documents
or certify provider behavior. See [supported subset](docs/SUBSET.md).

## Quickstart / 快速开始

With Git installed, start from a new checkout / 首次使用先克隆并进入目录：

```console
git clone https://github.com/lllleolin-max/schemawitness.git
cd schemawitness
```

Python 3.11+; run from a clone in the intended Python environment. `pip` installs the `jsonschema` runtime dependency and builds a normal wheel. For an isolated install, run `python -m venv .venv`, then `.venv\Scripts\Activate.ps1` in PowerShell or `source .venv/bin/activate` in Bash. Examples contain disclosed synthetic API contracts.

```sh
python -m pip install .
schemawitness examples/old.json examples/new.json --direction request
# exit 1, BREAKING, wire={"quantity":1}; source.valid=true; target.valid=false
schemawitness examples/old.json examples/new.json --direction response
# exit 0, COMPATIBLE (new responses are within the old contract)
schemawitness review examples/release.json
# exit 1, BLOCK: 2 BREAKING + 2 COMPATIBLE directional checks
python examples/workflow.py
```

Exit 1 is expected in the breaking examples; run each command separately. If the console command is not on PATH, use `python -m schemawitness` with the same arguments. The workflow script prints each operation/direction result and finishes with `release=BLOCK; two verified wire fixtures available for maintainer review`.

中文：安装后把旧、新 schema 交给 CLI；请求检查旧输入是否仍能被接受，响应检查
新输出是否仍满足旧契约。BREAKING 会给出经过 JSON 序列化、再解析、独立验证的
具体反例，可复制为回归测试。COMPATIBLE 只来自充分证明。UNKNOWN 表示支持范围、
资源边界或证明规则不足，不能当作通过。批量 `review` 的任何不确定结果都会 BLOCK。

```python
from schemawitness import compare, loads, review

old = loads('{"type":"number","minimum":0}')
new = loads('{"type":"number","exclusiveMinimum":0}')
r = compare(old, new, direction="request")
assert r.status == "BREAKING"
assert r.wire == "0"
assert r.validation["source"]["valid"] and not r.validation["target"]["valid"]
print(r.wire)  # 0: an old-valid request that the new schema rejects
```

Use `loads` for precision-sensitive JSON; it preserves finite decimal literals
as Decimal. SDK floats mean their Python JSON wire spelling, which may already
be rounded by the caller. Use Decimal for exact decimal input.

Exit codes: 0 COMPATIBLE, 1 BREAKING, 2 UNKNOWN, 3 INVALID. Output is one JSON
object; `wire` is the exact JSON text to validate or save as a test fixture.
Request/response source and target labels are explained by the `inclusion` field.
Batch input uses unique operation IDs and embedded old/new schemas for both
request and response; [example](examples/release.json) is the format reference.

## Shared batch work / 整批工作预算

Version 0.2 adds an opt-in budget and pair cache for a single review call.
`compare(...)` and `review(manifest)` retain their original per-direction
`Limits`. Those limits never promised a shared total across operations.

```python
from schemawitness import BatchLimits, review

report = review(manifest, batch_limits=BatchLimits(max_work=10_000))
assert report["decision"] in {"ALLOW", "BLOCK"}
print(report["batch"]["work_used"], report["batch"]["core_compare_calls"])
```

```console
schemawitness review examples/release.json --batch-max-work 10000
python examples/batch_review.py
python benchmarks/batch_work.py --batch-work 100000 --out batch-work-new.json
```

The example is offline and synthetic. The benchmark requires a new output
filename and counts actual comparisons, expansions, search and backend calls,
including full input/cache/result handling. Use `--operations 1` for a small
case; omit `--batch-work` to measure the original behavior.

Complete operation shape and unique IDs are checked before any comparison.
With a shared budget, each operation still receives request/response evidence
and its own provenance. Equal original documents reuse a check only in the
same direction. Cache results are detached copies; changing an input before a
later review cannot reuse an earlier call's cache. An exhausted work, input or
storage bound returns typed UNKNOWN for unevaluated directions and BLOCK.
Only completed checks retain their actual proof or certified wire witness.

Raising `Limits.max_depth` does not raise Python's recursion limit. If an owned
batch input, identity or result-copy traversal exhausts the interpreter stack,
the affected and remaining checks return UNKNOWN/BLOCK with
`batch_recursion_limit`. Completed earlier checks retain their evidence. Result
transport uses the configured depth plus its report envelope, so a supported
deep wire witness is not rejected by an unrelated default serialization depth.

The work ledger counts application calls, rather than CPU instructions or
wall-clock time. The cache is private to one call; there is no network lookup,
cross-process persistence or concurrent-mutation contract. Serialized storage
caps do not bound Python object overhead or RSS. See [exact budget accounting
and measured costs](docs/BATCH.md) before applying it to hostile input.

## Use the result in a review / 接入契约审查

Supply effective old/new JSON schemas, rather than an OpenAPI document, and select the direction that matches the consumer. Copy the JSON text in `wire` into a regression fixture and preserve the source/target validation evidence with the review. `wire` is a JSON string containing the instance text: parse it once to obtain the instance, rather than testing the outer report string.

For a release, put operation schemas in [a review manifest](examples/release.json) and run `review`; permit only `decision: ALLOW`. A `BLOCK` with UNKNOWN needs broader contract tests or maintainer review, not an automatic compatibility assumption. Check [the subset and limits](docs/SUBSET.md) first: common assertions such as `pattern`, `format` and `oneOf`, external references, and recursive references are outside this checker.

## Evidence and scope

- [Architecture and soundness rules](docs/ARCHITECTURE.md)
- [Shared batch bounds and synthetic measurements](docs/BATCH.md)
- [Executed comparison and prior art](docs/COMPARISON.md)
- [Three review cycles](docs/ITERATIONS.md)
- [Windows console runner correction and controlled verification](docs/CONSOLE_LAYOUT.md)
- [Bounded commercial pilot](docs/PILOT.md)
- [Security](SECURITY.md), [contributing](CONTRIBUTING.md), MIT [license](LICENSE)

The checked-in CI builds and tests an installed wheel on Ubuntu/Windows,
Python 3.11/3.14. Local evidence records the actual interpreter used; remote CI
and independent portfolio review are separate gates. No adoption, customers,
revenue or willingness to pay have been established.

Optional verification: `python -m unittest discover -s tests -v` runs the suite. Run `python benchmarks/compare.py` and `python benchmarks/adverse.py` for the disclosed synthetic comparisons, or `python benchmarks/encoded_pointer_probe.py` and `python benchmarks/reviewer_membership_probe.py` for focused reference/membership probes. These checks are separate from the first-use workflow.
