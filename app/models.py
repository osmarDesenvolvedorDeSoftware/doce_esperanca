from __future__ import annotations

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class TextoInstitucional(db.Model, TimestampMixin):
    __tablename__ = "textos"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    resumo = db.Column(db.String(512))
    conteudo = db.Column(db.Text, nullable=False)
    imagem_path = db.Column(db.String(512))

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<TextoInstitucional {self.slug!r}>"


class Parceiro(db.Model, TimestampMixin):
    __tablename__ = "parceiros"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    descricao = db.Column(db.Text)
    website = db.Column(db.String(255))
    logo_path = db.Column(db.String(512))

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Parceiro {self.slug!r}>"


class Voluntario(db.Model, TimestampMixin):
    __tablename__ = "voluntarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    area = db.Column(db.String(255))
    disponibilidade = db.Column(db.String(255))
    descricao = db.Column(db.Text)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Voluntario {self.nome!r}>"


class Galeria(db.Model, TimestampMixin):
    __tablename__ = "galeria"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    descricao = db.Column(db.Text)
    imagem_path = db.Column(db.String(512), nullable=False)
    publicado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Galeria {self.slug!r}>"


class Transparencia(db.Model, TimestampMixin):
    __tablename__ = "transparencia"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    descricao = db.Column(db.Text)
    arquivo_path = db.Column(db.String(512), nullable=False)
    publicado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Transparencia {self.slug!r}>"


class Apoio(db.Model, TimestampMixin):
    __tablename__ = "apoios"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    imagem_path = db.Column(db.String(255))

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Apoio {self.titulo!r}>"


class Banner(db.Model, TimestampMixin):
    __tablename__ = "banners"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.String(512))
    ordem = db.Column(db.Integer, nullable=False, default=0)
    imagem_path = db.Column(db.String(512), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Banner {self.titulo!r}>"


class User(db.Model, UserMixin, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User {self.username!r}>"

    @property
    def password(self) -> None:
        raise AttributeError("password is write-only")

    @password.setter
    def password(self, value: str) -> None:
        self.password_hash = generate_password_hash(value)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_id(self) -> str:
        return str(self.id)

    @classmethod
    def create(cls, username: str, email: str, password: str, **kwargs: object) -> "User":
        user = cls(username=username, email=email, **kwargs)
        user.set_password(password)
        return user


class Depoimento(db.Model, TimestampMixin):
    __tablename__ = "depoimentos"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text)
    video = db.Column(db.String(255), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Depoimento {self.titulo!r}>"
