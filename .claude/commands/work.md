Execute a single work unit with an automatic review loop.

## Input

$ARGUMENTS should describe the work unit. This can be:
- A description of what to implement (e.g., "Add ETag header to bitmap responses")
- A reference to a work plan unit (e.g., "Unit 2 from the plan above")

## Process

### Phase 1: Implement (TDD — Red/Green/Refactor)

1. **Understand the task**: Read all relevant files before making changes.
2. **Red — Write failing tests first**:
   - Write tests that describe the expected behavior for this work unit
   - Run the tests and confirm they fail (this validates the tests are meaningful)
   - If the project area doesn't have a test infrastructure yet, set one up as part of this step
3. **Green — Make the tests pass**:
   - Write the minimal production code needed to make the failing tests pass
   - Do not add behavior beyond what the tests require
   - Run the tests and confirm they all pass
4. **Refactor — Clean up**:
   - Improve the code structure while keeping tests green
   - Remove duplication, improve naming, simplify logic
   - Run the tests after each refactor step to ensure nothing breaks
5. **Self-check**: Before requesting review, verify:
   - All tests pass
   - Code compiles/passes type checks if applicable
   - Changes are minimal and focused on the task
   - No debug code left behind

### Phase 2: Review Loop

4. **Spawn a reviewer agent** using the code-reviewer agent type. Give it:
   - The full diff of your changes
   - The work unit description for context
   - Instructions to follow the review criteria from the `/review` command

5. **Process review results**:
   - **All PASS**: Done! Summarize what was done to the user.
   - **Has REWORK items**: Fix each REWORK item, then request review again (go to step 4).
   - **Has FLAG_FOR_HUMAN items (no REWORK)**: Present the flagged items to the user and wait for their input.
   - **Has both REWORK and FLAG_FOR_HUMAN**: Fix all REWORK items first, then re-review. FLAG_FOR_HUMAN items persist across review rounds.

6. **Max 3 review rounds**: If REWORK items persist after 3 rounds, present the remaining issues to the user as FLAG_FOR_HUMAN.

### Phase 2.5: Documentation Check

7. **Spawn a documentation agent** using the documentation-generator agent type. Give it:
   - The full diff of your changes
   - The work unit description for context
   - Instructions to check whether any existing documentation needs updating as a result of the changes. This includes:
     - `CLAUDE.md` (project structure, endpoints, architecture decisions, technical notes)
     - `docs/` folder contents
     - README or other docs at the repo root
     - Inline docstrings/comments that reference changed behavior
   - The agent should either make the necessary doc updates directly, or report that no updates are needed.
   - Do NOT create new documentation files unless the changes introduce entirely new concepts not covered anywhere.

### Phase 3: Commit & PR

8. **If FLAG_FOR_HUMAN items exist**: Present them to the user and wait for decisions before proceeding.

9. **Create a branch and commit**:
   - Branch name: `<type>/<short-kebab-description>` using conventional prefixes: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`, `test/` (e.g., `feat/add-etag-headers`, `fix/ical-date-offset`)
   - Create the branch from the current HEAD
   - Stage only the files changed in this work unit (including any doc updates from Phase 2.5)
   - Commit with a clear message describing the change

10. **Push and create a PR**:
    - Push the branch to origin
    - Create a PR using `gh pr create` with:
      - A concise title
      - A body summarizing the changes, any FLAG_FOR_HUMAN decisions made, and a test plan
    - Return the PR URL to the user

11. **Switch back to the base branch** so the next work unit starts clean.

## Guidelines

- Keep changes focused on the work unit — don't fix unrelated issues
- If the work unit turns out to be larger than expected, stop and tell the user it should be split
- If you hit a blocker that requires a design decision, stop and ask rather than guessing
