# Alibaba DashScope Wan API Reference

## Regional Endpoints

| Region | Base URL |
|--------|----------|
| Singapore | `https://dashscope-intl.aliyuncs.com/api/v1` |
| Virginia | `https://dashscope-us.aliyuncs.com/api/v1` |
| Beijing | `https://dashscope.aliyuncs.com/api/v1` |

**Important**: Each region has separate API keys. Cross-region calls result in authentication failures.

## Authentication

```
Authorization: Bearer <DASHSCOPE_API_KEY>
```

## Available Models

### Text-to-Video
| Model | Resolution | Duration | Notes |
|-------|-----------|----------|-------|
| `wan2.6-t2v` | 720P, 1080P | 2-15s | **HTTP only** - no SDK support |
| `wan2.5-t2v-preview` | 720P | 5s | Supports audio input |
| `wan2.2-t2v-plus` | 720P | 5s | |
| `wan2.1-t2v-turbo` | 480P | 5s | Fast |
| `wan2.1-t2v-plus` | 720P | 5s | |

### Image-to-Video
| Model | Resolution | Duration | Notes |
|-------|-----------|----------|-------|
| `wan2.6-i2v` | 720P, 1080P | 2-15s | Multi-shot support |
| `wan2.6-i2v-flash` | 720P, 1080P | 2-15s | Faster, audio support |
| `wan2.5-i2v-preview` | 720P | 5s | |
| `wan2.2-i2v-plus` | 720P | 5s | |
| `wan2.2-i2v-flash` | 480P | 5s | |
| `wan2.1-i2v-turbo` | 480P | 5s | |
| `wan2.1-i2v-plus` | 720P | 5s | |

### First & Last Frame to Video
| Model | Resolution | Duration | Notes |
|-------|-----------|----------|-------|
| `wan2.2-kf2v-flash` | 480P-1080P | 5s | Recommended |
| `wan2.1-kf2v-plus` | 720P | 5s | Complex motion |

### Image Generation
| Model | Notes |
|-------|-------|
| `wan2.6-image` | Text-to-image, image editing, mixed text/image output |

### Digital Human (Lip-sync)
| Model | Resolution | Duration | Notes |
|-------|-----------|----------|-------|
| `wan2.2-s2v` | 480P, 720P | <20s | Image + audio → lip-sync video |

### Reference-to-Video
| Model | Notes |
|-------|-------|
| `wan2.6-r2v` | Not yet officially documented - check Model Studio |

## API Endpoints by Task

### Text-to-Video
```
POST {base}/services/aigc/video-generation/video-synthesis
```

### Image-to-Video
```
POST {base}/services/aigc/video-generation/video-synthesis
```

### First/Last Frame Video
```
POST {base}/services/aigc/image2video/video-synthesis
```

### Image Generation (wan2.6-image)
```
POST {base}/services/aigc/multimodal-generation/generation  (sync)
POST {base}/services/aigc/image-generation/generation       (async)
```

### Digital Human (wan2.2-s2v)
```
POST {base}/services/aigc/image2video/video-synthesis
```

### Task Status Query
```
GET {base}/tasks/{task_id}
```

## Required Headers

| Header | Value | Required For |
|--------|-------|--------------|
| `Content-Type` | `application/json` | All |
| `Authorization` | `Bearer <key>` | All |
| `X-DashScope-Async` | `enable` | HTTP async calls |
| `X-DashScope-Sse` | `enable` | Streaming (wan2.6-image) |

## Request/Response Examples

### Text-to-Video Request
```json
{
  "model": "wan2.6-t2v",
  "input": {
    "prompt": "A cat walking in a garden",
    "negative_prompt": "blurry, low quality"
  },
  "parameters": {
    "size": "1280*720",
    "duration": 5,
    "prompt_extend": true
  }
}
```

### Image-to-Video Request
```json
{
  "model": "wan2.6-i2v",
  "input": {
    "prompt": "The person waves hello",
    "img_url": "https://example.com/image.jpg"
  },
  "parameters": {
    "resolution": "720P",
    "duration": 5
  }
}
```

### Task Creation Response
```json
{
  "output": {
    "task_id": "abc123",
    "task_status": "PENDING"
  },
  "request_id": "req-xyz"
}
```

### Task Query Response (Success)
```json
{
  "output": {
    "task_id": "abc123",
    "task_status": "SUCCEEDED",
    "video_url": "https://...",
    "orig_prompt": "...",
    "actual_prompt": "..."
  }
}
```

## Task Status Values
`PENDING` → `RUNNING` → `SUCCEEDED` | `FAILED` | `CANCELED` | `UNKNOWN`

## Key Limitations

- Video/task URLs expire after **24 hours**
- Poll interval: ~15 seconds recommended
- Image constraints: JPEG/PNG/BMP/WEBP, 360-2000px, max 10MB
- Audio constraints: WAV/MP3, 3-30 seconds, max 15MB
- wan2.6-t2v **does not support SDK** - use HTTP directly

## Python SDK Usage

```python
import dashscope
from dashscope import VideoSynthesis, ImageSynthesis

dashscope.api_key = "your-key"
# For international: dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'

# Image-to-Video (synchronous - SDK handles polling)
response = VideoSynthesis.call(
    model='wan2.6-i2v-flash',
    prompt='A person smiling',
    img_url='https://example.com/image.jpg',
    resolution="720P",
    duration=5
)

# Async call (returns task_id immediately)
response = VideoSynthesis.async_call(
    model='wan2.6-i2v',
    prompt='Description',
    img_url='https://...'
)
task_id = response.output.task_id

# Check task status
result = VideoSynthesis.fetch(task_id)
```

## Sources

- [Text-to-Video API](https://www.alibabacloud.com/help/en/model-studio/text-to-video-api-reference)
- [Image-to-Video API](https://www.alibabacloud.com/help/en/model-studio/image-to-video-api-reference)
- [First/Last Frame API](https://www.alibabacloud.com/help/en/model-studio/image-to-video-by-first-and-last-frame-api-reference)
- [Image Generation API](https://www.alibabacloud.com/help/en/model-studio/wan-image-generation-api-reference)
- [Digital Human API](https://www.alibabacloud.com/help/en/model-studio/wan-s2v-api)
- [Video Generation Guide](https://www.alibabacloud.com/help/en/model-studio/use-video-generation/)
