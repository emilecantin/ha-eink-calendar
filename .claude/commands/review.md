Perform a code review of recent changes. Use $ARGUMENTS for scope (e.g., a specific file, "last commit", or "staged changes"). If no arguments, review all uncommitted changes.

## Process

1. **Gather the diff**: Use `git diff` (unstaged), `git diff --cached` (staged), or `git diff HEAD~1` (last commit) depending on the scope.
2. **Read full context**: For each changed file, read the complete file (not just the diff) to understand the changes in context.
3. **Review each change** against the criteria below.
4. **Output a structured review**.

## Review Criteria

For each finding, categorize as:

- **PASS** — Code is correct, clear, and follows project conventions. No action needed.
- **REWORK** — A concrete issue that the implementer should fix. Must include a specific description of what's wrong and what to do instead.
- **FLAG_FOR_HUMAN** — A design decision, trade-off, or ambiguity that needs human judgment. Explain the concern and options.

### What to Check

1. **Correctness**: Does the code do what it's supposed to? Logic errors, off-by-ones, missing edge cases.
2. **Project conventions**: Follows patterns established in CLAUDE.md and existing code. No unnecessary style changes.
3. **Security**: No injection vulnerabilities, no secrets in code, proper input validation at boundaries.
4. **Known pitfalls**: Check CLAUDE.md "Critical Technical Notes" for project-specific gotchas (e.g., iCal date handling, e-paper init order).
5. **Simplicity**: No over-engineering, unnecessary abstractions, or changes beyond scope.
6. **Breaking changes**: Could this break existing functionality? ESP32 firmware? HA integration?

### What NOT to Flag

- Style preferences that don't affect correctness
- Missing docstrings/comments on clear code
- Hypothetical future issues unrelated to the change
- Things already flagged in a previous review round

## Output Format

```
## Code Review

### Summary
[1-2 sentence overview of the changes and overall assessment]

### Findings

#### [filename:line] — REWORK
[Description of issue and how to fix it]

#### [filename:line] — FLAG_FOR_HUMAN
[Description of concern and options]

### Verdict: [PASS | NEEDS_REWORK | NEEDS_HUMAN_INPUT]
[If NEEDS_REWORK: list the REWORK items that must be addressed]
[If NEEDS_HUMAN_INPUT: list the FLAG_FOR_HUMAN items needing decisions]
```

If there are no findings, output:

```
## Code Review

### Summary
[Overview of changes]

### Verdict: PASS
All changes look good. No issues found.
```
