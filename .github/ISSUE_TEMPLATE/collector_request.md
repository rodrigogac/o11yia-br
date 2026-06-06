name: Collector request
description: Suggest or discuss a new data collector
labels: ["collector"]
assignees: []

body:
  - type: markdown
    attributes:
      value: |
        Thank you for suggesting a collector! Please describe the tool and what metrics you'd like to capture.

  - type: textarea
    id: tool
    attributes:
      label: Tool/Source
      description: What tool or IDE should this collector support?
      placeholder: |
        Example: JetBrains Fleet, Cursor IDE, GitHub Copilot (web), etc.
    validations:
      required: true

  - type: textarea
    id: metrics
    attributes:
      label: What metrics should be collected?
      description: What usage information should this collector capture?
      placeholder: |
        - Token counts (input/output)
        - Model name
        - Request/interaction duration
        - Feature used (chat, inline completion, etc.)
        - Error/status codes
    validations:
      required: true

  - type: textarea
    id: no_collect
    attributes:
      label: What data must NOT be collected?
      description: Be explicit about boundaries (privacy-critical).
      placeholder: |
        - NO source code
        - NO prompt content
        - NO generated code
        - NO secrets or API keys
        - NO user messages or conversations
        - NO keystroke logging
        - NO screenshots
    validations:
      required: true

  - type: textarea
    id: use_case
    attributes:
      label: Expected use case
      description: Why would teams want this collector?
      placeholder: |
        Many teams use Cursor IDE alongside VSCode. A Cursor collector would help them track
        total AI coding usage across all their tools and projects.

  - type: textarea
    id: privacy
    attributes:
      label: Privacy/security considerations
      description: |
        What are the privacy or security implications?
        Can the tool be instrumented without accessing sensitive data?
      placeholder: |
        Cursor exposes a Language Model API similar to VSCode.
        We should be able to hook into token counting without accessing prompts or code.
        Potential risk: need to ensure no editor content is captured in logs.

  - type: textarea
    id: extra
    attributes:
      label: Additional context
      description: Links, documentation, or other relevant info?
      placeholder: |
        - Tool documentation: [link]
        - API or plugin reference: [link]
        - Similar tool already supported: VSCode extension
        - Team interest: [e.g., "X teams asked for this"]
