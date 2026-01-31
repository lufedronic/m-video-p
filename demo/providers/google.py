"""
Google provider implementation using Gemini Image (Nano Banana Pro) and Veo 3.1.
"""
import os
import io
import uuid
import base64
import time
from typing import Optional

from google import genai
from google.genai import types

from .base import ImageProvider, VideoProvider, ImageData, GenerationTask


def _get_client():
    """Get or create the Gemini client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    return genai.Client(api_key=api_key)


class GeminiImageProvider(ImageProvider):
    """
    Image generation using Gemini's Imagen model.
    This is synchronous - returns immediately with base64 image data.
    """

    def __init__(self):
        # Use Imagen 4 for image generation (Imagen 3 was shut down Jan 2026)
        # Options: imagen-4.0-generate-001, imagen-4.0-ultra-generate-001, imagen-4.0-fast-generate-001
        self.model = "imagen-4.0-generate-001"

    @property
    def name(self) -> str:
        return "google"

    def generate_image(self, prompt: str, **kwargs) -> GenerationTask:
        """
        Generate an image using Google's Imagen model.
        Returns synchronously with base64 image data.
        """
        task_id = str(uuid.uuid4())
        task = GenerationTask(
            provider=self.name,
            task_type="image",
            task_id=task_id,
            status="processing"
        )

        try:
            client = _get_client()

            print(f"[GeminiImageProvider] Generating image with model: {self.model}")
            print(f"[GeminiImageProvider] Prompt: {prompt[:100]}...")

            # Use Imagen for image generation
            response = client.models.generate_images(
                model=self.model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                    safety_filter_level="block_low_and_above",
                )
            )

            print(f"[GeminiImageProvider] Response received, images: {len(response.generated_images) if response.generated_images else 0}")

            # Extract image from response
            if response.generated_images and len(response.generated_images) > 0:
                image = response.generated_images[0]
                # The image data is in image.image (bytes)
                if hasattr(image, 'image') and image.image:
                    # image.image is a PIL Image or bytes depending on SDK version
                    if hasattr(image.image, 'data'):
                        # It's bytes-like
                        image_bytes = image.image.data
                    elif hasattr(image.image, 'save'):
                        # It's a PIL Image
                        buffer = io.BytesIO()
                        image.image.save(buffer, format="PNG")
                        image_bytes = buffer.getvalue()
                    else:
                        # Try direct bytes
                        image_bytes = bytes(image.image)

                    image_data = base64.b64encode(image_bytes).decode("utf-8")
                    task.status = "completed"
                    task.result = ImageData(
                        base64_data=image_data,
                        mime_type="image/png"
                    )
                    print(f"[GeminiImageProvider] Image generated successfully, size: {len(image_bytes)} bytes")
                else:
                    task.status = "error"
                    task.error = "Image object has no image data"
                    print(f"[GeminiImageProvider] Error: Image object has no image data. Attrs: {dir(image)}")
            else:
                task.status = "error"
                task.error = "No images in response"
                print(f"[GeminiImageProvider] Error: No images in response")

        except Exception as e:
            task.status = "error"
            task.error = str(e)
            print(f"[GeminiImageProvider] Exception: {e}")
            import traceback
            traceback.print_exc()

        return task

    def poll_task(self, task: GenerationTask) -> GenerationTask:
        """
        Gemini image generation is synchronous, so this just returns the task.
        """
        return task


class VeoVideoProvider(VideoProvider):
    """
    Video generation using Veo 3.1.
    Supports first/last frame video generation.
    """

    def __init__(self):
        # Use the fast model by default for quicker iteration
        self.model = os.getenv("VEO_MODEL", "veo-3.1-generate-preview")
        # Track active operations by task_id
        self._operations: dict[str, object] = {}

    @property
    def name(self) -> str:
        return "google"

    def generate_video(
        self,
        prompt: str,
        first_frame: Optional[ImageData] = None,
        last_frame: Optional[ImageData] = None,
        **kwargs
    ) -> GenerationTask:
        """
        Generate video using Veo 3.1 with first/last frame.
        Returns a task that needs to be polled for completion.
        """
        task_id = str(uuid.uuid4())
        task = GenerationTask(
            provider=self.name,
            task_type="video",
            task_id=task_id,
            status="processing"
        )

        try:
            client = _get_client()

            # Convert ImageData to PIL Images for Veo
            first_pil = None
            last_pil = None

            if first_frame and first_frame.has_data():
                first_pil = self._image_data_to_pil(first_frame)

            if last_frame and last_frame.has_data():
                last_pil = self._image_data_to_pil(last_frame)

            if not first_pil:
                task.status = "error"
                task.error = "First frame image is required for Veo video generation"
                return task

            # Build config
            config_kwargs = {
                "aspect_ratio": "16:9"
            }

            # Add last frame if provided
            if last_pil:
                config_kwargs["last_frame"] = last_pil

            config = types.GenerateVideosConfig(**config_kwargs)

            # Start video generation
            operation = client.models.generate_videos(
                model=self.model,
                prompt=prompt,
                image=first_pil,
                config=config
            )

            # Store operation for polling
            task.provider_data = {
                "operation_name": getattr(operation, 'name', str(task_id)),
                "start_time": time.time()
            }
            self._operations[task_id] = operation

        except Exception as e:
            task.status = "error"
            task.error = str(e)

        return task

    def poll_task(self, task: GenerationTask) -> GenerationTask:
        """
        Poll Veo operation for completion.
        """
        if task.is_complete():
            return task

        operation = self._operations.get(task.task_id)
        if not operation:
            task.status = "error"
            task.error = "Operation not found - may have been lost on server restart"
            return task

        try:
            client = _get_client()

            # Refresh operation status
            operation = client.operations.get(operation)
            self._operations[task.task_id] = operation

            if operation.done:
                if hasattr(operation, 'error') and operation.error:
                    task.status = "error"
                    task.error = str(operation.error)
                elif hasattr(operation, 'response') and operation.response:
                    # Get the generated video
                    videos = operation.response.generated_videos
                    if videos and len(videos) > 0:
                        video = videos[0]
                        # Download the video bytes
                        video_bytes = client.files.download(file=video.video)
                        task.status = "completed"
                        task.result_bytes = video_bytes
                    else:
                        task.status = "error"
                        task.error = "No video in response"
                else:
                    task.status = "error"
                    task.error = "Operation completed but no response"

                # Clean up stored operation
                del self._operations[task.task_id]
            else:
                task.status = "processing"
                # Add elapsed time to provider data
                start_time = task.provider_data.get("start_time", time.time())
                task.provider_data["elapsed_seconds"] = int(time.time() - start_time)

        except Exception as e:
            task.status = "error"
            task.error = str(e)
            # Clean up on error
            if task.task_id in self._operations:
                del self._operations[task.task_id]

        return task

    def _image_data_to_pil(self, image_data: ImageData):
        """Convert ImageData to PIL Image."""
        from PIL import Image

        if image_data.base64_data:
            # Decode base64 to PIL
            img_bytes = base64.b64decode(image_data.base64_data)
            return Image.open(io.BytesIO(img_bytes))
        elif image_data.url:
            # Download from URL and convert to PIL
            import requests
            response = requests.get(image_data.url, timeout=60)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content))

        return None
