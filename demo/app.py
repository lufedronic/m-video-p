"""
m(video)p - Generate product demo videos from just an idea
"""
import os
import json
import requests
from flask import Flask, request, jsonify, render_template, session
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

CONSTRAINTS:
- Generate THREE separate 5-second video segments that will be combined into one 15-second video
- AI video CANNOT render ANY text. NEVER include text, words, UI, screens with content, or readable elements
- Use ONLY: visual metaphors, light/particle effects, human emotions, object transformations, environmental changes

Structure (3 segments, 5 seconds each):
1. HOOK (0-5s): Visual attention grab - show the problem through emotion/environment
2. MAGIC (5-10s): The transformation - abstract visual representation of the solution
3. PAYOFF (10-15s): The result - human satisfaction, visual resolution, brand feeling

Output as JSON:
{{
  "title": "Video title",
  "segments": [
    {{
      "segment": 1,
      "name": "hook",
      "duration": "5s",
      "video_prompt": "EXTREMELY DETAILED 5-second video prompt (150-200 words). Be hyper-specific: exact camera movement (slow dolly in, 45-degree arc, etc), precise lighting setup (key light position, rim lighting, color temperature), detailed environment (materials, textures, atmosphere), frame-by-frame subject actions, specific color hex codes or references, emotional tone. NO TEXT/UI/WORDS. Cinematic 4K quality. Include render style (photorealistic, Unreal Engine 5, etc)."
    }},
    {{
      "segment": 2,
      "name": "magic",
      "duration": "5s",
      "video_prompt": "EXTREMELY DETAILED 5-second video prompt (150-200 words). Must visually connect to segment 1 with consistent lighting/color. Describe the transformation frame-by-frame: what morphs, how light changes, particle effects, camera reaction. Abstract but SPECIFIC. NO TEXT/UI/WORDS."
    }},
    {{
      "segment": 3,
      "name": "payoff",
      "duration": "5s",
      "video_prompt": "EXTREMELY DETAILED 5-second video prompt (150-200 words). Visual resolution of the story. Describe: final camera position, lighting climax, subject's emotional state or environmental transformation, how motion settles. Must feel like satisfying conclusion. NO TEXT/UI/WORDS."
    }}
  ],
  "visual_style": "Overall cinematic style description",
  "color_palette": "Primary colors used across all segments"
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
    """Send 3 segment prompts to Wan API for parallel video generation"""
    data = request.json
    segments = data.get("segments", [])

    # Fallback for old single-prompt format
    if not segments and data.get("video_prompt"):
        segments = [{"video_prompt": data.get("video_prompt"), "segment": 1}]

    print(f"=== Generating {len(segments)} video segments ===")

    task_ids = []
    errors = []

    try:
        # Launch all segments in parallel
        for seg in segments:
            prompt = seg.get("video_prompt", "")
            segment_num = seg.get("segment", 1)
            print(f"Segment {segment_num}: {prompt[:100]}...")

            response = requests.post(
                f"{WAN_API_URL}/api/generate",
                json={
                    "model": "wan2.6-t2v",
                    "prompt": prompt,
                    "duration": 5
                },
                timeout=30
            )

            result = response.json()
            print(f"Segment {segment_num} response: {result.get('status')}")

            if result.get("status") == "processing":
                task_ids.append({
                    "segment": segment_num,
                    "task_id": result.get("task_id"),
                    "status": "processing"
                })
            else:
                errors.append(f"Segment {segment_num}: {result.get('error', 'Unknown error')}")

        if errors and not task_ids:
            return jsonify({"error": "; ".join(errors)}), 500

        return jsonify({
            "status": "processing",
            "segments": task_ids,
            "total_segments": len(segments),
            "message": f"Generating {len(task_ids)} video segments in parallel"
        })

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Wan API not running. Start it with: cd /Users/lucas/dev/hackersquad && ./run.sh"}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/video-status/<task_id>")
def video_status(task_id):
    """Check video generation status for single task"""
    try:
        response = requests.get(
            f"{WAN_API_URL}/api/task/{task_id}",
            timeout=30
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
                timeout=30
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


if __name__ == "__main__":
    app.run(debug=True, port=5001)
