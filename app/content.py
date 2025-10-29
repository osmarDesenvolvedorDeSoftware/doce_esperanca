from __future__ import annotations

import json
from logging import Logger
from typing import Dict, List, Optional

CONTENT_PLACEHOLDER = "Conteúdo em atualização"

FOOTER_CONTACT_FIELDS = (
    "support_text",
    "address",
    "phone",
    "facebook",
    "instagram",
    "youtube",
    "whatsapp",
)

FOOTER_CONTACT_DEFAULTS = {
    "support_text": "Transformando doações em oportunidades.",
    "address": "Rua Solidária, 123\nBairro Esperança, Recife - PE",
    "phone": "+55 (81) 99999-9999",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "youtube": "https://www.youtube.com",
    "whatsapp": "https://wa.me/5581999999999",
}


def decode_footer_contact_payload(
    raw_content: Optional[str], *, logger: Optional[Logger] = None
) -> Dict[str, str]:
    """Return sanitized footer data parsed from JSON content."""

    if not raw_content:
        return {}

    try:
        parsed = json.loads(raw_content)
    except (TypeError, ValueError) as exc:
        if logger:
            logger.warning("JSON inválido no conteúdo do rodapé: %s", exc)
        return {}

    if not isinstance(parsed, dict):
        if logger:
            logger.warning(
                "Conteúdo do rodapé deve ser um objeto JSON, mas foi %s",
                type(parsed).__name__,
            )
        return {}

    sanitized: Dict[str, str] = {}
    for field in FOOTER_CONTACT_FIELDS:
        value = parsed.get(field)
        if isinstance(value, str):
            sanitized[field] = value.strip()

    return sanitized


def footer_contact_with_defaults(
    raw_content: Optional[str], *, logger: Optional[Logger] = None
) -> Dict[str, str]:
    """Merge stored footer data with defaults for presentation."""

    stored_values = decode_footer_contact_payload(raw_content, logger=logger)
    combined = dict(FOOTER_CONTACT_DEFAULTS)
    for field in FOOTER_CONTACT_FIELDS:
        value = stored_values.get(field)
        if value:
            combined[field] = value

    return combined

INSTITUTIONAL_SECTIONS: List[Dict[str, str]] = [
    {
        "slug": "inicio",
        "label": "Texto da Home",
        "default_title": "Bem-vindo(a) ao Projeto Doce Esperança",
        "content_help": "Texto de abertura exibido na página inicial.",
        "image_help": "Imagem de destaque mostrada no topo da página inicial.",
    },
    {
        "slug": "missao",
        "label": "Missão",
        "default_title": "Nossa missão",
        "content_help": "Descreva a missão da ONG apresentada na página inicial e na página Sobre.",
    },
    {
        "slug": "principios",
        "label": "Princípios e Atuação",
        "default_title": "Princípios e atuação",
        "content_help": "Liste os princípios e áreas de atuação destacados na página inicial.",
    },
    {
        "slug": "sobre",
        "label": "Texto da página Sobre",
        "default_title": "Sobre a Doce Esperança",
        "content_help": "Conte a história da ONG e destaque seus diferenciais na página Sobre.",
        "image_help": "Imagem apresentada no topo da página Sobre.",
    },
    {
        "slug": "contato",
        "label": "Texto da página Contato",
        "default_title": "Fale com a Doce Esperança",
        "content_help": "Inclua endereço, horários, canais de contato e links úteis. Esse conteúdo também aparece no rodapé.",
        "resumo_help": "Informe o e-mail principal para receber mensagens do formulário de contato.",
    },
    {
        "slug": "placeholder_parceiros",
        "label": "Mensagem - parceiros indisponíveis",
        "default_title": "Parcerias em atualização",
        "content_help": "Mensagem exibida quando não há parceiros cadastrados nas páginas Início e Projetos.",
    },
    {
        "slug": "placeholder_produtos",
        "label": "Mensagem - produtos artesanais indisponíveis",
        "default_title": "Produtos em atualização",
        "content_help": "Mensagem exibida quando não há materiais ou produtos artesanais cadastrados na página Doação.",
    },
    {
        "slug": "placeholder_transparencia",
        "label": "Mensagem - documentos de transparência indisponíveis",
        "default_title": "Transparência em atualização",
        "content_help": "Mensagem exibida quando não há documentos de transparência publicados.",
    },
    {
        "slug": "placeholder_apoios",
        "label": "Mensagem - apoios indisponíveis",
        "default_title": "Apoios em atualização",
        "content_help": "Mensagem exibida quando não há registros de apoio cadastrados na página Projetos.",
    },
    {
        "slug": "placeholder_voluntarios",
        "label": "Mensagem - voluntariado indisponível",
        "default_title": "Voluntariado em atualização",
        "content_help": "Mensagem exibida quando não há voluntários cadastrados na página Projetos.",
    },
    {
        "slug": "placeholder_galeria",
        "label": "Mensagem - galeria vazia",
        "default_title": "Galeria em atualização",
        "content_help": "Mensagem exibida quando não há itens publicados na galeria de fotos.",
    },
]

INSTITUTIONAL_SECTION_MAP: Dict[str, Dict[str, str]] = {
    section["slug"]: section for section in INSTITUTIONAL_SECTIONS
}

INSTITUTIONAL_SLUGS: List[str] = [section["slug"] for section in INSTITUTIONAL_SECTIONS]

__all__ = [
    "CONTENT_PLACEHOLDER",
    "FOOTER_CONTACT_DEFAULTS",
    "FOOTER_CONTACT_FIELDS",
    "decode_footer_contact_payload",
    "footer_contact_with_defaults",
    "INSTITUTIONAL_SECTIONS",
    "INSTITUTIONAL_SECTION_MAP",
    "INSTITUTIONAL_SLUGS",
]
