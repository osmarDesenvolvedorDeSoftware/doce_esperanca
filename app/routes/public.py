from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

import qrcode
from qrcode.constants import ERROR_CORRECT_M

from flask import (
    Blueprint,
    abort,
    current_app,
    g,
    redirect,
    request,
    Response,
    render_template,
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
from app.services.seo import (
    DEFAULT_KEYWORDS,
    DEFAULT_SITE_DESCRIPTION,
    DEFAULT_SITE_NAME,
    build_metadata,
    build_organization_schema,
    parse_iso_datetime,
    summarize_text,
)
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


def _get_inicio_texto() -> Optional[TextoInstitucional]:
    if hasattr(g, "_inicio_texto"):
        return getattr(g, "_inicio_texto")

    inicio_texto = TextoInstitucional.query.filter_by(slug="inicio").first()
    g._inicio_texto = inicio_texto
    return inicio_texto


def _get_site_identity() -> str:
    if hasattr(g, "_site_identity"):
        return getattr(g, "_site_identity")

    inicio_texto = _get_inicio_texto()
    identity = DEFAULT_SITE_NAME
    if inicio_texto and inicio_texto.titulo:
        identity = inicio_texto.titulo.strip() or DEFAULT_SITE_NAME

    g._site_identity = identity
    return identity


def _get_site_tagline() -> str:
    if hasattr(g, "_site_tagline"):
        return getattr(g, "_site_tagline")

    inicio_texto = _get_inicio_texto()
    tagline = summarize_text(
        inicio_texto.resumo if inicio_texto else None,
        inicio_texto.conteudo if inicio_texto else None,
        fallback=DEFAULT_SITE_DESCRIPTION,
    ) or DEFAULT_SITE_DESCRIPTION

    g._site_tagline = tagline
    return tagline


def _absolute_static_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None

    cleaned = str(path).lstrip("/")
    if not cleaned:
        return None

    try:
        return url_for("static", filename=cleaned, _external=True)
    except Exception:  # pragma: no cover - fallback safety
        current_app.logger.warning("Falha ao gerar URL absoluta para %s", path)
        return None


def _default_share_image() -> str:
    cached = getattr(g, "_default_share_image", None)
    if cached:
        return cached

    image_url = url_for("static", filename="img/Todos.jpg", _external=True)
    g._default_share_image = image_url
    return image_url


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
    inicio_texto = _get_inicio_texto()

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

    site_identity = _get_site_identity()
    site_tagline = _get_site_tagline()
    site_keywords = ", ".join(DEFAULT_KEYWORDS)
    default_share_image = _default_share_image()

    contato_email = None
    if contato_texto and contato_texto.resumo:
        contato_email = contato_texto.resumo.strip() or None

    base_url = url_for("public.index", _external=True)
    logo_url = _absolute_static_url("img/logo.ico")
    same_as_links = []
    for key in ("facebook", "instagram", "youtube", "whatsapp"):
        normalized = _normalize_external_url(footer_contact_data.get(key, ""))
        if normalized:
            same_as_links.append(normalized)

    organization_schema = build_organization_schema(
        site_name=site_identity,
        base_url=base_url,
        logo_url=logo_url,
        description=site_tagline,
        email=contato_email,
        phone=footer_contact_data.get("phone"),
        address=footer_contact_data.get("address"),
        same_as=same_as_links,
    )

    return {
        "footer_contact": contato_texto,
        "footer_contact_data": footer_contact_data,
        "footer_contact_phone_href": footer_contact_phone_href,
        "site_identity": site_identity,
        "site_tagline": site_tagline,
        "site_keywords": site_keywords,
        "default_share_image": default_share_image,
        "organization_schema": organization_schema,
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
    texto_inicio = textos.get("inicio")
    site_name = _get_site_identity()
    description = summarize_text(
        texto_inicio.resumo if texto_inicio else None,
        texto_inicio.conteudo if texto_inicio else None,
        fallback=DEFAULT_SITE_DESCRIPTION,
    )
    hero_title = (
        texto_inicio.titulo.strip()
        if texto_inicio and texto_inicio.titulo
        else site_name
    )
    share_image = (
        _absolute_static_url(banners[0].imagem_path)
        if banners and getattr(banners[0], "imagem_path", None)
        else None
    ) or _default_share_image()
    website_schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "url": url_for("public.index", _external=True),
        "name": site_name,
        "description": description,
    }
    seo = build_metadata(
        title=f"Início - {site_name}",
        description=description,
        canonical=url_for("public.index", _external=True),
        extra_keywords=[hero_title, "campanhas solidárias", "impacto comunitário"],
        og_image=share_image,
        structured_data=website_schema,
    )

    return render_template(
        "public/inicio.html",
        textos=textos,
        parceiros=parceiros,
        banners=banners,
        parceiros_placeholder=textos.get("placeholder_parceiros"),
        active_page="inicio",
        seo=seo,
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
    texto_sobre = textos.get("sobre")
    texto_missao = textos.get("missao")
    site_name = _get_site_identity()
    description = summarize_text(
        texto_sobre.resumo if texto_sobre else None,
        texto_sobre.conteudo if texto_sobre else None,
        texto_missao.conteudo if texto_missao else None,
        fallback=DEFAULT_SITE_DESCRIPTION,
    )
    share_image = (
        _absolute_static_url(texto_sobre.imagem_path)
        if texto_sobre and texto_sobre.imagem_path
        else None
    ) or _default_share_image()
    seo = build_metadata(
        title=f"Sobre - {site_name}",
        description=description,
        canonical=url_for("public.sobre", _external=True),
        extra_keywords=["história da ONG", "missão solidária"],
        og_image=share_image,
    )
    return render_template(
        "public/sobre.html",
        texto_sobre=texto_sobre,
        texto_missao=texto_missao,
        active_page="sobre",
        seo=seo,
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
    canonical_url = (
        url_for("public.galeria", page=page, _external=True)
        if page and page > 1
        else url_for("public.galeria", _external=True)
    )
    description = summarize_text(
        texto_galeria.resumo if texto_galeria else None,
        texto_galeria.conteudo if texto_galeria else None,
        fallback="Explore a galeria de fotos e registros das ações da Doce Esperança.",
    )
    gallery_image = (
        _absolute_static_url(galerias[0].imagem_path)
        if galerias and getattr(galerias[0], "imagem_path", None)
        else None
    ) or _default_share_image()
    gallery_schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": header_title,
        "description": description,
        "url": canonical_url,
    }
    seo = build_metadata(
        title=f"Galeria - {_get_site_identity()}",
        description=description,
        canonical=canonical_url,
        extra_keywords=["galeria de fotos", "ações sociais"],
        og_image=gallery_image,
        structured_data=gallery_schema,
        noindex=page > 1,
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
        seo=seo,
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
    texto_depoimentos = textos.get("depoimentos")
    description = summarize_text(
        texto_depoimentos.resumo if texto_depoimentos else None,
        texto_depoimentos.conteudo if texto_depoimentos else None,
        fallback="Histórias de transformação contadas por quem vivencia a Doce Esperança.",
    )
    seo = build_metadata(
        title=f"Depoimentos - {_get_site_identity()}",
        description=description,
        canonical=url_for("public.depoimentos", _external=True),
        extra_keywords=["relatos de impacto", "histórias reais"],
        og_image=_default_share_image(),
    )
    return render_template(
        "public/depoimentos.html",
        texto_depoimentos=texto_depoimentos,
        depoimentos=depoimentos_itens,
        active_page="depoimentos",
        seo=seo,
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

    description = "Acesse relatórios, documentos e prestações de contas da Doce Esperança."
    seo = build_metadata(
        title=f"Transparência - {_get_site_identity()}",
        description=description,
        canonical=url_for("public.transparencia", _external=True),
        extra_keywords=["prestação de contas", "documentos da ONG"],
        og_image=_default_share_image(),
    )

    return render_template(
        "public/transparencia.html",
        documentos=documentos,
        transparencia_placeholder=placeholders.get("placeholder_transparencia"),
        active_page="transparencia",
        seo=seo,
    )


@public_bp.route("/doacao/")
@safe_route()
def doacao() -> str:
    documentos = (
        Transparencia.query.order_by(Transparencia.publicado_em.desc(), Transparencia.id.desc()).all()
    )
    pix_qrcode_path = _ensure_pix_qrcode()
    site_name = _get_site_identity()
    description = (
        "Contribua com a Doce Esperança por PIX, transferência ou doações em "
        "materiais e fortaleça projetos sociais que transformam vidas."
    )
    share_image = _absolute_static_url(pix_qrcode_path) if pix_qrcode_path else _default_share_image()
    seo = build_metadata(
        title=f"Doações - {site_name}",
        description=description,
        canonical=url_for("public.doacao", _external=True),
        extra_keywords=["doações por PIX", "como ajudar"],
        og_image=share_image,
    )
    return render_template(
        "public/doacao.html",
        documentos=documentos,
        pix_qrcode_path=pix_qrcode_path,
        pix_key=PIX_KEY,
        pix_copy_paste=PIX_COPY_AND_PASTE,
        active_page="doacao",
        seo=seo,
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

    site_name = _get_site_identity()
    description = (
        "Conheça a loja solidária da Doce Esperança e apoie projetos sociais "
        "adquirindo produtos artesanais feitos com carinho."
    )
    share_image = (
        _absolute_static_url(produtos[0]["imagem"])
        if produtos and produtos[0].get("imagem")
        else _default_share_image()
    )
    catalog_schema = {
        "@context": "https://schema.org",
        "@type": "OfferCatalog",
        "name": f"Loja Solidária {site_name}",
        "description": description,
        "url": url_for("public.loja", _external=True),
    }
    seo = build_metadata(
        title=f"Loja Solidária - {site_name}",
        description=description,
        canonical=url_for("public.loja", _external=True),
        extra_keywords=["produtos solidários", "artesanato social"],
        og_image=share_image,
        structured_data=catalog_schema,
    )

    return render_template(
        "public/loja.html",
        produtos=produtos,
        pix_key=PIX_KEY,
        active_page="loja",
        seo=seo,
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
    canonical_url = url_for(
        "public.loja_produto",
        produto_id=contexto_produto["id"],
        slug=slug_canonical,
        _external=True,
    )
    description = summarize_text(
        contexto_produto.get("descricao"),
        fallback="Produto solidário disponível na loja da Doce Esperança.",
    )
    image_url = (
        _absolute_static_url(contexto_produto.get("imagem"))
        if contexto_produto.get("imagem")
        else None
    ) or _default_share_image()
    video_url = None
    if contexto_produto.get("video"):
        video_url = _absolute_static_url(contexto_produto.get("video"))
    product_schema = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": contexto_produto.get("nome") or "Produto solidário",
        "description": description,
        "image": [image_url] if image_url else None,
        "url": canonical_url,
        "offers": {
            "@type": "Offer",
            "price": f"{contexto_produto['total']:.2f}",
            "priceCurrency": "BRL",
            "availability": "https://schema.org/InStock",
            "url": canonical_url,
        },
    }
    if video_url:
        product_schema["video"] = video_url
    seo = build_metadata(
        title=f"{contexto_produto.get('nome') or 'Produto'} - {_get_site_identity()}",
        description=description,
        canonical=canonical_url,
        extra_keywords=[contexto_produto.get("nome") or "produto solidário"],
        og_image=image_url,
        structured_data=product_schema,
    )

    return render_template(
        "public/loja_produto.html",
        produto=contexto_produto,
        pix_key=PIX_KEY,
        active_page="loja",
        seo=seo,
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

    description = (
        "Conheça os projetos, parceiros, apoios e voluntários que movimentam a "
        "rede solidária da Doce Esperança."
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Projetos sociais",
        "description": description,
        "url": url_for("public.projetos", _external=True),
    }
    seo = build_metadata(
        title=f"Projetos - {_get_site_identity()}",
        description=description,
        canonical=url_for("public.projetos", _external=True),
        extra_keywords=["projetos sociais", "parcerias solidárias"],
        og_image=_default_share_image(),
        structured_data=schema,
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
        seo=seo,
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
    description = summarize_text(
        contact_description,
        texto_contato.conteudo if texto_contato else None,
        fallback="Entre em contato com a equipe da Doce Esperança e conheça nossos canais de atendimento.",
    )
    seo = build_metadata(
        title=f"Contato - {_get_site_identity()}",
        description=description,
        canonical=url_for("public.contato", _external=True),
        extra_keywords=["fale conosco", "contato ONG"],
        og_image=_default_share_image(),
    )
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
        seo=seo,
    )


@public_bp.route("/robots.txt")
@safe_route()
def robots_txt() -> Response:
    sitemap_url = url_for("public.sitemap", _external=True)
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Allow: /",
        f"Sitemap: {sitemap_url}",
    ]
    body = "\n".join(lines) + "\n"
    return current_app.response_class(body, mimetype="text/plain")


@public_bp.route("/sitemap.xml")
@safe_route()
def sitemap() -> Response:
    urls: List[Dict[str, Optional[str]]] = []
    pages = [
        ("public.index", "weekly", "1.0"),
        ("public.sobre", "monthly", "0.8"),
        ("public.projetos", "monthly", "0.8"),
        ("public.galeria", "weekly", "0.7"),
        ("public.depoimentos", "monthly", "0.6"),
        ("public.transparencia", "monthly", "0.6"),
        ("public.doacao", "weekly", "0.7"),
        ("public.loja", "weekly", "0.7"),
        ("public.contato", "yearly", "0.5"),
    ]

    for endpoint, changefreq, priority in pages:
        try:
            loc = url_for(endpoint, _external=True)
        except Exception:
            current_app.logger.debug("Endpoint %s not found for sitemap", endpoint)
            continue
        urls.append(
            {
                "loc": loc,
                "changefreq": changefreq,
                "priority": priority,
                "lastmod": None,
            }
        )

    produtos = load_store_products()
    for item in produtos:
        produto_id = item.get("id")
        if produto_id is None:
            continue
        slug = _slugify(str(item.get("nome", "")))
        try:
            loc = url_for(
                "public.loja_produto",
                produto_id=produto_id,
                slug=slug,
                _external=True,
            )
        except Exception:
            continue
        timestamp = item.get("updated_at") or item.get("created_at")
        lastmod_dt: Optional[datetime] = None
        if isinstance(timestamp, (int, float)):
            lastmod_dt = datetime.utcfromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            lastmod_dt = parse_iso_datetime(timestamp)
        lastmod = lastmod_dt.date().isoformat() if lastmod_dt else None
        urls.append(
            {
                "loc": loc,
                "changefreq": "weekly",
                "priority": "0.6",
                "lastmod": lastmod,
            }
        )

    xml_entries = []
    for entry in urls:
        parts = ["  <url>", f"    <loc>{entry['loc']}</loc>"]
        if entry.get("lastmod"):
            parts.append(f"    <lastmod>{entry['lastmod']}</lastmod>")
        if entry.get("changefreq"):
            parts.append(f"    <changefreq>{entry['changefreq']}</changefreq>")
        if entry.get("priority"):
            parts.append(f"    <priority>{entry['priority']}</priority>")
        parts.append("  </url>")
        xml_entries.append("\n".join(parts))

    xml_body = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<urlset xmlns=\"https://www.sitemaps.org/schemas/sitemap/0.9\">\n"
        + "\n".join(xml_entries)
        + "\n</urlset>\n"
    )
    return current_app.response_class(xml_body, mimetype="application/xml")
