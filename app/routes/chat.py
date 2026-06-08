from flask import Blueprint, request, session, jsonify
from app.services.jarvis_service import ask_jarvis, ask_jarvis_brain
from app.models import save_chat_session, get_chat_sessions, delete_chat_session
import json

chat_bp = Blueprint('chat_routes', __name__)

@chat_bp.route("/ask", methods=["POST"])
def ask():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    prompt = data.get("prompt")
    history = data.get("history", [])
    
    # This is a simplified version of the logic in app.py
    # In a full refactor, we would move the complex _build_reply logic here
    response = ask_jarvis(prompt, history)
    
    return jsonify({"reply": response})

@chat_bp.route("/get_sessions")
def get_sessions():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify(get_chat_sessions(session["user"]))

@chat_bp.route("/delete_session", methods=["POST"])
def delete_session():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403
    session_key = request.json.get("session_key")
    delete_chat_session(session["user"], session_key)
    return jsonify({"status": "success"})
