from datetime import UTC, datetime, timedelta

from app.extensions import db
from app.models import User, UserRole


def test_admin_can_access_dashboard(make_user, login_account, client):
    make_user(
        username="admin1",
        email="admin1@example.com",
        password="StrongPass1!",
        role=UserRole.ADMIN,
    )

    login_response = login_account("admin1@example.com", "StrongPass1!")
    assert login_response.status_code == 302

    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    assert b"Admin Dashboard" in response.data


def test_user_cannot_access_admin_dashboard(make_user, login_account, client):
    make_user(
        username="basicuser",
        email="basicuser@example.com",
        password="StrongPass1!",
        role=UserRole.USER,
    )

    login_account("basicuser@example.com", "StrongPass1!")
    response = client.get("/admin/dashboard")

    assert response.status_code == 403
    assert b"403 - Access Forbidden" in response.data


def test_admin_can_change_role_status_and_unlock(make_user, login_account, client, app):
    admin = make_user(
        username="admin2",
        email="admin2@example.com",
        password="StrongPass1!",
        role=UserRole.ADMIN,
    )
    target = make_user(
        username="target_user",
        email="target@example.com",
        password="StrongPass1!",
        role=UserRole.USER,
    )

    with app.app_context():
        locked_target = db.session.get(User, target.id)
        locked_target.locked_until = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10)
        db.session.commit()

    login_account("admin2@example.com", "StrongPass1!")

    role_response = client.post(
        f"/admin/users/{target.id}/role",
        data={"role": "admin"},
        follow_redirects=False,
    )
    assert role_response.status_code == 302

    status_response = client.post(
        f"/admin/users/{target.id}/status",
        data={"is_active": "false"},
        follow_redirects=False,
    )
    assert status_response.status_code == 302

    unlock_response = client.post(
        f"/admin/users/{target.id}/unlock",
        follow_redirects=False,
    )
    assert unlock_response.status_code == 302

    with app.app_context():
        refreshed_target = db.session.get(User, target.id)
        assert refreshed_target.role == UserRole.ADMIN
        assert refreshed_target.is_active is False
        assert refreshed_target.locked_until is None

        refreshed_admin = db.session.get(User, admin.id)
        assert refreshed_admin.role == UserRole.ADMIN


def test_admin_cannot_demote_self(make_user, login_account, client, app):
    admin = make_user(
        username="admin_self",
        email="admin_self@example.com",
        password="StrongPass1!",
        role=UserRole.ADMIN,
    )

    login_account("admin_self@example.com", "StrongPass1!")

    response = client.post(
        f"/admin/users/{admin.id}/role",
        data={"role": "user"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"cannot remove your own admin role" in response.data.lower()

    with app.app_context():
        refreshed = db.session.get(User, admin.id)
        assert refreshed.role == UserRole.ADMIN


def test_admin_can_delete_regular_user(make_user, login_account, client, app):
    make_user(
        username="admin_delete_user",
        email="admin_delete_user@example.com",
        password="StrongPass1!",
        role=UserRole.ADMIN,
    )
    target = make_user(
        username="delete_me_user",
        email="delete_me_user@example.com",
        password="StrongPass1!",
        role=UserRole.USER,
    )

    login_account("admin_delete_user@example.com", "StrongPass1!")
    response = client.post(f"/admin/users/{target.id}/delete", follow_redirects=False)
    assert response.status_code == 302

    with app.app_context():
        assert db.session.get(User, target.id) is None


def test_admin_can_delete_another_admin_when_multiple_exist(make_user, login_account, client, app):
    actor = make_user(
        username="admin_actor",
        email="admin_actor@example.com",
        password="StrongPass1!",
        role=UserRole.ADMIN,
    )
    target = make_user(
        username="admin_target",
        email="admin_target@example.com",
        password="StrongPass1!",
        role=UserRole.ADMIN,
    )

    login_account("admin_actor@example.com", "StrongPass1!")
    response = client.post(f"/admin/users/{target.id}/delete", follow_redirects=False)
    assert response.status_code == 302

    with app.app_context():
        assert db.session.get(User, target.id) is None
        remaining_admin = db.session.get(User, actor.id)
        assert remaining_admin is not None
        assert User.query.filter(User.role == UserRole.ADMIN).count() == 1


def test_last_admin_cannot_be_deleted(make_user, login_account, client, app):
    admin = make_user(
        username="last_admin",
        email="last_admin@example.com",
        password="StrongPass1!",
        role=UserRole.ADMIN,
    )

    login_account("last_admin@example.com", "StrongPass1!")
    response = client.post(f"/admin/users/{admin.id}/delete", follow_redirects=True)

    assert response.status_code == 200
    assert b"Cannot delete the last remaining admin account." in response.data

    with app.app_context():
        assert db.session.get(User, admin.id) is not None


def test_admin_can_delete_self_if_another_admin_exists(make_user, login_account, client, app):
    actor = make_user(
        username="self_delete_admin",
        email="self_delete_admin@example.com",
        password="StrongPass1!",
        role=UserRole.ADMIN,
    )
    make_user(
        username="backup_admin",
        email="backup_admin@example.com",
        password="StrongPass1!",
        role=UserRole.ADMIN,
    )

    login_account("self_delete_admin@example.com", "StrongPass1!")
    response = client.post(f"/admin/users/{actor.id}/delete", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert any(
        header.startswith("access_token_cookie=")
        and ("Max-Age=0" in header or "Expires=Thu, 01 Jan 1970" in header)
        for header in response.headers.getlist("Set-Cookie")
    )

    with app.app_context():
        assert db.session.get(User, actor.id) is None
        assert User.query.filter(User.role == UserRole.ADMIN).count() == 1


def test_admin_can_create_account_from_admin_panel(make_user, login_account, client, app):
    make_user(
        username="creator_admin",
        email="creator_admin@example.com",
        password="StrongPass1!",
        role=UserRole.ADMIN,
    )

    login_account("creator_admin@example.com", "StrongPass1!")
    response = client.post(
        "/admin/users/add",
        data={
            "full_name": "New Team Member",
            "username": "new_member",
            "email": "new_member@example.com",
            "password": "StrongPass1!",
            "role": "user",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        created = User.query.filter_by(username="new_member").first()
        assert created is not None
        assert created.role == UserRole.USER


def test_admin_can_open_add_users_page(make_user, login_account, client):
    make_user(
        username="ui_admin",
        email="ui_admin@example.com",
        password="StrongPass1!",
        role=UserRole.ADMIN,
    )

    login_account("ui_admin@example.com", "StrongPass1!")
    response = client.get("/admin/users/add")

    assert response.status_code == 200
    assert b"Add Users" in response.data
    assert b"Create Account" in response.data


def test_non_admin_cannot_create_account(make_user, login_account, client, app):
    make_user(
        username="normal_user",
        email="normal_user@example.com",
        password="StrongPass1!",
        role=UserRole.USER,
    )

    login_account("normal_user@example.com", "StrongPass1!")
    response = client.post(
        "/admin/users/add",
        data={
            "username": "blocked_create",
            "email": "blocked_create@example.com",
            "password": "StrongPass1!",
            "role": "user",
        },
        follow_redirects=False,
    )

    assert response.status_code == 403

    with app.app_context():
        assert User.query.filter_by(username="blocked_create").first() is None


def test_user_directory_is_read_only(make_user, login_account, client):
    make_user(
        username="reader",
        email="reader@example.com",
        password="StrongPass1!",
        role=UserRole.USER,
    )
    make_user(
        username="admin_directory",
        email="admin_directory@example.com",
        password="StrongPass1!",
        role=UserRole.ADMIN,
    )

    login_account("reader@example.com", "StrongPass1!")
    response = client.get("/directory")

    assert response.status_code == 200
    assert b"Members Directory" in response.data
    assert b"Deactivate" not in response.data
    assert b"Unlock" not in response.data
    assert b"Delete" not in response.data
    assert b"Add User/Admin" not in response.data
