from flask import Blueprint, render_template, request, redirect, session, jsonify
from app.models import get_chat_sessions, log_visit
from app.utils.helpers import get_greeting
import os

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    if "user" in session:
        return redirect("/landing")
    return render_template("login.html")

@main_bp.route("/landing")
def landing():
    if "user" not in session:
        return redirect("/")
    username = session["user"]
    sessions = get_chat_sessions(username)
    log_visit()
    return render_template("landing.html", username=username, sessions=sessions)

@main_bp.route("/chat")
def chat():
    if "user" not in session:
        return redirect("/")
    return render_template("chat.html", username=session["user"])

@main_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")
