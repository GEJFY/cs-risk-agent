# CS Risk Agent

**Enterprise Multi-Cloud AI Orchestrator for Consolidated Subsidiary Risk Analysis**

連結子会社リスク分析のためのエンタープライズ向けマルチクラウド AI 基盤

## Features

- **Multi-Cloud AI Orchestration**: Azure AI Foundry / AWS Bedrock / GCP Vertex AI を透過的に扱う Provider Pattern
- **Hybrid Deployment**: Cloud API + Local LLM (Ollama/vLLM) の構成ファイルベース切替
- **Model Tiering**: SOTA (GPT-4o, Claude 3.5 Sonnet) と Cost-Effective (Flash, Haiku) の動的切替
- **FinOps Circuit Breaker**: 月間予算に基づくリクエスト遮断機能
- **4 Analysis Engines**: 裁量的発生高 / 不正予測 / ルールベース / ベンフォード分析
- **AI Agent (LangGraph)**: 6つのプローブによる探索的分析
- **Full Observability**: 構造化ログ (JSON) + OpenTelemetry + 監査ログ
- **Infrastructure as Code**: Terraform によるマルチクラウドプロビジョニング

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Frontend (Next.js 15 + shadcn/ui + Recharts)       │
├─────────────────────────────────────────────────────┤
│  API Layer (FastAPI + JWT Auth + Audit Middleware)   │
├───────────────┬───────────────┬─────────────────────┤
│ AI Orchestr.  │ Analysis Eng. │ AI Agents           │
│ ├ Router      │ ├ DA Model    │ ├ Orchestrator      │
│ ├ CircuitBkr  │ ├ Fraud Pred  │ ├ Anomaly Probe     │
│ ├ CostTracker │ ├ Rule Engine │ ├ Ratio Probe       │
│ └ ModelTier   │ ├ Benford     │ ├ Trend Probe       │
│               │ └ Risk Scorer │ ├ Relationship Probe│
│               │               │ └ Cross-Ref Probe   │
├───────────────┴───────────────┴─────────────────────┤
│  Providers: Azure | AWS | GCP | Ollama | vLLM       │
├─────────────────────────────────────────────────────┤
│  Data: PostgreSQL 16 | Redis 7 | ETL Pipeline       │
└─────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. クローン
git clone https://github.com/GEJFY/cs-risk-agent.git
cd cs-risk-agent

# 2. 環境変数
cp .env.example .env

# 3. Docker Compose 起動
docker compose -f infra/docker/docker-compose.yml up -d

# 4. アクセス
# API:       http://localhost:8005/docs
# Dashboard: http://localhost:3005
```

## Development

```bash
# Backend
cd backend && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/uvicorn cs_risk_agent.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Test
cd backend && .venv/Scripts/pytest --cov
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, shadcn/ui, Recharts, Zustand, TanStack Query |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| AI/ML | LangGraph, XGBoost, scikit-learn, statsmodels, SHAP |
| AI Providers | Azure AI Foundry, AWS Bedrock, GCP Vertex AI, Ollama, vLLM |
| Database | PostgreSQL 16, Redis 7, Alembic |
| Observability | structlog, OpenTelemetry, Prometheus |
| Infrastructure | Terraform, Docker, GitHub Actions |

## Documentation

- [Architecture Design](docs/architecture.md) - 設計書 (Mermaid図含む)
- [Setup Guide](docs/setup-guide.md) - 環境構築手順
- [Operation Manual](docs/operation-manual.md) - 運用マニュアル
- [Cost Estimation](docs/cost-estimation.md) - コスト試算

## Demo Scenarios

```bash
python scripts/generate_demo_data.py       # デモデータ生成
python scripts/demo_failover.py            # フェイルオーバーデモ
python scripts/demo_hybrid_governance.py   # ハイブリッドガバナンスデモ
python scripts/demo_anomaly_detection.py   # 異常検知デモ
```

## License

Proprietary - All rights reserved.
