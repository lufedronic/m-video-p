"""
Anthropic Claude LLM provider implementation.
"""
import os
import json
import uuid
from typing import Optional, Any

import anthropic

from .base import LLMProvider, LLMResponse, Message


class AnthropicProvider(LLMProvider):
    """LLM provider using Anthropic Claude models."""

    MODELS = [
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ]

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = anthropic.Anthropic(api_key=api_key)

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-20250514"

    @property
    def available_models(self) -> list[str]:
        return self.MODELS

    def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        thinking: bool = False,
        max_tokens: int = 8192,
        **kwargs
    ) -> LLMResponse:
        """
        Send a chat request to Claude.

        Args:
            messages: Conversation messages
            model: Model to use
            temperature: Sampling temperature
            thinking: Enable extended thinking mode
            max_tokens: Maximum tokens in response
        """
        model = model or self.default_model

        # Extract system message if present
        system_content = None
        claude_messages = []

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            elif msg.role in ("user", "assistant"):
                claude_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        try:
            # Build request kwargs
            request_kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": claude_messages,
            }

            if system_content:
                request_kwargs["system"] = system_content

            # Handle extended thinking for Claude
            if thinking:
                # Extended thinking requires specific budget and temperature
                request_kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": 10000
                }
                # Extended thinking requires temperature = 1
                request_kwargs["temperature"] = 1.0
            else:
                request_kwargs["temperature"] = temperature

            response = self.client.messages.create(**request_kwargs)

            # Extract text and thinking from response
            result_text = ""
            thinking_text = ""

            for block in response.content:
                if block.type == "thinking":
                    thinking_text += block.thinking
                elif block.type == "text":
                    result_text += block.text

            return LLMResponse(
                content=result_text,
                model=model,
                provider=self.name,
                thinking=thinking_text if thinking_text else None
            )

        except Exception as e:
            return LLMResponse(
                content="",
                model=model,
                provider=self.name,
                error=str(e)
            )

    # ============ Consistency Extraction Tools ============

    EXTRACTION_TOOLS = [
        {
            "name": "extract_human_subject",
            "description": "Extract visual details about a human subject from the conversation for video consistency. Call this when you identify a person who will appear in the video.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Human-readable identifier (e.g., 'Main User', 'Sarah')"},
                    "role": {"type": "string", "description": "Role in the video: 'protagonist', 'supporting', 'background'"},
                    "gender": {"type": "string", "description": "Gender presentation: 'male', 'female', 'non-binary', 'ambiguous'"},
                    "age_range": {"type": "string", "description": "Apparent age: 'child', 'teen', 'young adult', 'middle-aged', 'elderly'"},
                    "build": {"type": "string", "description": "Body type: 'slim', 'athletic', 'average', 'muscular', 'heavy'"},
                    "skin_tone": {"type": "string", "description": "Skin tone description"},
                    "hair_color": {"type": "string", "description": "Hair color"},
                    "hair_style": {"type": "string", "description": "Hair style: 'short', 'medium', 'long', 'bald', etc."},
                    "eye_color": {"type": "string", "description": "Eye color if mentioned"},
                    "clothing_style": {"type": "string", "description": "Overall clothing style: 'casual', 'formal', 'sporty', etc."},
                    "clothing_description": {"type": "string", "description": "Specific clothing items mentioned"},
                    "distinguishing_features": {"type": "string", "description": "Any notable features: glasses, beard, tattoos, etc."},
                    "confidence": {"type": "string", "enum": ["confirmed", "inferred"], "description": "Whether details are explicitly stated or inferred"}
                },
                "required": ["name", "role", "confidence"]
            }
        },
        {
            "name": "extract_animal_subject",
            "description": "Extract visual details about an animal subject (pet, mascot, etc.) for video consistency.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name or identifier (e.g., 'Family Dog', 'Max')"},
                    "role": {"type": "string", "description": "Role in the video: 'pet', 'mascot', 'background'"},
                    "species": {"type": "string", "description": "Animal species: 'dog', 'cat', 'bird', etc."},
                    "breed": {"type": "string", "description": "Specific breed if mentioned"},
                    "color": {"type": "string", "description": "Fur/feather color"},
                    "pattern": {"type": "string", "description": "Color pattern: 'solid', 'spotted', 'striped'"},
                    "size": {"type": "string", "description": "Size: 'small', 'medium', 'large'"},
                    "features": {"type": "string", "description": "Distinguishing features"},
                    "confidence": {"type": "string", "enum": ["confirmed", "inferred"]}
                },
                "required": ["name", "species", "confidence"]
            }
        },
        {
            "name": "extract_object_subject",
            "description": "Extract visual details about an important object/product for video consistency.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name or identifier (e.g., 'Hero Product', 'Smartphone')"},
                    "role": {"type": "string", "description": "Role: 'product', 'hero_prop', 'background_prop'"},
                    "category": {"type": "string", "description": "Object type: 'smartphone', 'laptop', 'furniture', etc."},
                    "brand_style": {"type": "string", "description": "Design style: 'Apple-like', 'industrial', 'vintage'"},
                    "material": {"type": "string", "description": "Primary material: 'metal', 'plastic', 'wood', 'glass'"},
                    "color": {"type": "string", "description": "Primary color"},
                    "finish": {"type": "string", "description": "Surface finish: 'matte', 'glossy', 'brushed'"},
                    "key_features": {"type": "string", "description": "Visual features that make it identifiable"},
                    "confidence": {"type": "string", "enum": ["confirmed", "inferred"]}
                },
                "required": ["name", "category", "confidence"]
            }
        },
        {
            "name": "extract_environment",
            "description": "Extract details about the video's setting/environment for visual consistency.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Environment name (e.g., 'Home Office', 'Coffee Shop')"},
                    "setting_type": {"type": "string", "description": "'indoor', 'outdoor', 'studio'"},
                    "location": {"type": "string", "description": "General location type: 'office', 'home', 'street', etc."},
                    "specific_area": {"type": "string", "description": "Specific area: 'desk', 'living room', 'sidewalk'"},
                    "time_of_day": {"type": "string", "description": "'morning', 'afternoon', 'evening', 'night'"},
                    "lighting_type": {"type": "string", "description": "'natural', 'artificial', 'mixed'"},
                    "lighting_quality": {"type": "string", "description": "'soft', 'hard', 'diffused'"},
                    "mood": {"type": "string", "description": "Atmosphere: 'professional', 'cozy', 'energetic'"},
                    "color_scheme": {"type": "string", "description": "Dominant colors: 'warm earth tones', 'cool blues'"},
                    "background_elements": {"type": "string", "description": "Key background items: 'plants', 'monitors', 'windows'"},
                    "confidence": {"type": "string", "enum": ["confirmed", "inferred"]}
                },
                "required": ["name", "setting_type", "confidence"]
            }
        },
        {
            "name": "extract_visual_style",
            "description": "Extract the overall visual/cinematic style for the video.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Style name (e.g., 'Corporate Clean', 'Warm Cinematic')"},
                    "style": {"type": "string", "description": "'photorealistic', 'cinematic', 'animated', 'stylized'"},
                    "tone": {"type": "string", "description": "Color tone: 'warm', 'cool', 'neutral', 'dramatic'"},
                    "color_grade": {"type": "string", "description": "'natural', 'desaturated', 'vibrant', 'film-like'"},
                    "quality": {"type": "string", "description": "Production quality: '4K', 'cinematic', 'professional'"},
                    "shot_type": {"type": "string", "description": "Default shot framing: 'close-up', 'medium', 'wide'"},
                    "camera_angle": {"type": "string", "description": "'eye-level', 'low', 'high', 'dutch'"},
                    "visual_motif": {"type": "string", "description": "Recurring visual element or theme"},
                    "confidence": {"type": "string", "enum": ["confirmed", "inferred"]}
                },
                "required": ["name", "style", "confidence"]
            }
        },
        {
            "name": "no_extraction_needed",
            "description": "Call this if the conversation doesn't contain any new visual details to extract.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Why no extraction is needed"}
                },
                "required": ["reason"]
            }
        }
    ]

    def extract_consistency_data(
        self,
        conversation_history: list[Message],
        current_turn: int,
        model: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Extract visual consistency data from conversation using tool_use.

        Args:
            conversation_history: The full conversation so far
            current_turn: Current conversation turn number (for source tracking)
            model: Model to use (defaults to provider's default)

        Returns:
            Dict with extracted data:
            {
                "subjects": [...],  # List of subject extractions
                "environment": {...} or None,
                "style": {...} or None,
                "has_updates": bool
            }
        """
        model = model or self.default_model

        # Build extraction prompt
        system_prompt = """You are a visual consistency extractor for video generation.
Your task is to identify and extract visual details about:
1. SUBJECTS: People, animals, or important objects that appear in the video
2. ENVIRONMENT: The setting/location where the video takes place
3. VISUAL STYLE: The overall look, feel, and cinematic style

Analyze the conversation and extract any visual details mentioned or implied.
Use the tools to record each distinct element. Call multiple tools if there are multiple subjects.
If nothing new needs to be extracted, call no_extraction_needed.

IMPORTANT:
- Mark confidence as "confirmed" only for details explicitly stated by the user
- Mark confidence as "inferred" for details you're deducing from context
- Extract even partial information - we track uncertainty
- For humans, pay attention to ANY physical description, clothing, or appearance mentions
- Focus on the LATEST messages for new information"""

        # Convert conversation to Claude format
        claude_messages = []
        for msg in conversation_history:
            if msg.role in ("user", "assistant"):
                claude_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Add extraction instruction
        claude_messages.append({
            "role": "user",
            "content": "Based on our conversation, extract any visual consistency information for video generation. Call the appropriate extraction tools for each subject, the environment, and the visual style."
        })

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=claude_messages,
                tools=self.EXTRACTION_TOOLS,
                tool_choice={"type": "any"}  # Force tool use
            )

            # Parse tool calls from response
            result = {
                "subjects": [],
                "environment": None,
                "style": None,
                "has_updates": False,
                "raw_extractions": []
            }

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    # Add source turn to all extractions
                    tool_input["source_turn"] = current_turn

                    result["raw_extractions"].append({
                        "tool": tool_name,
                        "data": tool_input
                    })

                    if tool_name == "extract_human_subject":
                        result["subjects"].append({
                            "type": "human",
                            **tool_input
                        })
                        result["has_updates"] = True

                    elif tool_name == "extract_animal_subject":
                        result["subjects"].append({
                            "type": "animal",
                            **tool_input
                        })
                        result["has_updates"] = True

                    elif tool_name == "extract_object_subject":
                        result["subjects"].append({
                            "type": "object",
                            **tool_input
                        })
                        result["has_updates"] = True

                    elif tool_name == "extract_environment":
                        result["environment"] = tool_input
                        result["has_updates"] = True

                    elif tool_name == "extract_visual_style":
                        result["style"] = tool_input
                        result["has_updates"] = True

                    elif tool_name == "no_extraction_needed":
                        # No updates, keep has_updates as False
                        pass

            return result

        except Exception as e:
            return {
                "subjects": [],
                "environment": None,
                "style": None,
                "has_updates": False,
                "error": str(e)
            }

    def _build_subject_from_extraction(
        self,
        extraction: dict[str, Any],
        subject_type: str
    ) -> dict[str, Any]:
        """
        Convert raw extraction data into SubjectSheet-compatible format.

        This is a helper to transform tool output into our Pydantic schema format.
        """
        from demo.consistency.schemas import (
            SubjectType, ConfidenceLevel, Attribute,
            HumanDetails, AnimalDetails, ObjectDetails,
            HairDetails, FaceDetails, BodyDetails, ClothingDetails
        )

        confidence = ConfidenceLevel.CONFIRMED if extraction.get("confidence") == "confirmed" else ConfidenceLevel.INFERRED
        source_turn = extraction.get("source_turn")

        def make_attr(value: Optional[str]) -> Optional[Attribute]:
            if value:
                return Attribute(value=value, confidence=confidence, source_turn=source_turn)
            return None

        subject_data = {
            "id": str(uuid.uuid4()),
            "name": extraction.get("name"),
            "role": extraction.get("role"),
        }

        if subject_type == "human":
            subject_data["subject_type"] = SubjectType.HUMAN
            subject_data["human_details"] = HumanDetails(
                gender=make_attr(extraction.get("gender")),
                hair=HairDetails(
                    color=make_attr(extraction.get("hair_color")),
                    style=make_attr(extraction.get("hair_style"))
                ) if extraction.get("hair_color") or extraction.get("hair_style") else None,
                face=FaceDetails(
                    skin_tone=make_attr(extraction.get("skin_tone")),
                    eye_color=make_attr(extraction.get("eye_color")),
                    distinguishing_features=make_attr(extraction.get("distinguishing_features"))
                ) if any(extraction.get(k) for k in ["skin_tone", "eye_color", "distinguishing_features"]) else None,
                body=BodyDetails(
                    age_range=make_attr(extraction.get("age_range")),
                    build=make_attr(extraction.get("build"))
                ) if extraction.get("age_range") or extraction.get("build") else None,
                clothing=ClothingDetails(
                    style=make_attr(extraction.get("clothing_style")),
                    upper_body=make_attr(extraction.get("clothing_description"))
                ) if extraction.get("clothing_style") or extraction.get("clothing_description") else None
            )

        elif subject_type == "animal":
            subject_data["subject_type"] = SubjectType.ANIMAL
            subject_data["animal_details"] = AnimalDetails(
                species=make_attr(extraction.get("species")),
                breed=make_attr(extraction.get("breed")),
                color=make_attr(extraction.get("color")),
                pattern=make_attr(extraction.get("pattern")),
                size=make_attr(extraction.get("size")),
                features=make_attr(extraction.get("features"))
            )

        elif subject_type == "object":
            subject_data["subject_type"] = SubjectType.OBJECT
            subject_data["object_details"] = ObjectDetails(
                category=make_attr(extraction.get("category")),
                brand_style=make_attr(extraction.get("brand_style")),
                material=make_attr(extraction.get("material")),
                color=make_attr(extraction.get("color")),
                finish=make_attr(extraction.get("finish")),
                key_features=make_attr(extraction.get("key_features"))
            )

        return subject_data
