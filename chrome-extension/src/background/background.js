// Background service worker for Revela Chrome Extension

// Installation listener
chrome.runtime.onInstalled.addListener((details) => {
  console.log('Revela extension installed:', details.reason);
  
  if (details.reason === 'install') {
    // Set default settings
    chrome.storage.sync.set({
      apiEndpoint: 'http://localhost:8000',
      autoAnalyze: false
    });
  }
});

// Message listener
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Background received message:', request);
  
  if (request.action === 'analyzeImage') {
    handleImageAnalysis(request.data)
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }
  
  if (request.action === 'getSettings') {
    chrome.storage.sync.get(['apiEndpoint', 'autoAnalyze'], (settings) => {
      sendResponse({ success: true, data: settings });
    });
    return true;
  }
});

// Handle image analysis
async function handleImageAnalysis(imageData) {
  try {
    // Get API endpoint from storage
    const settings = await chrome.storage.sync.get(['apiEndpoint']);
    const apiEndpoint = settings.apiEndpoint || 'http://localhost:8000';
    
    // Send to backend API
    const response = await fetch(`${apiEndpoint}/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        image: imageData.image,
        type: imageData.type
      })
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

// Context menu (optional - for right-click functionality)
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'analyzeWithRevela',
    title: 'Analyze with Revela',
    contexts: ['image']
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'analyzeWithRevela') {
    // Send message to content script to handle the image
    chrome.tabs.sendMessage(tab.id, {
      action: 'analyzeContextImage',
      imageUrl: info.srcUrl
    });
  }
});

console.log('Revela background service worker loaded');
