import os
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

    # Register blueprints
    from app.routes import main, api
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp)

    return app

