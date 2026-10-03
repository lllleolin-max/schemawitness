# SchemaWitness

Review a schema change with a concrete wire counterexample or a sufficient
inclusion proof. Request compatibility means **old ⊆ new**; response
compatibility means **new ⊆ old**. A search that finds nothing returns UNKNOWN.

For API maintainers who need reviewable JSON regression fixtures when a nested
contract changes. This library checks a useful JSON Schema 2020-12 subset,
including same-document references, `$ref` siblings, intersection, objects,
arrays, numeric intervals and finite enums. It does not parse OpenAPI documents
or certify provider behavior. See [supported subset](docs/SUBSET.md).

## Quickstart / 快速开始

Python 3.11+; examples contain disclosed synthetic API contracts.

```sh
python -m pip install .
schemawitness examples/old.json examples/new.json --direction request
# exit 1, BREAKING, wire={"quantity":1}; source.valid=true; target.valid=false
schemawitness examples/old.json examples/new.json --direction response
# exit 0, COMPATIBLE (new responses are within the old contract)
schemawitness review examples/release.json
# exit 1, BLOCK: 2 BREAKING + 2 COMPATIBLE directional checks
python examples/workflow.py
python benchmarks/compare.py
python benchmarks/adverse.py
python benchmarks/encoded_pointer_probe.py
python -m unittest discover -s tests -v
```

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
```

Use `loads` for precision-sensitive JSON; it preserves finite decimal literals
as Decimal. SDK floats mean their Python JSON wire spelling, which may already
be rounded by the caller. Use Decimal for exact decimal input.

Exit codes: 0 COMPATIBLE, 1 BREAKING, 2 UNKNOWN, 3 INVALID. Output is one JSON
object; `wire` is the exact JSON text to validate or save as a test fixture.
Request/response source and target labels are explained by the `inclusion` field.
Batch input uses unique operation IDs and embedded old/new schemas for both
request and response; [example](examples/release.json) is the format reference.

## Evidence and scope

- [Architecture and soundness rules](docs/ARCHITECTURE.md)
- [Executed comparison and prior art](docs/COMPARISON.md)
- [Three review cycles](docs/ITERATIONS.md)
- [Bounded commercial pilot](docs/PILOT.md)
- [Security](SECURITY.md), [contributing](CONTRIBUTING.md), MIT [license](LICENSE)

The checked-in CI builds and tests an installed wheel on Ubuntu/Windows,
Python 3.11/3.14. Local evidence records the actual interpreter used; remote CI
and independent portfolio review are separate gates. No adoption, customers,
revenue or willingness to pay have been established.
