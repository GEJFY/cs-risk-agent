# セットアップガイド

## 前提条件

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Git
- (任意) Terraform 1.9+

## ローカル環境構築

### 1. リポジトリクローン

```bash
git clone https://github.com/your-org/cs-risk-agent.git
cd cs-risk-agent
```

### 2. 環境変数設定

```bash
cp .env.example .env
# .env を編集し、APIキー等を設定
```

### 3. Docker Compose 起動 (推奨)

```bash
# DB + Redis + Backend + Frontend を一括起動
docker compose -f infra/docker/docker-compose.yml up -d

# ログ確認
docker compose -f infra/docker/docker-compose.yml logs -f backend
```

アクセス:
- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:3000

### 4. ローカル直接起動

#### Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
uvicorn cs_risk_agent.main:app --reload --port 8000
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

```bash
python scripts/generate_demo_data.py
```

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

`enable_aws = true` または `enable_gcp = true` に設定し、同様に `terraform apply` を実行。

## デモ実行

```bash
# フェイルオーバーデモ
python scripts/demo_failover.py

# ハイブリッドガバナンスデモ
python scripts/demo_hybrid_governance.py

# 異常検知デモ (要: デモデータ生成済み)
python scripts/demo_anomaly_detection.py
```

## テスト実行

```bash
cd backend
pytest                           # 全テスト
pytest tests/unit/               # ユニットテストのみ
pytest --cov --cov-report=html   # カバレッジレポート
```
