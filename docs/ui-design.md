# Conversational UI Design Document

## Overview

This document proposes UI improvements for the m(video)p chat interface to address common pain points in LLM-based conversational UIs: wall of text responses, awkward Q&A mapping, and assumption correction overhead.

---

## 1. Existing Product Research

### ChatGPT / Claude.ai - AI Response Formatting

**How they structure responses:**
- Both use **markdown-based formatting**: headers, bullet lists, code blocks, bold/italic emphasis
- ChatGPT introduced **formatting blocks** (Jan 2026) that display complex content like emails in document-style layouts separate from chat bubbles
- Claude uses **Artifacts** - substantial content (>15 lines) renders in a dedicated sidebar window, preventing messy conversation streams
- Clear visual hierarchy with consistent spacing between sections

**What makes it seamless:**
- Progressive disclosure: complex information revealed in layers
- Separation of concerns: chat for conversation, artifacts for content output
- Markdown creates predictable, scannable structure
- Users know instantly what type of content they're looking at

**Takeaway for our UI:** Separate conversational messages from structured data output. Use cards/sections instead of inline paragraphs.

---

### Linear - Structured Input Excellence

**How they handle structured input:**
- Explicitly **rejects pure chat interfaces** as "weak and generic"
- Uses a **workbench metaphor**: organized workspace with specific tools for specific tasks
- Structured side panels for metadata and properties
- AI functions complement traditional UI rather than replacing forms
- Multiple view types (list, board, timeline) create context for work

**What makes it seamless:**
- Users don't experience unpredictable AI outputs - they're grounded in structured context
- Clear separation between input fields and result areas
- Forms minimize variance in user inputs and outputs
- Workbench paradigm makes interaction feel purposeful

**Takeaway for our UI:** Ground AI interactions in structured context. The Product Canvas sidebar is good - extend this pattern to the conversation itself.

---

### Typeform / Tally - Conversational Forms

**How they handle structured input:**
- **One question at a time** creates rhythm and increases completion rates
- **Conditional logic**: questions show/hide/skip based on previous answers
- Tally uses a document-style editor with slash commands
- Typeform adjusts questions in real-time based on responses

**What makes it seamless:**
- Single question per screen reduces cognitive load
- Conditional logic creates sense of "the form understands me"
- Answer context flows naturally into next question
- Clear multi-step flows feel like guided conversations

**Takeaway for our UI:** Ask questions one at a time with dedicated input fields. Use conditional logic to skip irrelevant questions.

---

### Notion AI - Blending AI with Structured Content

**How they blend AI with UI:**
- AI is **embedded across all pages** in context - not a separate chat window
- AI databases with properties like "AI summary," "AI keywords," "AI translation"
- Smart autofill adapts to existing data patterns
- AI works within data structures (databases, properties, templates)

**What makes it seamless:**
- AI never pulls you out of your workspace
- Suggestions adapt to personal workflow patterns
- AI respects your data patterns

**Takeaway for our UI:** Let users edit AI-generated content inline rather than through follow-up messages.

---

### Intercom / Drift - Support Chat Flows

**How they structure Q&A:**
- Workflow automations have **triggers** followed by **blocks** (multiple steps per block)
- Blocks structure conversational turns - avoiding walls of text
- **Playbooks** create conditional chat flows with different paths for different user types
- Pre-set questions qualify visitors progressively

**Key principles from Intercom's design guidelines:**
1. **Consistency**: Conversation flows predictably
2. **Visual Hierarchy**: Clear relationships between elements
3. **Progressive Disclosure**: Complexity revealed step-by-step
4. **Guided Navigation**: Make next steps obvious
5. **Listen more than speak**: Learn from responses

**Takeaway for our UI:** Break responses into discrete blocks. Provide guided navigation with buttons for common actions.

---

## 2. Problem Analysis

### Problem 1: Wall of Text Responses

**Current state:** LLM responses are continuous paragraphs with no formatting or visual breaks.

**Why it's bad:**
- Users can't scan for specific information
- No visual hierarchy to distinguish important vs. supplementary content
- Feels overwhelming and robotic
- Hard to reference specific parts in follow-up messages

**Example of the problem:**
```
Assistant: Your product sounds interesting. I think you're building a task
management app for remote teams. The key features would be real-time
collaboration, deadline tracking, and integrations with Slack. Your target
user seems to be startup founders or engineering managers. The problem
you're solving is that current tools are too complex. I'm assuming you
want a minimalist design aesthetic and possibly a freemium pricing model...
```

This wall of text buries important extracted information in unstructured prose.

---

### Problem 2: Q&A Answer Mapping Friction

**Current state:** Users must number their answers or specify which question they're responding to.

**Why it's bad:**
- Extra cognitive load to remember question numbers
- Easy to miscount or correspond answers to wrong questions
- Breaks conversational flow
- Forces users to re-read questions to number correctly

**Example of the problem:**
```
Assistant: A few questions:
1. What's your target market?
2. What's the main feature?
3. How will users pay?

User: 1. Small businesses 2. AI scheduling 3. Monthly subscription
```

This forces users into an unnatural pattern that feels like filling out a form in chat.

---

### Problem 3: Assumption Correction Overhead

**Current state:** Users need a separate section or follow-up message to correct wrong assumptions.

**Why it's bad:**
- Assumptions often go unnoticed until they cause problems later
- Correcting after the fact requires re-explaining context
- No easy way to "confirm" correct assumptions or "reject" wrong ones
- Clarify/correction cycles slow down alignment

**Example of the problem:**
```
Assistant: Assumptions: B2B SaaS, US market, web-first, $20/mo pricing

User: Actually, it's B2C and mobile-first. Also the pricing should be free with ads.
```

The user must re-type and clarify, leading to misunderstanding that could've been caught earlier.

---

### Problem 4: Slow Alignment Cycles

**Current state:** Takes multiple turns to align LLM understanding with user intent.

**Why it's bad:**
- Each clarification round requires full message exchanges
- No way to "tune" specific fields without full conversation
- Product Canvas updates lag behind conversation
- Users can't directly edit extracted data

---

## 3. Proposed Solutions

### Solution 1: Structured Response Segments

**Replace wall of text with distinct visual blocks:**

Instead of one paragraph, break responses into **card-based segments**:

- **Message Card**: Conversational response (greeting, summary, next steps)
- **Question Card**: Individual questions with inline answer inputs
- **Assumption Card**: Extracted assumptions with confirm/edit toggles
- **Data Card**: Structured product data that syncs with canvas

**Benefits:**
- Scannable sections with clear visual hierarchy
- Each segment has a distinct purpose
- Users can interact with specific sections independently
- Easier to reference in follow-ups

---

### Solution 2: Inline Per-Question Answer Boxes

**Replace numbered lists with individual input fields:**

Each question appears as a separate card with its own text input or reply button:

```
┌─────────────────────────────────────────────┐
│ 🎯 Target Market                            │
│ "Who is your ideal customer?"               │
│ ┌─────────────────────────────────────────┐ │
│ │ Small business owners...                │ │
│ └─────────────────────────────────────────┘ │
│ [Skip] [Answer]                             │
└─────────────────────────────────────────────┘
```

**Benefits:**
- No numbering or mapping required
- Each question has dedicated input context
- Users can skip questions or answer out of order
- Answers are directly associated with questions

---

### Solution 3: Editable Assumption Badges with Toggle Confirm

**Display assumptions as interactive badges:**

```
┌─────────────────────────────────────────────┐
│ 📋 Assumptions (click to edit)              │
│                                             │
│ [✓ B2B SaaS]  [✗ US Market]  [? Web-first] │
│                                             │
│ ✓ = Confirmed   ✗ = Wrong   ? = Unsure     │
└─────────────────────────────────────────────┘
```

**Interaction:**
- Click badge to cycle: confirmed → wrong → unsure
- Click "edit" icon to change the assumption text
- Wrong assumptions prompt for correction inline
- Confirmed assumptions locked and greyed out

**Benefits:**
- One-click confirmation or rejection
- Visual status for each assumption
- No need to type corrections for simple yes/no
- Clear overview of what LLM has extracted

---

### Solution 4: Quick Action Buttons

**Add contextual buttons to reduce typing:**

```
┌─────────────────────────────────────────────┐
│ What would you like to do next?             │
│                                             │
│ [Add more details]  [Generate script]       │
│ [Edit assumptions]  [Start over]            │
└─────────────────────────────────────────────┘
```

**Benefits:**
- Guided navigation for common actions
- Reduces cognitive load
- Faster than typing commands
- Makes next steps obvious

---

## 4. Implementation Guidance

### Component Structure

**New HTML elements needed:**

```html
<!-- Structured Response Container -->
<div class="response-structured">

  <!-- Message Section -->
  <div class="response-message">
    <p>Conversational text here...</p>
  </div>

  <!-- Questions Section -->
  <div class="response-questions">
    <div class="question-card" data-question-id="q1">
      <div class="question-label">Target Market</div>
      <div class="question-text">Who is your ideal customer?</div>
      <input type="text" class="question-input" placeholder="Type your answer...">
      <div class="question-actions">
        <button class="btn-skip">Skip</button>
        <button class="btn-answer">Answer</button>
      </div>
    </div>
    <!-- More question cards... -->
  </div>

  <!-- Assumptions Section -->
  <div class="response-assumptions">
    <div class="assumption-badge" data-status="confirmed">
      <span class="assumption-text">B2B SaaS</span>
      <button class="assumption-toggle">✓</button>
      <button class="assumption-edit">✎</button>
    </div>
    <!-- More assumption badges... -->
  </div>

  <!-- Quick Actions -->
  <div class="response-actions">
    <button class="action-btn">Add more details</button>
    <button class="action-btn primary">Generate script</button>
  </div>

</div>
```

**CSS structure:**

```css
.response-structured {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.question-card {
  background: var(--surface);
  border: 1px solid var(--surface2);
  border-radius: 12px;
  padding: 16px;
}

.assumption-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 20px;
  background: var(--surface2);
}

.assumption-badge[data-status="confirmed"] {
  background: var(--success-dim);
  border: 1px solid var(--success);
}

.assumption-badge[data-status="wrong"] {
  background: var(--error-dim);
  border: 1px solid var(--error);
}
```

**JavaScript handlers:**

```javascript
// Handle inline question answers
document.querySelectorAll('.question-card .btn-answer').forEach(btn => {
  btn.addEventListener('click', (e) => {
    const card = e.target.closest('.question-card');
    const questionId = card.dataset.questionId;
    const answer = card.querySelector('.question-input').value;
    submitAnswer(questionId, answer);
  });
});

// Handle assumption toggles
document.querySelectorAll('.assumption-toggle').forEach(btn => {
  btn.addEventListener('click', (e) => {
    const badge = e.target.closest('.assumption-badge');
    cycleAssumptionStatus(badge);
  });
});

function cycleAssumptionStatus(badge) {
  const statuses = ['confirmed', 'wrong', 'unsure'];
  const current = badge.dataset.status;
  const next = statuses[(statuses.indexOf(current) + 1) % statuses.length];
  badge.dataset.status = next;
}
```

---

### ASCII Wireframe - New Chat UI

```
┌────────────────────────────────────────────────────────────────────┐
│  m(video)p    [Session ▼]    [Scripts ▼]         [LLM: Gemini ▼]  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────────────────────────────────┐  ┌──────────────┐│
│  │                                             │  │ PRODUCT      ││
│  │  [m] Tell me about your product idea...    │  │ CANVAS       ││
│  │                                             │  │              ││
│  │  ──────────────────────────────────────────│  │ Name: ...    ││
│  │                                             │  │ Problem: ... ││
│  │  [Y] It's a task app for remote teams...   │  │ Solution: ...││
│  │                                             │  │              ││
│  │  ──────────────────────────────────────────│  │ [Generate]   ││
│  │                                             │  └──────────────┘│
│  │  [m] ┌─────────────────────────────────┐   │                  │
│  │      │ Got it! A few questions:        │   │                  │
│  │      └─────────────────────────────────┘   │                  │
│  │                                             │                  │
│  │      ┌─────────────────────────────────┐   │                  │
│  │      │ 🎯 Target Market                │   │                  │
│  │      │ Who will use this?              │   │                  │
│  │      │ ┌─────────────────────────────┐ │   │                  │
│  │      │ │ Remote engineering teams    │ │   │                  │
│  │      │ └─────────────────────────────┘ │   │                  │
│  │      │ [Skip]              [Answer ➜] │   │                  │
│  │      └─────────────────────────────────┘   │                  │
│  │                                             │                  │
│  │      ┌─────────────────────────────────┐   │                  │
│  │      │ 📋 Assumptions                  │   │                  │
│  │      │                                 │   │                  │
│  │      │ [✓ SaaS] [✗ US only] [? Paid]  │   │                  │
│  │      └─────────────────────────────────┘   │                  │
│  │                                             │                  │
│  │      ┌─────────────────────────────────┐   │                  │
│  │      │ [Add details] [Generate script] │   │                  │
│  │      └─────────────────────────────────┘   │                  │
│  │                                             │                  │
│  ├─────────────────────────────────────────────┤                  │
│  │ ┌─────────────────────────────────────────┐ │                  │
│  │ │ Type a message...                  [Send]│ │                  │
│  │ └─────────────────────────────────────────┘ │                  │
│  └─────────────────────────────────────────────┘                  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

### LLM Output Format (JSON Schema)

To render structured UI, the LLM must return JSON instead of plain text:

```json
{
  "response_type": "structured",
  "message": "Got it! Let me ask a few clarifying questions.",
  "questions": [
    {
      "id": "q1",
      "label": "Target Market",
      "question": "Who is your ideal customer?",
      "placeholder": "e.g., Small business owners, developers...",
      "required": true
    },
    {
      "id": "q2",
      "label": "Key Differentiator",
      "question": "What makes your solution unique?",
      "placeholder": "e.g., AI-powered, faster than competitors...",
      "required": false
    }
  ],
  "assumptions": [
    {
      "id": "a1",
      "text": "B2B SaaS product",
      "confidence": "high",
      "status": "pending"
    },
    {
      "id": "a2",
      "text": "US market focus",
      "confidence": "medium",
      "status": "pending"
    }
  ],
  "quick_actions": [
    {
      "id": "add_details",
      "label": "Add more details",
      "action": "continue_conversation"
    },
    {
      "id": "generate",
      "label": "Generate script",
      "action": "trigger_generation",
      "primary": true
    }
  ],
  "product_understanding": {
    "name": "TaskFlow",
    "problem": "Remote teams struggle with task coordination",
    "solution": "Real-time collaborative task management",
    "confidence": 0.65
  }
}
```

**Schema definition:**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["response_type", "message"],
  "properties": {
    "response_type": {
      "enum": ["structured", "simple"]
    },
    "message": {
      "type": "string",
      "description": "Conversational message text"
    },
    "questions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "question"],
        "properties": {
          "id": { "type": "string" },
          "label": { "type": "string" },
          "question": { "type": "string" },
          "placeholder": { "type": "string" },
          "required": { "type": "boolean" }
        }
      }
    },
    "assumptions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "text"],
        "properties": {
          "id": { "type": "string" },
          "text": { "type": "string" },
          "confidence": { "enum": ["low", "medium", "high"] },
          "status": { "enum": ["pending", "confirmed", "rejected"] }
        }
      }
    },
    "quick_actions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "label", "action"],
        "properties": {
          "id": { "type": "string" },
          "label": { "type": "string" },
          "action": { "type": "string" },
          "primary": { "type": "boolean" }
        }
      }
    },
    "product_understanding": {
      "type": "object",
      "properties": {
        "name": { "type": "string" },
        "tagline": { "type": "string" },
        "problem": { "type": "string" },
        "solution": { "type": "string" },
        "target_user": { "type": "string" },
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
      }
    }
  }
}
```

---

### Changes to demo/templates/index.html

**Key modifications needed:**

1. **Add new CSS classes** for structured response components (question cards, assumption badges, action buttons)

2. **Modify `addMessageHTML()` function** to detect structured JSON responses and render appropriate components:

```javascript
function addMessageHTML(data, role) {
  if (role === 'assistant' && data.response_type === 'structured') {
    return renderStructuredResponse(data);
  }
  // Fall back to current behavior for simple responses
  return renderSimpleMessage(data.message || data, role);
}

function renderStructuredResponse(data) {
  let html = '<div class="response-structured">';

  // Message section
  if (data.message) {
    html += `<div class="response-message">${data.message}</div>`;
  }

  // Questions section
  if (data.questions?.length) {
    html += '<div class="response-questions">';
    data.questions.forEach(q => {
      html += renderQuestionCard(q);
    });
    html += '</div>';
  }

  // Assumptions section
  if (data.assumptions?.length) {
    html += '<div class="response-assumptions">';
    data.assumptions.forEach(a => {
      html += renderAssumptionBadge(a);
    });
    html += '</div>';
  }

  // Quick actions
  if (data.quick_actions?.length) {
    html += '<div class="response-actions">';
    data.quick_actions.forEach(action => {
      html += `<button class="action-btn ${action.primary ? 'primary' : ''}"
                       onclick="handleQuickAction('${action.action}')">${action.label}</button>`;
    });
    html += '</div>';
  }

  html += '</div>';
  return html;
}
```

3. **Add event handlers** for inline question answering and assumption toggling

4. **Modify `/chat` endpoint** to return structured JSON format (requires changes to demo/app.py prompt)

---

## 5. Implementation Priority

| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| 1 | Structured response rendering | Medium | High |
| 2 | Inline question cards | Medium | High |
| 3 | Assumption badges | Low | Medium |
| 4 | Quick action buttons | Low | Medium |
| 5 | LLM output format changes | Medium | High |

**Recommended Phase 1:**
- Implement structured response container
- Add question card components with inline inputs
- Modify LLM prompt to return JSON format

**Phase 2:**
- Add editable assumption badges
- Implement quick action buttons
- Add confirmation animations

---

## 6. References

- [ChatGPT UI Guidelines](https://developers.openai.com/apps-sdk/concepts/ui-guidelines/)
- [Claude Artifacts Documentation](https://support.claude.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them/)
- [Linear Design Philosophy](https://linear.app/now/design-for-the-ai-age)
- [Typeform Conditional Logic](https://tally.so/help/conditional-form-logic)
- [Intercom Conversational Design](https://www.intercom.com/blog/conversational-design-for-better-products/)
- [Intercom Interaction Design Fundamentals](https://www.intercom.com/blog/fundamentals-good-interaction-design/)
