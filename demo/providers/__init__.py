"""
Provider factory and registry for image/video generation.
"""
import os
from typing import Optional

from .base import ImageProvider, VideoProvider, ImageData, GenerationTask

# Registry of available providers
_image_providers: dict[str, type[ImageProvider]] = {}
_video_providers: dict[str, type[VideoProvider]] = {}


def register_image_provider(name: str, provider_class: type[ImageProvider]):
    """Register an image provider class."""
    _image_providers[name] = provider_class


def register_video_provider(name: str, provider_class: type[VideoProvider]):
    """Register a video provider class."""
    _video_providers[name] = provider_class


def get_image_provider(name: Optional[str] = None) -> ImageProvider:
    """
    Get an image provider instance.
    If name is None, uses IMAGE_PROVIDER env var or defaults to 'wan'.
    """
    if name is None:
        name = os.getenv("IMAGE_PROVIDER", "wan")

    if name not in _image_providers:
        available = list(_image_providers.keys())
        raise ValueError(f"Unknown image provider '{name}'. Available: {available}")

    return _image_providers[name]()


def get_video_provider(name: Optional[str] = None) -> VideoProvider:
    """
    Get a video provider instance.
    If name is None, uses VIDEO_PROVIDER env var or defaults to 'wan'.
    """
    if name is None:
        name = os.getenv("VIDEO_PROVIDER", "wan")

    if name not in _video_providers:
        available = list(_video_providers.keys())
        raise ValueError(f"Unknown video provider '{name}'. Available: {available}")

    return _video_providers[name]()


def list_providers() -> dict:
    """List all registered providers."""
    return {
        "image": list(_image_providers.keys()),
        "video": list(_video_providers.keys())
    }


# Import and register providers
from .wan import WanImageProvider, WanVideoProvider
from .google import GeminiImageProvider, VeoVideoProvider

register_image_provider("wan", WanImageProvider)
register_video_provider("wan", WanVideoProvider)
register_image_provider("google", GeminiImageProvider)
register_video_provider("google", VeoVideoProvider)


__all__ = [
    "ImageProvider",
    "VideoProvider",
    "ImageData",
    "GenerationTask",
    "get_image_provider",
    "get_video_provider",
    "list_providers",
]
