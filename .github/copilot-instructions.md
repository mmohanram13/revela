# GitHub Copilot Instructions for Revela Project

## Python Environment & Package Management

### Virtual Environment
- **Always ensure** Python commands run in the project's virtual environment
- Activate the virtual environment with: `source .venv/bin/activate`
- If the virtual environment doesn't exist, create it with: `uv venv`

### Package Management
- **Always use `uv`** as the Python package manager
- Install packages with: `uv add <package-name>`
- Never use `pip`, `pip3`, or other package managers
- Update dependencies with: `uv add --upgrade <package-name>`

## Running the Application

### From Root Directory
- **Always run the application using**: `uv run application/main.py`
- This command automatically uses the virtual environment and `uv` package manager
- Do not run `python application/main.py` or `python main.py`

### Workflow
1. Ensure virtual environment is activated: `source .venv/bin/activate`
2. Run the application: `uv run application/main.py`

## Project Structure
- `application/` - Main application code
- `chrome-extension/` - Chrome extension code
- `ollama-gemma/` - Ollama Gemma integration (includes Docker setup)
- `pyproject.toml` - Project configuration and dependencies

## Development Guidelines

### Dependencies
- Minimum Python version: 3.11
- Current dependencies in `pyproject.toml`:
  - `ollama>=0.6.0`
- Add new dependencies to `pyproject.toml` and install with `uv pip install`

### Code Standards
- Follow Python best practices and PEP 8 style guide
- Write clear, maintainable code with appropriate comments
- Add type hints where applicable

### Before Committing
- Verify the application runs: `uv run application/main.py`
- Check that virtual environment is properly configured
- Ensure all dependencies are documented in `pyproject.toml`

## Common Commands Reference

| Task | Command |
|------|---------|
| Create virtual environment | `uv venv .venv` |
| Activate virtual environment | `source .venv/bin/activate` |
| Install packages | `uv add <package>` |
| Run application | `uv run application/main.py` |
| Add dependency to project | Edit `pyproject.toml` then run `uv add` |

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
- `chrome-extension/images/` - Extension icons and images
- `manifest.json` - Extension manifest configuration (if exists)
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
