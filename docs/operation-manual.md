# 運用マニュアル

## 1. ログ監視

### 構造化ログ (JSON)

全ログは JSON 形式で出力される。主要フィールド:

| フィールド | 説明 |
|-----------|------|
| `timestamp` | ISO 8601 タイムスタンプ |
| `level` | ログレベル (INFO/WARNING/ERROR) |
| `event` | イベント名 |
| `provider` | AIプロバイダー名 |
| `cost_usd` | リクエストコスト |
| `request_id` | リクエスト追跡ID |

### 重要ログイベント

```
circuit_breaker.alert        # 予算アラート閾値超過 (80%)
circuit_breaker.opened       # サーキットブレーカー発動 (95%)
circuit_breaker.monthly_reset # 月次リセット
router.provider_failed       # プロバイダー障害 → フォールバック
router.success               # リクエスト成功
audit                        # 監査ログエントリ
```

### ログレベル設定

```bash
# .env
LOG_LEVEL=INFO    # 本番推奨
LOG_LEVEL=DEBUG   # 開発/トラブルシューティング
```

## 2. 予算管理 (FinOps)

### サーキットブレーカー状態

| 状態 | 条件 | 動作 |
|------|------|------|
| CLOSED | 利用率 < 80% | 正常稼働 |
| HALF_OPEN | 80% ≤ 利用率 < 95% | 警告ログ出力 |
| OPEN | 利用率 ≥ 95% | リクエスト遮断 |

### 予算確認 API

```bash
curl http://localhost:8000/api/v1/admin/budget
```

### 予算リセット

月初に自動リセット。手動リセット:
```bash
curl -X POST http://localhost:8000/api/v1/admin/budget/reset
```

## 3. モデル更新

### モデルティア変更

`.env` で環境変数を変更:
```bash
AZURE_SOTA_DEPLOYMENT=gpt-4o-2024-11-20
AZURE_COST_EFFECTIVE_DEPLOYMENT=gpt-4o-mini
```

### 新プロバイダー追加

1. `ai/providers/` に新プロバイダークラスを作成
2. `AIProvider` を継承し `complete/stream/embed` を実装
3. `ai/registry.py` の `_PROVIDER_FACTORIES` に登録

## 4. トラブルシューティング

### 全プロバイダー障害

**症状**: `AllProvidersFailedError`
**対応**:
1. `GET /api/v1/admin/providers` で各プロバイダー状態確認
2. APIキー有効期限を確認
3. クラウドサービスのステータスページを確認
4. `AI_MODE=local` に切替 (Ollama稼働中の場合)

### 予算超過でリクエスト遮断

**症状**: `BudgetExceededError`
**対応**:
1. `GET /api/v1/admin/budget` で現在の利用状況確認
2. `AI_MONTHLY_BUDGET_USD` の値を見直し
3. `cost_effective` ティアへの切替を検討
4. 緊急時: 管理者による予算リセット

### DB接続エラー

**対応**:
1. PostgreSQL サービス稼働確認
2. `DATABASE_URL` の接続文字列確認
3. ファイアウォール/セキュリティグループ確認

### フロントエンド API接続エラー

**対応**:
1. Backend が起動していることを確認
2. `NEXT_PUBLIC_API_URL` が正しいか確認
3. CORS 設定を確認 (`main.py` の `allow_origins`)

## 5. バックアップ・リカバリ

### データベースバックアップ

```bash
# 手動バックアップ
pg_dump -h localhost -U postgres cs_risk_agent > backup_$(date +%Y%m%d).sql

# リストア
psql -h localhost -U postgres cs_risk_agent < backup_20240101.sql
```

### クラウド環境

- Azure: PostgreSQL Flexible Server の自動バックアップ (30日保持)
- AWS: RDS 自動スナップショット
- GCP: Cloud SQL PITR (本番環境)
