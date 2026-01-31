# Session Handoff - Visual Consistency System

**Date:** 2026-01-30

## What Was Built

A **visual consistency system** for the m(video)p demo app that ensures AI-generated video frames maintain consistent character/environment appearances.

### The Problem
Video scripts said "SAME woman, SAME shot" but each AI API call is independent with no memory → inconsistent visuals.

### The Solution
Structured data extraction + programmatic prompt assembly. Every prompt now contains FULL descriptions instead of relative references.

## Completed Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ | Schema Foundation - `demo/consistency/` with Pydantic models |
| 2 | ✅ | Extraction Integration - Claude tool_use extracts subjects/env/style |
| 3 | ✅ | Reference Image Generation - `/api/generate-reference` endpoint |
| 4 | ✅ | Prompt Assembly - `PromptAssembler` with detail levels |
| 5 | ✅ | Wan R2V Mode - `generate_video_r2v()` for subject consistency |

## Key Files

```
demo/consistency/
├── schemas.py      # SubjectSheet, EnvironmentSheet, VisualStyle
├── manager.py      # ConsistencyManager - state tracking
├── assembler.py    # PromptAssembler - builds prompts from state

demo/providers/
├── llm/anthropic.py  # extract_consistency_data() with 6 tools
├── wan.py            # generate_video_r2v() for R2V mode
├── google.py         # Imagen 3 for images

demo/app.py           # /chat extracts consistency, /api/generate-reference
demo/start            # Quick start script
```

## How It Works

1. User chats about their product → Claude extracts visual details via tool_use
2. Details stored in `ConsistencyManager` (subjects, environment, style)
3. When generating frames, `PromptAssembler` builds full prompts:
   - Keyframes: detailed (Imagen 3, no limit)
   - Video segments: compressed (<800 chars for Wan 2.6)
4. Reference images can be generated for subjects
5. Wan R2V mode uses reference images for video consistency

## Quick Start

```bash
demo/start        # Starts server at http://localhost:5001
```

## API Endpoints

- `POST /chat` - Chat + auto-extracts consistency data
- `GET /api/consistency-state` - View extracted visual details
- `POST /api/generate-reference` - Generate subject reference image

## Tests

```bash
cd demo && ../venv/bin/pytest tests/ -v
# 19 tests pass
```

## Recent Fixes

- `safety_filter_level` changed to `"block_low_and_above"` (Google API requirement)
- Test imports fixed with `sys.path.insert`
- Worktree script auto-symlinks `.env` files

## What's Left (Phase 6)

- [ ] A/B test against old approach
- [ ] Feature flag for gradual rollout
- [ ] Fix `datetime.utcnow()` deprecation warnings
- [ ] Integrate consistency prompts into `/generate-script` fully
- [ ] UI to display extracted consistency state

## Orchestrator Improvements Made

- `worktree.sh` now auto-symlinks `.env` files to worktrees
- SKILL.md updated with documentation
- Task prompts include test-based success criteria
