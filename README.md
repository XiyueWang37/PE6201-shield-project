# Shield: AI-Assisted Harmful Content Intervention

Shield is a prototype for classifying the harassment severity of a social media comment in context. The system returns a severity label, a short rationale, and a deterministic policy action: allow, prompt the user to reconsider, or escalate to a human moderator.

This repository is prepared for the PE6201 End-of-Course Project final submission.

## Persona

Shield is designed for Trust and Safety teams at social media platforms or online community operators. The end user is a person writing or receiving a potentially harmful comment. The product goal is not to automatically punish users, but to intervene earlier and reduce harm while avoiding unnecessary prompts for normal criticism.

## Input

The prototype accepts:

- `comment`: the final comment being assessed.
- `context`: optional preceding thread messages.
- `author_role`: optional metadata used only for display or future policy tuning.

## Output

The prototype returns:

- `severity`: one of `normal`, `low`, `medium`, `high`, or `critical`.
- `rationale`: a short explanation of the classification.
- `policy_action`: one of `allow`, `prompt_reconsider`, or `escalate_to_moderator`.
- `confidence`: a simple confidence label for the prototype.

## Product Architecture

```text
User comment + optional thread context
        |
        v
Contextual severity classifier
        |
        v
Structured output: severity + rationale + confidence
        |
        v
Deterministic policy table
        |
        v
allow / prompt_reconsider / escalate_to_moderator
```

The LLM or classifier is scoped to contextual judgement. The final action is produced by a deterministic policy table so that the product remains auditable and adjustable without retraining the model.

## Repository Structure

```text
src/
  shield_classifier.py   # Severity classifier interface and local fallback
  policy.py              # Deterministic severity-to-action policy table
  run_demo.py            # Command line demo
data/
  README.md              # Data source and relabelling explanation
  relabelled_eval_set.csv # Hand-labelled prototype evaluation set
evals/
  README.md              # Evaluation design and metrics
  eval_cases.csv          # Single-comment eval results
  context_eval_cases.csv  # Context sensitivity eval cases
  metrics_summary.csv     # Metrics target and result summary
docs/
  architecture.md
  metrics_summary.md
  final_report_draft.md
  final_report.pdf
demo/
  demo_script.md
```

## Setup

Use Python 3.10 or later.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The current version can run locally without an API key. If an LLM provider is connected later, add the API key through an environment variable and keep it out of the repository.

## Run Demo

```bash
python src/run_demo.py
```

## Run Evals

The current repository includes a small prototype evaluation set and metric summary. The intended full version is 150 hand-relabelled items; this submission keeps the smaller set inspectable and transparent:

- False negative rate on high and critical harassment.
- False positive or over-prompt rate on normal criticism.
- Cost per 1,000 comments.
- Context sensitivity: whether the label changes correctly when thread context is included.

## Metrics Targeted

| Metric | Target | Why it matters |
| --- | ---: | --- |
| False negative rate on high/critical cases | below 10% | Missed severe harassment creates direct user harm. |
| False positive rate on normal criticism | below 15-20% | Over-prompting normal users damages trust and product adoption. |
| Cost per 1,000 comments | report measured or estimated value | Platform deployment depends on scale economics. |
| Context movement accuracy | report separately | Tests whether Shield uses context instead of keyword matching. |

## Limitations

This is a course prototype, not a production moderation system. It does not make enforcement decisions by itself. High-risk, uncertain, and potentially severe cases should be reviewed by a human moderator. The evaluation set is intentionally small and hand-relabelled so that the reasoning is inspectable, but a production system would need larger multilingual, demographic, and adversarial testing.

## Academic Integrity

All reported measurements should come from runs performed by the author. Do not commit API keys, private user data, or generated metric values that were not actually measured.
