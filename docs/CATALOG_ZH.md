# 中文交付说明（独立评分待定）

SchemaWitness 为 API 维护者提供方向明确的 JSON Schema 兼容性证据。请求检查
旧输入是否仍能被新版本接受（old ⊆ new）；响应检查新输出是否仍符合旧契约
（new ⊆ old）。SDK 和 CLI 可返回包含关系的充分证明、具体 wire 反例，或带
精确原因的 UNKNOWN。批量清单把每个 operation 的请求、响应检查汇总成发布决策。

使用已实测的 `python -m pip install .` 安装后，执行
`schemawitness examples/old.json examples/new.json --direction request`，会返回
BREAKING、退出码 1 和 `{"quantity":1}`。执行 `schemawitness review examples/release.json`
会汇总两条 BREAKING、两条 COMPATIBLE 并给出 BLOCK。执行
`python examples/workflow.py` 可读简洁的评审结果；`python benchmarks/compare.py`
运行浅层比较、完整机制及两个消融；`python benchmarks/adverse.py` 展示实际不确定边界。

为什么构建：浅层字段差异容易漏掉嵌套类型、数组元素或引用处的约束收紧，也容易
把请求、响应方向混淆。项目把充分证明与有限反例搜索分开，用精确十进制传输及
独立验证器核验实际 wire 值，给评审者可直接复制的回归测试输入。它与 oasdiff
的广泛 OpenAPI 规则和 Pact 的真实提供方契约验证互补，不宣称替代这些工具或首创。

商业、技术、创新三个轴的正式分数和原因由独立评审在准确冻结 SHA 上给出；
构建代理不自行评分。可审阅证据分别是完整发布评审流程与有边界的试点经济模型、
真实自审修正及 625 对独立有限域 oracle、可执行的基线与证明/搜索消融。当前客户、
收入、采用量和付费意愿均未知。

边界包括不完整的充分证明、受预算限制的搜索、显式 JSON Schema 2020-12 子集，
以及需要调用方先导出有效请求/响应 schema。UNKNOWN 不会当作兼容；不存在提供方
行为验证、通用蕴含求解器或 OS 沙箱。完整限制和实测命令见 SUBSET 与 RELEASE_VERIFICATION。
