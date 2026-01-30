"""
Base abstractions for image and video generation providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import base64
import io


@dataclass
class ImageData:
    """Unified image data container that handles both URL and base64 formats."""
    url: Optional[str] = None
    base64_data: Optional[str] = None
    mime_type: str = "image/png"

    def to_base64(self) -> Optional[str]:
        """Return base64-encoded image data."""
        return self.base64_data

    def to_bytes(self) -> Optional[bytes]:
        """Return raw image bytes."""
        if self.base64_data:
            return base64.b64decode(self.base64_data)
        return None

    def to_url(self, cache_func=None) -> Optional[str]:
        """
        Return URL for the image.
        If only base64 data is available and cache_func is provided,
        use it to cache the image and return a URL.
        """
        if self.url:
            return self.url
        if self.base64_data and cache_func:
            return cache_func(self.to_bytes(), self.mime_type)
        return None

    def has_data(self) -> bool:
        """Check if this ImageData contains any image data."""
        return bool(self.url or self.base64_data)


@dataclass
class GenerationTask:
    """
    Represents an ongoing or completed generation task.
    Works for both image and video generation across providers.
    """
    provider: str
    task_type: str  # "image" or "video"
    task_id: str
    status: str = "pending"  # "pending", "processing", "completed", "error"

    # For images
    result: Optional[ImageData] = None

    # For videos
    result_url: Optional[str] = None
    result_bytes: Optional[bytes] = None

    # Error information
    error: Optional[str] = None

    # Provider-specific data (for polling)
    provider_data: dict = field(default_factory=dict)

    def is_complete(self) -> bool:
        """Check if task has finished (successfully or with error)."""
        return self.status in ("completed", "error")

    def is_success(self) -> bool:
        """Check if task completed successfully."""
        return self.status == "completed"


class ImageProvider(ABC):
    """Abstract base class for image generation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass

    @abstractmethod
    def generate_image(self, prompt: str, **kwargs) -> GenerationTask:
        """
        Start image generation.
        Returns a GenerationTask that may be immediately complete (sync)
        or require polling (async).
        """
        pass

    @abstractmethod
    def poll_task(self, task: GenerationTask) -> GenerationTask:
        """
        Poll an in-progress task for status updates.
        Returns updated task with current status and results if complete.
        """
        pass


class VideoProvider(ABC):
    """Abstract base class for video generation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass

    @abstractmethod
    def generate_video(
        self,
        prompt: str,
        first_frame: Optional[ImageData] = None,
        last_frame: Optional[ImageData] = None,
        **kwargs
    ) -> GenerationTask:
        """
        Start video generation.
        For keyframe-to-video, provide first_frame and last_frame.
        Returns a GenerationTask that typically requires polling.
        """
        pass

    @abstractmethod
    def poll_task(self, task: GenerationTask) -> GenerationTask:
        """
        Poll an in-progress task for status updates.
        Returns updated task with current status and results if complete.
        """
        pass
