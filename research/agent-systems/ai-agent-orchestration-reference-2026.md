# AI Agent Orchestration & Multi-Agent Systems Reference (Early 2026)

> A concise reference for building agents that gather product research and orchestrate video generation.

---

## 1. Agent Frameworks Comparison

### LangGraph (LangChain Ecosystem)
**Architecture:** Graph-first stateful workflows with nodes, edges, and conditional routing.

**Pros:**
- Maximum control and flexibility for complex workflows
- 2.2x faster than CrewAI; most token-efficient (2,589 tokens vs 8-9x more for others)
- Excellent for traceable, debuggable flows
- Native `interrupt()` function for human-in-the-loop checkpoints
- Strong memory support: in-thread memory + cross-thread memory with `MemorySaver`

**Cons:**
- Steeper learning curve
- Requires understanding of graph-based state management

**Best for:** Complex orchestration, multi-step reasoning, production systems needing detailed control.

### CrewAI
**Architecture:** Role-based "crews" of agents with distinct roles, goals, and backstories.

**Pros:**
- Beginner-friendly; intuitive concepts
- Production-ready with layered memory (ChromaDB for short-term, SQLite for long-term)
- Fast setup for team-based coordination
- Backed by AI Fund (Andrew Ng)

**Cons:**
- Less flexible than LangGraph for complex conditional flows
- Slower performance than LangGraph

**Best for:** Production systems with role-based task delegation; quick prototypes.

### AutoGen (Microsoft)
**Architecture:** Multi-agent conversations with adaptive routing and async communication.

**Pros:**
- Native `UserProxyAgent` for human-in-the-loop
- Excellent for research and prototyping
- Good balance of ease and flexibility
- October 2025 merger with Semantic Kernel enhanced capabilities

**Cons:**
- Token-heavy compared to LangGraph
- Less structured than graph-based approaches

**Best for:** Research, prototyping, systems requiring natural human-agent collaboration.

### Claude Tool Use (Anthropic)
**Advanced Features (2026):**
- **Tool Search Tool:** Discovers tools on-demand (avoids context stuffing)
- **Programmatic Tool Calling:** Reduces context window impact
- **Strict Mode:** `strict: true` guarantees schema validation
- **Automatic Tool Call Clearing:** Clears old tool results near token limits

**Best Practices:**
- Provide clear error messages with `is_error: true`
- Include tool usage examples (not just schema)
- Implement input validation before execution
- Use automatic compaction for long-running tasks

---

## 2. Planning & Task Decomposition

### State-of-the-Art Approaches

**Hierarchical Multi-Agent (AGENTORCHESTRA)**
- Planning agents use ReAct-based tool-calling: think-then-act paradigm
- Record decisions in memory; continuously extract insights
- Todo tool structures tasks: identifier, description, priority, status, result
- Achieves 25.9% on HLE benchmark (vs. o3: 20.3%, Gemini-2.5-pro: 17.8%)

**Dynamic Task Decomposition (TDAG Framework)**
- Dynamically decomposes tasks and generates specialized subagents
- Avoids "error propagation" from fixed subtask sequences
- Adapts to unpredictable real-world conditions

### Core Principles (AOP Framework)
1. **Solvability:** Each sub-task must be resolvable by available agents
2. **Completeness:** Sub-tasks collectively achieve the original goal
3. **Non-redundancy:** No duplicate or unnecessary work

### For Your Use Case (Product Research + Video)
Recommended approach:
```
[User Query]
    -> [Planning Agent] decomposes into:
        1. Market research subtask -> Research Agent
        2. Competitor analysis subtask -> Research Agent
        3. Script generation subtask -> Content Agent
        4. Video generation subtask -> Video Agent
    -> [Orchestrator] manages execution & state
```

---

## 3. Tool Use: State of the Art

### Web Browsing
**Browser-Use Framework (Recommended)**
- Python-based, uses Playwright
- 89.1% on WebVoyager benchmark
- Autonomous task planning with LangChain integration
- Handles cookie banners, captchas adaptively
- `pip install browser-use`

**Key Considerations:**
- Fully autonomous agents require LLM call per decision (cost/latency tradeoff)
- Local execution possible via Ollama + DeepSeek

### API Integration
- Use framework-native tool-calling (LangChain, Claude's tool use)
- MCP (Model Context Protocol) servers provide standardized integrations
- LLM Browser supports: MCP, LangChain, OpenAI CUA, Browser Use, n8n, CrewAI

### Web Scraping for Research
**Top Tools (2026):**
| Tool | Key Feature | Best For |
|------|-------------|----------|
| Browse AI | No-code, visual builder | Market research |
| GPTBots | Enterprise AI agents | Custom scraping |
| Kadoa | Zero-maintenance | Dynamic sites |
| Oxylabs AI Studio | Natural language setup | Low-code teams |

**Industry Stats:**
- 99.5% accuracy on JavaScript-heavy sites
- 30-40% faster than traditional scraping
- 62% shift toward no-code tools

### Video Generation APIs
| Platform | Max Duration | API Access | Best For |
|----------|--------------|------------|----------|
| **Sora 2** | 60s | Limited (Pro $200/mo) | Cinematic quality |
| **Runway Gen-4/4.5** | ~15-30s | Limited | Professional control |
| **Pika Labs** | ~15s | Full API | Fast prototyping, effects |
| **Kling 2.0** | 120s | API available | Long-form content |

**Costs:** $0.01-$0.50 per second depending on platform/features.
**Trend:** Real-time generation expected (10-30s) by late 2026.

---

## 4. Context Management & Memory

### Memory Architecture Types

**Short-Term Memory**
- Recent queries, responses, system prompts
- Stored in active context window
- LangGraph: `thread_id` based

**Long-Term Memory**
- **Episodic:** Specific events, conversation history
- **Procedural:** Instructions, rules for recurring tasks
- **Semantic:** General knowledge, facts (often RAG-based)

### RAG (Retrieval-Augmented Generation)
**Traditional RAG Limitations:**
- Static workflows
- Limited multistep reasoning
- No adaptive retrieval

**Agentic RAG (2026 Standard):**
- Agents dynamically decide when/what to retrieve
- Multiple source integration
- Iterative refinement of context
- Design patterns: reflection, planning, tool use, multiagent collaboration

### Self-Evolving Memory (Cutting Edge)
- Inspired by Zettelkasten method
- Memories generate their own contextual descriptions
- Form meaningful connections automatically
- Evolve content and relationships over time

### Framework-Specific Memory

| Framework | Short-Term | Long-Term |
|-----------|------------|-----------|
| LangGraph | MemorySaver + thread_id | InMemoryStore/external DB |
| CrewAI | ChromaDB vector store | SQLite tables |
| AutoGen | Conversation history | Configurable backends |

### Best Practices
1. Separate short-term and long-term storage
2. Use vector embeddings for semantic retrieval
3. Implement automatic compaction for long tasks
4. Consider episodic + semantic memory combination

---

## 5. Human-in-the-Loop (HITL)

### When to Insert Checkpoints
- Access approvals and configuration changes
- Destructive or irreversible actions
- Legal, financial, or reputational risk decisions
- Low-confidence predictions or edge cases

### Implementation Patterns

**LangGraph (Recommended):**
```python
# interrupt() pauses execution, waits for input, resumes cleanly
from langgraph.checkpoint import interrupt

def approval_node(state):
    if needs_human_approval(state):
        return interrupt("Please approve this action: ...")
    return continue_execution(state)
```

**AutoGen:**
- Native `UserProxyAgent` for human participation
- Humans can review, approve, or modify steps

### Best Practices
1. **Strategic Involvement:** Focus humans on edge cases, not every output
2. **Risk-Based Routing:** Categorize outputs, automate low-risk decisions
3. **Feedback Loops:** Reviewer corrections should improve routing logic
4. **Audit Trails:** Log every intervention (who, when, decision, rationale)

### Regulatory Considerations
- **EU AI Act Article 14:** Requires human oversight for high-risk AI
- Affected domains: hiring, credit, healthcare, critical infrastructure
- Humans must understand system capabilities and have authority to intervene

### Scaling Challenge
> "At millions of decisions per second, the idea that humans can meaningfully supervise AI one decision at a time is no longer realistic."

Solution: AI-assisted oversight layers + strategic human checkpoints.

---

## 6. Reliability & Failure Modes

### Production Statistics
- **70-85%** of AI initiatives fail to meet expected outcomes
- Main causes: integration issues (not LLM failures)
- Three leading causes: "Dumb RAG," brittle connectors, no event-driven architecture

### Common Failure Modes

| Failure Mode | Description | Mitigation |
|--------------|-------------|------------|
| **Hallucination Cascades** | One fabrication triggers multi-system incidents | Ground with RAG, add verification steps |
| **Memory Corruption** | Slightly wrong entries compound over time | Regular memory audits, structured storage |
| **Tool Initialization** | Primary bottleneck for smaller models | Robust retry logic, fallbacks |
| **Early Error Cascades** | One early mistake compounds through workflow | Validation at each step |

### Error Handling Best Practices

**Retry Logic:**
- Only retry transient errors (timeouts, rate limits)
- Never retry: auth failures, invalid requests, permanent errors
- Use exponential backoff
- Respect `Retry-After` headers

**Graceful Degradation:**
- Maintain reduced functionality vs. complete failure
- Route to alternative models/providers on failure
- Implement circuit breaker patterns

**Saga Orchestration Pattern:**
- Each transaction has a "compensating action"
- On failure, orchestrator rolls back to consistent state
- Essential for distributed agent transactions

### Observability Requirements
Every tool call should log:
- `trace_id` (correlate with entire workflow)
- Upstream API response (status, headers, body)
- Timing and token usage

### Model Reliability Benchmarks
- Mid-sized models (qwen2.5:14b): 96.6% success rate, 7.3s latency
- Good accuracy-efficiency tradeoff for resource-constrained deployments

---

## 7. Architecture Recommendation for Your Use Case

### Product Research + Video Generation Agent

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (LangGraph)                  │
│  - State management, conditional routing, checkpoints        │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Research Agent│    │ Content Agent │    │  Video Agent  │
│               │    │               │    │               │
│ - Browse AI   │    │ - Script gen  │    │ - Pika API    │
│ - Browser-Use │    │ - Prompt opt  │    │ - Runway API  │
│ - Web scraping│    │               │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌───────────────┐
                    │  Memory Layer │
                    │ (RAG + Vector)│
                    └───────────────┘
```

### Key Design Decisions

1. **Framework:** LangGraph for orchestration (performance + control)
2. **Research Tools:** Browser-Use + Kadoa/Browse AI for web scraping
3. **Video API:** Pika Labs (best API access, fast iteration) or Runway (quality)
4. **Memory:** Agentic RAG with vector store (ChromaDB or similar)
5. **HITL Checkpoints:**
   - After research compilation (validate findings)
   - Before video generation (approve script/concept)
   - After video generation (approve final output)

### Implementation Tips

1. Start with simple linear flow, add complexity incrementally
2. Implement comprehensive logging from day one
3. Use `strict: true` for all tool definitions
4. Build fallback chains for each external API
5. Design compensating actions for each destructive operation

---

## Sources

### Agent Frameworks
- [Turing - AI Agent Frameworks Comparison](https://www.turing.com/resources/ai-agent-frameworks)
- [AIMultiple - Top Agentic AI Frameworks 2026](https://research.aimultiple.com/agentic-frameworks/)
- [Iterathon - Agent Orchestration 2026 Guide](https://iterathon.tech/blog/ai-agent-orchestration-frameworks-2026)
- [Medium - Comparing LangGraph, CrewAI, AutoGen](https://medium.com/@a.posoldova/comparing-4-agentic-frameworks-langgraph-crewai-autogen-and-strands-agents-b2d482691311)

### Task Decomposition
- [OpenReview - AGENTORCHESTRA](https://openreview.net/pdf/4967a6e0001e9c13cec8d73db97143a3da3a55f2.pdf)
- [ScienceDirect - TDAG Framework](https://www.sciencedirect.com/science/article/abs/pii/S0893608025000796)
- [Medium - Agent-Oriented Planning](https://medium.com/@NAITIVE/navigating-the-complexity-of-agent-oriented-planning-in-multi-agent-systems-4c2ead2e2567)

### Tool Use & Web Browsing
- [Browser-Use GitHub](https://github.com/browser-use/browser-use)
- [Claude API Docs - Tool Use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [Anthropic - Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)

### Memory & RAG
- [arXiv - Agentic RAG Survey](https://arxiv.org/abs/2501.09136)
- [MongoDB - Long-Term Memory with LangGraph](https://www.mongodb.com/company/blog/product-release-announcements/powering-long-term-memory-for-agents-langgraph)
- [arXiv - A-Mem: Agentic Memory](https://arxiv.org/html/2502.12110v11)

### Human-in-the-Loop
- [Permit.io - HITL Best Practices](https://www.permit.io/blog/human-in-the-loop-for-ai-agents-best-practices-frameworks-use-cases-and-demo)
- [Parseur - HITL Complete Guide 2026](https://parseur.com/blog/human-in-the-loop-ai)
- [LangChain Docs - Human-in-the-Loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)

### Reliability
- [arXiv - Tool Invocation Reliability](https://arxiv.org/abs/2601.16280)
- [Galileo - 7 Agent Failure Modes](https://galileo.ai/blog/agent-failure-modes-guide)
- [n8n - 15 Best Practices for Production Agents](https://blog.n8n.io/best-practices-for-deploying-ai-agents-in-production/)
- [Composio - Why AI Pilots Fail](https://composio.dev/blog/why-ai-agent-pilots-fail-2026-integration-roadmap)

### Video Generation
- [WaveSpeedAI - AI Video APIs 2026](https://wavespeed.ai/blog/posts/complete-guide-ai-video-apis-2026/)
- [PXZ.ai - Sora vs Runway vs Pika](https://pxz.ai/blog/sora-vs-runway-vs-pika-best-ai-video-generator-2026-comparison)

### Web Scraping & Research
- [GPTBots - Top Web Scraping AI Agents](https://www.gptbots.ai/blog/web-scraping-ai-agents)
- [Kadoa - Best AI Web Scrapers 2026](https://www.kadoa.com/blog/best-ai-web-scrapers-2026)
