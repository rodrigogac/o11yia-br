#!/bin/bash
# ============================================================
# O11yIA BR - Script de Configuração do VSCode
# Configura o OpenTelemetry nativo do Copilot para enviar métricas
# ============================================================

set -e

# Configurações - EDITAR ANTES DE RODAR
SERVER_URL="${O11YIA_SERVER:-http://servidor.interno:8080}"
USER_EMAIL="${O11YIA_USER:-$(whoami)@empresa.gov.br}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║       O11yIA BR - Configuração do VSCode                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Servidor: $SERVER_URL"
echo "Usuário:  $USER_EMAIL"
echo ""

# Detectar sistema operacional e path do settings.json
case "$(uname -s)" in
    Linux*)
        VSCODE_SETTINGS="$HOME/.config/Code/User/settings.json"
        ;;
    Darwin*)
        VSCODE_SETTINGS="$HOME/Library/Application Support/Code/User/settings.json"
        ;;
    MINGW*|CYGWIN*|MSYS*)
        VSCODE_SETTINGS="$APPDATA/Code/User/settings.json"
        ;;
    *)
        echo "❌ Sistema operacional não suportado"
        exit 1
        ;;
esac

# Verificar se VSCode está instalado
if [ ! -d "$(dirname "$VSCODE_SETTINGS")" ]; then
    echo "❌ Diretório do VSCode não encontrado"
    echo "   Esperado: $(dirname "$VSCODE_SETTINGS")"
    exit 1
fi

# Backup
if [ -f "$VSCODE_SETTINGS" ]; then
    BACKUP="$VSCODE_SETTINGS.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$VSCODE_SETTINGS" "$BACKUP"
    echo "✓ Backup criado: $BACKUP"
else
    echo "{}" > "$VSCODE_SETTINGS"
    echo "✓ Arquivo settings.json criado"
fi

# Instalar jq se não existir
if ! command -v jq &> /dev/null; then
    echo "⚠️  jq não encontrado. Instalando..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y jq
    elif command -v brew &> /dev/null; then
        brew install jq
    else
        echo "❌ Não foi possível instalar jq automaticamente"
        echo "   Por favor, instale manualmente: https://stedolan.github.io/jq/"
        exit 1
    fi
fi

# Configurar OTel
echo ""
echo "Configurando OpenTelemetry..."

# Adicionar configurações
TEMP_FILE=$(mktemp)
jq --arg url "$SERVER_URL/v1/traces" \
   --arg user "$USER_EMAIL" \
   '. + {
    "github.copilot.chat.otel.enabled": true,
    "github.copilot.chat.otel.otlpEndpoint": $url,
    "github.copilot.chat.otel.serviceName": ("copilot-" + $user),
    "github.copilot.enable": true,
    "github.copilot.advanced": {
        "debug.overrideEngine": "",
        "debug.overrideProxyUrl": "",
        "debug.testOverrideProxyUrl": ""
    }
}' "$VSCODE_SETTINGS" > "$TEMP_FILE"

mv "$TEMP_FILE" "$VSCODE_SETTINGS"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                   ✓ CONFIGURAÇÃO CONCLUÍDA               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Configurações aplicadas em: $VSCODE_SETTINGS"
echo ""
echo "Próximos passos:"
echo "  1. Reinicie o VSCode"
echo "  2. Use o Copilot normalmente"
echo "  3. Verifique o dashboard em: ${SERVER_URL/8080/8501}"
echo ""
echo "Para verificar se está funcionando:"
echo "  curl $SERVER_URL/health"
echo ""
