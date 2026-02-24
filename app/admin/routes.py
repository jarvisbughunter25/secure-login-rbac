from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from flask_jwt_extended import unset_jwt_cookies
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.admin.forms import AdminCreateUserForm
from app.extensions import db
from app.models import AuditLog, User, UserRole, utcnow
from app.security.audit import record_audit_event
from app.security.authz import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _admin_count() -> int:
    return User.query.filter(User.role == UserRole.ADMIN).count()


def _first_form_error(form: AdminCreateUserForm) -> str:
    for field_errors in form.errors.values():
        if field_errors:
            return field_errors[0]
    return "Invalid input."


def _render_add_users_page(form: AdminCreateUserForm, status_code: int = 200):
    recent_users = User.query.order_by(User.created_at.desc()).limit(8).all()
    return (
        render_template(
            "admin/add_users.html",
            form=form,
            recent_users=recent_users,
        ),
        status_code,
    )


@admin_bp.get("/dashboard")
@role_required("admin")
def dashboard():
    users = User.query.order_by(User.created_at.desc()).all()

    total_users = User.query.count()
    admin_count = _admin_count()
    active_count = User.query.filter(User.is_active.is_(True)).count()
    locked_count = User.query.filter(User.locked_until.isnot(None), User.locked_until > utcnow()).count()

    return render_template(
        "admin/dashboard.html",
        users=users,
        admin_count=admin_count,
        total_users=total_users,
        active_count=active_count,
        locked_count=locked_count,
    )


@admin_bp.route("/users/add", methods=["GET", "POST"])
@role_required("admin")
def add_users():
    actor = g.current_user
    form = AdminCreateUserForm()

    if request.method == "GET":
        return _render_add_users_page(form)

    if not form.validate_on_submit():
        flash(_first_form_error(form), "danger")
        return _render_add_users_page(form, 400)

    username = form.username.data.strip()
    email = form.email.data.strip().lower()

    if User.query.filter(func.lower(User.username) == username.lower()).first():
        form.username.errors.append("Username already exists.")
        return _render_add_users_page(form, 400)

    if User.query.filter(func.lower(User.email) == email).first():
        form.email.errors.append("Email already exists.")
        return _render_add_users_page(form, 400)

    selected_role = form.role.data.lower().strip()
    role = UserRole.ADMIN if selected_role == UserRole.ADMIN.value else UserRole.USER

    user = User(
        full_name=(form.full_name.data or "").strip() or None,
        username=username,
        email=email,
        role=role,
    )
    user.set_password(form.password.data)

    try:
        db.session.add(user)
        db.session.flush()
        record_audit_event(f"admin_create_user_target_{user.id}", "success", actor)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Unable to create user due to duplicate data.", "danger")
        return _render_add_users_page(form, 409)

    flash(f"New {role.value} account created for {user.username}.", "success")
    return redirect(url_for("admin.add_users"))


@admin_bp.post("/users/<int:user_id>/role")
@role_required("admin")
def update_role(user_id: int):
    target = db.session.get(User, user_id)
    if not target:
        abort(404)
    actor = g.current_user

    new_role = request.form.get("role", "").strip().lower()
    if new_role not in {UserRole.ADMIN.value, UserRole.USER.value}:
        flash("Invalid role value.", "danger")
        return redirect(url_for("admin.dashboard"))

    if target.id == actor.id and new_role != UserRole.ADMIN.value:
        flash("You cannot remove your own admin role.", "warning")
        return redirect(url_for("admin.dashboard"))

    if target.role == UserRole.ADMIN and new_role == UserRole.USER.value and _admin_count() <= 1:
        flash("Cannot demote the last remaining admin.", "warning")
        return redirect(url_for("admin.dashboard"))

    target.role = UserRole.ADMIN if new_role == UserRole.ADMIN.value else UserRole.USER
    record_audit_event(f"role_change_target_{target.id}", "success", actor)
    db.session.commit()

    flash("User role updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/users/<int:user_id>/status")
@role_required("admin")
def update_status(user_id: int):
    target = db.session.get(User, user_id)
    if not target:
        abort(404)
    actor = g.current_user

    active_value = request.form.get("is_active", "true").strip().lower()
    should_activate = active_value in {"1", "true", "yes", "on"}

    if target.id == actor.id and not should_activate:
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for("admin.dashboard"))

    if target.role == UserRole.ADMIN and not should_activate and _admin_count() <= 1:
        flash("Cannot deactivate the last remaining admin.", "warning")
        return redirect(url_for("admin.dashboard"))

    target.is_active = should_activate
    if should_activate:
        action = "activate"
    else:
        action = "deactivate"
        target.clear_lockout()

    record_audit_event(f"{action}_target_{target.id}", "success", actor)
    db.session.commit()

    flash("User status updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/users/<int:user_id>/unlock")
@role_required("admin")
def unlock_user(user_id: int):
    target = db.session.get(User, user_id)
    if not target:
        abort(404)
    actor = g.current_user

    target.clear_lockout()
    record_audit_event(f"unlock_target_{target.id}", "success", actor)
    db.session.commit()

    flash("User account unlocked.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/users/<int:user_id>/delete")
@role_required("admin")
def delete_user(user_id: int):
    target = db.session.get(User, user_id)
    if not target:
        abort(404)

    actor = g.current_user
    deleting_self = target.id == actor.id

    if target.role == UserRole.ADMIN and _admin_count() <= 1:
        flash("Cannot delete the last remaining admin account.", "warning")
        return redirect(url_for("admin.dashboard"))

    # Preserve historical logs by nulling user ownership before deleting account.
    AuditLog.query.filter(AuditLog.user_id == target.id).update({AuditLog.user_id: None})

    target_label = target.username
    db.session.delete(target)

    if deleting_self:
        record_audit_event(f"self_delete_target_{user_id}", "success")
    else:
        record_audit_event(f"delete_target_{user_id}", "success", actor)

    db.session.commit()

    if deleting_self:
        response = redirect(url_for("auth.login"))
        unset_jwt_cookies(response)
        flash("Your account was deleted.", "info")
        return response

    flash(f"User '{target_label}' deleted.", "success")
    return redirect(url_for("admin.dashboard"))
