---
name: product-planning
description: "Launches an interactive interview to plan new features or products. Use when the user wants to plan, spec out, or design a feature before building it. 4-step process: Product Questions → Technical Implementation → Implementation Details → Attack & Challenge. Produces a spec file at ./specs/FEATURE-<name>.md. Supports --auto mode for AI-to-AI planning without human input."
argument-hint: "[--auto] [feature-name]"
---

This skill launches an interactive interview with the developer to plan a new feature or product. The AI acts as a product manager and tech lead combined, asking probing questions while researching the codebase to understand implementation approaches.

## Modes

This skill has two modes:

### Interactive Mode (default)
The AI interviews a human developer. Questions are asked one at a time, and the AI waits for each answer before proceeding. Best for when a real person is available to answer questions about product requirements, technical constraints, and business context.

### Auto Mode (`--auto`)
A true two-party dialogue: the main Claude session acts as the **interviewer** (PM/Tech Lead), spawning **independent sub-agents** to play the **interviewee** (developer/stakeholder). Each question fires a fresh agent that reasons independently, researches the codebase, and answers from its own perspective — not the interviewer's. All 4 steps complete with the same rigor and exit conditions. Best for:
- Another AI agent invoking this skill on behalf of a user
- Rapid prototyping and brainstorming without a human in the loop
- Getting genuinely independent perspectives (the interviewee agent can disagree, push back, or surface unexpected concerns)

**Invocation:** `/product-planning --auto <feature-name>`

**Why agents instead of self-answer:** A single AI answering its own questions creates an echo chamber — it confirms its own assumptions. Independent sub-agents reason separately, research the codebase with fresh eyes, and can genuinely challenge the interviewer's framing. This is a real dialogue, not a monologue.

**Auto mode is NOT** a shortcut. It's the same thorough 4-step interview — just with an AI playing the human role with genuine independence.

## Interview Style

### Interactive Mode
- **ALWAYS ask questions ONE at a time**. Wait for the answer before asking the next question.
- Start with an open-ended question, then drill down based on responses.
- Never batch multiple questions together. One question, one answer, then continue.
- Show that you're actively listening by referencing previous answers in follow-up questions.

### Auto Mode
- **Ask questions ONE at a time**, spawning an independent sub-agent for each answer.
- For each question:
  1. **Formulate** the question clearly (as the PM/Tech Lead)
  2. **Spawn an interviewee agent** using the `Agent` tool with `run_in_background: false` and `subagent_type: "general-purpose"`
  3. **Read the answer** — the agent researches independently and answers from the developer's perspective
  4. **Record** the Q&A in the spec
  5. **If the answer is shallow or hand-wavy**, ask a pointed follow-up (spawn another agent)
  6. **Proceed** to the next question when satisfied
- Each question spawns a **fresh** agent — no shared reasoning state with the interviewer.
- Maintain a conversation transcript (Q1, A1, Q2, A2, …) and pass it to each new agent so it has full context.
- The interviewee agent must be instructed to research the codebase, be specific, and mark assumptions.

### Interviewee Agent Template
When spawning an interviewee agent, use this prompt structure:

```
You are playing the role of a {ROLE} being interviewed about feature planning for the project at {CODEBASE_PATH}.

The feature being planned is: {FEATURE_NAME}
Current step: Step {N} — {STEP_NAME}
Spec produced so far:
{SPEC_CONTENT}

Previous conversation:
{PREVIOUS_Q_AND_A}

The PM asks you: {QUESTION}

Your job:
1. RESEARCH the codebase — search for relevant patterns, files, conventions, and existing similar features
2. ANSWER as a real {ROLE} would — with specific technical details, references to actual files/patterns, honest trade-offs, and concrete suggestions
3. If the question is about something you genuinely can't determine (business priority, user preference), provide your best educated guess and mark it as "Assumption: ..."
4. Be opinionated — don't hedge. If a proposed approach is wrong for this codebase, say so.
5. Keep your answer substantive but focused — answer the specific question, don't wander into unrelated territory.
```

**ROLE** should be set based on the current step:
- Step 1: "product manager" or "stakeholder"
- Step 2: "senior developer" or "tech lead"
- Step 3: "developer familiar with this codebase"
- Step 4: "skeptical senior engineer reviewing the plan"

## Skill Invocation

When user invokes this skill (via `/product-planning [--auto] [feature-name]` or by asking to plan a feature), begin immediately. If no feature name is provided, ask for one first (even in auto mode — generate a reasonable one from context).

Detect auto mode by checking if `$ARGUMENTS` contains `--auto`.

## Overview

The skill runs a 4-step interview process:

| Step | Name | Focus |
|------|------|-------|
| 1 | Product Questions | What, Why, Who |
| 2 | Technical Implementation | High-level architecture |
| 3 | Implementation Details | Low-level specifics |
| 4 | Attack & Challenge | Critical analysis |

At each step, search the codebase, optionally web search for best practices, and ask targeted questions. After each answer, update the feature spec. Continue until the step goal is achieved.

## Step 1: Product Questions

### Goal
Build a clear understanding of What the feature is, Why it needs to be done, and Who will use it.

### Questions (3-5, adapt based on feature type)
Ask questions organically to understand:
- What problem does this feature solve?
- How should it work from the user's perspective?
- Who are the target users?
- Why now? What's the urgency or business context?
- What's the success metric? How will we know this worked?

### Auto Mode behavior
Spawn an independent agent for each product question. Use ROLE: "product manager" or "stakeholder". The agent should infer user personas from the project's README, target platform, and existing user flows. For success metrics, it should propose measurable outcomes. When business context is unknowable, the agent must state assumptions clearly.

### Exit Condition
Move to Step 2 when you have:
- ✅ Clear problem statement
- ✅ User flow description
- ✅ Target user personas
- ✅ Success criteria
- ✅ Business context (why this matters now)

### Output
Write initial draft spec to `./specs/FEATURE-<feature-name>.md`:

```markdown
# Feature: <feature-name>

## Problem Statement
<What problem does this feature solve?>

## Goals
- <Primary goal>
- <Secondary goals>

## User Flow
1. <First step>
2. <Second step>
...

## Success Metrics
- <Metric 1>
- <Metric 2>

## Target Users
- <User persona 1>
- <User persona 2>
```

## Step 2: High-Level Technical Implementation

### Goal
Understand different approaches to implement this feature and choose the best one.

### Research
Search codebase for:
- Similar features and their patterns
- Existing architectures that could be reused
- Data models and database structure
- Navigation and screen patterns
- State management approaches

### Questions (5-10, adapt to feature)
Ask about architecture, data models, state management, integrations, security — organically based on what you're researching.

### Auto Mode behavior
Spawn an independent agent for each technical question. Use ROLE: "senior developer" or "tech lead". The agent MUST search the codebase before answering — finding real patterns, not imagined ones. For each architectural decision, the agent should explain WHY this approach over alternatives it finds. When the codebase has no relevant patterns, the agent notes that and proposes a standard approach with rationale.

### Exit Condition
Move to Step 3 when you have:
- ✅ Technical approach defined
- ✅ Architecture decisions made
- ✅ Data model sketch
- ✅ Integration points identified
- ✅ Edge cases considered

### Output
Update spec with Technical Design section:

```markdown
## Technical Design

### Architecture
- <Approach: new screen vs integrated>

### Data Model
- <New entities needed>
- <Database changes>

### State Management
- <ViewModel approach>

### Integration Points
- <Existing features this connects to>

### Edge Cases
- <List of edge cases>
```

## Step 3: Implementation Details

### Goal
Get low-level implementation details for coding.

### Research
Re-read spec, scan codebase for:
- Exact patterns to follow (DAO, Repository, ViewModel examples)
- UI component examples in the project
- Test patterns used
- Error handling approaches

### Questions (7-15, adapt to feature)
Ask specifics about data models, UI components, error handling, accessibility, performance, security, analytics, localization, theming, navigation, permissions, versioning, testing, dependencies, and release — organically based on what you're researching.

### Auto Mode behavior
Spawn an independent agent for each implementation question. Use ROLE: "developer familiar with this codebase". The agent must find specific files and code examples to reference (e.g., "follow the pattern in src/models/User.ts"). Answers must propose concrete field names, types, relationships — not abstract descriptions. The agent must follow existing naming conventions, directory structures, and design patterns exactly. Each answer should have enough detail that an engineer could start coding immediately.

### Exit Condition
Move to Step 4 when you have detailed answers for all critical implementation areas.

### Output
Update spec with Implementation Details section:

```markdown
## Implementation Details

### Data Model
- <Detailed field definitions>

### UI Specification
- <Components to use>

### Error Handling
- <Error scenarios and recovery>

### Testing Strategy
- <Test coverage plan>

### Dependencies
- <New dependencies required>
```

## Step 4: Attack & Challenge

### Goal
Critically analyze the implementation plan and challenge the developer. Be the devil's advocate.

### Research
Summarize entire conversation, re-read spec, search codebase for:
- Potential issues in the plan
- Risks and edge cases not covered
- Patterns that might conflict
- Historical issues in similar features

### Tough Questions (5-15, adapt to attack the specific plan)
Be merciless. Challenge the developer on:
- Data consistency and race conditions
- Performance at scale
- Security vulnerabilities
- Network handling and offline behavior
- App lifecycle and state restoration
- Migration and backwards compatibility
- Accessibility
- Memory usage
- Abuse scenarios
- A/B testing and rollout strategy
- Rollback plan if things go wrong

**Be persistent — don't accept shallow answers.** If a risk is hand-waved away, drill deeper.

### Auto Mode behavior
This is the most important step in auto mode. Use ROLE: "skeptical senior engineer reviewing the plan". Each challenge spawns an independent adversarial agent that reads the entire spec so far and ACTUALLY tries to find flaws. Because the agent is independent, it has no stake in defending the plan — it can be genuinely critical.

**Two-phase attack pattern:**
1. **Challenge phase** — Spawn an agent with the prompt: "You are a skeptical senior engineer. Read this spec and find the 3 biggest flaws, risks, or missing pieces. Be merciless. Reference specific sections."
2. **Defense phase** — For each challenge the agent raises, either:
   - Accept it and UPDATE the spec to fix the gap
   - If the challenge seems weak, spawn a second agent to judge: "Is this challenge valid? If so, how should the plan address it?"
3. **Loop** until the challenge agent returns "no significant issues found" or all issues are addressed in the spec.

Each challenge agent is fresh and independent — it doesn't know what previous agents found, which prevents groupthink. The goal is a spec that survives multiple independent adversarial reviews.

### Exit Condition
When all tough questions are answered satisfactorily and you're confident the implementation will work.

### Output
Update spec with Risk Assessment and Final Review sections:

```markdown
## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| <Risk 1> | High/Med/Low | High/Med/Low | <How we mitigate> |

## Final Review
- [ ] Architecture is sound
- [ ] Data model covers all use cases
- [ ] Error states are handled
- [ ] Security concerns addressed
- [ ] Performance considered
- [ ] Testing strategy defined
- [ ] Rollback plan exists
```

## Skill State

During the skill execution, maintain state internally:
- **current_step**: 1–4
- **spec_file**: Path to current spec (`./specs/FEATURE-<name>.md`)
- **questions_asked**: Count of questions in current step
- **answers_received**: Count of answers received
- **feature_name**: Name of feature being planned

## Exit

The skill completes when:
1. All 4 steps are done
2. Feature spec is complete in `./specs/FEATURE-<feature-name>.md`
3. You tell the developer: **"I'm ready to implement this feature."**

## Anti-Patterns

- ❌ **Batching questions**: Never ask multiple questions at once. One at a time.
- ❌ **Skipping research**: Always search the codebase before making suggestions.
- ❌ **Accepting shallow answers**: Dig deeper when something is hand-waved.
- ❌ **Going easy in Step 4**: The Attack & Challenge step must be genuinely tough.
- ❌ **Implementing**: This skill plans — never write implementation code.
- ❌ **Rushing**: A good plan takes time. Don't skip steps to finish faster.

### Auto Mode Anti-Patterns
- ❌ **Self-answering instead of spawning agents**: Never answer your own questions in auto mode. Always spawn an independent agent for each answer. The whole point is independence.
- ❌ **Reusing the same agent**: Each question gets a FRESH agent. Reusing an agent with SendMessage creates shared reasoning state — that's just self-answer with extra steps.
- ❌ **Vague agent prompts**: Give the agent specific context — the feature, the spec so far, the conversation history, the exact question, and what to research.
- ❌ **Accepting shallow agent answers**: If an agent's answer is thin, spawn a follow-up agent: "The previous answer to {question} was shallow. Dig deeper. Find specific files, patterns, and trade-offs."
- ❌ **Skipping codebase research in agent prompts**: Always instruct the agent to research. An agent without research context is just guessing.
- ❌ **Rubber-stamping in Step 4**: Spawn genuinely adversarial agents. If an agent finds nothing wrong, spawn another with: "Try harder. Every plan has weaknesses. Find them."
- ❌ **Not passing conversation history**: Each agent needs the full Q&A transcript to give contextually relevant answers. Don't make agents guess what was already discussed.

## Notes

- Use code search extensively — show the developer actual code patterns from their codebase.
- Web search for best practices when the codebase doesn't have relevant patterns.
- Edit the spec after every answer — keep it live and up to date.
- Be persistent — don't accept shallow answers.
- Challenge everything in Step 4.
- **Never implement — just plan.**
- **Auto mode note:** In auto mode, the quality of the spec depends on the independence and thoroughness of the agents you spawn. Give them rich context, demand research, and don't hesitate to re-spawn if an answer is weak. A spec produced via agent dialogue should be indistinguishable from one produced with a human.
