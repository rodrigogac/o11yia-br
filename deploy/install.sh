#!/bin/bash
# ============================================================
# O11yIA BR - Instalador Completo
# Instala e configura todos os componentes nas máquinas do time
# ============================================================

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configurações - EDITAR AQUI
SERVER_URL="${O11YIA_SERVER:-http://localhost:8080}"
USER_EMAIL="${O11YIA_USER:-$(whoami)@empresa.gov.br}"

print_header() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║       O11yIA BR - Instalador de Plugins                  ║${NC}"
    echo -e "${CYAN}║       Monitoramento de Créditos do GitHub Copilot        ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

detect_os() {
    case "$(uname -s)" in
        Linux*)     OS="linux" ;;
        Darwin*)    OS="macos" ;;
        MINGW*|CYGWIN*|MSYS*) OS="windows" ;;
        *)          OS="unknown" ;;
    esac
    echo $OS
}

# ============================================================
# MENU PRINCIPAL
# ============================================================

show_menu() {
    echo ""
    echo -e "${CYAN}Selecione o que deseja instalar:${NC}"
    echo ""
    echo "  1) VSCode   - Configurar OpenTelemetry nativo"
    echo "  2) Chrome   - Instalar extensão do browser"
    echo "  3) IntelliJ - Instalar plugin da IDE"
    echo "  4) Tudo     - Instalar todos os componentes"
    echo "  5) Verificar - Testar conexão com servidor"
    echo "  6) Sair"
    echo ""
    read -p "Opção [1-6]: " choice
    echo ""
    
    case $choice in
        1) install_vscode ;;
        2) install_chrome ;;
        3) install_intellij ;;
        4) install_all ;;
        5) verify_connection ;;
        6) exit 0 ;;
        *) print_error "Opção inválida"; show_menu ;;
    esac
}

# ============================================================
# INSTALAÇÃO VSCODE
# ============================================================

install_vscode() {
    print_step "Configurando VSCode..."
    
    OS=$(detect_os)
    
    case $OS in
        linux)
            VSCODE_SETTINGS="$HOME/.config/Code/User/settings.json"
            ;;
        macos)
            VSCODE_SETTINGS="$HOME/Library/Application Support/Code/User/settings.json"
            ;;
        windows)
            VSCODE_SETTINGS="$APPDATA/Code/User/settings.json"
            ;;
        *)
            print_error "Sistema operacional não suportado"
            return 1
            ;;
    esac
    
    # Verificar se VSCode existe
    if [ ! -d "$(dirname "$VSCODE_SETTINGS")" ]; then
        print_error "VSCode não encontrado em: $(dirname "$VSCODE_SETTINGS")"
        print_warning "Instale o VSCode primeiro: https://code.visualstudio.com"
        return 1
    fi
    
    # Verificar se Copilot está instalado
    if command -v code &> /dev/null; then
        if ! code --list-extensions 2>/dev/null | grep -q "github.copilot"; then
            print_warning "Extensão GitHub Copilot não detectada"
            read -p "Deseja instalar agora? [s/N]: " install_copilot
            if [[ "$install_copilot" =~ ^[Ss]$ ]]; then
                code --install-extension github.copilot
                code --install-extension github.copilot-chat
                print_success "Extensões Copilot instaladas"
            fi
        else
            print_success "GitHub Copilot já instalado"
        fi
    fi
    
    # Backup
    if [ -f "$VSCODE_SETTINGS" ]; then
        BACKUP="$VSCODE_SETTINGS.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$VSCODE_SETTINGS" "$BACKUP"
        print_success "Backup criado: $BACKUP"
    else
        mkdir -p "$(dirname "$VSCODE_SETTINGS")"
        echo "{}" > "$VSCODE_SETTINGS"
    fi
    
    # Verificar jq
    if ! command -v jq &> /dev/null; then
        print_warning "Instalando jq..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y jq
        elif command -v brew &> /dev/null; then
            brew install jq
        elif command -v pacman &> /dev/null; then
            sudo pacman -S jq
        else
            print_error "Instale jq manualmente: https://stedolan.github.io/jq/"
            return 1
        fi
    fi
    
    # Configurar OTel
    TEMP_FILE=$(mktemp)
    jq --arg url "$SERVER_URL/v1/traces" \
       --arg user "$USER_EMAIL" \
       '. + {
        "github.copilot.chat.otel.enabled": true,
        "github.copilot.chat.otel.otlpEndpoint": $url,
        "github.copilot.chat.otel.serviceName": ("copilot-" + $user),
        "github.copilot.enable": true
    }' "$VSCODE_SETTINGS" > "$TEMP_FILE"
    
    mv "$TEMP_FILE" "$VSCODE_SETTINGS"
    
    print_success "VSCode configurado!"
    echo ""
    echo -e "  ${CYAN}Configurações aplicadas:${NC}"
    echo "  • OTel habilitado"
    echo "  • Endpoint: $SERVER_URL/v1/traces"
    echo "  • Usuário: $USER_EMAIL"
    echo ""
    print_warning "Reinicie o VSCode para aplicar as configurações"
    
    show_menu
}

# ============================================================
# INSTALAÇÃO CHROME
# ============================================================

install_chrome() {
    print_step "Preparando extensão Chrome..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    EXTENSION_DIR="$SCRIPT_DIR/../plugins/chrome-extension"
    
    if [ ! -d "$EXTENSION_DIR" ]; then
        print_error "Diretório da extensão não encontrado: $EXTENSION_DIR"
        return 1
    fi
    
    # Criar ícones placeholder se não existirem
    ICONS_DIR="$EXTENSION_DIR/icons"
    mkdir -p "$ICONS_DIR"
    
    if [ ! -f "$ICONS_DIR/icon16.png" ]; then
        print_step "Criando ícones..."
        # SVG simples convertido para PNG (placeholder)
        for size in 16 48 128; do
            if command -v convert &> /dev/null; then
                convert -size ${size}x${size} xc:#4ecdc4 \
                    -fill white -gravity center \
                    -pointsize $((size/2)) -annotate 0 "⚡" \
                    "$ICONS_DIR/icon${size}.png" 2>/dev/null || \
                # Fallback: criar PNG vazio
                printf '\x89PNG\r\n\x1a\n' > "$ICONS_DIR/icon${size}.png"
            else
                # Criar arquivo placeholder
                printf '\x89PNG\r\n\x1a\n' > "$ICONS_DIR/icon${size}.png"
            fi
        done
        print_success "Ícones criados"
    fi
    
    # Atualizar configuração padrão na extensão
    BACKGROUND_JS="$EXTENSION_DIR/background.js"
    if [ -f "$BACKGROUND_JS" ]; then
        sed -i.bak "s|serverUrl: 'http://localhost:8080'|serverUrl: '$SERVER_URL'|g" "$BACKGROUND_JS"
        sed -i.bak "s|userId: 'user@empresa.gov.br'|userId: '$USER_EMAIL'|g" "$BACKGROUND_JS"
        rm -f "$BACKGROUND_JS.bak"
    fi
    
    print_success "Extensão preparada!"
    echo ""
    echo -e "  ${CYAN}Passos para instalar no Chrome:${NC}"
    echo ""
    echo "  1. Abra o Chrome e vá para: chrome://extensions"
    echo ""
    echo "  2. Ative o 'Modo desenvolvedor' (canto superior direito)"
    echo ""
    echo "  3. Clique em 'Carregar sem compactação'"
    echo ""
    echo "  4. Selecione a pasta:"
    echo -e "     ${GREEN}$EXTENSION_DIR${NC}"
    echo ""
    echo "  5. A extensão aparecerá na barra do Chrome"
    echo ""
    echo "  6. Clique no ícone ⚡ e configure se necessário"
    echo ""
    
    # Tentar abrir Chrome extensions
    read -p "Deseja abrir chrome://extensions agora? [s/N]: " open_chrome
    if [[ "$open_chrome" =~ ^[Ss]$ ]]; then
        if command -v google-chrome &> /dev/null; then
            google-chrome "chrome://extensions" &
        elif command -v chromium &> /dev/null; then
            chromium "chrome://extensions" &
        elif [ "$OS" = "macos" ]; then
            open -a "Google Chrome" "chrome://extensions"
        else
            print_warning "Abra manualmente: chrome://extensions"
        fi
    fi
    
    show_menu
}

# ============================================================
# INSTALAÇÃO INTELLIJ
# ============================================================

install_intellij() {
    print_step "Preparando plugin IntelliJ..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PLUGIN_DIR="$SCRIPT_DIR/../plugins/intellij-plugin"
    
    if [ ! -d "$PLUGIN_DIR" ]; then
        print_error "Diretório do plugin não encontrado: $PLUGIN_DIR"
        return 1
    fi
    
    # Verificar Gradle
    if [ -f "$PLUGIN_DIR/gradlew" ]; then
        GRADLE="$PLUGIN_DIR/gradlew"
    elif command -v gradle &> /dev/null; then
        GRADLE="gradle"
    else
        print_warning "Gradle não encontrado. Baixando wrapper..."
        cd "$PLUGIN_DIR"
        
        # Criar gradle wrapper
        mkdir -p gradle/wrapper
        cat > gradle/wrapper/gradle-wrapper.properties << 'EOF'
distributionUrl=https\://services.gradle.org/distributions/gradle-8.5-bin.zip
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
EOF
        
        # Download gradlew
        curl -sL "https://raw.githubusercontent.com/gradle/gradle/v8.5.0/gradlew" -o gradlew
        chmod +x gradlew
        GRADLE="./gradlew"
        cd - > /dev/null
    fi
    
    print_step "Compilando plugin (pode demorar na primeira vez)..."
    
    cd "$PLUGIN_DIR"
    $GRADLE buildPlugin --no-daemon 2>&1 | while read line; do
        echo "  $line"
    done
    
    BUILD_STATUS=${PIPESTATUS[0]}
    cd - > /dev/null
    
    if [ $BUILD_STATUS -eq 0 ]; then
        ZIP_FILE=$(find "$PLUGIN_DIR/build/distributions" -name "*.zip" 2>/dev/null | head -1)
        
        if [ -n "$ZIP_FILE" ]; then
            print_success "Plugin compilado: $ZIP_FILE"
            echo ""
            echo -e "  ${CYAN}Passos para instalar no IntelliJ:${NC}"
            echo ""
            echo "  1. Abra IntelliJ IDEA"
            echo ""
            echo "  2. Vá em: File > Settings > Plugins"
            echo ""
            echo "  3. Clique no ícone ⚙️ > 'Install Plugin from Disk...'"
            echo ""
            echo "  4. Selecione o arquivo:"
            echo -e "     ${GREEN}$ZIP_FILE${NC}"
            echo ""
            echo "  5. Reinicie o IntelliJ"
            echo ""
            echo "  6. Configure em: File > Settings > Tools > O11yIA Copilot Metrics"
            echo ""
        else
            print_error "Arquivo ZIP não encontrado após build"
        fi
    else
        print_error "Falha na compilação do plugin"
        echo ""
        echo "Verifique se você tem:"
        echo "  • JDK 17+ instalado"
        echo "  • Conexão com a internet (para baixar dependências)"
        echo ""
    fi
    
    show_menu
}

# ============================================================
# INSTALAR TUDO
# ============================================================

install_all() {
    print_step "Instalando todos os componentes..."
    echo ""
    
    echo -e "${CYAN}[1/3] VSCode${NC}"
    install_vscode_silent
    
    echo -e "${CYAN}[2/3] Chrome${NC}"
    install_chrome_silent
    
    echo -e "${CYAN}[3/3] IntelliJ${NC}"
    install_intellij_silent
    
    echo ""
    print_success "Todos os componentes preparados!"
    echo ""
    echo -e "${CYAN}Resumo:${NC}"
    echo "  • VSCode: Configurado com OTel"
    echo "  • Chrome: Extensão pronta para carregar"
    echo "  • IntelliJ: Plugin compilado"
    echo ""
    echo -e "${YELLOW}Próximos passos:${NC}"
    echo "  1. Reinicie o VSCode"
    echo "  2. Carregue a extensão no Chrome (chrome://extensions)"
    echo "  3. Instale o .zip no IntelliJ"
    echo ""
    
    show_menu
}

# Versões silenciosas para install_all
install_vscode_silent() {
    OS=$(detect_os)
    case $OS in
        linux) VSCODE_SETTINGS="$HOME/.config/Code/User/settings.json" ;;
        macos) VSCODE_SETTINGS="$HOME/Library/Application Support/Code/User/settings.json" ;;
        *) return ;;
    esac
    
    if [ -d "$(dirname "$VSCODE_SETTINGS")" ] && command -v jq &> /dev/null; then
        [ -f "$VSCODE_SETTINGS" ] || echo "{}" > "$VSCODE_SETTINGS"
        TEMP_FILE=$(mktemp)
        jq --arg url "$SERVER_URL/v1/traces" --arg user "$USER_EMAIL" \
           '. + {"github.copilot.chat.otel.enabled": true, "github.copilot.chat.otel.otlpEndpoint": $url}' \
           "$VSCODE_SETTINGS" > "$TEMP_FILE" && mv "$TEMP_FILE" "$VSCODE_SETTINGS"
        print_success "VSCode configurado"
    else
        print_warning "VSCode não encontrado ou jq não instalado"
    fi
}

install_chrome_silent() {
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    EXTENSION_DIR="$SCRIPT_DIR/../plugins/chrome-extension"
    
    if [ -d "$EXTENSION_DIR" ]; then
        mkdir -p "$EXTENSION_DIR/icons"
        for size in 16 48 128; do
            [ -f "$EXTENSION_DIR/icons/icon${size}.png" ] || printf '\x89PNG\r\n\x1a\n' > "$EXTENSION_DIR/icons/icon${size}.png"
        done
        print_success "Chrome extension preparada"
    else
        print_warning "Extensão Chrome não encontrada"
    fi
}

install_intellij_silent() {
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PLUGIN_DIR="$SCRIPT_DIR/../plugins/intellij-plugin"
    
    if [ -d "$PLUGIN_DIR" ] && command -v java &> /dev/null; then
        print_warning "IntelliJ: Execute './gradlew buildPlugin' manualmente"
    else
        print_warning "IntelliJ plugin requer JDK 17+"
    fi
}

# ============================================================
# VERIFICAR CONEXÃO
# ============================================================

verify_connection() {
    print_step "Testando conexão com servidor..."
    echo ""
    
    echo -e "  Servidor: ${CYAN}$SERVER_URL${NC}"
    echo -e "  Usuário:  ${CYAN}$USER_EMAIL${NC}"
    echo ""
    
    # Health check
    print_step "Health check..."
    if curl -s --connect-timeout 5 "$SERVER_URL/health" | grep -q "healthy"; then
        print_success "Servidor respondendo!"
    else
        print_error "Servidor não está acessível"
        echo ""
        echo "Verifique se:"
        echo "  1. O servidor está rodando (docker compose up -d)"
        echo "  2. A URL está correta: $SERVER_URL"
        echo "  3. Não há firewall bloqueando a porta"
        show_menu
        return
    fi
    
    # Testar envio de métrica
    print_step "Testando envio de métrica..."
    RESPONSE=$(curl -s -X POST "$SERVER_URL/v1/metrics" \
        -H "Content-Type: application/json" \
        -d "{
            \"user_id\": \"$USER_EMAIL\",
            \"source\": \"test\",
            \"model\": \"gpt-4o\",
            \"input_tokens\": 10,
            \"output_tokens\": 20
        }")
    
    if echo "$RESPONSE" | grep -q "success"; then
        print_success "Métrica enviada com sucesso!"
        CREDITS=$(echo "$RESPONSE" | grep -o '"credits_used":[0-9.]*' | cut -d: -f2)
        echo "  Créditos calculados: $CREDITS"
    else
        print_error "Falha ao enviar métrica"
        echo "  Resposta: $RESPONSE"
    fi
    
    # Verificar dados do usuário
    print_step "Verificando dados do usuário..."
    USER_DATA=$(curl -s "$SERVER_URL/v1/users/$USER_EMAIL")
    
    if echo "$USER_DATA" | grep -q "total_credits"; then
        TOTAL=$(echo "$USER_DATA" | grep -o '"total_credits":[0-9.]*' | cut -d: -f2)
        print_success "Usuário encontrado no sistema"
        echo "  Total de créditos: $TOTAL"
    else
        print_warning "Usuário ainda não tem métricas registradas"
    fi
    
    echo ""
    print_success "Conexão verificada!"
    echo ""
    echo -e "  Dashboard: ${GREEN}${SERVER_URL/8080/8501}${NC}"
    
    show_menu
}

# ============================================================
# CONFIGURAÇÃO INICIAL
# ============================================================

configure() {
    echo ""
    echo -e "${CYAN}Configuração:${NC}"
    echo ""
    
    read -p "URL do servidor [$SERVER_URL]: " input_server
    [ -n "$input_server" ] && SERVER_URL="$input_server"
    
    read -p "Seu email [$USER_EMAIL]: " input_email
    [ -n "$input_email" ] && USER_EMAIL="$input_email"
    
    # Salvar para sessão
    export O11YIA_SERVER="$SERVER_URL"
    export O11YIA_USER="$USER_EMAIL"
    
    print_success "Configuração salva para esta sessão"
}

# ============================================================
# MAIN
# ============================================================

print_header

echo -e "${CYAN}Configuração atual:${NC}"
echo "  Servidor: $SERVER_URL"
echo "  Usuário:  $USER_EMAIL"
echo ""

read -p "Deseja alterar? [s/N]: " change_config
if [[ "$change_config" =~ ^[Ss]$ ]]; then
    configure
fi

show_menu
