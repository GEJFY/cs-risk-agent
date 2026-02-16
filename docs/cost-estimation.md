# コスト試算

## 前提条件

| 項目 | 値 |
|------|-----|
| 分析対象 | 50社 (親会社) + 連結子会社 200社 |
| 月間 AI 呼び出し | 約 5,000 リクエスト |
| 平均トークン (入力) | 2,000 トークン/リクエスト |
| 平均トークン (出力) | 1,000 トークン/リクエスト |
| SOTA / Cost-Effective 比率 | 20% / 80% |
| 月間合計トークン (入力) | 10M tokens |
| 月間合計トークン (出力) | 5M tokens |

## クラウド別コスト比較

### Azure 構成

| リソース | SKU | 月額 (USD) |
|---------|-----|-----------|
| Azure OpenAI GPT-4o (SOTA 20%) | Standard (30 TPM) | ~$75 |
| Azure OpenAI GPT-4o-mini (CE 80%) | Standard (60 TPM) | ~$6 |
| App Service | B1 (1 core, 1.75GB) | ~$13 |
| PostgreSQL Flexible | B_Standard_B1ms | ~$13 |
| Redis Cache | Basic C0 | ~$16 |
| Key Vault | Standard | ~$1 |
| **Azure 合計** | | **~$124/月** |

### AWS 構成

| リソース | SKU | 月額 (USD) |
|---------|-----|-----------|
| Bedrock Claude 3.5 Sonnet (SOTA 20%) | On-Demand | ~$90 |
| Bedrock Claude 3 Haiku (CE 80%) | On-Demand | ~$5 |
| ECS Fargate | 0.5 vCPU, 1GB | ~$15 |
| RDS PostgreSQL | db.t3.micro | ~$13 |
| ElastiCache Redis | cache.t3.micro | ~$12 |
| Secrets Manager | Standard | ~$1 |
| **AWS 合計** | | **~$136/月** |

### GCP 構成

| リソース | SKU | 月額 (USD) |
|---------|-----|-----------|
| Vertex AI Gemini 1.5 Pro (SOTA 20%) | On-Demand | ~$38 |
| Vertex AI Gemini 1.5 Flash (CE 80%) | On-Demand | ~$2 |
| Cloud Run | 1 vCPU, 512MB | ~$10 |
| Cloud SQL PostgreSQL | db-f1-micro | ~$8 |
| Memorystore Redis | Basic 1GB | ~$35 |
| Secret Manager | Standard | ~$1 |
| **GCP 合計** | | **~$94/月** |

### ローカル構成 (Ollama / vLLM)

| リソース | 仕様 | 費用 |
|---------|------|------|
| GPU サーバー | NVIDIA RTX 4090 (24GB VRAM) | 初期投資 ~$1,600 |
| ソフトウェア | Ollama / vLLM | 無料 (OSS) |
| 電気代 | 450W x 24h x 30日 | ~$30/月 |
| **ランニングコスト** | | **~$30/月** |

## ハイブリッド構成 (推奨)

データ分類に基づいて最適なプロバイダーを自動選択する構成。

| 処理内容 | プロバイダー | 月額 | 備考 |
|---------|------------|------|------|
| 機密データ分析 (20%) | Ollama ローカル | ~$6 | データ外部送出なし |
| 一般分析 (60%) | GCP Gemini Flash | ~$2 | 最低コスト |
| 高精度分析 (20%) | Azure GPT-4o | ~$75 | 最高精度 |
| インフラ (GCP 最小構成) | Cloud Run + SQL | ~$53 | 常時稼働 |
| **ハイブリッド合計** | | **~$136/月** | |

### コスト比較サマリー

```
GCP 単体:        $94/月  ← 最安 (AI コスト最小)
Azure 単体:      $124/月
ハイブリッド:     $136/月 ← 推奨 (セキュリティ + コスト最適)
AWS 単体:        $136/月
ローカルのみ:     $30/月  ← 最安 (GPU 初期投資別)
```

## スケールアップ時の見積もり

| 規模 | リクエスト数/月 | Azure | GCP | ハイブリッド |
|------|---------------|-------|-----|------------|
| 小規模 (子会社 50社) | 5,000 | $124 | $94 | $136 |
| 中規模 (子会社 500社) | 50,000 | $860 | $450 | $580 |
| 大規模 (子会社 2,000社) | 200,000 | $3,100 | $1,600 | $2,000 |

(AI コストはリクエスト数に比例、インフラコストはスケールに応じてアップグレード)

## コスト最適化のポイント

### 1. Model Tiering (効果: 最大 90% 削減)

日常分析は `cost_effective` ティア、重要分析のみ `sota` を使用。

```
例: 全リクエスト SOTA の場合
  Azure GPT-4o: $2.50/1M in + $10.00/1M out = $75/月

Model Tiering 適用 (SOTA 20%, CE 80%):
  GPT-4o (20%):      $15/月
  GPT-4o-mini (80%):  $6/月
  合計: $21/月 (72% 削減)
```

### 2. サーキットブレーカー (効果: 予算超過防止)

```bash
# .env
AI_MONTHLY_BUDGET_USD=500.0       # 月間上限
AI_BUDGET_ALERT_THRESHOLD=0.8     # 80% で警告
AI_CIRCUIT_BREAKER_THRESHOLD=0.95 # 95% で遮断
```

### 3. ハイブリッドモード (効果: 機密データ保護 + コスト削減)

```yaml
# config.yml
ai:
  hybrid_rules:
    - data_classification: confidential
      provider: ollama        # 無料 (ローカル)
    - data_classification: general
      provider: gcp           # $0.075/1M tokens (最安クラウド)
```

### 4. キャッシュ活用 (効果: 重複リクエスト排除)

同一パラメータの分析結果を Redis にキャッシュし、AI 呼び出しを削減。

### 5. バッチ処理 (効果: ピーク分散)

リアルタイム不要の分析はオフピーク時に集約実行し、レートリミット回避とコスト最適化を両立。

## ROI 試算

### 手作業との比較

| 項目 | 手作業 (人件費) | CS Risk Agent |
|------|---------------|---------------|
| 1社あたり分析時間 | 8時間 | 5分 |
| 50社の月次分析 | 400時間 (~2.5人月) | 4時間 (自動) |
| 人件費 (月額) | ~$12,500 | - |
| システムコスト (月額) | - | ~$136 |
| **月間コスト削減** | | **~$12,364** |
| **年間コスト削減** | | **~$148,000** |
| **ROI** | | **~9,100%** |

(人件費: $50/時間で試算。実際の効果は分析範囲・精度要件により異なる)
