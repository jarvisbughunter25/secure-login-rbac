from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import PasswordField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError

from app.auth.forms import USERNAME_PATTERN, password_strength_errors


class ProfileDetailsForm(FlaskForm):
    full_name = StringField("Full name", validators=[Optional(), Length(min=2, max=80)])
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
    bio = TextAreaField("Bio", validators=[Optional(), Length(max=280)])


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords do not match.")],
    )

    def validate_new_password(self, field):
        failures = password_strength_errors(field.data or "")
        if failures:
            requirement_text = ", ".join(failures)
            raise ValidationError(f"Password must include {requirement_text}.")


class AvatarUploadForm(FlaskForm):
    avatar = FileField(
        "Profile photo",
        validators=[
            FileRequired(message="Please choose an image file."),
            FileAllowed(["png", "jpg", "jpeg", "webp"], "Allowed types: png, jpg, jpeg, webp."),
        ],
    )
