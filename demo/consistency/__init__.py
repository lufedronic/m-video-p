"""
Visual Consistency Module for Video Generation.

This module provides schemas and state management for maintaining
visual consistency across video frames and segments.

Main components:
- SubjectSheet: Unified schema for humans, animals, and objects
- EnvironmentSheet: Environment/setting configuration
- VisualStyle: Cinematic and visual style settings
- VideoConsistencyState: Complete state container
- ConsistencyManager: State tracking and persistence
- PromptAssembler: Assembles optimized prompts for image/video generation
"""
from .schemas import (
    # Enums
    ConfidenceLevel,
    SubjectType,
    # Base models
    Attribute,
    # Detail models
    HairDetails,
    FaceDetails,
    ClothingDetails,
    BodyDetails,
    HumanDetails,
    AnimalDetails,
    ObjectDetails,
    LightingDetails,
    CameraDetails,
    # Main sheets
    SubjectSheet,
    EnvironmentSheet,
    VisualStyle,
    VideoConsistencyState,
)

from .manager import ConsistencyManager
from .assembler import PromptAssembler, create_assembler

__all__ = [
    # Enums
    "ConfidenceLevel",
    "SubjectType",
    # Base models
    "Attribute",
    # Detail models
    "HairDetails",
    "FaceDetails",
    "ClothingDetails",
    "BodyDetails",
    "HumanDetails",
    "AnimalDetails",
    "ObjectDetails",
    "LightingDetails",
    "CameraDetails",
    # Main sheets
    "SubjectSheet",
    "EnvironmentSheet",
    "VisualStyle",
    "VideoConsistencyState",
    # Manager
    "ConsistencyManager",
    # Assembler
    "PromptAssembler",
    "create_assembler",
]
