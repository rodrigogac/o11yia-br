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
    const metric = extractMetricFromRequest(details, config.userId);
    if (metric) {
      metricsQueue.push(metric);
      updateBadge();
    }
  },
  { urls: ["<all_urls>"] }
);

// Extrai métrica do request
function extractMetricFromRequest(details, userId) {
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
  
  return {
    user_id: userId,
    source: 'browser',
    model: 'gpt-4o', // Copilot usa GPT-4o por padrão
    input_tokens: estimatedTokens.input,
    output_tokens: estimatedTokens.output,
    timestamp: new Date().toISOString(),
    session_id: `chrome-${Date.now()}`,
    context: context
  };
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
  const metricsToSend = [...metricsQueue];
  metricsQueue = [];
  
  try {
    const response = await fetch(`${config.serverUrl}/v1/metrics/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(metricsToSend)
    });
    
    if (!response.ok) {
      // Se falhar, recoloca na fila
      metricsQueue = [...metricsToSend, ...metricsQueue];
      console.error('Failed to send metrics:', response.statusText);
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
      metricsQueue.push(message.metric);
      updateBadge();
      sendResponse({ success: true });
      return true;
  }
});

// Obtém estatísticas do servidor
async function getStats() {
  const config = await chrome.storage.sync.get(DEFAULT_CONFIG);
  
  try {
    const response = await fetch(`${config.serverUrl}/v1/users/${encodeURIComponent(config.userId)}`);
    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.error('Error fetching stats:', error);
  }
  
  return null;
}
