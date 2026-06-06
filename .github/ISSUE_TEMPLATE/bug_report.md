name: Bug report
description: Report a problem in O11yIA BR
labels: ["bug"]
assignees: []

body:
  - type: markdown
    attributes:
      value: |
        Thank you for reporting a bug! Please provide as much detail as possible.

  - type: textarea
    id: description
    attributes:
      label: Description
      description: What's the problem?
      placeholder: |
        Example: The dashboard crashes when I try to filter by team.
    validations:
      required: true

  - type: textarea
    id: steps
    attributes:
      label: Steps to reproduce
      description: How do I reproduce the issue?
      placeholder: |
        1. Start the backend with `docker compose up`
        2. Open the dashboard
        3. Navigate to Team view
        4. Click the "Filter" dropdown
        5. Select a team
        6. Dashboard crashes
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: Expected behavior
      description: What should happen instead?
      placeholder: |
        The dashboard should filter metrics by the selected team.

  - type: textarea
    id: actual
    attributes:
      label: Actual behavior
      description: What actually happens?
      placeholder: |
        The dashboard refreshes momentarily, then throws a "KeyError" exception.

  - type: textarea
    id: environment
    attributes:
      label: Environment
      description: |
        Share details about your setup:
        - OS and version (Windows 10, macOS 14, Ubuntu 22.04, etc.)
        - Docker version (if using Docker)
        - Python version (if running locally)
        - VSCode/Chrome/IntelliJ version (if collector-related)
      placeholder: |
        - OS: macOS 14.1
        - Docker: 25.0.1
        - Python: 3.11
        - Docker Compose: 2.24.0

  - type: textarea
    id: logs
    attributes:
      label: Error or logs
      description: |
        If you have error messages, logs, or stack traces, paste them here.
      placeholder: |
        ```
        Traceback (most recent call last):
          File "...", line X, in ...
        KeyError: 'team'
        ```

  - type: textarea
    id: privacy
    attributes:
      label: Privacy/security impact
      description: |
        Does this bug potentially affect privacy or security?
        (e.g., leaking code, prompts, secrets, or exposing unauthorized data?)
      placeholder: |
        No known privacy impact.

  - type: textarea
    id: extra
    attributes:
      label: Additional context
      description: Any other information that might help?
      placeholder: |
        - Also occurs with X team size
        - Workaround: restart the dashboard