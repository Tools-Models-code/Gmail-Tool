import os
import logging
import subprocess
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        PROXY_LIST=os.environ.get('PROXY_LIST', ''),
        DEFAULT_PROXY_TYPE=os.environ.get('DEFAULT_PROXY_TYPE', 'http'),
    )

    CORS(app)

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
        
    # Try to ensure Playwright is properly installed
    try:
        # Check if we're in a production environment (like Render)
        if os.environ.get('RENDER') or os.environ.get('PRODUCTION'):
            logging.info("Production environment detected, checking Playwright installation...")
            
            # Configure Playwright to use the user-space installation
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.expanduser("~/.cache/ms-playwright")
            
            # Look for Playwright browsers in multiple possible locations
            chrome_paths = [
                os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
                os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome-linux/chrome"),
                os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome.exe"),
                # Add Node-installed Playwright browser paths
                os.path.expanduser("~/.cache/playwright/chromium-*/chrome-linux/chrome"),
                os.path.expanduser("~/.cache/playwright/chromium-*/chrome-win/chrome.exe"),
                # Check in node_modules too
                os.path.expanduser("~/node_modules/playwright-chromium/.local-browsers/chromium-*/chrome-linux/chrome")
            ]
            
            # Check if any of the browser paths exist
            browser_found = False
            for path_pattern in chrome_paths:
                import glob
                matching_paths = glob.glob(path_pattern)
                if matching_paths:
                    logging.info(f"Found browser at: {matching_paths[0]}")
                    browser_found = True
                    break
            
            if not browser_found:
                logging.warning("Playwright browsers not found, attempting installation...")
                
                # Try different approaches for browser installation without requiring root
                # The key is to download just the browser binaries without system dependencies
                install_attempts = [
                    # Approach 1: Use Python-based installation with skip-browser-download=0
                    {
                        "cmd": "PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/ms-playwright PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0 python -m playwright install chromium",
                        "shell": True,
                        "name": "Python-based installation"
                    },
                    # Approach 2: Use playwright-core npm package
                    {
                        "cmd": "export NVM_DIR=$HOME/.nvm && [ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\" && npm install -g playwright-core && npx playwright install chromium",
                        "shell": True,
                        "name": "NPM playwright-core"
                    },
                    # Approach 3: Direct download of browser binary using curl
                    {
                        "cmd": "mkdir -p $HOME/.cache/ms-playwright && cd $HOME/.cache/ms-playwright && curl -L https://playwright.azureedge.net/builds/chromium/1108/chromium-linux.zip -o chromium-linux.zip && unzip -o chromium-linux.zip && chmod +x chromium-*/chrome-linux/chrome",
                        "shell": True,
                        "name": "Direct download"
                    }
                ]
                
                success = False
                
                for attempt in install_attempts:
                    try:
                        logging.info(f"Attempting browser installation with {attempt['name']}...")
                        subprocess.run(attempt["cmd"], shell=attempt["shell"], check=True)
                        logging.info(f"Browser installation successful via {attempt['name']}")
                        success = True
                        break
                    except Exception as e:
                        logging.error(f"Failed {attempt['name']}: {str(e)}")
                
                if not success:
                    logging.error("All browser installation attempts failed")
    except Exception as e:
        logging.error(f"Error during Playwright setup: {str(e)}")

    # Register blueprints
    from app.routes import main, api
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp)

    return app

