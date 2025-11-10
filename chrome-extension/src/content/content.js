// Content script for Revela Chrome Extension
console.log('Revela content script loaded');

// Listen for messages from popup or background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Content script received message:', request);
  
  if (request.action === 'analyze') {
    analyzeCurrentPage()
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }
  
  if (request.action === 'capture') {
    captureSelection()
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }
  
  if (request.action === 'analyzeContextImage') {
    analyzeImageUrl(request.imageUrl)
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }
});

// Analyze current page for charts and tables
async function analyzeCurrentPage() {
  const elements = {
    images: [],
    canvases: [],
    tables: []
  };
  
  // Find all images
  const images = document.querySelectorAll('img');
  images.forEach(img => {
    if (img.src && img.width > 100 && img.height > 100) {
      elements.images.push({
        src: img.src,
        width: img.width,
        height: img.height,
        alt: img.alt
      });
    }
  });
  
  // Find all canvas elements (charts are often rendered on canvas)
  const canvases = document.querySelectorAll('canvas');
  canvases.forEach(canvas => {
    if (canvas.width > 100 && canvas.height > 100) {
      elements.canvases.push({
        width: canvas.width,
        height: canvas.height,
        dataUrl: canvas.toDataURL('image/png')
      });
    }
  });
  
  // Find all tables
  const tables = document.querySelectorAll('table');
  tables.forEach(table => {
    const rows = table.querySelectorAll('tr');
    if (rows.length > 0) {
      elements.tables.push({
        rows: rows.length,
        html: table.outerHTML.substring(0, 500) // Limit size
      });
    }
  });
  
  return {
    url: window.location.href,
    title: document.title,
    elements: elements,
    counts: {
      images: elements.images.length,
      canvases: elements.canvases.length,
      tables: elements.tables.length
    }
  };
}

// Capture selected element
async function captureSelection() {
  const selection = window.getSelection();
  const selectedElement = selection.anchorNode?.parentElement;
  
  if (!selectedElement) {
    throw new Error('No element selected');
  }
  
  // Check if selection contains a table
  const table = selectedElement.closest('table');
  if (table) {
    return {
      type: 'table',
      html: table.outerHTML,
      text: table.textContent
    };
  }
  
  // Check if selection contains an image
  const img = selectedElement.closest('img');
  if (img) {
    return {
      type: 'image',
      src: img.src,
      alt: img.alt
    };
  }
  
  // Check if selection contains a canvas
  const canvas = selectedElement.closest('canvas');
  if (canvas) {
    return {
      type: 'canvas',
      dataUrl: canvas.toDataURL('image/png')
    };
  }
  
  throw new Error('Selected element is not a chart or table');
}

// Analyze image from URL
async function analyzeImageUrl(imageUrl) {
  try {
    // Convert image to base64
    const response = await fetch(imageUrl);
    const blob = await response.blob();
    const base64 = await blobToBase64(blob);
    
    // Send to background script for API call
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({
        action: 'analyzeImage',
        data: {
          image: base64,
          type: 'chart'
        }
      }, (response) => {
        if (response.success) {
          resolve(response.data);
        } else {
          reject(new Error(response.error));
        }
      });
    });
  } catch (error) {
    console.error('Error analyzing image:', error);
    throw error;
  }
}

// Helper: Convert blob to base64
function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

// Add visual indicator for analyzable elements (optional)
function highlightAnalyzableElements() {
  const style = document.createElement('style');
  style.textContent = `
    .revela-highlight {
      outline: 2px dashed #667eea !important;
      outline-offset: 2px;
    }
  `;
  document.head.appendChild(style);
  
  // Highlight images, canvases, and tables on hover
  document.addEventListener('mouseover', (e) => {
    const target = e.target;
    if (target.tagName === 'IMG' || target.tagName === 'CANVAS' || target.tagName === 'TABLE') {
      target.classList.add('revela-highlight');
    }
  });
  
  document.addEventListener('mouseout', (e) => {
    const target = e.target;
    if (target.tagName === 'IMG' || target.tagName === 'CANVAS' || target.tagName === 'TABLE') {
      target.classList.remove('revela-highlight');
    }
  });
}

// Initialize
// highlightAnalyzableElements(); // Uncomment to enable hover highlighting
