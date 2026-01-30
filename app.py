import os
import json
import uuid
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# API Configuration
API_KEY = os.getenv("ALIBABA_API_KEY")
# Change this based on your region: dashscope-intl (Singapore), dashscope-us (Virginia), dashscope (Beijing)
BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope-intl.aliyuncs.com/api/v1")

# Available models with their configurations
MODELS = {
    # Image Generation
    "wan2.6-image": {
        "type": "image",
        "description": "Text to Image / Image Editing",
        "endpoint": "/services/aigc/multimodal-generation/generation",
        "sync": True,
    },
    # Text to Video
    "wan2.6-t2v": {
        "type": "video",
        "description": "Text to Video (2-15s, 720P/1080P)",
        "endpoint": "/services/aigc/video-generation/video-synthesis",
        "sync": False,  # HTTP only, no SDK support
        "params": {"size": "1280*720", "duration": 5, "prompt_extend": True},
        "default_negative_prompt": "blurry, low quality, distorted, deformed, ugly, bad anatomy",
    },
    # Image to Video
    "wan2.6-i2v": {
        "type": "video",
        "description": "Image to Video (2-15s, 720P/1080P)",
        "endpoint": "/services/aigc/video-generation/video-synthesis",
        "sync": False,
        "requires_image": True,
        "params": {"resolution": "720P", "duration": 5},
    },
    "wan2.6-i2v-flash": {
        "type": "video",
        "description": "Image to Video Fast (2-15s, audio support)",
        "endpoint": "/services/aigc/video-generation/video-synthesis",
        "sync": False,
        "requires_image": True,
        "params": {"resolution": "720P", "duration": 5},
    },
    # Reference to Video (may not be available yet)
    "wan2.6-r2v": {
        "type": "video",
        "description": "Reference to Video (experimental)",
        "endpoint": "/services/aigc/video-generation/video-synthesis",
        "sync": False,
        "requires_video": True,
        "params": {"duration": 5},
    },
    # Additional useful models
    "wan2.2-kf2v-flash": {
        "type": "video",
        "description": "First & Last Frame to Video (5s)",
        "endpoint": "/services/aigc/image2video/video-synthesis",
        "sync": False,
        "requires_first_last_frame": True,
        "params": {"resolution": "720P"},
    },
    "wan2.2-s2v": {
        "type": "video",
        "description": "Digital Human Lip-sync",
        "endpoint": "/services/aigc/image2video/video-synthesis",
        "sync": False,
        "requires_image": True,
        "requires_audio": True,
        "params": {"resolution": "720P"},
    },
}

# Storage
DATA_DIR = "data"
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
PROMPTS_FILE = os.path.join(DATA_DIR, "saved_prompts.json")
history = []
saved_prompts = []


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "outputs"), exist_ok=True)


def load_data():
    global history, saved_prompts
    ensure_data_dir()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    if os.path.exists(PROMPTS_FILE):
        with open(PROMPTS_FILE, "r") as f:
            saved_prompts = json.load(f)


def save_history():
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def save_prompts():
    with open(PROMPTS_FILE, "w") as f:
        json.dump(saved_prompts, f, indent=2)


def make_api_request(endpoint, payload, async_mode=True, sse_mode=False):
    """Make HTTP request to DashScope API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    if async_mode:
        headers["X-DashScope-Async"] = "enable"
    if sse_mode:
        headers["X-DashScope-SSE"] = "enable"

    url = f"{BASE_URL}{endpoint}"

    if sse_mode:
        # Handle SSE streaming response
        print(f">>> SSE request to {url}")
        print(f">>> Payload: {json.dumps(payload, indent=2)[:500]}")
        response = requests.post(url, headers=headers, json=payload, timeout=120, stream=True)
        print(f">>> Response status: {response.status_code}")

        if response.status_code != 200:
            # Try to get error from response
            try:
                error_data = response.json()
                print(f">>> Error response: {error_data}")
                return error_data
            except:
                return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}

        final_data = None
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                print(f">>> SSE line: {line[:200]}")
                if line.startswith('data:'):
                    try:
                        data = json.loads(line[5:])
                        final_data = data
                    except json.JSONDecodeError:
                        continue
        return final_data if final_data else {"error": "No data received from SSE stream"}
    else:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        return response.json()


def query_task(task_id):
    """Query task status"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    url = f"{BASE_URL}/tasks/{task_id}"
    response = requests.get(url, headers=headers, timeout=30)
    return response.json()


load_data()


@app.route("/")
def index():
    return render_template("index.html", models=MODELS)


@app.route("/api/models")
def get_models():
    return jsonify(MODELS)


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.json
    model = data.get("model")
    prompt = data.get("prompt")
    image_url = data.get("image_url")
    audio_url = data.get("audio_url")
    first_frame_url = data.get("first_frame_url")
    last_frame_url = data.get("last_frame_url")
    video_url = data.get("video_url")

    # Optional parameters
    duration = data.get("duration")
    resolution = data.get("resolution")

    if not model or model not in MODELS:
        return jsonify({"error": f"Invalid model: {model}"}), 400

    model_config = MODELS[model]

    entry = {
        "id": str(uuid.uuid4()),
        "model": model,
        "prompt": prompt,
        "image_url": image_url,
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "result": None,
        "error": None,
        "task_id": None,
    }

    try:
        print(f"=== Generate: model={model}, type={model_config['type']}, image_url={image_url} ===")
        if model_config["type"] == "image":
            if image_url:
                print(">>> Image EDITING mode")
                # Image EDITING mode - use multimodal endpoint
                payload = {
                    "model": model,
                    "input": {
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"image": image_url},
                                    {"text": prompt}
                                ]
                            }
                        ]
                    },
                    "parameters": {
                        "n": 1,
                        "size": "1280*1280",
                    }
                }
                response = make_api_request(model_config["endpoint"], payload, async_mode=False)

                if "output" in response and "choices" in response["output"]:
                    entry["status"] = "completed"
                    images = []
                    for choice in response["output"]["choices"]:
                        for content in choice.get("message", {}).get("content", []):
                            if content.get("type") == "image":
                                images.append(content.get("image"))
                    entry["result"] = {"type": "image", "urls": images}
                else:
                    entry["status"] = "error"
                    entry["error"] = response.get("message", str(response))
            else:
                # Pure TEXT-TO-IMAGE mode - use multimodal endpoint with enable_interleave + SSE
                print(">>> Text-to-Image mode (SSE)")
                payload = {
                    "model": model,
                    "input": {
                        "messages": [
                            {
                                "role": "user",
                                "content": [{"text": prompt}]
                            }
                        ]
                    },
                    "parameters": {
                        "max_images": 1,
                        "size": "1024*1024",
                        "enable_interleave": True,
                        "stream": True,
                    }
                }
                response = make_api_request(model_config["endpoint"], payload, async_mode=False, sse_mode=True)

                if "output" in response and "choices" in response["output"]:
                    entry["status"] = "completed"
                    images = []
                    for choice in response["output"]["choices"]:
                        for content in choice.get("message", {}).get("content", []):
                            if content.get("type") == "image":
                                images.append(content.get("image"))
                    entry["result"] = {"type": "image", "urls": images}
                elif "output" in response and "task_id" in response["output"]:
                    entry["status"] = "processing"
                    entry["task_id"] = response["output"]["task_id"]
                    entry["result"] = {"type": "image", "task_id": response["output"]["task_id"]}
                else:
                    entry["status"] = "error"
                    entry["error"] = response.get("message", str(response))

        elif model_config["type"] == "video":
            # Video generation
            input_data = {"prompt": prompt or ""}

            # Add default negative prompt if configured
            if model_config.get("default_negative_prompt"):
                input_data["negative_prompt"] = model_config["default_negative_prompt"]

            # Add image URL for i2v models
            if model_config.get("requires_image") and image_url:
                input_data["img_url"] = image_url

            # Add audio URL for s2v models
            if model_config.get("requires_audio") and audio_url:
                input_data["audio_url"] = audio_url

            # Add first/last frame for kf2v models
            if model_config.get("requires_first_last_frame"):
                if first_frame_url:
                    input_data["first_frame_url"] = first_frame_url
                if last_frame_url:
                    input_data["last_frame_url"] = last_frame_url

            # Add video URL for r2v models
            if model_config.get("requires_video") and video_url:
                input_data["video_url"] = video_url

            # Build parameters
            params = dict(model_config.get("params", {}))
            if duration:
                params["duration"] = int(duration)
            if resolution:
                params["resolution"] = resolution

            payload = {
                "model": model,
                "input": input_data,
                "parameters": params,
            }

            response = make_api_request(model_config["endpoint"], payload, async_mode=True)

            if "output" in response and "task_id" in response["output"]:
                entry["status"] = "processing"
                entry["task_id"] = response["output"]["task_id"]
                entry["result"] = {"type": "video", "task_id": response["output"]["task_id"]}
            else:
                entry["status"] = "error"
                entry["error"] = response.get("message", str(response))

    except Exception as e:
        entry["status"] = "error"
        entry["error"] = str(e)

    history.insert(0, entry)
    save_history()

    return jsonify(entry)


@app.route("/api/task/<task_id>")
def check_task(task_id):
    """Check status of async task"""
    try:
        response = query_task(task_id)

        if "output" in response:
            output = response["output"]
            task_status = output.get("task_status", "UNKNOWN")

            if task_status == "SUCCEEDED":
                # Update history entry if we can find it
                video_url = output.get("video_url")
                # For image tasks, check results array
                results = output.get("results", [])
                image_urls = [r.get("url") for r in results if r.get("url")]

                result = {"status": "completed"}
                if video_url:
                    result["result"] = {"type": "video", "url": video_url}
                elif image_urls:
                    result["result"] = {"type": "image", "urls": image_urls}

                # Update history
                for h in history:
                    if h.get("task_id") == task_id:
                        h["status"] = "completed"
                        h["result"] = result.get("result")
                        save_history()
                        break

                return jsonify(result)

            elif task_status == "FAILED":
                error_msg = output.get("message", "Task failed")
                for h in history:
                    if h.get("task_id") == task_id:
                        h["status"] = "error"
                        h["error"] = error_msg
                        save_history()
                        break
                return jsonify({"status": "error", "error": error_msg})

            else:
                return jsonify({
                    "status": "processing",
                    "task_status": task_status,
                })
        else:
            return jsonify({
                "status": "error",
                "error": response.get("message", "Unknown error")
            })

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})


@app.route("/api/history")
def get_history():
    return jsonify(history)


@app.route("/api/history/<entry_id>", methods=["DELETE"])
def delete_history_entry(entry_id):
    global history
    history = [h for h in history if h["id"] != entry_id]
    save_history()
    return jsonify({"success": True})


@app.route("/api/prompts")
def get_prompts():
    return jsonify(saved_prompts)


@app.route("/api/prompts", methods=["POST"])
def save_prompt():
    data = request.json
    prompt_entry = {
        "id": str(uuid.uuid4()),
        "name": data.get("name", "Untitled"),
        "prompt": data.get("prompt"),
        "model": data.get("model"),
        "created_at": datetime.now().isoformat(),
    }
    saved_prompts.append(prompt_entry)
    save_prompts()
    return jsonify(prompt_entry)


@app.route("/api/prompts/<prompt_id>", methods=["DELETE"])
def delete_prompt(prompt_id):
    global saved_prompts
    saved_prompts = [p for p in saved_prompts if p["id"] != prompt_id]
    save_prompts()
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
