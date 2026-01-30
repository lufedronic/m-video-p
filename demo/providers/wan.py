"""
Wan (Alibaba DashScope) provider implementation.
Wraps the existing Wan API calls for image and video generation.
"""
import os
import uuid
import requests
from typing import Optional

from .base import ImageProvider, VideoProvider, ImageData, GenerationTask


class WanImageProvider(ImageProvider):
    """Image generation using Wan 2.6 Image model via local API proxy."""

    def __init__(self):
        self.api_url = os.getenv("WAN_API_URL", "http://localhost:5000")
        self.timeout = 180

    @property
    def name(self) -> str:
        return "wan"

    def generate_image(self, prompt: str, **kwargs) -> GenerationTask:
        """Generate an image using wan2.6-image model."""
        task_id = str(uuid.uuid4())
        task = GenerationTask(
            provider=self.name,
            task_type="image",
            task_id=task_id,
            status="processing"
        )

        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": "wan2.6-image",
                    "prompt": prompt
                },
                timeout=self.timeout
            )
            result = response.json()

            if result.get("status") == "completed" and result.get("result", {}).get("urls"):
                # Sync completion
                task.status = "completed"
                task.result = ImageData(url=result["result"]["urls"][0])
            elif result.get("task_id"):
                # Async - need to poll
                task.task_id = result["task_id"]
                task.status = "processing"
                task.provider_data = {"wan_task_id": result["task_id"]}
            else:
                task.status = "error"
                task.error = result.get("error", "Failed to start image generation")

        except requests.exceptions.ConnectionError:
            task.status = "error"
            task.error = "Wan API not running at " + self.api_url
        except Exception as e:
            task.status = "error"
            task.error = str(e)

        return task

    def poll_task(self, task: GenerationTask) -> GenerationTask:
        """Poll Wan API for task status."""
        if task.is_complete():
            return task

        wan_task_id = task.provider_data.get("wan_task_id", task.task_id)

        try:
            response = requests.get(
                f"{self.api_url}/api/task/{wan_task_id}",
                timeout=self.timeout
            )
            result = response.json()

            if result.get("status") == "completed":
                urls = result.get("result", {}).get("urls", [])
                if urls:
                    task.status = "completed"
                    task.result = ImageData(url=urls[0])
                else:
                    task.status = "error"
                    task.error = "No image URL in response"
            elif result.get("status") == "error":
                task.status = "error"
                task.error = result.get("error", "Generation failed")
            else:
                task.status = "processing"
                task.provider_data["task_status"] = result.get("task_status", "RUNNING")

        except Exception as e:
            task.status = "error"
            task.error = str(e)

        return task


class WanVideoProvider(VideoProvider):
    """Video generation using Wan 2.2 KF2V Flash model via local API proxy."""

    def __init__(self):
        self.api_url = os.getenv("WAN_API_URL", "http://localhost:5000")
        self.timeout = 180

    @property
    def name(self) -> str:
        return "wan"

    def generate_video(
        self,
        prompt: str,
        first_frame: Optional[ImageData] = None,
        last_frame: Optional[ImageData] = None,
        **kwargs
    ) -> GenerationTask:
        """Generate video using wan2.2-kf2v-flash (keyframe to video)."""
        task_id = str(uuid.uuid4())
        task = GenerationTask(
            provider=self.name,
            task_type="video",
            task_id=task_id,
            status="processing"
        )

        # Get URLs for the frames - Wan requires URLs
        first_url = first_frame.url if first_frame else None
        last_url = last_frame.url if last_frame else None

        if not first_url or not last_url:
            task.status = "error"
            task.error = "Wan video provider requires image URLs for first and last frames"
            return task

        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": "wan2.2-kf2v-flash",
                    "prompt": prompt,
                    "first_frame_url": first_url,
                    "last_frame_url": last_url
                },
                timeout=self.timeout
            )
            result = response.json()

            if result.get("status") == "processing":
                task.task_id = result.get("task_id", task_id)
                task.status = "processing"
                task.provider_data = {"wan_task_id": result["task_id"]}
            elif result.get("status") == "completed":
                task.status = "completed"
                task.result_url = result.get("result", {}).get("url")
            else:
                task.status = "error"
                task.error = result.get("error", "Failed to start video generation")

        except requests.exceptions.ConnectionError:
            task.status = "error"
            task.error = "Wan API not running at " + self.api_url
        except Exception as e:
            task.status = "error"
            task.error = str(e)

        return task

    def poll_task(self, task: GenerationTask) -> GenerationTask:
        """Poll Wan API for video task status."""
        if task.is_complete():
            return task

        wan_task_id = task.provider_data.get("wan_task_id", task.task_id)

        try:
            response = requests.get(
                f"{self.api_url}/api/task/{wan_task_id}",
                timeout=self.timeout
            )
            result = response.json()

            if result.get("status") == "completed":
                url = result.get("result", {}).get("url")
                if url:
                    task.status = "completed"
                    task.result_url = url
                else:
                    task.status = "error"
                    task.error = "No video URL in response"
            elif result.get("status") == "error":
                task.status = "error"
                task.error = result.get("error", "Video generation failed")
            else:
                task.status = "processing"
                task.provider_data["task_status"] = result.get("task_status", "RUNNING")

        except Exception as e:
            task.status = "error"
            task.error = str(e)

        return task
