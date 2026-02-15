.PHONY: help setup dev test lint format build clean docker-up docker-down migrate

help: ## ヘルプ表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Setup ---
setup: ## 初期セットアップ (venv + deps)
	cd backend && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"
	cd frontend && npm install

setup-backend: ## バックエンドのみセットアップ
	cd backend && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"

setup-frontend: ## フロントエンドのみセットアップ
	cd frontend && npm install

# --- Development ---
dev-backend: ## バックエンド開発サーバー起動 (port 8005)
	cd backend && .venv/Scripts/uvicorn cs_risk_agent.main:app --reload --host 0.0.0.0 --port 8005

dev-frontend: ## フロントエンド開発サーバー起動 (port 3005)
	cd frontend && npx next dev -p 3005

# --- Testing ---
test: ## 全テスト実行
	cd backend && .venv/Scripts/pytest

test-cov: ## カバレッジ付きテスト
	cd backend && .venv/Scripts/pytest --cov=src/cs_risk_agent --cov-report=html --cov-report=term-missing

test-frontend: ## フロントエンドテスト
	cd frontend && npm test

# --- Linting ---
lint: ## Lint実行 (ruff + mypy)
	cd backend && .venv/Scripts/ruff check src/ tests/
	cd backend && .venv/Scripts/mypy src/

lint-fix: ## Lint自動修正
	cd backend && .venv/Scripts/ruff check --fix src/ tests/

format: ## コードフォーマット
	cd backend && .venv/Scripts/ruff format src/ tests/

# --- Database ---
migrate: ## DBマイグレーション実行
	cd backend && .venv/Scripts/alembic upgrade head

migrate-new: ## 新規マイグレーション作成
	cd backend && .venv/Scripts/alembic revision --autogenerate -m "$(MSG)"

# --- Docker ---
docker-up: ## Docker Compose起動
	docker compose -f infra/docker/docker-compose.yml up -d

docker-down: ## Docker Compose停止
	docker compose -f infra/docker/docker-compose.yml down

docker-build: ## Dockerイメージビルド
	docker compose -f infra/docker/docker-compose.yml build

# --- Clean ---
clean: ## キャッシュ・ビルド成果物削除
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/htmlcov backend/.coverage
	rm -rf frontend/.next frontend/out

# --- Demo ---
demo-data: ## デモデータ生成（東洋重工グループ）
	cd backend && .venv/Scripts/python ../scripts/generate_demo_data.py

demo-failover: ## フェイルオーバーデモ実行
	cd backend && .venv/Scripts/python -m scripts.demo_failover

demo-anomaly: ## 異常検知デモ実行
	cd backend && .venv/Scripts/python -m scripts.demo_anomaly_detection
