from functools import wraps

from flask import abort, flash, g, redirect, url_for
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.extensions import db
from app.models import User


AUTH_REDIRECT_ENDPOINT = "auth.login"


def _identity_to_user(identity) -> User | None:
    if not identity:
        return None

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None

    return db.session.get(User, user_id)


def attach_current_user() -> None:
    g.current_user = None
    try:
        verify_jwt_in_request(optional=True, locations=["cookies"])
    except Exception:
        return

    identity = get_jwt_identity()
    user = _identity_to_user(identity)
    if user and user.is_active:
        g.current_user = user


def is_authenticated() -> bool:
    return bool(getattr(g, "current_user", None))


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        attach_current_user()
        if not g.current_user:
            flash("Please log in to continue.", "warning")
            return redirect(url_for(AUTH_REDIRECT_ENDPOINT))
        return view_func(*args, **kwargs)

    return wrapped


def role_required(required_role: str):
    role_value = required_role.lower().strip()

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(*args, **kwargs):
            if g.current_user.role.value != role_value:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator
