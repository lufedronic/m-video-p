"""
m(video)p - Generate product demo videos from just an idea
"""
import os
import json
import requests
import subprocess
import tempfile
import uuid
from flask import Flask, request, jsonify, render_template, session, send_file
from dotenv import load_dotenv
from google import genai

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3-flash-preview"

# System prompt for context gathering
SYSTEM_PROMPT = """You are a product strategist helping someone create a demo video for their product idea. Your goal is to deeply understand their product so you can help generate a compelling demo video.

IMPORTANT APPROACH:
1. When the user describes their idea, immediately make EDUCATED GUESSES about aspects they haven't mentioned
2. Present your assumptions clearly, then ask targeted follow-up questions
3. Be conversational and natural - like a smart co-founder brainstorming

For each response, you MUST output valid JSON with this structure:
{
  "message": "Your conversational response to the user",
  "product_understanding": {
    "name": "Product name (your guess if not provided)",
    "tagline": "One-line description",
    "problem": "The problem it solves",
    "solution": "How it solves it",
    "target_user": "Who it's for",
    "key_features": ["feature1", "feature2", "feature3"],
    "tone": "Professional/Playful/Technical/etc",
    "visual_style": "Minimal/Bold/Corporate/Startup/etc"
  },
  "confidence": 0.0 to 1.0,
  "ready_for_video": true/false,
  "assumptions_made": ["assumption1", "assumption2"]
}

IMPORTANT CONSTRAINTS:
1. Videos are 3 segments of 5 seconds each (15s total) - focus on ONE killer moment per segment.
2. AI video CANNOT render text AT ALL. NEVER include any text, words, letters, numbers, or UI with readable content. Instead use:
   - Pure visual metaphors: glowing orbs, light trails, particle effects, abstract shapes
   - Symbolic representations: icons transform, objects morph, energy flows
   - Human emotions/reactions: faces, gestures, body language
   - Environmental storytelling: lighting changes, camera movement, atmosphere shifts
   - NO screens showing text, NO text overlays, NO written words of any kind

Start with LOW confidence and build up as you learn more. Mark ready_for_video=true only when confidence > 0.8 and you have enough detail for a compelling 10-second demo.

Be concise. Ask 1-2 questions max per turn. Make bold guesses - it's easier for users to correct than to describe from scratch."""


def chat_with_gemini(conversation_history):
    """Send conversation to Gemini with thinking enabled"""

    # Build messages
    messages = [{"role": "user", "parts": [{"text": SYSTEM_PROMPT}]}]
    messages.append({"role": "model", "parts": [{"text": "I understand. I'll help gather context about the product idea, make educated guesses, and ask targeted questions. I'll respond in the JSON format specified."}]})

    for msg in conversation_history:
        role = "user" if msg["role"] == "user" else "model"
        messages.append({"role": role, "parts": [{"text": msg["content"]}]})

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=messages,
            config={
                "thinking_config": {"thinking_level": "high"},
                "temperature": 0.7,
            }
        )

        # Extract text from response
        result_text = ""
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'text') and part.text:
                result_text += part.text

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
    session["conversation"] = []
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")

    if "conversation" not in session:
        session["conversation"] = []

    # Add user message
    session["conversation"].append({"role": "user", "content": user_message})

    # Get Gemini response
    response = chat_with_gemini(session["conversation"])

    # Add assistant response to history
    session["conversation"].append({"role": "assistant", "content": json.dumps(response)})
    session.modified = True

    return jsonify(response)


@app.route("/reset", methods=["POST"])
def reset():
    session["conversation"] = []
    return jsonify({"status": "ok"})


@app.route("/generate-script", methods=["POST"])
def generate_script():
    """Generate a video script from the product understanding"""
    print("=== Generate script called ===")
    data = request.json
    product = data.get("product_understanding", {})
    print(f"Product: {product}")

    script_prompt = f"""Based on this product understanding, generate a punchy 15-second demo video script:

Product: {json.dumps(product, indent=2)}

CRITICAL CONSTRAINTS:
- Generate THREE separate 5-second video segments that will be combined into ONE COHESIVE 15-second video
- AI video CANNOT render ANY text. NEVER include text, words, UI, screens with content, or readable elements
- Use ONLY: visual metaphors, light/particle effects, human emotions, object transformations, environmental changes

VISUAL CONSISTENCY IS PARAMOUNT:
- ALL 4 keyframes MUST share the EXACT SAME: subject/person, environment/location, camera angle style, lighting setup, color palette
- Think of it as ONE continuous shot with transformation - the SAME person in the SAME room with lighting/mood changes
- Each keyframe prompt MUST explicitly reference the consistent elements (e.g., "The same person from previous frames...", "In the same minimalist office...")
- Use a SINGLE recurring visual motif/symbol throughout (e.g., a glowing orb, light particles, color shift)

Structure (3 segments, 5 seconds each):
1. HOOK (0-5s): Visual attention grab - show the problem through emotion/environment
2. MAGIC (5-10s): The transformation - abstract visual representation of the solution
3. PAYOFF (10-15s): The result - human satisfaction, visual resolution, brand feeling

Output as JSON:
{{
  "title": "Video title",
  "visual_style": "DEFINE FIRST: Exact cinematic style that ALL frames must follow (e.g., 'Photorealistic, shallow depth of field, warm cinematic lighting, 35mm lens look')",
  "color_palette": "DEFINE FIRST: Exact colors for ALL frames (e.g., 'Deep navy blue shadows, warm amber highlights, soft cream midtones')",
  "consistent_elements": "DEFINE FIRST: Elements that appear in EVERY frame (e.g., 'A 30-year-old woman with dark hair, minimalist white office, soft morning light from left window')",
  "visual_motif": "DEFINE FIRST: The recurring symbol/effect (e.g., 'Soft golden light particles that grow brighter through the sequence')",
  "keyframes": [
    {{
      "frame": 1,
      "name": "opening",
      "image_prompt": "DETAILED 80-100 word prompt. START with the consistent_elements, THEN add this frame's unique state: problem/tension visible. Include: exact composition, subject expression/posture showing frustration, the visual_motif in its initial dim state, color_palette applied. NO TEXT/UI/WORDS."
    }},
    {{
      "frame": 2,
      "name": "transition_1_2",
      "image_prompt": "DETAILED 80-100 word prompt. START by restating consistent_elements ('The same [person] in the same [environment]...'). Show: first hint of transformation, visual_motif beginning to glow/activate, subject's expression shifting to curiosity. Maintain EXACT same camera angle and lighting direction. NO TEXT/UI/WORDS."
    }},
    {{
      "frame": 3,
      "name": "transition_2_3",
      "image_prompt": "DETAILED 80-100 word prompt. START by restating consistent_elements. Show: transformation in full effect, visual_motif at peak brightness/activity, subject engaged and hopeful. SAME environment now feels warmer/brighter. Maintain camera consistency. NO TEXT/UI/WORDS."
    }},
    {{
      "frame": 4,
      "name": "closing",
      "image_prompt": "DETAILED 80-100 word prompt. START by restating consistent_elements. Show: resolution achieved, visual_motif settled into satisfying final state, subject expressing relief/joy/satisfaction. Environment at its warmest/brightest. SAME camera angle, lighting now at peak warmth. NO TEXT/UI/WORDS."
    }}
  ],
  "segments": [
    {{
      "segment": 1,
      "name": "hook",
      "first_frame": 1,
      "last_frame": 2,
      "motion_description": "Subtle motion only - small movements, breathing, the visual_motif beginning to appear (1-2 sentences)"
    }},
    {{
      "segment": 2,
      "name": "magic",
      "first_frame": 2,
      "last_frame": 3,
      "motion_description": "The transformation motion - visual_motif expanding/growing, lighting shift, subject's posture changing (1-2 sentences)"
    }},
    {{
      "segment": 3,
      "name": "payoff",
      "first_frame": 3,
      "last_frame": 4,
      "motion_description": "Resolution motion - visual_motif settling, subject relaxing into satisfaction, final lighting bloom (1-2 sentences)"
    }}
  ]
}}"""

    try:
        print("Calling Gemini API...")
        response = client.models.generate_content(
            model=MODEL,
            contents=script_prompt,
            config={
                "thinking_config": {"thinking_level": "medium"},
                "temperature": 0.8,
            }
        )
        print("Gemini response received")

        result_text = ""
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'text') and part.text:
                result_text += part.text

        print(f"Raw result: {result_text[:200]}...")

        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]

        parsed = json.loads(result_text.strip())
        print("Successfully parsed JSON")
        return jsonify(parsed)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# Wan API integration
WAN_API_URL = "http://localhost:5000"


@app.route("/generate-video", methods=["POST"])
def generate_video():
    """Generate videos using keyframe-to-video approach for cohesive transitions"""
    data = request.json
    keyframes = data.get("keyframes", [])
    segments = data.get("segments", [])

    print(f"=== Keyframe-to-Video Generation ===")
    print(f"Keyframes: {len(keyframes)}, Segments: {len(segments)}")

    if not keyframes or not segments:
        return jsonify({"error": "Missing keyframes or segments"}), 400

    try:
        # Step 1: Generate all keyframe images in parallel
        print("Step 1: Generating keyframe images...")
        image_tasks = []

        for kf in keyframes:
            frame_num = kf.get("frame")
            prompt = kf.get("image_prompt", "")
            print(f"  Frame {frame_num}: {prompt[:80]}...")

            response = requests.post(
                f"{WAN_API_URL}/api/generate",
                json={
                    "model": "wan2.6-image",
                    "prompt": prompt
                },
                timeout=180
            )

            result = response.json()
            if result.get("status") == "completed" and result.get("result", {}).get("urls"):
                # Sync image generation completed immediately
                image_tasks.append({
                    "frame": frame_num,
                    "status": "completed",
                    "url": result["result"]["urls"][0]
                })
            elif result.get("task_id"):
                # Async - need to poll
                image_tasks.append({
                    "frame": frame_num,
                    "status": "processing",
                    "task_id": result.get("task_id")
                })
            else:
                image_tasks.append({
                    "frame": frame_num,
                    "status": "error",
                    "error": result.get("error", "Failed to start image generation")
                })

        return jsonify({
            "status": "generating_keyframes",
            "phase": "keyframes",
            "keyframe_tasks": image_tasks,
            "segments": segments,
            "message": f"Generating {len(keyframes)} keyframe images"
        })

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Wan API not running"}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/generate-videos-from-keyframes", methods=["POST"])
def generate_videos_from_keyframes():
    """Generate videos from keyframe images using kf2v model"""
    data = request.json
    keyframe_urls = data.get("keyframe_urls", {})  # {1: url, 2: url, 3: url, 4: url}
    segments = data.get("segments", [])

    print(f"=== Generating videos from keyframes ===")
    print(f"Keyframe URLs: {list(keyframe_urls.keys())}")

    video_tasks = []

    try:
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
                    "error": f"Missing keyframe URLs for frames {first_frame} or {last_frame}"
                })
                continue

            print(f"  Segment {segment_num}: frames {first_frame}→{last_frame}")

            response = requests.post(
                f"{WAN_API_URL}/api/generate",
                json={
                    "model": "wan2.2-kf2v-flash",
                    "prompt": motion,
                    "first_frame_url": first_url,
                    "last_frame_url": last_url
                },
                timeout=180
            )

            result = response.json()
            if result.get("status") == "processing":
                video_tasks.append({
                    "segment": segment_num,
                    "status": "processing",
                    "task_id": result.get("task_id")
                })
            else:
                video_tasks.append({
                    "segment": segment_num,
                    "status": "error",
                    "error": result.get("error", "Failed to start video generation")
                })

        return jsonify({
            "status": "generating_videos",
            "phase": "videos",
            "segments": video_tasks,
            "message": f"Generating {len(video_tasks)} video segments from keyframes"
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/video-status/<task_id>")
def video_status(task_id):
    """Check video generation status for single task"""
    try:
        response = requests.get(
            f"{WAN_API_URL}/api/task/{task_id}",
            timeout=180
        )
        result = response.json()
        print(f"Task {task_id} status: {result}")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/video-status-multi", methods=["POST"])
def video_status_multi():
    """Check status of multiple video segments"""
    data = request.json
    segments = data.get("segments", [])

    results = []
    all_completed = True
    any_failed = False

    for seg in segments:
        task_id = seg.get("task_id")
        segment_num = seg.get("segment")

        try:
            response = requests.get(
                f"{WAN_API_URL}/api/task/{task_id}",
                timeout=180
            )
            result = response.json()

            segment_result = {
                "segment": segment_num,
                "task_id": task_id,
                "status": result.get("status"),
                "task_status": result.get("task_status")
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

    return jsonify({
        "segments": results,
        "all_completed": all_completed,
        "any_failed": any_failed
    })


@app.route("/stitch-videos", methods=["POST"])
def stitch_videos():
    """Download and stitch multiple video segments using ffmpeg"""
    data = request.json
    video_urls = data.get("videos", [])  # [{segment: 1, url: "..."}, ...]

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

            return jsonify({
                "status": "completed",
                "url": f"/static/{output_filename}"
            })

    except subprocess.TimeoutExpired:
        return jsonify({"error": "ffmpeg timed out"}), 500
    except Exception as e:
        print(f"Stitch error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)
