from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo


class NewPasswordForm(FlaskForm):
    current_password = PasswordField('current_password', [DataRequired()])
    new_password = PasswordField('new_password', [DataRequired()])
    confirm_password = PasswordField(
        'confirm_password',
        [
            DataRequired(),
            EqualTo('new_password', 'O campo deve ser igual a nova senha.')
        ]
    )


class ShopeeForm(FlaskForm):
    app_id = StringField('app_id', [DataRequired()])
    secret = StringField('secret', [DataRequired()])


class ThreadsForm(FlaskForm):
    code = StringField('code', [DataRequired()])
