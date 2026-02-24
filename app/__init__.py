import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, g, redirect, render_template, url_for

# Load .env deterministically before app config resolution.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

from app.config import BaseConfig, config_by_name
from app.extensions import csrf, db, jwt, migrate
from app.models import utcnow
from app.security.authz import attach_current_user, is_authenticated


def create_app(config_object=None, config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(BaseConfig)

    if config_object is None:
        env_name = os.getenv("FLASK_ENV", "production").strip().lower()
        app.config.from_object(config_by_name.get(env_name, BaseConfig))
    elif isinstance(config_object, dict):
        app.config.from_mapping(config_object)
    else:
        app.config.from_object(config_object)

    if config_overrides:
        app.config.from_mapping(config_overrides)

    register_extensions(app)
    register_blueprints(app)
    register_handlers(app)

    @app.before_request
    def _load_current_user():
        attach_current_user()

    @app.context_processor
    def inject_helpers():
        def avatar_url(user) -> str:
            if user and user.avatar_filename:
                subdir = app.config.get("AVATAR_UPLOAD_SUBDIR", "uploads/avatars").strip("/")
                return url_for("static", filename=f"{subdir}/{user.avatar_filename}")
            return url_for("static", filename="img/avatar-default.svg")

        return {
            "utcnow": utcnow,
            "avatar_url": avatar_url,
        }

    @app.get("/")
    def index():
        if is_authenticated():
            return redirect(url_for("user.home"))
        return render_template("landing.html")

    return app


def register_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    csrf.init_app(app)


def register_blueprints(app: Flask) -> None:
    from app.admin.routes import admin_bp
    from app.auth.routes import auth_bp
    from app.user.routes import user_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)


def register_handlers(app: Flask) -> None:
    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(413)
    def payload_too_large(_error):
        flash(
            f"Uploaded file is too large. Maximum allowed is {app.config.get('AVATAR_MAX_MB', 2)} MB.",
            "danger",
        )
        if is_authenticated():
            return redirect(url_for("user.profile"))
        return render_template("errors/413.html"), 413
