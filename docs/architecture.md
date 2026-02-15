# アーキテクチャ設計書

## 1. システム概要

CS Risk Agent は、連結子会社のリスク分析を行うエンタープライズ向け マルチクラウド AI オーケストレーターである。

### 設計原則

- **Provider Pattern**: マルチクラウド AI プロバイダーを透過的に抽象化
- **Hybrid Deployment**: クラウド / ローカル LLM の構成ファイルベース切替
- **FinOps**: サーキットブレーカーによる予算管理
- **Observability**: 構造化ログ + OpenTelemetry + 監査ログ

## 2. 5層アーキテクチャ

```mermaid
graph TB
    subgraph "Layer 1: Presentation"
        NextJS[Next.js Dashboard]
        SwaggerUI[Swagger UI]
    end

    subgraph "Layer 2: API Gateway"
        FastAPI[FastAPI REST API]
        Auth[JWT Auth + RBAC]
        Audit[Audit Middleware]
        CORS[CORS Middleware]
    end

    subgraph "Layer 3: Business Logic"
        subgraph "AI Orchestration"
            Router[Model Router]
            CB[Circuit Breaker]
            CT[Cost Tracker]
            Tier[Model Tier Manager]
        end
        subgraph "Analysis Engines"
            DA[Discretionary Accruals]
            FP[Fraud Prediction]
            RE[Rule Engine - 26 Rules]
            BF[Benford Analysis]
            RS[Risk Scorer]
        end
        subgraph "AI Agents - LangGraph"
            Orch[Orchestrator]
            AP[Anomaly Probe]
            RP[Ratio Probe]
            TP[Trend Probe]
            RelP[Relationship Probe]
            XRP[Cross-Reference Probe]
        end
    end

    subgraph "Layer 4: Provider Abstraction"
        Azure[Azure AI Foundry]
        AWS[AWS Bedrock]
        GCP[GCP Vertex AI]
        Ollama[Ollama Local]
        VLLM[vLLM Local]
    end

    subgraph "Layer 5: Data & Infrastructure"
        PG[(PostgreSQL 16)]
        Redis[(Redis 7)]
        ETL[ETL Pipeline]
        EDINET[EDINET API]
    end

    NextJS --> FastAPI
    FastAPI --> Auth --> Audit
    FastAPI --> Router
    Router --> CB --> CT
    Router --> Azure & AWS & GCP & Ollama & VLLM
    FastAPI --> DA & FP & RE & BF
    FastAPI --> Orch
    Orch --> AP & RP & TP & RelP & XRP
    FastAPI --> PG
    FastAPI --> Redis
    ETL --> EDINET
    ETL --> PG
```

## 3. AI Orchestration Layer

### Provider Pattern

```mermaid
classDiagram
    class AIProvider {
        <<abstract>>
        +name: str
        +is_available: bool
        +complete(messages, model) AIResponse
        +stream(messages, model) AsyncIterator
        +embed(texts, model) EmbeddingResponse
        +health_check() bool
    }

    class AzureFoundryProvider {
        -_client: ChatCompletionsClient
        +complete()
        +stream()
    }

    class AWSBedrockProvider {
        -_client: boto3.Client
        +complete()
        +stream()
    }

    class GCPVertexProvider {
        -_model: GenerativeModel
        +complete()
        +stream()
    }

    class OllamaLocalProvider {
        -_client: AsyncClient
        +complete()
        +stream()
    }

    AIProvider <|-- AzureFoundryProvider
    AIProvider <|-- AWSBedrockProvider
    AIProvider <|-- GCPVertexProvider
    AIProvider <|-- OllamaLocalProvider
```

### フォールバックチェーン

```mermaid
sequenceDiagram
    participant Client
    participant Router as Model Router
    participant CB as Circuit Breaker
    participant Azure
    participant AWS
    participant GCP
    participant Ollama

    Client->>Router: complete(messages)
    Router->>CB: check_budget()
    CB-->>Router: OK
    Router->>Azure: complete()
    Azure--xRouter: Error (503)
    Router->>AWS: complete() [fallback]
    AWS-->>Router: Response
    Router->>CB: record_usage()
    Router-->>Client: AIResponse (provider=aws)
```

### Model Tiering

| Provider | SOTA | Cost-Effective |
|----------|------|----------------|
| Azure | GPT-4o ($2.50/1M in) | GPT-4o-mini ($0.15/1M in) |
| AWS | Claude 3.5 Sonnet ($3.00/1M in) | Claude 3 Haiku ($0.25/1M in) |
| GCP | Gemini 1.5 Pro ($1.25/1M in) | Gemini 1.5 Flash ($0.075/1M in) |
| Ollama | Llama 3.1 70B (無料) | Llama 3.1 8B (無料) |

## 4. 分析エンジン

### 統合リスクスコアリング

```mermaid
graph LR
    DA[裁量的発生高<br>Weight: 30%] --> RS[統合リスクスコア<br>0-100]
    FP[不正予測<br>Weight: 30%] --> RS
    RE[ルールエンジン<br>Weight: 25%] --> RS
    BF[ベンフォード<br>Weight: 15%] --> RS
    RS --> CL{リスクレベル}
    CL -->|≥80| Critical[🔴 Critical]
    CL -->|≥60| High[🟠 High]
    CL -->|≥40| Medium[🟡 Medium]
    CL -->|<40| Low[🟢 Low]
```

## 5. デプロイメントパターン

### パターン1: クラウドネイティブ (推奨)

```mermaid
graph TB
    subgraph "Azure"
        AzureAI[Azure AI Foundry]
        AzureKV[Key Vault]
        AzureApp[App Service]
        AzureDB[(PostgreSQL Flexible)]
        AzureRedis[(Redis Cache)]
    end

    subgraph "AWS"
        Bedrock[Bedrock]
        SM[Secrets Manager]
        ECS[ECS Fargate]
    end

    subgraph "GCP"
        VertexAI[Vertex AI]
        GSM[Secret Manager]
        CloudRun[Cloud Run]
    end
```

### パターン2: ハイブリッド

- 機密データ → ローカル Ollama/vLLM
- 一般データ → クラウド AI (Azure/AWS/GCP)
- 構成: `config.yml` の `hybrid_rules` で制御

### パターン3: フルローカル

- 全処理をローカル Ollama/vLLM で実行
- インターネット接続不要
- 構成: `AI_MODE=local`

## 6. セキュリティ

- **認証**: JWT (HS256) + RBAC (5ロール)
- **シークレット**: 各クラウドの Secret Manager (Key Vault / SM / GSM)
- **通信**: TLS 1.2+ 必須
- **監査**: 全AI操作の入出力を監査ログに記録
- **データ分類**: confidential / internal / general / public
