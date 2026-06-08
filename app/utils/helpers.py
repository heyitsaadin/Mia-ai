import ast
from datetime import datetime

def safe_eval(expr):
    expr = expr.replace("×", "*").replace("÷", "/").replace(" x ", "*").strip()
    try:
        tree = ast.parse(expr, mode='eval')
        allowed_nodes = (
            ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
            ast.FloorDiv, ast.USub, ast.UAdd
        )
        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise ValueError("Invalid expression")
        return eval(compile(tree, "<string>", "eval"), {"__builtins__": {}}, {})
    except (ValueError, SyntaxError, ZeroDivisionError):
        raise ValueError("Invalid expression")

def contains_bad_words(text, bad_words):
    return any(word in text.lower() for word in bad_words)

def get_greeting(username, IST):
    hour = datetime.now(IST).hour
    period = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
    greetings = [
        f"Good {period}, {username}! 😊 Hope you're having a great one — what's on your mind?",
        f"Hey {username}! 👋 Good {period} to you! Ready to help whenever you are.",
        f"Good {period}, {username}! ✨ Great to see you — what can Jarvis do for you today?",
        f"Hey hey, {username}! 🌟 Good {period}! I'm all ears — what do you need?",
        f"Good {period}, {username}! 🤖 Jarvis online and ready. What's up?",
    ]
    return greetings[datetime.now(IST).minute % len(greetings)]
