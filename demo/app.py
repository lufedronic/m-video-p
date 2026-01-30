"""
m(video)p - Generate product demo videos from just an idea
"""
import os
import json
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
1. Videos are max 15 seconds - focus on ONE killer moment, not a product tour. Think "viral hook" not "explainer video".
2. AI video cannot render readable text/UI reliably. Turn this into a FEATURE by recommending stylized approaches:
   - Wireframe aesthetic: text shown as gray bars/lines (like real UI wireframes, "greeking")
   - Shallow depth of field: screen slightly blurred, human/context sharp
   - Abstract/symbolic UI: glowing cards, floating shapes, animated icons
   - This communicates "concept" which fits a POC video and reduces cognitive load

Start with LOW confidence and build up as you learn more. Mark ready_for_video=true only when confidence > 0.8 and you have enough detail for a compelling 15-second demo.

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
- Max 15 seconds. This is a viral hook, not an explainer. Focus on ONE killer moment.
- AI video CANNOT render readable text/UI. Design visuals that work around this:
  * Use wireframe aesthetic: represent text as gray bars/lines (standard "greeking" convention)
  * Use shallow depth of field: screen slightly soft, human/environment sharp
  * Use abstract/symbolic UI: glowing cards, floating shapes, animated icons
  * This "concept visualization" style communicates POC and focuses viewers on flow, not content

Create a script with 2-3 scenes max:
1. Hook (0-3s): Instant attention grab - the problem or "what if"
2. Magic moment (3-12s): Show the ONE thing that makes this product special
3. Payoff (12-15s): Result + product name + CTA

Output as JSON:
{{
  "title": "Video title",
  "scenes": [
    {{
      "timestamp": "0:00-0:03",
      "type": "hook",
      "visual": "Description of what's shown",
      "narration": "Voiceover text (keep it SHORT)",
      "text_overlay": "On-screen text if any"
    }}
  ],
  "music_mood": "Suggested music style",
  "total_duration": "15s"
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


if __name__ == "__main__":
    app.run(debug=True, port=5001)
