name: Feature request
description: Suggest an improvement for O11yIA BR
labels: ["enhancement"]
assignees: []

body:
  - type: markdown
    attributes:
      value: |
        Thank you for suggesting a feature! Please describe the problem and your proposed solution.

  - type: textarea
    id: problem
    attributes:
      label: Problem
      description: What problem does this feature solve?
      placeholder: |
        Example: Currently, there's no way to export a team's usage report for audits or compliance reviews.
    validations:
      required: true

  - type: textarea
    id: solution
    attributes:
      label: Proposed solution
      description: How would you solve this?
      placeholder: |
        Add a "Export" button on the Team view that generates a CSV or PDF report of:
        - User-level token usage
        - Model distribution
        - Cost breakdown
        - Date range (configurable)
    validations:
      required: true

  - type: textarea
    id: use_case
    attributes:
      label: Use case
      description: Who would benefit and how?
      placeholder: |
        Compliance officers and engineering managers need to audit AI tool usage for their organizations.
        A downloadable report would help them present this data to stakeholders without needing direct dashboard access.

  - type: textarea
    id: metrics
    attributes:
      label: Metrics involved
      description: What data/metrics would this feature use or expose?
      placeholder: |
        - User ID
        - Model name
        - Input/output token counts
        - Calculated cost
        - Date range

  - type: textarea
    id: privacy
    attributes:
      label: Privacy/security considerations
      description: |
        Does this feature collect new data?
        Does it expose sensitive information?
        How should it be secured?
      placeholder: |
        No new data collection. Export includes aggregated metrics only (no source code, prompts, or secrets).
        Should be restricted to authenticated users with admin or audit role.

  - type: textarea
    id: extra
    attributes:
      label: Additional context
      description: Links, examples, mockups, or other relevant info?
      placeholder: |
        - Related issue: #123
        - Similar feature in X tool: [link]
        - Suggested file format: CSV (Excel-compatible)
