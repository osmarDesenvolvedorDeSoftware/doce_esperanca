from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

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
from markupsafe import Markup, escape

from app.content import (
    CONTENT_PLACEHOLDER,
    INSTITUTIONAL_SECTION_MAP,
    footer_contact_with_defaults,
)
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

SOCIAL_PLATFORMS = {
    "facebook": ("bi bi-facebook", "Facebook"),
    "instagram": ("bi bi-instagram", "Instagram"),
    "youtube": ("bi bi-youtube", "YouTube"),
}


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


def _normalize_phone_link(phone: str) -> Optional[str]:
    if not phone:
        return None

    stripped = phone.strip()
    digits_only = re.sub(r"[^0-9]", "", stripped)
    if not digits_only:
        return None

    if stripped.startswith("+"):
        return f"+{digits_only}"
    return digits_only


def _normalize_external_url(url: str) -> Optional[str]:
    if not url:
        return None

    stripped = url.strip()
    if not stripped:
        return None

    if stripped.startswith("//"):
        return f"https:{stripped}"

    if re.match(r"^https?://", stripped, re.IGNORECASE):
        return stripped

    return f"https://{stripped}"


def _normalize_whatsapp_link(raw_value: str) -> Optional[str]:
    if not raw_value:
        return None

    stripped = raw_value.strip()
    if not stripped:
        return None

    lower_value = stripped.lower()

    if lower_value.startswith("http://"):
        return f"https://{stripped[7:]}"

    if lower_value.startswith("https://"):
        return stripped

    if lower_value.startswith("//"):
        return f"https:{stripped}"

    if lower_value.startswith("wa.me/"):
        return f"https://{stripped}"

    if lower_value.startswith("api.whatsapp.com"):
        return f"https://{stripped}" if not lower_value.startswith("https://") else stripped

    digits_only = re.sub(r"[^0-9]", "", stripped)
    if digits_only:
        return f"https://api.whatsapp.com/send?phone={digits_only}"

    return None


def _prepare_map_embed(map_value: Any) -> Optional[Markup]:
    if not map_value:
        return None

    if isinstance(map_value, dict):
        for key in ("iframe", "html", "src", "url"):
            nested_value = map_value.get(key)
            if nested_value:
                map_value = nested_value
                break
        else:
            return None

    map_str = str(map_value).strip()
    if not map_str:
        return None

    iframe_pattern = re.compile(
        r"<iframe\b[^>]*>.*?</iframe>", re.IGNORECASE | re.DOTALL
    )
    iframe_match = iframe_pattern.search(map_str)

    if iframe_match:
        iframe_html = iframe_match.group(0)
    elif map_str.lower().startswith("<iframe"):
        iframe_html = map_str
    else:
        iframe_src = escape(map_str)
        iframe_html = (
            f'<iframe src="{iframe_src}" '
            "loading=\"lazy\" allowfullscreen=\"\" "
            "referrerpolicy=\"no-referrer-when-downgrade\"></iframe>"
        )

    if "class=" in iframe_html:
        iframe_html = re.sub(
            r'class=\"',
            'class="border-0 w-100 h-100 ',
            iframe_html,
            count=1,
        )
    else:
        iframe_html = iframe_html.replace(
            "<iframe", '<iframe class="border-0 w-100 h-100"', 1
        )

    style_pattern = re.compile(r'style\s*=\s*"([^"]*)"', re.IGNORECASE)

    def _inject_min_height(match: re.Match) -> str:
        existing = match.group(1).strip()
        if re.search(r"min-height\s*:", existing, re.IGNORECASE):
            return f'style="{existing}"'

        prefix = "min-height:400px;"
        if existing:
            if not existing.endswith(";"):
                existing = f"{existing};"
            new_value = f"{prefix} {existing.strip()}"
        else:
            new_value = prefix
        return f'style="{new_value}"'

    if style_pattern.search(iframe_html):
        iframe_html = style_pattern.sub(_inject_min_height, iframe_html, count=1)
    else:
        iframe_html = iframe_html.replace(
            "<iframe", '<iframe style="min-height:400px"', 1
        )

    return Markup(iframe_html)


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

    footer_contact_data = footer_contact_with_defaults(
        contato_texto.conteudo if contato_texto else None,
        logger=current_app.logger,
    )
    footer_contact_phone_href = _normalize_phone_link(
        footer_contact_data.get("phone", "")
    )

    site_identity = CONTENT_PLACEHOLDER
    if inicio_texto and inicio_texto.titulo:
        site_identity = inicio_texto.titulo

    return {
        "footer_contact": contato_texto,
        "footer_contact_data": footer_contact_data,
        "footer_contact_phone_href": footer_contact_phone_href,
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
    galerias = list(itens_pagination.items)
    has_items = len(galerias) > 0

    texto_galeria = textos.get("galeria")
    header_title = (
        texto_galeria.titulo
        if texto_galeria and texto_galeria.titulo
        else ("Galeria" if has_items else CONTENT_PLACEHOLDER)
    )
    header_intro_html = (
        texto_galeria.conteudo
        if texto_galeria and texto_galeria.conteudo
        else (None if has_items else CONTENT_PLACEHOLDER)
    )
    return render_template(
        "public/galeria.html",
        texto_galeria=texto_galeria,
        galeria_placeholder=textos.get("placeholder_galeria"),
        galerias=galerias,
        itens=galerias,
        pagination=itens_pagination,
        has_items=has_items,
        header_title=header_title,
        header_intro_html=header_intro_html,
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
    documentos = (
        Transparencia.query.order_by(Transparencia.publicado_em.desc(), Transparencia.id.desc()).all()
    )
    pix_qrcode_path = _ensure_pix_qrcode()
    return render_template(
        "public/doacao.html",
        documentos=documentos,
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
    contact_address_lines: List[str] = []
    contact_social_links: List[Dict[str, str]] = []
    contact_whatsapp_display: Optional[str] = None
    contact_content_is_json = False
    contact_info: Dict[str, Any] = {}

    if texto_contato and texto_contato.conteudo:
        raw_content = texto_contato.conteudo
        stripped_content = raw_content.strip()
        parsed_contact_data: Optional[Dict[str, Any]] = None

        if stripped_content:
            try:
                parsed = json.loads(stripped_content)
            except ValueError:
                parsed = None

            if isinstance(parsed, dict):
                parsed_contact_data = parsed

        if parsed_contact_data is not None:
            contact_content_is_json = True
            contact_info = parsed_contact_data

            address_value = str(parsed_contact_data.get("address") or "").strip()
            if address_value:
                contact_address_lines = [
                    line.strip()
                    for line in re.split(r"\r?\n", address_value)
                    if line.strip()
                ]

            phone_value = str(parsed_contact_data.get("phone") or "").strip()
            if phone_value and "phone" not in contact_channels:
                normalized_phone = _normalize_phone_link(phone_value)
                href_phone = normalized_phone or phone_value
                contact_channels["phone"] = {
                    "href": f"tel:{href_phone}",
                    "label": phone_value,
                }

            email_value = str(parsed_contact_data.get("email") or "").strip()
            if email_value:
                contact_email = contact_email or email_value
                contact_channels.setdefault(
                    "email",
                    {
                        "href": f"mailto:{email_value}",
                        "label": email_value,
                    },
                )

            whatsapp_value = parsed_contact_data.get("whatsapp")
            whatsapp_href = (
                _normalize_whatsapp_link(str(whatsapp_value))
                if whatsapp_value
                else None
            )
            if whatsapp_href:
                whatsapp_label = (
                    str(parsed_contact_data.get("whatsapp_label") or "").strip()
                    or "Enviar mensagem"
                )
                contact_channels["whatsapp"] = {
                    "href": whatsapp_href,
                    "label": whatsapp_label,
                }

            whatsapp_display_value = (
                parsed_contact_data.get("whatsapp_display")
                or parsed_contact_data.get("whatsapp_number")
            )
            if whatsapp_display_value:
                contact_whatsapp_display = str(whatsapp_display_value).strip() or None

            social_links: List[Dict[str, str]] = []
            for platform, (icon, title) in SOCIAL_PLATFORMS.items():
                link_value = parsed_contact_data.get(platform)
                normalized_link = (
                    _normalize_external_url(str(link_value)) if link_value else None
                )
                if normalized_link:
                    social_links.append(
                        {
                            "platform": platform,
                            "icon": icon,
                            "title": title,
                            "href": normalized_link,
                        }
                    )
            contact_social_links = social_links

            description_value = (
                parsed_contact_data.get("description")
                or parsed_contact_data.get("intro")
                or parsed_contact_data.get("about")
            )
            if description_value:
                safe_description = "<br>".join(
                    escape(str(description_value)).splitlines()
                )
                contact_description = Markup(safe_description)
            else:
                contact_description = Markup(
                    "Estamos à disposição para falar com você pelos canais abaixo."
                )

            map_value = parsed_contact_data.get("map") or parsed_contact_data.get(
                "iframe"
            )
            map_candidate = _prepare_map_embed(map_value)
            if map_candidate:
                map_embed = map_candidate
        else:
            cleaned_html = raw_content

            anchor_pattern = re.compile(
                r"<a\b[^>]*href\s*=\s*\"(?P<href>[^\"]+)\"[^>]*>(?P<label>.*?)</a>",
                re.IGNORECASE | re.DOTALL,
            )
            for match in anchor_pattern.finditer(raw_content):
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
                r"(<iframe\b[^>]*src=\"[^\"]*google\.com/maps[^\"]*\"[^>]*></iframe>)",
                re.IGNORECASE | re.DOTALL,
            )
            map_match = map_pattern.search(cleaned_html)
            if map_match:
                map_candidate = _prepare_map_embed(map_match.group(1))
                if map_candidate:
                    map_embed = map_candidate
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
        contact_address_lines=contact_address_lines,
        contact_social_links=contact_social_links,
        contact_whatsapp_display=contact_whatsapp_display,
        contact_content_is_json=contact_content_is_json,
        contact_info=contact_info,
        active_page="contato",
    )
