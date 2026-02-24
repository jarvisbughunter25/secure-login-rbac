import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import User, UserRole


@pytest.fixture()
def app():
    flask_app = create_app(TestingConfig, config_overrides={"SERVER_NAME": "localhost.localdomain"})

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(app):
    def _make_user(
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
    ) -> User:
        user = User(
            username=username,
            email=email.lower(),
            role=role,
            is_active=is_active,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _make_user


@pytest.fixture()
def get_captcha_answer(client):
    def _get(scope: str) -> str:
        with client.session_transaction() as session:
            return session[f"captcha_{scope}_answer"]

    return _get


@pytest.fixture()
def register_account(client, get_captcha_answer):
    def _register(
        username: str,
        email: str,
        password: str,
        role: str = "user",
    ):
        client.get("/register")
        answer = get_captcha_answer("register")
        return client.post(
            "/register",
            data={
                "username": username,
                "email": email,
                "password": password,
                "role": role,
                "captcha_answer": answer,
            },
            follow_redirects=False,
        )

    return _register


@pytest.fixture()
def login_account(client, get_captcha_answer):
    def _login(email: str, password: str):
        client.get("/login")
        answer = get_captcha_answer("login")
        return client.post(
            "/login",
            data={
                "email": email,
                "password": password,
                "captcha_answer": answer,
            },
            follow_redirects=False,
        )

    return _login
