import re

from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField
from wtforms.validators import DataRequired, Email, Length, Regexp, ValidationError

USERNAME_PATTERN = r"^[A-Za-z0-9_]{3,30}$"


PASSWORD_REQUIREMENTS = [
    (re.compile(r".{10,}"), "at least 10 characters"),
    (re.compile(r"[A-Z]"), "an uppercase letter"),
    (re.compile(r"[a-z]"), "a lowercase letter"),
    (re.compile(r"\d"), "a number"),
    (re.compile(r"[^A-Za-z0-9]"), "a special character"),
]


def password_strength_errors(password: str) -> list[str]:
    failures = [message for regex, message in PASSWORD_REQUIREMENTS if not regex.search(password)]
    return failures


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=30),
            Regexp(USERNAME_PATTERN, message="Username can contain only letters, numbers, and underscore."),
        ],
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired()])
    role = SelectField(
        "Role",
        choices=[("user", "User"), ("admin", "Admin")],
        validators=[DataRequired()],
        default="user",
    )
    captcha_answer = StringField("Captcha")

    def validate_password(self, field):
        failures = password_strength_errors(field.data or "")
        if failures:
            requirement_text = ", ".join(failures)
            raise ValidationError(f"Password must include {requirement_text}.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired()])
    captcha_answer = StringField("Captcha")
