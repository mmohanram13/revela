// DOM elements
const backendStatus = document.getElementById('backend-status');
const localhostToggle = document.getElementById('localhost-toggle');
const endpointUrl = document.getElementById('endpoint-url');
const retryButton = document.getElementById('retry-button');

// Default API endpoints
const PRODUCTION_ENDPOINT = 'https://revela-app-759597171569.europe-west4.run.app';
const LOCALHOST_ENDPOINT = 'http://localhost:8080';

// Get current endpoint
function getCurrentEndpoint(useLocalhost) {
  return useLocalhost ? LOCALHOST_ENDPOINT : PRODUCTION_ENDPOINT;
}

// Update endpoint display
function updateEndpointDisplay(useLocalhost) {
  endpointUrl.textContent = getCurrentEndpoint(useLocalhost);
}

// Initialize toggle state
async function initToggle() {
  const settings = await chrome.storage.sync.get(['useLocalhost']);
  const useLocalhost = settings.useLocalhost || false;
  localhostToggle.checked = useLocalhost;
  updateEndpointDisplay(useLocalhost);
}

// Check backend connectivity
async function checkBackend() {
  // Add spinning animation to retry button
  retryButton.classList.add('spinning');
  
  try {
    const settings = await chrome.storage.sync.get(['useLocalhost']);
    const useLocalhost = settings.useLocalhost || false;
    const apiEndpoint = getCurrentEndpoint(useLocalhost);
    
    // Update endpoint display
    updateEndpointDisplay(useLocalhost);
    
    // Show connecting status
    backendStatus.textContent = 'Connecting...';
    backendStatus.className = 'status-value';
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);
    
    const response = await fetch(`${apiEndpoint}/health`, {
      method: 'GET',
      signal: controller.signal,
      cache: 'no-cache',
      headers: {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    });
    
    clearTimeout(timeoutId);
    
    if (response.ok) {
      backendStatus.textContent = 'Connected';
      backendStatus.className = 'status-value connected';
    } else {
      backendStatus.textContent = 'Error';
      backendStatus.className = 'status-value disconnected';
    }
  } catch (error) {
    // Only log unexpected errors, not network failures (which are expected when server is down)
    if (error.name !== 'AbortError' && error.name !== 'TypeError') {
      console.error('Backend check failed:', error);
    }
    backendStatus.textContent = 'Disconnected';
    backendStatus.className = 'status-value disconnected';
  } finally {
    // Remove spinning animation
    retryButton.classList.remove('spinning');
  }
}

// Toggle event listener
localhostToggle.addEventListener('change', async (e) => {
  const useLocalhost = e.target.checked;
  await chrome.storage.sync.set({ useLocalhost });
  
  // Update endpoint display immediately
  updateEndpointDisplay(useLocalhost);
  
  // Recheck backend connection
  await checkBackend();
});

// Retry button event listener
retryButton.addEventListener('click', async () => {
  await checkBackend();
});

// Initialize on load
initToggle();
checkBackend();
