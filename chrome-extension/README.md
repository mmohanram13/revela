# Revela Chrome Extension

AI-powered Chrome extension for analyzing charts and tables using Gemma.

## Features

- 🔍 Analyze charts and tables on any webpage
- 📊 Automatic detection of visualizations
- 🤖 AI-powered insights using Gemma
- 🎯 Context menu integration
- ⚡ Fast and lightweight

## Installation

### Development Mode

1. Install dependencies:
   ```bash
   npm install
   ```

2. Open Chrome and navigate to `chrome://extensions/`

3. Enable "Developer mode" (toggle in top-right corner)

4. Click "Load unpacked"

5. Select the `chrome-extension` directory

### Usage

1. Click the Revela icon in your browser toolbar
2. Choose an action:
   - **Analyze Current Page**: Detects and analyzes all charts/tables on the page
   - **Capture Selection**: Analyzes a selected element
3. Right-click on any image and select "Analyze with Revela"

## Configuration

The extension connects to the local API endpoint at `http://localhost:8000` by default. You can change this in the extension settings.

## File Structure

```
chrome-extension/
├── manifest.json          # Extension configuration
├── popup.html            # Popup UI
├── popup.css             # Popup styles
├── popup.js              # Popup logic
├── background.js         # Background service worker
├── content.js            # Content script for page interaction
├── content.css           # Content script styles
├── package.json          # Node dependencies
└── images/               # Extension icons and assets
```

## Development

### Testing
1. Make changes to the extension files
2. Go to `chrome://extensions/`
3. Click the refresh icon on the Revela extension card
4. Test the changes

### Debugging
- **Popup**: Right-click the popup and select "Inspect"
- **Background**: Click "Inspect views: service worker" on the extension card
- **Content Script**: Use the browser's developer tools on any webpage

## API Integration

The extension communicates with the backend API running at `http://localhost:8000`. Make sure the backend server is running before using the extension.

### API Endpoints

- `POST /analyze` - Analyze an image or table
  ```json
  {
    "image": "base64_encoded_image",
    "type": "chart|table"
  }
  ```

## Permissions

The extension requires the following permissions:
- `activeTab` - Access the current tab for analysis
- `storage` - Save user settings
- `scripting` - Inject content scripts for page analysis
- `contextMenus` - Add right-click menu options

## Contributing

When making changes:
1. Test thoroughly in Chrome
2. Ensure all dependencies are in `package.json`
3. Verify `manifest.json` is correctly configured
4. Check that the extension loads without errors

## License

MIT
