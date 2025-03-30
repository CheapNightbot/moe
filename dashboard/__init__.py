import os
from flask import Flask


def create_app():
    app = Flask(__name__)
    # Use a secure secret key; set SECRET_KEY in your environment for production.
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        # To generate a secure key, run:
        # python -c "import secrets; print(secrets.token_hex(32))"
        raise RuntimeError("SECRET_KEY environment variable is not set!")
    app.config["SECRET_KEY"] = secret_key

    # Register blueprints
    from .routes.main import main_bp

    app.register_blueprint(main_bp)

    return app
