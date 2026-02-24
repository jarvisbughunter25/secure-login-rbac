import io
from pathlib import Path

from app.extensions import db
from app.models import User, UserRole


def test_user_can_update_profile_details(make_user, login_account, client, app):
    user = make_user(
        username="profile_user",
        email="profile_user@example.com",
        password="StrongPass1!",
        role=UserRole.USER,
    )

    login_account("profile_user@example.com", "StrongPass1!")

    response = client.post(
        "/profile/details",
        data={
            "full_name": "Profile User",
            "username": "profile_user_updated",
            "email": "profile_user_updated@example.com",
            "bio": "Security analyst and blue-team enthusiast.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    with app.app_context():
        refreshed = db.session.get(User, user.id)
        assert refreshed.full_name == "Profile User"
        assert refreshed.username == "profile_user_updated"
        assert refreshed.email == "profile_user_updated@example.com"
        assert refreshed.bio == "Security analyst and blue-team enthusiast."


def test_user_can_change_password(make_user, login_account, client):
    make_user(
        username="password_user",
        email="password_user@example.com",
        password="StrongPass1!",
        role=UserRole.USER,
    )

    login_account("password_user@example.com", "StrongPass1!")

    update_response = client.post(
        "/profile/password",
        data={
            "current_password": "StrongPass1!",
            "new_password": "NewStrongPass2@",
            "confirm_password": "NewStrongPass2@",
        },
        follow_redirects=False,
    )
    assert update_response.status_code == 302

    client.post("/logout", follow_redirects=False)

    login_response = login_account("password_user@example.com", "NewStrongPass2@")
    assert login_response.status_code == 302


def test_user_can_upload_avatar(make_user, login_account, client, app):
    user = make_user(
        username="avatar_user",
        email="avatar_user@example.com",
        password="StrongPass1!",
        role=UserRole.USER,
    )

    login_account("avatar_user@example.com", "StrongPass1!")

    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128
    response = client.post(
        "/profile/avatar",
        data={"avatar": (io.BytesIO(fake_png), "avatar.png")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        refreshed = db.session.get(User, user.id)
        assert refreshed.avatar_filename is not None

        upload_path = (
            Path(app.static_folder)
            / app.config.get("AVATAR_UPLOAD_SUBDIR", "uploads/avatars")
            / refreshed.avatar_filename
        )
        assert upload_path.exists()
        upload_path.unlink()


def test_avatar_upload_rejects_invalid_extension(make_user, login_account, client):
    make_user(
        username="avatar_invalid",
        email="avatar_invalid@example.com",
        password="StrongPass1!",
        role=UserRole.USER,
    )

    login_account("avatar_invalid@example.com", "StrongPass1!")

    response = client.post(
        "/profile/avatar",
        data={"avatar": (io.BytesIO(b"not-an-image"), "avatar.txt")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert b"Allowed types" in response.data


def test_user_can_remove_uploaded_avatar(make_user, login_account, client, app):
    user = make_user(
        username="avatar_remove_user",
        email="avatar_remove_user@example.com",
        password="StrongPass1!",
        role=UserRole.USER,
    )
    login_account("avatar_remove_user@example.com", "StrongPass1!")

    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 256
    upload_response = client.post(
        "/profile/avatar",
        data={"avatar": (io.BytesIO(fake_png), "avatar-remove.png")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert upload_response.status_code == 302

    with app.app_context():
        refreshed = db.session.get(User, user.id)
        uploaded_filename = refreshed.avatar_filename
        assert uploaded_filename is not None
        uploaded_path = (
            Path(app.static_folder)
            / app.config.get("AVATAR_UPLOAD_SUBDIR", "uploads/avatars")
            / uploaded_filename
        )
        assert uploaded_path.exists()

    remove_response = client.post("/profile/avatar/remove", follow_redirects=False)
    assert remove_response.status_code == 302
    assert remove_response.headers["Location"].endswith("/profile")

    with app.app_context():
        refreshed = db.session.get(User, user.id)
        assert refreshed.avatar_filename is None
        assert not uploaded_path.exists()
