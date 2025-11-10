# GitHub Copilot Instructions for Revela Project

## Python Environment & Package Management

### Virtual Environment
- **Always ensure** Python commands run in the project's virtual environment
- Activate the virtual environment with: `source revela-app/.venv/bin/activate`
- If the virtual environment doesn't exist, create it with: `cd revela-app && uv venv`

### Package Management
- **Always use `uv`** as the Python package manager
- Install packages with: `uv add <package-name>`
- Never use `pip`, `pip3`, or other package managers
- Update dependencies with: `uv add --upgrade <package-name>`

## Running the Application

### From Root Directory
- **Always run the application using**: `cd revela-app && ./start-app.sh`
- Or manually from revela-app directory: `uv run gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 --reload src.app:app`
- Uses gunicorn for both local development and production for consistency
- The `--reload` flag enables auto-reload on code changes during development

### Workflow
1. Navigate to revela-app: `cd revela-app`
2. Ensure virtual environment is activated: `source .venv/bin/activate`
3. Run the application: `./start-app.sh`
4. Access the app at: http://localhost:8080

## Project Structure
- `revela-app/` - Main application code (Flask app with gunicorn)
  - `.venv/` - Virtual environment
  - `pyproject.toml` - Project configuration and dependencies
  - `Dockerfile` - Production Docker configuration
  - `start-app.sh` - Application startup script
  - `src/` - Source code directory (all Python files)
    - `__init__.py` - Package initialization
    - `app.py` - Flask application and routes
    - `config_module.py` - Configuration management
    - `ollama_client.py` - Ollama API client
    - `images/` - Image assets
  - `ui/` - User interface assets
    - `static/` - Static assets
      - `styles.css` - CSS styles
      - `index.js` - JavaScript
    - `templates/` - HTML templates
      - `index.html` - Main page template
- `chrome-extension/` - Chrome extension code
  - `src/` - Source code directory
    - `background/` - Background service worker (background.js)
    - `content/` - Content scripts (content.js, content.css)
    - `popup/` - Extension popup (popup.html, popup.js, popup.css)
  - `public/` - Public assets
    - `manifest.json` - Extension manifest
    - `images/` - Extension icons and images
- `ollama-gemma/` - Ollama Gemma integration (includes Docker setup)

## Development Guidelines

### Dependencies
- Minimum Python version: 3.11
- Current dependencies in `revela-app/pyproject.toml`:
  - `ollama>=0.6.0`
  - `flask>=3.0.0`
  - `gunicorn>=23.0.0`
  - Other dependencies as listed
- Add new dependencies from revela-app directory: `cd revela-app && uv add <package>`

### Code Standards
- Follow Python best practices and PEP 8 style guide
- Write clear, maintainable code with appropriate comments
- Add type hints where applicable
- Use relative imports in modules (`from .config import config`)

### Before Committing
- Verify the application runs: `cd revela-app && ./start-app.sh`
- Check that virtual environment is properly configured
- Ensure all dependencies are documented in `revela-app/pyproject.toml`
- Test Docker build: `cd revela-app && docker build -t revela-app .`

## Common Commands Reference

| Task | Command |
|------|---------|
| Create virtual environment | `cd revela-app && uv venv .venv` |
| Activate virtual environment | `source revela-app/.venv/bin/activate` |
| Install packages | `cd revela-app && uv add <package>` |
| Run application (local) | `cd revela-app && ./start-app.sh` |
| Run with gunicorn manually | `cd revela-app && uv run gunicorn --bind 0.0.0.0:8080 --workers 2 --reload src.api.app:app` |
| Build Docker image | `cd revela-app && docker build -t revela-app .` |
| Run Docker container | `docker run -p 8080:8080 revela-app` |
| Add dependency to project | `cd revela-app && uv add <package>` |

## Chrome Extension Development

### Package Management
- **Always use `npm`** as the JavaScript package manager for the Chrome extension
- Install packages with: `npm install <package-name>`
- Install dev dependencies with: `npm install --save-dev <package-name>`
- Never use `yarn`, `pnpm`, or other package managers for the extension

### Working with the Chrome Extension

#### From chrome-extension Directory
- Navigate to the extension directory: `cd chrome-extension`
- Install dependencies: `npm install`
- Build the extension (if build script exists): `npm run build`
- Run development mode (if available): `npm run dev`

### Extension Structure
- `chrome-extension/` - Chrome extension root directory
  - `src/` - Source code directory
    - `background/` - Background service worker
    - `content/` - Content scripts and styles
    - `popup/` - Popup UI (HTML, CSS, JS)
  - `public/` - Public assets
    - `manifest.json` - Extension manifest configuration
    - `images/` - Extension icons and images
  - `package.json` - Node dependencies and scripts (if exists)

### Development Guidelines

#### JavaScript Standards
- Follow modern JavaScript (ES6+) best practices
- Use `const` and `let` instead of `var`
- Write clear, maintainable code with appropriate comments
- Use async/await for asynchronous operations
- Follow Chrome Extension API best practices

#### Chrome Extension Best Practices
- Keep background scripts lightweight
- Use content scripts for page interaction
- Implement proper message passing between extension components
- Handle permissions appropriately in manifest
- Test extension in Chrome before committing

### Before Committing
- Test the extension in Chrome browser
- Ensure all dependencies are documented in `package.json`
- Verify manifest.json is properly configured
- Check that extension loads without errors

### Common Commands Reference

| Task | Command |
|------|---------|
| Navigate to extension | `cd chrome-extension` |
| Install dependencies | `npm install` |
| Add package | `npm install <package>` |
| Add dev dependency | `npm install --save-dev <package>` |
| Build extension | `npm run build` |
| Development mode | `npm run dev` |

## Notes
- This is a Chrome extension project with AI-powered chart/table analysis using Gemma
- Docker setup is available in `ollama-gemma/` for local model deployment
- Always reference the `.venv/bin/activate` script for environment setup
- Chrome extension uses npm for JavaScript dependencies
