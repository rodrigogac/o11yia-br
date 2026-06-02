/**
 * O11yIA BR - Popup Script
 */

document.addEventListener('DOMContentLoaded', async () => {
  const content = document.getElementById('content');
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  
  // Carrega configuração
  const config = await new Promise(resolve => {
    chrome.runtime.sendMessage({ type: 'GET_CONFIG' }, resolve);
  });
  
  // Carrega estatísticas
  const stats = await new Promise(resolve => {
    chrome.runtime.sendMessage({ type: 'GET_STATS' }, resolve);
  });
  
  // Atualiza status
  if (stats) {
    statusDot.classList.remove('offline');
    statusText.textContent = 'Conectado';
  } else {
    statusDot.classList.add('offline');
    statusText.textContent = 'Offline';
  }
  
  // Renderiza conteúdo
  if (stats) {
    renderStats(stats, config);
  } else {
    renderOffline(config);
  }
  
  function renderStats(stats, config) {
    // Calcula pool (simplificado - em produção viria do servidor)
    const isPromo = new Date().getMonth() >= 5 && new Date().getMonth() <= 7;
    const poolPerUser = isPromo ? 7000 : 3900;
    const percentUsed = Math.min((stats.total_credits / poolPerUser) * 100, 100);
    
    let progressClass = '';
    if (percentUsed > 90) progressClass = 'danger';
    else if (percentUsed > 70) progressClass = 'warning';
    
    content.innerHTML = `
      <div class="card">
        <div class="card-title">Seus Créditos</div>
        <div class="metric-value">${stats.total_credits.toFixed(1)}<span class="metric-unit">/ ${poolPerUser}</span></div>
        <div class="progress-bar">
          <div class="progress-fill ${progressClass}" style="width: ${percentUsed}%"></div>
        </div>
      </div>
      
      <div class="card">
        <div class="card-title">Resumo</div>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-value">${formatNumber(stats.total_input_tokens)}</div>
            <div class="stat-label">Input Tokens</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">${formatNumber(stats.total_output_tokens)}</div>
            <div class="stat-label">Output Tokens</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">${stats.request_count}</div>
            <div class="stat-label">Requests</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">${Object.keys(stats.by_source || {}).length}</div>
            <div class="stat-label">Fontes</div>
          </div>
        </div>
      </div>
      
      <div class="actions">
        <button class="btn-primary" id="syncBtn">⟳ Sincronizar</button>
        <button class="btn-secondary" id="configBtn">⚙ Config</button>
      </div>
      
      <div class="user-info">${config.userId}</div>
    `;
    
    // Event listeners
    document.getElementById('syncBtn').addEventListener('click', async () => {
      const btn = document.getElementById('syncBtn');
      btn.textContent = '⟳ Sincronizando...';
      btn.disabled = true;
      
      await new Promise(resolve => {
        chrome.runtime.sendMessage({ type: 'FORCE_SYNC' }, resolve);
      });
      
      btn.textContent = '✓ Sincronizado!';
      setTimeout(() => {
        btn.textContent = '⟳ Sincronizar';
        btn.disabled = false;
      }, 1500);
    });
    
    document.getElementById('configBtn').addEventListener('click', () => {
      chrome.runtime.openOptionsPage();
    });
  }
  
  function renderOffline(config) {
    content.innerHTML = `
      <div class="error">
        Não foi possível conectar ao servidor.<br>
        Verifique a configuração.
      </div>
      
      <div class="actions">
        <button class="btn-secondary" id="configBtn">⚙ Configurações</button>
      </div>
      
      <div class="user-info">${config.userId}</div>
    `;
    
    document.getElementById('configBtn').addEventListener('click', () => {
      chrome.runtime.openOptionsPage();
    });
  }
  
  function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
  }
});
