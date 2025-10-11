"""Decorators for route safety and error handling."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional

from flask import current_app, flash, jsonify, redirect, request, url_for
from werkzeug.exceptions import HTTPException


def _should_return_json() -> bool:
    if request.is_json:
        return True

    best = request.accept_mimetypes.best
    if best == "application/json" and (
        request.accept_mimetypes[best] >= request.accept_mimetypes.get("text/html", 0)
    ):
        return True

    if request.blueprint and request.blueprint.endswith("_api"):
        return True

    return False


def _build_redirect(redirect_endpoint: Optional[str]) -> Any:
    target: Optional[str] = None
    if redirect_endpoint:
        try:
            target = url_for(redirect_endpoint)
        except Exception:  # pragma: no cover - fallback
            target = None

    if not target:
        target = request.referrer or url_for("public.index")

    response = redirect(target)
    return response


def safe_route(
    func: Optional[Callable[..., Any]] = None,
    *,
    json_response: bool | None = None,
    redirect_endpoint: Optional[str] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Wrap a route function to provide consistent error handling.

    Parameters
    ----------
    json_response:
        Force JSON responses when ``True``. When ``False`` the handler attempts
        to render HTML responses. When ``None`` (default) the decision is based
        on the request headers.
    redirect_endpoint:
        Optional endpoint to redirect HTML responses to when an error occurs.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            wants_json = _should_return_json() if json_response is None else json_response

            try:
                return fn(*args, **kwargs)
            except HTTPException:
                raise
            except ValueError as exc:
                message = str(exc) or "Dados inválidos."
                current_app.logger.warning("Erro de validação: %s", message)
                if wants_json:
                    return jsonify({"erro": message}), 400
                flash(message, "danger")
                response = _build_redirect(redirect_endpoint)
                response.status_code = 400
                return response
            except FileNotFoundError as exc:
                message = str(exc) or "Arquivo não encontrado"
                current_app.logger.warning("Arquivo não encontrado: %s", message)
                if wants_json:
                    return jsonify({"erro": "Arquivo não encontrado"}), 404
                flash("Arquivo solicitado não foi encontrado.", "warning")
                response = _build_redirect(redirect_endpoint)
                response.status_code = 404
                return response
            except Exception as exc:  # pragma: no cover - fallback
                current_app.logger.exception("Erro não tratado na rota")
                message = str(exc) if str(exc) else "Ocorreu um erro inesperado."
                if wants_json:
                    return jsonify({"erro": message}), 500
                flash("Ocorreu um erro inesperado. Tente novamente em instantes.", "danger")
                response = _build_redirect(redirect_endpoint)
                response.status_code = 500
                return response

        return wrapper

    if func is not None:
        return decorator(func)

    return decorator


__all__ = ["safe_route"]
