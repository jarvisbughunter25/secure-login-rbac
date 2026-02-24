from flask import Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.auth.forms import LoginForm, RegistrationForm
from app.extensions import db
from app.models import User, UserRole, utcnow
from app.security.audit import record_audit_event
from app.security.authz import is_authenticated, login_required
from app.security.captcha import (
    generate_math_challenge,
    get_math_challenge,
    is_turnstile_enabled,
    verify_math_challenge,
    verify_turnstile_token,
)
from app.security.lockout import clear_failed_attempts, is_account_locked, record_failed_attempt

auth_bp = Blueprint("auth", __name__)


def _captcha_context(scope: str) -> dict:
    turnstile_enabled = is_turnstile_enabled()
    return {
        "turnstile_enabled": turnstile_enabled,
        "turnstile_site_key": current_app.config.get("TURNSTILE_SITE_KEY", ""),
        "captcha_question": None if turnstile_enabled else get_math_challenge(scope),
    }


def _validate_captcha(scope: str, submitted_math_answer: str) -> bool:
    if is_turnstile_enabled():
        token = request.form.get("cf-turnstile-response", "")
        return verify_turnstile_token(token, request.remote_addr)
    return verify_math_challenge(scope, submitted_math_answer)


@auth_bp.get("/captcha/<string:scope>/refresh")
def refresh_captcha(scope: str):
    if scope not in {"login", "register"}:
        abort(404)

    if is_turnstile_enabled():
        return jsonify({"error": "Math captcha is disabled when Turnstile is enabled."}), 400

    question = generate_math_challenge(scope)
    return jsonify({"question": question})


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if is_authenticated():
        return redirect(url_for("user.home"))

    form = RegistrationForm()

    if request.method == "GET" and not is_turnstile_enabled():
        generate_math_challenge("register")

    if form.validate_on_submit():
        if not _validate_captcha("register", form.captcha_answer.data):
            flash("CAPTCHA verification failed. Please try again.", "danger")
            record_audit_event("register_captcha_fail", "failure")
            db.session.commit()
            if not is_turnstile_enabled():
                generate_math_challenge("register")
            return render_template("auth/register.html", form=form, **_captcha_context("register")), 400

        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        if User.query.filter(func.lower(User.username) == username.lower()).first():
            form.username.errors.append("This username is already in use.")
            if not is_turnstile_enabled():
                generate_math_challenge("register")
            return render_template("auth/register.html", form=form, **_captcha_context("register")), 400

        if User.query.filter(func.lower(User.email) == email).first():
            form.email.errors.append("This email is already registered.")
            if not is_turnstile_enabled():
                generate_math_challenge("register")
            return render_template("auth/register.html", form=form, **_captcha_context("register")), 400

        selected_role = form.role.data.lower()
        if selected_role == UserRole.ADMIN.value and not current_app.config.get(
            "ALLOW_ADMIN_SELF_REGISTRATION", True
        ):
            form.role.errors.append("Admin self-registration is disabled.")
            if not is_turnstile_enabled():
                generate_math_challenge("register")
            return render_template("auth/register.html", form=form, **_captcha_context("register")), 403

        user = User(
            username=username,
            email=email,
            role=UserRole.ADMIN if selected_role == UserRole.ADMIN.value else UserRole.USER,
        )
        user.set_password(form.password.data)

        try:
            db.session.add(user)
            db.session.flush()
            record_audit_event("register", "success", user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Registration failed due to conflicting user data.", "danger")
            if not is_turnstile_enabled():
                generate_math_challenge("register")
            return render_template("auth/register.html", form=form, **_captcha_context("register")), 409

        flash("Account created successfully. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    if form.errors and request.method == "POST" and not is_turnstile_enabled():
        generate_math_challenge("register")

    return render_template("auth/register.html", form=form, **_captcha_context("register"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if is_authenticated():
        return redirect(url_for("user.home"))

    form = LoginForm()

    if request.method == "GET" and not is_turnstile_enabled():
        generate_math_challenge("login")

    if form.validate_on_submit():
        if not _validate_captcha("login", form.captcha_answer.data):
            flash("CAPTCHA verification failed. Please try again.", "danger")
            record_audit_event("login_captcha_fail", "failure")
            db.session.commit()
            if not is_turnstile_enabled():
                generate_math_challenge("login")
            return render_template("auth/login.html", form=form, **_captcha_context("login")), 400

        email = form.email.data.strip().lower()
        user = User.query.filter(func.lower(User.email) == email).first()

        generic_error = "Invalid credentials or account locked."

        if not user or not user.is_active:
            flash(generic_error, "danger")
            record_audit_event("login_fail", "failure", user)
            db.session.commit()
            if not is_turnstile_enabled():
                generate_math_challenge("login")
            return render_template("auth/login.html", form=form, **_captcha_context("login")), 401

        if is_account_locked(user):
            flash(generic_error, "danger")
            record_audit_event("login_locked", "failure", user)
            db.session.commit()
            if not is_turnstile_enabled():
                generate_math_challenge("login")
            return render_template("auth/login.html", form=form, **_captcha_context("login")), 423

        if not user.verify_password(form.password.data):
            was_locked = record_failed_attempt(user, current_app.config)
            if was_locked:
                record_audit_event("lockout", "failure", user)
            record_audit_event("login_fail", "failure", user)
            db.session.commit()
            flash(generic_error, "danger")
            if not is_turnstile_enabled():
                generate_math_challenge("login")
            return render_template("auth/login.html", form=form, **_captcha_context("login")), 401

        clear_failed_attempts(user)
        user.last_login_at = utcnow()
        token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role.value},
        )
        record_audit_event("login_success", "success", user)
        db.session.commit()

        response = redirect(url_for("user.home"))
        set_access_cookies(response, token)
        flash("Login successful.", "success")
        return response

    if form.errors and request.method == "POST" and not is_turnstile_enabled():
        generate_math_challenge("login")

    return render_template("auth/login.html", form=form, **_captcha_context("login"))


@auth_bp.post("/logout")
@login_required
def logout():
    user = g.current_user
    record_audit_event("logout", "success", user)
    db.session.commit()

    response = redirect(url_for("auth.login"))
    unset_jwt_cookies(response)
    flash("You have been logged out.", "info")
    return response
