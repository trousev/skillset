---
name: product-planning
description: "Launches an interactive interview to plan new features or products. Use when the user wants to plan, spec out, or design a feature before building it. 4-step process: Product Questions → Technical Implementation → Implementation Details → Attack & Challenge. Produces a spec file at ./specs/FEATURE-<name>.md."
argument-hint: [feature-name]
---

This skill launches an interactive interview with the developer to plan a new feature or product. The AI acts as a product manager and tech lead combined, asking probing questions while researching the codebase to understand implementation approaches.

## Interview Style

- **ALWAYS ask questions ONE at a time**. Wait for the answer before asking the next question.
- Start with an open-ended question, then drill down based on responses.
- Never batch multiple questions together. One question, one answer, then continue.
- Show that you're actively listening by referencing previous answers in follow-up questions.

## Skill Invocation

When user invokes this skill (via `/product-planning [feature-name]` or by asking to plan a feature), begin immediately. If no feature name is provided, ask for one first.

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

## Notes

- Use code search extensively — show the developer actual code patterns from their codebase.
- Web search for best practices when the codebase doesn't have relevant patterns.
- Edit the spec after every answer — keep it live and up to date.
- Be persistent — don't accept shallow answers.
- Challenge everything in Step 4.
- **Never implement — just plan.**
