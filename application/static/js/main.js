// Extension detection handling
let extensionConfirmed = localStorage.getItem('extensionConfirmed') === 'true';

// Show/hide extension alerts based on state
function updateExtensionStatus() {
    const alertElement = document.getElementById('extension-alert');
    const confirmedElement = document.getElementById('extension-confirmed');
    
    if (extensionConfirmed) {
        alertElement.style.display = 'none';
        confirmedElement.style.display = 'block';
    } else {
        alertElement.style.display = 'block';
        confirmedElement.style.display = 'none';
    }
}

// Extension confirmation button
document.getElementById('confirm-extension-btn')?.addEventListener('click', () => {
    extensionConfirmed = true;
    localStorage.setItem('extensionConfirmed', 'true');
    updateExtensionStatus();
});

// Initialize extension status on load
updateExtensionStatus();

// Image handling
let currentImageData = null;
const imageUpload = document.getElementById('image-upload');
const imagePreviewContainer = document.getElementById('image-preview-container');
const imagePreview = document.getElementById('image-preview');
const removeImageBtn = document.getElementById('remove-image');

// Handle file upload
imageUpload?.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
            currentImageData = event.target.result;
            imagePreview.src = event.target.result;
            imagePreviewContainer.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
});

// Handle paste event for images
document.addEventListener('paste', (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    
    for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
            const blob = items[i].getAsFile();
            const reader = new FileReader();
            reader.onload = (event) => {
                currentImageData = event.target.result;
                imagePreview.src = event.target.result;
                imagePreviewContainer.style.display = 'block';
            };
            reader.readAsDataURL(blob);
            e.preventDefault();
            break;
        }
    }
});

// Remove image
removeImageBtn?.addEventListener('click', () => {
    currentImageData = null;
    imagePreview.src = '';
    imagePreviewContainer.style.display = 'none';
    imageUpload.value = '';
});

// Form submission
const analysisForm = document.getElementById('analysis-form');
const analyzeBtn = document.getElementById('analyze-btn');
const responseSection = document.getElementById('response-section');
const responseContent = document.getElementById('response-content');
const loadingIndicator = document.getElementById('loading-indicator');

analysisForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const prompt = document.getElementById('prompt').value.trim();
    
    if (!prompt) {
        alert('Please enter a question or analysis request.');
        return;
    }
    
    // Disable submit button and show loading
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = 'Analyzing...';
    responseSection.style.display = 'block';
    loadingIndicator.style.display = 'flex';
    responseContent.textContent = '';
    
    try {
        // Prepare request data
        const requestData = {
            prompt: prompt,
            image: currentImageData || ''
        };
        
        // Make request to analyze endpoint
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Analysis failed');
        }
        
        // Handle streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            // Decode chunk and add to buffer
            buffer += decoder.decode(value, { stream: true });
            
            // Process complete messages
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep incomplete line in buffer
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    
                    if (data.error) {
                        throw new Error(data.error);
                    }
                    
                    if (data.chunk) {
                        responseContent.textContent += data.chunk;
                    }
                    
                    if (data.done) {
                        loadingIndicator.style.display = 'none';
                        analyzeBtn.disabled = false;
                        analyzeBtn.textContent = 'Analyze';
                    }
                }
            }
        }
        
    } catch (error) {
        console.error('Error during analysis:', error);
        responseContent.textContent = `Error: ${error.message}`;
        loadingIndicator.style.display = 'none';
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = 'Analyze';
    }
});
