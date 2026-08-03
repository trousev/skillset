# Stack — Stacked PR Workflow

Instructs Claude Code to deliver work as a stack of small, verified, CI-green PRs — one task per PR, each stacked on the previous one.

## What it does

When invoked via `/stack`, this skill transforms how the AI delivers code:

- **Result = a set of PRs**, not a single branch or a pile of commits on master
- Each PR is **small and focused** — one logical task, one concern
- Each PR is **stacked** on top of the previous one (branch-2 is based on branch-1, etc.)
- Each PR is **locally verified** before pushing — tests pass, linters pass, build succeeds
- Each PR is **CI-green** before merging — all repository checks must pass
- **No direct pushes to master** — everything goes through PRs

Supports `--merge` flag for cases where some PRs in the stack are already merged to master.

## Usage

### Standard — start a new stack from master

```
/stack
```

Followed by your task description. The AI will:

1. Plan the PR decomposition
2. Announce the stack plan
3. Implement each PR sequentially — verifying locally, waiting for CI, merging, then moving to the next

### With --merge — continue an existing stack

```
/stack --merge
```

Followed by your task description. The AI will:

1. Detect which PRs are already merged to master
2. Rebase remaining branches
3. Continue building the stack from where the merged PRs left off

## Install

```bash
# Add the marketplace (one-time)
claude marketplace add trousev/skillset

# Install the plugin
claude plugin install stack@trousev-skillset
```

## Example

```
/stack Add user authentication with JWT tokens

## Stack Plan

1. `feature/auth-db-schema` — Database migration for users table
2. `feature/auth-hash-utils` — Password hashing utilities
3. `feature/auth-jwt-middleware` — JWT token generation and middleware
4. `feature/auth-login-endpoint` — Login/logout API endpoints
5. `feature/auth-tests` — Integration tests

Each PR: one concern, locally verified, CI-green before merging.
```

## Why stacks?

- **Easier to review** — reviewing a 50-line PR takes minutes; reviewing a 2000-line PR takes hours
- **Faster CI** — small PRs run fewer tests, get results faster
- **Bisectable history** — if a bug is introduced, `git bisect` points to the exact change
- **Lower risk** — merging small, verified pieces reduces integration pain
- **No "big bang" merges** — each PR leaves master in a working state

## License

MIT
