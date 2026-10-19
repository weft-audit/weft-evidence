# weft — 控制论实验报告（可复现证据包）

**2026-10-19 实录**：治理层六件套（哨兵/完成否定/判断技能/账本/断点/评分官）
核心链路 **2–3 小时**移植进 DSH 0.2.1-rc.2 并全自动发布五仓；
期间发现并修复一个官方静默禁用缺陷（官方仓库 Discussion #10203）。
全程记录：[DSH 多 Agent 拓扑迁移实战记录](docs/reports/2026-10-19-DSH多Agent拓扑迁移实战记录.md)
｜ [最终报告](docs/reports/2026-10-19-DSH生态移植与连接层报告.md)
｜ [极客简报](docs/reports/2026-10-19-迁移简报-极客版.md)

同一模型，20 条真实任务：

| 组 | 配置 | 得分 |
|---|---|---|
| A | 多 Agent 编排（三层审计 + 心跳遥测） | **0.97 ~ 1.00** |
| B | 裸模型，无工具 | **0.02 ~ 0.07** |

模型没有变，变的是编排。评分 rubric 原文、脚本、历次报告全在本仓库，
`python regression.py` 一键复跑。

### 与生态内现有方案的区别（据对方 README 核实，2026-10-19）

| 方案 | 它们做的 | 我们的差异 |
|---|---|---|
| dsh-tower（多 Agent 编排，worktree 隔离） | 提交前的审查/合并门禁 | 我们是**运行时逐事件拦截**：每一步都过闸，不是合并前一次性审 |
| dsh-codex-ultra-mode（动态子智能体编排） | 任务开始后的动态分解与回收 | 我们多一层**入口守门人**：闲聊态零工具，工作意图必须显式确认才拉起系统 |
| 各类插件族 | 能力扩展 | 我们做的是治理层（车间主任），不是更多螺丝刀 |

### 可观测性说明（诚实标注）

当前遥测为自定义格式（心跳计数器 + JSONL 事件日志），**尚未对齐
OpenTelemetry GenAI 语义**；迁移到 OTel（span 树、可被 Langfuse/Jaeger 消费）
为明确目标，未完成前不宣称「可观测性对齐行业标准」。日志不含任何密钥明文，
脱敏扫描在案。

### 裁判可靠性校准（Ground Truth）

「0.97 vs 0.02」是单裁判结果；按评测工程标准，裁判自身必须先校准。
已备 5 条人工标注集（[校准集](docs/reports/ground-truth-5.md)），
标注完成后由三眼定分评分官同题复评，计算人工一致率，结果随仓库公开。

## 四大铁律

```
1. 防自噬：代码层不可变，能力层可扩展（Skill/插件经测试挂载）。
   来源：Agent 改自身代码导致脑死亡的真实事故。
2. 三层审计：小审计双清单（硬命中即暂停，软项只建议）；
   大审计 0-10 裁决；审计器只读，人类终裁。
3. 五分钟遥测：心跳轻唤醒，物理静默；白班交互校准，夜班自动跑批。
4. 意图触发（设计稿）：对话者与办事系统物理隔离；
   闲聊唤醒不了任何工具，开工必须显式确认。
```

## 事故复盘（五篇，全部挂证据等级）

- [42 分钟全线连环崩溃](docs/incidents/incident-2026-10-15.md)（时间线全来自日志）
- [自噬脑死亡](docs/incidents/incident-self-modify.md)
- [并发写冲突](docs/incidents/incident-concurrent-write.md)
- [OOM 强杀](docs/incidents/incident-oom.md)
- [VPN 断联](docs/incidents/incident-vpn.md)

## 插件

- [dsh-guardrail](https://github.com/weft-audit/dsh-guardrail) —
  双清单护栏，15 例测试全 PASS，Windows/Linux 双规则集。

## 其它

- [metrics.md](metrics.md) — 量化账本，每行挂口径
- [评估方法-20261018.md](评估方法-20261018.md) — rubric 原文与已知局限
- [philosophy.md](philosophy.md) — 思想底稿与经历
- [dialogist.md](dialogist.md) — 对话者机制
- [docs/rules.md](docs/rules.md) — 规则体系与判断清单（公开版）
- [docs/architecture.md](docs/architecture.md) — 架构图（审计环/四层记忆/防自噬）
- [docs/faq.md](docs/faq.md) — 常见质问与回答
- [docs/roadmap.md](docs/roadmap.md) — 公开路线图

## 诚实规则

本仓库只放能复现的东西。面板实录与机记切片分列标注，不混；
所有者口述一律标【口述】；无证据不算完成。
