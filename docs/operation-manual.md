# 運用マニュアル

## 1. ヘルスチェック

### エンドポイント

| エンドポイント | 目的 | チェック内容 |
|--------------|------|-------------|
| `GET /api/v1/health/` | Liveness probe | アプリケーション稼働確認 |
| `GET /api/v1/health/readiness` | Readiness probe | DB + Redis 接続確認 |

### Readiness レスポンス例

```json
{
  "status": "ready",
  "timestamp": "2026-02-17T10:30:00Z",
  "components": {
    "database": {
      "status": "ok",
      "message": "connected",
      "latency_ms": 2.35
    },
    "redis": {
      "status": "ok",
      "message": "connected",
      "latency_ms": 1.12
    }
  }
}
```

`status` が `degraded` の場合、いずれかのコンポーネントが `error` 状態。

## 2. ログ監視

### 構造化ログ (JSON)

全ログは JSON 形式で出力される。主要フィールド:

| フィールド | 説明 | 例 |
|-----------|------|-----|
| `timestamp` | ISO 8601 タイムスタンプ | `2026-02-17T10:30:00Z` |
| `level` | ログレベル | `info` / `warning` / `error` |
| `event` | イベント名 | `router.success` |
| `provider` | AIプロバイダー名 | `azure` / `aws` / `ollama` |
| `cost_usd` | リクエストコスト | `0.0045` |
| `request_id` | リクエスト追跡ID (UUID) | `a1b2c3d4-...` |
| `tokens` | 消費トークン数 | `150` |
| `user_id` | 操作ユーザーID | `user-123` |

### 重要ログイベント一覧

| イベント | レベル | 説明 | 対応 |
|---------|--------|------|------|
| `circuit_breaker.alert` | WARNING | 予算利用率 80% 超過 | コスト状況確認 |
| `circuit_breaker.opened` | ERROR | 予算利用率 95% でブレーカー発動 | 即時対応 (下記参照) |
| `circuit_breaker.monthly_reset` | INFO | 月次予算リセット | 対応不要 |
| `router.provider_failed` | WARNING | プロバイダー障害、フォールバック実行 | 原因調査 |
| `router.success` | INFO | リクエスト正常完了 | 対応不要 |
| `router.stream.provider_failed` | WARNING | ストリーミング中のプロバイダー障害 | 原因調査 |
| `router.hybrid_routing` | INFO | ハイブリッドルーティング発動 | 対応不要 |
| `database_health_check_failed` | ERROR | DB接続失敗 | DB状態確認 |
| `redis_health_check_failed` | ERROR | Redis接続失敗 | Redis状態確認 |
| `readiness_check_degraded` | WARNING | ヘルスチェック異常あり | コンポーネント確認 |

### ログレベル設定

```bash
# .env
LOG_LEVEL=INFO      # 本番推奨
LOG_LEVEL=WARNING   # 低ノイズ運用
LOG_LEVEL=DEBUG     # 開発/トラブルシューティング
LOG_FORMAT=json     # 本番 (構造化ログ)
LOG_FORMAT=console  # 開発 (人間が読みやすい形式)
```

### 監査ログ

全 API リクエストの以下の情報がミドルウェアで自動記録される:

- リクエスト元 IP アドレス (X-Forwarded-For 対応)
- ユーザーID (Bearer トークンから抽出)
- HTTP メソッド + パス
- レスポンスステータスコード
- 処理時間 (ms)

## 3. 予算管理 (FinOps)

### サーキットブレーカー状態遷移

```
CLOSED (正常) ──利用率80%超過──> HALF_OPEN (警告)
HALF_OPEN (警告) ──利用率95%超過──> OPEN (遮断)
OPEN (遮断) ──月次リセット──> CLOSED (正常)
OPEN (遮断) ──手動リセット──> CLOSED (正常)
```

| 状態 | 条件 | 動作 |
|------|------|------|
| **CLOSED** | 利用率 < 80% | 全リクエスト許可 |
| **HALF_OPEN** | 80% <= 利用率 < 95% | 警告ログ出力、リクエストは許可 |
| **OPEN** | 利用率 >= 95% | 新規リクエスト遮断 (`BudgetExceededError`) |

### 予算管理 API

```bash
# 現在の予算状況確認
curl http://localhost:8005/api/v1/admin/budget

# 手動リセット (管理者のみ)
curl -X POST http://localhost:8005/api/v1/admin/budget/reset \
  -H "Authorization: Bearer <admin-token>"

# コストサマリー
curl http://localhost:8005/api/v1/admin/costs
```

### コスト最適化のチェックポイント

1. **Model Tiering 活用**: 日常分析は `cost_effective`、重要分析のみ `sota`
2. **ローカル LLM 活用**: 機密データは Ollama で無料処理
3. **バッチ処理**: リアルタイム不要の分析はオフピーク時に集約実行
4. **予算アラート**: `AI_BUDGET_ALERT_THRESHOLD=0.8` で早期警告

## 4. 認証・認可

### JWT トークン

```bash
# トークン生成 (Python)
from cs_risk_agent.core.security import create_access_token, Role
token = create_access_token(subject="user-id", role=Role.AUDITOR)
```

```bash
# API 呼び出し時のヘッダー
curl http://localhost:8005/api/v1/companies \
  -H "Authorization: Bearer <jwt-token>"
```

### ロール一覧

| ロール | 説明 | 主要権限 |
|--------|------|---------|
| `admin` | システム管理者 | 全権限 |
| `auditor` | 内部監査担当 | 閲覧 + 分析実行 + レポート生成 |
| `cfo` | 最高財務責任者 | 閲覧 + 分析実行 + レポート生成 |
| `ceo` | 最高経営責任者 | 閲覧 + レポート生成 |
| `viewer` | 閲覧専用ユーザー | 閲覧のみ |

## 5. モデル管理

### モデルティア変更

`.env` で環境変数を変更後、アプリケーションを再起動:

```bash
# Azure
AZURE_AI_SOTA_DEPLOYMENT=gpt-4o-2024-11-20
AZURE_AI_COST_EFFECTIVE_DEPLOYMENT=gpt-4o-mini

# AWS
AWS_BEDROCK_SOTA_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
AWS_BEDROCK_COST_EFFECTIVE_MODEL=anthropic.claude-3-haiku-20240307-v1:0

# GCP
GCP_SOTA_MODEL=gemini-1.5-pro
GCP_COST_EFFECTIVE_MODEL=gemini-1.5-flash
```

### 新プロバイダー追加手順

1. `backend/src/cs_risk_agent/ai/providers/` に新プロバイダークラスを作成
2. `AIProvider` プロトコルを実装 (`complete`, `stream`, `embed`, `health_check`, `close`)
3. `ai/registry.py` の `_PROVIDER_FACTORIES` にファクトリ関数を登録
4. `ai/model_tier.py` の `MODEL_PRESETS` にモデル定義を追加
5. `.env.example` に接続設定を追加
6. テストを作成・実行

### プロバイダー状態確認

```bash
# 全プロバイダーの状態
curl http://localhost:8005/api/v1/admin/providers

# ルーター全体の状態 (モード、チェーン、コスト含む)
curl http://localhost:8005/api/v1/admin/status
```

## 6. トラブルシューティング

### 全プロバイダー障害

**症状**: `AllProvidersFailedError` / HTTP 503

**対応手順**:

1. プロバイダー状態確認: `GET /api/v1/admin/providers`
2. 各プロバイダーの API キー有効期限を確認
3. クラウドサービスのステータスページを確認
   - Azure: https://status.azure.com
   - AWS: https://health.aws.amazon.com
   - GCP: https://status.cloud.google.com
4. ローカル LLM への緊急切替: `AI_MODE=local` (Ollama 稼働中の場合)

### 予算超過でリクエスト遮断

**症状**: `BudgetExceededError` / HTTP 429

**対応手順**:

1. 現在の利用状況確認: `GET /api/v1/admin/budget`
2. コスト内訳確認: `GET /api/v1/admin/costs`
3. 対策を選択:
   - `cost_effective` ティアへの切替 (コスト大幅削減)
   - `AI_MONTHLY_BUDGET_USD` の引き上げ
   - 緊急時: 管理者による手動予算リセット

### DB 接続エラー

**症状**: ヘルスチェック `database.status = "error"`

**対応手順**:

1. PostgreSQL サービス稼働確認: `docker compose ps db`
2. 接続テスト: `psql -h localhost -p 15435 -U postgres -d cs_risk_agent`
3. `DATABASE_URL` の接続文字列確認
4. ファイアウォール / セキュリティグループ確認
5. コネクションプール枯渇の場合: `pool_size` / `max_overflow` の調整

### Redis 接続エラー

**症状**: ヘルスチェック `redis.status = "error"`

**対応手順**:

1. Redis サービス稼働確認: `docker compose ps redis`
2. 接続テスト: `redis-cli -h localhost -p 16380 ping`
3. `REDIS_URL` の接続文字列確認
4. メモリ使用量確認: `redis-cli -p 16380 info memory`

### フロントエンド API 接続エラー

**対応手順**:

1. Backend の起動確認: `curl http://localhost:8005/api/v1/health/`
2. `NEXT_PUBLIC_API_URL` が正しいか確認 (通常 `http://localhost:8005`)
3. CORS 設定を確認 (`CORS_ORIGINS` 環境変数)
4. ブラウザの開発者ツールで実際のエラーメッセージを確認

### 分析結果が不正確

**対応手順**:

1. 入力データの品質確認 (欠損値、異常値)
2. デモデータの場合: 意図的に 7.9% の異常仕訳が含まれている
3. ルールエンジンの閾値調整が必要な場合: `analysis/rule_engine.py` の各ルール条件を確認
4. 不正予測モデルの再学習が必要な場合: `FraudPredictor.train()` で新データで学習

## 7. バックアップ・リカバリ

### データベースバックアップ

```bash
# 手動バックアップ (ローカル Docker 環境)
docker compose -f infra/docker/docker-compose.yml exec db \
  pg_dump -U postgres cs_risk_agent > backup_$(date +%Y%m%d).sql

# リストア
docker compose -f infra/docker/docker-compose.yml exec -T db \
  psql -U postgres cs_risk_agent < backup_20260217.sql
```

### クラウド環境

| プロバイダー | サービス | 自動バックアップ | 保持期間 |
|------------|---------|:---------------:|---------|
| Azure | PostgreSQL Flexible Server | o | 35日 |
| AWS | RDS | o | 7日 (最大35日) |
| GCP | Cloud SQL | o | 7日 (PITR対応) |

### 災害復旧 (DR) チェックリスト

1. DB バックアップの存在確認 (日次)
2. バックアップからのリストアテスト (月次)
3. `.env` / シークレットのバックアップ (変更時)
4. Terraform state ファイルのバックアップ (変更時)
5. アプリケーションのバージョン記録

## 8. 定期メンテナンス

### 日次

- ヘルスチェック確認 (`/api/v1/health/readiness`)
- 予算利用率確認 (`/api/v1/admin/budget`)
- エラーログ確認 (`LOG_LEVEL=ERROR` のログエントリ)

### 週次

- プロバイダー状態確認 (`/api/v1/admin/providers`)
- コストトレンド確認 (`/api/v1/admin/costs`)
- ディスク使用量確認 (特にログファイル)

### 月次

- 予算自動リセットの確認
- DB バックアップリストアテスト
- 依存パッケージのセキュリティ更新確認
- API キー / シークレットのローテーション
