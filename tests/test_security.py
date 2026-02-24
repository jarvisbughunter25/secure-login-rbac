from datetime import UTC, datetime, timedelta

from app.extensions import db
from app.models import User, UserRole


def _fail_login_once(client, get_captcha_answer, email: str):
    client.get("/login")
    answer = get_captcha_answer("login")
    return client.post(
        "/login",
        data={
            "email": email,
            "password": "WrongPassword1!",
            "captcha_answer": answer,
        },
        follow_redirects=False,
    )


def test_account_lockout_after_multiple_failures(app, make_user, client, get_captcha_answer):
    user = make_user(
        username="locked",
        email="locked@example.com",
        password="StrongPass1!",
    )

    attempts = app.config["LOCKOUT_MAX_ATTEMPTS"]
    for _ in range(attempts):
        response = _fail_login_once(client, get_captcha_answer, "locked@example.com")
        assert response.status_code == 401

    with app.app_context():
        refreshed = db.session.get(User, user.id)
        assert refreshed.locked_until is not None
        assert refreshed.locked_until > datetime.now(UTC).replace(tzinfo=None)

    client.get("/login")
    answer = get_captcha_answer("login")
    locked_response = client.post(
        "/login",
        data={
            "email": "locked@example.com",
            "password": "StrongPass1!",
            "captcha_answer": answer,
        },
        follow_redirects=False,
    )
    assert locked_response.status_code == 423


def test_unlock_flow_by_admin(make_user, login_account, client, app):
    admin = make_user(
        username="admin_unlock",
        email="admin_unlock@example.com",
        password="StrongPass1!",
        role=UserRole.ADMIN,
    )
    locked_user = make_user(
        username="locked2",
        email="locked2@example.com",
        password="StrongPass1!",
        role=UserRole.USER,
    )

    with app.app_context():
        target = db.session.get(User, locked_user.id)
        target.locked_until = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10)
        db.session.commit()

    login_account("admin_unlock@example.com", "StrongPass1!")

    response = client.post(
        f"/admin/users/{locked_user.id}/unlock",
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        refreshed = db.session.get(User, locked_user.id)
        assert refreshed.locked_until is None

        actor = db.session.get(User, admin.id)
        assert actor.role == UserRole.ADMIN


def test_captcha_failure_handling_on_register(client, get_captcha_answer, app):
    client.get("/register")
    _ = get_captcha_answer("register")

    response = client.post(
        "/register",
        data={
            "username": "captcha_fail",
            "email": "captcha@example.com",
            "password": "StrongPass1!",
            "role": "user",
            "captcha_answer": "99999",
        },
        follow_redirects=False,
    )

    assert response.status_code == 400

    with app.app_context():
        assert User.query.filter_by(email="captcha@example.com").first() is None


def test_directory_requires_auth_cookie(client):
    response = client.get("/directory", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_home_requires_auth_cookie(client):
    response = client.get("/home", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_turnstile_verification_failure(monkeypatch, client, app):
    app.config.update(
        TURNSTILE_ENABLED=True,
        TURNSTILE_SITE_KEY="site-key",
        TURNSTILE_SECRET_KEY="secret-key",
    )

    monkeypatch.setattr("app.auth.routes.verify_turnstile_token", lambda token, remote_ip: False)

    response = client.post(
        "/register",
        data={
            "username": "turnstile_user",
            "email": "turnstile@example.com",
            "password": "StrongPass1!",
            "role": "user",
            "cf-turnstile-response": "dummy-token",
        },
        follow_redirects=False,
    )

    assert response.status_code == 400

    with app.app_context():
        assert User.query.filter_by(email="turnstile@example.com").first() is None


def test_captcha_refresh_endpoint_returns_question(client):
    response = client.get("/captcha/login/refresh")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert "question" in payload
    assert "What is" in payload["question"]
