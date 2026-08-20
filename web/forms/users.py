from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Optional
from enum import Enum


class UserAccess(Enum):
    USER = 'USER'
    ADMIN = 'ADMIN'


def user_access_coerce(data):
    if isinstance(data, UserAccess):
        return data.value
    return data


class UserAddForm(FlaskForm):
    username = StringField('username', [DataRequired()])
    password = PasswordField('password', [DataRequired()])
    access = SelectField(
        'access',
        choices=[(a.value, a.value) for a in UserAccess],
        coerce=user_access_coerce,
        validators=[DataRequired()]
    )


class UserEditForm(UserAddForm):
    password = PasswordField('password', [Optional()])
