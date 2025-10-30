from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import FrozenSet, Iterable, Optional

from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from werkzeug.utils import secure_filename
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    IntegerField,
    PasswordField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional as OptionalValidator,
    URL,
    ValidationError,
)

ALLOWED_IMAGE_EXTENSIONS: Iterable[str] = ("jpg", "jpeg", "png")
ALLOWED_VIDEO_EXTENSIONS: Iterable[str] = ("mp4", "mov", "avi", "mkv", "webm")
DISALLOWED_UPLOAD_EXTENSIONS: FrozenSet[str] = frozenset(
    {
        "exe",
        "bat",
        "cmd",
        "com",
        "cpl",
        "js",
        "jse",
        "msi",
        "msp",
        "msc",
        "pif",
        "ps1",
        "reg",
        "scr",
        "sh",
        "vb",
        "vbe",
        "vbs",
    }
)


class FileSize:
    """WTForms validator to ensure file size does not exceed a limit."""

    def __init__(self, max_size: Optional[int] = None) -> None:
        self.max_size = max_size

    def __call__(self, form: FlaskForm, field: FileField) -> None:  # type: ignore[override]
        if not field.data:
            return

        data = field.data
        max_size = self.max_size
        if max_size is None:
            max_size = int(current_app.config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

        if hasattr(data, "seek") and hasattr(data, "tell"):
            current_position = data.tell()
            data.seek(0, 2)
            size = data.tell()
            data.seek(current_position)
        else:
            data.stream.seek(0, 2)
            size = data.stream.tell()
            data.stream.seek(0)

        if size > max_size:
            raise ValidationError(
                f"O arquivo excede o tamanho máximo permitido de {max_size // (1024 * 1024)} MB."
            )


class LoginForm(FlaskForm):
    username = StringField("Usuário", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Senha", validators=[DataRequired(), Length(min=6, max=255)])
    remember = BooleanField("Lembrar de mim")
    submit = SubmitField("Entrar")


class TextoInstitucionalForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired(), Length(max=255)])
    slug = StringField("Slug", validators=[DataRequired(), Length(max=255)])
    resumo = StringField("Resumo", validators=[OptionalValidator(), Length(max=512)])
    conteudo = TextAreaField("Conteúdo", validators=[DataRequired()])
    support_text = StringField(
        "Texto de apoio",
        validators=[OptionalValidator(), Length(max=255)],
    )
    address = TextAreaField(
        "Endereço",
        validators=[OptionalValidator(), Length(max=512)],
    )
    phone = StringField(
        "Telefone",
        validators=[OptionalValidator(), Length(max=64)],
    )
    facebook = StringField(
        "Facebook",
        validators=[OptionalValidator(), URL(), Length(max=255)],
    )
    instagram = StringField(
        "Instagram",
        validators=[OptionalValidator(), URL(), Length(max=255)],
    )
    youtube = StringField(
        "YouTube",
        validators=[OptionalValidator(), URL(), Length(max=255)],
    )
    whatsapp = StringField(
        "WhatsApp",
        validators=[OptionalValidator(), URL(), Length(max=255)],
    )
    imagem = FileField(
        "Imagem",
        validators=[
            OptionalValidator(),
            FileAllowed(ALLOWED_IMAGE_EXTENSIONS, "Somente imagens são permitidas."),
            FileSize(),
        ],
    )
    submit = SubmitField("Salvar")


class ParceiroForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=255)])
    slug = StringField("Slug", validators=[DataRequired(), Length(max=255)])
    descricao = TextAreaField("Descrição", validators=[OptionalValidator()])
    website = StringField("Website", validators=[OptionalValidator(), URL(), Length(max=255)])
    logo = FileField(
        "Logo",
        validators=[
            OptionalValidator(),
            FileAllowed(ALLOWED_IMAGE_EXTENSIONS, "Somente imagens são permitidas."),
            FileSize(),
        ],
    )
    submit = SubmitField("Salvar")


class VoluntarioForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=255)])
    area = StringField("Área", validators=[DataRequired(), Length(max=255)])
    disponibilidade = StringField("Disponibilidade", validators=[OptionalValidator(), Length(max=255)])
    descricao = TextAreaField("Descrição", validators=[OptionalValidator()])
    foto = FileField(
        "Foto",
        validators=[
            OptionalValidator(),
            FileAllowed(ALLOWED_IMAGE_EXTENSIONS, "Somente imagens são permitidas."),
            FileSize(),
        ],
    )
    submit = SubmitField("Salvar")


class GaleriaForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired(), Length(max=255)])
    slug = StringField("Slug", validators=[DataRequired(), Length(max=255)])
    descricao = TextAreaField("Descrição", validators=[OptionalValidator()])
    publicado_em = DateField(
        "Publicado em",
        validators=[OptionalValidator()],
        default=datetime.utcnow,
        format="%Y-%m-%d",
    )
    imagem = FileField(
        "Imagem",
        validators=[
            OptionalValidator(),
            FileAllowed(ALLOWED_IMAGE_EXTENSIONS, "Somente imagens são permitidas."),
            FileSize(),
        ],
    )
    submit = SubmitField("Salvar")


class TransparenciaForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired(), Length(max=255)])
    slug = StringField("Slug", validators=[DataRequired(), Length(max=255)])
    descricao = TextAreaField("Descrição", validators=[OptionalValidator()])
    publicado_em = DateField(
        "Publicado em",
        validators=[OptionalValidator()],
        default=datetime.utcnow,
        format="%Y-%m-%d",
    )
    arquivo = FileField(
        "Arquivo",
        validators=[
            OptionalValidator(),
            FileSize(),
        ],
    )
    submit = SubmitField("Salvar")

    def validate_arquivo(self, field: FileField) -> None:  # type: ignore[override]
        data = field.data
        if not data or not getattr(data, "filename", "").strip():
            return

        filename = secure_filename(data.filename or "")
        if not filename:
            raise ValidationError("Nome de arquivo inválido.")

        suffixes = [suffix.lstrip(".").lower() for suffix in Path(filename).suffixes]
        if not suffixes:
            raise ValidationError("Arquivo deve possuir uma extensão válida.")

        if any(suffix in DISALLOWED_UPLOAD_EXTENSIONS for suffix in suffixes):
            raise ValidationError("Esse tipo de arquivo não é permitido para upload.")


class ApoioForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired(), Length(max=255)])
    descricao = TextAreaField("Descrição", validators=[DataRequired()])
    imagem = FileField(
        "Imagem",
        validators=[
            OptionalValidator(),
            FileAllowed(ALLOWED_IMAGE_EXTENSIONS, "Somente imagens são permitidas."),
            FileSize(),
        ],
    )
    submit = SubmitField("Salvar")


class BannerForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired(), Length(max=255)])
    descricao = TextAreaField(
        "Descrição", validators=[OptionalValidator(), Length(max=512)]
    )
    ordem = IntegerField("Ordem", validators=[OptionalValidator()], default=0)
    imagem = FileField(
        "Imagem",
        validators=[
            OptionalValidator(),
            FileAllowed(ALLOWED_IMAGE_EXTENSIONS, "Somente imagens são permitidas."),
            FileSize(),
        ],
    )
    submit = SubmitField("Salvar")


class DepoimentoForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired(), Length(max=150)])
    descricao = TextAreaField("Descrição", validators=[OptionalValidator()])
    video = FileField(
        "Vídeo",
        validators=[
            OptionalValidator(),
            FileAllowed(ALLOWED_VIDEO_EXTENSIONS, "Somente vídeos são permitidos."),
            FileSize(),
        ],
    )
    submit = SubmitField("Salvar")


def _strip_filter(value: Optional[str]) -> Optional[str]:
    if isinstance(value, str):
        return value.strip()
    return value


def _decimal_filter(value: Optional[str]) -> Optional[str]:
    if isinstance(value, str):
        cleaned = value.strip().replace(" ", "")
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "")
        cleaned = cleaned.replace(",", ".")
        return cleaned
    return value


class ProdutoLojaForm(FlaskForm):
    nome = StringField(
        "Nome",
        validators=[DataRequired(), Length(max=255)],
        filters=[_strip_filter],
    )
    descricao = TextAreaField(
        "Descrição",
        validators=[DataRequired()],
        filters=[_strip_filter],
    )
    preco = DecimalField(
        "Preço",
        validators=[DataRequired(), NumberRange(min=0)],
        places=2,
        rounding=None,
        filters=[_decimal_filter],
    )
    frete = DecimalField(
        "Frete",
        validators=[DataRequired(), NumberRange(min=0)],
        places=2,
        rounding=None,
        filters=[_decimal_filter],
    )
    imagem = FileField(
        "Imagem",
        validators=[
            OptionalValidator(),
            FileSize(),
        ],
    )
    video = FileField(
        "Vídeo",
        validators=[
            OptionalValidator(),
            FileAllowed(ALLOWED_VIDEO_EXTENSIONS, "Somente vídeos são permitidos."),
            FileSize(),
        ],
    )
    submit = SubmitField("Salvar produto")
