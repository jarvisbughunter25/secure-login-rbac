from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField
from wtforms.validators import DataRequired, Email, Length, Regexp, ValidationError

from app.auth.forms import USERNAME_PATTERN, password_strength_errors


class AdminCreateUserForm(FlaskForm):
    full_name = StringField("Full name", validators=[Length(max=80)])
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=30),
            Regexp(
                USERNAME_PATTERN,
                message="Username can contain only letters, numbers, and underscore.",
            ),
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

    def validate_password(self, field):
        failures = password_strength_errors(field.data or "")
        if failures:
            requirement_text = ", ".join(failures)
            raise ValidationError(f"Password must include {requirement_text}.")
