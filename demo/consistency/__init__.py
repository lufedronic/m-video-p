"""
Visual consistency system for demo video generation.

This package provides tools for maintaining visual consistency
across generated images and video segments.
"""
from .assembler import PromptAssembler, create_assembler

__all__ = ["PromptAssembler", "create_assembler"]
