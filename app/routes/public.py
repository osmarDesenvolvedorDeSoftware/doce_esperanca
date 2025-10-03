from __future__ import annotations

from flask import Blueprint, render_template

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    return render_template("public/index.html")
