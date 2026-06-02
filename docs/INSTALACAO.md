# O11yIA BR - Guia de Instalação dos Plugins

## 🚀 Instalação Rápida (Recomendado)

### Linux/Mac
```bash
cd ~/projetosdocker/o11yia-br/deploy

# Configurar variáveis
export O11YIA_SERVER="http://servidor.setid.tcu.gov.br:8080"
export O11YIA_USER="seu.email@tcu.gov.br"

# Executar instalador interativo
chmod +x install.sh
./install.sh
```

### Windows (PowerShell)
```powershell
cd C:\projetosdocker\o11yia-br\deploy

# Executar instalador
.\Install.ps1 -ServerUrl "http://servidor.setid.tcu.gov.br:8080" -UserEmail "seu.email@tcu.gov.br"
```

---

## 📦 Instalação Manual por Componente

### 1️⃣ VSCode (OpenTelemetry Nativo)

O VSCode com Copilot suporta envio de métricas via OpenTelemetry nativamente.

**Configuração Manual:**

1. Abra o VSCode
2. Pressione `Ctrl+Shift+P` (ou `Cmd+Shift+P` no Mac)
3. Digite "Preferences: Open Settings (JSON)"
4. Adicione as linhas:

```json
{
    "github.copilot.chat.otel.enabled": true,
    "github.copilot.chat.otel.otlpEndpoint": "http://SERVIDOR:8080/v1/traces",
    "github.copilot.chat.otel.serviceName": "copilot-SEU.EMAIL@tcu.gov.br",
    "github.copilot.enable": true
}
```

5. Substitua `SERVIDOR` pelo IP/hostname do servidor O11yIA
6. Substitua `SEU.EMAIL` pelo seu email corporativo
7. Reinicie o VSCode

**Verificação:**
- Use o Copilot normalmente
- Acesse o dashboard para ver suas métricas

---

### 2️⃣ Chrome Extension

A extensão monitora o uso do Copilot no browser (github.com).

**Instalação:**

1. Abra o Chrome
2. Digite na barra de endereço: `chrome://extensions`
3. Ative o **Modo desenvolvedor** (toggle no canto superior direito)
4. Clique em **"Carregar sem compactação"**
5. Navegue até a pasta:
   ```
   ~/projetosdocker/o11yia-br/plugins/chrome-extension
   ```
6. Selecione a pasta e clique "OK"

**Configuração:**

1. Clique no ícone da extensão ⚡ na barra do Chrome
2. Clique em "⚙ Config"
3. Configure:
   - **URL do Servidor:** `http://servidor:8080`
   - **ID do Usuário:** `seu.email@tcu.gov.br`
4. Clique "Salvar"
5. Clique "Testar Conexão" para verificar

**Uso:**
- Navegue no github.com usando Copilot Chat
- A extensão captura automaticamente o uso
- Clique no ícone para ver seu consumo

---

### 3️⃣ IntelliJ IDEA Plugin

Plugin para monitorar uso do Copilot no IntelliJ.

**Pré-requisitos:**
- JDK 17+ instalado
- IntelliJ IDEA 2024.1+

**Compilação:**

```bash
cd ~/projetosdocker/o11yia-br/plugins/intellij-plugin

# Se não tiver gradlew, instale o Gradle
# sudo apt install gradle  # Linux
# brew install gradle      # Mac

# Compilar
./gradlew buildPlugin

# O arquivo .zip estará em:
# build/distributions/o11yia-copilot-metrics-1.0.0.zip
```

**Instalação no IntelliJ:**

1. Abra o IntelliJ IDEA
2. Vá em `File > Settings` (ou `IntelliJ IDEA > Preferences` no Mac)
3. Navegue até `Plugins`
4. Clique no ícone ⚙️ (engrenagem)
5. Selecione **"Install Plugin from Disk..."**
6. Navegue até o arquivo `.zip` gerado
7. Clique "OK" e reinicie o IntelliJ

**Configuração:**

1. Vá em `File > Settings > Tools > O11yIA Copilot Metrics`
2. Configure:
   - **URL do Servidor:** `http://servidor:8080`
   - **ID do Usuário:** `seu.email@tcu.gov.br`
3. Marque "Ativar coleta de métricas"
4. Clique "Testar Conexão"
5. Clique "OK"

**Uso:**
- O widget aparece na barra de status (canto inferior)
- Mostra créditos consumidos em tempo real
- Menu `Tools > Mostrar Dashboard` abre o dashboard web

---

## ✅ Verificação Pós-Instalação

### Testar Conexão

```bash
# Health check
curl http://servidor:8080/health

# Enviar métrica de teste
curl -X POST http://servidor:8080/v1/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "seu.email@tcu.gov.br",
    "source": "teste-manual",
    "model": "gpt-4o",
    "input_tokens": 100,
    "output_tokens": 200
  }'

# Verificar suas métricas
curl http://servidor:8080/v1/users/seu.email@tcu.gov.br
```

### Acessar Dashboard

Abra no navegador: `http://servidor:8501`

---

## 🔧 Troubleshooting

### VSCode não envia métricas

1. Verifique se a extensão GitHub Copilot está instalada e ativa
2. Confirme que o `settings.json` tem as configurações corretas
3. Reinicie o VSCode completamente
4. Verifique logs: `Help > Toggle Developer Tools > Console`

### Chrome Extension não conecta

1. Verifique se a URL do servidor está correta (sem barra no final)
2. Teste a conexão nas configurações da extensão
3. Verifique se não há bloqueio de CORS ou firewall
4. Abra DevTools da extensão: `chrome://extensions > Inspecionar`

### IntelliJ Plugin não aparece

1. Confirme que o IntelliJ é versão 2024.1+
2. Verifique se o plugin está habilitado em `Settings > Plugins > Installed`
3. Reinicie o IntelliJ completamente
4. Verifique logs: `Help > Show Log in Explorer/Finder`

### Servidor retorna erro

1. Verifique se o Docker está rodando: `docker ps`
2. Verifique logs: `docker logs o11yia-api`
3. Confirme que a porta 8080 está acessível

---

## 📊 Pool de Créditos - Referência

| Período | Créditos/Usuário | Time (18 pessoas) |
|---------|------------------|-------------------|
| Jun-Ago 2026 (Promo) | 7.000 | 126.000 |
| Set 2026+ (Normal) | 3.900 | 70.200 |

**Alertas automáticos:**
- 🟡 Warning: Pool > 80%
- 🔴 Critical: Pool > 90%

---

## 📞 Suporte

- **Dashboard:** http://servidor:8501
- **API Docs:** http://servidor:8080/docs
- **Email:** suporte-o11yia@tcu.gov.br
