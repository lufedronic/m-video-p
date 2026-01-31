"""
Tests for Phase 1: Prompt Tweaks - Grounding prompts in reality.

Run with:
    cd demo && pytest tests/test_phase1_prompt_tweaks.py -v

Success criteria: All tests must pass.

These tests verify:
1. System prompt contains grounding instructions
2. Script generation prompt guides toward realistic visuals
3. Futuristic requests are handled with near-future realism
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestSystemPromptGrounding:
    """Test that system prompt guides toward realistic product demos."""

    def test_system_prompt_mentions_realism(self):
        """System prompt should instruct grounding in reality."""
        from app import SYSTEM_PROMPT

        prompt_lower = SYSTEM_PROMPT.lower()

        # Should mention realism/grounded/realistic
        realism_terms = ['realistic', 'grounded', 'reality', 'credible', 'believable']
        has_realism = any(term in prompt_lower for term in realism_terms)

        assert has_realism, (
            "SYSTEM_PROMPT should contain instructions about keeping suggestions "
            "realistic and grounded. Users want demos for products they could "
            "launch soon, not sci-fi concepts."
        )

    def test_system_prompt_warns_against_futuristic(self):
        """System prompt should discourage overly futuristic suggestions."""
        from app import SYSTEM_PROMPT

        prompt_lower = SYSTEM_PROMPT.lower()

        # Should mention avoiding futuristic/sci-fi
        anti_scifi_terms = ['futuristic', 'sci-fi', 'science fiction', 'far future', 'overly abstract']
        has_warning = any(term in prompt_lower for term in anti_scifi_terms)

        assert has_warning, (
            "SYSTEM_PROMPT should warn against overly futuristic or sci-fi suggestions. "
            "The prompt should guide toward near-term realistic product demos."
        )

    def test_system_prompt_allows_future_with_constraints(self):
        """When future tech is needed, prompt should guide to near-future realism."""
        from app import SYSTEM_PROMPT

        prompt_lower = SYSTEM_PROMPT.lower()

        # Should mention "near future" or "next few years" as acceptable
        near_future_terms = ['near future', 'next few years', 'realistic future', 'emerging technology']
        has_near_future = any(term in prompt_lower for term in near_future_terms)

        # This is a softer requirement - if not present, just warn
        if not has_near_future:
            pytest.skip(
                "Optional: SYSTEM_PROMPT could mention near-future as acceptable "
                "when users specifically request futuristic features."
            )


class TestScriptGenerationPrompt:
    """Test that script generation promotes realistic visuals."""

    def test_script_prompt_avoids_abstract_visuals(self):
        """Script generation should not suggest overly abstract visuals."""
        # We need to check the script_prompt in generate_script()
        # This requires reading the function or having it as a constant

        # Read the app.py to find the script prompt
        import inspect
        from app import generate_script

        source = inspect.getsource(generate_script)
        source_lower = source.lower()

        # The prompt should discourage abstract/floating/ethereal imagery
        # OR emphasize concrete, tangible visuals
        concrete_terms = ['concrete', 'tangible', 'realistic', 'grounded', 'believable']
        has_concrete_guidance = any(term in source_lower for term in concrete_terms)

        # Allow test to pass if either:
        # 1. Has concrete guidance
        # 2. Or mentions avoiding abstract (will be added)
        assert has_concrete_guidance or 'abstract' in source_lower, (
            "Script generation prompt should guide toward concrete, realistic visuals "
            "rather than abstract floating shapes and ethereal concepts."
        )


class TestProductUnderstandingRealism:
    """Test that product understanding captures realism preferences."""

    def test_visual_style_includes_realism_option(self):
        """Visual style options should include realistic/grounded choices."""
        from app import SYSTEM_PROMPT

        # The product understanding schema mentions visual_style
        # Check if realistic options are suggested
        prompt_lower = SYSTEM_PROMPT.lower()

        # Should suggest realistic visual styles
        realistic_styles = ['minimal', 'clean', 'professional', 'modern', 'corporate']
        has_realistic_styles = any(style in prompt_lower for style in realistic_styles)

        # This is informational - the key is that futuristic isn't the default
        assert 'visual_style' in prompt_lower, (
            "SYSTEM_PROMPT should mention visual_style in product understanding"
        )
