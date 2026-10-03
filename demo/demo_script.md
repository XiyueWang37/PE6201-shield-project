# Demo Script

Target length: 5 minutes.

## 0:00-0:30 Problem

Shield addresses online harassment before or immediately after posting. The goal is not automatic punishment. The goal is an earlier intervention that protects users without over-prompting normal criticism.

## 0:30-1:15 Architecture

Show the architecture:

```text
comment/context -> severity classifier -> policy table -> action
```

Explain that the model classifies severity, but the deterministic policy table chooses the product action.

## 1:15-2:45 Demo Examples

Run:

```bash
python src/run_demo.py
```

Show three cases:

- Normal criticism -> allow.
- Direct insult -> prompt reconsider or higher.
- Context-sensitive case -> label changes when context is included.

## 2:45-3:45 Metrics

Show the metrics summary:

- False negative rate on high/critical cases.
- False positive rate on normal criticism.
- Cost per 1,000 comments.
- Context movement accuracy.

## 3:45-4:45 Critique

State the limitations:

- Small relabelled dataset.
- Ambiguous speech and sarcasm remain hard.
- Cultural and linguistic variation need more testing.
- Severe decisions must remain human-reviewed.

## 4:45-5:00 Closing

Shield is useful because it combines contextual AI judgement with an auditable deterministic policy layer.
