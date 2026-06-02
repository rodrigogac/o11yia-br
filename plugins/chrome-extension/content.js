/**
 * O11yIA BR - Content Script
 * Injetado nas páginas do GitHub para capturar uso do Copilot Chat
 */

(function() {
  'use strict';
  
  // Observer para detectar interações com Copilot Chat
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) {
          // Detecta mensagens do Copilot Chat
          if (node.matches?.('[data-copilot-message]') || 
              node.querySelector?.('[data-copilot-message]')) {
            handleCopilotMessage(node);
          }
          
          // Detecta sugestões de código inline
          if (node.classList?.contains('copilot-suggestion') ||
              node.querySelector?.('.copilot-suggestion')) {
            handleCopilotSuggestion(node);
          }
        }
      });
    });
  });
  
  // Inicia observação
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
  
  // Processa mensagem do Copilot Chat
  function handleCopilotMessage(node) {
    const messageText = node.textContent || '';
    const tokenCount = estimateTokens(messageText);
    
    sendMetric({
      context: 'chat',
      input_tokens: 0, // Será estimado pelo background
      output_tokens: tokenCount
    });
  }
  
  // Processa sugestão de código
  function handleCopilotSuggestion(node) {
    const codeText = node.textContent || '';
    const tokenCount = estimateTokens(codeText);
    
    sendMetric({
      context: 'inline',
      input_tokens: Math.ceil(tokenCount * 0.2),
      output_tokens: tokenCount
    });
  }
  
  // Estima tokens (~4 chars por token)
  function estimateTokens(text) {
    return Math.ceil(text.length / 4);
  }
  
  // Envia métrica para o background
  function sendMetric(partialMetric) {
    chrome.runtime.sendMessage({
      type: 'ADD_METRIC',
      metric: {
        ...partialMetric,
        source: 'browser',
        model: 'gpt-4o',
        timestamp: new Date().toISOString()
      }
    });
  }
  
  // Intercepta fetch para capturar requests do Copilot
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    const [url, options] = args;
    const urlStr = typeof url === 'string' ? url : url.url;
    
    // Verifica se é request do Copilot
    if (urlStr.includes('copilot') || urlStr.includes('completions')) {
      const response = await originalFetch.apply(this, args);
      
      // Clone para ler o body
      const clone = response.clone();
      try {
        const data = await clone.json();
        
        // Extrai tokens se disponível no response
        if (data.usage) {
          sendMetric({
            context: urlStr.includes('chat') ? 'chat' : 'completion',
            model: data.model || 'gpt-4o',
            input_tokens: data.usage.prompt_tokens || 0,
            output_tokens: data.usage.completion_tokens || 0
          });
        }
      } catch (e) {
        // Ignora se não for JSON
      }
      
      return response;
    }
    
    return originalFetch.apply(this, args);
  };
  
  console.log('[O11yIA BR] Content script loaded');
})();
