# AI Agent 客服对话评测体系

## 1. 业务目标

本项目把客服 Agent 的评测目标拆成三层：

- 客服质量：是否理解问题、是否解决问题、信息是否完整、语气是否得体。
- 销售转化：是否识别购买意向，是否推进到试用、优惠、套餐选择或销售跟进。
- 系统优化：失败到底来自 Prompt、Memory、Skill、知识库、转人工规则还是安全策略。

这比单纯看满意度更贴近真实业务，因为客服 Agent 不只负责回答，还承担售前咨询、转化辅助、风险兜底和人工分流。

## 2. 字段设计

| 字段 | 含义 |
| --- | --- |
| `intent` | 用户意图，例如退款、查物流、套餐对比、投诉升级 |
| `conversion_stage` | 用户所处阶段，例如 awareness、consideration、checkout、retention |
| `purchase_intent_level` | 购买意向，low / medium / high |
| `escalation_needed` | 是否需要转人工 |
| `escalation_done` | Agent 是否已完成转人工 |
| `agent_action` | Agent 主要动作，例如 answer_only、recommend_plan、knowledge_lookup、transfer_human |
| `issue_category` | 问题类别，例如 refund、pricing、complaint、account |

这些字段用于把对话质量和业务目标连起来。例如，高购买意向用户如果只得到泛泛回答，即使没有明显客服错误，也会被识别为转化机会损失。

## 3. 评分维度

| 维度 | 评估问题 |
| --- | --- |
| 意图理解 | Agent 是否理解用户真实诉求 |
| 问题解决 | 用户问题是否被解决 |
| 信息完整性 | 是否给出条件、入口、时效、费用、下一步动作等必要信息 |
| 同理心/语气 | 对负面情绪、投诉、焦虑是否有安抚 |
| 安全合规 | 是否避免过度承诺、索要敏感信息或错误保证 |
| 转人工时机 | 该升级时是否及时升级 |
| 销售转化推进 | 高意向用户是否被推进到试用、优惠、套餐或销售跟进 |

综合分采用加权规则计算，上传新 CSV 后会重新评估。

## 4. 两层失败归因

表层失败原因用于给业务方看，回答“用户体验哪里不好”：

- 未理解用户意图
- 答非所问
- 解决方案不完整
- 语气生硬
- 风险/合规问题
- 未及时转人工
- 重复追问
- 承诺过度

底层系统归因用于给 Agent 团队看，回答“系统能力哪里需要改”：

- Prompt 约束不足
- Memory 未正确保留上下文
- Skill 调用失败
- 知识库缺失
- 转人工规则缺失
- 安全策略不足
- 意图识别错误

## 5. LLM-as-a-Judge 扩展模板

当前项目默认使用可复现规则评分，不依赖 API。后续可以接入 LLM-as-a-Judge，使用如下模板：

```text
你是 AI 客服对话质检员。请基于以下多轮对话，按 0-100 分评估：
1. 意图理解
2. 问题解决
3. 信息完整性
4. 同理心/语气
5. 安全合规
6. 转人工时机
7. 销售转化推进

请输出：
- 每个维度分数
- 表层失败原因
- 底层系统归因
- 一条具体优化建议

对话：
{{conversation_text}}

业务字段：
intent={{intent}}
conversion_stage={{conversion_stage}}
purchase_intent_level={{purchase_intent_level}}
escalation_needed={{escalation_needed}}
agent_action={{agent_action}}
```
