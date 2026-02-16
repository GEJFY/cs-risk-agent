# CS Risk Agent

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
![Coverage 94%](https://img.shields.io/badge/Coverage-94%25-brightgreen.svg)
![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)

**Enterprise Multi-Cloud AI Orchestrator for Consolidated Subsidiary Risk Analysis**

連結子会社リスク分析のためのエンタープライズ向けマルチクラウド AI 基盤

---

## Overview

CS Risk Agent は、連結子会社の財務データを AI で自動分析し、不正リスクや異常を検知するエンタープライズシステムです。マルチクラウド AI プロバイダー (Azure / AWS / GCP / ローカル LLM) を透過的に切替え、コスト最適化とデータ機密性を両立します。

### 主要ユースケース

- 連結子会社 (50〜2,000社) の月次財務分析を自動化
- 裁量的発生高・ベンフォード分析による会計不正の早期検知
- AI エージェントによる探索的リスク分析とレポート自動生成
- マルチクラウド環境でのコスト最適化 (Model Tiering + Circuit Breaker)

## Features

### AI Orchestration

- **Multi-Cloud Provider Pattern**: Azure AI Foundry / AWS Bedrock / GCP Vertex AI を統一インターフェースで利用
- **Hybrid Deployment**: Cloud API + Local LLM (Ollama/vLLM) の構成ファイルベース切替
- **Model Tiering**: SOTA (GPT-4o, Claude 3.5 Sonnet) と Cost-Effective (Gemini Flash, Haiku) の自動選択
- **FinOps Circuit Breaker**: 月間予算ベースの自動遮断 (80% 警告 / 95% 遮断)
- **Automatic Failover**: プロバイダー障害時のフォールバックチェーン (azure → aws → gcp → ollama)

### Analysis Engines

- **Discretionary Accruals Model**: 修正ジョーンズモデルによる裁量的発生高の検知
- **Fraud Prediction**: XGBoost + SHAP による不正予測と説明可能 AI
- **Rule Engine**: 業界基準ベースの閾値ルール評価 (流動比率、負債比率 等)
- **Benford Analysis**: ベンフォードの法則に基づく数値分布の異常検知

### AI Agent (LangGraph)

6つの専門プローブによる探索的分析:

- Anomaly Probe / Ratio Probe / Trend Probe / Relationship Probe / Cross-Reference Probe / Reporting Probe

### Enterprise Features

- **JWT Authentication**: HS256 ベースの認証 + RBAC (Admin / Auditor / CFO / CEO / Viewer)
- **Full Observability**: 構造化ログ (JSON) + OpenTelemetry + Prometheus メトリクス + 監査ログ
- **Report Generation**: PDF / PowerPoint の自動生成
- **Infrastructure as Code**: Terraform によるマルチクラウドプロビジョニング

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Frontend (Next.js 15 + shadcn/ui + Recharts)            │
│  Dashboard / Company List / Risk Detail / Report Viewer  │
├──────────────────────────────────────────────────────────┤
│  API Layer (FastAPI + JWT Auth + Audit Middleware)        │
│  /companies  /risk-scores  /analysis  /ai  /reports      │
├────────────────┬────────────────┬─────────────────────────┤
│ AI Orchestr.   │ Analysis Eng.  │ AI Agents (LangGraph)  │
│ ├ Router       │ ├ DA Model     │ ├ Orchestrator         │
│ ├ CircuitBkr   │ ├ Fraud Pred   │ ├ Anomaly Probe       │
│ ├ CostTracker  │ ├ Rule Engine  │ ├ Ratio Probe         │
│ └ ModelTier    │ ├ Benford      │ ├ Trend Probe         │
│                │ └ Risk Scorer  │ ├ Relationship Probe   │
│                │                │ └ Cross-Ref Probe      │
├────────────────┴────────────────┴─────────────────────────┤
│  Providers: Azure | AWS | GCP | Ollama | vLLM            │
├──────────────────────────────────────────────────────────┤
│  Data: PostgreSQL 16 | Redis 7 | ETL (EDINET/XBRL)      │
└──────────────────────────────────────────────────────────┘
```

## Quick Start

### Docker Compose (推奨)

```bash
# 1. クローン
git clone https://github.com/GEJFY/cs-risk-agent.git
cd cs-risk-agent

# 2. 環境変数
cp .env.example .env
# .env を編集して AI プロバイダーの API キーを設定

# 3. Docker Compose 起動
docker compose -f infra/docker/docker-compose.yml up -d

# 4. アクセス
# API Docs:  http://localhost:8005/docs
# Dashboard: http://localhost:3005
```

| サービス | ホストポート | コンテナポート | URL |
| -------- | ------------ | -------------- | --- |
| Backend (FastAPI) | 8005 | 8000 | `http://localhost:8005/docs` |
| Frontend (Next.js) | 3005 | 3000 | `http://localhost:3005` |
| PostgreSQL | 15435 | 5432 | - |
| Redis | 16380 | 6379 | - |

### ローカル開発

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/uvicorn cs_risk_agent.main:app --reload --port 8005

# Frontend (別ターミナル)
cd frontend
npm install
npm run dev

# デモデータ生成
python scripts/generate_demo_data.py
```

## Project Structure

```
cs-risk-agent/
├── backend/
│   ├── src/cs_risk_agent/       # メインパッケージ (64 モジュール)
│   │   ├── ai/                  # AI プロバイダー & エージェント
│   │   │   ├── agents/          # LangGraph プローブ (6種)
│   │   │   ├── providers/       # Azure / AWS / GCP / Ollama / vLLM
│   │   │   ├── router.py        # AI ルーティング & フォールバック
│   │   │   ├── circuit_breaker.py
│   │   │   └── cost_tracker.py
│   │   ├── analysis/            # 分析エンジン (4種)
│   │   ├── api/                 # FastAPI エンドポイント
│   │   │   └── v1/              # API v1 ルーター
│   │   ├── core/                # 設定 / セキュリティ / 例外
│   │   ├── data/                # SQLAlchemy モデル / リポジトリ
│   │   ├── etl/                 # EDINET / XBRL / Excel
│   │   ├── observability/       # ログ / メトリクス / 監査
│   │   ├── reports/             # PDF / PPTX 生成
│   │   └── main.py              # FastAPI アプリケーション
│   ├── tests/                   # テストスイート (45 ファイル, 819 テスト)
│   │   ├── unit/                # ユニットテスト
│   │   ├── integration/         # API 統合テスト
│   │   └── e2e/                 # E2E ビジネスシナリオ
│   └── pyproject.toml
├── frontend/                    # Next.js 15 ダッシュボード
├── infra/
│   ├── docker/                  # Dockerfile & docker-compose.yml
│   └── terraform/               # マルチクラウド IaC
├── scripts/                     # デモ & ユーティリティ
├── demo_data/                   # サンプル財務データ
└── docs/                        # 設計書 / 運用マニュアル
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, shadcn/ui, Recharts, Zustand, TanStack Query |
| Backend | Python 3.11, FastAPI 0.115, SQLAlchemy 2.0, Pydantic v2 |
| AI/ML | LangGraph, XGBoost, scikit-learn, statsmodels, SHAP |
| AI Providers | Azure AI Foundry, AWS Bedrock, GCP Vertex AI, Ollama, vLLM |
| Database | PostgreSQL 16, Redis 7, Alembic |
| Observability | structlog, OpenTelemetry, Prometheus |
| Reports | ReportLab (PDF), python-pptx (PowerPoint), Jinja2 |
| Security | python-jose (JWT), passlib (bcrypt) |
| Infrastructure | Terraform, Docker, GitHub Actions |
| Quality | pytest, ruff, mypy, Vitest, Playwright |

## API Endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/api/v1/health/` | ヘルスチェック (DB/Redis 接続確認) |
| GET | `/api/v1/companies/` | 企業一覧取得 |
| GET | `/api/v1/companies/{id}` | 企業詳細取得 |
| GET | `/api/v1/risk-scores/` | リスクスコア一覧 |
| POST | `/api/v1/analysis/run` | 分析実行 |
| GET | `/api/v1/analysis/{id}/result` | 分析結果取得 |
| POST | `/api/v1/ai/insights` | AI インサイト生成 |
| GET | `/api/v1/financials/` | 財務データ取得 |
| GET | `/api/v1/reports/` | レポート一覧 |
| POST | `/api/v1/reports/generate` | レポート生成 (PDF/PPTX) |
| POST | `/api/v1/admin/users` | ユーザー管理 |

詳細: `http://localhost:8005/docs` (Swagger UI)

## Testing

```bash
cd backend

# 全テスト実行 (カバレッジ付き)
.venv/Scripts/pytest --cov

# ユニットテストのみ
.venv/Scripts/pytest tests/unit/

# 統合テストのみ
.venv/Scripts/pytest tests/integration/

# 特定テスト実行
.venv/Scripts/pytest tests/unit/test_benford.py -v
```

| 項目 | 値 |
| ---- | --- |
| テストファイル数 | 45 |
| テストケース数 | 819 |
| カバレッジ | 94% |
| テスト構成 | Unit / Integration / E2E |

## Demo Scenarios

```bash
# デモ財務データ生成 (東洋重工グループ 15社)
python scripts/generate_demo_data.py

# マルチクラウドフェイルオーバーデモ
python scripts/demo_failover.py

# ハイブリッドガバナンスデモ (機密データのローカル処理)
python scripts/demo_hybrid_governance.py

# 異常検知デモ (ベンフォード分析 + 裁量的発生高)
python scripts/demo_anomaly_detection.py
```

## Cost Estimation

| 構成 | 月額 (USD) | 備考 |
| ---- | ---------- | ---- |
| GCP 単体 | ~$94 | AI コスト最小 |
| Azure 単体 | ~$124 | GPT-4o 高精度 |
| ハイブリッド | ~$136 | セキュリティ + コスト最適 (推奨) |
| AWS 単体 | ~$136 | Claude 3.5 Sonnet |
| ローカルのみ | ~$30 | GPU 初期投資別 |

詳細: [Cost Estimation](docs/cost-estimation.md) (ROI 試算含む: 年間 ~$148,000 削減)

## Documentation

| ドキュメント | 内容 |
| ------------ | ---- |
| [Architecture Design](docs/architecture.md) | システム設計書 (Mermaid 図、ER 図、API 仕様) |
| [Setup Guide](docs/setup-guide.md) | 環境構築手順 (Docker / ローカル / Terraform) |
| [Operation Manual](docs/operation-manual.md) | 運用マニュアル (監視 / 障害対応 / 保守) |
| [Cost Estimation](docs/cost-estimation.md) | コスト試算 (クラウド比較 / ROI) |

## Environment Variables

主要な環境変数 (`.env.example` 参照):

```bash
# Application
APP_HOST=0.0.0.0
APP_PORT=8005

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:15435/cs_risk_agent

# Redis
REDIS_URL=redis://localhost:16380/0

# AI Providers (使用するプロバイダーのキーを設定)
AZURE_AI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_AI_API_KEY=your-key
AWS_REGION=ap-northeast-1
GCP_PROJECT_ID=your-project

# AI Orchestration
AI_DEFAULT_PROVIDER=azure
AI_FALLBACK_CHAIN=azure,aws,gcp,ollama
AI_MONTHLY_BUDGET_USD=500.0

# JWT Authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
```

## License

Proprietary - All rights reserved.
