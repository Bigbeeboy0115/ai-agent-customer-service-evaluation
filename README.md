# AI Agent Customer Service Evaluation

AI Agent 客服对话评测与优化分析项目。项目基于模拟多轮客服/销售对话数据，构建评测指标体系，分析不同 Agent 版本在问题解决、风险控制、转人工、销售转化推进等方面的表现，并通过 Streamlit 看板展示低分样本、失败原因和系统归因。

## Project Scope

- Generate 300 simulated customer-service conversations.
- Compare three Agent versions: baseline, prompt optimized, and tool augmented.
- Evaluate conversations across resolution, CSAT, manual score, risk flag, escalation, and conversion progress.
- Split failures into surface-level issues and system-level root causes.
- Provide evidence-based optimization suggestions for Prompt, Memory, Skill, knowledge base, and escalation rules.

## Repository Structure

```text
app.py
data/
  sample_conversations.csv
  sample_conversations_300.csv
docs/
  evaluation_framework.md
  optimization_report.md
scripts/
  generate_sample_data.py
requirements.txt
start_app.bat
```

## Core Fields

`conversation_id`, `date`, `agent_version`, `scenario`, `customer_segment`, `intent`, `conversion_stage`, `purchase_intent_level`, `escalation_needed`, `escalation_done`, `agent_action`, `issue_category`, `turn_count`, `conversation_text`, `resolved`, `csat`, `manual_score`, `risk_flag`

## Evaluation Dimensions

- Intent understanding
- Problem resolution
- Information completeness
- Empathy and tone
- Safety and compliance
- Escalation timing
- Sales conversion progress

## Streamlit Dashboard

The app supports:

- Uploading or using default conversation CSV data
- Viewing average score, resolution rate, risk rate, conversion-progress rate, and escalation completion rate
- Comparing Agent versions across quality and risk metrics
- Inspecting failure reason distribution and system-level attribution
- Filtering low-score conversations
- Reviewing single-conversation details and recommended optimization actions

## Run Locally

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows, `start_app.bat` can be used to launch the dashboard.

## Data Statement

This project uses simulated customer-service conversation data. It does not contain private customer data or company internal business data.
