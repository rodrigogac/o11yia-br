/**
 * O11yIA BR - Options Script
 */

document.addEventListener('DOMContentLoaded', async () => {
  const form = document.getElementById('configForm');
  const serverUrlInput = document.getElementById('serverUrl');
  const userIdInput = document.getElementById('userId');
  const apiKeyInput = document.getElementById('apiKey');
  const teamInput = document.getElementById('team');
  const projectInput = document.getElementById('project');
  const enabledInput = document.getElementById('enabled');
  const messageDiv = document.getElementById('message');
  const testBtn = document.getElementById('testBtn');

  // Carrega configuração atual
  const config = await new Promise(resolve => {
    chrome.runtime.sendMessage({ type: 'GET_CONFIG' }, resolve);
  });

  serverUrlInput.value = config.serverUrl || '';
  userIdInput.value = config.userId || '';
  apiKeyInput.value = config.apiKey || '';
  teamInput.value = config.team || '';
  projectInput.value = config.project || '';
  enabledInput.checked = config.enabled !== false;

  // Salvar
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const newConfig = {
      serverUrl: serverUrlInput.value.trim().replace(/\/$/, ''),
      userId: userIdInput.value.trim(),
      apiKey: apiKeyInput.value.trim(),
      team: teamInput.value.trim(),
      project: projectInput.value.trim(),
      enabled: enabledInput.checked
    };

    await new Promise(resolve => {
      chrome.runtime.sendMessage({ type: 'SET_CONFIG', config: newConfig }, resolve);
    });

    showMessage('Configurações salvas!', 'success');
  });

  // Testar conexão
  testBtn.addEventListener('click', async () => {
    testBtn.disabled = true;
    testBtn.textContent = 'Testando...';

    const serverUrl = serverUrlInput.value.trim().replace(/\/$/, '');
    const apiKey = apiKeyInput.value.trim();

    try {
      // 1) GET /health (não exige autenticação)
      const healthResp = await fetch(`${serverUrl}/health`, { method: 'GET' });

      if (!healthResp.ok) {
        showMessage(`✗ /health respondeu com erro: ${healthResp.status}`, 'error');
        return;
      }

      if (!apiKey) {
        showMessage('✓ Servidor online (/health), mas a API Key não está preenchida. Preencha para enviar métricas.', 'error');
        return;
      }

      // 2) POST métrica de teste em /v1/metrics com X-API-Key
      const testMetric = {
        user_id: userIdInput.value.trim() || 'test@o11yia.br',
        source: 'browser',
        model: 'gpt-4o',
        input_tokens: 1,
        output_tokens: 1,
        context: 'test',
        session_id: `chrome-test-${Date.now()}`,
        timestamp: new Date().toISOString()
      };
      if (teamInput.value.trim()) testMetric.team = teamInput.value.trim();
      if (projectInput.value.trim()) testMetric.project = projectInput.value.trim();

      const metricResp = await fetch(`${serverUrl}/v1/metrics`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify(testMetric)
      });

      if (metricResp.status === 401) {
        showMessage('✗ 401 Unauthorized: API Key inválida. Verifique o valor de X-API-Key.', 'error');
      } else if (metricResp.ok) {
        const result = await metricResp.json();
        showMessage(`✓ Conexão e autenticação OK! Métrica de teste enviada (créditos: ${result.credits_used}).`, 'success');
      } else {
        showMessage(`✗ POST /v1/metrics respondeu com erro: ${metricResp.status}`, 'error');
      }
    } catch (error) {
      showMessage(`✗ Não foi possível conectar: ${error.message}`, 'error');
    } finally {
      testBtn.disabled = false;
      testBtn.textContent = 'Testar Conexão';
    }
  });
  
  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    
    setTimeout(() => {
      messageDiv.textContent = '';
      messageDiv.className = '';
    }, 5000);
  }
});
