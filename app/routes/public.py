from __future__ import annotations

from typing import Dict, Optional

from flask import Blueprint, render_template

from app.content import CONTENT_PLACEHOLDER, INSTITUTIONAL_SECTION_MAP
from app.models import Apoio, Banner, Galeria, Parceiro, TextoInstitucional, Transparencia, Voluntario


public_bp = Blueprint("public", __name__)


@public_bp.context_processor
def inject_public_defaults() -> Dict[str, object]:
    """Share default context data across public templates."""

    contato_texto = TextoInstitucional.query.filter_by(slug="contato").first()
    inicio_texto = TextoInstitucional.query.filter_by(slug="inicio").first()

    site_identity = CONTENT_PLACEHOLDER
    if inicio_texto and inicio_texto.titulo:
        site_identity = inicio_texto.titulo

    return {
        "footer_contact": contato_texto,
        "site_identity": site_identity,
        "content_placeholder": CONTENT_PLACEHOLDER,
        "institutional_sections": INSTITUTIONAL_SECTION_MAP,
    }


def _collect_textos(*slugs: str) -> Dict[str, TextoInstitucional]:
    """Return a mapping of slug to TextoInstitucional for the provided slugs."""
    unique_slugs = {slug for slug in slugs if slug}
    if not unique_slugs:
        return {}

    textos = (
        TextoInstitucional.query.filter(TextoInstitucional.slug.in_(unique_slugs)).all()
    )
    return {texto.slug: texto for texto in textos}


@public_bp.route("/")
def index() -> str:
    textos = _collect_textos(
        "inicio",
        "missao",
        "principios",
        "placeholder_parceiros",
    )
    parceiros = Parceiro.query.order_by(Parceiro.nome.asc()).all()
    banners = Banner.query.order_by(Banner.ordem.asc(), Banner.created_at.desc()).all()
    return render_template(
        "public/inicio.html",
        textos=textos,
        parceiros=parceiros,
        banners=banners,
        parceiros_placeholder=textos.get("placeholder_parceiros"),
        active_page="inicio",
    )


@public_bp.route("/sobre/")
def sobre() -> str:
    textos = _collect_textos("sobre", "missao")
    return render_template(
        "public/sobre.html",
        texto_sobre=textos.get("sobre"),
        texto_missao=textos.get("missao"),
        active_page="sobre",
    )


@public_bp.route("/galeria/")
def galeria() -> str:
    textos = _collect_textos("galeria", "placeholder_galeria")
    itens = Galeria.query.order_by(Galeria.publicado_em.desc(), Galeria.id.desc()).all()
    return render_template(
        "public/galeria.html",
        texto_galeria=textos.get("galeria"),
        galeria_placeholder=textos.get("placeholder_galeria"),
        itens=itens,
        active_page="galeria",
    )


@public_bp.route("/doacao/")
def doacao() -> str:
    textos = _collect_textos(
        "doacao",
        "placeholder_produtos",
        "placeholder_transparencia",
    )
    materiais = Galeria.query.order_by(Galeria.publicado_em.desc(), Galeria.id.desc()).all()
    documentos = (
        Transparencia.query.order_by(Transparencia.publicado_em.desc(), Transparencia.id.desc()).all()
    )
    return render_template(
        "public/doacao.html",
        texto_doacao=textos.get("doacao"),
        materiais=materiais,
        documentos=documentos,
        produtos_placeholder=textos.get("placeholder_produtos"),
        transparencia_placeholder=textos.get("placeholder_transparencia"),
        active_page="doacao",
    )


@public_bp.route("/projetos/")
def projetos() -> str:
    placeholders = _collect_textos(
        "placeholder_parceiros",
        "placeholder_apoios",
        "placeholder_voluntarios",
        "placeholder_transparencia",
    )
    parceiros = Parceiro.query.order_by(Parceiro.nome.asc()).all()
    apoios = Apoio.query.order_by(Apoio.titulo.asc()).all()
    voluntarios = Voluntario.query.order_by(Voluntario.nome.asc()).all()
    documentos = (
        Transparencia.query.order_by(Transparencia.publicado_em.desc(), Transparencia.id.desc()).all()
    )

    return render_template(
        "public/projetos.html",
        parceiros=parceiros,
        apoios=apoios,
        voluntarios=voluntarios,
        documentos=documentos,
        parceiros_placeholder=placeholders.get("placeholder_parceiros"),
        apoios_placeholder=placeholders.get("placeholder_apoios"),
        voluntarios_placeholder=placeholders.get("placeholder_voluntarios"),
        transparencia_placeholder=placeholders.get("placeholder_transparencia"),
        active_page="projetos",
    )


@public_bp.route("/contato/")
def contato() -> str:
    textos = _collect_textos("contato")
    texto_contato = textos.get("contato")
    contact_email: Optional[str] = None
    if texto_contato and texto_contato.resumo:
        contact_email = texto_contato.resumo.strip()
    return render_template(
        "public/contato.html",
        texto_contato=texto_contato,
        contact_email=contact_email,
        active_page="contato",
    )
