/**
 * O11yIA BR - Options Script
 */

document.addEventListener('DOMContentLoaded', async () => {
  const form = document.getElementById('configForm');
  const serverUrlInput = document.getElementById('serverUrl');
  const userIdInput = document.getElementById('userId');
  const enabledInput = document.getElementById('enabled');
  const messageDiv = document.getElementById('message');
  const testBtn = document.getElementById('testBtn');
  
  // Carrega configuração atual
  const config = await new Promise(resolve => {
    chrome.runtime.sendMessage({ type: 'GET_CONFIG' }, resolve);
  });
  
  serverUrlInput.value = config.serverUrl || '';
  userIdInput.value = config.userId || '';
  enabledInput.checked = config.enabled !== false;
  
  // Salvar
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const newConfig = {
      serverUrl: serverUrlInput.value.trim().replace(/\/$/, ''),
      userId: userIdInput.value.trim(),
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
    
    try {
      const response = await fetch(`${serverUrl}/health`, {
        method: 'GET',
        timeout: 5000
      });
      
      if (response.ok) {
        const data = await response.json();
        showMessage(`✓ Conexão OK! Servidor respondendo em ${serverUrl}`, 'success');
      } else {
        showMessage(`✗ Servidor respondeu com erro: ${response.status}`, 'error');
      }
    } catch (error) {
      showMessage(`✗ Não foi possível conectar: ${error.message}`, 'error');
    }
    
    testBtn.disabled = false;
    testBtn.textContent = 'Testar Conexão';
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
