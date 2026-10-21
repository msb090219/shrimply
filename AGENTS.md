# Repository workflow

Before changing application code, read `docs/TODO.md` and identify the task the
change addresses. If the change adds user-facing behavior, add or update its task
before implementation. At the same time, add a linked entry under **New features
to check on Mac** with the Windows task ID, an implementation-commit placeholder,
and Mac test steps. If the feature starts on Mac, make the reciprocal Windows
handoff clear in the task.

Implement shared behavior once where possible. After the code lands, replace the
handoff placeholder with its commit and record Windows and Mac packaged-app
verification separately. Automated tests alone do not complete a platform check.
For fixes and maintenance, update `docs/TODO.md` when they change an existing task
or leave platform-specific work outstanding; do not create a Mac feature entry
for a change with no user-facing or platform impact.
