# Architecture

Shield separates model judgement from product action.

```text
Comment and optional context
        |
        v
Severity classifier
        |
        v
Structured output
severity + rationale + confidence
        |
        v
Deterministic policy table
        |
        v
allow / prompt_reconsider / escalate_to_moderator
```

## Why This Design

The classifier handles the language understanding problem: whether a comment is harmless criticism, an insult, harassment, or a severe threat in context. The deterministic policy table handles the product decision. This division makes the system easier to audit because a platform can change the action attached to each severity level without changing the model.

## Policy Table

| Severity | Policy action | Reason |
| --- | --- | --- |
| normal | allow | No intervention needed. |
| low | allow | Mild negativity should not over-trigger prompts. |
| medium | prompt_reconsider | The user gets a chance to revise before posting. |
| high | escalate_to_moderator | Human review is needed. |
| critical | escalate_to_moderator | Severe risk should not be handled automatically. |

## Human-in-the-Loop Boundary

Shield should not independently suspend users, remove accounts, or make high-impact enforcement decisions. It should route severe or uncertain cases to human moderation.
