# =============================================================================
# CS Risk Agent - ワンクリック デモ起動スクリプト
# =============================================================================
# 使い方:  PowerShellで  .\start_demo.ps1
# 停止:    このウィンドウで Enter を押す → バックエンド＆フロントエンド両方停止
# =============================================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  CS Risk Agent - Demo Launcher" -ForegroundColor Cyan
Write-Host "  東洋重工グループ リスク分析デモ" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: .env ---
if (-not (Test-Path "$ProjectRoot\.env")) {
    Write-Host "[1/5] .env ファイル作成中..." -ForegroundColor Yellow
    Copy-Item "$ProjectRoot\.env.example" "$ProjectRoot\.env"
    Write-Host "  -> .env 作成完了" -ForegroundColor Green
} else {
    Write-Host "[1/5] .env OK" -ForegroundColor DarkGray
}

# --- Step 2: Backend venv ---
if (-not (Test-Path "$ProjectRoot\backend\.venv\Scripts\python.exe")) {
    Write-Host "[2/5] Python venv 作成中 (初回のみ・数分かかります)..." -ForegroundColor Yellow
    Push-Location "$ProjectRoot\backend"
    python -m venv .venv
    .\.venv\Scripts\pip install --quiet -e ".[dev]"
    Pop-Location
    Write-Host "  -> venv + 依存パッケージ完了" -ForegroundColor Green
} else {
    Write-Host "[2/5] Python venv OK" -ForegroundColor DarkGray
}

# --- Step 3: Demo data ---
if (-not (Test-Path "$ProjectRoot\demo_data\companies.json")) {
    Write-Host "[3/5] デモデータ生成中..." -ForegroundColor Yellow
    & "$ProjectRoot\backend\.venv\Scripts\python.exe" "$ProjectRoot\scripts\generate_demo_data.py"
    Write-Host "  -> デモデータ生成完了" -ForegroundColor Green
} else {
    Write-Host "[3/5] デモデータ OK" -ForegroundColor DarkGray
}

# --- Step 4: Frontend deps ---
if (-not (Test-Path "$ProjectRoot\frontend\node_modules\.package-lock.json")) {
    Write-Host "[4/5] npm install 中..." -ForegroundColor Yellow
    Push-Location "$ProjectRoot\frontend"
    npm install --silent 2>$null
    Pop-Location
    Write-Host "  -> npm install 完了" -ForegroundColor Green
} else {
    Write-Host "[4/5] node_modules OK" -ForegroundColor DarkGray
}

# --- Step 5: Launch both servers ---
Write-Host ""
Write-Host "[5/5] サーバー起動中..." -ForegroundColor Yellow

# バックエンドを別ウィンドウで起動
$backendProc = Start-Process -FilePath "$ProjectRoot\backend\.venv\Scripts\uvicorn.exe" `
    -ArgumentList "cs_risk_agent.main:app --reload --host 0.0.0.0 --port 8005" `
    -WorkingDirectory "$ProjectRoot\backend" `
    -WindowStyle Normal `
    -PassThru

Start-Sleep -Seconds 3

# フロントエンドを別ウィンドウで起動
$frontendProc = Start-Process -FilePath "npx" `
    -ArgumentList "next dev -p 3005" `
    -WorkingDirectory "$ProjectRoot\frontend" `
    -WindowStyle Normal `
    -PassThru

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  起動完了!" -ForegroundColor Green
Write-Host "" -ForegroundColor White
Write-Host "  Backend API:  http://localhost:8005/docs" -ForegroundColor White
Write-Host "  Frontend UI:  http://localhost:3005" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "  シナリオ: 東洋重工グループ (子会社15社)" -ForegroundColor White
Write-Host "  Critical: 2社  High: 3社  Medium: 3社  Low: 7社" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# ブラウザ自動オープン
Start-Process "http://localhost:8005/docs"
Start-Sleep -Seconds 1
Start-Process "http://localhost:3005"

Write-Host "Enter を押すと両サーバーを停止します..." -ForegroundColor DarkGray
Read-Host

# クリーンアップ
Write-Host "停止中..." -ForegroundColor Yellow
try { Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue } catch {}
try { Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue } catch {}
# npxの子プロセス(node)も停止
Get-Process -Name "node" -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowTitle -match "next" -or $_.CommandLine -match "3005" } |
    Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "停止完了" -ForegroundColor Green
