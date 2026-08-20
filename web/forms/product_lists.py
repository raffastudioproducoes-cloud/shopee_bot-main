from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FieldList
from wtforms.validators import DataRequired, Optional


class ProductListForm(FlaskForm):
    name = StringField('name', [DataRequired()])
    list = FieldList(IntegerField('list', [Optional()]))
