from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).parent
SAMPLE_PATH = ROOT / "data" / "sample_conversations_300.csv"

REQUIRED_COLUMNS = [
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

VERSION_LABELS = {
    "v1_baseline": "v1 基础客服",
    "v2_prompt_optimized": "v2 Prompt 优化",
    "v3_tool_augmented": "v3 工具增强",
}

VERSION_DESCRIPTIONS = {
    "v1_baseline": "基础客服，只回答用户问题，缺少结构化追问、转化推进和升级规则。",
    "v2_prompt_optimized": "增强语气、结构化回答和追问能力，能覆盖更多服务细节。",
    "v3_tool_augmented": "加入知识库、转人工、风险提醒规则，更接近真实 Agent 工作流。",
}

SURFACE_REASONS = [
    "未理解用户意图",
    "答非所问",
    "解决方案不完整",
    "语气生硬",
    "风险/合规问题",
    "未及时转人工",
    "重复追问",
    "承诺过度",
]

ROOT_CAUSES = [
    "Prompt 约束不足",
    "Memory 未正确保留上下文",
    "Skill 调用失败",
    "知识库缺失",
    "转人工规则缺失",
    "安全策略不足",
    "意图识别错误",
]


def to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y", "是"}


def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            if column in {"escalation_needed", "escalation_done", "resolved", "risk_flag"}:
                df[column] = False
            elif column in {"turn_count", "csat", "manual_score"}:
                df[column] = 0
            else:
                df[column] = "未知"

    for column in ["escalation_needed", "escalation_done", "resolved", "risk_flag"]:
        df[column] = df[column].map(to_bool)

    for column in ["turn_count", "csat", "manual_score"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date.astype(str)
    df["conversation_text"] = df["conversation_text"].fillna("").astype(str).str.replace("\\n", "\n", regex=False)
    return df


def infer_failure(row: pd.Series) -> tuple[str, str]:
    reasons: list[str] = []
    causes: list[str] = []

    action = str(row["agent_action"])
    issue = str(row["issue_category"])
    manual_score = float(row["manual_score"])
    high_intent = str(row["purchase_intent_level"]) == "high"
    needs_escalation = bool(row["escalation_needed"])
    did_escalate = bool(row["escalation_done"])
    resolved = bool(row["resolved"])
    risk = bool(row["risk_flag"])

    if risk:
        if action == "overpromise":
            reasons.append("承诺过度")
        reasons.append("风险/合规问题")
        causes.append("安全策略不足")

    if needs_escalation and not did_escalate:
        reasons.append("未及时转人工")
        causes.append("转人工规则缺失")

    if action == "answer_only" and issue in {"refund", "invoice", "pricing", "coupon", "sales_consulting"}:
        reasons.append("解决方案不完整")
        causes.append("Prompt 约束不足")

    if action == "repeat_policy":
        reasons.append("重复追问")
        causes.append("Memory 未正确保留上下文")

    if action == "skill_failed":
        reasons.append("解决方案不完整")
        causes.append("Skill 调用失败")

    if action == "answer_only" and manual_score < 55:
        reasons.append("语气生硬")
        causes.append("Prompt 约束不足")

    if not resolved and manual_score < 60 and action in {"answer_only", "repeat_policy"}:
        reasons.append("答非所问")
        causes.append("意图识别错误")

    if issue in {"refund", "logistics", "account", "invoice"} and action == "answer_only":
        causes.append("知识库缺失")

    if high_intent and action not in {"recommend_plan", "offer_coupon", "knowledge_lookup", "risk_warning"}:
        reasons.append("解决方案不完整")
        causes.append("Prompt 约束不足")

    if manual_score < 50 and not reasons:
        reasons.append("未理解用户意图")
        causes.append("意图识别错误")

    if not reasons:
        reasons.append("无明显失败")
    if not causes:
        causes.append("无明显系统问题")

    return "；".join(dict.fromkeys(reasons)), "；".join(dict.fromkeys(causes))


def score_dimensions(row: pd.Series, surface_reason: str) -> dict[str, int]:
    action = str(row["agent_action"])
    issue = str(row["issue_category"])
    version = str(row["agent_version"])
    high_intent = str(row["purchase_intent_level"]) == "high"
    resolved = bool(row["resolved"])
    risk = bool(row["risk_flag"])
    needs_escalation = bool(row["escalation_needed"])
    did_escalate = bool(row["escalation_done"])
    manual = float(row["manual_score"])

    intent_score = 90
    if "未理解用户意图" in surface_reason:
        intent_score = 45
    elif "答非所问" in surface_reason:
        intent_score = 55
    elif not resolved:
        intent_score = 72

    resolution_score = 90 if resolved else 52
    if "解决方案不完整" in surface_reason:
        resolution_score = min(resolution_score, 62)

    completeness_score = {
        "answer_only": 55,
        "repeat_policy": 45,
        "ask_clarifying": 76,
        "structured_answer": 86,
        "recommend_plan": 88,
        "offer_coupon": 88,
        "knowledge_lookup": 94,
        "transfer_human": 86,
        "risk_warning": 90,
        "skill_failed": 48,
        "overpromise": 38,
    }.get(action, 72)
    if issue in {"refund", "invoice", "logistics"} and action == "answer_only":
        completeness_score -= 10

    empathy_score = 82 if version != "v1_baseline" else 62
    if issue == "complaint" and action in {"answer_only", "repeat_policy"}:
        empathy_score = 38
    elif issue == "complaint" and action == "transfer_human":
        empathy_score = 94

    safety_score = 42 if risk else 90
    if action == "overpromise":
        safety_score = 30
    elif action == "risk_warning":
        safety_score = 96

    if needs_escalation and did_escalate:
        escalation_score = 94
    elif needs_escalation and not did_escalate:
        escalation_score = 34
    else:
        escalation_score = 88

    if high_intent:
        conversion_score = 88 if action in {"recommend_plan", "offer_coupon", "knowledge_lookup", "risk_warning"} else 45
    elif str(row["purchase_intent_level"]) == "medium":
        conversion_score = 78 if action in {"structured_answer", "knowledge_lookup", "recommend_plan"} else 60
    else:
        conversion_score = 72

    scores = {
        "意图理解": intent_score,
        "问题解决": resolution_score,
        "信息完整性": completeness_score,
        "同理心/语气": empathy_score,
        "安全合规": safety_score,
        "转人工时机": escalation_score,
        "销售转化推进": conversion_score,
    }
    return {key: clamp(value * 0.75 + manual * 0.25) for key, value in scores.items()}


def make_suggestion(row: pd.Series, surface_reason: str, root_cause: str) -> str:
    scenario = str(row["scenario"])
    action = str(row["agent_action"])
    high_intent = str(row["purchase_intent_level"]) == "high"

    if scenario == "退款咨询":
        return (
            "退款咨询场景中，Agent 不能只回答可以退款，需要补齐条件、时效、入口和费用。"
            "建议在 Prompt 中加入售后政策回答四要素，并在用户情绪为负面时先安抚再解释规则。"
        )
    if scenario in {"套餐对比", "优惠券咨询"} or high_intent:
        return (
            "高购买意向场景中，Agent 需要把回答推进到下一步动作。建议识别 purchase_intent_level=high 后，"
            "输出套餐差异、适用人群、优惠信息和明确 CTA，例如试用申请、优惠券领取或销售顾问跟进。"
        )
    if scenario == "投诉升级":
        return (
            "投诉升级场景中，如果 escalation_needed=true 且用户连续表达不满，Agent 应立即触发人工转接。"
            "建议补充转人工规则，并把前序问题、催办次数和用户诉求写入转接摘要。"
        )
    if scenario == "账户异常":
        return (
            "账户异常场景涉及安全风险，Agent 应先提醒用户不要提供密码、验证码等敏感信息。"
            "建议接入账号安全 Skill，并在验证码失败、疑似盗号、登录异常时进入人工安全队列。"
        )
    if scenario == "物流查询":
        return (
            "物流查询场景需要调用订单或物流 Skill，而不是泛泛回复在路上。建议返回当前位置、预计送达时间、"
            "超时后的催派动作，并保留订单号用于后续追踪。"
        )
    if scenario == "发票咨询":
        return (
            "发票咨询场景应说明发票抬头、税号、订单号、接收邮箱和开票时效。"
            "建议把发票政策沉淀到知识库，并让 Agent 主动确认是否补开历史订单。"
        )
    if "承诺过度" in surface_reason or action == "overpromise":
        return (
            "风险承诺场景不能使用一定提升、保证翻倍等表达。建议在安全策略中加入禁用承诺清单，"
            "并把回答改为试点评估、A/B 测试和指标验证方案。"
        )
    if "Memory" in root_cause:
        return (
            "多轮对话中出现重复追问，说明上下文保留不足。建议把用户已提供的信息写入短期 Memory，"
            "并在下一轮回复前检查是否已经询问过相同问题。"
        )
    return (
        "建议把当前场景拆成意图、必要信息、可执行动作和升级条件四部分，分别写入 Prompt、知识库和转人工规则，"
        "让 Agent 不只回答问题，也能推进业务目标。"
    )


def evaluate(df: pd.DataFrame) -> pd.DataFrame:
    evaluated = df.copy()
    failures = evaluated.apply(infer_failure, axis=1, result_type="expand")
    evaluated["surface_failure_reason"] = failures[0]
    evaluated["system_root_cause"] = failures[1]

    dimension_rows = []
    for _, row in evaluated.iterrows():
        dimension_rows.append(score_dimensions(row, row["surface_failure_reason"]))
    dimension_df = pd.DataFrame(dimension_rows)
    for column in dimension_df.columns:
        evaluated[column] = dimension_df[column]

    weights = {
        "意图理解": 0.16,
        "问题解决": 0.18,
        "信息完整性": 0.16,
        "同理心/语气": 0.12,
        "安全合规": 0.14,
        "转人工时机": 0.12,
        "销售转化推进": 0.12,
    }
    evaluated["eval_score"] = 0
    for column, weight in weights.items():
        evaluated["eval_score"] += evaluated[column] * weight
    evaluated["eval_score"] = evaluated["eval_score"].round(1)

    evaluated["conversion_advanced"] = evaluated["agent_action"].isin(
        ["recommend_plan", "offer_coupon", "knowledge_lookup", "risk_warning"]
    ) & evaluated["purchase_intent_level"].eq("high")
    evaluated["escalation_success"] = evaluated["escalation_needed"] & evaluated["escalation_done"]
    evaluated["optimization_suggestion"] = evaluated.apply(
        lambda row: make_suggestion(row, row["surface_failure_reason"], row["system_root_cause"]),
        axis=1,
    )
    return evaluated


def explode_counts(df: pd.DataFrame, column: str) -> pd.DataFrame:
    values = (
        df[column]
        .str.split("；")
        .explode()
        .loc[lambda series: ~series.isin(["无明显失败", "无明显系统问题"])]
    )
    if values.empty:
        return pd.DataFrame({"name": ["暂无明显问题"], "count": [0]})
    return values.value_counts().rename_axis("name").reset_index(name="count")


@st.cache_data
def load_sample() -> pd.DataFrame:
    return pd.read_csv(SAMPLE_PATH)


def read_uploaded_file(file) -> pd.DataFrame:
    return pd.read_csv(file)


def render_metric(label: str, value: str, help_text: str) -> None:
    st.metric(label=label, value=value, help=help_text)


def main() -> None:
    st.set_page_config(
        page_title="AI Agent 客服评测与优化分析",
        layout="wide",
    )
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.4rem; }
        div[data-testid="stMetric"] {
            background:#151a24;
            border:1px solid #293241;
            padding:14px 16px;
            border-radius:8px;
            box-shadow:0 8px 24px rgba(0,0,0,.16);
        }
        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] p,
        div[data-testid="stMetric"] div {
            color:#a8b3c4 !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
            color:#a8b3c4 !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color:#f8fafc !important;
            font-weight:700;
        }
        h1, h2, h3 { letter-spacing: 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("AI Agent 客服对话评测与优化分析")
    st.caption("围绕客服质量、销售转化、转人工处理和 Prompt / Memory / Skill 系统归因的作品集项目")

    with st.sidebar:
        st.header("数据与筛选")
        uploaded = st.file_uploader("上传客服对话 CSV", type=["csv"])
        st.caption("未上传时默认使用内置模拟数据。")

    try:
        raw_df = read_uploaded_file(uploaded) if uploaded else load_sample()
        df = evaluate(normalize_data(raw_df))
    except Exception as exc:
        st.error(f"数据读取或评分失败：{exc}")
        st.stop()

    with st.sidebar:
        version_options = sorted(df["agent_version"].dropna().unique())
        scenario_options = sorted(df["scenario"].dropna().unique())
        reason_options = SURFACE_REASONS
        root_options = ROOT_CAUSES

        selected_versions = st.multiselect("Agent 版本", version_options, default=version_options)
        selected_scenarios = st.multiselect("场景", scenario_options, default=scenario_options)
        selected_reasons = st.multiselect("表层失败原因", reason_options)
        selected_roots = st.multiselect("底层系统归因", root_options)
        score_range = st.slider("综合评分区间", 0, 100, (0, 100))
        show_low_only = st.checkbox("只看低分对话", value=False)

    filtered = df[
        df["agent_version"].isin(selected_versions)
        & df["scenario"].isin(selected_scenarios)
        & df["eval_score"].between(score_range[0], score_range[1])
    ].copy()
    if selected_reasons:
        filtered = filtered[filtered["surface_failure_reason"].apply(lambda text: any(item in text for item in selected_reasons))]
    if selected_roots:
        filtered = filtered[filtered["system_root_cause"].apply(lambda text: any(item in text for item in selected_roots))]
    if show_low_only:
        filtered = filtered[filtered["eval_score"] < 70]

    if filtered.empty:
        st.warning("当前筛选条件下没有数据。")
        st.stop()

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        render_metric("平均评分", f"{filtered['eval_score'].mean():.1f}", "综合七个维度后的 Agent 表现")
    with col2:
        render_metric("解决率", f"{filtered['resolved'].mean() * 100:.1f}%", "resolved=true 的会话占比")
    with col3:
        render_metric("风险率", f"{filtered['risk_flag'].mean() * 100:.1f}%", "含合规或承诺风险的会话占比")
    with col4:
        high_intent = filtered[filtered["purchase_intent_level"].eq("high")]
        conversion_rate = high_intent["conversion_advanced"].mean() if not high_intent.empty else 0
        render_metric("高意向推进率", f"{conversion_rate * 100:.1f}%", "高购买意向用户被推进到试用、优惠或销售跟进的比例")
    with col5:
        escalation_rows = filtered[filtered["escalation_needed"]]
        escalation_rate = escalation_rows["escalation_done"].mean() if not escalation_rows.empty else 0
        render_metric("转人工完成率", f"{escalation_rate * 100:.1f}%", "需要升级的对话中已转人工的比例")

    st.subheader("Agent 版本对比")
    version_rows = []
    for version, group in filtered.groupby("agent_version"):
        high_group = group[group["purchase_intent_level"].eq("high")]
        escalation_group = group[group["escalation_needed"]]
        version_rows.append(
            {
                "agent_version": version,
                "avg_score": group["eval_score"].mean(),
                "risk_rate": group["risk_flag"].mean(),
                "resolved_rate": group["resolved"].mean(),
                "conversion_rate": high_group["conversion_advanced"].mean() if not high_group.empty else 0,
                "escalation_done_rate": escalation_group["escalation_done"].mean() if not escalation_group.empty else 0,
                "conversations": len(group),
            }
        )
    version_summary = pd.DataFrame(version_rows).round(3)
    version_summary["version_name"] = version_summary["agent_version"].map(VERSION_LABELS).fillna(version_summary["agent_version"])
    compare_long = version_summary.melt(
        id_vars=["agent_version", "version_name"],
        value_vars=["avg_score", "resolved_rate", "risk_rate", "conversion_rate", "escalation_done_rate"],
        var_name="metric",
        value_name="value",
    )
    compare_long["display_value"] = compare_long.apply(
        lambda row: row["value"] if row["metric"] == "avg_score" else row["value"] * 100,
        axis=1,
    )
    metric_names = {
        "avg_score": "平均分",
        "resolved_rate": "解决率",
        "risk_rate": "风险率",
        "conversion_rate": "转化推进率",
        "escalation_done_rate": "转人工成功率",
    }
    compare_long["metric"] = compare_long["metric"].map(metric_names)
    st.plotly_chart(
        px.bar(
            compare_long,
            x="version_name",
            y="display_value",
            color="metric",
            barmode="group",
            text_auto=".1f",
            labels={"version_name": "Agent 版本", "display_value": "分数 / 百分比", "metric": "指标"},
            color_discrete_sequence=["#0f766e", "#2563eb", "#b7791f", "#be123c", "#475569"],
        ),
        use_container_width=True,
    )

    story_cols = st.columns(3)
    for idx, (version, text) in enumerate(VERSION_DESCRIPTIONS.items()):
        with story_cols[idx]:
            score = version_summary.loc[version_summary["agent_version"].eq(version), "avg_score"]
            st.markdown(f"**{VERSION_LABELS[version]}**")
            st.caption(text)
            if not score.empty:
                st.write(f"当前筛选平均分：{score.iloc[0]:.1f}")

    left, right = st.columns(2)
    with left:
        st.subheader("表层失败原因分布")
        reason_counts = explode_counts(filtered, "surface_failure_reason")
        st.plotly_chart(
            px.bar(reason_counts, x="count", y="name", orientation="h", text="count", labels={"count": "会话数", "name": "失败原因"}),
            use_container_width=True,
        )
    with right:
        st.subheader("底层系统归因分布")
        root_counts = explode_counts(filtered, "system_root_cause")
        st.plotly_chart(
            px.bar(root_counts, x="count", y="name", orientation="h", text="count", labels={"count": "会话数", "name": "系统归因"}),
            use_container_width=True,
        )

    st.subheader("低分对话筛选")
    low_score = filtered.sort_values(["eval_score", "csat"]).head(50)
    st.dataframe(
        low_score[
            [
                "conversation_id",
                "date",
                "agent_version",
                "scenario",
                "intent",
                "purchase_intent_level",
                "eval_score",
                "surface_failure_reason",
                "system_root_cause",
                "resolved",
                "csat",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("单条对话诊断")
    selected_id = st.selectbox("选择会话", low_score["conversation_id"].tolist())
    selected = filtered[filtered["conversation_id"].eq(selected_id)].iloc[0]

    detail_left, detail_right = st.columns([1.15, 0.85])
    with detail_left:
        st.markdown("**原始多轮对话**")
        st.code(selected["conversation_text"], language="text")
        st.markdown("**场景化优化建议**")
        st.info(selected["optimization_suggestion"])

    with detail_right:
        st.markdown("**诊断摘要**")
        st.write(f"Agent 版本：{VERSION_LABELS.get(selected['agent_version'], selected['agent_version'])}")
        st.write(f"业务场景：{selected['scenario']} / {selected['issue_category']}")
        st.write(f"转化阶段：{selected['conversion_stage']}，购买意向：{selected['purchase_intent_level']}")
        st.write(f"表层失败原因：{selected['surface_failure_reason']}")
        st.write(f"底层系统归因：{selected['system_root_cause']}")
        st.write(f"是否需要转人工：{selected['escalation_needed']}，是否已转人工：{selected['escalation_done']}")

        dimension_cols = ["意图理解", "问题解决", "信息完整性", "同理心/语气", "安全合规", "转人工时机", "销售转化推进"]
        radar_df = pd.DataFrame({"dimension": dimension_cols, "score": [selected[col] for col in dimension_cols]})
        st.plotly_chart(
            px.line_polar(
                radar_df,
                r="score",
                theta="dimension",
                line_close=True,
                range_r=[0, 100],
                markers=True,
            ),
            use_container_width=True,
        )

    st.subheader("上传字段要求")
    st.caption("上传 CSV 可以缺少部分字段，系统会自动补默认值；但字段越完整，归因越贴近真实业务。")
    st.code(", ".join(REQUIRED_COLUMNS), language="text")


if __name__ == "__main__":
    main()
