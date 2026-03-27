Break a feature or task into discrete "work units" that can each be implemented and reviewed independently.

## Input

The user will describe a feature, bug fix, or task. Use $ARGUMENTS as the task description.

## Process

1. **Analyze the task**: Read relevant code, understand scope and dependencies.
2. **Break into work units**: Each work unit must:
   - Be small enough to fit entirely in context (aim for <300 lines changed)
   - Be independently testable or verifiable
   - Leave the codebase in a working state when complete
   - Have a clear, specific description of what changes to make
3. **Order by dependency**: Earlier units should not depend on later ones.
4. **Output a numbered plan** in this format:

```
## Work Plan: [Task Title]

### Unit 1: [Short title]
**Files**: list of files to touch
**Changes**: Specific description of what to implement
**Tests**: What tests to write (these are written first per TDD)
**Verify**: How to verify this unit works

### Unit 2: [Short title]
...
```

## Guidelines

- Prefer many small units over few large ones
- Each unit should ideally touch 1-3 files
- If a unit requires changing >5 files, consider splitting further
- Every unit follows TDD: tests are written first, so each unit must describe what tests to write
- If a project area lacks test infrastructure, the first unit should set it up
- Flag any units that need human decision-making with **[NEEDS INPUT]**
- After presenting the plan, ask the user to confirm or adjust before proceeding
