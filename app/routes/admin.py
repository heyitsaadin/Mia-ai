from flask import Blueprint, render_template, request, redirect, session, jsonify
from app.models import get_all_bans, get_user, log_visit
import os

admin_bp = Blueprint('admin', __name__)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
ADMIN_SLUG = os.environ.get("ADMIN_SLUG", "x7k2mq9p")
ADMIN_BASE = f"/admin/{ADMIN_SLUG}"

@admin_bp.route(ADMIN_BASE, methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(ADMIN_BASE)
        return render_template("admin.html", error="Invalid password")
    
    if not session.get("admin"):
        return render_template("admin.html")
    
    bans = get_all_bans()
    return render_template("admin.html", bans=bans, logged_in=True)

@admin_bp.route(f"{ADMIN_BASE}/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(ADMIN_BASE)
