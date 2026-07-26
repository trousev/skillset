# Eval Scenarios: product-planning

These scenarios test the product-planning skill's behavior. Each describes a user interaction and the expected behaviors from Claude when using this skill.

## Scenario: Basic feature planning invocation

**Prompt**: "Help me plan a user authentication feature. We need login, registration, and password reset."

**Expected behaviors**:
- Skill activates and begins Step 1 (Product Questions)
- Asks ONE question at a time (never batches multiple questions)
- First question is open-ended about the problem or user needs
- Creates a spec file at `./specs/FEATURE-user-authentication.md`
- Does NOT write implementation code

## Scenario: Asking clarifying questions before proceeding

**Prompt**: "I want to add dark mode to my app."

**Expected behaviors**:
- Skill begins with product questions about dark mode
- Asks about target users and their needs
- Explores whether this is system-following or manual toggle
- Does NOT jump to implementation details in the first question
- Waits for each answer before asking the next question

## Scenario: Step 4 Attack & Challenge is genuinely critical

**Prompt**: "Plan a real-time chat feature with WebSocket support."

**Expected behaviors**:
- By Step 4, challenges the developer on real concerns
- Asks about reconnection handling and message ordering
- Questions scalability (how many concurrent users?)
- Probes security (message encryption, authentication for WebSocket)
- Does NOT accept shallow answers — follows up on hand-waved responses

## Scenario: Skill does not implement

**Prompt**: "Plan a file upload feature with drag-and-drop."

**Expected behaviors**:
- Skill plans and produces a spec document
- Does NOT write any implementation code (no JavaScript, no React components)
- Ends with "I'm ready to implement this feature" or similar
- The spec file contains all 4 sections (Problem, Technical Design, Implementation Details, Risk Assessment)
