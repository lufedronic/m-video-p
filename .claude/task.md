# Task: Reference Image Generation (Phase 3)

## Your Assignment

Implement reference image generation for the visual consistency system. Reference images are clean portraits/headshots of subjects that will be used to maintain visual consistency across video frames.

## Files to Modify

- `demo/app.py` - Add `/api/generate-reference` endpoint
- `demo/consistency/manager.py` - Add `set_reference_url()` method
- `demo/consistency/schemas.py` - Ensure `reference_image_url` field exists on SubjectSheet

## Success Criteria (IMPORTANT)

Your task is complete when ALL tests pass:

```bash
cd demo && ../venv/bin/pytest tests/test_reference_images.py -v
```

**Run the tests frequently** as you implement. Do NOT mark this task as complete until all tests pass.

The tests define exactly what your implementation must do. Read them carefully to understand the requirements.

## What You Need to Implement

1. **SubjectSheet.reference_image_url field** - Store the URL of the generated reference
2. **ConsistencyManager.set_reference_url(subject_id, url)** - Update a subject's reference
3. **`/api/generate-reference` endpoint** that:
   - Takes `subject_id` and optional `pose` in request body
   - Uses `PromptAssembler.assemble_reference_prompt()` to build the prompt
   - Calls Imagen 3 (Google) provider to generate the image
   - Stores the result URL in the subject
   - Returns the URL or task_id for polling

## Parallel Context

Other Claude instances are working on:
- **wan-r2v**: Implementing Wan 2.6 Reference-to-Video mode (they need your reference URLs!)

**DO NOT modify files assigned to the other worktree:**
- Do NOT touch `demo/providers/wan.py`

## Dependencies

- None - can start immediately
- The consistency module (schemas.py, manager.py, assembler.py) is already complete

## Constraints

- Stay within your assigned files
- The reference prompt generation already exists in `assembler.py` - use it
- Use the Google/Imagen 3 provider for image generation (better quality than Wan for stills)

## Getting Started

1. **Read the test file first**: `demo/tests/test_reference_images.py`
2. **Create a task list** based on the tests using the TaskCreate tool
3. Update task status as you work (in_progress → completed)
4. Run tests frequently to check progress

## Commit Strategy (IMPORTANT)

**Commit after completing each major piece of work.** This lets the orchestrator track your progress.

Example commits:
1. "Add reference_image_url field to SubjectSheet"
2. "Add set_reference_url method to ConsistencyManager"
3. "Add /api/generate-reference endpoint - tests passing"

## When Done

When you've completed all tasks:
1. **Verify all tests pass**: `cd demo && ../venv/bin/pytest tests/test_reference_images.py -v`
2. Make a final commit with all changes
3. **Clearly tell the user you're done** with:
   - Summary of what was implemented
   - Confirmation that all tests pass
   - Any notes for the merge phase
