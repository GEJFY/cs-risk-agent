# コスト試算

## 前提条件

- 分析対象: 50社（連結子会社200社）
- 月間AI呼び出し: 約5,000リクエスト
- 平均トークン: 入力2,000 / 出力1,000 トークン/リクエスト
- モード: SOTA 20% / Cost-Effective 80%

## Azure 構成

| リソース | SKU | 月額 (USD) |
|---------|-----|-----------|
| Azure OpenAI GPT-4o | Standard (30 TPM) | ~$75 |
| Azure OpenAI GPT-4o-mini | Standard (60 TPM) | ~$6 |
| App Service | B1 (1 core, 1.75GB) | ~$13 |
| PostgreSQL Flexible | B_Standard_B1ms | ~$13 |
| Redis Cache | Basic C0 | ~$16 |
| Key Vault | Standard | ~$1 |
| **Azure 合計** | | **~$124/月** |

## AWS 構成

| リソース | SKU | 月額 (USD) |
|---------|-----|-----------|
| Bedrock Claude 3.5 Sonnet | On-Demand | ~$90 |
| Bedrock Claude 3 Haiku | On-Demand | ~$5 |
| ECS Fargate | 0.5 vCPU, 1GB | ~$15 |
| RDS PostgreSQL | db.t3.micro | ~$13 |
| ElastiCache Redis | cache.t3.micro | ~$12 |
| Secrets Manager | Standard | ~$1 |
| **AWS 合計** | | **~$136/月** |

## GCP 構成

| リソース | SKU | 月額 (USD) |
|---------|-----|-----------|
| Vertex AI Gemini 1.5 Pro | On-Demand | ~$38 |
| Vertex AI Gemini 1.5 Flash | On-Demand | ~$2 |
| Cloud Run | 1 vCPU, 512MB | ~$10 |
| Cloud SQL PostgreSQL | db-f1-micro | ~$8 |
| Memorystore Redis | Basic 1GB | ~$35 |
| Secret Manager | Standard | ~$1 |
| **GCP 合計** | | **~$94/月** |

## ローカル構成 (Ollama)

| リソース | 仕様 | 費用 |
|---------|------|------|
| GPU サーバー | NVIDIA RTX 4090 | 初期投資 (電気代のみ) |
| ソフトウェア | Ollama / vLLM | 無料 |
| **ランニングコスト** | | **~$30/月 (電気代)** |

## ハイブリッド構成 (推奨)

| 処理内容 | プロバイダー | 月額 |
|---------|------------|------|
| 機密データ分析 (20%) | Ollama ローカル | ~$6 |
| 一般分析 (60%) | GCP Gemini Flash | ~$2 |
| 高精度分析 (20%) | Azure GPT-4o | ~$75 |
| インフラ (GCP最小構成) | Cloud Run + SQL | ~$53 |
| **ハイブリッド合計** | | **~$136/月** |

## コスト最適化のポイント

1. **Model Tiering**: 日常分析は Cost-Effective、重要分析のみ SOTA
2. **サーキットブレーカー**: 月額予算上限を設定し超過を防止
3. **キャッシュ**: 同一クエリの結果を Redis キャッシュ
4. **バッチ処理**: リアルタイム不要の分析はオフピーク時に実行
