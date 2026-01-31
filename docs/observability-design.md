# LLM Observability System Design

This document outlines the research and architectural design for a reusable LLM observability library that integrates with our existing `providers/llm/` abstraction.

## Table of Contents

1. [Platform Research](#platform-research)
2. [Architecture Design](#architecture-design)
3. [Agent/Claude Code Readability](#agentclaude-code-readability)
4. [Integration Patterns](#integration-patterns)

---

## Platform Research

### 1. LangSmith (LangChain)

**Overview:** LangSmith is LangChain's commercial observability platform for tracing, debugging, and evaluating LLM applications.

**How It Captures LLM Calls:**
- Uses callback handlers that send traces asynchronously to LangSmith's collector
- For LangChain: Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY`
- For non-LangChain: Use `@traceable` decorator on functions
- Zero latency impact due to async trace collection

**Data Schema:**
- Traces are structured as trees of "runs" (root run + child runs for each inner call)
- Each run captures: inputs, outputs, metadata, timestamps, parent_id
- Supports custom metadata and feedback/scoring

**Multi-Provider Support:**
- Framework-agnostic; works with any LLM provider
- Integrates natively with LangChain, LangGraph, or custom code
- Manual instrumentation required for non-LangChain code

**Pros:**
- Rich UI for visualizing execution trees
- Built-in evaluation and testing tools
- Low integration friction for LangChain users
- Self-hosting available on Enterprise plan

**Cons:**
- Cloud SaaS primarily (self-host requires enterprise)
- Free tier limited to 5K traces/month
- Closed-source (only SDKs are open)

**Sources:** [LangSmith Observability](https://www.langchain.com/langsmith/observability), [LangSmith Docs](https://docs.langchain.com/langsmith/observability)

---

### 2. Langfuse (Open Source)

**Overview:** Langfuse is an open-source LLM engineering platform for tracing, monitoring, evaluation, and prompt management.

**How It Captures LLM Calls:**
- Native SDKs for Python/JS with decorators and context managers
- OpenTelemetry-native SDK v3 (thin layer over official OTEL client)
- 50+ framework integrations (LangChain, OpenAI SDK, LiteLLM, etc.)
- Automatic instrumentation via OTEL auto-instrumentation

**Data Schema:**
- **Traces**: Represent a single request/operation (e.g., user question to bot response)
- **Observations**: Individual steps within a trace (generations, tool calls, retrieval steps)
- Observations can be nested for complex workflows
- Supports sessions (multi-turn conversations) and user tracking
- Agent workflows visualized as graphs

**Multi-Provider Support:**
- Provider-agnostic via OTEL instrumentation
- Direct integrations: OpenAI, Anthropic, Claude, Gemini, etc.
- LiteLLM gateway support for unified access

**Pros:**
- Fully open source (MIT license)
- Self-hostable in minutes (Docker/Kubernetes)
- OpenTelemetry-native (future-proof, no vendor lock-in)
- Strong prompt management and versioning
- LLM-as-a-judge evaluation built-in
- Runs on ClickHouse for high-volume writes

**Cons:**
- Requires infrastructure to self-host
- Cloud offering has usage limits on free tier
- UI less polished than commercial alternatives

**Sources:** [Langfuse GitHub](https://github.com/langfuse/langfuse), [Langfuse Observability Docs](https://langfuse.com/docs/observability/overview), [Langfuse Data Model](https://langfuse.com/docs/observability/data-model)

---

### 3. OpenLLMetry / OpenTelemetry

**Overview:** OpenLLMetry extends OpenTelemetry with LLM-specific instrumentation. It's the open standard approach to LLM observability.

**How It Captures LLM Calls:**
- Non-intrusive instrumentation built on OpenTelemetry
- Auto-instrumentation libraries for LLM providers and frameworks
- Captures prompts, completions, token usage, model parameters
- Compatible with any OTEL backend (Jaeger, Zipkin, Datadog, etc.)

**Data Schema (GenAI Semantic Conventions):**
- Standard attributes defined by OTel GenAI Semantic Conventions:
  - `gen_ai.request.model` - Model identifier
  - `gen_ai.usage.input_tokens` - Input token count
  - `gen_ai.usage.output_tokens` - Output token count
  - `gen_ai.provider.name` - Provider identifier
  - `gen_ai.operation.name` - Operation type
  - `gen_ai.request.temperature` - Sampling temperature
  - `gen_ai.response.finish_reason` - Why generation stopped

**Multi-Provider Support:**
- Instrumentations for: OpenAI, Anthropic, Cohere, Google
- Vector DB support: Pinecone, Chroma, Qdrant, Weaviate
- Frameworks: LangChain, Haystack, LlamaIndex

**Pros:**
- Open standard (CNCF project)
- No vendor lock-in
- Works with existing observability infrastructure
- Consistent schema across all providers
- Community-driven, extensible

**Cons:**
- Requires understanding of OTEL concepts
- Need to set up your own backend/UI
- Less specialized LLM features compared to purpose-built tools

**Sources:** [OpenLLMetry GitHub](https://github.com/traceloop/openllmetry), [OpenTelemetry LLM Observability Blog](https://opentelemetry.io/blog/2024/llm-observability/)

---

### 4. Helicone

**Overview:** Open-source LLM observability platform with proxy-based integration.

**How It Captures LLM Calls:**
- **Proxy/Gateway approach**: Change base URL to Helicone's gateway
- One line of code to integrate
- AI Gateway provides unified API for 100+ models
- No SDK changes required for supported providers

**Data Schema:**
- Request/response logging with full payloads
- Automatic cost tracking and token counting
- Session and user tracking
- Latency and error metrics

**Multi-Provider Support:**
- OpenAI, Anthropic, Gemini, Groq via unified gateway
- LangChain, Vercel AI SDK integrations
- OpenAI-compatible API for any provider

**Pros:**
- Easiest integration (just change base URL)
- Built-in caching for cost savings
- Prompt versioning and management
- Security scanning (prompt injection detection)
- SOC 2 compliant, 10K free requests/month

**Cons:**
- Proxy adds network hop (potential latency)
- Less control over instrumentation
- Dependent on Helicone infrastructure for proxy mode

**Sources:** [Helicone GitHub](https://github.com/Helicone/helicone), [Helicone Docs](https://docs.helicone.ai/getting-started/quick-start)

---

### 5. Arize Phoenix

**Overview:** Open-source AI observability platform with strong evaluation and debugging focus.

**How It Captures LLM Calls:**
- OpenTelemetry-based instrumentation
- First-class integrations with LlamaIndex, LangChain, OpenAI
- Manual and automatic instrumentation options

**Data Schema:**
- Traces as trees of spans
- Span-level visibility for precise debugging
- Captures: latency, token usage, runtime exceptions, function calls
- Detailed retrieval document inspection for RAG

**Multi-Provider Support:**
- OpenAI, Bedrock, MistralAI, VertexAI, LiteLLM, Google GenAI
- Frameworks: LlamaIndex, LangChain, Haystack, DSPy, smolagents

**Pros:**
- Strong debugging tools (agent graph visualization)
- RAG-specific features (retrieved document inspection)
- Evaluation tools built-in
- Runs locally (no external dependencies)
- OTEL-based (no vendor lock-in)

**Cons:**
- Focused on experimentation/debugging, less on production monitoring
- Smaller community than Langfuse

**Sources:** [Arize Phoenix GitHub](https://github.com/Arize-ai/phoenix), [Phoenix Tracing Docs](https://arize.com/docs/phoenix/tracing/llm-traces)

---

### Platform Comparison Summary

| Feature | LangSmith | Langfuse | OpenLLMetry | Helicone | Phoenix |
|---------|-----------|----------|-------------|----------|---------|
| Open Source | SDKs only | Yes (MIT) | Yes | Yes | Yes |
| Self-Host | Enterprise | Easy | N/A (backend) | Yes | Yes |
| Integration Effort | Low | Low-Medium | Medium | Very Low | Low |
| OTEL Compatible | No | Yes | Yes | No | Yes |
| Proxy Mode | No | No | No | Yes | No |
| Multi-Provider | Yes | Yes | Yes | Yes | Yes |
| Cost Tracking | Yes | Yes | Manual | Auto | Yes |

**Recommendation for Our Use Case:** Adopt a **Langfuse-inspired approach** with OpenTelemetry compatibility. This gives us:
- Open standard compliance for future flexibility
- Lightweight self-hosted storage (JSON files or SQLite)
- Decorator-based instrumentation pattern
- Schema compatible with industry standards

---

## Architecture Design

### Design Principles

1. **Zero-friction integration**: One decorator or wrapper to instrument any LLM call
2. **Enforce by default**: Make observability opt-out rather than opt-in
3. **Agent-readable output**: Logs optimized for Claude Code to analyze
4. **Provider-agnostic**: Works with Gemini, Claude, OpenAI, or any provider

### Data Schema

Our trace schema follows OpenTelemetry GenAI Semantic Conventions with extensions for our use case:

```python
@dataclass
class LLMTrace:
    """Complete trace of an LLM interaction."""
    # Identification
    trace_id: str              # UUID for this trace
    span_id: str               # UUID for this span within trace
    parent_span_id: Optional[str]  # For nested calls

    # Timing
    timestamp: str             # ISO 8601 format
    duration_ms: float         # Total execution time

    # Provider info
    provider: str              # "gemini", "anthropic", "openai"
    model: str                 # "gemini-3-flash-preview", "claude-3-opus", etc.

    # Request details
    messages: list[dict]       # Input messages (role, content)
    system_prompt: Optional[str]  # System prompt if separate
    temperature: float
    thinking_enabled: bool
    extra_params: dict         # Provider-specific params

    # Response details
    output: str                # Model's response content
    thinking: Optional[str]    # Model's reasoning if available
    structured_output: Optional[dict]  # If using structured output mode
    finish_reason: str         # "stop", "length", "tool_use", etc.

    # Token usage
    input_tokens: int
    output_tokens: int
    thinking_tokens: Optional[int]  # For reasoning models
    total_tokens: int

    # Cost (calculated)
    estimated_cost_usd: Optional[float]

    # Status
    status: str                # "success", "error"
    error_type: Optional[str]  # Exception class name
    error_message: Optional[str]

    # Context for debugging
    function_name: str         # Calling function
    file_path: str             # Source file
    line_number: int

    # Custom metadata
    tags: list[str]            # User-defined tags
    metadata: dict             # Arbitrary key-value pairs
```

### Storage Strategy

**Primary: JSONL Files** (newline-delimited JSON)
- One file per day: `logs/llm-traces/YYYY-MM-DD.jsonl`
- Human-readable and grep-friendly
- Easy to parse programmatically
- No database dependencies
- Append-only for simplicity

```
logs/
└── llm-traces/
    ├── 2026-01-30.jsonl
    ├── 2026-01-29.jsonl
    └── ...
```

**Secondary: SQLite** (optional, for querying)
- Single file: `logs/traces.db`
- Enables SQL queries for analysis
- Index on timestamp, provider, status, tags
- Populated from JSONL files via import script

**Log Rotation:**
- Keep 30 days of JSONL files by default
- Compress older files with gzip
- Configurable via environment variable

### Instrumentation Pattern

**Option 1: Decorator (Recommended)**

```python
from observability import traced_llm

@traced_llm(tags=["scene-generation"])
def generate_scene_description(prompt: str) -> str:
    provider = get_llm_provider("gemini")
    response = provider.generate(prompt, thinking=True)
    return response.content
```

**Option 2: Context Manager**

```python
from observability import llm_trace

def generate_scene_description(prompt: str) -> str:
    with llm_trace(tags=["scene-generation"]) as trace:
        provider = get_llm_provider("gemini")
        response = provider.generate(prompt, thinking=True)
        trace.set_output(response)
        return response.content
```

**Option 3: Wrapper at Provider Level**

```python
# In providers/llm/__init__.py
def get_llm_provider(name: str = None) -> LLMProvider:
    provider = _get_raw_provider(name)
    return TracedLLMProvider(provider)  # Auto-wraps all calls
```

### Enforcement Mechanisms

To **require** all LLM code to use observability:

1. **Abstract Base Class Enforcement**
   - Make `LLMProvider.chat()` abstract with a `_chat_impl()` that subclasses override
   - Base class always wraps `_chat_impl()` with tracing
   - No way to call LLM without going through traced base class

2. **Lint Rules**
   - Custom ruff/pylint rule to flag direct SDK imports
   - Require using `get_llm_provider()` instead of raw `genai.Client()`

3. **Type Checking**
   - Return `TracedLLMResponse` which carries trace_id
   - Functions that consume LLM output require `TracedLLMResponse` type

4. **Import Hook** (aggressive)
   - Patch SDK modules at import time to auto-instrument

**Recommended Approach:** Combine #1 (base class) and #2 (lint rules) for practical enforcement without being too invasive.

---

## Agent/Claude Code Readability

The primary consumer of these logs is Claude Code doing self-verification and prompt engineering feedback.

### Log Format for Machine Consumption

**JSONL Format** (one trace per line):

```json
{"trace_id":"abc123","timestamp":"2026-01-30T14:23:45Z","provider":"gemini","model":"gemini-3-flash-preview","messages":[{"role":"user","content":"Generate a scene..."}],"output":"The scene shows...","thinking":"Let me analyze...","input_tokens":150,"output_tokens":423,"duration_ms":1234,"status":"success","tags":["scene-generation"],"function_name":"generate_scene_description","file_path":"demo/video_gen.py","line_number":45}
```

**Key Design Decisions for Agent Readability:**

1. **Complete prompts and outputs** - Full content, not truncated
2. **Thinking/reasoning captured** - Critical for understanding model behavior
3. **Source location** - File and line number for code correlation
4. **Flat structure** - No deep nesting, easy to parse
5. **ISO timestamps** - Unambiguous, sortable
6. **Consistent field names** - Predictable schema for parsing

### Query Patterns for Claude Code

**Query by Time Range:**
```bash
# Get traces from today
cat logs/llm-traces/2026-01-30.jsonl

# Get traces from last hour
cat logs/llm-traces/2026-01-30.jsonl | \
  jq 'select(.timestamp > "2026-01-30T13:00:00Z")'
```

**Query by Status:**
```bash
# Find all errors
grep '"status":"error"' logs/llm-traces/2026-01-30.jsonl | jq .

# Find successful calls with high latency
cat logs/llm-traces/2026-01-30.jsonl | \
  jq 'select(.status == "success" and .duration_ms > 5000)'
```

**Query by Tag/Function:**
```bash
# Find all scene generation calls
grep '"scene-generation"' logs/llm-traces/2026-01-30.jsonl | jq .

# Find calls from specific function
grep '"generate_scene_description"' logs/llm-traces/2026-01-30.jsonl
```

**Summarize Token Usage:**
```bash
cat logs/llm-traces/2026-01-30.jsonl | \
  jq -s '{total_input: (map(.input_tokens) | add), total_output: (map(.output_tokens) | add), count: length}'
```

### Metadata for Prompt Engineering Feedback

Include fields that help close the feedback loop:

```python
metadata = {
    # What version of the prompt is this?
    "prompt_version": "v2.3",
    "prompt_template_id": "scene-gen-001",

    # What was the expected vs actual outcome?
    "expected_format": "json",
    "validation_passed": True,

    # User/session context
    "session_id": "sess_abc123",
    "user_id": "user_456",

    # Experiment tracking
    "experiment": "temperature-sweep",
    "experiment_variant": "temp-0.3"
}
```

### Summary Views for Automated Analysis

Provide utility functions that generate Claude-friendly summaries:

```python
def get_recent_trace_summary(hours: int = 1) -> str:
    """Generate a markdown summary of recent traces for Claude to read."""
    traces = load_traces(since=datetime.now() - timedelta(hours=hours))

    return f"""
## LLM Trace Summary (last {hours} hour(s))

**Total Calls:** {len(traces)}
**Success Rate:** {success_rate:.1%}
**Avg Latency:** {avg_latency:.0f}ms
**Total Tokens:** {total_tokens:,}

### By Provider:
{provider_breakdown}

### Errors ({error_count}):
{error_summary}

### High Latency Calls (>{threshold}ms):
{latency_outliers}
"""
```

---

## Integration Patterns

### Integration with Existing `providers/llm/` Abstraction

**Current Structure:**
```
providers/llm/
├── __init__.py      # Factory and registry
├── base.py          # LLMProvider ABC, Message, LLMResponse
├── gemini.py        # GeminiProvider
├── anthropic.py     # AnthropicProvider
└── openai.py        # OpenAIProvider
```

**Proposed Integration:**

```python
# providers/llm/base.py - Modified

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        thinking: bool = False,
        **kwargs
    ) -> LLMResponse:
        """
        Traced wrapper around _chat_impl.
        All providers automatically get observability.
        """
        with llm_trace(
            provider=self.name,
            model=model or self.default_model,
            messages=messages,
            temperature=temperature,
            thinking=thinking,
            **kwargs
        ) as trace:
            response = self._chat_impl(messages, model, temperature, thinking, **kwargs)
            trace.record_response(response)
            return response

    @abstractmethod
    def _chat_impl(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        thinking: bool = False,
        **kwargs
    ) -> LLMResponse:
        """Actual implementation. Subclasses override this."""
        pass
```

**Benefits:**
- Zero changes needed in provider implementations (Gemini, Claude, OpenAI)
- Observability enforced at base class level
- Existing code continues to work

### Provider-Specific Adaptations

**Gemini (google-genai):**
```python
# Additional fields to capture
trace.metadata["thinking_level"] = config.get("thinking_level", "medium")
trace.thinking = extract_thinking_from_parts(response.candidates[0].content.parts)
```

**Anthropic (Claude):**
```python
# Capture thinking from extended thinking feature
if response.thinking:
    trace.thinking = response.thinking
trace.metadata["stop_reason"] = response.stop_reason
```

**OpenAI:**
```python
# Capture function/tool calls
if response.choices[0].message.tool_calls:
    trace.metadata["tool_calls"] = [
        {"name": tc.function.name, "arguments": tc.function.arguments}
        for tc in response.choices[0].message.tool_calls
    ]
```

### Configuration

**Environment Variables:**
```bash
# Enable/disable observability (default: enabled)
LLM_OBSERVABILITY_ENABLED=true

# Log directory
LLM_OBSERVABILITY_LOG_DIR=./logs/llm-traces

# Retention period in days
LLM_OBSERVABILITY_RETENTION_DAYS=30

# Log level (debug, info, warn, error)
LLM_OBSERVABILITY_LEVEL=info

# Include full prompts/outputs (disable for PII concerns)
LLM_OBSERVABILITY_CAPTURE_CONTENT=true
```

### Initialization

```python
# In app startup (e.g., demo/app.py)
from observability import init_observability

# Auto-configures from environment
init_observability()

# Or with explicit config
init_observability(
    log_dir="./logs/llm-traces",
    retention_days=30,
    capture_content=True
)
```

### Example Integration Flow

```python
# demo/video_gen.py
from providers.llm import get_llm_provider, Message

def generate_video_script(product_description: str) -> str:
    """Generate a video script. Automatically traced via base class."""
    provider = get_llm_provider("gemini")

    messages = [
        Message(role="system", content="You are a video script writer..."),
        Message(role="user", content=f"Write a script for: {product_description}")
    ]

    response = provider.chat(
        messages=messages,
        thinking=True,
        temperature=0.7
    )

    # Trace automatically captured:
    # - Full messages array
    # - System prompt
    # - Response content and thinking
    # - Token counts
    # - Latency
    # - Any errors

    return response.content
```

---

## Implementation Roadmap

### Phase 1: Core Library
1. Create `observability/` module with trace dataclass and JSONL writer
2. Implement context manager and decorator
3. Add to `providers/llm/base.py`

### Phase 2: Query Utilities
1. CLI tool for querying traces: `python -m observability query --since 1h`
2. Summary generation for Claude Code
3. SQLite export for complex queries

### Phase 3: Integration
1. Update all LLM-using code to go through providers
2. Add lint rules to enforce provider usage
3. Add trace_id to API responses for debugging

### Phase 4: Analysis
1. Cost tracking and reporting
2. Performance dashboards
3. Anomaly detection (unusual latency, error spikes)

---

## References

- [LangSmith Observability](https://www.langchain.com/langsmith/observability)
- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse Data Model](https://langfuse.com/docs/observability/data-model)
- [OpenLLMetry](https://github.com/traceloop/openllmetry)
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/blog/2024/llm-observability/)
- [Helicone](https://www.helicone.ai/)
- [Arize Phoenix](https://phoenix.arize.com/)
- [Datadog LLM Observability](https://docs.datadoghq.com/llm_observability/terms/)
