from datetime import UTC, datetime
from enum import Enum

from passlib.hash import argon2

from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), nullable=False, unique=True, index=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    full_name = db.Column(db.String(80), nullable=True)
    bio = db.Column(db.String(280), nullable=True)
    avatar_filename = db.Column(db.String(255), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER)

    failed_attempts = db.Column(db.Integer, nullable=False, default=0)
    failed_attempt_window_start = db.Column(db.DateTime, nullable=True)
    locked_until = db.Column(db.DateTime, nullable=True)

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    audit_logs = db.relationship("AuditLog", backref="user", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = argon2.hash(password)

    def verify_password(self, password: str) -> bool:
        return argon2.verify(password, self.password_hash)

    @property
    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > utcnow())

    def clear_lockout(self) -> None:
        self.failed_attempts = 0
        self.failed_attempt_window_start = None
        self.locked_until = None

    @property
    def display_name(self) -> str:
        value = (self.full_name or "").strip()
        return value or self.username

    @property
    def initials(self) -> str:
        source = (self.full_name or self.username or "").strip()
        if not source:
            return "U"

        parts = [part for part in source.replace("_", " ").split() if part]
        if not parts:
            return source[:1].upper()

        if len(parts) == 1:
            return parts[0][:1].upper()

        return f"{parts[0][0]}{parts[-1][0]}".upper()


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
