from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField
from wtforms.validators import DataRequired, Optional, Length, URL


class ProductForm(FlaskForm):
    product_id = IntegerField('product_id', [DataRequired()])
    name = StringField('name', [DataRequired(), Length(max=500)])
    original_link = StringField('original_link', [DataRequired(), Length(max=2000), URL()])
    commission_link = StringField('commission_link', [DataRequired(), Length(max=2000), URL()])
    commission = StringField('commission', [Optional(), Length(max=50)])
    image = StringField('image', [DataRequired(), Length(max=2000)])
    price_min = StringField('price_min', [DataRequired(), Length(max=50)])
    price_max = StringField('price_max', [Optional(), Length(max=50)])
