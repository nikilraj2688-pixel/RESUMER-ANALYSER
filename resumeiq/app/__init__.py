import logging
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .config import Config

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "60 per hour"],
    storage_uri="memory://"
)

def create_app(config_class=Config) -> Flask:
    """Application factory for ResumeIQ."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Logging setup
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Extensions
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    limiter.init_app(app)

    # Register Blueprints
    from .routes.analyze import analyze_bp
    from .routes.history import history_bp
    from .routes.roles import roles_bp
    from .routes.web import web_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(analyze_bp, url_prefix="/api")
    app.register_blueprint(history_bp, url_prefix="/api")
    app.register_blueprint(roles_bp, url_prefix="/api")

    return app

