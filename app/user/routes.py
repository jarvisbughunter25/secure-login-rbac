from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, flash, g, redirect, render_template, url_for
from sqlalchemy import case, func
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import User, UserRole, utcnow
from app.security.audit import record_audit_event
from app.security.authz import login_required
from app.user.forms import AvatarUploadForm, PasswordChangeForm, ProfileDetailsForm

user_bp = Blueprint("user", __name__)


def _avatar_dir() -> Path:
    subdir = current_app.config.get("AVATAR_UPLOAD_SUBDIR", "uploads/avatars").strip("/")
    directory = Path(current_app.static_folder) / subdir
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _remove_avatar_file(filename: str | None) -> None:
    if not filename:
        return

    path = _avatar_dir() / filename
    if path.exists() and path.is_file():
        path.unlink()


def _profile_forms(user: User):
    details_form = ProfileDetailsForm(
        full_name=user.full_name or "",
        username=user.username,
        email=user.email,
        bio=user.bio or "",
    )
    password_form = PasswordChangeForm()
    avatar_form = AvatarUploadForm()
    return details_form, password_form, avatar_form


def _render_profile(
    user: User,
    details_form: ProfileDetailsForm | None = None,
    password_form: PasswordChangeForm | None = None,
    avatar_form: AvatarUploadForm | None = None,
    status_code: int = 200,
):
    if details_form is None or password_form is None or avatar_form is None:
        details_form, password_form, avatar_form = _profile_forms(user)

    return (
        render_template(
            "user/profile.html",
            user=user,
            details_form=details_form,
            password_form=password_form,
            avatar_form=avatar_form,
            avatar_max_mb=current_app.config.get("AVATAR_MAX_MB", 2),
        ),
        status_code,
    )


@user_bp.get("/directory")
@login_required
def directory():
    role_order = case((User.role == UserRole.ADMIN, 0), else_=1)
    users = User.query.order_by(role_order.asc(), func.lower(User.username).asc()).all()
    admin_count = sum(1 for user in users if user.role == UserRole.ADMIN)
    user_count = len(users) - admin_count
    return render_template("user/directory.html", users=users, admin_count=admin_count, user_count=user_count)


@user_bp.get("/home")
@login_required
def home():
    user = g.current_user

    total_users = User.query.count()
    admin_count = User.query.filter(User.role == UserRole.ADMIN).count()
    user_count = User.query.filter(User.role == UserRole.USER).count()
    active_count = User.query.filter(User.is_active.is_(True)).count()
    locked_count = User.query.filter(User.locked_until.isnot(None), User.locked_until > utcnow()).count()

    return render_template(
        "user/home.html",
        user=user,
        total_users=total_users,
        admin_count=admin_count,
        user_count=user_count,
        active_count=active_count,
        locked_count=locked_count,
    )


@user_bp.get("/dashboard")
@login_required
def dashboard_legacy_redirect():
    return redirect(url_for("user.home"))


@user_bp.get("/profile")
@login_required
def profile():
    return _render_profile(g.current_user)


@user_bp.post("/profile/details")
@login_required
def update_profile_details():
    user = g.current_user
    details_form = ProfileDetailsForm()
    _, password_form, avatar_form = _profile_forms(user)

    if not details_form.validate_on_submit():
        return _render_profile(
            user,
            details_form=details_form,
            password_form=password_form,
            avatar_form=avatar_form,
            status_code=400,
        )

    new_username = details_form.username.data.strip()
    new_email = details_form.email.data.strip().lower()
    new_full_name = (details_form.full_name.data or "").strip() or None
    new_bio = (details_form.bio.data or "").strip() or None

    username_conflict = User.query.filter(
        func.lower(User.username) == new_username.lower(),
        User.id != user.id,
    ).first()
    if username_conflict:
        details_form.username.errors.append("This username is already in use.")

    email_conflict = User.query.filter(
        func.lower(User.email) == new_email,
        User.id != user.id,
    ).first()
    if email_conflict:
        details_form.email.errors.append("This email is already registered.")

    if details_form.username.errors or details_form.email.errors:
        return _render_profile(
            user,
            details_form=details_form,
            password_form=password_form,
            avatar_form=avatar_form,
            status_code=400,
        )

    user.full_name = new_full_name
    user.username = new_username
    user.email = new_email
    user.bio = new_bio

    record_audit_event("profile_update", "success", user)
    db.session.commit()

    flash("Profile details updated.", "success")
    return redirect(url_for("user.profile"))


@user_bp.post("/profile/password")
@login_required
def update_profile_password():
    user = g.current_user
    details_form, _, avatar_form = _profile_forms(user)
    password_form = PasswordChangeForm()

    if not password_form.validate_on_submit():
        return _render_profile(
            user,
            details_form=details_form,
            password_form=password_form,
            avatar_form=avatar_form,
            status_code=400,
        )

    if not user.verify_password(password_form.current_password.data):
        password_form.current_password.errors.append("Current password is incorrect.")
        return _render_profile(
            user,
            details_form=details_form,
            password_form=password_form,
            avatar_form=avatar_form,
            status_code=400,
        )

    user.set_password(password_form.new_password.data)
    record_audit_event("password_change", "success", user)
    db.session.commit()

    flash("Password updated successfully.", "success")
    return redirect(url_for("user.profile"))


@user_bp.post("/profile/avatar")
@login_required
def update_profile_avatar():
    user = g.current_user
    details_form, password_form, _ = _profile_forms(user)
    avatar_form = AvatarUploadForm()

    if not avatar_form.validate_on_submit():
        return _render_profile(
            user,
            details_form=details_form,
            password_form=password_form,
            avatar_form=avatar_form,
            status_code=400,
        )

    upload = avatar_form.avatar.data
    original_name = secure_filename(upload.filename or "")
    if "." not in original_name:
        avatar_form.avatar.errors.append("File extension is required.")
        return _render_profile(
            user,
            details_form=details_form,
            password_form=password_form,
            avatar_form=avatar_form,
            status_code=400,
        )

    extension = original_name.rsplit(".", 1)[1].lower()
    allowed_extensions = current_app.config.get("ALLOWED_AVATAR_EXTENSIONS", {"png", "jpg", "jpeg", "webp"})
    if extension not in allowed_extensions:
        avatar_form.avatar.errors.append("Unsupported file extension.")
        return _render_profile(
            user,
            details_form=details_form,
            password_form=password_form,
            avatar_form=avatar_form,
            status_code=400,
        )

    saved_name = f"user_{user.id}_{uuid4().hex[:12]}.{extension}"
    destination = _avatar_dir() / saved_name
    upload.save(destination)

    previous_avatar = user.avatar_filename
    user.avatar_filename = saved_name

    record_audit_event("avatar_update", "success", user)
    db.session.commit()

    _remove_avatar_file(previous_avatar)

    flash("Profile photo updated.", "success")
    return redirect(url_for("user.profile"))


@user_bp.post("/profile/avatar/remove")
@login_required
def remove_profile_avatar():
    user = g.current_user
    if not user.avatar_filename:
        flash("No custom profile photo to remove.", "info")
        return redirect(url_for("user.profile"))

    previous_avatar = user.avatar_filename
    user.avatar_filename = None

    record_audit_event("avatar_remove", "success", user)
    db.session.commit()

    _remove_avatar_file(previous_avatar)

    flash("Profile photo removed.", "success")
    return redirect(url_for("user.profile"))
