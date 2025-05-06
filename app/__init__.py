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
            
            # Check if chromium is installed
            chromium_path = os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome")
            if not os.path.exists(chromium_path.replace("*", "1169")) and not os.path.exists(chromium_path.replace("*", "1045")):
                logging.warning("Playwright browsers not found, attempting installation...")
                
                try:
                    # Try to install Playwright browsers
                    subprocess.run(["playwright", "install", "chromium"], check=True)
                    subprocess.run(["playwright", "install-deps", "chromium"], check=True)
                    logging.info("Playwright browsers installed successfully")
                except Exception as e:
                    logging.error(f"Failed to install Playwright browsers: {str(e)}")
    except Exception as e:
        logging.error(f"Error during Playwright setup: {str(e)}")

    # Register blueprints
    from app.routes import main, api
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp)

    return app

