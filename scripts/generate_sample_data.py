from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "sample_conversations_300.csv"
random.seed(20260609)

FIELDS = [
    "conversation_id",
    "date",
    "agent_version",
    "scenario",
    "customer_segment",
    "intent",
    "conversion_stage",
    "purchase_intent_level",
    "escalation_needed",
    "escalation_done",
    "agent_action",
    "issue_category",
    "turn_count",
    "conversation_text",
    "resolved",
    "csat",
    "manual_score",
    "risk_flag",
]

VERSIONS = ["v1_baseline", "v2_prompt_optimized", "v3_tool_augmented"]
CUSTOMER_SEGMENTS = ["新访客", "已购用户", "高意向线索", "企业用户", "价格敏感用户", "愤怒用户", "老用户"]

SCENARIOS = [
    {
        "scenario": "售前功能咨询",
        "issue_category": "sales_consulting",
        "intent": "ask_feature",
        "stage": "awareness",
        "intent_level": "medium",
        "needs_escalation": False,
    },
    {
        "scenario": "退款咨询",
        "issue_category": "refund",
        "intent": "refund_policy",
        "stage": "post_purchase",
        "intent_level": "low",
        "needs_escalation": False,
    },
    {
        "scenario": "套餐对比",
        "issue_category": "pricing",
        "intent": "compare_plans",
        "stage": "consideration",
        "intent_level": "high",
        "needs_escalation": False,
    },
    {
        "scenario": "投诉升级",
        "issue_category": "complaint",
        "intent": "complaint_escalation",
        "stage": "retention",
        "intent_level": "low",
        "needs_escalation": True,
    },
    {
        "scenario": "物流查询",
        "issue_category": "logistics",
        "intent": "track_order",
        "stage": "post_purchase",
        "intent_level": "low",
        "needs_escalation": False,
    },
    {
        "scenario": "优惠券咨询",
        "issue_category": "coupon",
        "intent": "apply_coupon",
        "stage": "checkout",
        "intent_level": "high",
        "needs_escalation": False,
    },
    {
        "scenario": "账户异常",
        "issue_category": "account",
        "intent": "recover_account",
        "stage": "retention",
        "intent_level": "low",
        "needs_escalation": True,
    },
    {
        "scenario": "发票咨询",
        "issue_category": "invoice",
        "intent": "invoice_request",
        "stage": "post_purchase",
        "intent_level": "medium",
        "needs_escalation": False,
    },
    {
        "scenario": "风险承诺",
        "issue_category": "sales_consulting",
        "intent": "ask_guarantee",
        "stage": "consideration",
        "intent_level": "high",
        "needs_escalation": False,
    },
    {
        "scenario": "活动规则咨询",
        "issue_category": "coupon",
        "intent": "promotion_rule",
        "stage": "checkout",
        "intent_level": "medium",
        "needs_escalation": False,
    },
]


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def choose_action(version: str, issue: str, scenario: str) -> str:
    if version == "v1_baseline":
        if scenario == "风险承诺" and random.random() < 0.55:
            return "overpromise"
        if issue == "complaint" and random.random() < 0.55:
            return "repeat_policy"
        return "answer_only"

    if version == "v2_prompt_optimized":
        if issue == "logistics" and random.random() < 0.18:
            return "skill_failed"
        if issue in {"pricing", "coupon", "sales_consulting"} and scenario != "风险承诺":
            return random.choice(["structured_answer", "recommend_plan", "offer_coupon"])
        if scenario == "风险承诺":
            return "structured_answer"
        if issue in {"refund", "invoice", "account"}:
            return "structured_answer"
        if issue == "logistics":
            return "ask_clarifying"
        if issue == "complaint":
            return random.choice(["structured_answer", "repeat_policy"])
        return "structured_answer"

    if issue in {"refund", "invoice", "logistics", "sales_consulting"}:
        if scenario == "风险承诺":
            return "risk_warning"
        return "knowledge_lookup"
    if issue in {"pricing", "coupon"}:
        return random.choice(["recommend_plan", "offer_coupon", "knowledge_lookup"])
    if issue in {"complaint", "account"}:
        return random.choice(["transfer_human", "risk_warning"])
    return "knowledge_lookup"


def outcome(version: str, action: str, needs_escalation: bool) -> tuple[bool, bool, bool, int, int]:
    risk = action == "overpromise"
    if version == "v1_baseline":
        resolved_prob = 0.28
        score_base = random.randint(38, 65)
        csat_base = random.randint(1, 3)
    elif version == "v2_prompt_optimized":
        resolved_prob = 0.68
        score_base = random.randint(68, 88)
        csat_base = random.randint(3, 5)
    else:
        resolved_prob = 0.86
        score_base = random.randint(82, 97)
        csat_base = random.randint(4, 5)

    if action in {"answer_only", "repeat_policy", "skill_failed", "overpromise"}:
        resolved_prob -= 0.24
        score_base -= random.randint(8, 22)
        csat_base = min(csat_base, random.randint(1, 3))
    if action in {"knowledge_lookup", "transfer_human", "risk_warning"}:
        resolved_prob += 0.08
        score_base += random.randint(2, 6)
    if needs_escalation and action not in {"transfer_human", "risk_warning"}:
        resolved_prob -= 0.22
        score_base -= random.randint(7, 18)

    escalation_done = needs_escalation and action in {"transfer_human", "risk_warning"} and random.random() < 0.9
    resolved = random.random() < max(0.05, min(0.98, resolved_prob))
    manual_score = max(25, min(99, score_base))
    csat = max(1, min(5, csat_base + (1 if resolved and random.random() < 0.35 else 0)))
    return resolved, escalation_done, risk, csat, manual_score


def make_text(scenario: str, action: str, issue: str) -> str:
    variants = {
        "售前功能咨询": {
            "answer_only": "用户: 你们的 AI 客服能接企业微信吗？\\nAgent: 可以。\\n用户: 能自动识别退款和投诉吗？\\nAgent: 可以的。",
            "structured_answer": "用户: 你们的 AI 客服能接企业微信吗？\\nAgent: 支持企业微信会话接入，也可以配置意图识别、知识库和人工转接。你更关注售前线索还是售后问题？\\n用户: 售后。\\nAgent: 建议先接入退款、物流和投诉三类高频场景。",
            "knowledge_lookup": "用户: 你们的 AI 客服能接企业微信吗？\\nAgent: 我查到当前方案支持企业微信、网页客服和小程序会话接入。\\n用户: 售后量大能先试吗？\\nAgent: 可以先用退款、物流、投诉三个场景做 7 天试点。",
        },
        "退款咨询": {
            "answer_only": "用户: 我买错套餐了能退款吗？\\nAgent: 可以退款。\\n用户: 在哪里退？多久到？\\nAgent: 按平台规则处理。",
            "structured_answer": "用户: 我买错套餐了能退款吗？\\nAgent: 我先帮你判断，需要看购买时间、是否使用权益和购买渠道。\\n用户: 昨天买的，没用。\\nAgent: 通常可在订单详情页提交申请，审核后原路退回。",
            "knowledge_lookup": "用户: 我买错套餐了能退款吗？\\nAgent: 我查到退款需要看购买渠道、购买时间、权益使用和发票状态。\\n用户: 昨天买的没用。\\nAgent: 建议在订单详情提交，审核通常 1 到 3 个工作日。",
        },
        "套餐对比": {
            "answer_only": "用户: 标准版和专业版差别是什么？我们 20 人客服团队想买。\\nAgent: 专业版功能更多。\\n用户: 哪个适合我们？\\nAgent: 看需求。",
            "recommend_plan": "用户: 标准版和专业版差别是什么？我们 20 人客服团队想买。\\nAgent: 20 人团队建议专业版，重点是多坐席、知识库权限、质检看板和转人工规则。\\n用户: 能试用吗？\\nAgent: 可以先申请试用，并让销售顾问确认团队报价。",
            "knowledge_lookup": "用户: 标准版和专业版差别是什么？我们 20 人客服团队想买。\\nAgent: 我查到专业版更适合多坐席协同、知识库分权和质检看板。\\n用户: 有企业优惠吗？\\nAgent: 我可以生成试用申请，并提示销售顾问跟进企业优惠。",
        },
        "投诉升级": {
            "repeat_policy": "用户: 我已经催三次了还没人处理。\\nAgent: 请耐心等待。\\n用户: 我要投诉。\\nAgent: 按规则需要等待。\\n用户: 我要人工。\\nAgent: 请继续等待。",
            "structured_answer": "用户: 我已经催三次了还没人处理。\\nAgent: 很抱歉让你重复等待。我先帮你确认订单号和问题类型。\\n用户: 我现在就要人工。\\nAgent: 我理解你的着急，但还需要先收集信息。",
            "transfer_human": "用户: 我已经催三次了还没人处理。\\nAgent: 抱歉让你多次催促，我识别到这是投诉升级场景。\\n用户: 我要人工。\\nAgent: 已为你转接人工客服，并附上前序问题摘要。",
            "risk_warning": "用户: 我已经催三次了还没人处理。\\nAgent: 抱歉让你重复等待，我会优先升级人工处理。\\n用户: 别再让我重复说。\\nAgent: 已记录催办次数和诉求摘要，转接时不会让你重复描述。",
        },
        "物流查询": {
            "answer_only": "用户: 我的货怎么还没到？\\nAgent: 物流在路上。\\n用户: 到哪里了？\\nAgent: 请等一下。",
            "ask_clarifying": "用户: 我的货怎么还没到？\\nAgent: 我来帮你查，请提供订单号或手机号后四位。\\n用户: 订单 8831。\\nAgent: 收到，我会按订单号查询预计送达时间。",
            "skill_failed": "用户: 我的订单今天能到吗？\\nAgent: 我尝试查询物流，但当前系统暂无结果。\\n用户: 所以现在到哪里了？\\nAgent: 建议稍后再试或等待短信通知。",
            "knowledge_lookup": "用户: 我的货怎么还没到？\\nAgent: 我查到订单已到达分拨中心，预计明天派送。\\n用户: 如果明天还不到呢？\\nAgent: 超过预计时间后我会生成催派工单。",
        },
        "优惠券咨询": {
            "answer_only": "用户: 我准备下单，有没有优惠券？\\nAgent: 有活动。\\n用户: 在哪里领？\\nAgent: 活动页。",
            "offer_coupon": "用户: 我准备下单，有没有优惠券？\\nAgent: 可以先领取新人券和专业版满减券。\\n用户: 我想买专业版。\\nAgent: 建议先领券再进结算页，系统会自动选择最优券。",
            "recommend_plan": "用户: 我准备下单，有没有优惠券？\\nAgent: 如果你买专业版，建议先确认团队人数和使用周期。\\n用户: 有优惠吗？\\nAgent: 可以领取专业版满减券，并申请销售顾问确认企业优惠。",
            "knowledge_lookup": "用户: 我准备下单，有没有优惠券？\\nAgent: 我查到你当前可用新人券和专业版满减券。\\n用户: 怎么用？\\nAgent: 结算页会自动选择最优券，并显示最终应付金额。",
        },
        "账户异常": {
            "answer_only": "用户: 我的账号突然登录不上了。\\nAgent: 重试一下。\\n用户: 重试很多次了。\\nAgent: 换个网络。",
            "structured_answer": "用户: 我的账号突然登录不上了。\\nAgent: 我先帮你判断，请确认是否更换手机号、是否收到风险提示、是否能接收验证码。\\n用户: 收不到验证码。\\nAgent: 可能是短信通道或账号风控问题。",
            "risk_warning": "用户: 我的账号突然登录不上了。\\nAgent: 这可能涉及账号安全，请不要提供密码或验证码。\\n用户: 那怎么办？\\nAgent: 我会转接账号安全人工队列，并附上验证码失败摘要。",
            "transfer_human": "用户: 我的账号突然登录不上了。\\nAgent: 我识别到账户异常需要人工核验。\\n用户: 好。\\nAgent: 已转接账号安全队列，并保留当前问题摘要。",
        },
        "发票咨询": {
            "answer_only": "用户: 可以开企业发票吗？\\nAgent: 可以。\\n用户: 需要什么信息？\\nAgent: 填信息就行。",
            "structured_answer": "用户: 可以开企业发票吗？\\nAgent: 可以，通常需要抬头、税号、邮箱和订单信息。\\n用户: 多久能开？\\nAgent: 一般 1 到 3 个工作日，具体以审核为准。",
            "knowledge_lookup": "用户: 可以开企业发票吗？\\nAgent: 我查到企业发票需要公司抬头、税号、订单号和邮箱。\\n用户: 可以补开上个月的吗？\\nAgent: 可以申请补开，但需要订单仍在可开票周期内。",
        },
        "风险承诺": {
            "overpromise": "用户: 买了以后一定能提升转化吗？\\nAgent: 一定可以，保证翻倍。\\n用户: 真的保证吗？\\nAgent: 是的，肯定有效。",
            "structured_answer": "用户: 买了以后一定能提升转化吗？\\nAgent: 不建议承诺固定增长。更合理的是先看咨询量、知识库质量和人工承接流程。\\n用户: 那怎么评估？\\nAgent: 可以用试点数据看解决率、转人工率和线索推进率。",
            "risk_warning": "用户: 买了以后一定能提升转化吗？\\nAgent: 我不能承诺固定提升比例，但可以帮你设计试点评估。\\n用户: 怎么做？\\nAgent: 建议用两周 A/B 测试，对比解决率、线索留资率和人工跟进转化。",
        },
        "活动规则咨询": {
            "answer_only": "用户: 活动券能和会员折扣一起用吗？\\nAgent: 看规则。\\n用户: 规则在哪？\\nAgent: 活动页。",
            "structured_answer": "用户: 活动券能和会员折扣一起用吗？\\nAgent: 需要看券类型。有些满减券可叠加会员价，有些新人券不可叠加。\\n用户: 我现在下单怎么确认？\\nAgent: 以结算页展示的可用优惠为准。",
            "knowledge_lookup": "用户: 活动券能和会员折扣一起用吗？\\nAgent: 我查到满减券可与会员价叠加，但新人专享券不可叠加。\\n用户: 怎么确认？\\nAgent: 进入结算页后系统会显示最优组合和不可用原因。",
            "offer_coupon": "用户: 活动券能和会员折扣一起用吗？\\nAgent: 你可以先领券再进结算页，我会提示可叠加和不可叠加原因。\\n用户: 那我买专业版。\\nAgent: 建议选择专业版满减券，并确认最终应付金额。",
        },
    }
    scenario_map = variants[scenario]
    if action in scenario_map:
        return scenario_map[action]
    if action == "answer_only" and "answer_only" in scenario_map:
        return scenario_map["answer_only"]
    if action == "structured_answer" and "structured_answer" in scenario_map:
        return scenario_map["structured_answer"]
    if action == "knowledge_lookup" and "knowledge_lookup" in scenario_map:
        return scenario_map["knowledge_lookup"]
    return next(iter(scenario_map.values()))


def main() -> None:
    rows = []
    start = date(2026, 5, 20)
    for i in range(1, 301):
        version = VERSIONS[(i - 1) % len(VERSIONS)]
        scenario_config = SCENARIOS[(i - 1 + random.randint(0, 4)) % len(SCENARIOS)]
        scenario = scenario_config["scenario"]
        issue = scenario_config["issue_category"]
        action = choose_action(version, issue, scenario)
        needs_escalation = scenario_config["needs_escalation"]
        resolved, escalation_done, risk, csat, manual_score = outcome(version, action, needs_escalation)
        current_date = start + timedelta(days=(i - 1) % 21)
        turn_count = random.randint(3, 8)
        text = make_text(scenario, action, issue)
        rows.append(
            {
                "conversation_id": f"CS{i:04d}",
                "date": current_date.isoformat(),
                "agent_version": version,
                "scenario": scenario,
                "customer_segment": random.choice(CUSTOMER_SEGMENTS),
                "intent": scenario_config["intent"],
                "conversion_stage": scenario_config["stage"],
                "purchase_intent_level": scenario_config["intent_level"],
                "escalation_needed": bool_text(needs_escalation),
                "escalation_done": bool_text(escalation_done),
                "agent_action": action,
                "issue_category": issue,
                "turn_count": turn_count,
                "conversation_text": text,
                "resolved": bool_text(resolved),
                "csat": csat,
                "manual_score": manual_score,
                "risk_flag": bool_text(risk),
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows -> {OUTPUT}")


if __name__ == "__main__":
    main()
