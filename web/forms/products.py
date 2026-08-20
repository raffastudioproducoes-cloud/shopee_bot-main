from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField
from wtforms.validators import DataRequired, Optional


class ProductForm(FlaskForm):
    product_id = IntegerField('product_id', [DataRequired()])
    name = StringField('name', [DataRequired()])
    original_link = StringField('original_link', [DataRequired()])
    commission_link = StringField('commission_link', [DataRequired()])
    commission = StringField('commission', [Optional()])
    image = StringField('image', [DataRequired()])
    price_min = StringField('price_min', [DataRequired()])
    price_max = StringField('price_max', [Optional()])
