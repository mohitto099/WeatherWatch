
# Coding Agent Rules

## 1. Scope Control
- Fix only the issue explicitly reported by the user.
- Inspect the relevant code before making changes.
- Identify the root cause before editing.
- Modify the minimum number of files possible.
- Do not refactor, restructure, rename or optimize unrelated code.
- Do not modify working modules unless absolutely necessary.
- Preserve existing architecture, APIs, interfaces and coding conventions.

## 2. Testing and Resource Usage
- Do not run the entire test suite by default.
- Do not run builds, linting, type checks or other validation repeatedly.
- First identify the single most relevant test or validation command.
- Run targeted tests only when necessary.
- Never repeat a passing check without a specific reason.
- If a check fails, investigate the actual failure before rerunning it.
- Do not install additional dependencies unless explicitly necessary.

## 3. Context Management
- Treat the existing codebase as the source of truth.
- Do not assume how modules work; inspect their actual implementation.
- Do not invent requirements or introduce unnecessary features.
- If the root cause is unclear, ask the user rather than guessing.
- Do not expand the task beyond the reported bug.

## 4. Change Protection
- Never overwrite unrelated user changes.
- Do not revert existing modifications.
- Do not delete files or change configurations without justification.
- Avoid changing shared interfaces and dependencies.

## 5. Completion
- Summarize the root cause.
- List the exact files modified.
- Explain the fix briefly.
- Report which checks were actually executed.
- Clearly disclose anything not tested.
- Stop once the reported bug is fixed.

