"""
m(video)p - Generate product demo videos from just an idea
"""
import os
import json
import requests
import subprocess
import tempfile
import uuid
import time
import base64
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, send_file, Response
from dotenv import load_dotenv

import db
from providers import (
    get_image_provider,
    get_video_provider,
    list_providers,
    ImageData,
    GenerationTask,
)
from providers.llm import (
    get_llm_provider,
    list_llm_providers,
    get_available_llm_providers,
    Message,
)
from consistency import ConsistencyManager, SubjectType, ConfidenceLevel, PromptAssembler

# Global consistency managers by session_id
_consistency_managers: dict[str, ConsistencyManager] = {}


def get_consistency_manager(session_id: str) -> ConsistencyManager:
    """Get or create a ConsistencyManager for a session."""
    if session_id not in _consistency_managers:
        _consistency_managers[session_id] = ConsistencyManager(session_id=session_id)
    return _consistency_managers[session_id]

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============ Image Cache for base64 images ============
# Google provider returns base64, but we need URLs for some operations
_image_cache: dict[str, tuple[bytes, str, float]] = {}  # cache_id -> (bytes, mime_type, timestamp)
IMAGE_CACHE_TTL = 3600  # 1 hour

# ============ Persisted Images Directory ============
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "data", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)


def cache_image(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """Cache image bytes and return a URL path to serve them."""
    cache_id = uuid.uuid4().hex[:16]
    _image_cache[cache_id] = (image_bytes, mime_type, time.time())
    # Clean up old entries
    _cleanup_image_cache()
    return f"/api/images/{cache_id}"


def _cleanup_image_cache():
    """Remove expired cache entries."""
    now = time.time()
    expired = [k for k, v in _image_cache.items() if now - v[2] > IMAGE_CACHE_TTL]
    for k in expired:
        del _image_cache[k]


@app.route("/api/images/<cache_id>")
def serve_cached_image(cache_id):
    """Serve a cached image by its ID."""
    if cache_id not in _image_cache:
        return jsonify({"error": "Image not found or expired"}), 404

    image_bytes, mime_type, _ = _image_cache[cache_id]
    return Response(image_bytes, mimetype=mime_type)


# ============ Persisted Image Functions ============

def persist_image(image_data, video_id=None, frame_num=None, original_url=None):
    """
    Persist an image to disk and database.

    Args:
        image_data: Either a URL string, base64 string, or raw bytes
        video_id: Optional associated video ID
        frame_num: Optional frame number (1-4)
        original_url: Optional original URL (if image_data is bytes/base64)

    Returns:
        Tuple of (image_id, url_path)
    """
    image_bytes = None
    mime_type = "image/png"

    if isinstance(image_data, bytes):
        image_bytes = image_data
    elif isinstance(image_data, str):
        if image_data.startswith("data:"):
            # Data URL: data:image/png;base64,xxx
            header, b64_data = image_data.split(",", 1)
            if "image/jpeg" in header or "image/jpg" in header:
                mime_type = "image/jpeg"
            elif "image/webp" in header:
                mime_type = "image/webp"
            image_bytes = base64.b64decode(b64_data)
        elif image_data.startswith("/api/images/"):
            # Local cached image - get from cache
            cache_id = image_data.split("/")[-1]
            if cache_id in _image_cache:
                image_bytes, mime_type, _ = _image_cache[cache_id]
            else:
                raise ValueError(f"Cached image not found: {cache_id}")
        elif image_data.startswith("http://") or image_data.startswith("https://"):
            # Remote URL - download
            original_url = original_url or image_data
            resp = requests.get(image_data, timeout=60)
            resp.raise_for_status()
            image_bytes = resp.content
            content_type = resp.headers.get("content-type", "image/png")
            if "jpeg" in content_type or "jpg" in content_type:
                mime_type = "image/jpeg"
            elif "webp" in content_type:
                mime_type = "image/webp"
            elif "png" in content_type:
                mime_type = "image/png"
        else:
            # Assume raw base64
            image_bytes = base64.b64decode(image_data)

    if not image_bytes:
        raise ValueError("Could not extract image bytes from provided data")

    # Determine file extension
    ext = ".png"
    if mime_type == "image/jpeg":
        ext = ".jpg"
    elif mime_type == "image/webp":
        ext = ".webp"

    # Save to disk
    image_id = uuid.uuid4().hex
    filename = f"{image_id}{ext}"
    file_path = os.path.join(IMAGES_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(image_bytes)

    # Save to database
    db.create_persisted_image(
        file_path=file_path,
        video_id=video_id,
        frame_number=frame_num,
        original_url=original_url,
        mime_type=mime_type
    )

    return image_id, f"/api/images/persisted/{image_id}"


@app.route("/api/images/persisted/<image_id>")
def serve_persisted_image(image_id):
    """Serve a persisted image by its ID."""
    # Look up in database
    image_record = db.get_persisted_image(image_id)
    if not image_record:
        # Also check if it's a raw filename (legacy support)
        for ext in [".png", ".jpg", ".webp"]:
            file_path = os.path.join(IMAGES_DIR, f"{image_id}{ext}")
            if os.path.exists(file_path):
                mime_type = "image/png" if ext == ".png" else "image/jpeg" if ext == ".jpg" else "image/webp"
                return send_file(file_path, mimetype=mime_type)
        return jsonify({"error": "Image not found"}), 404

    file_path = image_record["file_path"]
    if not os.path.exists(file_path):
        return jsonify({"error": "Image file missing"}), 404

    return send_file(file_path, mimetype=image_record.get("mime_type", "image/png"))


@app.route("/api/images/persist/<cache_id>", methods=["POST"])
def persist_cached_image(cache_id):
    """Persist a cached (in-memory) image to disk."""
    if cache_id not in _image_cache:
        return jsonify({"error": "Cached image not found or expired"}), 404

    data = request.json or {}
    video_id = data.get("video_id")
    frame_num = data.get("frame_number")

    try:
        image_bytes, mime_type, _ = _image_cache[cache_id]
        image_id, url = persist_image(
            image_bytes,
            video_id=video_id,
            frame_num=frame_num,
            original_url=f"/api/images/{cache_id}"
        )
        return jsonify({"image_id": image_id, "url": url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/images/upload", methods=["POST"])
def upload_image():
    """Upload a custom image via multipart form."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    video_id = request.form.get("video_id")
    frame_num = request.form.get("frame_number")
    if frame_num:
        frame_num = int(frame_num)

    # Determine mime type from filename
    filename = file.filename.lower()
    if filename.endswith(".jpg") or filename.endswith(".jpeg"):
        mime_type = "image/jpeg"
        ext = ".jpg"
    elif filename.endswith(".webp"):
        mime_type = "image/webp"
        ext = ".webp"
    else:
        mime_type = "image/png"
        ext = ".png"

    try:
        image_bytes = file.read()
        image_id, url = persist_image(
            image_bytes,
            video_id=video_id,
            frame_num=frame_num
        )
        return jsonify({"image_id": image_id, "url": url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ Export/Import Endpoints ============

def _fetch_image_as_base64(url):
    """Fetch an image URL and return base64 data with mime type."""
    if url.startswith("/api/images/"):
        # Local image - could be cached or persisted
        parts = url.split("/")
        image_id = parts[-1]

        # Check persisted first
        if "persisted" in url:
            image_record = db.get_persisted_image(image_id)
            if image_record and os.path.exists(image_record["file_path"]):
                with open(image_record["file_path"], "rb") as f:
                    image_bytes = f.read()
                mime_type = image_record.get("mime_type", "image/png")
                return base64.b64encode(image_bytes).decode(), mime_type

        # Check cache
        if image_id in _image_cache:
            image_bytes, mime_type, _ = _image_cache[image_id]
            return base64.b64encode(image_bytes).decode(), mime_type

        # Try persisted by ID
        for ext in [".png", ".jpg", ".webp"]:
            file_path = os.path.join(IMAGES_DIR, f"{image_id}{ext}")
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    image_bytes = f.read()
                mime_type = "image/png" if ext == ".png" else "image/jpeg" if ext == ".jpg" else "image/webp"
                return base64.b64encode(image_bytes).decode(), mime_type

        return None, None

    elif url.startswith("http://") or url.startswith("https://"):
        # Remote URL
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/png")
            if "jpeg" in content_type or "jpg" in content_type:
                mime_type = "image/jpeg"
            elif "webp" in content_type:
                mime_type = "image/webp"
            else:
                mime_type = "image/png"
            return base64.b64encode(resp.content).decode(), mime_type
        except Exception as e:
            print(f"Failed to fetch image from {url}: {e}")
            return None, None

    return None, None


@app.route("/api/export/script/<video_id>")
def export_script(video_id):
    """Export just the script as JSON (for quick copy/paste)."""
    video = db.get_video(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    if not video.get("script"):
        return jsonify({"error": "No script found for this video"}), 404

    return jsonify({
        "script": video["script"],
        "video_id": video_id
    })


@app.route("/api/export/bundle/<video_id>")
def export_bundle(video_id):
    """Export full bundle with script and base64-encoded images."""
    video = db.get_video(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    if not video.get("script"):
        return jsonify({"error": "No script found for this video"}), 404

    script = video["script"]
    keyframe_urls = video.get("keyframe_urls", {})

    # Get session info for name
    sess = db.get_session(video.get("session_id")) if video.get("session_id") else None
    name = sess.get("name") if sess else script.get("title", "Untitled")

    # Fetch and encode images
    images = {}
    for frame_num, url in keyframe_urls.items():
        if url:
            b64_data, mime_type = _fetch_image_as_base64(url)
            if b64_data:
                images[str(frame_num)] = {
                    "data": b64_data,
                    "mime_type": mime_type
                }

    bundle = {
        "version": "1.0",
        "type": "script-with-images",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "name": name,
        "script": script,
        "images": images
    }

    return jsonify(bundle)


@app.route("/api/import/bundle", methods=["POST"])
def import_bundle():
    """
    Import a bundle (script + optional images).

    Creates a new session and video record, persists images locally.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate bundle format
    if data.get("type") not in ["script-with-images", "script-only", None]:
        return jsonify({"error": "Invalid bundle type"}), 400

    script = data.get("script")
    if not script:
        return jsonify({"error": "No script in bundle"}), 400

    images_data = data.get("images", {})
    name = data.get("name") or script.get("title", "Imported Script")

    # Create new session
    session_id = db.create_session(name=name)

    # Create video record
    video_id = db.create_video(session_id, script=script)

    # Persist images
    keyframe_urls = {}
    for frame_num, img_info in images_data.items():
        try:
            if isinstance(img_info, dict):
                # New format: {"data": "base64...", "mime_type": "image/png"}
                b64_data = img_info.get("data", "")
                mime_type = img_info.get("mime_type", "image/png")
                # Reconstruct data URL
                image_data = f"data:{mime_type};base64,{b64_data}"
            else:
                # Legacy: raw base64 or URL
                image_data = img_info

            image_id, url = persist_image(
                image_data,
                video_id=video_id,
                frame_num=int(frame_num)
            )
            keyframe_urls[str(frame_num)] = url
        except Exception as e:
            print(f"Failed to persist image for frame {frame_num}: {e}")

    # Update video with keyframe URLs
    if keyframe_urls:
        db.update_video(video_id, keyframe_urls=keyframe_urls)

    # Update Flask session - only store session_id, not conversation (to avoid cookie overflow)
    session["session_id"] = session_id
    session.modified = True

    return jsonify({
        "video_id": video_id,
        "session_id": session_id,
        "keyframe_urls": keyframe_urls,
        "message": f"Imported bundle with {len(keyframe_urls)} images"
    })


# ============ Task Registry for polling ============
# Store GenerationTask objects for async polling
_task_registry: dict[str, GenerationTask] = {}


def register_task(task: GenerationTask) -> str:
    """Register a task for later polling."""
    _task_registry[task.task_id] = task
    return task.task_id


def get_task(task_id: str) -> GenerationTask | None:
    """Get a registered task by ID."""
    return _task_registry.get(task_id)


def remove_task(task_id: str):
    """Remove a completed task from registry."""
    _task_registry.pop(task_id, None)


# System prompt for context gathering
SYSTEM_PROMPT = """You are a product strategist helping someone create a demo video for their product idea. Your goal is to deeply understand their product so you can help generate a compelling demo video.

IMPORTANT: Keep all suggestions GROUNDED IN REALITY.
- Users are building products they could launch soon - demos must feel credible and believable
- Avoid overly futuristic or sci-fi aesthetics - they reduce credibility for real product demos
- Visual suggestions should feel like "a product launching in 2026" not "a product from 2050"
- If the user's idea IS futuristic, frame it as near future (next few years), not science fiction

IMPORTANT APPROACH:
1. When the user describes their idea, immediately make EDUCATED GUESSES about aspects they haven't mentioned
2. Present your assumptions clearly, then ask targeted follow-up questions
3. Be conversational and natural - like a smart co-founder brainstorming

For each response, you MUST output valid JSON with this STRUCTURED format:
{
  "response_type": "structured",
  "message": "Your brief conversational response (1-2 sentences max)",
  "questions": [
    {
      "id": "q1",
      "label": "Short Label",
      "question": "Your specific question?",
      "placeholder": "Example answer hint..."
    }
  ],
  "assumptions": [
    {
      "id": "a1",
      "text": "Assumption text",
      "confidence": "high|medium|low",
      "status": "pending"
    }
  ],
  "quick_actions": [
    {
      "id": "action_id",
      "label": "Button Label",
      "action": "action_type",
      "primary": false
    }
  ],
  "product_understanding": {
    "name": "Product name (your guess if not provided)",
    "tagline": "One-line description",
    "problem": "The problem it solves",
    "solution": "How it solves it",
    "target_user": "Who it's for",
    "key_features": ["feature1", "feature2", "feature3"],
    "tone": "Professional/Playful/Technical/etc",
    "visual_style": "Minimal/Bold/Corporate/Startup/Modern/Clean/Professional - keep it realistic"
  },
  "confidence": 0.0 to 1.0,
  "ready_for_video": true/false
}

RESPONSE FORMAT RULES:
- "response_type": Always "structured" for main responses, use "simple" only for very brief confirmations
- "message": Keep SHORT (1-2 sentences). Don't repeat questions in the message.
- "questions": 1-2 questions max per turn. Each needs id, label, question, placeholder.
- "assumptions": Convert your guesses into structured assumptions with confidence level.
- "quick_actions": Add contextual buttons. Common actions:
  - {"id": "generate", "label": "Generate script", "action": "trigger_generation", "primary": true} - when ready
  - {"id": "add_details", "label": "Add more details", "action": "add_details", "primary": false}
  - {"id": "continue", "label": "Continue", "action": "continue_conversation", "primary": false}
- When confidence > 0.8 and ready_for_video=true, include the "Generate script" action as primary.

IMPORTANT CONSTRAINTS:
1. Videos are 3 segments of 5 seconds each (15s total) - focus on ONE killer moment per segment.
2. AI video CANNOT render text AT ALL. NEVER include any text, words, letters, numbers, or UI with readable content. Instead use:
   - Clean visual metaphors: light effects, smooth transitions, color shifts
   - Symbolic representations: icons transform, objects morph, energy flows
   - Human emotions/reactions: faces, gestures, body language
   - Environmental storytelling: lighting changes, camera movement, atmosphere shifts
   - NO screens showing text, NO text overlays, NO written words of any kind
3. Keep visuals REALISTIC and TANGIBLE - avoid overly abstract floating shapes or ethereal cosmic imagery

Start with LOW confidence and build up as you learn more. Mark ready_for_video=true only when confidence > 0.8 and you have enough detail for a compelling 10-second demo.

Be concise. Make bold guesses - it's easier for users to correct than to describe from scratch."""


def chat_with_llm(conversation_history, provider_name=None, model=None):
    """Send conversation to the configured LLM provider."""

    # Get provider from session or parameter
    if provider_name is None:
        provider_name = session.get("llm_provider", os.getenv("LLM_PROVIDER", "gemini"))
    if model is None:
        model = session.get("llm_model")

    try:
        provider = get_llm_provider(provider_name)
    except ValueError as e:
        return {
            "message": f"LLM provider error: {str(e)}",
            "product_understanding": {},
            "confidence": 0.0,
            "ready_for_video": False,
            "assumptions_made": [],
            "error": str(e)
        }

    # Build messages with system prompt
    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
    ]

    for msg in conversation_history:
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append(Message(role=role, content=msg["content"]))

    try:
        response = provider.chat(
            messages=messages,
            model=model,
            temperature=0.7,
            thinking=True,
            thinking_level="high"  # For Gemini
        )

        if response.error:
            return {
                "message": f"Error: {response.error}",
                "product_understanding": {},
                "confidence": 0.0,
                "ready_for_video": False,
                "assumptions_made": [],
                "error": response.error
            }

        result_text = response.content

        # Parse JSON from response
        # Handle markdown code blocks
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]

        return json.loads(result_text.strip())

    except json.JSONDecodeError as e:
        return {
            "message": result_text if result_text else "I had trouble processing that. Could you rephrase?",
            "product_understanding": {},
            "confidence": 0.0,
            "ready_for_video": False,
            "assumptions_made": [],
            "error": str(e)
        }
    except Exception as e:
        return {
            "message": f"Error: {str(e)}",
            "product_understanding": {},
            "confidence": 0.0,
            "ready_for_video": False,
            "assumptions_made": [],
            "error": str(e)
        }


@app.route("/")
def index():
    # Check for session_id in query params
    session_id = request.args.get("session")

    if session_id:
        # Load existing session from URL parameter
        existing = db.get_session(session_id)
        if existing:
            session["session_id"] = session_id
            # Don't store conversation in session cookie - load from DB when needed
            return render_template("index.html")

    # Check if Flask session already has a valid session_id
    existing_session_id = session.get("session_id")
    if existing_session_id:
        # Verify the session still exists in database
        existing = db.get_session(existing_session_id)
        if existing:
            # Session is still valid, keep using it
            return render_template("index.html")

    # Create new session only if none exists
    new_session_id = db.create_session()
    session["session_id"] = new_session_id
    return render_template("index.html")


# ============ Provider API Routes ============

@app.route("/api/providers", methods=["GET"])
def get_providers():
    """List available providers and current selection."""
    providers = list_providers()
    return jsonify({
        "available": providers,
        "current": {
            "image": session.get("image_provider", os.getenv("IMAGE_PROVIDER", "wan")),
            "video": session.get("video_provider", os.getenv("VIDEO_PROVIDER", "wan"))
        }
    })


@app.route("/api/set-provider", methods=["POST"])
def set_provider():
    """Set the current provider for image and/or video generation."""
    data = request.json or {}
    providers = list_providers()

    if "image" in data:
        if data["image"] in providers["image"]:
            session["image_provider"] = data["image"]
        else:
            return jsonify({"error": f"Unknown image provider: {data['image']}"}), 400

    if "video" in data:
        if data["video"] in providers["video"]:
            session["video_provider"] = data["video"]
        else:
            return jsonify({"error": f"Unknown video provider: {data['video']}"}), 400

    session.modified = True
    return jsonify({
        "status": "ok",
        "current": {
            "image": session.get("image_provider", os.getenv("IMAGE_PROVIDER", "wan")),
            "video": session.get("video_provider", os.getenv("VIDEO_PROVIDER", "wan"))
        }
    })


@app.route("/api/llm-providers", methods=["GET"])
def get_llm_providers():
    """List available LLM providers, their models, and current selection."""
    providers = list_llm_providers()
    available = get_available_llm_providers()

    return jsonify({
        "available": available,
        "providers": providers,
        "current": {
            "provider": session.get("llm_provider", os.getenv("LLM_PROVIDER", "gemini")),
            "model": session.get("llm_model")  # None means use provider default
        }
    })


@app.route("/api/set-llm-provider", methods=["POST"])
def set_llm_provider():
    """Set the current LLM provider and/or model."""
    data = request.json or {}
    available = get_available_llm_providers()

    if "provider" in data:
        if data["provider"] in available:
            session["llm_provider"] = data["provider"]
            # Reset model when switching providers
            session["llm_model"] = None
        else:
            return jsonify({"error": f"Unknown or unconfigured LLM provider: {data['provider']}"}), 400

    if "model" in data:
        # Validate model belongs to current provider
        provider_name = session.get("llm_provider", os.getenv("LLM_PROVIDER", "gemini"))
        try:
            provider = get_llm_provider(provider_name)
            if data["model"] and data["model"] not in provider.available_models:
                return jsonify({"error": f"Unknown model '{data['model']}' for provider {provider_name}"}), 400
            session["llm_model"] = data["model"] if data["model"] else None
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    session.modified = True
    return jsonify({
        "status": "ok",
        "current": {
            "provider": session.get("llm_provider", os.getenv("LLM_PROVIDER", "gemini")),
            "model": session.get("llm_model")
        }
    })


# ============ Session API Routes ============

@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    """List all sessions with summary info."""
    sessions = db.list_sessions()
    return jsonify(sessions)


@app.route("/api/sessions", methods=["POST"])
def create_session():
    """Create a new session."""
    data = request.json or {}
    name = data.get("name")
    session_id = db.create_session(name=name)
    return jsonify({"id": session_id})


@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    """Get full session data."""
    sess = db.get_session(session_id)
    if not sess:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(sess)


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    """Delete a session."""
    db.delete_session(session_id)
    return jsonify({"status": "ok"})


@app.route("/api/sessions/<session_id>/name", methods=["PUT"])
def rename_session(session_id):
    """Rename a session."""
    data = request.json or {}
    name = data.get("name", "")
    db.rename_session(session_id, name)
    return jsonify({"status": "ok"})


@app.route("/api/current-session", methods=["GET"])
def get_current_session():
    """Get the current session ID."""
    session_id = session.get("session_id")
    if not session_id:
        return jsonify({"error": "No active session"}), 404
    return jsonify({"id": session_id})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")

    # Ensure we have a session_id
    if "session_id" not in session:
        session["session_id"] = db.create_session()

    session_id = session["session_id"]

    # Add user message to database first
    db.add_message(session_id, "user", user_message)

    # Load conversation from database (not Flask session - avoids cookie overflow)
    conversation = db.get_conversation(session_id)
    turn_number = len(conversation) // 2  # Track conversation turn (after adding user message)

    # Get LLM response
    response = chat_with_llm(conversation)

    # Add assistant response to database
    assistant_content = json.dumps(response)
    db.add_message(session_id, "assistant", assistant_content)

    # Reload conversation for consistency extraction (now includes assistant response)
    conversation = db.get_conversation(session_id)

    # Update session with product understanding
    if response.get("product_understanding"):
        product = response["product_understanding"]
        db.update_session(
            session_id,
            product_understanding=product,
            confidence=response.get("confidence", 0.0),
            is_ready=response.get("ready_for_video", False)
        )
        # Auto-generate session name from product name if not set
        if product.get("name"):
            existing = db.get_session(session_id)
            if existing and not existing.get("name"):
                db.rename_session(session_id, product["name"])

    # ============ Visual Consistency Extraction ============
    # Extract visual details for video consistency using Claude's tool_use
    extraction_data = None
    try:
        # Only extract if Anthropic API is available
        anthropic_provider = get_llm_provider("anthropic")
        if anthropic_provider:
            # Convert conversation to Message format (conversation already loaded from DB above)
            messages = [
                Message(role=msg["role"], content=msg["content"])
                for msg in conversation
            ]

            extraction_result = anthropic_provider.extract_consistency_data(
                conversation_history=messages,
                current_turn=turn_number
            )

            if extraction_result.get("has_updates"):
                # Get or create consistency manager for this session
                manager = get_consistency_manager(session_id)

                # Apply extracted subjects
                for subject_data in extraction_result.get("subjects", []):
                    subject_type = subject_data.get("type")
                    if subject_type == "human":
                        manager.create_human_subject(
                            name=subject_data.get("name", "Person"),
                            role=subject_data.get("role", "protagonist"),
                            gender=subject_data.get("gender"),
                            age_range=subject_data.get("age_range")
                        )
                    elif subject_type == "animal":
                        subject = manager.add_subject(
                            subject_type=SubjectType.ANIMAL,
                            name=subject_data.get("name"),
                            role=subject_data.get("role", "pet")
                        )
                    elif subject_type == "object":
                        subject = manager.add_subject(
                            subject_type=SubjectType.OBJECT,
                            name=subject_data.get("name"),
                            role=subject_data.get("role", "product")
                        )

                # Apply extracted environment
                if extraction_result.get("environment"):
                    env_data = extraction_result["environment"]
                    manager.set_environment(name=env_data.get("name", "Scene"))
                    manager.update_environment(
                        turn=turn_number,
                        confidence=ConfidenceLevel.CONFIRMED if env_data.get("confidence") == "confirmed" else ConfidenceLevel.INFERRED,
                        setting_type=env_data.get("setting_type"),
                        location=env_data.get("location"),
                        time_of_day=env_data.get("time_of_day"),
                        mood=env_data.get("mood")
                    )

                # Apply extracted style
                if extraction_result.get("style"):
                    style_data = extraction_result["style"]
                    manager.set_style(name=style_data.get("name", "Visual Style"))
                    manager.update_style(
                        turn=turn_number,
                        confidence=ConfidenceLevel.CONFIRMED if style_data.get("confidence") == "confirmed" else ConfidenceLevel.INFERRED,
                        style=style_data.get("style"),
                        tone=style_data.get("tone"),
                        color_grade=style_data.get("color_grade")
                    )

                # Include extraction summary in response
                extraction_data = {
                    "subjects_count": len(extraction_result.get("subjects", [])),
                    "has_environment": extraction_result.get("environment") is not None,
                    "has_style": extraction_result.get("style") is not None,
                    "raw_extractions": extraction_result.get("raw_extractions", [])
                }

    except Exception as e:
        # Non-fatal: extraction is optional enhancement
        print(f"Consistency extraction error: {e}")

    # Add extraction data to response if available
    if extraction_data:
        response["consistency_extraction"] = extraction_data

    return jsonify(response)


@app.route("/api/consistency-state", methods=["GET"])
def get_consistency_state():
    """Get the current visual consistency state for a session."""
    session_id = session.get("session_id")
    if not session_id:
        return jsonify({"error": "No active session"}), 404

    if session_id not in _consistency_managers:
        return jsonify({
            "session_id": session_id,
            "subjects": [],
            "environment": None,
            "style": None,
            "prompt_preview": None
        })

    manager = _consistency_managers[session_id]
    state = manager.state

    # Build response with serializable data
    subjects = []
    for subject in state.subjects:
        subject_info = {
            "id": subject.id,
            "name": subject.name,
            "type": subject.subject_type.value,
            "role": subject.role,
            "prompt_block": subject.to_prompt_block(detail_level="medium")
        }
        subjects.append(subject_info)

    environment = None
    if state.environment:
        environment = {
            "id": state.environment.id,
            "name": state.environment.name,
            "prompt_block": state.environment.to_prompt_block(detail_level="medium")
        }

    style = None
    if state.style:
        style = {
            "id": state.style.id,
            "name": state.style.name,
            "prompt_block": state.style.to_prompt_block(detail_level="medium")
        }

    return jsonify({
        "session_id": session_id,
        "subjects": subjects,
        "environment": environment,
        "style": style,
        "prompt_preview": manager.get_prompt_block(detail_level="medium")
    })


@app.route("/api/generate-reference", methods=["POST"])
def generate_reference():
    """
    Generate a reference image for a subject.

    Request body:
        - subject_id: ID of the subject to generate reference for
        - pose: Optional pose/orientation for the reference

    Returns:
        - url/reference_url: The generated image URL (if sync completion)
        - task_id: Task ID for polling (if async)
    """
    # Check for session
    session_id = session.get("session_id")
    if not session_id:
        return jsonify({"error": "No active session"}), 400

    data = request.json or {}
    subject_id = data.get("subject_id")
    pose = data.get("pose")

    if not subject_id:
        return jsonify({"error": "subject_id is required"}), 400

    # Get or create consistency manager for this session
    manager = get_consistency_manager(session_id)

    # Get the subject
    subject = manager.get_subject(subject_id)
    if not subject:
        return jsonify({"error": f"Subject not found: {subject_id}"}), 404

    try:
        # Build the reference prompt using PromptAssembler
        assembler = PromptAssembler(manager.state)
        prompt = assembler.assemble_reference_prompt(
            subject_id=subject_id,
            pose=pose
        )

        print(f"[generate-reference] Generating reference for subject {subject_id}")
        print(f"[generate-reference] Prompt: {prompt[:150]}...")

        # Try Google/Imagen 3 provider first (better quality for stills), fall back to Wan
        task = None
        try:
            image_provider = get_image_provider("google")
            task = image_provider.generate_image(prompt)
            if task.status == "error":
                raise ValueError(task.error or "Google provider failed")
        except Exception as google_err:
            print(f"[generate-reference] Google provider failed: {google_err}, falling back to Wan")
            image_provider = get_image_provider("wan")
            task = image_provider.generate_image(prompt)

        if task.status == "completed" and task.result:
            # Sync completion - get URL (cache if needed for base64)
            url = task.result.to_url(cache_func=cache_image)

            # Store the reference URL on the subject
            manager.set_reference_url(subject_id, url)

            return jsonify({
                "status": "completed",
                "url": url,
                "reference_url": url,
                "subject_id": subject_id
            })

        elif task.status == "processing":
            # Async - register task for polling
            register_task(task)
            # Store subject_id in task data for later reference URL update
            task.provider_data["subject_id"] = subject_id
            task.provider_data["session_id"] = session_id
            return jsonify({
                "status": "processing",
                "task_id": task.task_id,
                "subject_id": subject_id,
                "message": "Reference image generation started"
            })

        else:
            return jsonify({
                "error": task.error or "Failed to start image generation",
                "status": "error"
            }), 500

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"[generate-reference] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/reset", methods=["POST"])
def reset():
    # Clean up old consistency manager
    old_session_id = session.get("session_id")
    if old_session_id and old_session_id in _consistency_managers:
        del _consistency_managers[old_session_id]

    # Create a new session instead of just clearing
    new_session_id = db.create_session()
    session["session_id"] = new_session_id
    # Don't store conversation in session cookie - it's in the database
    return jsonify({"status": "ok", "session_id": new_session_id})


@app.route("/generate-script", methods=["POST"])
def generate_script():
    """Generate a video script from the product understanding"""
    print("=== Generate script called ===")
    data = request.json
    product = data.get("product_understanding", {})
    print(f"Product: {product}")

    # Get conversation history for additional context (load from database, not session cookie)
    conversation_context = ""
    session_id = session.get("session_id")
    if session_id:
        conversation = db.get_conversation(session_id)
        if conversation:
            conversation_context = "\n".join([
                f"{msg['role'].upper()}: {msg['content'][:500]}"
                for msg in conversation[-6:]  # Last 6 messages for context
            ])

    script_prompt = f"""Based on this product understanding and conversation context, generate a punchy 15-second demo video script:

Product: {json.dumps(product, indent=2)}

Conversation Context (use this to understand user preferences and product details):
{conversation_context if conversation_context else "No additional context"}

CRITICAL CONSTRAINTS:
- Generate THREE separate 5-second video segments that will be combined into ONE COHESIVE 15-second video
- AI video CANNOT render readable text/words. But SCREENS ARE ENCOURAGED for digital products!

FOR DIGITAL PRODUCTS (apps, software, websites, browser extensions, SaaS, AI tools):
- The SCREEN should be the HERO of 70-80% of the video
- Show the screen prominently with "GREEKED" UI: gray rectangular bars for text, colored shapes for buttons, abstract icons
- NEVER show actual readable text - use thick gray horizontal lines to represent text blocks
- UI elements should be simplified: colored rectangles for buttons, simple geometric shapes for icons
- The screen should GLOW and feel magical - light emanating from it, reflections on the user's face
- Camera angles: over-the-shoulder looking at screen, close-up of screen with user reflection, screen filling 60%+ of frame
- Show the transformation ON THE SCREEN: cluttered gray bars -> organized glowing elements -> satisfying resolved state

FOR PHYSICAL PRODUCTS:
- Focus on the product itself with dramatic lighting
- Show human interaction and emotional response

VISUAL CONSISTENCY IS PARAMOUNT:
- ALL 4 keyframes MUST share the EXACT SAME: subject/person, environment/location, camera angle style, lighting setup, color palette
- The SAME screen/monitor in the SAME position throughout
- Each keyframe prompt MUST explicitly reference the consistent elements
- Use a SINGLE recurring visual motif throughout (for digital: glowing UI elements, light from screen, cursor trails)

Structure (3 segments, 5 seconds each):
1. HOOK (0-5s): The problem state - screen showing chaotic/cluttered greeked UI, user looking frustrated
2. MAGIC (5-10s): The transformation - screen elements reorganizing, glowing, the "magic moment"
3. PAYOFF (10-15s): The result - clean organized screen, user satisfaction, warm glow

Output as JSON:
{{
  "title": "Video title",
  "is_digital_product": true/false,
  "visual_style": "DEFINE FIRST: Exact cinematic style (e.g., 'Photorealistic, shallow depth of field, screen as light source, 35mm lens')",
  "color_palette": "DEFINE FIRST: Exact colors - for digital products include screen glow color (e.g., 'Deep navy shadows, electric blue screen glow, warm amber accents')",
  "consistent_elements": "DEFINE FIRST: Elements in EVERY frame. For digital: include monitor/screen description, user description, room setup, camera angle",
  "visual_motif": "DEFINE FIRST: For digital products, this should relate to the screen (e.g., 'Soft blue light emanating from screen that grows warmer and brighter')",
  "keyframes": [
    {{
      "frame": 1,
      "name": "opening",
      "image_prompt": "DETAILED 80-100 word prompt. For digital products: SCREEN MUST BE VISIBLE taking up significant frame space. Show greeked UI (gray bars for text, simple shapes for buttons) in a cluttered/chaotic state. User visible but secondary to screen. Screen casts cool light on user's frustrated face. Describe exact screen content using abstract shapes. NO READABLE TEXT but DO show the screen prominently."
    }},
    {{
      "frame": 2,
      "name": "transition_1_2",
      "image_prompt": "DETAILED 80-100 word prompt. SAME screen, SAME angle. Screen beginning to transform - some greeked elements starting to glow/organize. User's expression shifting to curiosity, lit by changing screen light. The visual_motif (screen glow) intensifying. Maintain exact camera position."
    }},
    {{
      "frame": 3,
      "name": "transition_2_3",
      "image_prompt": "DETAILED 80-100 word prompt. SAME screen, SAME angle. Screen transformation in full effect - greeked UI elements now organized, glowing with product's brand color. Beautiful abstract patterns of rectangles and shapes. User engaged, face illuminated warmly. Screen is the visual hero."
    }},
    {{
      "frame": 4,
      "name": "closing",
      "image_prompt": "DETAILED 80-100 word prompt. SAME screen, SAME angle. Screen showing resolved, clean greeked UI - organized gray bars, glowing accent elements, satisfying visual order. User relaxed and satisfied, bathed in warm screen glow. The screen radiates accomplishment. Environment feels warm and successful."
    }}
  ],
  "segments": [
    {{
      "segment": 1,
      "name": "hook",
      "first_frame": 1,
      "last_frame": 2,
      "motion_description": "Screen elements subtly shifting, user's small movements, light from screen flickering slightly"
    }},
    {{
      "segment": 2,
      "name": "magic",
      "first_frame": 2,
      "last_frame": 3,
      "motion_description": "Screen elements animating - reorganizing, glowing trails, the transformation happening ON the screen"
    }},
    {{
      "segment": 3,
      "name": "payoff",
      "first_frame": 3,
      "last_frame": 4,
      "motion_description": "Screen settling into final state, warm light bloom, user leaning back in satisfaction"
    }}
  ]
}}"""

    try:
        # Get LLM provider
        provider_name = session.get("llm_provider", os.getenv("LLM_PROVIDER", "gemini"))
        model = session.get("llm_model")

        print(f"Calling LLM API (provider: {provider_name}, model: {model or 'default'})...")
        provider = get_llm_provider(provider_name)

        response = provider.generate(
            prompt=script_prompt,
            model=model,
            temperature=0.8,
            thinking=True,
            thinking_level="medium"  # For Gemini
        )

        if response.error:
            print(f"LLM error: {response.error}")
            return jsonify({"error": response.error}), 500

        print(f"LLM response received from {response.provider}/{response.model}")

        result_text = response.content
        print(f"Raw result: {result_text[:200]}...")

        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]

        parsed = json.loads(result_text.strip())
        print("Successfully parsed JSON")

        # Save script to database
        session_id = session.get("session_id")
        if session_id:
            video_id = db.create_video(session_id, script=parsed)
            parsed["video_id"] = video_id

        return jsonify(parsed)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============ Video Generation Routes (Provider-aware) ============

@app.route("/generate-video", methods=["POST"])
def generate_video():
    """Generate keyframe images using the selected provider."""
    data = request.json
    keyframes = data.get("keyframes", [])
    segments = data.get("segments", [])

    # Get provider from session or request
    provider_name = data.get("provider") or session.get("image_provider") or os.getenv("IMAGE_PROVIDER", "wan")

    print(f"=== Keyframe Generation (provider: {provider_name}) ===")
    print(f"Keyframes: {len(keyframes)}, Segments: {len(segments)}")

    if not keyframes or not segments:
        return jsonify({"error": "Missing keyframes or segments"}), 400

    try:
        image_provider = get_image_provider(provider_name)
        image_tasks = []

        for kf in keyframes:
            frame_num = kf.get("frame")
            prompt = kf.get("image_prompt", "")
            print(f"  Frame {frame_num}: {prompt[:80]}...")

            task = image_provider.generate_image(prompt)

            if task.status == "completed" and task.result:
                # Sync completion - get URL (cache if needed for base64)
                url = task.result.to_url(cache_func=cache_image)
                image_tasks.append({
                    "frame": frame_num,
                    "status": "completed",
                    "url": url,
                    "provider": provider_name
                })
            elif task.status == "processing":
                # Async - register task for polling
                register_task(task)
                image_tasks.append({
                    "frame": frame_num,
                    "status": "processing",
                    "task_id": task.task_id,
                    "provider": provider_name
                })
            else:
                image_tasks.append({
                    "frame": frame_num,
                    "status": "error",
                    "error": task.error or "Failed to start image generation",
                    "provider": provider_name
                })

        return jsonify({
            "status": "generating_keyframes",
            "phase": "keyframes",
            "keyframe_tasks": image_tasks,
            "segments": segments,
            "provider": provider_name,
            "message": f"Generating {len(keyframes)} keyframe images with {provider_name}"
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/video-status/<task_id>")
def video_status(task_id):
    """Check generation status for a single task (works for both image and video)."""
    # Get provider from query params
    provider_name = request.args.get("provider", "wan")

    # First check our task registry
    task = get_task(task_id)

    if task:
        # Poll using the appropriate provider
        try:
            if task.task_type == "image":
                provider = get_image_provider(task.provider)
            else:
                provider = get_video_provider(task.provider)

            task = provider.poll_task(task)
            _task_registry[task_id] = task  # Update registry

            if task.status == "completed":
                if task.task_type == "image" and task.result:
                    url = task.result.to_url(cache_func=cache_image)
                    return jsonify({
                        "status": "completed",
                        "result": {"urls": [url]} if url else {}
                    })
                elif task.task_type == "video":
                    # Handle video result
                    if task.result_url:
                        return jsonify({
                            "status": "completed",
                            "result": {"url": task.result_url}
                        })
                    elif task.result_bytes:
                        # Save video bytes to static folder
                        filename = f"video_{task_id[:8]}.mp4"
                        filepath = os.path.join("static", filename)
                        os.makedirs("static", exist_ok=True)
                        with open(filepath, "wb") as f:
                            f.write(task.result_bytes)
                        url = f"/static/{filename}"
                        return jsonify({
                            "status": "completed",
                            "result": {"url": url}
                        })
            elif task.status == "error":
                return jsonify({
                    "status": "error",
                    "error": task.error
                })
            else:
                return jsonify({
                    "status": "processing",
                    "task_status": task.provider_data.get("task_status", "RUNNING")
                })

        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500

    # Fallback: try Wan API directly for backwards compatibility
    try:
        wan_url = os.getenv("WAN_API_URL", "http://localhost:5000")
        response = requests.get(f"{wan_url}/api/task/{task_id}", timeout=180)
        result = response.json()
        print(f"Task {task_id} status (Wan fallback): {result}")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/generate-videos-from-keyframes", methods=["POST"])
def generate_videos_from_keyframes():
    """Generate videos from keyframe images using the selected provider."""
    data = request.json
    keyframe_urls = data.get("keyframe_urls", {})  # {1: url, 2: url, 3: url, 4: url}
    segments = data.get("segments", [])
    video_id = data.get("video_id")

    # Get provider from session or request
    provider_name = data.get("provider") or session.get("video_provider") or os.getenv("VIDEO_PROVIDER", "wan")

    print(f"=== Video Generation (provider: {provider_name}) ===")
    print(f"Keyframe URLs: {list(keyframe_urls.keys())}")

    # Save keyframe URLs to video record
    if video_id and keyframe_urls:
        db.update_video(video_id, keyframe_urls=keyframe_urls)
    elif session.get("session_id") and keyframe_urls:
        # Try to get video from session
        video = db.get_session_video(session["session_id"])
        if video:
            db.update_video(video["id"], keyframe_urls=keyframe_urls)

    try:
        video_provider = get_video_provider(provider_name)
        video_tasks = []

        for seg in segments:
            segment_num = seg.get("segment")
            first_frame = seg.get("first_frame")
            last_frame = seg.get("last_frame")
            motion = seg.get("motion_description", "")

            first_url = keyframe_urls.get(str(first_frame))
            last_url = keyframe_urls.get(str(last_frame))

            if not first_url or not last_url:
                video_tasks.append({
                    "segment": segment_num,
                    "status": "error",
                    "error": f"Missing keyframe URLs for frames {first_frame} or {last_frame}",
                    "provider": provider_name
                })
                continue

            print(f"  Segment {segment_num}: frames {first_frame}->{last_frame}")

            # Create ImageData from URLs
            first_image = ImageData(url=first_url)
            last_image = ImageData(url=last_url)

            task = video_provider.generate_video(
                prompt=motion,
                first_frame=first_image,
                last_frame=last_image
            )

            if task.status == "processing":
                register_task(task)
                video_tasks.append({
                    "segment": segment_num,
                    "status": "processing",
                    "task_id": task.task_id,
                    "provider": provider_name
                })
            elif task.status == "completed":
                url = task.result_url
                if task.result_bytes and not url:
                    # Save bytes to file
                    filename = f"seg_{segment_num}_{task.task_id[:8]}.mp4"
                    filepath = os.path.join("static", filename)
                    os.makedirs("static", exist_ok=True)
                    with open(filepath, "wb") as f:
                        f.write(task.result_bytes)
                    url = f"/static/{filename}"
                video_tasks.append({
                    "segment": segment_num,
                    "status": "completed",
                    "url": url,
                    "provider": provider_name
                })
            else:
                video_tasks.append({
                    "segment": segment_num,
                    "status": "error",
                    "error": task.error or "Failed to start video generation",
                    "provider": provider_name
                })

        return jsonify({
            "status": "generating_videos",
            "phase": "videos",
            "segments": video_tasks,
            "provider": provider_name,
            "message": f"Generating {len(video_tasks)} video segments with {provider_name}"
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate-videos-direct", methods=["POST"])
def generate_videos_direct():
    """
    Generate videos directly from provided script and images.

    Skips keyframe generation phase - goes straight to video generation.
    Useful for imported bundles or when you already have keyframe images.

    Request body:
        - script: The video script with segments
        - images: Dict mapping frame numbers to URL or base64 images
                  e.g., {"1": "http://...", "2": "data:image/png;base64,..."}
        - provider: Optional video provider name
        - video_id: Optional existing video ID to update
        - persist_images: Optional bool to persist images before generation (default true)

    Returns:
        - video_tasks: Array of video generation tasks for polling
    """
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    script = data.get("script")
    images = data.get("images", {})
    provider_name = data.get("provider") or session.get("video_provider") or os.getenv("VIDEO_PROVIDER", "wan")
    video_id = data.get("video_id")
    persist = data.get("persist_images", True)

    if not script:
        return jsonify({"error": "No script provided"}), 400

    segments = script.get("segments", [])
    if not segments:
        return jsonify({"error": "No segments in script"}), 400

    print(f"=== Direct Video Generation (provider: {provider_name}) ===")
    print(f"Images provided: {list(images.keys())}")
    print(f"Segments: {len(segments)}")

    # Process images - convert to usable URLs
    keyframe_urls = {}
    for frame_num, img_data in images.items():
        frame_num = str(frame_num)
        if not img_data:
            continue

        if persist and not img_data.startswith("/api/images/persisted/"):
            # Persist the image first
            try:
                image_id, url = persist_image(
                    img_data,
                    video_id=video_id,
                    frame_num=int(frame_num)
                )
                keyframe_urls[frame_num] = url
            except Exception as e:
                print(f"Failed to persist image for frame {frame_num}: {e}")
                # Fall back to using the original data if it's a URL
                if img_data.startswith("http") or img_data.startswith("/"):
                    keyframe_urls[frame_num] = img_data
        else:
            keyframe_urls[frame_num] = img_data

    # Update video record with keyframe URLs if we have a video_id
    if video_id and keyframe_urls:
        db.update_video(video_id, keyframe_urls=keyframe_urls)

    # Now generate videos using the existing endpoint logic
    try:
        video_provider = get_video_provider(provider_name)
        video_tasks = []

        for seg in segments:
            segment_num = seg.get("segment")
            first_frame = seg.get("first_frame")
            last_frame = seg.get("last_frame")
            motion = seg.get("motion_description", "")

            first_url = keyframe_urls.get(str(first_frame))
            last_url = keyframe_urls.get(str(last_frame))

            if not first_url or not last_url:
                video_tasks.append({
                    "segment": segment_num,
                    "status": "error",
                    "error": f"Missing keyframe URLs for frames {first_frame} or {last_frame}",
                    "provider": provider_name
                })
                continue

            print(f"  Segment {segment_num}: frames {first_frame}->{last_frame}")

            # Create ImageData from URLs
            first_image = ImageData(url=first_url)
            last_image = ImageData(url=last_url)

            task = video_provider.generate_video(
                prompt=motion,
                first_frame=first_image,
                last_frame=last_image
            )

            if task.status == "processing":
                register_task(task)
                video_tasks.append({
                    "segment": segment_num,
                    "status": "processing",
                    "task_id": task.task_id,
                    "provider": provider_name
                })
            elif task.status == "completed":
                url = task.result_url
                if task.result_bytes and not url:
                    filename = f"seg_{segment_num}_{task.task_id[:8]}.mp4"
                    filepath = os.path.join("static", filename)
                    os.makedirs("static", exist_ok=True)
                    with open(filepath, "wb") as f:
                        f.write(task.result_bytes)
                    url = f"/static/{filename}"
                video_tasks.append({
                    "segment": segment_num,
                    "status": "completed",
                    "url": url,
                    "provider": provider_name
                })
            else:
                video_tasks.append({
                    "segment": segment_num,
                    "status": "error",
                    "error": task.error or "Failed to start video generation",
                    "provider": provider_name
                })

        return jsonify({
            "status": "generating_videos",
            "phase": "videos",
            "segments": video_tasks,
            "keyframe_urls": keyframe_urls,
            "video_id": video_id,
            "provider": provider_name,
            "message": f"Generating {len(video_tasks)} video segments with {provider_name}"
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/video-status-multi", methods=["POST"])
def video_status_multi():
    """Check status of multiple video segments."""
    data = request.json
    segments = data.get("segments", [])

    results = []
    all_completed = True
    any_failed = False

    for seg in segments:
        task_id = seg.get("task_id")
        segment_num = seg.get("segment")
        provider_name = seg.get("provider", "wan")

        # Check our task registry first
        task = get_task(task_id)

        if task:
            try:
                provider = get_video_provider(task.provider)
                task = provider.poll_task(task)
                _task_registry[task_id] = task

                segment_result = {
                    "segment": segment_num,
                    "task_id": task_id,
                    "status": task.status,
                    "provider": task.provider
                }

                if task.status == "completed":
                    url = task.result_url
                    if task.result_bytes and not url:
                        # Save bytes to file
                        filename = f"seg_{segment_num}_{task_id[:8]}.mp4"
                        filepath = os.path.join("static", filename)
                        os.makedirs("static", exist_ok=True)
                        with open(filepath, "wb") as f:
                            f.write(task.result_bytes)
                        url = f"/static/{filename}"
                    segment_result["url"] = url
                elif task.status == "error":
                    segment_result["error"] = task.error
                    any_failed = True
                else:
                    all_completed = False
                    segment_result["task_status"] = task.provider_data.get("task_status", "RUNNING")

                results.append(segment_result)
                continue

            except Exception as e:
                results.append({
                    "segment": segment_num,
                    "task_id": task_id,
                    "status": "error",
                    "error": str(e)
                })
                any_failed = True
                continue

        # Fallback: try Wan API directly
        try:
            wan_url = os.getenv("WAN_API_URL", "http://localhost:5000")
            response = requests.get(f"{wan_url}/api/task/{task_id}", timeout=180)
            result = response.json()

            segment_result = {
                "segment": segment_num,
                "task_id": task_id,
                "status": result.get("status"),
                "task_status": result.get("task_status"),
                "provider": "wan"
            }

            if result.get("status") == "completed":
                segment_result["url"] = result.get("result", {}).get("url")
            elif result.get("status") == "error":
                segment_result["error"] = result.get("error")
                any_failed = True
            else:
                all_completed = False

            results.append(segment_result)

        except Exception as e:
            results.append({
                "segment": segment_num,
                "task_id": task_id,
                "status": "error",
                "error": str(e)
            })
            any_failed = True

    # Only consider "all_completed" if we actually have successful videos
    successful_count = sum(1 for r in results if r.get("status") == "completed" and r.get("url"))

    return jsonify({
        "segments": results,
        "all_completed": all_completed and successful_count >= 2,  # Need at least 2 videos to stitch
        "any_failed": any_failed,
        "successful_count": successful_count
    })


@app.route("/stitch-videos", methods=["POST"])
def stitch_videos():
    """Download and stitch multiple video segments using ffmpeg"""
    data = request.json
    video_urls = data.get("videos", [])  # [{segment: 1, url: "..."}, ...]
    video_id = data.get("video_id")  # Optional: video record to update

    if len(video_urls) < 2:
        return jsonify({"error": "Need at least 2 videos to stitch"}), 400

    # Sort by segment
    video_urls = sorted(video_urls, key=lambda x: x.get("segment", 0))

    print(f"=== Stitching {len(video_urls)} videos ===")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Download all videos
            video_files = []
            for i, v in enumerate(video_urls):
                url = v.get("url")
                print(f"Downloading segment {i+1}...")

                # Handle local files vs remote URLs
                if url.startswith("/static/"):
                    # Local file - copy it
                    local_path = url.lstrip("/")
                    if os.path.exists(local_path):
                        filepath = os.path.join(tmpdir, f"seg_{i+1}.mp4")
                        with open(local_path, "rb") as src:
                            with open(filepath, "wb") as dst:
                                dst.write(src.read())
                        video_files.append(filepath)
                        continue

                # Remote URL - download it
                resp = requests.get(url, timeout=60)
                if resp.status_code != 200:
                    return jsonify({"error": f"Failed to download segment {i+1}"}), 500

                filepath = os.path.join(tmpdir, f"seg_{i+1}.mp4")
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                video_files.append(filepath)

            # Create concat file for ffmpeg
            concat_file = os.path.join(tmpdir, "concat.txt")
            with open(concat_file, "w") as f:
                for vf in video_files:
                    f.write(f"file '{vf}'\n")

            # Output path
            output_filename = f"stitched_{uuid.uuid4().hex[:8]}.mp4"
            output_path = os.path.join("static", output_filename)
            os.makedirs("static", exist_ok=True)

            # Run ffmpeg
            print("Running ffmpeg...")
            result = subprocess.run([
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                output_path
            ], capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                print(f"ffmpeg error: {result.stderr}")
                return jsonify({"error": f"ffmpeg failed: {result.stderr[:200]}"}), 500

            print(f"Stitched video saved to {output_path}")

            stitched_url = f"/static/{output_filename}"

            # Update video record if we have one
            if video_id:
                db.update_video(
                    video_id,
                    segment_urls=video_urls,
                    stitched_url=stitched_url,
                    status="completed"
                )
            # Also try to find video by session
            elif session.get("session_id"):
                video = db.get_session_video(session["session_id"])
                if video:
                    db.update_video(
                        video["id"],
                        segment_urls=video_urls,
                        stitched_url=stitched_url,
                        status="completed"
                    )

            return jsonify({
                "status": "completed",
                "url": stitched_url
            })

    except subprocess.TimeoutExpired:
        return jsonify({"error": "ffmpeg timed out"}), 500
    except Exception as e:
        print(f"Stitch error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)
