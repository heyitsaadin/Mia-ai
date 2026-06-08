import os
import re
import requests
import json as _json_mod
from app.models import save_chat_session

def _build_clean_history(history):
    last_img_prompt = ""
    last_img_analysis = ""
    for msg in reversed(history):
        txt = msg.get("text", "")
        if not last_img_prompt and "[I generated an image:" in txt:
            m = re.search(r'\[I generated an image: (.*?)\]', txt)
            if m: last_img_prompt = m.group(1).strip()
        if not last_img_analysis and "[IMAGE ANALYSIS RESULT]" in txt:
            last_img_analysis = txt[len("[IMAGE ANALYSIS RESULT]"):].strip()
        if last_img_prompt and last_img_analysis:
            break

    def _to_entry(msg):
        txt = msg.get("text", "")
        if "[I generated an image:" in txt:
            m = re.search(r'\[I generated an image: (.*?)\]', txt)
            img_prompt = m.group(1).strip() if m else "an image"
            return {"role": "assistant", "content": f"[I generated an image: {img_prompt}]"}
        if txt.startswith("[IMAGE ANALYSIS RESULT]"):
            return None
        if txt.startswith("[IMAGE EDITED:") or txt.startswith("__EDITED_IMAGE__"):
            return {"role": "assistant", "content": "[I edited the image as requested.]"}
        if txt.startswith("[YOUTUBE VIDEO:"):
            title = txt[len("[YOUTUBE VIDEO:"):].rstrip("]").strip()
            return {"role": "assistant", "content": f"[I found a YouTube video: {title}]"}
        if re.match(r'^\[(image|2 images) uploaded\]', txt, re.IGNORECASE):
            role = "user" if msg["sender"] == "You" else "assistant"
            return {"role": role, "content": txt[:120]}
        role = "user" if msg["sender"] == "You" else "assistant"
        return {"role": role, "content": txt}

    all_entries = [e for e in (_to_entry(m) for m in history) if e]
    if not all_entries:
        return [], last_img_prompt, last_img_analysis

    SOFT_LIMIT = 1200
    WINDOW_MIN = 4
    MSG_CAP    = 250
    capped = [{"role": e["role"], "content": e["content"][:MSG_CAP]} for e in all_entries]
    total_chars = sum(len(e["content"]) for e in capped)

    if total_chars <= SOFT_LIMIT:
        clean_msgs = capped
    else:
        clean_msgs = list(capped[-WINDOW_MIN:])
        first_user = next((e for e in capped if e["role"] == "user"), None)
        if first_user and first_user not in clean_msgs:
            clean_msgs = [first_user] + clean_msgs

    return clean_msgs, last_img_prompt, last_img_analysis

def ask_jarvis_brain(prompt, history=None):
    if history is None: history = []
    API_KEY = os.environ.get("GROQ_API_KEY")
    if not API_KEY:
        return {"action": "text", "reply": "Groq API key not configured.", "image_prompt": "", "high_quality": False, "wants_code": False, "youtube_plus_text": ""}
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}
    clean_msgs, last_img_prompt, last_img_analysis = _build_clean_history(history)
    
    system_msg = (
        "You are Jarvis, a personal AI assistant made by Aadin. Be warm, friendly, conversational. "
        "RESPOND ONLY IN THIS JSON: {\"action\":\"text\",\"reply\":\"\",\"image_prompt\":\"\",\"high_quality\":false,\"wants_code\":false,\"youtube_plus_text\":\"\"}"
    )
    
    messages = [{"role": "system", "content": system_msg}]
    messages.extend(clean_msgs)
    messages.append({"role": "user", "content": prompt})
    data = {"model": "llama-3.1-8b-instant", "messages": messages, "max_tokens": 400}
    
    try:
        raw = requests.post(url, headers=headers, json=data, timeout=20).json()
        raw_text = raw['choices'][0]['message']['content'].strip()
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        parsed = _json_mod.loads(raw_text)
        return parsed
    except Exception:
        return {"action": "text", "reply": "I'm having a moment - try again! 😅"}

def ask_jarvis(prompt, history=None, wants_code=False):
    if history is None: history = []
    API_KEY = os.environ.get("GROQ_API_KEY")
    if not API_KEY: return "Groq API key not configured."
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}
    
    system_msg = f"You are Jarvis, a personal AI assistant created by Aadin. Be warm and friendly."
    clean_msgs, last_img_prompt, last_img_analysis = _build_clean_history(history)
    
    messages = [{"role": "system", "content": system_msg}]
    messages.extend(clean_msgs)
    messages.append({"role": "user", "content": prompt})
    data = {"model": "llama-3.1-8b-instant", "messages": messages, "max_tokens": 512}
    
    try:
        res = requests.post(url, headers=headers, json=data, timeout=20).json()
        return res['choices'][0]['message']['content']
    except Exception:
        return "I'm having a moment — try again! 😅"
