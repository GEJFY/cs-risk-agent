"""Prometheus メトリクス定義."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Info

# --- アプリケーション情報 ---
APP_INFO = Info("cs_risk_agent", "Application information")

# --- AI リクエストメトリクス ---
AI_REQUESTS_TOTAL = Counter(
    "ai_requests_total",
    "Total AI requests",
    ["provider", "model", "tier", "status"],
)

AI_REQUEST_DURATION = Histogram(
    "ai_request_duration_seconds",
    "AI request duration",
    ["provider", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

AI_TOKENS_TOTAL = Counter(
    "ai_tokens_total",
    "Total tokens consumed",
    ["provider", "model", "direction"],  # direction: input/output
)

AI_COST_USD = Counter(
    "ai_cost_usd_total",
    "Total AI cost in USD",
    ["provider", "model"],
)

# --- サーキットブレーカーメトリクス ---
CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
)

BUDGET_USAGE_RATIO = Gauge(
    "budget_usage_ratio",
    "Budget usage ratio (0.0 to 1.0+)",
)

# --- 分析メトリクス ---
ANALYSIS_RUNS_TOTAL = Counter(
    "analysis_runs_total",
    "Total analysis runs",
    ["analysis_type", "status"],
)

ANALYSIS_DURATION = Histogram(
    "analysis_duration_seconds",
    "Analysis execution duration",
    ["analysis_type"],
    buckets=[0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# --- API メトリクス ---
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
)

# --- リスクスコアメトリクス ---
RISK_SCORES_CALCULATED = Counter(
    "risk_scores_calculated_total",
    "Total risk scores calculated",
    ["risk_level"],
)

HIGH_RISK_COMPANIES = Gauge(
    "high_risk_companies_count",
    "Number of companies with high/critical risk",
)
