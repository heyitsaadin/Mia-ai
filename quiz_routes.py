"""
─────────────────────────────────────────────────────
  JARVIS QUIZ — paste these routes into app.py
  BEFORE the  init_db()  line at the bottom.

  Also add to your requirements.txt / install:
      pip install pdfplumber
─────────────────────────────────────────────────────
"""

import json as _json
import pdfplumber


# ──────────────────────────────────────────────
# QUIZ PAGE
# ──────────────────────────────────────────────

@app.route("/quiz")
def quiz():
    """Serves the quiz playground page."""
    if "user" not in session:
        return redirect("/")
    heartbeat(session["user"])
    return render_template("quiz.html", username=session["user"])


# ──────────────────────────────────────────────
# GENERATE QUIZ FROM PDF
# ──────────────────────────────────────────────

@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    """
    Accepts a PDF upload, extracts its text,
    sends it to Groq (llama-3.1-8b-instant) and asks it
    to produce 10 MCQ questions as a JSON array.
    Returns: { "questions": [ ... ] }  or  { "error": "..." }
    """
    if "user" not in session:
        return _json.dumps({"error": "not_logged_in"}), 401, {"Content-Type": "application/json"}

    heartbeat(session["user"])

    # ── 1. Receive PDF ──
    pdf_file = request.files.get("pdf")
    if not pdf_file or not pdf_file.filename.lower().endswith(".pdf"):
        return _json.dumps({"error": "Please upload a valid PDF file."}), 400, {"Content-Type": "application/json"}

    # ── 2. Extract text with pdfplumber ──
    try:
        with pdfplumber.open(pdf_file) as pdf:
            pages_text = []
            for page in pdf.pages[:20]:          # cap at 20 pages
                t = page.extract_text()
                if t:
                    pages_text.append(t)
        raw_text = "\n".join(pages_text).strip()
    except Exception as e:
        return _json.dumps({"error": f"Could not read PDF: {str(e)}"}), 400, {"Content-Type": "application/json"}

    if not raw_text or len(raw_text) < 100:
        return _json.dumps({"error": "PDF appears to be empty or image-only. Please use a text-based PDF."}), 400, {"Content-Type": "application/json"}

    # Truncate to ~6000 chars so we stay within token limits
    study_material = raw_text[:6000]

    # ── 3. Ask Groq to generate MCQs ──
    API_KEY = os.environ["GROQ_API_KEY"]
    url     = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}

    system_prompt = """You are a professional exam question generator.
Your ONLY job is to read the study material provided and return exactly 10 multiple-choice questions as a raw JSON array.

Rules:
- Return ONLY a valid JSON array. No explanation, no markdown, no code fences.
- Each element must have exactly these keys:
    "question"    : the question string
    "options"     : an array of exactly 4 strings (the choices)
    "answer"      : the EXACT string from options that is correct
    "explanation" : a 1-2 sentence explanation of why the answer is correct
- Questions must be based strictly on the provided material.
- Vary difficulty: mix easy, medium, and hard questions.
- Never repeat questions."""

    user_prompt = f"Study material:\n\n{study_material}\n\nGenerate 10 MCQ questions."

    data = {
        "model":      "llama-3.1-8b-instant",
        "messages":   [
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_prompt}
        ],
        "max_tokens": 2048,
        "temperature": 0.4,
    }

    try:
        res = requests.post(url, headers=headers, json=data, timeout=40)
        raw = res.json()["choices"][0]["message"]["content"].strip()

        # Strip any accidental markdown fences
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip().rstrip("`").strip()

        questions = _json.loads(raw)

        # Basic validation
        if not isinstance(questions, list) or len(questions) == 0:
            raise ValueError("Empty or invalid question list")

        return _json.dumps({"questions": questions}), 200, {"Content-Type": "application/json"}

    except _json.JSONDecodeError:
        return _json.dumps({"error": "AI returned an invalid response. Please try again."}), 500, {"Content-Type": "application/json"}
    except Exception as e:
        return _json.dumps({"error": f"Quiz generation failed: {str(e)}"}), 500, {"Content-Type": "application/json"}
