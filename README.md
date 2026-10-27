# autoscientists

[![CI](https://github.com/shentonyan/autoscientists/actions/workflows/ci.yml/badge.svg)](https://github.com/shentonyan/autoscientists/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)
![dependencies](https://img.shields.io/badge/dependencies-none-lightgrey)
![status](https://img.shields.io/badge/status-v0.3%2C%20restricted%20search%20pilot-orange)

A small framework for running research questions as pre-registered, checkable
computations, designed to be driven by an AI agent and checked without trusting it.

An [AQuA-inspired pilot](docs/AQUA_PILOT.md) adds restricted candidate search,
validation-only memory and an independently audited public crypto backtest.
The auction card verifies at L2; the crypto baseline loses after costs. This is
not a reproduction of AQuA's undisclosed factors or equity model. The optional
quantitative scripts require NumPy; the framework itself uses only the standard library.

The [public futures follow-up](docs/AQUA_FUTURES.md) tests open-interest and
taker-flow events on a separately reserved quarter. It verifies at L3, but its
performance hypotheses are inconclusive and the full filter loses after costs.

[Extended experiments](docs/AQUA_EXTENDED.md) add a frozen quarterly search and
CNN/attention model ensembles. Both evaluations replay, and same-runtime full
model retraining matches; their performance targets are still unmet.

A [fixed US-equity proxy](docs/AQUA_EQUITY_PROXY.md) is locked before training.
Its public-source collection is in progress; it has no reported test result yet.

## AQuA 实验展示：两轮独立检验

**两轮实验均未达到预先设定的收益／预测优势标准。** 以下展示已记录的
BTC 永续合约实验；它们是方法层面的独立实现，原论文未公开的因子池、
股票池和精确模型仍无法恢复，不能据此宣称已复现原论文表现。

### 实验一：季度滚动策略检验（2025 Q2—Q4）

研究问题：持仓量（OI）下降后的价格反弹，结合主动买入流量，能否在
未参与选策略的后续季度产生扣成本收益？

训练窗口从 2024 年 7 月起扩展，每轮用测试季度之前的一个季度验证。
候选为 **12 个 OI／反弹／买入流量规则加空仓**；验证阶段按日均收益减去
1.645 倍标准误选择，非空仓规则至少需要 20 笔验证交易。这个惩罚分数是
选择启发式，不是经过多重选择校正的置信下界。成本为每边 2 bp，压力成本
为每边 5 bp；规则在查看测试结果前冻结。

![季度滚动检验：各季度选中策略与固定参考策略的扣成本损益](docs/img/aqua-walk-forward-results.png)

[下载 SVG 矢量图](docs/img/aqua-walk-forward-results.svg)

| 2025 年 4—12 月测试结果 | 记录值 | 含义 |
|---|---:|---|
| 选中策略 | 三个季度均为空仓 | 没有通过验证筛选的可交易规则 |
| 选中策略交易数／算术损益 | 0 笔／0.00% | 未证明交易获利；常规 Sharpe 未定义 |
| 固定 OI-only 参考损益 | −7.8817% | 先前研究确定的参考，不是本轮测试选出的赢家 |
| 固定弱买入流量参考损益 | −5.4505% | 同样扣除交易成本 |
| 预设联合成功标准 | 未达到 | 收益和增量收益假设无定论，季度／压力条件被否定 |

图表损益是相对初始名义本金的**算术损益**，不是复利收益。空仓比亏损参考少亏，
并不等于证明存在稳定交易优势。数据检查包括 389 个公开归档的校验和验证、
17,504 条样本的重复构建，以及 256 项原始数据标量比对。

[实验卡](cards/aqua-walk-forward.json) · [自动生成的结果报告](reports/aqua-walk-forward.md) ·
[不可变运行记录](runs/9ad10ec0892047f6.json)

### 实验二：CNN／注意力模型的独立确认（2026 年 1—9 月）

研究问题：卷积与时序注意力的组合，能否在独立测试期提高预测相关性，
并且优于 GRU、转化为扣成本后的交易收益？

输入为过去 **64 根五分钟 K 线的 9 项因果特征**；标签为额外延迟一根完整
五分钟 K 线后执行的、互不重叠的 30 分钟收益。CNN32 和 CNN64 使用卷积、
Transformer、门控池化及预测头；GRU32 和岭回归作为参考。三个神经网络配置
各用三个随机种子，共 **9 次训练**。这些是本项目预设的实现选择，并非原论文
公开的精确参数。

| 阶段 | 时间 | 样本数 | 用途 |
|---|---|---:|---|
| 训练 | 2024 年 7 月—2025 年 9 月 | 21,546 | 拟合模型与训练集归一化 |
| 验证 | 2025 年 10—12 月 | 4,415 | 选检查点、CNN 配置、方向及交易阈值 |
| 独立测试 | 2026 年 1—9 月 | 13,103 | 冻结后评分，不反向更换模型或阈值 |

![模型确认：测试 IC 点估计、选中 CNN 的置信区间及相对 GRU 的配对差异](docs/img/aqua-hybrid-confirmation-results.png)

[下载 SVG 矢量图](docs/img/aqua-hybrid-confirmation-results.svg)

| 模型／统计量 | 测试记录值 |
|---|---:|
| 验证阶段选中的 CNN32：Pearson IC | 0.005891 |
| CNN32 的 95% 区间 | [−0.015730, 0.029251] |
| CNN64：IC，仅作描述 | 0.009911 |
| GRU32 参考：IC | 0.018437 |
| 岭回归：IC，仅作描述 | 0.000205 |
| CNN32 相对 GRU 的 IC 差异：95% 区间 | [−0.035642, 0.012438] |
| 选中模型的测试交易数／算术损益 | 0 笔／0.00% |

IC 是全测试期预测与标签的 Pearson 相关系数；方向仅在验证集校准。区间采用
14 天分块 bootstrap。两个关键区间均包含零，因此**未证实 CNN 有正向预测优势，
也未证实它优于 GRU**。所有合格的验证交易阈值扣成本后亏损，策略按预设规则
空仓；四项确认假设均为无定论，不能根据测试 IC 改选其他模型。

原始输入重复构建和检查点推理复核通过；完整九成员训练在同一运行环境中
再次执行，导出预测完全一致。这证明同环境可重复性，不证明模型有收益优势。
两张实验卡的评估均通过 L3 复核；模型卡的 L3 针对已固定预测的评估，
并不认证 GPU 训练或原论文实现的正确性。

[实验卡](cards/aqua-hybrid-confirmation.json) · [自动生成的结果报告](reports/aqua-hybrid-confirmation.md) ·
[不可变运行记录](runs/55cf5d72f8ec4568.json) · [完整重复训练比对](research/model_forecasts/retraining_audit.json)

图中数值直接读取上述运行记录：[图表数据与来源哈希](docs/img/aqua-confirmation-chart-data.json)。
安装可选绘图库 matplotlib 后，可用 `python research/plot_confirmations.py` 重新生成 PNG／SVG；
这一步只绘制已有结果，不重新训练或重新选择测试策略。

![The research loop](docs/img/workflow.svg)

Before an experiment runs, its hypotheses and the outcomes that would refute them are
written down and hashed. After it runs, a separate step re-executes it, compares the
result with an independently computed reference, and generates the report from
recorded data. Free-text interpretation is kept apart and labelled as unverified.
`PROTOCOL.md` has the rules and their limits.

Standard library only. CI runs Python 3.10 to 3.13.

## Try it in two minutes

```
git clone https://github.com/shentonyan/autoscientists
cd autoscientists
python -m autosci --root examples/quickstart verify dice-sum
python -m autosci selftest
```

The first command re-executes a finished example and checks it against an exact
enumeration. The second corrupts a copy of the repository on purpose, 13 different
ways, and requires the verifier to notice each one. `docs/TUTORIAL.md` walks through
the example.

## What it checks

![Self-test matrix](docs/img/selftest.svg)

The calibration card reproduces two sealed-bid auction results known in closed form and
refutes one claim known to be false. The simulation and the closed form agree:

![Calibration](docs/img/calibration.svg)

Results get an evidence level, and the ledger is hash-chained:

![Evidence ladder](docs/img/evidence.svg)

![Ledger](docs/img/ledger.svg)

## Who may change what

![Trust tiers](docs/img/tiers.svg)

The framework's own checks are frozen: changes to them need the maintainer, and
`python -m autosci guard --base origin/main` lists them. Other parts can be proposed as
recorded variants and measured against a fixed benchmark before review
(`docs/EVOLUTION.md`).

## Using it with an AI agent

| you use | do this |
|---|---|
| Claude Code | open the repository; the `autoscientists` skill in `.claude/skills/` triggers when you give it a research idea. `CLAUDE.md` imports `AGENTS.md`. |
| another coding agent | point it at `AGENTS.md`; the procedure is `.claude/skills/autoscientists/SKILL.md` |
| no agent | run the commands yourself, see `docs/TUTORIAL.md` |

Ideas go in `state/QUEUE.md`. The agent takes one per wake-up, opens a **draft** pull
request, and stops at the first failed verification. Frequency and scheduling are up to
you; nothing in the repository schedules itself.

## Commands

```
python -m autosci new my-card        # write an empty card
python -m autosci cycle my-card      # validate, lock, run, report, verify
python -m autosci verify my-card     # re-execute and check independently
python -m autosci lint my-card       # notes: numbers and sources must be grounded
python -m autosci status             # cards, ledger chain, sources
python -m autosci govern             # should the loop stop and ask a human?
python -m autosci calibration        # how often predicted verdicts matched
python -m autosci guard --base origin/main   # changes to the frozen core
python -m autosci selftest           # corrupt a copy on purpose
python -m autosci evolve status      # variant archive
python -m unittest discover -s tests
python scripts/make_figures.py       # regenerate docs/img/*.svg
```

An experiment is a file in `experiments/` with `run`, `evaluate` and `crosscheck`.
Shapes are in `.claude/skills/autoscientists/card-schema.md`.

## Layout

| path | contents |
|---|---|
| `autosci/` | the framework (frozen core) |
| `cards/`, `experiments/` | research cards with locks; experiment modules |
| `runs/`, `reports/` | one JSON record per run; generated reports and `*.notes.md` |
| `state/` | ledger, variant archive, source registry, governor limits, manifest, queue, journal |
| `examples/quickstart/` | a complete, self-contained example |
| `.claude/` | skills, read-only reviewer agent, permission settings |
| `docs/` | `ARCHITECTURE.md`, `TUTORIAL.md`, `EVOLUTION.md`, `SURVEY.md`, figures |
| `scripts/` | figure generator |
| `tests/` | tests, including deliberate tampering |

## Limits

Checks here catch edits, missing cross-checks, uncited sources, unsupported numbers in
notes and irreproducible results. They do not establish that a question is the right
one, that a model fits reality, or that a source is correct. The independent reviewer is
the same model family as the author. See section 9 of `PROTOCOL.md`, and the FAQ in
`docs/ARCHITECTURE.md`.

## Contributing and security

See `CONTRIBUTING.md` and `SECURITY.md`. Pull requests carry a disclosure line; see
`.github/PULL_REQUEST_TEMPLATE.md`.
