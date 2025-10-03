from __future__ import annotations

from typing import Dict

from flask import Blueprint, render_template

from app.models import (
    Apoio,
    Galeria,
    Parceiro,
    TextoInstitucional,
    Transparencia,
    Voluntario,
)


public_bp = Blueprint("public", __name__)


@public_bp.context_processor
def inject_public_defaults() -> Dict[str, object]:
    """Share default context data across public templates."""

    social_links = [
        {
            "name": "Instagram",
            "url": "https://www.instagram.com/associacao.doceesperanca?igsh=eHJzdDV5bzVpcnpq",
            "icon_path": "img/Instagram.jpeg",
        },
        {
            "name": "Facebook",
            "url": "https://www.facebook.com/share/1MF7W2e9g6/",
            "icon_path": "img/facee.png",
        },
        {
            "name": "WhatsApp",
            "url": "https://wa.me/qr/H35632XZAYX2F1",
            "icon_path": "img/whatsapp4.jpg",
        },
        {
            "name": "E-mail",
            "url": "mailto:dinarigo@hotmail.com",
            "icon_path": "img/email.png",
        },
    ]

    contact_info = {
        "email": "dinarigo@hotmail.com",
        "phone": "11 94855-1497",
        "address": "Rua Julio Andre Correia, 173 - Jardim Umuarama, São Paulo - SP",
        "zip_code": "04650-170",
        "office_hours": "Seg a Sex das 10h às 17h",
    }

    return {"social_links": social_links, "contact_info": contact_info}


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
    textos = _collect_textos("inicio", "missao", "principios")
    parceiros = Parceiro.query.order_by(Parceiro.nome.asc()).all()
    estatuto_pontos = [
        "Desenvolver atividades educacionais, recreativas, sociais, habitacionais, esportivas, culturais e de promoção à saúde, visando ao bem-estar integral.",
        "Organizar trabalhos para orientação e formação de mão de obra por meio de cursos educacionais e profissionais.",
        "Orientar cooperativas e oficinas profissionalizantes que fomentem inclusão e geração de renda.",
        "Pleitear junto ao poder público soluções para as necessidades do bairro e da comunidade atendida.",
        "Promover assistência a crianças, adolescentes e idosos com foco em inclusão e qualidade de vida.",
        "Oferecer cursos e palestras sobre temas como saúde, cidadania, profissionalização e prevenção às drogas.",
        "Proteger o patrimônio artístico, histórico, paisagístico e o meio ambiente.",
        "Captar recursos de entidades nacionais e internacionais para manutenção das atividades sociais.",
        "Participar de seleções públicas e privadas para financiamento de projetos sociais e educacionais.",
    ]
    return render_template(
        "public/inicio.html",
        textos=textos,
        parceiros=parceiros,
        estatuto_pontos=estatuto_pontos,
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
    textos = _collect_textos("galeria")
    itens = Galeria.query.order_by(Galeria.publicado_em.desc(), Galeria.id.desc()).all()
    return render_template(
        "public/galeria.html",
        texto_galeria=textos.get("galeria"),
        itens=itens,
        active_page="galeria",
    )


@public_bp.route("/doacao/")
def doacao() -> str:
    textos = _collect_textos("doacao")
    materiais = Galeria.query.order_by(Galeria.publicado_em.desc(), Galeria.id.desc()).all()
    documentos = (
        Transparencia.query.order_by(Transparencia.publicado_em.desc(), Transparencia.id.desc()).all()
    )
    return render_template(
        "public/doacao.html",
        texto_doacao=textos.get("doacao"),
        materiais=materiais,
        documentos=documentos,
        active_page="doacao",
    )


@public_bp.route("/projetos/")
def projetos() -> str:
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
        active_page="projetos",
    )


@public_bp.route("/contato/")
def contato() -> str:
    textos = _collect_textos("contato")
    return render_template(
        "public/contato.html",
        texto_contato=textos.get("contato"),
        active_page="contato",
    )
