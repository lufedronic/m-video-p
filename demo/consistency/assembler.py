"""
Prompt assembler for visual consistency system.
Converts structured consistency data into optimized prompts for image/video models.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal, Optional

if TYPE_CHECKING:
    from .schemas import SubjectSheet, EnvironmentSheet, VideoConsistencyState, VisualStyle


class PromptAssembler:
    """
    Assembles structured consistency objects into optimized prompts
    for image and video generation models.

    Handles provider-specific constraints:
    - Imagen 3: Component-based budgets for different elements
    - Wan 2.6: Hard 800 character total limit

    Prompt order (matters for model attention):
    style > subject > action > environment > camera
    """

    # Imagen 3 character budgets by component
    IMAGEN3_BUDGET = {
        "foreground_subject": 150,
        "background": 30,
        "environment": 80,
        "style": 60,
        "action": 40,
        "camera": 30,
    }

    # Wan 2.6 has a hard total character limit
    WAN_BUDGET = {
        "total": 800,
        # Suggested allocation within total
        "style": 80,
        "subject": 200,
        "action": 100,
        "environment": 150,
        "camera": 50,
        "buffer": 220,  # Flexibility for compression
    }

    def _get_subject(self, subject_id: str) -> Optional["SubjectSheet"]:
        """Get a subject by ID from the subjects list."""
        if not self.state or not self.state.subjects:
            return None
        for subject in self.state.subjects:
            if subject.id == subject_id:
                return subject
        return None

    def __init__(self, state: Optional["VideoConsistencyState"] = None):
        """
        Initialize assembler with optional consistency state.

        Args:
            state: VideoConsistencyState containing subjects, environments, and style
        """
        self.state = state

    def set_state(self, state: "VideoConsistencyState") -> None:
        """Update the consistency state."""
        self.state = state

    def assemble_keyframe_prompt(
        self,
        subject_ids: list[str],
        environment_id: Optional[str] = None,
        action: Optional[str] = None,
        camera: Optional[str] = None,
        foreground_subjects: Optional[list[str]] = None,
        provider: Literal["imagen3", "wan"] = "imagen3",
    ) -> str:
        """
        Assemble a prompt for keyframe (image) generation.

        Keyframes get more detailed prompts since images can handle
        more visual complexity than video frames.

        Args:
            subject_ids: List of subject IDs to include in the scene
            environment_id: Optional environment ID for scene context
            action: Optional action description for the subject(s)
            camera: Optional camera angle/shot type
            foreground_subjects: Subject IDs that should get full detail (rest get minimal)
            provider: Target provider for budget optimization

        Returns:
            Assembled prompt string optimized for the target provider
        """
        if not self.state:
            raise ValueError("No consistency state set. Call set_state() first.")

        foreground_subjects = foreground_subjects or subject_ids
        parts: list[str] = []

        # 1. Style (highest priority)
        if self.state.style:
            style_block = self._get_style_block(detail_level="full")
            if style_block:
                parts.append(style_block)

        # 2. Subjects (foreground = full detail, background = minimal)
        for sid in subject_ids:
            sheet = self._get_subject(sid)
            if not sheet:
                continue
            detail = "full" if sid in foreground_subjects else "minimal"
            subject_block = sheet.to_prompt_block(detail_level=detail)
            if subject_block:
                parts.append(subject_block)

        # 3. Action
        if action:
            parts.append(action.strip())

        # 4. Environment
        if environment_id and self.state.environment and self.state.environment.id == environment_id:
            env_sheet = self.state.environment
            env_block = env_sheet.to_prompt_block(detail_level="medium")
            if env_block:
                parts.append(env_block)

        # 5. Camera
        if camera:
            parts.append(camera.strip())

        # Join and apply provider-specific optimization
        prompt = ", ".join(filter(None, parts))

        if provider == "wan":
            prompt = self._compress_for_wan(prompt)

        return prompt

    def assemble_video_segment_prompt(
        self,
        subject_ids: list[str],
        environment_id: Optional[str] = None,
        action: Optional[str] = None,
        camera: Optional[str] = None,
        motion_hint: Optional[str] = None,
    ) -> str:
        """
        Assemble a prompt for video segment generation.

        Video prompts MUST stay under 800 characters for Wan 2.6.
        Uses aggressive compression and prioritizes motion/action.

        Args:
            subject_ids: List of subject IDs in the scene
            environment_id: Optional environment ID
            action: Action/motion description (prioritized for video)
            camera: Camera movement description
            motion_hint: Additional motion guidance

        Returns:
            Compressed prompt string under 800 characters
        """
        if not self.state:
            raise ValueError("No consistency state set. Call set_state() first.")

        parts: list[str] = []

        # 1. Style (compressed for video)
        if self.state.style:
            style_block = self._get_style_block(detail_level="minimal")
            if style_block:
                parts.append(style_block)

        # 2. Primary subject only, medium detail
        # For video, focus on the first/main subject
        if subject_ids:
            main_subject = self._get_subject(subject_ids[0])
            if main_subject:
                subject_block = main_subject.to_prompt_block(detail_level="medium")
                if subject_block:
                    parts.append(subject_block)

        # 3. Action (critical for video - gets priority)
        if action:
            parts.append(action.strip())

        # 4. Motion hint
        if motion_hint:
            parts.append(motion_hint.strip())

        # 5. Environment (minimal for video)
        if environment_id and self.state.environment and self.state.environment.id == environment_id:
            env_sheet = self.state.environment
            env_block = env_sheet.to_prompt_block(detail_level="minimal")
            if env_block:
                parts.append(env_block)

        # 6. Camera movement
        if camera:
            parts.append(camera.strip())

        # Join and compress to meet Wan limit
        prompt = ", ".join(filter(None, parts))
        prompt = self._compress_for_wan(prompt)

        return prompt

    def assemble_reference_prompt(
        self,
        subject_id: str,
        pose: Optional[str] = None,
        background: str = "plain white background",
    ) -> str:
        """
        Assemble a prompt for generating a reference image of a subject.

        Reference images are used to establish visual consistency
        before generating scenes. They should be clear, well-lit,
        and focus entirely on the subject.

        Args:
            subject_id: ID of the subject to generate reference for
            pose: Optional pose/orientation for the reference
            background: Background description (default: plain white)

        Returns:
            Prompt optimized for clear reference image generation
        """
        if not self.state:
            raise ValueError("No consistency state set. Call set_state() first.")

        sheet = self._get_subject(subject_id)
        if not sheet:
            raise ValueError(f"Subject '{subject_id}' not found in consistency state")
        parts: list[str] = []

        # Style if available (for consistent look)
        if self.state.style:
            style_block = self._get_style_block(detail_level="medium")
            if style_block:
                parts.append(style_block)

        # Full subject description for reference
        subject_block = sheet.to_prompt_block(detail_level="full")
        if subject_block:
            parts.append(subject_block)

        # Pose/orientation
        if pose:
            parts.append(pose.strip())

        # Clean background for clarity
        parts.append(background)

        # Reference-specific instructions
        parts.append("clear lighting, full visibility, reference sheet style")

        return ", ".join(filter(None, parts))

    def _get_style_block(self, detail_level: Literal["full", "medium", "minimal"]) -> str:
        """Extract style information at the specified detail level."""
        if not self.state or not self.state.style:
            return ""

        style = self.state.style

        # Try to use to_prompt_block if available
        if hasattr(style, "to_prompt_block"):
            return style.to_prompt_block(detail_level=detail_level)

        # Fallback: construct from known attributes
        parts = []

        if hasattr(style, "aesthetic") and style.aesthetic:
            parts.append(style.aesthetic)

        if detail_level in ("full", "medium"):
            if hasattr(style, "color_palette") and style.color_palette:
                parts.append(style.color_palette)
            if hasattr(style, "lighting") and style.lighting:
                parts.append(style.lighting)

        if detail_level == "full":
            if hasattr(style, "mood") and style.mood:
                parts.append(style.mood)
            if hasattr(style, "rendering_style") and style.rendering_style:
                parts.append(style.rendering_style)

        return ", ".join(filter(None, parts))

    def _compress_for_wan(self, prompt: str, target_length: int = 800) -> str:
        """
        Compress a prompt to fit within Wan 2.6's character limit.

        Compression strategies (applied in order):
        1. Remove redundant whitespace
        2. Remove filler phrases
        3. Abbreviate common terms
        4. Truncate at sentence boundary if still over

        Args:
            prompt: Original prompt text
            target_length: Maximum character count (default: 800)

        Returns:
            Compressed prompt under target_length
        """
        if len(prompt) <= target_length:
            return prompt

        # Strategy 1: Normalize whitespace
        prompt = " ".join(prompt.split())
        prompt = re.sub(r"\s*,\s*", ", ", prompt)
        prompt = re.sub(r",+", ",", prompt)

        if len(prompt) <= target_length:
            return prompt

        # Strategy 2: Remove filler phrases
        filler_phrases = [
            r"\bvery\s+",
            r"\breally\s+",
            r"\bextremely\s+",
            r"\bquite\s+",
            r"\bsomewhat\s+",
            r"\ba bit\s+",
            r"\bslightly\s+",
            r"\bin the style of\b",
            r"\bwith a\s+",
            r"\bthat is\s+",
            r"\bwhich is\s+",
            r"\band also\b",
            r"\bas well as\b",
        ]

        for pattern in filler_phrases:
            if len(prompt) <= target_length:
                break
            prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)

        # Clean up any double spaces or commas created
        prompt = " ".join(prompt.split())
        prompt = re.sub(r",\s*,", ",", prompt)
        prompt = re.sub(r"^\s*,\s*", "", prompt)

        if len(prompt) <= target_length:
            return prompt

        # Strategy 3: Abbreviate common terms
        abbreviations = [
            (r"\bbackground\b", "bg"),
            (r"\bforeground\b", "fg"),
            (r"\bcharacter\b", "char"),
            (r"\benvironment\b", "env"),
            (r"\bphotorealistic\b", "photreal"),
            (r"\bhigh quality\b", "HQ"),
            (r"\bhigh resolution\b", "hi-res"),
            (r"\bcinematic lighting\b", "cinema light"),
            (r"\bprofessional\b", "pro"),
            (r"\bdetailed\b", "detail"),
        ]

        for pattern, replacement in abbreviations:
            if len(prompt) <= target_length:
                break
            prompt = re.sub(pattern, replacement, prompt, flags=re.IGNORECASE)

        if len(prompt) <= target_length:
            return prompt

        # Strategy 4: Truncate at natural boundary
        # Try to cut at last comma before limit
        truncated = prompt[:target_length]
        last_comma = truncated.rfind(",")
        last_period = truncated.rfind(".")

        cut_point = max(last_comma, last_period)
        if cut_point > target_length * 0.7:  # Don't cut too much
            prompt = prompt[:cut_point].strip()
        else:
            # Hard truncate at word boundary
            prompt = prompt[:target_length]
            last_space = prompt.rfind(" ")
            if last_space > target_length * 0.8:
                prompt = prompt[:last_space]

        return prompt.strip().rstrip(",").strip()

    def estimate_prompt_length(
        self,
        subject_ids: list[str],
        environment_id: Optional[str] = None,
        action: Optional[str] = None,
        camera: Optional[str] = None,
        prompt_type: Literal["keyframe", "video"] = "keyframe",
    ) -> dict[str, int]:
        """
        Estimate the length of a prompt before assembling it.

        Useful for planning and debugging prompt budget issues.

        Returns:
            Dict with component lengths and total
        """
        estimates = {
            "style": 0,
            "subjects": 0,
            "action": 0,
            "environment": 0,
            "camera": 0,
            "total": 0,
        }

        if not self.state:
            return estimates

        detail = "full" if prompt_type == "keyframe" else "medium"

        if self.state.style:
            style_block = self._get_style_block(detail_level=detail)
            estimates["style"] = len(style_block)

        for sid in subject_ids:
            sheet = self._get_subject(sid)
            if sheet:
                block = sheet.to_prompt_block(detail_level=detail)
                estimates["subjects"] += len(block)

        if action:
            estimates["action"] = len(action)

        if environment_id and self.state.environment and self.state.environment.id == environment_id:
            env_sheet = self.state.environment
            env_detail = "medium" if prompt_type == "keyframe" else "minimal"
            block = env_sheet.to_prompt_block(detail_level=env_detail)
            estimates["environment"] = len(block)

        if camera:
            estimates["camera"] = len(camera)

        # Account for separators (", " = 2 chars each)
        num_parts = sum(1 for v in estimates.values() if v > 0)
        separator_chars = max(0, num_parts - 1) * 2

        estimates["total"] = sum(estimates.values()) + separator_chars

        return estimates


def create_assembler(state: Optional["VideoConsistencyState"] = None) -> PromptAssembler:
    """Factory function to create a PromptAssembler instance."""
    return PromptAssembler(state=state)
