---
name: stack
description: "Instructs the AI to deliver work as a stack of small, focused PRs — one task per PR, each stacked on the previous one. Use when the user wants structured, reviewable, CI-verified pull requests instead of a single large merge. With --merge: fully autonomous — create PRs, wait for CI, and merge them all. Without --merge: create PRs but leave merging to the human."
argument-hint: "[--merge]"
---

# /stack — Stacked PR Workflow

This skill instructs the AI to deliver the **result** as a stack of small, independently reviewable PRs — each building on top of the previous one, like a tower. No monolithic PRs. No direct pushes to master.

## Core Concept

The **result** of your work is NOT a single branch. It is a **stack of PRs**:

```
master  ←  PR #1  ←  PR #2  ←  PR #3
              ↑         ↑         ↑
          branch-1   branch-2   branch-3
          (based on  (based on  (based on
           master)   branch-1)  branch-2)
```

Each PR:
- **Is small** — one logical change, one task. A reviewer should be able to understand it in 5 minutes.
- **Is atomic** — it stands alone conceptually. It doesn't depend on "I'll fix this in the next PR."
- **Is locally verified** — you MUST build/test/lint locally before pushing. If the repo has scripts (`./script/test`, `./script/lint`), run them.
- **Is CI-green** — all repository signals (checks, statuses, required workflows) must pass before merging.
- **Stacks on the previous one** — each branch is created from the previous PR's branch (not master), unless it's the first PR or the previous PR is already merged.

## Branch Naming

Use descriptive, kebab-case branch names that reflect the task:

```
feature/name-part-1      # First PR — base: master
feature/name-part-2      # Second PR — base: feature/name-part-1
feature/name-part-3      # Third PR — base: feature/name-part-2
```

For bug fixes or cleanup:
```
fix/description
chore/description
```

**Never use generic names** like `feature/updates`, `fix/bug`, `dev-branch`.

## `--merge` Flag — Autonomous Mode

When the user invokes `/stack --merge`, you are in **autonomous mode**. This means:

- You plan, implement, create PRs, **and merge them all** — without asking for confirmation on each merge.
- After each PR passes CI, you merge it immediately and move to the next.
- You do NOT stop to ask "shall I merge?" — the `--merge` flag IS the user's pre-authorization to merge.

Without `--merge`: you are in **manual mode**. You still plan, implement, and create PRs — but you **do NOT merge**. You stop after creating each PR (or at the end of the stack) and tell the user the PRs are ready for review. The human decides when to merge.

### Merge Strategy

When merging autonomously, use the repository's preferred merge method:

```bash
# Check what the repo uses (look at merged PRs or .github/ settings)
gh pr view <pr-number> --json mergedBy,state

# Default to --squash for clean history unless the repo clearly uses --merge
gh pr merge <branch-name> --squash --auto --delete-branch
```

**Always use `--auto`** when available — it tells GitHub to merge as soon as all required checks pass, rather than polling CI yourself. If `--auto` is not supported or the repo has no required checks, poll with `gh pr checks --watch` and merge immediately after.

## Workflow

### Phase 1: Plan the Stack

Before writing code, plan the PR decomposition:

1. **Read the requirements** thoroughly.
2. **Decompose** into independent, logical tasks. Each task → one PR.
3. **Order** the tasks: foundational changes first, dependent changes later.
4. **Validate**: is each task truly one concern? If a task description has "and" in it, split it.
5. **Announce the plan** to the user:

```
## Stack Plan

1. `feature/name-scaffold` — Project scaffold, scripts, dependencies
2. `feature/name-core` — Core implementation
3. `feature/name-tests` — Tests and edge cases
4. `feature/name-docs` — Documentation updates

Each PR passes local verification + CI before proceeding to the next.
```

### Phase 2: Implement PR by PR

For each PR in the stack, from first to last:

1. **Create the branch** from the correct base:
   - First PR: from `master` (or `main`)
   - Subsequent PRs: from the previous PR's branch
   ```bash
   git checkout <previous-branch>
   git checkout -b <new-branch>
   ```

2. **Implement the task** — and ONLY that task. Do not fix unrelated things. Do not refactor code that isn't directly related to this task. Stay focused.

3. **Verify locally** — before pushing, verify your work:
   ```bash
   # Run project tests (use whatever scripts the project provides)
   ./script/test   # or equivalent
   
   # Run linters
   ./script/lint   # or equivalent
   
   # If the project has a build step, run it
   ./script/build  # or equivalent
   ```
   If anything fails, fix it NOW. Do NOT push broken code and "fix it in the next PR."

4. **Self-review the diff**:
   ```bash
   git diff <base-branch>...HEAD
   ```
   Ask yourself:
   - Is every changed line necessary for THIS task?
   - Are there leftover debug logs or commented-out code?
   - Does the code follow the project's conventions (CLAUDE.md, AGENTS.md)?

5. **Push and create the PR**:
   ```bash
   git push -u origin <branch-name>
   gh pr create \
     --base <previous-branch-or-master> \
     --title "<descriptive title>" \
     --body "<what this PR does, why, and how to verify>"
   ```

6. **Wait for CI** — monitor the PR until all checks pass:
   ```bash
   gh pr checks <branch-name> --watch
   ```
   - If CI fails: fix the branch, push again, wait for re-run. Do NOT open the next PR while CI is red.
   - If CI passes: move to the next PR or merge.

7. **Merge** (if `--merge` mode) — once CI is green AND the PR is complete:
   ```bash
   gh pr merge <branch-name> --squash --delete-branch
   ```
   If the project requires PR approval: wait for it. Don't bypass branch protection.
   If NOT in `--merge` mode: **stop here** — the PR is ready for human review. Do NOT merge.

8. **Update the stack** — after merging, rebase remaining unmerged branches:
   ```bash
   git checkout <next-branch>
   git rebase master   # or the merged PR's new base
   ```

### Phase 3: Final Verification

After all PRs are merged to master:

1. **Check out master** and pull:
   ```bash
   git checkout master
   git pull origin master
   ```

2. **Run the full test suite one last time** to verify the entire stack integrates correctly.

3. **Report the result**:

   **With `--merge`** (autonomous — all merged):
   ```
   ## Stack Complete ✓
   
   ✅ PR #1: <title> — <link> (merged)
   ✅ PR #2: <title> — <link> (merged)
   ✅ PR #3: <title> — <link> (merged)
   
   All checks green. All PRs merged.
   ```

   **Without `--merge`** (manual — PRs open, not merged):
   ```
   ## Stack Ready for Review
   
   🔵 PR #1: <title> — <link> (CI ✅)
   🔵 PR #2: <title> — <link> (CI ✅)
   🔵 PR #3: <title> — <link> (CI ✅)
   
   All checks green. PRs are open and ready for your review.
   ```

## PR Quality Standards

Every PR must meet these standards:

| Standard | Check |
|----------|-------|
| **Single concern** | The PR does ONE thing. Not two things. Not "thing A + cleanup." |
| **Small diff** | Ideally <200 lines changed. Never >500. If it's bigger, split it. |
| **Self-contained** | The PR can be merged independently without breaking master. |
| **Locally verified** | Tests pass locally. Linters pass. Build succeeds. |
| **CI green** | All repository checks are passing. No skipped or ignored failures. |
| **Descriptive title** | The PR title explains WHAT, not just where. "Add database migration for user preferences", not "Update schema." |
| **Useful body** | The PR body explains WHY this change, HOW it works, and HOW to verify it. |
| **No unrelated changes** | No drive-by formatting, no "while I'm here" refactors, no fixing unrelated typos. Open a separate PR if something else needs fixing. |

## Branch Protection

If the repository does NOT yet have branch protection configured, set it up:

```bash
# Require PR before merging (no direct pushes to master)
gh api repos/<owner>/<repo>/branches/master/protection \
  -X PUT \
  -F required_status_checks='{"strict":true,"contexts":[]}' \
  -F enforce_admins=false \
  -F required_pull_request_reviews='{"required_approving_review_count":0}' \
  -F restrictions=null

# Block merge if CI checks are failing
# (Set specific check contexts as required after they exist)
```

**Important:** Do NOT require code reviews for solo projects. Do NOT add restrictions beyond PR-required + CI-green.

## Anti-Patterns

- ❌ **Monolithic PR**: "The feature" in one PR with 40 files changed. Split it.
- ❌ **Skipping local verification**: "I'll let CI catch it." CI is the safety net, not the primary verification. Run tests locally FIRST.
- ❌ **Stacking on unmerged PRs indefinitely**: Don't build a 10-PR tower on unmerged branches. Merge early, merge often. Aim for 2–4 unmerged PRs max in the stack at any time.
- ❌ **Direct pushes to master**: Never. Always through a PR. Even for "trivial" fixes.
- ❌ **Merging with failing CI**: Never merge a red PR. Fix it first. The only exception: flaky tests that are pre-existing and documented as flaky.
- ❌ **Scope creep in PRs**: You notice a typo in an unrelated file. Don't fix it in this PR. Open a separate PR or note it for later.
- ❌ **Force-pushing to a shared branch**: After a PR is opened, use `git push --force-with-lease` only if you're the only contributor. If others may have checked out your branch, use regular pushes or coordinate.
- ❌ **Opening PRs without a plan**: Don't just start coding and figure out the stack later. Plan first, then implement.
- ❌ **"Will fix in next PR"**: Every PR must be correct and complete on its own. No deferred fixes.
- ❌ **Not checking the repo's CLAUDE.md/AGENTS.md**: Every repo has conventions. Read them before writing code. Follow them.
- ❌ **Asking to merge in `--merge` mode**: The `--merge` flag IS the authorization. Don't ask "shall I merge this PR?" — just merge it when CI is green.
- ❌ **Merging without `--merge`**: The absence of `--merge` means the human wants control. Don't merge anything — open PRs and report they're ready.

## Quick Reference

### With `--merge` (autonomous: create → CI → merge → next)

```bash
# Plan
git fetch origin
git checkout master && git pull

# PR #1
git checkout -b feature/name-1
# ... implement, verify locally ...
git push -u origin feature/name-1
gh pr create --base master --title "Part 1: <description>" --body "..."
gh pr checks feature/name-1 --watch
gh pr merge feature/name-1 --squash --delete-branch   # merge immediately, no questions

# PR #2 — based on PR #1's branch (or rebase onto master if #1 merged)
git checkout feature/name-1 && git pull
git checkout -b feature/name-2
# ... implement, verify locally ...
git push -u origin feature/name-2
gh pr create --base feature/name-1 --title "Part 2: <description>" --body "..."

# After PR #1 is merged, rebase #2
git checkout feature/name-2
git rebase master
git push --force-with-lease

# Merge #2
gh pr merge feature/name-2 --squash --delete-branch

# Repeat for all PRs in the stack...

# Final
git checkout master && git pull
./script/test
# Report: all merged.
```

### Without `--merge` (manual: create PRs, human merges)

```bash
# Same as above for each PR, but STOP after creating the PR and CI passing.
# Do NOT run `gh pr merge`.

# PR #1
git checkout -b feature/name-1
# ... implement, verify locally ...
git push -u origin feature/name-1
gh pr create --base master --title "Part 1: <description>" --body "..."
gh pr checks feature/name-1 --watch
# STOP. PR is ready. Do not merge.

# ... repeat for all PRs ...

# Final report:
# All PRs open, CI green, ready for your review.
```

## Notes

- The stack is a **delivery mechanism**, not a planning exercise. The goal is to get small, verified pieces into master quickly and safely.
- Each PR should leave the codebase in a **working state**. A half-implemented feature that doesn't compile or crashes is not acceptable.
- If a PR grows unexpectedly large during implementation, **stop and re-plan**. Split it into smaller PRs.
- **Merge early.** Don't hoard unmerged branches. The longer a branch sits unmerged, the more conflicts and drift it accumulates.
- When in doubt: **smaller PRs, more of them.** A 50-line PR is always better than a 500-line PR.
