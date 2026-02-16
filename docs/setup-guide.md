# セットアップガイド

## 前提条件

| ソフトウェア | バージョン | 必須 | 備考 |
|------------|-----------|:----:|------|
| Python | 3.11+ | o | 3.11 推奨 (安定性) |
| Node.js | 20+ | o | フロントエンドビルド用 |
| Docker & Docker Compose | 最新版 | o | ローカル DB/Redis 起動用 |
| Git | 最新版 | o | |
| PostgreSQL | 16 | - | Docker 使用時は不要 |
| Redis | 7 | - | Docker 使用時は不要 |
| Terraform | 1.9+ | - | クラウドデプロイ時のみ |
| Ollama | 最新版 | - | ローカル LLM 使用時のみ |

## ローカル環境構築

### 1. リポジトリクローン

```bash
git clone https://github.com/GEJFY/cs-risk-agent.git
cd cs-risk-agent
```

### 2. 環境変数設定

```bash
cp .env.example .env
```

`.env` ファイルを編集し、使用するプロバイダーの認証情報を設定する。

#### 環境変数リファレンス

**アプリケーション基本設定**

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `APP_ENV` | `development` | 実行環境 (`development` / `staging` / `production`) |
| `APP_DEBUG` | `true` | デバッグモード |
| `APP_SECRET_KEY` | - | アプリケーションシークレット (本番では必ず変更) |
| `APP_PORT` | `8005` | バックエンドポート |

**データベース**

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `DATABASE_URL` | `postgresql+asyncpg://...localhost:5432/cs_risk_agent` | 非同期接続URL |
| `DATABASE_SYNC_URL` | `postgresql://...localhost:5432/cs_risk_agent` | 同期接続URL (マイグレーション用) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 接続URL |

**AI プロバイダー** (使用するものだけ設定)

| 変数 | 説明 |
|------|------|
| `AZURE_AI_ENDPOINT` | Azure AI Foundry エンドポイント |
| `AZURE_AI_API_KEY` | Azure API キー |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | AWS 認証情報 |
| `GCP_PROJECT_ID` | GCP プロジェクト ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP サービスアカウントキーパス |
| `OLLAMA_BASE_URL` | Ollama サーバー URL (デフォルト: `http://localhost:11434`) |

**AI オーケストレーション**

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `AI_DEFAULT_PROVIDER` | `azure` | デフォルト AI プロバイダー |
| `AI_FALLBACK_CHAIN` | `azure,aws,gcp,ollama` | フォールバック順序 (カンマ区切り) |
| `AI_MODE` | `cloud` | 動作モード (`cloud` / `local` / `hybrid`) |
| `AI_MONTHLY_BUDGET_USD` | `500.0` | 月間予算上限 (USD) |
| `AI_BUDGET_ALERT_THRESHOLD` | `0.8` | 予算アラート閾値 (80%) |
| `AI_CIRCUIT_BREAKER_THRESHOLD` | `0.95` | サーキットブレーカー閾値 (95%) |

**JWT 認証**

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `JWT_SECRET_KEY` | - | JWT 署名キー (本番では必ず変更) |
| `JWT_ALGORITHM` | `HS256` | 署名アルゴリズム |
| `JWT_EXPIRATION_MINUTES` | `60` | トークン有効期限 (分) |

**可観測性**

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `LOG_LEVEL` | `INFO` | ログレベル (`DEBUG` / `INFO` / `WARNING` / `ERROR`) |
| `LOG_FORMAT` | `json` | ログ形式 (`json` / `console`) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OpenTelemetry エンドポイント |

### 3. Docker Compose 起動 (推奨)

```bash
# DB + Redis + Backend + Frontend を一括起動
docker compose -f infra/docker/docker-compose.yml up -d

# ログ確認
docker compose -f infra/docker/docker-compose.yml logs -f backend

# 停止
docker compose -f infra/docker/docker-compose.yml down
```

アクセス先:

| サービス | URL |
|---------|-----|
| Backend API (Swagger UI) | http://localhost:8005/docs |
| Frontend Dashboard | http://localhost:3005 |
| PostgreSQL | `localhost:15435` |
| Redis | `localhost:16380` |

### 4. ローカル直接起動

DB と Redis は Docker で起動し、Backend/Frontend はローカルで直接実行する方式。

#### DB + Redis 起動

```bash
docker compose -f infra/docker/docker-compose.yml up -d db redis
```

#### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
uvicorn cs_risk_agent.main:app --reload --port 8005
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. データベースマイグレーション

```bash
cd backend
alembic upgrade head
```

### 6. デモデータ投入

東洋重工グループ (1社 + 15子会社) のデモデータを生成:

```bash
python scripts/generate_demo_data.py
```

生成されるデータ:

| ファイル | 内容 |
|---------|------|
| `demo_data/companies.json` | 企業マスタ (16社) |
| `demo_data/subsidiaries.json` | 子会社詳細 (15社、10ヶ国、6セグメント) |
| `demo_data/financial_statements.csv` | 財務諸表 (128期間) |
| `demo_data/journal_entries.csv` | 仕訳データ (1,520件 + 120異常仕訳) |
| `demo_data/risk_scores.json` | 事前計算リスクスコア |
| `demo_data/alerts.json` | アラート (8件) |

## クラウド環境構築

### Azure

```bash
cd infra/terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars を編集

terraform init
terraform plan
terraform apply
```

### AWS / GCP

`terraform.tfvars` で `enable_aws = true` または `enable_gcp = true` に設定し、同様に `terraform apply` を実行。

### Terraform モジュール構成

```
infra/terraform/
├── modules/
│   ├── azure/    # Azure AI Foundry, App Service, PostgreSQL, Redis, Key Vault
│   ├── aws/      # Bedrock, ECS Fargate, RDS, ElastiCache, Secrets Manager
│   └── gcp/      # Vertex AI, Cloud Run, Cloud SQL, Memorystore, Secret Manager
└── environments/
    ├── dev/      # 開発環境
    ├── staging/  # ステージング環境
    └── prod/     # 本番環境
```

## デモ実行

```bash
# フェイルオーバーデモ
# Azure 障害時の AWS 自動切替を実演
python scripts/demo_failover.py

# ハイブリッドガバナンスデモ
# データ分類に基づくローカル/クラウド自動ルーティング
python scripts/demo_hybrid_governance.py

# 異常検知デモ (要: デモデータ生成済み)
# ベンフォード分析 + ルールエンジンによる不正検出
python scripts/demo_anomaly_detection.py
```

## テスト実行

```bash
cd backend

# 全テスト実行
pytest

# ユニットテストのみ
pytest tests/unit/

# E2E テスト
pytest tests/e2e/

# カバレッジレポート (HTML)
pytest --cov --cov-report=html
# → htmlcov/index.html をブラウザで開く

# 特定テストのみ
pytest tests/unit/test_rule_engine.py -v

# Lint チェック
ruff check src/

# 型チェック
mypy src/
```

### フロントエンドテスト

```bash
cd frontend

# ユニットテスト
npm run test

# E2E テスト (Playwright)
npx playwright test
```

## トラブルシューティング

### ポート競合

Docker Compose はデフォルトで以下のポートを使用する。競合する場合は `docker-compose.yml` で変更する。

| ポート | サービス |
|--------|---------|
| 15435 | PostgreSQL |
| 16380 | Redis |
| 8005 | Backend API |
| 3005 | Frontend |

### Python パッケージインストールエラー

```bash
# ビルドツール不足の場合
pip install --upgrade pip setuptools wheel

# Windows で lxml / psycopg2 のビルドに失敗する場合
pip install --only-binary :all: lxml psycopg2-binary
```

### OneDrive 環境での注意事項

OneDrive 同期フォルダ内で `venv` を作成するとシンボリックリンクの問題が発生する場合がある。

```bash
# 一時的に OneDrive 同期を無効化してから venv 作成
python -m venv .venv --copies
```

### データベース接続エラー

```bash
# Docker で DB が起動しているか確認
docker compose -f infra/docker/docker-compose.yml ps

# DB への直接接続テスト
psql -h localhost -p 15435 -U postgres -d cs_risk_agent

# ヘルスチェック API で確認
curl http://localhost:8005/api/v1/health/readiness
```
