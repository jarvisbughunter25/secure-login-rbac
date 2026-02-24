import os
from datetime import timedelta


def get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me-32chars-min")
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY",
        "dev-jwt-secret-key-change-me-32chars-min",
    )
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://secure_user:secure_password@localhost/secure_login_db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_HTTPONLY = True
    JWT_COOKIE_SECURE = get_bool_env("JWT_COOKIE_SECURE", False)
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    AVATAR_MAX_MB = int(os.getenv("AVATAR_MAX_MB", 2))
    MAX_CONTENT_LENGTH = AVATAR_MAX_MB * 1024 * 1024
    AVATAR_UPLOAD_SUBDIR = os.getenv("AVATAR_UPLOAD_SUBDIR", "uploads/avatars")
    ALLOWED_AVATAR_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    WTF_CSRF_TIME_LIMIT = None

    TURNSTILE_ENABLED = get_bool_env("TURNSTILE_ENABLED", False)
    TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY", "")
    TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")

    LOCKOUT_MAX_ATTEMPTS = int(os.getenv("LOCKOUT_MAX_ATTEMPTS", 5))
    LOCKOUT_WINDOW_MINUTES = int(os.getenv("LOCKOUT_WINDOW_MINUTES", 15))
    LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", 30))

    ALLOW_ADMIN_SELF_REGISTRATION = get_bool_env("ALLOW_ADMIN_SELF_REGISTRATION", True)


class DevelopmentConfig(BaseConfig):
    # Security-first default: keep debugger OFF unless explicitly enabled.
    DEBUG = get_bool_env("FLASK_DEBUG", False)


class ProductionConfig(BaseConfig):
    DEBUG = False


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    JWT_COOKIE_SECURE = False
    TURNSTILE_ENABLED = False
    ALLOW_ADMIN_SELF_REGISTRATION = True


config_by_name = {
    "production": ProductionConfig,
    "development": DevelopmentConfig,
    "testing": TestingConfig,
}
