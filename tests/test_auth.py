from app.extensions import db
from app.models import User, UserRole


def test_registration_success(register_account, app):
    response = register_account(
        username="alice_user",
        email="alice@example.com",
        password="StrongPass1!",
        role="user",
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with app.app_context():
        user = User.query.filter_by(email="alice@example.com").first()
        assert user is not None
        assert user.role == UserRole.USER
        assert user.password_hash != "StrongPass1!"


def test_registration_rejects_duplicate_username(register_account, app):
    first = register_account(
        username="same_name",
        email="first@example.com",
        password="StrongPass1!",
    )
    assert first.status_code == 302

    second = register_account(
        username="same_name",
        email="second@example.com",
        password="StrongPass1!",
    )

    assert second.status_code == 400
    assert b"already in use" in second.data

    with app.app_context():
        assert User.query.count() == 1


def test_registration_rejects_weak_password(register_account):
    response = register_account(
        username="weakpass",
        email="weak@example.com",
        password="weakpass",
    )

    assert response.status_code == 200
    assert b"Password must include" in response.data


def test_registration_rejects_invalid_email(register_account):
    response = register_account(
        username="invalidemail",
        email="not-an-email",
        password="StrongPass1!",
    )

    assert response.status_code == 200
    assert b"Invalid email address" in response.data


def test_login_success_sets_jwt_cookie(make_user, login_account):
    make_user(
        username="bob",
        email="bob@example.com",
        password="StrongPass1!",
        role=UserRole.USER,
    )

    response = login_account("bob@example.com", "StrongPass1!")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/home")
    assert any(
        "access_token_cookie=" in header
        for header in response.headers.getlist("Set-Cookie")
    )


def test_login_invalid_credentials(make_user, login_account, app):
    user = make_user(
        username="charlie",
        email="charlie@example.com",
        password="StrongPass1!",
    )

    response = login_account("charlie@example.com", "WrongPassword1!")

    assert response.status_code == 401
    assert b"Invalid credentials or account locked" in response.data

    with app.app_context():
        refreshed = db.session.get(User, user.id)
        assert refreshed.failed_attempts == 1
