// Simple markdown parser for rendering LLM responses
// Lightweight alternative to full markdown libraries

/**
 * Parse markdown text and convert to HTML
 * Supports: headings, bold, lists, code blocks, line breaks
 */
function parseMarkdown(markdown) {
  if (!markdown) return '';
  
  let html = markdown;
  
  // Escape HTML to prevent XSS
  html = html.replace(/&/g, '&amp;')
             .replace(/</g, '&lt;')
             .replace(/>/g, '&gt;');
  
  // Convert code blocks (```)
  html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
  
  // Convert inline code (`)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // Convert headings (##)
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  
  // Convert bold (**text**)
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  
  // Convert italic (*text*)
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  
  // Convert numbered lists
  html = html.replace(/^(\d+)\. (.+)$/gm, '<li class="numbered-item"><span class="number">$1.</span> $2</li>');
  
  // Wrap consecutive list items in ol
  html = html.replace(/(<li class="numbered-item">.*?<\/li>\s*)+/gs, (match) => {
    return '<ol class="markdown-list">' + match + '</ol>';
  });
  
  // Convert bullet points
  html = html.replace(/^[•\-\*] (.+)$/gm, '<li>$1</li>');
  
  // Wrap consecutive bullet items in ul
  html = html.replace(/(<li>(?!.*class="numbered-item").*?<\/li>\s*)+/gs, (match) => {
    return '<ul class="markdown-list">' + match + '</ul>';
  });
  
  // Convert line breaks
  html = html.replace(/\n\n/g, '</p><p>');
  html = html.replace(/\n/g, '<br>');
  
  // Wrap in paragraph if not already wrapped
  if (!html.startsWith('<')) {
    html = '<p>' + html + '</p>';
  }
  
  return html;
}

// Export for use in content script
window.parseMarkdown = parseMarkdown;
