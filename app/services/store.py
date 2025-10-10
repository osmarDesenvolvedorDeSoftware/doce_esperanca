from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, List

from flask import current_app


def _get_store_data_path() -> Path:
    """Return the path to the JSON file that stores the products."""

    default_folder = Path(current_app.static_folder) / "data"
    data_folder = Path(current_app.config.get("STORE_DATA_FOLDER", default_folder))
    data_folder.mkdir(parents=True, exist_ok=True)
    filename = current_app.config.get("STORE_DATA_FILENAME", "produtos.json")
    return data_folder / filename


def _coerce_decimal(value: Any, default: float = 0.0) -> float:
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return default


def load_products() -> List[Dict[str, Any]]:
    """Load store products from the JSON file."""

    data_path = _get_store_data_path()
    if not data_path.exists():
        return []

    try:
        raw_content = data_path.read_text(encoding="utf-8")
    except OSError:
        current_app.logger.exception("Não foi possível ler o arquivo de produtos da loja.")
        return []

    if not raw_content.strip():
        return []

    try:
        payload = json.loads(raw_content)
    except json.JSONDecodeError:
        current_app.logger.exception("Conteúdo JSON inválido em %s", data_path)
        return []

    if not isinstance(payload, list):
        return []

    products: List[Dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        product = {
            "id": item.get("id"),
            "nome": item.get("nome", ""),
            "descricao": item.get("descricao", ""),
            "preco": _coerce_decimal(item.get("preco"), 0.0),
            "frete": _coerce_decimal(item.get("frete"), 0.0),
            "imagem": item.get("imagem"),
            "video": item.get("video"),
            "created_at": item.get("created_at"),
        }
        products.append(product)

    return products


def save_products(products: Iterable[Dict[str, Any]]) -> None:
    """Persist the provided list of products to the JSON file."""

    data_path = _get_store_data_path()
    serializable: List[Dict[str, Any]] = []
    for item in products:
        if not isinstance(item, dict):
            continue
        serializable.append(
            {
                "id": item.get("id"),
                "nome": item.get("nome"),
                "descricao": item.get("descricao"),
                "preco": _coerce_decimal(item.get("preco"), 0.0),
                "frete": _coerce_decimal(item.get("frete"), 0.0),
                "imagem": item.get("imagem"),
                "video": item.get("video"),
                "created_at": item.get("created_at"),
            }
        )

    try:
        data_path.write_text(
            json.dumps(serializable, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        current_app.logger.exception("Não foi possível salvar o arquivo de produtos da loja.")
        raise
