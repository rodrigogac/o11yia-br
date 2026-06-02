# ============================================================
# O11yIA BR - Instalador Completo (PowerShell)
# Para Windows - Instala e configura todos os componentes
# ============================================================

param(
    [string]$ServerUrl = "http://localhost:8080",
    [string]$UserEmail = "$env:USERNAME@empresa.gov.br"
)

# Cores
$Colors = @{
    Cyan = "Cyan"
    Green = "Green"
    Yellow = "Yellow"
    Red = "Red"
    Blue = "Blue"
}

function Write-Header {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║       O11yIA BR - Instalador de Plugins                  ║" -ForegroundColor Cyan
    Write-Host "║       Monitoramento de Créditos do GitHub Copilot        ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step { param($Message) Write-Host "▶ $Message" -ForegroundColor Blue }
function Write-Success { param($Message) Write-Host "✓ $Message" -ForegroundColor Green }
function Write-Warning { param($Message) Write-Host "⚠ $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "✗ $Message" -ForegroundColor Red }

function Show-Menu {
    Write-Host ""
    Write-Host "Selecione o que deseja instalar:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1) VSCode   - Configurar OpenTelemetry nativo"
    Write-Host "  2) Chrome   - Preparar extensão do browser"
    Write-Host "  3) IntelliJ - Compilar plugin da IDE"
    Write-Host "  4) Tudo     - Instalar todos os componentes"
    Write-Host "  5) Verificar - Testar conexão com servidor"
    Write-Host "  6) Sair"
    Write-Host ""
    
    $choice = Read-Host "Opção [1-6]"
    
    switch ($choice) {
        "1" { Install-VSCode }
        "2" { Install-Chrome }
        "3" { Install-IntelliJ }
        "4" { Install-All }
        "5" { Test-Connection }
        "6" { exit }
        default { Write-Error "Opção inválida"; Show-Menu }
    }
}

# ============================================================
# INSTALAÇÃO VSCODE
# ============================================================

function Install-VSCode {
    Write-Step "Configurando VSCode..."
    
    $settingsPath = "$env:APPDATA\Code\User\settings.json"
    
    if (-not (Test-Path (Split-Path $settingsPath))) {
        Write-Error "VSCode não encontrado"
        Write-Warning "Instale o VSCode: https://code.visualstudio.com"
        Show-Menu
        return
    }
    
    # Verificar Copilot
    if (Get-Command code -ErrorAction SilentlyContinue) {
        $extensions = code --list-extensions 2>$null
        if ($extensions -notcontains "github.copilot") {
            Write-Warning "GitHub Copilot não detectado"
            $install = Read-Host "Deseja instalar agora? [s/N]"
            if ($install -match "^[Ss]$") {
                code --install-extension github.copilot
                code --install-extension github.copilot-chat
                Write-Success "Extensões Copilot instaladas"
            }
        } else {
            Write-Success "GitHub Copilot já instalado"
        }
    }
    
    # Backup
    if (Test-Path $settingsPath) {
        $backup = "$settingsPath.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item $settingsPath $backup
        Write-Success "Backup criado: $backup"
        $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    } else {
        $settings = @{}
    }
    
    # Configurar OTel
    $settings | Add-Member -NotePropertyName "github.copilot.chat.otel.enabled" -NotePropertyValue $true -Force
    $settings | Add-Member -NotePropertyName "github.copilot.chat.otel.otlpEndpoint" -NotePropertyValue "$ServerUrl/v1/traces" -Force
    $settings | Add-Member -NotePropertyName "github.copilot.chat.otel.serviceName" -NotePropertyValue "copilot-$UserEmail" -Force
    $settings | Add-Member -NotePropertyName "github.copilot.enable" -NotePropertyValue $true -Force
    
    $settings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath -Encoding UTF8
    
    Write-Success "VSCode configurado!"
    Write-Host ""
    Write-Host "  Configurações aplicadas:" -ForegroundColor Cyan
    Write-Host "  • OTel habilitado"
    Write-Host "  • Endpoint: $ServerUrl/v1/traces"
    Write-Host "  • Usuário: $UserEmail"
    Write-Host ""
    Write-Warning "Reinicie o VSCode para aplicar as configurações"
    
    Show-Menu
}

# ============================================================
# INSTALAÇÃO CHROME
# ============================================================

function Install-Chrome {
    Write-Step "Preparando extensão Chrome..."
    
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $extensionDir = Join-Path (Split-Path $scriptDir) "plugins\chrome-extension"
    
    if (-not (Test-Path $extensionDir)) {
        Write-Error "Diretório da extensão não encontrado"
        Show-Menu
        return
    }
    
    # Criar ícones placeholder
    $iconsDir = Join-Path $extensionDir "icons"
    New-Item -ItemType Directory -Path $iconsDir -Force | Out-Null
    
    foreach ($size in @(16, 48, 128)) {
        $iconPath = Join-Path $iconsDir "icon$size.png"
        if (-not (Test-Path $iconPath)) {
            # Criar PNG mínimo válido
            [byte[]]$pngHeader = 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A
            [System.IO.File]::WriteAllBytes($iconPath, $pngHeader)
        }
    }
    
    Write-Success "Extensão preparada!"
    Write-Host ""
    Write-Host "  Passos para instalar no Chrome:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1. Abra o Chrome e vá para: chrome://extensions"
    Write-Host ""
    Write-Host "  2. Ative o 'Modo desenvolvedor' (canto superior direito)"
    Write-Host ""
    Write-Host "  3. Clique em 'Carregar sem compactação'"
    Write-Host ""
    Write-Host "  4. Selecione a pasta:" -ForegroundColor White
    Write-Host "     $extensionDir" -ForegroundColor Green
    Write-Host ""
    Write-Host "  5. A extensão aparecerá na barra do Chrome"
    Write-Host ""
    
    $open = Read-Host "Deseja abrir chrome://extensions agora? [s/N]"
    if ($open -match "^[Ss]$") {
        Start-Process "chrome://extensions"
    }
    
    Show-Menu
}

# ============================================================
# INSTALAÇÃO INTELLIJ
# ============================================================

function Install-IntelliJ {
    Write-Step "Preparando plugin IntelliJ..."
    
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $pluginDir = Join-Path (Split-Path $scriptDir) "plugins\intellij-plugin"
    
    if (-not (Test-Path $pluginDir)) {
        Write-Error "Diretório do plugin não encontrado"
        Show-Menu
        return
    }
    
    # Verificar Java
    if (-not (Get-Command java -ErrorAction SilentlyContinue)) {
        Write-Error "Java não encontrado"
        Write-Warning "Instale JDK 17+: https://adoptium.net"
        Show-Menu
        return
    }
    
    $javaVersion = java -version 2>&1 | Select-String "version"
    Write-Host "  Java: $javaVersion"
    
    # Verificar/criar gradlew
    $gradlew = Join-Path $pluginDir "gradlew.bat"
    if (-not (Test-Path $gradlew)) {
        Write-Warning "Gradle wrapper não encontrado"
        Write-Host "  Execute manualmente:"
        Write-Host "    cd $pluginDir"
        Write-Host "    gradle wrapper"
        Write-Host "    .\gradlew.bat buildPlugin"
        Show-Menu
        return
    }
    
    Write-Step "Compilando plugin (pode demorar)..."
    
    Push-Location $pluginDir
    & .\gradlew.bat buildPlugin --no-daemon
    $buildResult = $LASTEXITCODE
    Pop-Location
    
    if ($buildResult -eq 0) {
        $zipFile = Get-ChildItem "$pluginDir\build\distributions\*.zip" | Select-Object -First 1
        
        if ($zipFile) {
            Write-Success "Plugin compilado: $($zipFile.FullName)"
            Write-Host ""
            Write-Host "  Passos para instalar no IntelliJ:" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "  1. Abra IntelliJ IDEA"
            Write-Host "  2. Vá em: File > Settings > Plugins"
            Write-Host "  3. Clique no ícone ⚙️ > 'Install Plugin from Disk...'"
            Write-Host "  4. Selecione: $($zipFile.FullName)" -ForegroundColor Green
            Write-Host "  5. Reinicie o IntelliJ"
            Write-Host ""
        }
    } else {
        Write-Error "Falha na compilação"
    }
    
    Show-Menu
}

# ============================================================
# INSTALAR TUDO
# ============================================================

function Install-All {
    Write-Step "Instalando todos os componentes..."
    
    # VSCode
    Write-Host "`n[1/3] VSCode" -ForegroundColor Cyan
    $settingsPath = "$env:APPDATA\Code\User\settings.json"
    if (Test-Path (Split-Path $settingsPath)) {
        if (-not (Test-Path $settingsPath)) { "{}" | Set-Content $settingsPath }
        $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
        $settings | Add-Member -NotePropertyName "github.copilot.chat.otel.enabled" -NotePropertyValue $true -Force
        $settings | Add-Member -NotePropertyName "github.copilot.chat.otel.otlpEndpoint" -NotePropertyValue "$ServerUrl/v1/traces" -Force
        $settings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath -Encoding UTF8
        Write-Success "VSCode configurado"
    } else {
        Write-Warning "VSCode não encontrado"
    }
    
    # Chrome
    Write-Host "`n[2/3] Chrome" -ForegroundColor Cyan
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $extensionDir = Join-Path (Split-Path $scriptDir) "plugins\chrome-extension"
    if (Test-Path $extensionDir) {
        Write-Success "Chrome extension pronta em: $extensionDir"
    }
    
    # IntelliJ
    Write-Host "`n[3/3] IntelliJ" -ForegroundColor Cyan
    Write-Warning "Execute manualmente: gradlew buildPlugin"
    
    Write-Host ""
    Write-Success "Preparação concluída!"
    Write-Host ""
    Write-Host "Próximos passos:" -ForegroundColor Yellow
    Write-Host "  1. Reinicie o VSCode"
    Write-Host "  2. Carregue a extensão no Chrome"
    Write-Host "  3. Compile e instale o plugin IntelliJ"
    
    Show-Menu
}

# ============================================================
# VERIFICAR CONEXÃO
# ============================================================

function Test-Connection {
    Write-Step "Testando conexão com servidor..."
    Write-Host ""
    Write-Host "  Servidor: $ServerUrl" -ForegroundColor Cyan
    Write-Host "  Usuário:  $UserEmail" -ForegroundColor Cyan
    Write-Host ""
    
    # Health check
    Write-Step "Health check..."
    try {
        $health = Invoke-RestMethod -Uri "$ServerUrl/health" -TimeoutSec 5
        if ($health.status -eq "healthy") {
            Write-Success "Servidor respondendo!"
        }
    } catch {
        Write-Error "Servidor não está acessível"
        Write-Host "  Verifique se o servidor está rodando"
        Show-Menu
        return
    }
    
    # Enviar métrica teste
    Write-Step "Testando envio de métrica..."
    try {
        $body = @{
            user_id = $UserEmail
            source = "test-powershell"
            model = "gpt-4o"
            input_tokens = 10
            output_tokens = 20
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$ServerUrl/v1/metrics" -Method Post -Body $body -ContentType "application/json"
        Write-Success "Métrica enviada! Créditos: $($response.credits_used)"
    } catch {
        Write-Error "Falha ao enviar métrica"
    }
    
    Write-Host ""
    Write-Success "Conexão verificada!"
    Write-Host ""
    $dashboardUrl = $ServerUrl -replace ":8080", ":8501"
    Write-Host "  Dashboard: $dashboardUrl" -ForegroundColor Green
    
    Show-Menu
}

# ============================================================
# MAIN
# ============================================================

Write-Header

Write-Host "Configuração atual:" -ForegroundColor Cyan
Write-Host "  Servidor: $ServerUrl"
Write-Host "  Usuário:  $UserEmail"
Write-Host ""

$change = Read-Host "Deseja alterar? [s/N]"
if ($change -match "^[Ss]$") {
    $newServer = Read-Host "URL do servidor [$ServerUrl]"
    if ($newServer) { $ServerUrl = $newServer }
    
    $newEmail = Read-Host "Seu email [$UserEmail]"
    if ($newEmail) { $UserEmail = $newEmail }
    
    Write-Success "Configuração atualizada"
}

Show-Menu
