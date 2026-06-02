# ============================================================
# O11yIA BR - Script de Configuração do VSCode (PowerShell)
# Para Windows
# ============================================================

param(
    [string]$ServerUrl = "http://servidor.interno:8080",
    [string]$UserEmail = "$env:USERNAME@empresa.gov.br"
)

Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       O11yIA BR - Configuração do VSCode                 ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "Servidor: $ServerUrl"
Write-Host "Usuário:  $UserEmail"
Write-Host ""

# Path do settings.json
$settingsPath = "$env:APPDATA\Code\User\settings.json"

# Verificar se existe
if (-not (Test-Path (Split-Path $settingsPath))) {
    Write-Host "❌ VSCode não encontrado" -ForegroundColor Red
    exit 1
}

# Backup
if (Test-Path $settingsPath) {
    $backup = "$settingsPath.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $settingsPath $backup
    Write-Host "✓ Backup criado: $backup" -ForegroundColor Green
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
} else {
    $settings = @{}
}

# Adicionar configurações
$settings | Add-Member -NotePropertyName "github.copilot.chat.otel.enabled" -NotePropertyValue $true -Force
$settings | Add-Member -NotePropertyName "github.copilot.chat.otel.otlpEndpoint" -NotePropertyValue "$ServerUrl/v1/traces" -Force
$settings | Add-Member -NotePropertyName "github.copilot.chat.otel.serviceName" -NotePropertyValue "copilot-$UserEmail" -Force
$settings | Add-Member -NotePropertyName "github.copilot.enable" -NotePropertyValue $true -Force

# Salvar
$settings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath -Encoding UTF8

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                   ✓ CONFIGURAÇÃO CONCLUÍDA               ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos passos:"
Write-Host "  1. Reinicie o VSCode"
Write-Host "  2. Use o Copilot normalmente"
Write-Host "  3. Verifique o dashboard em: $($ServerUrl -replace '8080','8501')"
Write-Host ""
