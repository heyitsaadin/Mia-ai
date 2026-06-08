import os
import requests
import base64
import json as _json_mod
import io as _io
from PIL import Image as PILImage
from urllib.parse import quote

def compress_image(raw_bytes, max_kb=2000):
    img = PILImage.open(_io.BytesIO(raw_bytes)).convert("RGB")
    initial_buf = _io.BytesIO()
    img.save(initial_buf, format="JPEG", quality=95)
    if initial_buf.tell() < max_kb * 1024:
        return initial_buf.getvalue()
    quality = 85
    max_iterations = 10
    last_size = float('inf')
    best_buf = initial_buf
    for _ in range(max_iterations):
        buf = _io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        size = buf.tell()
        if size < max_kb * 1024:
            return buf.getvalue()
        if last_size - size < 5000:
            best_buf = buf
            break
        last_size = size
        best_buf = buf
        quality -= 10
    if best_buf.tell() > max_kb * 1024:
        ratio = (max_kb * 1024) / best_buf.tell()
        new_size = (int(img.width * ratio**0.5), int(img.height * ratio**0.5))
        img.thumbnail(new_size, PILImage.Resampling.LANCZOS)
        buf = _io.BytesIO()
        img.save(buf, format="JPEG", quality=70, optimize=True)
        return buf.getvalue()
    return best_buf.getvalue()

def _img_html(src, prompt):
    escaped = prompt.replace("'", "\\'")
    return (
        f'<div class="jarvis-img-wrap">'
        f'<img src="{src}" alt="{prompt}" class="jarvis-img" '
        f'onload="this.classList.add(\'loaded\')" '
        f'onerror="this.parentElement.innerHTML=\'❌ Could not generate image. Try a different prompt.\'">'
        f'<div class="jarvis-img-footer">'
        f'<span class="jarvis-img-caption">🎨 {prompt}</span>'
        f'<button onclick="downloadImage(\'{src}\',\'{escaped}\')" class="jarvis-img-dl">'
        f'&#8203;'
        f'</button>'
        f'</div>'
        f'</div>'
    )

def _try_huggingface(prompt):
    HF_API_KEY = os.environ.get("HF_API_KEY", "")
    if not HF_API_KEY:
        return None
    try:
        resp = requests.post(
            "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell",
            headers={"Authorization": f"Bearer {HF_API_KEY}"},
            json={"inputs": prompt},
            timeout=60
        )
        if resp.status_code == 200 and resp.content:
            b64 = base64.b64encode(resp.content).decode("utf-8")
            return _img_html(f"data:image/jpeg;base64,{b64}", prompt)
    except Exception as e:
        print(f"[IMG][HF] exception: {e}")
    return None

def _try_stable_horde(prompt):
    import time as _time
    api_key = os.environ.get("HORDE_API_KEY", "0000000000")
    try:
        submit = requests.post(
            "https://stablehorde.net/api/v2/generate/async",
            headers={"apikey": api_key, "Content-Type": "application/json"},
            json={
                "prompt": prompt,
                "params": {"sampler_name": "k_euler", "cfg_scale": 7,
                           "steps": 20, "width": 512, "height": 512, "n": 1},
                "models": ["Deliberate", "stable_diffusion"],
                "r2": True, "nsfw": False,
            },
            timeout=20
        )
        if submit.status_code != 202:
            return None
        job_id = submit.json().get("id")
        if not job_id:
            return None
        for _ in range(18):
            _time.sleep(5)
            check  = requests.get(f"https://stablehorde.net/api/v2/generate/check/{job_id}",
                                  headers={"apikey": api_key}, timeout=10)
            if check.json().get("done"):
                break
        else:
            return None
        result      = requests.get(f"https://stablehorde.net/api/v2/generate/status/{job_id}",
                                   headers={"apikey": api_key}, timeout=15)
        generations = result.json().get("generations", [])
        if not generations:
            return None
        img_url = generations[0].get("img", "")
        if not img_url:
            return None
        img_resp = requests.get(img_url, timeout=30)
        if img_resp.status_code == 200:
            b64 = base64.b64encode(img_resp.content).decode("utf-8")
            ct  = img_resp.headers.get("content-type", "image/webp")
            ext = "png" if "png" in ct else "jpeg" if "jpeg" in ct else "webp"
            return _img_html(f"data:image/{ext};base64,{b64}", prompt)
    except Exception as e:
        print(f"[IMG][Horde] exception: {e}")
    return None

def generate_image(prompt):
    html = _try_huggingface(prompt)
    if html:
        return html
    html = _try_stable_horde(prompt)
    if html:
        return html
    return "❌ Image generation failed - all providers unavailable right now. Try again in a moment."
