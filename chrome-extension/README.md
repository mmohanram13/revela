# Revela Chrome Extension

AI-powered Chrome extension for analyzing charts and tables using Gemma.

## Development Setup

### Prerequisites
- Node.js (v16 or higher)
- npm

### Installation

```bash
cd chrome-extension
npm install
```

### Development

Run the development server with hot reload:

```bash
npm run dev
```

This will start Vite in development mode. The extension will be built to the `dist/` directory.

To load the extension in Chrome:
1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `dist/` directory from this project

The extension will automatically rebuild when you make changes to the source files.

### Production Build

Build the extension for production:

```bash
npm run build
```

The optimized extension will be output to the `dist/` directory.

## Project Structure

```
chrome-extension/
├── src/
│   ├── background/
│   │   └── background.js      # Background service worker
│   ├── content/
│   │   ├── content.js          # Content script
│   │   └── content.css         # Content styles
│   └── popup/
│       ├── popup.html          # Popup UI
│       ├── popup.js            # Popup logic
│       └── popup.css           # Popup styles
├── public/
│   ├── manifest.json           # Extension manifest
│   └── images/                 # Extension icons
├── vite.config.js              # Vite configuration
└── package.json                # Dependencies and scripts
```

## Build System

This extension uses [Vite](https://vitejs.dev/) with the [@crxjs/vite-plugin](https://crxjs.dev/vite-plugin) for building. This provides:

- Fast development with Hot Module Replacement (HMR)
- Optimized production builds
- Modern JavaScript/CSS support
- Automatic manifest handling

## Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Technologies

- **Build Tool**: Vite
- **Chrome Extension**: Manifest V3
- **AI Integration**: Gemma via Ollama
