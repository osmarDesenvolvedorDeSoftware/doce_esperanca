from flask import Blueprint


public_bp = Blueprint("public", __name__)
admin_bp = Blueprint("admin", __name__)


@public_bp.route("/")
def index():
    return "Public Home"


@admin_bp.route("/")
def admin_index():
    return "Admin Home"
