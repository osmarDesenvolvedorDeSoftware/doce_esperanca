from __future__ import annotations

import os
from datetime import date, datetime, time
from pathlib import Path
from typing import Iterable, Optional

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

from app import db, login_manager
from app.forms import (
    ApoioForm,
    GaleriaForm,
    LoginForm,
    ParceiroForm,
    TextoInstitucionalForm,
    TransparenciaForm,
    VoluntarioForm,
)
from app.models import Apoio, Galeria, Parceiro, TextoInstitucional, Transparencia, User, Voluntario

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _save_file(field_storage, base_folder: str) -> Optional[str]:
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
    field_storage.save(file_path)

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
    textos = TextoInstitucional.query.order_by(TextoInstitucional.created_at.desc()).all()
    return render_template("admin/textos/list.html", textos=textos)


@admin_bp.route("/textos/criar", methods=["GET", "POST"])
@login_required
def textos_create():
    form = TextoInstitucionalForm()
    if form.validate_on_submit():
        texto = TextoInstitucional(
            titulo=form.titulo.data,
            slug=form.slug.data,
            resumo=form.resumo.data,
            conteudo=form.conteudo.data,
        )
        if form.imagem.data:
            relative_path = _save_file(form.imagem.data, current_app.config["IMAGE_UPLOAD_FOLDER"])
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
    texto = TextoInstitucional.query.get_or_404(texto_id)
    form = TextoInstitucionalForm(obj=texto)
    if request.method == "GET":
        form.conteudo.data = texto.conteudo
    if form.validate_on_submit():
        texto.titulo = form.titulo.data
        texto.slug = form.slug.data
        texto.resumo = form.resumo.data
        texto.conteudo = form.conteudo.data

        if form.imagem.data:
            _delete_file(texto.imagem_path)
            texto.imagem_path = _save_file(form.imagem.data, current_app.config["IMAGE_UPLOAD_FOLDER"])

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
    if form.validate_on_submit():
        if not form.imagem.data:
            form.imagem.errors.append("Envie uma imagem para a galeria.")
        else:
            item = Galeria(
                titulo=form.titulo.data,
                slug=form.slug.data,
                descricao=form.descricao.data,
                publicado_em=_combine_date_with_min_time(form.publicado_em.data) or datetime.utcnow(),
                imagem_path=_save_file(form.imagem.data, current_app.config["IMAGE_UPLOAD_FOLDER"]),
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
    if item.publicado_em:
        form.publicado_em.data = item.publicado_em.date()
    if form.validate_on_submit():
        item.titulo = form.titulo.data
        item.slug = form.slug.data
        item.descricao = form.descricao.data
        item.publicado_em = _combine_date_with_min_time(form.publicado_em.data) or item.publicado_em
        if form.imagem.data:
            _delete_file(item.imagem_path)
            item.imagem_path = _save_file(form.imagem.data, current_app.config["IMAGE_UPLOAD_FOLDER"])
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
