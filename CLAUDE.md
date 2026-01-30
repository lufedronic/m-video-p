# HackerSquad - AI Product Demo Video Generator

## Project Vision

**Goal:** Enable people to test product ideas without building any product. Using AI image/video models, generate "launch-style" demo videos from just a product description.

**Example use case:** A founder describes their SaaS idea → system generates a professional demo video showing the hypothetical product in action → founder uses video to validate market interest before building anything.

## Key Research Findings (Jan 2026)

### The Opportunity
- **Market gap exists:** No tool generates product demos for products that don't exist yet
- **Validation precedent:** Dropbox's 3-min demo video drove signups from 5K→75K overnight
- **Demo automation market:** $2.1B in 2026, growing to $7.8B by 2033

### Technical Reality
| Capability | Status |
|------------|--------|
| AI video (general scenes) | Mature (Sora 2, Veo 3, Wan 2.6) |
| AI video (UI/text rendering) | **NOT reliable** |
| Text-to-UI generation | Good (v0, Lovable) |
| AI avatars/voiceover | Mature (Synthesia, HeyGen) |

**Critical insight:** AI video can't reliably render software UIs. Solution: Generate real UI with v0/Lovable → screen record → composite with AI video for context.

### Recommended Stack
- **LLM:** Gemini 3 Flash Preview with high thinking (context gathering)
- **Agent framework:** LangGraph (fastest, most efficient)
- **UI generation:** v0 by Vercel or Lovable
- **Video APIs:** Pika Labs (best API), Wan 2.6 (local option)
- **Avatars:** Synthesia or HeyGen

## Gemini SDK Usage (IMPORTANT)

**Model:** `gemini-3-flash-preview` with thinking enabled

**Always check latest docs:** https://ai.google.dev/gemini-api/docs

```python
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Your prompt here",
    config={
        "thinking_config": {"thinking_budget": 10000}  # High thinking
    }
)
```

**Key points:**
- Use `google-genai` package (not the old `google-generativeai`)
- Thinking budget: 0-24576 tokens (use 10000+ for complex reasoning)
- Access thinking: `response.candidates[0].content.parts` (look for thought parts)

### Research Documents
See `research/SYNTHESIS.md` for full analysis. Individual docs in:
- `research/video-gen/` - Video model capabilities
- `research/ui-generation/` - UI mockup tools
- `research/agent-systems/` - Agent orchestration
- `research/competitors/` - Competitive landscape
- `research/user-research/` - User needs & validation

---

# Alibaba Wan API Testing Interface

Flask-based testing interface for Alibaba DashScope Wan video/image generation models.

## Quick Reference

### API Regions
- **Singapore**: `https://dashscope-intl.aliyuncs.com/api/v1` (default)
- **Virginia**: `https://dashscope-us.aliyuncs.com/api/v1`
- **Beijing**: `https://dashscope.aliyuncs.com/api/v1`

Set via `DASHSCOPE_BASE_URL` env var. Each region needs its own API key.

### Authentication
```
Authorization: Bearer <ALIBABA_API_KEY>
```

### Key Models
| Model | Type | Notes |
|-------|------|-------|
| `wan2.6-image` | T2I/Edit | Sync multimodal endpoint |
| `wan2.6-t2v` | T2V | **HTTP only** - no SDK |
| `wan2.6-i2v` | I2V | Async, needs img_url |
| `wan2.6-i2v-flash` | I2V | Faster, audio support |
| `wan2.6-r2v` | R2V | May not be documented yet |
| `wan2.2-kf2v-flash` | First/Last Frame | 5s fixed |
| `wan2.2-s2v` | Lip-sync | Needs image + audio |

### API Flow (Video)
1. POST to create task → get `task_id`
2. GET `/tasks/{task_id}` to poll (every ~15s)
3. Status: `PENDING` → `RUNNING` → `SUCCEEDED`/`FAILED`
4. Video URL expires in 24 hours

### Required Headers
- `Content-Type: application/json`
- `Authorization: Bearer <key>`
- `X-DashScope-Async: enable` (for async calls)

### Constraints
- Images: JPEG/PNG/BMP/WEBP, 360-2000px, max 10MB
- Audio: WAV/MP3, 3-30s, max 15MB
- Video duration: 2-15s (model dependent)

## Project Structure
```
app.py          - Flask backend
templates/      - Web UI
docs/           - Full API reference
data/           - History & saved prompts (gitignored)
```

## Running
```bash
./run.sh
# or: python app.py
```
Open http://localhost:5000

## Full Documentation
See `docs/alibaba-api-reference.md` for complete API details.
