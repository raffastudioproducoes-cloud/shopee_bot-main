from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, IntegerField, SelectField, FieldList, \
    FormField, ValidationError, DateTimeLocalField, TimeField
from wtforms.validators import DataRequired, Optional, NumberRange, Length

from shopee_bot.database.schedulers import NETWORK_FUNC_MAP


class Media(FlaskForm):
    id = IntegerField("id", [Optional()])
    file_name = StringField("file_name", [DataRequired(), Length(max=255)])
    file_path = StringField("file_path", [DataRequired(), Length(max=2000)])
    size = IntegerField("size", [DataRequired()])
    type = SelectField(
        "type",
        choices=[('IMAGE', 'IMAGE'), ('VIDEO', 'VIDEO')],
        validators=[DataRequired()]
    )


class Post(FlaskForm):
    id = IntegerField("id", [Optional()])
    text = StringField("text", [Optional(), Length(max=5000)])
    medias = FieldList(FormField(Media))

    def validate(self, extra_validators=None):
        rv = super(Post, self).validate(extra_validators)
        if not rv:
            return False

        # validação condicional
        if self.text.data == "" and self.medias.data == []:
            self.text.errors.append(
                "Texto é obrigatório"
            )
            return False


class Job(FlaskForm):
    id = StringField("id", [Optional()])
    func = StringField('func', validators=[DataRequired()])
    trigger = SelectField(
        "trigger",
        choices=[('cron', 'Cron'), ('date', 'Date')],
        validators=[DataRequired()]
    )
    time = TimeField('time', format="%H:%M")
    day_of_week = IntegerField(
        'day_of_week',
        validators=[Optional(), NumberRange(min=0, max=6)]
    )
    start_date = DateTimeLocalField('start_date', validators=[Optional()])
    run_date = DateTimeLocalField('run_date', validators=[Optional()])

    def validate(self, extra_validators=None):
        rv = super(Job, self).validate(extra_validators)
        if not rv:
            return False

        # Validação condicional com base no trigger
        if self.trigger.data == 'cron':
            if self.time.data is None:
                self.time.errors.append(
                    'Hora é obrigatório para trigger "cron".'
                )
                return False
            if self.day_of_week.data is None:
                self.day_of_week.errors.append(
                    'Dia da semana é obrigatório para trigger "cron".'
                )
                return False
        elif self.trigger.data == 'date':
            if self.run_date.data is None:
                self.run_date.errors.append(
                    'Data de execução é obrigatória para trigger "date".'
                )
                return False

        return True


class PostForm(FlaskForm):
    product_ids = FieldList(
        IntegerField('product_ids', [DataRequired()]), min_entries=1
    )
    posts = FieldList(FormField(Post), min_entries=1)
    job = FormField(Job)
    network = SelectField(
        "network",
        choices=[(key, key) for key in NETWORK_FUNC_MAP],
        default="threads",
        validators=[Optional()]
    )
    files = FieldList(
        FieldList(FileField("files", [Optional()]))
    )

    def validate_files(self, field):
        if not field.data:
            return

        allowed_exts = {'.webp', '.jpg', '.jpeg', '.png', '.gif', '.mp4'}
        for arr_files in field.data:
            for file in arr_files:
                if not file:
                    continue

                if not any(
                    file.filename.lower().endswith(ext) for ext in allowed_exts
                ):
                    raise ValidationError(
                        "Formato de arquivo inválido: {0}. Permitidos: {1}".format(
                            file.filename, allowed_exts)
                    )
