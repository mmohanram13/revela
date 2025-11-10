// Background service worker for Revela Chrome Extension

// Default API endpoints
const PRODUCTION_ENDPOINT = 'https://revela-app-759597171569.europe-west4.run.app';
const LOCALHOST_ENDPOINT = 'http://localhost:8080';

// Installation listener
chrome.runtime.onInstalled.addListener((details) => {
  console.log('Revela extension installed:', details.reason);
  
  if (details.reason === 'install') {
    // Set default settings - use production by default
    chrome.storage.sync.set({
      useLocalhost: false,
      autoAnalyze: false
    });
  }
});

// Message listener for communication between content script and backend
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Background received message:', request);
  
  if (request.action === 'analyzeTable') {
    handleTableAnalysis(request.data)
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }
  
  if (request.action === 'getSettings') {
    chrome.storage.sync.get(['useLocalhost', 'autoAnalyze'], (settings) => {
      const apiEndpoint = settings.useLocalhost ? LOCALHOST_ENDPOINT : PRODUCTION_ENDPOINT;
      sendResponse({ success: true, data: { ...settings, apiEndpoint } });
    });
    return true;
  }
});

// Handle table analysis
async function handleTableAnalysis(data) {
  try {
    // Get API endpoint from storage
    const settings = await chrome.storage.sync.get(['useLocalhost']);
    const apiEndpoint = settings.useLocalhost ? LOCALHOST_ENDPOINT : PRODUCTION_ENDPOINT;
    
    // Send to backend API
    const response = await fetch(`${apiEndpoint}/api/${data.endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data.payload)
    });
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }
    
    const result = await response.json();
    return result;
    
  } catch (error) {
    console.error('Analysis error:', error);
    throw error;
  }
}

console.log('Revela background service worker loaded');
