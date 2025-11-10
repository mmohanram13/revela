// Content script for Revela Chrome Extension
// Note: CSS is loaded via manifest.json content_scripts

console.log('Revela content script loaded');

// Global error handler for extension context invalidation
window.addEventListener('error', (event) => {
  if (event.message?.includes('Extension context invalidated')) {
    event.preventDefault();
    console.log('Extension was reloaded, suppressing error');
    return true;
  }
});

// Session management
let activeSessions = new Map();
let hoveredElement = null;

// Default API endpoints
const PRODUCTION_ENDPOINT = 'https://revela-app-759597171569.europe-west4.run.app';
const LOCALHOST_ENDPOINT = 'http://localhost:8080';

// Configuration
const HOVER_DELAY = 300; // ms before showing hover icon

// Get API endpoint based on settings
async function getApiEndpoint() {
  try {
    // Check if extension context is valid
    if (!chrome.runtime?.id) {
      console.warn('Extension context invalidated, using default endpoint');
      return PRODUCTION_ENDPOINT;
    }
    
    const settings = await chrome.storage.sync.get(['useLocalhost']);
    return settings.useLocalhost ? LOCALHOST_ENDPOINT : PRODUCTION_ENDPOINT;
  } catch (error) {
    console.error('Error getting API endpoint:', error);
    return PRODUCTION_ENDPOINT; // Default to production
  }
}

// Generate unique session ID
function generateSessionId() {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Listen for messages from popup or background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Content script received message:', request);
  
  if (request.action === 'toggleDetection') {
    toggleElementDetection(request.enabled);
    sendResponse({ success: true });
  }
  
  return true;
});

// Detect if element is analyzable (table or chart image)
function isAnalyzableElement(element) {
  // Check for tables - accept ALL tables
  if (element.tagName === 'TABLE') {
    console.log('Revela: Found table', element);
    return true;
  }
  
  // Check for images - accept ALL images
  if (element.tagName === 'IMG') {
    console.log('Revela: Found image', element.src);
    return true;
  }
  
  // Check for canvas elements - accept ALL canvas
  if (element.tagName === 'CANVAS') {
    console.log('Revela: Found canvas', element);
    return true;
  }
  
  return false;
}

// Extract data from element
function extractElementData(element) {
  if (element.tagName === 'TABLE') {
    return {
      type: 'table',
      html: element.outerHTML,
      rowCount: element.querySelectorAll('tr').length,
      colCount: element.querySelectorAll('tr')[0]?.children.length || 0
    };
  }
  
  if (element.tagName === 'IMG') {
    return {
      type: 'image',
      src: element.src,
      alt: element.alt,
      width: element.width,
      height: element.height
    };
  }
  
  if (element.tagName === 'CANVAS') {
    return {
      type: 'canvas',
      dataUrl: element.toDataURL('image/png'),
      width: element.width,
      height: element.height
    };
  }
  
  return null;
}

// Create hover icon for element
function createHoverIcon(element) {
  // Remove existing hover icon if present
  removeHoverIcon();
  
  const icon = document.createElement('div');
  icon.className = 'revela-hover-icon';
  icon.innerHTML = `
    <img src="${chrome.runtime.getURL('images/logo.png')}" alt="Revela" />
  `;
  
  // Position the icon relative to the element
  const updateIconPosition = () => {
    const rect = element.getBoundingClientRect();
    icon.style.position = 'fixed';
    icon.style.top = `${rect.top + 8}px`;
    icon.style.right = `${window.innerWidth - rect.right + 8}px`;
    icon.style.zIndex = '2147483647';
  };
  
  updateIconPosition();
  
  // Update position on scroll
  const scrollListener = () => {
    if (document.body.contains(icon)) {
      updateIconPosition();
    } else {
      window.removeEventListener('scroll', scrollListener, true);
    }
  };
  window.addEventListener('scroll', scrollListener, true);
  
  // Create action menu
  const menu = document.createElement('div');
  menu.className = 'revela-action-menu';
  menu.innerHTML = `
    <button class="revela-action-btn" data-action="quick">Quick Insights</button>
    <button class="revela-action-btn" data-action="deep">Deep Analyse</button>
  `;
  
  icon.appendChild(menu);
  
  // Add click handlers
  menu.querySelectorAll('.revela-action-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      e.preventDefault();
      const action = btn.dataset.action;
      
      // Hide menu and icon immediately
      removeHoverIcon();
      
      if (action === 'quick') {
        await handleQuickInsights(element);
      } else if (action === 'deep') {
        await handleDeepAnalyse(element);
      }
    });
  });
  
  // Show menu on hover over icon
  icon.addEventListener('mouseenter', () => {
    menu.style.display = 'flex';
  });
  
  // Keep menu visible when hovering over menu itself
  menu.addEventListener('mouseenter', () => {
    menu.style.display = 'flex';
  });
  
  // Hide menu when mouse leaves both icon and menu
  const hideMenu = () => {
    setTimeout(() => {
      if (!icon.matches(':hover') && !menu.matches(':hover')) {
        menu.style.display = 'none';
      }
    }, 100);
  };
  
  icon.addEventListener('mouseleave', hideMenu);
  menu.addEventListener('mouseleave', hideMenu);
  
  document.body.appendChild(icon);
  return icon;
}

function removeHoverIcon() {
  const existing = document.querySelector('.revela-hover-icon');
  if (existing) {
    existing.remove();
  }
  currentIconElement = null;
}

// Handle Quick Insights
async function handleQuickInsights(element) {
  const sessionId = generateSessionId();
  const elementData = extractElementData(element);
  const apiEndpoint = await getApiEndpoint();
  
  console.log('Revela: Quick Insights requested');
  console.log('Element data:', elementData);
  console.log('API endpoint:', apiEndpoint);
  
  // Open sidebar immediately with loading state
  openQuickInsightsSidebar(sessionId, elementData, null, element, true);
  
  try {
    const payload = {
      sessionId,
      data: elementData,
      url: window.location.href
    };
    
    console.log('Revela: Sending request:', payload);
    
    const response = await fetch(`${apiEndpoint}/api/quick-insights`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    });
    
    console.log('Revela: Response status:', response.status);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Revela: API error response:', errorText);
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }
    
    const result = await response.json();
    console.log('Revela: Got insights:', result);
    
    // Update sidebar with insights
    updateQuickInsightsSidebar(sessionId, result.insights);
    
  } catch (error) {
    console.error('Quick insights error:', error);
    updateQuickInsightsSidebar(sessionId, null, `Failed to generate insights: ${error.message}`);
  }
}

// Handle Deep Analyse
async function handleDeepAnalyse(element) {
  const sessionId = generateSessionId();
  const elementData = extractElementData(element);
  const apiEndpoint = await getApiEndpoint();
  
  console.log('Revela: Deep Analyse requested');
  console.log('Element data:', elementData);
  
  // Store session
  activeSessions.set(sessionId, {
    element,
    data: elementData,
    startTime: Date.now()
  });
  
  try {
    // Initialize session with backend
    const response = await fetch(`${apiEndpoint}/api/session/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sessionId,
        data: elementData,
        url: window.location.href
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Revela: Session start error:', errorText);
      throw new Error(`Session initialization failed: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('Revela: Session started:', result);
    
    // Open in-page sidebar with context about what was attached
    openSidebar(sessionId, elementData, result.summary, element);
    
  } catch (error) {
    console.error('Deep analyse error:', error);
    showError(`Failed to start analysis session: ${error.message}`);
    activeSessions.delete(sessionId);
  }
}

// Show insights tooltip
function showInsightsTooltip(element, insights) {
  removeInsightsTooltip();
  
  const tooltip = document.createElement('div');
  tooltip.className = 'revela-insights-tooltip';
  tooltip.innerHTML = `
    <div class="revela-insights-header">
      <img src="${chrome.runtime.getURL('images/logo.png')}" alt="Revela" class="revela-tooltip-logo" />
      <span>Quick Insights</span>
      <button class="revela-close-btn">&times;</button>
    </div>
    <div class="revela-insights-content">
      ${insights}
    </div>
  `;
  
  // Position near element
  const rect = element.getBoundingClientRect();
  tooltip.style.position = 'fixed';
  tooltip.style.top = `${rect.bottom + 10}px`;
  tooltip.style.left = `${rect.left}px`;
  tooltip.style.zIndex = '2147483647';
  
  // Close button handler
  tooltip.querySelector('.revela-close-btn').addEventListener('click', removeInsightsTooltip);
  
  document.body.appendChild(tooltip);
  
  // Auto-remove after 10 seconds
  setTimeout(removeInsightsTooltip, 10000);
}

function removeInsightsTooltip() {
  const tooltip = document.querySelector('.revela-insights-tooltip');
  if (tooltip) {
    tooltip.remove();
  }
}

// Open sidebar for deep analysis
function openSidebar(sessionId, elementData, summary, element) {
  // Remove existing sidebar if any
  closeSidebar();
  
  // Create context message based on element type
  let contextMessage = '';
  let elementType = '';
  let imagePreview = '';
  
  if (elementData.type === 'table') {
    const rows = summary?.row_count || 'unknown';
    const cols = summary?.column_count || 'unknown';
    elementType = 'Table';
    contextMessage = `<strong>Table added to context</strong><br><br>• Rows: ${rows}<br>• Columns: ${cols}`;
  } else if (elementData.type === 'image') {
    elementType = 'Image';
    contextMessage = `<strong>Image automatically attached to context</strong><br><br>• Dimensions: ${elementData.width}×${elementData.height}px`;
    imagePreview = `<img src="${elementData.src}" class="revela-image-preview" alt="Preview" />`;
  } else if (elementData.type === 'canvas') {
    elementType = 'Chart';
    contextMessage = `<strong>Chart/Canvas attached to context</strong><br><br>• Dimensions: ${elementData.width}×${elementData.height}px`;
    // For canvas, render the canvas data as image
    if (elementData.dataUrl) {
      imagePreview = `<img src="${elementData.dataUrl}" class="revela-image-preview" alt="Chart Preview" />`;
    }
  }
  
  const sidebar = document.createElement('div');
  sidebar.className = 'revela-sidebar';
  sidebar.id = `revela-sidebar-${sessionId}`;
  sidebar.innerHTML = `
    <div class="revela-sidebar-header">
      <img src="${chrome.runtime.getURL('images/logo.png')}" alt="Revela" class="revela-sidebar-logo" />
      <h3>revela - Deep Analyse</h3>
      <button class="revela-close-btn" id="revela-sidebar-close">&times;</button>
    </div>
    <div class="revela-chat-container" id="revela-chat-${sessionId}">
      <div class="revela-chat-messages" id="revela-messages-${sessionId}">
        <div class="revela-context-card">
          ${imagePreview}
          <div class="revela-context-content">
            ${contextMessage}
          </div>
          <button class="revela-navigate-btn" id="revela-navigate-${sessionId}">
            Navigate to ${elementType}
          </button>
        </div>
        <div class="revela-message revela-assistant-message">
          I'm ready to analyze this data. What would you like to know?
        </div>
      </div>
      <div class="revela-chat-input-container">
        <textarea 
          id="revela-input-${sessionId}" 
          class="revela-chat-input" 
          placeholder="Ask a question about this data..."
          rows="2"
        ></textarea>
        <button id="revela-send-${sessionId}" class="revela-send-btn">
          Send
        </button>
      </div>
    </div>
  `;
  
  document.body.appendChild(sidebar);
  
  // Add class to body to push content
  document.body.classList.add('revela-sidebar-open');
  
  // Event listeners
  document.getElementById('revela-sidebar-close').addEventListener('click', () => {
    endSession(sessionId);
    closeSidebar();
  });
  
  // Navigate to element button
  document.getElementById(`revela-navigate-${sessionId}`).addEventListener('click', () => {
    if (element && document.body.contains(element)) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Add temporary highlight
      element.style.outline = '3px solid #667eea';
      element.style.outlineOffset = '4px';
      setTimeout(() => {
        element.style.outline = '';
        element.style.outlineOffset = '';
      }, 2000);
    }
  });
  
  // Image preview click handler for full-screen view
  const imagePreviewEl = sidebar.querySelector('.revela-image-preview');
  if (imagePreviewEl) {
    imagePreviewEl.style.cursor = 'pointer';
    imagePreviewEl.addEventListener('click', () => {
      const imgSrc = imagePreviewEl.src;
      openFullScreenImage(imgSrc);
    });
  }
  
  const input = document.getElementById(`revela-input-${sessionId}`);
  const sendBtn = document.getElementById(`revela-send-${sessionId}`);
  
  sendBtn.addEventListener('click', () => sendMessage(sessionId));
  
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(sessionId);
    }
  });
  
  // Focus input
  input.focus();
}

// Open sidebar for quick insights (no chat functionality)
function openQuickInsightsSidebar(sessionId, elementData, insights, element, isLoading = false) {
  // Remove existing sidebar if any
  closeSidebar();
  
  // Create context message based on element type
  let contextMessage = '';
  let elementType = '';
  let imagePreview = '';
  
  if (elementData.type === 'table') {
    elementType = 'Table';
    contextMessage = `<strong>Table Insights</strong><br><br>• Rows: ${elementData.rowCount}<br>• Columns: ${elementData.colCount}`;
  } else if (elementData.type === 'image') {
    elementType = 'Image';
    contextMessage = `<strong>Image Insights</strong><br><br>• Dimensions: ${elementData.width}×${elementData.height}px`;
    imagePreview = `<img src="${elementData.src}" class="revela-image-preview" alt="Preview" />`;
  } else if (elementData.type === 'canvas') {
    elementType = 'Chart';
    contextMessage = `<strong>Chart Insights</strong><br><br>• Dimensions: ${elementData.width}×${elementData.height}px`;
    // For canvas, render the canvas data as image
    if (elementData.dataUrl) {
      imagePreview = `<img src="${elementData.dataUrl}" class="revela-image-preview" alt="Chart Preview" />`;
    }
  }
  
  // Create insights content
  let insightsContent = '';
  if (isLoading) {
    insightsContent = `
      <div class="revela-message revela-loading-message">
        <div class="revela-spinner-small"></div>
        <span>Generating insights...</span>
      </div>
    `;
  } else if (insights) {
    insightsContent = `
      <div class="revela-message revela-assistant-message">
        ${insights}
      </div>
    `;
  }
  
  const sidebar = document.createElement('div');
  sidebar.className = 'revela-sidebar';
  sidebar.id = `revela-sidebar-${sessionId}`;
  sidebar.innerHTML = `
    <div class="revela-sidebar-header">
      <img src="${chrome.runtime.getURL('images/logo.png')}" alt="Revela" class="revela-sidebar-logo" />
      <h3>revela - Quick Insights</h3>
      <button class="revela-close-btn" id="revela-sidebar-close">&times;</button>
    </div>
    <div class="revela-chat-container" id="revela-chat-${sessionId}">
      <div class="revela-chat-messages" id="revela-messages-${sessionId}">
        <div class="revela-context-card">
          ${imagePreview}
          <div class="revela-context-content">
            ${contextMessage}
          </div>
          <button class="revela-navigate-btn" id="revela-navigate-${sessionId}">
            Navigate to ${elementType}
          </button>
        </div>
        ${insightsContent}
      </div>
    </div>
  `;
  
  document.body.appendChild(sidebar);
  
  // Add class to body to push content
  document.body.classList.add('revela-sidebar-open');
  
  // Event listeners
  document.getElementById('revela-sidebar-close').addEventListener('click', () => {
    closeSidebar();
  });
  
  // Navigate to element button
  document.getElementById(`revela-navigate-${sessionId}`).addEventListener('click', () => {
    if (element && document.body.contains(element)) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Add temporary highlight
      element.style.outline = '3px solid #667eea';
      element.style.outlineOffset = '4px';
      setTimeout(() => {
        element.style.outline = '';
        element.style.outlineOffset = '';
      }, 2000);
    }
  });
  
  // Image preview click handler for full-screen view
  const imagePreviewEl = sidebar.querySelector('.revela-image-preview');
  if (imagePreviewEl) {
    imagePreviewEl.style.cursor = 'pointer';
    imagePreviewEl.addEventListener('click', () => {
      const imgSrc = imagePreviewEl.src;
      openFullScreenImage(imgSrc);
    });
  }
}

// Update quick insights sidebar with results or error
function updateQuickInsightsSidebar(sessionId, insights, error = null) {
  const messagesContainer = document.getElementById(`revela-messages-${sessionId}`);
  if (!messagesContainer) {
    console.error('Messages container not found for session:', sessionId);
    return;
  }
  
  // Remove loading message
  const loadingMsg = messagesContainer.querySelector('.revela-loading-message');
  if (loadingMsg) {
    loadingMsg.remove();
  }
  
  // Add insights or error message
  const messageEl = document.createElement('div');
  if (error) {
    messageEl.className = 'revela-message revela-error-message';
    messageEl.textContent = error;
  } else if (insights) {
    messageEl.className = 'revela-message revela-assistant-message';
    // Parse markdown to HTML
    messageEl.innerHTML = parseMarkdown(insights);
  }
  
  messagesContainer.appendChild(messageEl);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function closeSidebar() {
  const sidebar = document.querySelector('.revela-sidebar');
  if (sidebar) {
    sidebar.remove();
  }
  // Remove class from body to restore content
  document.body.classList.remove('revela-sidebar-open');
}

// Send message in chat
async function sendMessage(sessionId) {
  const input = document.getElementById(`revela-input-${sessionId}`);
  const messagesContainer = document.getElementById(`revela-messages-${sessionId}`);
  const apiEndpoint = await getApiEndpoint();
  
  const message = input.value.trim();
  if (!message) return;
  
  // Add user message to chat
  const userMsg = document.createElement('div');
  userMsg.className = 'revela-message revela-user-message';
  userMsg.textContent = message;
  messagesContainer.appendChild(userMsg);
  
  // Clear input
  input.value = '';
  
  // Scroll to bottom
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  // Show typing indicator
  const typingIndicator = document.createElement('div');
  typingIndicator.className = 'revela-message revela-typing-indicator';
  typingIndicator.innerHTML = '<span></span><span></span><span></span>';
  messagesContainer.appendChild(typingIndicator);
  
  try {
    // Send to backend
    const response = await fetch(`${apiEndpoint}/api/deep-analyse`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sessionId,
        message
      })
    });
    
    // Remove typing indicator
    typingIndicator.remove();
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const result = await response.json();
    
    // Add assistant response
    const assistantMsg = document.createElement('div');
    assistantMsg.className = 'revela-message revela-assistant-message';
    // Parse markdown to HTML
    assistantMsg.innerHTML = parseMarkdown(result.response);
    messagesContainer.appendChild(assistantMsg);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
  } catch (error) {
    typingIndicator.remove();
    console.error('Send message error:', error);
    
    const errorMsg = document.createElement('div');
    errorMsg.className = 'revela-message revela-error-message';
    errorMsg.textContent = 'Failed to get response. Please try again.';
    messagesContainer.appendChild(errorMsg);
  }
}

// End session
async function endSession(sessionId) {
  const apiEndpoint = await getApiEndpoint();
  
  try {
    await fetch(`${apiEndpoint}/api/session/end`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ sessionId })
    });
  } catch (error) {
    console.error('Error ending session:', error);
  }
  
  activeSessions.delete(sessionId);
}

// UI helpers
function showLoadingIndicator(message = 'Loading...') {
  removeLoadingIndicator();
  
  const loader = document.createElement('div');
  loader.className = 'revela-loading-indicator';
  loader.innerHTML = `
    <div class="revela-spinner"></div>
    <span>${message}</span>
  `;
  document.body.appendChild(loader);
}

function hideLoadingIndicator() {
  removeLoadingIndicator();
}

function removeLoadingIndicator() {
  const loader = document.querySelector('.revela-loading-indicator');
  if (loader) {
    loader.remove();
  }
}

function showError(message) {
  const error = document.createElement('div');
  error.className = 'revela-error-toast';
  error.textContent = message;
  document.body.appendChild(error);
  
  setTimeout(() => {
    error.remove();
  }, 5000);
}

function showNotification(message) {
  const notification = document.createElement('div');
  notification.className = 'revela-notification-toast';
  notification.textContent = message;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.remove();
  }, 5000);
}

// Element detection and hover handling
function toggleElementDetection(enabled) {
  if (enabled) {
    startDetection();
  } else {
    stopDetection();
  }
}

let detectionActive = false;
let hoverTimeout = null;
let currentIconElement = null; // Track which element has the icon

function startDetection() {
  if (detectionActive) return;
  
  detectionActive = true;
  console.log('Revela: Starting element detection');
  
  document.addEventListener('mouseover', handleMouseOver);
  document.addEventListener('mouseout', handleMouseOut);
}

function stopDetection() {
  detectionActive = false;
  
  document.removeEventListener('mouseover', handleMouseOver);
  document.removeEventListener('mouseout', handleMouseOut);
  
  removeHoverIcon();
  clearTimeout(hoverTimeout);
}

function handleMouseOver(e) {
  const element = e.target;
  
  // Skip if hovering over Revela UI
  if (element.closest('.revela-hover-icon, .revela-sidebar, .revela-insights-tooltip')) {
    return;
  }
  
  // Check the element itself or find the closest table/img/canvas
  let targetElement = element;
  
  // If we're hovering over a table cell, find the parent table
  if (!isAnalyzableElement(targetElement)) {
    targetElement = element.closest('TABLE, IMG, CANVAS');
  }
  
  // Debug: Log what we're hovering over
  if (element.tagName === 'TABLE' || element.tagName === 'IMG' || element.tagName === 'CANVAS' || 
      element.tagName === 'TD' || element.tagName === 'TH' || element.tagName === 'TR') {
    console.log('Revela: Hovering over', element.tagName, 'target:', targetElement?.tagName);
  }
  
  if (targetElement && isAnalyzableElement(targetElement)) {
    // If icon already exists for this element, don't recreate it
    if (currentIconElement === targetElement && document.querySelector('.revela-hover-icon')) {
      return;
    }
    
    console.log('Revela: Element is analyzable, showing icon after delay');
    hoveredElement = targetElement;
    
    clearTimeout(hoverTimeout);
    hoverTimeout = setTimeout(() => {
      if (hoveredElement === targetElement) {
        console.log('Revela: Creating hover icon for', targetElement);
        createHoverIcon(targetElement);
        currentIconElement = targetElement;
      }
    }, HOVER_DELAY);
  }
}

function handleMouseOut(e) {
  const element = e.target;
  const relatedTarget = e.relatedTarget;
  
  // For tables, check if we're leaving the entire table or just moving between cells
  if (element.tagName === 'TABLE' || element.closest('TABLE')) {
    const table = element.tagName === 'TABLE' ? element : element.closest('TABLE');
    
    // If we're moving to another element inside the same table, don't remove icon
    if (relatedTarget && relatedTarget.closest('TABLE') === table) {
      return;
    }
    
    // Only remove icon if we're actually leaving the table
    if (table === currentIconElement) {
      clearTimeout(hoverTimeout);
      
      setTimeout(() => {
        const icon = document.querySelector('.revela-hover-icon');
        // Only remove if not hovering over icon and not hovering over the table anymore
        if (icon && !icon.matches(':hover') && !table.matches(':hover')) {
          removeHoverIcon();
          currentIconElement = null;
        }
      }, 300);
    }
  } else {
    // For images and canvas, use the original logic
    if (element === hoveredElement) {
      clearTimeout(hoverTimeout);
      
      setTimeout(() => {
        const icon = document.querySelector('.revela-hover-icon');
        if (icon && !icon.matches(':hover') && !element.matches(':hover')) {
          removeHoverIcon();
          currentIconElement = null;
        }
      }, 200);
    }
  }
}

// Full-screen image viewer
function openFullScreenImage(imageSrc) {
  // Remove existing viewer if any
  closeFullScreenImage();
  
  const viewer = document.createElement('div');
  viewer.className = 'revela-fullscreen-viewer';
  viewer.id = 'revela-fullscreen-viewer';
  viewer.innerHTML = `
    <div class="revela-fullscreen-backdrop"></div>
    <div class="revela-fullscreen-content">
      <button class="revela-fullscreen-close">&times;</button>
      <img src="${imageSrc}" alt="Full screen view" class="revela-fullscreen-image" />
    </div>
  `;
  
  document.body.appendChild(viewer);
  
  // Prevent body scroll
  document.body.style.overflow = 'hidden';
  
  // Close on backdrop click
  viewer.querySelector('.revela-fullscreen-backdrop').addEventListener('click', closeFullScreenImage);
  
  // Close on close button click
  viewer.querySelector('.revela-fullscreen-close').addEventListener('click', closeFullScreenImage);
  
  // Close on ESC key
  const escHandler = (e) => {
    if (e.key === 'Escape') {
      closeFullScreenImage();
      document.removeEventListener('keydown', escHandler);
    }
  };
  document.addEventListener('keydown', escHandler);
}

function closeFullScreenImage() {
  const viewer = document.getElementById('revela-fullscreen-viewer');
  if (viewer) {
    viewer.remove();
    document.body.style.overflow = '';
  }
}

// Auto-start detection on load
console.log('Revela: Auto-starting detection on page load');
startDetection();

// Cleanup on unload
window.addEventListener('beforeunload', () => {
  try {
    // Check if extension context is still valid
    if (!chrome.runtime?.id) {
      return; // Silently exit if extension was reloaded
    }
    
    // End all active sessions
    activeSessions.forEach((_, sessionId) => {
      endSession(sessionId).catch(() => {
        // Silently ignore errors during cleanup
      });
    });
    
    stopDetection();
  } catch (error) {
    // Silently ignore all cleanup errors
  }
});
