from __future__ import annotations

import os
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Sequence

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from urllib.parse import urljoin, urlparse
from werkzeug.utils import secure_filename

from PIL import Image, ImageOps, UnidentifiedImageError

from app import db, login_manager
from app.forms import (
    ApoioForm,
    BannerForm,
    GaleriaForm,
    LoginForm,
    ParceiroForm,
    TextoInstitucionalForm,
    TransparenciaForm,
    VoluntarioForm,
)
from app.content import (
    INSTITUTIONAL_SECTION_MAP,
    INSTITUTIONAL_SECTIONS,
    INSTITUTIONAL_SLUGS,
)
from app.models import (
    Apoio,
    Banner,
    Galeria,
    Parceiro,
    TextoInstitucional,
    Transparencia,
    User,
    Voluntario,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _save_file(
    field_storage,
    base_folder: str,
    processor: Optional[Callable[[object, Path], None]] = None,
) -> Optional[str]:
    if not field_storage:
        return None

    filename = secure_filename(field_storage.filename or "")
    if not filename:
        return None

    name, extension = os.path.splitext(filename)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    final_name = f"{name}_{timestamp}{extension.lower()}"

    target_folder = Path(base_folder)
    _ensure_directory(target_folder)

    file_path = target_folder / final_name
    try:
        if processor:
            processor(field_storage, file_path)
        else:
            field_storage.save(file_path)
    except ValueError:
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass
        raise

    relative_path = os.path.relpath(file_path, start=current_app.static_folder)
    return relative_path.replace(os.sep, "/")


def _delete_file(relative_path: Optional[str]) -> None:
    if not relative_path:
        return

    candidate = Path(current_app.static_folder) / relative_path
    try:
        candidate = candidate.resolve(strict=False)
    except FileNotFoundError:
        return

    static_root = Path(current_app.static_folder).resolve()
    if not str(candidate).startswith(str(static_root)):
        return

    if candidate.exists():
        candidate.unlink()


def _process_image(
    field_storage,
    destination: Path,
    size: Optional[Sequence[int]] = None,
) -> None:
    stream = getattr(field_storage, "stream", field_storage)
    if hasattr(stream, "seek"):
        stream.seek(0)

    try:
        with Image.open(stream) as image:
            image = ImageOps.exif_transpose(image)
            if size:
                resample = getattr(Image, "Resampling", Image).LANCZOS
                image = ImageOps.fit(image, size, method=resample)

            extension = destination.suffix.lower()
            save_kwargs: Dict[str, object] = {}

            if extension in {".jpg", ".jpeg"}:
                image = image.convert("RGB")
                save_kwargs.setdefault("format", "JPEG")
                save_kwargs.setdefault("quality", 90)
            elif extension == ".png":
                if image.mode not in ("RGB", "RGBA", "LA", "L"):
                    image = image.convert("RGBA")
                save_kwargs.setdefault("format", "PNG")
            else:
                if image.mode not in ("RGB", "RGBA", "LA", "L"):
                    image = image.convert("RGB")
                save_kwargs.setdefault("format", image.format or "PNG")

            image.save(destination, **save_kwargs)
    except UnidentifiedImageError as exc:
        raise ValueError("O arquivo enviado não é uma imagem válida.") from exc
    finally:
        if hasattr(stream, "seek"):
            stream.seek(0)


def _combine_date_with_min_time(value: Optional[datetime | date]) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if hasattr(value, "year"):
        return datetime.combine(value, time.min)

    return None


def _is_safe_redirect_target(target: Optional[str]) -> bool:
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def _ensure_institutional_texts() -> Dict[str, TextoInstitucional]:
    existing = {
        texto.slug: texto
        for texto in TextoInstitucional.query.filter(
            TextoInstitucional.slug.in_(INSTITUTIONAL_SLUGS)
        ).all()
    }

    missing = [
        section for section in INSTITUTIONAL_SECTIONS if section["slug"] not in existing
    ]
    if missing:
        for section in missing:
            db.session.add(
                TextoInstitucional(
                    titulo=section.get("default_title") or section["label"],
                    slug=section["slug"],
                    conteudo="",
                )
            )
        db.session.commit()
        existing = {
            texto.slug: texto
            for texto in TextoInstitucional.query.filter(
                TextoInstitucional.slug.in_(INSTITUTIONAL_SLUGS)
            ).all()
        }

    return existing


@admin_bp.before_request
def restrict_to_admins() -> Optional[object]:
    if request.blueprint != admin_bp.name:
        return None

    endpoint = request.endpoint or ""
    allowed_endpoints: Iterable[str] = {"admin.login", "admin.send_upload"}

    if endpoint in allowed_endpoints:
        return None

    if not current_user.is_authenticated:
        return login_manager.unauthorized()

    if not getattr(current_user, "is_admin", False):
        abort(403)

    return None


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if getattr(current_user, "is_admin", False):
            return redirect(url_for("admin.dashboard"))
        logout_user()

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user and user.is_active and user.is_admin and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash("Login realizado com sucesso.", "success")
            next_page = request.args.get("next")
            if next_page and _is_safe_redirect_target(next_page):
                return redirect(next_page)
            return redirect(url_for("admin.dashboard"))
        flash("Credenciais inválidas ou acesso não autorizado.", "danger")
    return render_template("admin/login.html", form=form)


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada com sucesso.", "success")
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
@login_required
def dashboard():
    stats = {
        "textos": TextoInstitucional.query.count(),
        "parceiros": Parceiro.query.count(),
        "voluntarios": Voluntario.query.count(),
        "galerias": Galeria.query.count(),
        "transparencias": Transparencia.query.count(),
        "apoios": Apoio.query.count(),
        "banners": Banner.query.count(),
    }
    return render_template("admin/dashboard.html", stats=stats)


@admin_bp.route("/uploads/<path:filename>")
@login_required
def send_upload(filename: str):
    safe_path = Path(filename)
    if safe_path.is_absolute() or ".." in safe_path.parts:
        abort(404)
    return send_from_directory(current_app.static_folder, str(safe_path))


# ----- Texto Institucional -----


@admin_bp.route("/textos")
@login_required
def textos_list():
    featured_map = _ensure_institutional_texts()

    todos_textos = TextoInstitucional.query.order_by(TextoInstitucional.updated_at.desc()).all()
    ordered_featured = [
        featured_map[slug] for slug in INSTITUTIONAL_SLUGS if slug in featured_map
    ]
    outros_textos = [
        texto for texto in todos_textos if texto.slug not in featured_map
    ]
    outros_textos.sort(key=lambda item: (item.titulo or item.slug or "").lower())

    textos = ordered_featured + outros_textos
    return render_template(
        "admin/textos/list.html",
        textos=textos,
        institutional_slugs=set(INSTITUTIONAL_SLUGS),
        sections_map=INSTITUTIONAL_SECTION_MAP,
    )


@admin_bp.route("/textos/criar", methods=["GET", "POST"])
@login_required
def textos_create():
    form = TextoInstitucionalForm()
    _ensure_content_image_hint(form.imagem)
    if form.validate_on_submit():
        if form.slug.data in INSTITUTIONAL_SLUGS:
            form.slug.errors.append("Esse slug é reservado para conteúdos institucionais fixos.")
        else:
            texto = TextoInstitucional(
                titulo=form.titulo.data,
                slug=form.slug.data,
                resumo=form.resumo.data,
                conteudo=form.conteudo.data,
            )
            if form.imagem.data:
                try:
                    relative_path = _save_file(
                        form.imagem.data,
                        current_app.config["IMAGE_UPLOAD_FOLDER"],
                        processor=_content_image_processor,
                    )
                except ValueError as exc:
                    form.imagem.errors.append(str(exc))
                    return render_template("admin/textos/form.html", form=form, texto=None)
                texto.imagem_path = relative_path

            db.session.add(texto)
            try:
                db.session.commit()
                flash("Texto criado com sucesso.", "success")
                return redirect(url_for("admin.textos_list"))
            except IntegrityError:
                db.session.rollback()
                flash("Erro ao salvar texto. Verifique se o slug já está em uso.", "danger")
    return render_template("admin/textos/form.html", form=form, texto=None)


@admin_bp.route("/textos/<int:texto_id>/editar", methods=["GET", "POST"])
@login_required
def textos_edit(texto_id: int):
    _ensure_institutional_texts()
    texto = TextoInstitucional.query.get_or_404(texto_id)
    form = TextoInstitucionalForm(obj=texto)
    section_info = INSTITUTIONAL_SECTION_MAP.get(texto.slug)

    if section_info:
        render_kw = dict(form.slug.render_kw or {})
        render_kw.update({"readonly": True})
        form.slug.render_kw = render_kw
        form.slug.description = section_info.get("label")
        if section_info.get("resumo_help"):
            form.resumo.description = section_info["resumo_help"]
        if section_info.get("content_help"):
            form.conteudo.description = section_info["content_help"]
        if section_info.get("image_help"):
            form.imagem.description = section_info["image_help"]

    _ensure_content_image_hint(form.imagem)

    if request.method == "GET":
        form.conteudo.data = texto.conteudo
        form.slug.data = texto.slug
    elif section_info:
        form.slug.data = texto.slug
    if form.validate_on_submit():
        texto.titulo = form.titulo.data
        if section_info is None:
            texto.slug = form.slug.data
        else:
            form.slug.data = texto.slug
        texto.resumo = form.resumo.data
        texto.conteudo = form.conteudo.data

        if form.imagem.data:
            try:
                new_path = _save_file(
                    form.imagem.data,
                    current_app.config["IMAGE_UPLOAD_FOLDER"],
                    processor=_content_image_processor,
                )
            except ValueError as exc:
                form.imagem.errors.append(str(exc))
                return render_template("admin/textos/form.html", form=form, texto=texto)
            _delete_file(texto.imagem_path)
            texto.imagem_path = new_path

        try:
            db.session.commit()
            flash("Texto atualizado com sucesso.", "success")
            return redirect(url_for("admin.textos_list"))
        except IntegrityError:
            db.session.rollback()
            flash("Erro ao atualizar texto. Verifique se o slug já está em uso.", "danger")
    return render_template("admin/textos/form.html", form=form, texto=texto)


@admin_bp.route("/textos/<int:texto_id>/excluir", methods=["POST"])
@login_required
def textos_delete(texto_id: int):
    texto = TextoInstitucional.query.get_or_404(texto_id)
    if texto.slug in INSTITUTIONAL_SLUGS:
        flash("Este texto institucional não pode ser excluído.", "warning")
        return redirect(url_for("admin.textos_list"))
    _delete_file(texto.imagem_path)
    db.session.delete(texto)
    db.session.commit()
    flash("Texto excluído com sucesso.", "success")
    return redirect(url_for("admin.textos_list"))


# ----- Parceiros -----


@admin_bp.route("/parceiros")
@login_required
def parceiros_list():
    parceiros = Parceiro.query.order_by(Parceiro.created_at.desc()).all()
    return render_template("admin/parceiros/list.html", parceiros=parceiros)


@admin_bp.route("/parceiros/criar", methods=["GET", "POST"])
@login_required
def parceiros_create():
    form = ParceiroForm()
    if form.validate_on_submit():
        parceiro = Parceiro(
            nome=form.nome.data,
            slug=form.slug.data,
            descricao=form.descricao.data,
            website=form.website.data,
        )
        if form.logo.data:
            parceiro.logo_path = _save_file(form.logo.data, current_app.config["IMAGE_UPLOAD_FOLDER"])
        db.session.add(parceiro)
        try:
            db.session.commit()
            flash("Parceiro criado com sucesso.", "success")
            return redirect(url_for("admin.parceiros_list"))
        except IntegrityError:
            db.session.rollback()
            flash("Erro ao salvar parceiro. Verifique se o slug já está em uso.", "danger")
    return render_template("admin/parceiros/form.html", form=form, parceiro=None)


@admin_bp.route("/parceiros/<int:parceiro_id>/editar", methods=["GET", "POST"])
@login_required
def parceiros_edit(parceiro_id: int):
    parceiro = Parceiro.query.get_or_404(parceiro_id)
    form = ParceiroForm(obj=parceiro)
    if form.validate_on_submit():
        parceiro.nome = form.nome.data
        parceiro.slug = form.slug.data
        parceiro.descricao = form.descricao.data
        parceiro.website = form.website.data
        if form.logo.data:
            _delete_file(parceiro.logo_path)
            parceiro.logo_path = _save_file(form.logo.data, current_app.config["IMAGE_UPLOAD_FOLDER"])
        try:
            db.session.commit()
            flash("Parceiro atualizado com sucesso.", "success")
            return redirect(url_for("admin.parceiros_list"))
        except IntegrityError:
            db.session.rollback()
            flash("Erro ao atualizar parceiro. Verifique se o slug já está em uso.", "danger")
    return render_template("admin/parceiros/form.html", form=form, parceiro=parceiro)


@admin_bp.route("/parceiros/<int:parceiro_id>/excluir", methods=["POST"])
@login_required
def parceiros_delete(parceiro_id: int):
    parceiro = Parceiro.query.get_or_404(parceiro_id)
    _delete_file(parceiro.logo_path)
    db.session.delete(parceiro)
    db.session.commit()
    flash("Parceiro excluído com sucesso.", "success")
    return redirect(url_for("admin.parceiros_list"))


# ----- Apoios -----


@admin_bp.route("/apoios")
@login_required
def apoios_list():
    apoios = Apoio.query.order_by(Apoio.created_at.desc()).all()
    return render_template("admin/apoios/list.html", apoios=apoios)


@admin_bp.route("/apoios/criar", methods=["GET", "POST"])
@login_required
def apoios_create():
    form = ApoioForm()
    if form.validate_on_submit():
        apoio = Apoio(titulo=form.titulo.data, descricao=form.descricao.data)
        db.session.add(apoio)
        db.session.commit()
        flash("Apoio criado com sucesso.", "success")
        return redirect(url_for("admin.apoios_list"))
    return render_template("admin/apoios/form.html", form=form, apoio=None)


@admin_bp.route("/apoios/<int:apoio_id>/editar", methods=["GET", "POST"])
@login_required
def apoios_edit(apoio_id: int):
    apoio = Apoio.query.get_or_404(apoio_id)
    form = ApoioForm(obj=apoio)
    if form.validate_on_submit():
        apoio.titulo = form.titulo.data
        apoio.descricao = form.descricao.data
        db.session.commit()
        flash("Apoio atualizado com sucesso.", "success")
        return redirect(url_for("admin.apoios_list"))
    return render_template("admin/apoios/form.html", form=form, apoio=apoio)


@admin_bp.route("/apoios/<int:apoio_id>/excluir", methods=["POST"])
@login_required
def apoios_delete(apoio_id: int):
    apoio = Apoio.query.get_or_404(apoio_id)
    db.session.delete(apoio)
    db.session.commit()
    flash("Apoio excluído com sucesso.", "success")
    return redirect(url_for("admin.apoios_list"))


# ----- Banners -----


def _banner_processor(storage, path: Path) -> None:
    _process_image(storage, path, size=(1200, 400))


CONTENT_IMAGE_TARGET_SIZE = (1200, 800)
CONTENT_IMAGE_SIZE_HINT = (
    f"As imagens serão redimensionadas para {CONTENT_IMAGE_TARGET_SIZE[0]}x{CONTENT_IMAGE_TARGET_SIZE[1]} pixels."
)


def _content_image_processor(storage, path: Path) -> None:
    _process_image(storage, path, size=CONTENT_IMAGE_TARGET_SIZE)


def _ensure_content_image_hint(field: Any) -> None:
    size_hint = CONTENT_IMAGE_SIZE_HINT
    existing = getattr(field, "description", None) or ""
    if size_hint not in existing:
        field.description = f"{existing} {size_hint}".strip()


@admin_bp.route("/banners")
@login_required
def banners_list():
    banners = Banner.query.order_by(Banner.ordem.asc(), Banner.created_at.desc()).all()
    return render_template("admin/banners/list.html", banners=banners)


@admin_bp.route("/banners/criar", methods=["GET", "POST"])
@login_required
def banners_create():
    form = BannerForm()
    if form.validate_on_submit():
        if not form.imagem.data:
            form.imagem.errors.append("Envie uma imagem para o banner.")
        else:
            banner = Banner(
                titulo=form.titulo.data,
                descricao=form.descricao.data,
                ordem=form.ordem.data or 0,
            )
            try:
                banner.imagem_path = _save_file(
                    form.imagem.data,
                    current_app.config["BANNER_UPLOAD_FOLDER"],
                    processor=_banner_processor,
                )
            except ValueError as exc:
                form.imagem.errors.append(str(exc))
                return render_template("admin/banners/form.html", form=form, banner=None)

            db.session.add(banner)
            db.session.commit()
            flash("Banner criado com sucesso.", "success")
            return redirect(url_for("admin.banners_list"))
    return render_template("admin/banners/form.html", form=form, banner=None)


@admin_bp.route("/banners/<int:banner_id>/editar", methods=["GET", "POST"])
@login_required
def banners_edit(banner_id: int):
    banner = Banner.query.get_or_404(banner_id)
    form = BannerForm(obj=banner)
    if form.validate_on_submit():
        banner.titulo = form.titulo.data
        banner.descricao = form.descricao.data
        banner.ordem = form.ordem.data or 0

        if form.imagem.data:
            try:
                new_path = _save_file(
                    form.imagem.data,
                    current_app.config["BANNER_UPLOAD_FOLDER"],
                    processor=_banner_processor,
                )
            except ValueError as exc:
                form.imagem.errors.append(str(exc))
                return render_template("admin/banners/form.html", form=form, banner=banner)
            _delete_file(banner.imagem_path)
            banner.imagem_path = new_path

        db.session.commit()
        flash("Banner atualizado com sucesso.", "success")
        return redirect(url_for("admin.banners_list"))
    return render_template("admin/banners/form.html", form=form, banner=banner)


@admin_bp.route("/banners/<int:banner_id>/excluir", methods=["POST"])
@login_required
def banners_delete(banner_id: int):
    banner = Banner.query.get_or_404(banner_id)
    _delete_file(banner.imagem_path)
    db.session.delete(banner)
    db.session.commit()
    flash("Banner excluído com sucesso.", "success")
    return redirect(url_for("admin.banners_list"))


# ----- Voluntários -----


@admin_bp.route("/voluntarios")
@login_required
def voluntarios_list():
    voluntarios = Voluntario.query.order_by(Voluntario.created_at.desc()).all()
    return render_template("admin/voluntarios/list.html", voluntarios=voluntarios)


@admin_bp.route("/voluntarios/criar", methods=["GET", "POST"])
@login_required
def voluntarios_create():
    form = VoluntarioForm()
    if form.validate_on_submit():
        voluntario = Voluntario(
            nome=form.nome.data,
            area=form.area.data,
            disponibilidade=form.disponibilidade.data,
            descricao=form.descricao.data,
        )
        db.session.add(voluntario)
        db.session.commit()
        flash("Voluntário criado com sucesso.", "success")
        return redirect(url_for("admin.voluntarios_list"))
    return render_template("admin/voluntarios/form.html", form=form, voluntario=None)


@admin_bp.route("/voluntarios/<int:voluntario_id>/editar", methods=["GET", "POST"])
@login_required
def voluntarios_edit(voluntario_id: int):
    voluntario = Voluntario.query.get_or_404(voluntario_id)
    form = VoluntarioForm(obj=voluntario)
    if form.validate_on_submit():
        voluntario.nome = form.nome.data
        voluntario.area = form.area.data
        voluntario.disponibilidade = form.disponibilidade.data
        voluntario.descricao = form.descricao.data
        db.session.commit()
        flash("Voluntário atualizado com sucesso.", "success")
        return redirect(url_for("admin.voluntarios_list"))
    return render_template("admin/voluntarios/form.html", form=form, voluntario=voluntario)


@admin_bp.route("/voluntarios/<int:voluntario_id>/excluir", methods=["POST"])
@login_required
def voluntarios_delete(voluntario_id: int):
    voluntario = Voluntario.query.get_or_404(voluntario_id)
    db.session.delete(voluntario)
    db.session.commit()
    flash("Voluntário excluído com sucesso.", "success")
    return redirect(url_for("admin.voluntarios_list"))


# ----- Galeria -----


@admin_bp.route("/galeria")
@login_required
def galeria_list():
    itens = Galeria.query.order_by(Galeria.created_at.desc()).all()
    return render_template("admin/galeria/list.html", itens=itens)


@admin_bp.route("/galeria/criar", methods=["GET", "POST"])
@login_required
def galeria_create():
    form = GaleriaForm()
    _ensure_content_image_hint(form.imagem)
    if form.validate_on_submit():
        if not form.imagem.data:
            form.imagem.errors.append("Envie uma imagem para a galeria.")
        else:
            try:
                imagem_path = _save_file(
                    form.imagem.data,
                    current_app.config["IMAGE_UPLOAD_FOLDER"],
                    processor=_content_image_processor,
                )
            except ValueError as exc:
                form.imagem.errors.append(str(exc))
                return render_template("admin/galeria/form.html", form=form, item=None)
            item = Galeria(
                titulo=form.titulo.data,
                slug=form.slug.data,
                descricao=form.descricao.data,
                publicado_em=_combine_date_with_min_time(form.publicado_em.data) or datetime.utcnow(),
                imagem_path=imagem_path,
            )
            db.session.add(item)
            try:
                db.session.commit()
                flash("Item da galeria criado com sucesso.", "success")
                return redirect(url_for("admin.galeria_list"))
            except IntegrityError:
                db.session.rollback()
                flash("Erro ao salvar item da galeria. Verifique se o slug já está em uso.", "danger")
    return render_template("admin/galeria/form.html", form=form, item=None)


@admin_bp.route("/galeria/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
def galeria_edit(item_id: int):
    item = Galeria.query.get_or_404(item_id)
    form = GaleriaForm(obj=item)
    _ensure_content_image_hint(form.imagem)
    if item.publicado_em:
        form.publicado_em.data = item.publicado_em.date()
    if form.validate_on_submit():
        item.titulo = form.titulo.data
        item.slug = form.slug.data
        item.descricao = form.descricao.data
        item.publicado_em = _combine_date_with_min_time(form.publicado_em.data) or item.publicado_em
        if form.imagem.data:
            try:
                new_path = _save_file(
                    form.imagem.data,
                    current_app.config["IMAGE_UPLOAD_FOLDER"],
                    processor=_content_image_processor,
                )
            except ValueError as exc:
                form.imagem.errors.append(str(exc))
                return render_template("admin/galeria/form.html", form=form, item=item)
            _delete_file(item.imagem_path)
            item.imagem_path = new_path
        elif not item.imagem_path:
            form.imagem.errors.append("Envie uma imagem para a galeria.")
            return render_template("admin/galeria/form.html", form=form, item=item)
        try:
            db.session.commit()
            flash("Item da galeria atualizado com sucesso.", "success")
            return redirect(url_for("admin.galeria_list"))
        except IntegrityError:
            db.session.rollback()
            flash("Erro ao atualizar item da galeria. Verifique se o slug já está em uso.", "danger")
    return render_template("admin/galeria/form.html", form=form, item=item)


@admin_bp.route("/galeria/<int:item_id>/excluir", methods=["POST"])
@login_required
def galeria_delete(item_id: int):
    item = Galeria.query.get_or_404(item_id)
    _delete_file(item.imagem_path)
    db.session.delete(item)
    db.session.commit()
    flash("Item da galeria excluído com sucesso.", "success")
    return redirect(url_for("admin.galeria_list"))


# ----- Transparência -----


@admin_bp.route("/transparencia")
@login_required
def transparencia_list():
    itens = Transparencia.query.order_by(Transparencia.created_at.desc()).all()
    return render_template("admin/transparencia/list.html", itens=itens)


@admin_bp.route("/transparencia/criar", methods=["GET", "POST"])
@login_required
def transparencia_create():
    form = TransparenciaForm()
    if form.validate_on_submit():
        if not form.arquivo.data:
            form.arquivo.errors.append("Envie um arquivo PDF.")
        else:
            item = Transparencia(
                titulo=form.titulo.data,
                slug=form.slug.data,
                descricao=form.descricao.data,
                publicado_em=_combine_date_with_min_time(form.publicado_em.data) or datetime.utcnow(),
                arquivo_path=_save_file(form.arquivo.data, current_app.config["DOC_UPLOAD_FOLDER"]),
            )
            db.session.add(item)
            try:
                db.session.commit()
                flash("Documento de transparência criado com sucesso.", "success")
                return redirect(url_for("admin.transparencia_list"))
            except IntegrityError:
                db.session.rollback()
                flash("Erro ao salvar documento. Verifique se o slug já está em uso.", "danger")
    return render_template("admin/transparencia/form.html", form=form, item=None)


@admin_bp.route("/transparencia/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
def transparencia_edit(item_id: int):
    item = Transparencia.query.get_or_404(item_id)
    form = TransparenciaForm(obj=item)
    if item.publicado_em:
        form.publicado_em.data = item.publicado_em.date()
    if form.validate_on_submit():
        item.titulo = form.titulo.data
        item.slug = form.slug.data
        item.descricao = form.descricao.data
        item.publicado_em = _combine_date_with_min_time(form.publicado_em.data) or item.publicado_em
        if form.arquivo.data:
            _delete_file(item.arquivo_path)
            item.arquivo_path = _save_file(form.arquivo.data, current_app.config["DOC_UPLOAD_FOLDER"])
        elif not item.arquivo_path:
            form.arquivo.errors.append("Envie um arquivo PDF.")
            return render_template("admin/transparencia/form.html", form=form, item=item)
        try:
            db.session.commit()
            flash("Documento de transparência atualizado com sucesso.", "success")
            return redirect(url_for("admin.transparencia_list"))
        except IntegrityError:
            db.session.rollback()
            flash("Erro ao atualizar documento. Verifique se o slug já está em uso.", "danger")
    return render_template("admin/transparencia/form.html", form=form, item=item)


@admin_bp.route("/transparencia/<int:item_id>/excluir", methods=["POST"])
@login_required
def transparencia_delete(item_id: int):
    item = Transparencia.query.get_or_404(item_id)
    _delete_file(item.arquivo_path)
    db.session.delete(item)
    db.session.commit()
    flash("Documento de transparência excluído com sucesso.", "success")
    return redirect(url_for("admin.transparencia_list"))
