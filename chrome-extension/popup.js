// DOM elements
const analyzeBtn = document.getElementById('analyzeBtn');
const captureBtn = document.getElementById('captureBtn');
const settingsLink = document.getElementById('settingsLink');
const statusDiv = document.getElementById('status');
const resultsDiv = document.getElementById('results');
const resultsContent = document.getElementById('resultsContent');

// Show status message
function showStatus(message, type = 'info') {
  statusDiv.textContent = message;
  statusDiv.className = `status ${type}`;
  statusDiv.classList.remove('hidden');
  
  // Hide after 3 seconds for success/error
  if (type === 'success' || type === 'error') {
    setTimeout(() => {
      statusDiv.classList.add('hidden');
    }, 3000);
  }
}

// Show results
function showResults(data) {
  resultsContent.textContent = JSON.stringify(data, null, 2);
  resultsDiv.classList.remove('hidden');
}

// Analyze current page
analyzeBtn.addEventListener('click', async () => {
  try {
    showStatus('Analyzing page...', 'info');
    
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Send message to content script
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'analyze'
    });
    
    if (response.success) {
      showStatus('Analysis complete!', 'success');
      showResults(response.data);
    } else {
      showStatus('Analysis failed: ' + response.error, 'error');
    }
  } catch (error) {
    console.error('Error:', error);
    showStatus('Error: ' + error.message, 'error');
  }
});

// Capture selection
captureBtn.addEventListener('click', async () => {
  try {
    showStatus('Capturing selection...', 'info');
    
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Send message to content script
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'capture'
    });
    
    if (response.success) {
      showStatus('Capture complete!', 'success');
      showResults(response.data);
    } else {
      showStatus('Capture failed: ' + response.error, 'error');
    }
  } catch (error) {
    console.error('Error:', error);
    showStatus('Error: ' + error.message, 'error');
  }
});

// Settings link
settingsLink.addEventListener('click', (e) => {
  e.preventDefault();
  // TODO: Open settings page
  showStatus('Settings coming soon!', 'info');
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  console.log('Revela popup loaded');
});
