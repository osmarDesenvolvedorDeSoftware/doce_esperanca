from __future__ import annotations

from typing import Dict, Optional

from flask import Blueprint, current_app, render_template

from app.content import CONTENT_PLACEHOLDER, INSTITUTIONAL_SECTION_MAP
from app.models import Apoio, Banner, Galeria, Parceiro, TextoInstitucional, Transparencia, Voluntario


public_bp = Blueprint("public", __name__)


@public_bp.context_processor
def inject_public_defaults() -> Dict[str, object]:
    """Share default context data across public templates."""

    contato_texto = TextoInstitucional.query.filter_by(slug="contato").first()
    inicio_texto = TextoInstitucional.query.filter_by(slug="inicio").first()

    requested_slugs = ("contato", "inicio")
    current_app.logger.debug(
        "Context processor requested institucional slugs: %s", requested_slugs
    )
    for slug, texto in {"contato": contato_texto, "inicio": inicio_texto}.items():
        _log_texto_details(slug, texto)

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

    current_app.logger.debug(
        "Fetching TextoInstitucional entries for slugs: %s", sorted(unique_slugs)
    )

    textos = (
        TextoInstitucional.query.filter(TextoInstitucional.slug.in_(unique_slugs)).all()
    )
    texto_map = {texto.slug: texto for texto in textos}

    for slug in unique_slugs:
        if slug not in texto_map:
            current_app.logger.debug(
                "No TextoInstitucional found for slug '%s' during collection", slug
            )

    return texto_map


def _log_texto_details(slug: str, texto: Optional[TextoInstitucional]) -> None:
    """Emit debug information about the resolved TextoInstitucional."""

    if texto is None:
        current_app.logger.debug("No TextoInstitucional found for slug '%s'", slug)
        return

    snippet_source = texto.conteudo or texto.resumo or ""
    snippet = snippet_source.strip().replace("\n", " ")[:200]
    current_app.logger.debug(
        "Slug '%s' resolved to TextoInstitucional id=%s snippet='%s'",
        slug,
        texto.id,
        snippet,
    )


@public_bp.route("/")
def index() -> str:
    textos = _collect_textos(
        "inicio",
        "missao",
        "principios",
        "placeholder_parceiros",
    )
    requested_slugs = [
        "inicio",
        "missao",
        "principios",
        "placeholder_parceiros",
    ]
    current_app.logger.debug(
        "View 'index' requested institucional slugs: %s", requested_slugs
    )
    for slug in requested_slugs:
        _log_texto_details(slug, textos.get(slug))
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
    requested_slugs = ["sobre", "missao"]
    current_app.logger.debug(
        "View 'sobre' requested institucional slugs: %s", requested_slugs
    )
    for slug in requested_slugs:
        _log_texto_details(slug, textos.get(slug))
    return render_template(
        "public/sobre.html",
        texto_sobre=textos.get("sobre"),
        texto_missao=textos.get("missao"),
        active_page="sobre",
    )


@public_bp.route("/galeria/")
def galeria() -> str:
    textos = _collect_textos("galeria", "placeholder_galeria")
    requested_slugs = ["galeria", "placeholder_galeria"]
    current_app.logger.debug(
        "View 'galeria' requested institucional slugs: %s", requested_slugs
    )
    for slug in requested_slugs:
        _log_texto_details(slug, textos.get(slug))
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
    requested_slugs = [
        "doacao",
        "placeholder_produtos",
        "placeholder_transparencia",
    ]
    current_app.logger.debug(
        "View 'doacao' requested institucional slugs: %s", requested_slugs
    )
    for slug in requested_slugs:
        _log_texto_details(slug, textos.get(slug))
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
    requested_slugs = [
        "placeholder_parceiros",
        "placeholder_apoios",
        "placeholder_voluntarios",
        "placeholder_transparencia",
    ]
    current_app.logger.debug(
        "View 'projetos' requested institucional slugs: %s", requested_slugs
    )
    for slug in requested_slugs:
        _log_texto_details(slug, placeholders.get(slug))
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
    requested_slugs = ["contato"]
    current_app.logger.debug(
        "View 'contato' requested institucional slugs: %s", requested_slugs
    )
    for slug in requested_slugs:
        _log_texto_details(slug, textos.get(slug))
    contact_email: Optional[str] = None
    if texto_contato and texto_contato.resumo:
        contact_email = texto_contato.resumo.strip()
    return render_template(
        "public/contato.html",
        texto_contato=texto_contato,
        contact_email=contact_email,
        active_page="contato",
    )
