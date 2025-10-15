from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

import qrcode
from qrcode.constants import ERROR_CORRECT_M

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)
from markupsafe import Markup

from app.content import CONTENT_PLACEHOLDER, INSTITUTIONAL_SECTION_MAP
from app.models import (
    Apoio,
    Banner,
    Depoimento,
    Galeria,
    Parceiro,
    TextoInstitucional,
    Transparencia,
    Voluntario,
)
from app.services.store import load_products as load_store_products
from app.routes.decorators import safe_route


public_bp = Blueprint("public", __name__)


PIX_KEY = "15657616000107"
PIX_COPY_AND_PASTE = (
    "00020126360014BR.GOV.BCB.PIX0114156576160001075204000053039865802BR5901N6001C62170513DoacaoViaSite630474C1"
)
PIX_QRCODE_FILENAME = "pix.png"


def _ensure_pix_qrcode() -> Optional[str]:
    """Generate the PIX QR code file if it doesn't exist and return its relative path."""

    static_root = Path(current_app.static_folder)
    qrcode_folder = Path(current_app.config.get("QRCODE_UPLOAD_FOLDER", static_root / "uploads" / "qrcodes"))
    qrcode_folder.mkdir(parents=True, exist_ok=True)
    target_path = qrcode_folder / PIX_QRCODE_FILENAME

    if not target_path.exists():
        qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=10, border=4)
        qr.add_data(PIX_COPY_AND_PASTE)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")
        try:
            image.save(target_path)
        except OSError:
            current_app.logger.exception("Falha ao salvar o QR Code PIX em %s", target_path)
            return None

    try:
        relative_path = target_path.relative_to(static_root)
    except ValueError:
        current_app.logger.warning(
            "O diretório de QR Codes (%s) não está dentro da pasta estática (%s)",
            qrcode_folder,
            static_root,
        )
        relative_path = target_path

    return str(relative_path).replace("\\", "/")


def _format_currency(value: float) -> str:
    formatted = f"R$ {value:,.2f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug or "produto"


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
@safe_route()
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
@safe_route()
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
@safe_route()
def galeria() -> str:
    page = request.args.get("page", default=1, type=int)
    per_page = current_app.config.get("GALLERY_ITEMS_PER_PAGE", 12)
    textos = _collect_textos("galeria", "placeholder_galeria")
    requested_slugs = ["galeria", "placeholder_galeria"]
    current_app.logger.debug(
        "View 'galeria' requested institucional slugs: %s", requested_slugs
    )
    for slug in requested_slugs:
        _log_texto_details(slug, textos.get(slug))
    itens_pagination = (
        Galeria.query.order_by(Galeria.publicado_em.desc(), Galeria.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return render_template(
        "public/galeria.html",
        texto_galeria=textos.get("galeria"),
        galeria_placeholder=textos.get("placeholder_galeria"),
        itens=itens_pagination.items,
        pagination=itens_pagination,
        active_page="galeria",
    )


@public_bp.route("/depoimentos/")
@safe_route()
def depoimentos() -> str:
    textos = _collect_textos("depoimentos")
    requested_slugs = ["depoimentos"]
    current_app.logger.debug(
        "View 'depoimentos' requested institucional slugs: %s", requested_slugs
    )
    for slug in requested_slugs:
        _log_texto_details(slug, textos.get(slug))
    depoimentos_itens = Depoimento.query.order_by(
        Depoimento.created_at.desc(), Depoimento.id.desc()
    ).all()
    return render_template(
        "public/depoimentos.html",
        texto_depoimentos=textos.get("depoimentos"),
        depoimentos=depoimentos_itens,
        active_page="depoimentos",
    )


@public_bp.route("/transparencia/")
@safe_route()
def transparencia() -> str:
    placeholders = _collect_textos("placeholder_transparencia")
    requested_slugs = ["placeholder_transparencia"]
    current_app.logger.debug(
        "View 'transparencia' requested institucional slugs: %s", requested_slugs
    )
    for slug in requested_slugs:
        _log_texto_details(slug, placeholders.get(slug))
    documentos = (
        Transparencia.query.order_by(Transparencia.publicado_em.desc(), Transparencia.id.desc()).all()
    )

    return render_template(
        "public/transparencia.html",
        documentos=documentos,
        transparencia_placeholder=placeholders.get("placeholder_transparencia"),
        active_page="transparencia",
    )


@public_bp.route("/doacao/")
@safe_route()
def doacao() -> str:
    textos = _collect_textos(
        "doacao",
        "placeholder_transparencia",
    )
    requested_slugs = [
        "doacao",
        "placeholder_transparencia",
    ]
    current_app.logger.debug(
        "View 'doacao' requested institucional slugs: %s", requested_slugs
    )
    for slug in requested_slugs:
        _log_texto_details(slug, textos.get(slug))
    documentos = (
        Transparencia.query.order_by(Transparencia.publicado_em.desc(), Transparencia.id.desc()).all()
    )
    pix_qrcode_path = _ensure_pix_qrcode()
    return render_template(
        "public/doacao.html",
        texto_doacao=textos.get("doacao"),
        documentos=documentos,
        transparencia_placeholder=textos.get("placeholder_transparencia"),
        pix_qrcode_path=pix_qrcode_path,
        pix_key=PIX_KEY,
        pix_copy_paste=PIX_COPY_AND_PASTE,
        active_page="doacao",
    )


@public_bp.route("/loja/")
@safe_route()
def loja() -> str:
    produtos_raw = sorted(
        load_store_products(),
        key=lambda item: item.get("created_at") or "",
        reverse=True,
    )
    produtos: List[Dict[str, object]] = []
    for item in produtos_raw:
        preco = max(float(item.get("preco", 0.0)), 0.0)
        frete = max(float(item.get("frete", 0.0)), 0.0)
        slug = _slugify(str(item.get("nome", "")))
        produtos.append(
            {
                "id": item.get("id"),
                "nome": item.get("nome", ""),
                "descricao": item.get("descricao", ""),
                "imagem": item.get("imagem"),
                "video": item.get("video"),
                "preco": preco,
                "frete": frete,
                "preco_formatado": _format_currency(preco),
                "frete_formatado": _format_currency(frete),
                "total": preco + frete,
                "total_formatado": _format_currency(preco + frete),
                "slug": slug,
            }
        )

    return render_template(
        "public/loja.html",
        produtos=produtos,
        pix_key=PIX_KEY,
        active_page="loja",
    )


@public_bp.route("/loja/produto/<produto_id>/")
@public_bp.route("/loja/produto/<slug>/<produto_id>/")
@safe_route()
def loja_produto(produto_id: str, slug: Optional[str] = None) -> str:
    produtos = load_store_products()
    produto = next((item for item in produtos if str(item.get("id")) == produto_id), None)
    if not produto:
        abort(404)

    preco = max(float(produto.get("preco", 0.0)), 0.0)
    frete = max(float(produto.get("frete", 0.0)), 0.0)
    slug_canonical = _slugify(str(produto.get("nome", "")))

    if slug != slug_canonical:
        return redirect(
            url_for("public.loja_produto", slug=slug_canonical, produto_id=produto_id),
            code=301,
        )

    contexto_produto = {
        "id": produto.get("id"),
        "nome": produto.get("nome", ""),
        "descricao": produto.get("descricao", ""),
        "imagem": produto.get("imagem"),
        "video": produto.get("video"),
        "preco": preco,
        "frete": frete,
        "preco_formatado": _format_currency(preco),
        "frete_formatado": _format_currency(frete),
        "total": preco + frete,
        "total_formatado": _format_currency(preco + frete),
        "slug": slug_canonical,
    }

    return render_template(
        "public/loja_produto.html",
        produto=contexto_produto,
        pix_key=PIX_KEY,
        active_page="loja",
    )


@public_bp.route("/projetos/")
@safe_route()
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
@safe_route()
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
    contact_channels: Dict[str, Dict[str, str]] = {}
    contact_description: Optional[Markup] = None
    map_embed: Optional[Markup] = None
    if texto_contato and texto_contato.conteudo:
        raw_html = texto_contato.conteudo
        cleaned_html = raw_html

        anchor_pattern = re.compile(
            r"<a\\b[^>]*href\\s*=\\s*\"(?P<href>[^\"]+)\"[^>]*>(?P<label>.*?)</a>",
            re.IGNORECASE | re.DOTALL,
        )
        for match in anchor_pattern.finditer(raw_html):
            href = match.group("href").strip()
            label_markup = Markup(match.group("label"))
            label = label_markup.striptags().strip() or href
            href_lower = href.lower()
            channel_key: Optional[str] = None

            if href_lower.startswith("tel:"):
                channel_key = "phone"
                href = f"tel:{href.split(':', 1)[1]}"
            elif "wa.me" in href_lower or "api.whatsapp.com" in href_lower:
                channel_key = "whatsapp"
                if href_lower.startswith("//"):
                    href = f"https:{href}"
                elif href_lower.startswith("wa.me"):
                    href = f"https://{href}"
                elif href_lower.startswith("http://"):
                    href = f"https://{href[7:]}"
                elif not href_lower.startswith("https://"):
                    href = f"https://wa.me/{href.split('/')[-1]}"
            elif href_lower.startswith("mailto:"):
                channel_key = "email"
                href = f"mailto:{href.split(':', 1)[1]}"

            if channel_key and channel_key not in contact_channels:
                contact_channels[channel_key] = {"href": href, "label": label}
                cleaned_html = cleaned_html.replace(match.group(0), label, 1)

        map_pattern = re.compile(
            r"(<iframe\\b[^>]*src=\"[^\"]*google\\.com/maps[^\"]*\"[^>]*></iframe>)",
            re.IGNORECASE | re.DOTALL,
        )
        map_match = map_pattern.search(cleaned_html)
        if map_match:
            iframe_html = map_match.group(1)
            if "class=" in iframe_html:
                iframe_html = re.sub(
                    r"class=\"",
                    'class="border-0 w-100 h-100 ',
                    iframe_html,
                    count=1,
                )
            else:
                iframe_html = iframe_html.replace(
                    "<iframe", '<iframe class="border-0 w-100 h-100"', 1
                )
            map_embed = Markup(iframe_html)
            cleaned_html = cleaned_html.replace(map_match.group(1), "", 1)

        cleaned_html = cleaned_html.strip()
        if cleaned_html:
            contact_description = Markup(cleaned_html)

    if "email" not in contact_channels and contact_email:
        contact_channels["email"] = {
            "href": f"mailto:{contact_email}",
            "label": contact_email,
        }
    return render_template(
        "public/contato.html",
        texto_contato=texto_contato,
        contact_email=contact_email,
        contact_channels=contact_channels,
        contact_description=contact_description,
        map_embed=map_embed,
        active_page="contato",
    )
