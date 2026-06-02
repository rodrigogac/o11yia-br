/**
 * O11yIA BR - Copilot Metrics Chrome Extension
 * Background Service Worker
 * 
 * Intercepta requests do Copilot e envia métricas para o servidor central
 */

// Configurações padrão
const DEFAULT_CONFIG = {
  serverUrl: 'http://localhost:8080',
  userId: 'user@empresa.gov.br',
  apiKey: '',
  team: '',
  project: '',
  enabled: true
};

// Cache de métricas para envio em batch
let metricsQueue = [];
const BATCH_INTERVAL = 30000; // 30 segundos

// URLs do Copilot para monitorar
const COPILOT_PATTERNS = [
  'copilot-proxy.githubusercontent.com',
  'api.github.com/copilot',
  'api.github.com/user/copilot',
  'githubcopilot.com'
];

// Inicialização
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.get(DEFAULT_CONFIG, (config) => {
    if (!config.serverUrl) {
      chrome.storage.sync.set(DEFAULT_CONFIG);
    }
  });
  
  // Alarme para envio em batch
  chrome.alarms.create('sendMetrics', { periodInMinutes: 0.5 });
});

// Listener do alarme
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'sendMetrics') {
    flushMetricsQueue();
  }
});

// Intercepta requests
chrome.webRequest.onCompleted.addListener(
  async (details) => {
    // Verifica se é request do Copilot
    const isCopilotRequest = COPILOT_PATTERNS.some(pattern => 
      details.url.includes(pattern)
    );
    
    if (!isCopilotRequest) return;
    
    const config = await chrome.storage.sync.get(DEFAULT_CONFIG);
    if (!config.enabled) return;
    
    // Extrair informações do request
    const metric = extractMetricFromRequest(details, config);
    if (metric) {
      metricsQueue.push(metric);
      updateBadge();
    }
  },
  { urls: ["<all_urls>"] }
);

// Extrai métrica do request
function extractMetricFromRequest(details, config) {
  const url = new URL(details.url);

  // Identificar tipo de request
  let context = 'completion';
  if (url.pathname.includes('chat')) {
    context = 'chat';
  } else if (url.pathname.includes('inline')) {
    context = 'inline';
  }

  // Estimar tokens baseado no tamanho da response
  // Em produção, seria melhor parsear o response body
  const estimatedTokens = estimateTokensFromResponse(details);

  const metric = {
    user_id: config.userId,
    source: 'browser',
    model: 'gpt-4o', // Copilot usa GPT-4o por padrão
    input_tokens: estimatedTokens.input,
    output_tokens: estimatedTokens.output,
    timestamp: new Date().toISOString(),
    session_id: `chrome-${Date.now()}`,
    context: context
  };

  // Campos opcionais do config
  if (config.team) metric.team = config.team;
  if (config.project) metric.project = config.project;

  return metric;
}

// Estima tokens (heurística)
function estimateTokensFromResponse(details) {
  // Baseado em headers de content-length quando disponível
  const contentLength = details.responseHeaders?.find(
    h => h.name.toLowerCase() === 'content-length'
  )?.value || 500;
  
  // Aproximação: ~4 chars por token
  const outputTokens = Math.ceil(parseInt(contentLength) / 4);
  const inputTokens = Math.ceil(outputTokens * 0.3); // Estimativa: input ~30% do output
  
  return { input: inputTokens, output: outputTokens };
}

// Envia métricas para o servidor
async function flushMetricsQueue() {
  if (metricsQueue.length === 0) return;
  
  const config = await chrome.storage.sync.get(DEFAULT_CONFIG);

  // Sem API key não há como autenticar: mantém a fila para retry
  if (!config.apiKey) {
    console.error('[O11yIA BR] API Key não configurada. Métricas mantidas na fila. Configure em Opções.');
    return;
  }

  const metricsToSend = [...metricsQueue];
  metricsQueue = [];

  try {
    const response = await fetch(`${config.serverUrl}/v1/metrics/batch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': config.apiKey
      },
      body: JSON.stringify(metricsToSend)
    });

    if (response.status === 401) {
      // Autenticação falhou: mantém a fila para retry após corrigir a chave
      metricsQueue = [...metricsToSend, ...metricsQueue];
      console.error('[O11yIA BR] 401 Unauthorized: X-API-Key inválida ou ausente. Verifique a API Key nas Opções. Fila mantida para retry.');
    } else if (!response.ok) {
      // Se falhar, recoloca na fila
      metricsQueue = [...metricsToSend, ...metricsQueue];
      console.error('Failed to send metrics:', response.status, response.statusText);
    } else {
      const result = await response.json();
      console.log(`Sent ${result.count} metrics, ${result.total_credits} credits`);
    }
  } catch (error) {
    // Recoloca na fila em caso de erro
    metricsQueue = [...metricsToSend, ...metricsQueue];
    console.error('Error sending metrics:', error);
  }

  updateBadge();
}

// Atualiza badge com métricas pendentes
function updateBadge() {
  const count = metricsQueue.length;
  chrome.action.setBadgeText({ text: count > 0 ? count.toString() : '' });
  chrome.action.setBadgeBackgroundColor({ color: count > 5 ? '#ff6b6b' : '#4ecdc4' });
}

// API para popup e content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'GET_STATS':
      getStats().then(sendResponse);
      return true;
      
    case 'GET_CONFIG':
      chrome.storage.sync.get(DEFAULT_CONFIG, sendResponse);
      return true;
      
    case 'SET_CONFIG':
      chrome.storage.sync.set(message.config, () => sendResponse({ success: true }));
      return true;
      
    case 'FORCE_SYNC':
      flushMetricsQueue().then(() => sendResponse({ success: true }));
      return true;
      
    case 'ADD_METRIC':
      // Enriquece a métrica do content script com dados do config (user_id, team, project)
      chrome.storage.sync.get(DEFAULT_CONFIG, (config) => {
        if (!config.enabled) {
          sendResponse({ success: false, reason: 'disabled' });
          return;
        }
        const metric = {
          ...message.metric,
          user_id: message.metric.user_id || config.userId,
          source: 'browser'
        };
        if (config.team && !metric.team) metric.team = config.team;
        if (config.project && !metric.project) metric.project = config.project;
        metricsQueue.push(metric);
        updateBadge();
        sendResponse({ success: true });
      });
      return true;
  }
});

// Obtém estatísticas do servidor
async function getStats() {
  const config = await chrome.storage.sync.get(DEFAULT_CONFIG);

  if (!config.apiKey) {
    console.error('[O11yIA BR] API Key não configurada. Não é possível consultar estatísticas.');
    return null;
  }

  try {
    const response = await fetch(`${config.serverUrl}/v1/users/${encodeURIComponent(config.userId)}`, {
      headers: { 'X-API-Key': config.apiKey }
    });
    if (response.status === 401) {
      console.error('[O11yIA BR] 401 Unauthorized ao consultar estatísticas: verifique a API Key nas Opções.');
      return null;
    }
    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.error('Error fetching stats:', error);
  }

  return null;
}
