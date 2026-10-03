# Shield Demo Script

Target length: around 5 minutes. Keep the delivery precise and calm. Show your face and the screen.

## Before Recording

Open the GitHub repository page and a Terminal window in the project folder.

```bash
cd /path/to/PE6201-shield-project
python3 src/run_demo.py
```

Also open:

- `README.md`
- `docs/metrics_summary.md`
- `evals/metrics_summary.csv`

## 0:00-0:30 Opening

Hi, my project is Shield, an AI-assisted harmful content intervention prototype for social media platforms.

The problem is that online harassment is often contextual. A sentence can look harmless alone, but become threatening after repeated unwanted contact or stalking cues. Shield is designed to classify the severity of a comment in context, then turn that label into a product action: allow, prompt the user to reconsider, or escalate to a human moderator.

## 0:30-1:15 Architecture

Show the architecture section in `README.md` or `docs/architecture.md`.

Shield has two layers. First, a severity classifier reads the final comment and optional thread context. It returns a structured output: severity, rationale, and confidence. Second, a deterministic policy table maps the severity label to an action.

This separation is important. The AI handles contextual language judgement, but the product decision remains auditable. If the platform wants to change what happens to a medium-severity case, it can change the policy table without retraining the classifier.

## 1:15-2:25 Demo

Run:

```bash
python3 src/run_demo.py
```

Explain the three examples.

First, normal criticism: "I disagree with your conclusion because the evidence is weak." Shield allows it. That is important because the product should not suppress ordinary disagreement.

Second, direct insult: "You are such an idiot and should shut up." Shield classifies this as medium and triggers a reconsideration prompt. This is a lower-impact intervention before posting.

Third, the context-sensitive case: the final comment is "I will see you again." Alone, this could be harmless. But with the preceding context, where the user has already said "stop messaging me" and the other person says they know where the user goes after class, it becomes more threatening. This is the core reason Shield evaluates comments in context.

## 2:25-3:40 Metrics

Show `docs/metrics_summary.md`.

I evaluate Shield as a product intervention, not only as a classifier. Based on feedback, I report false negatives and false positives together.

On the small prototype eval set, the false positive rate on normal criticism is 0 percent. That means normal criticism was not over-prompted in this set.

However, the false negative rate on high and critical cases is 75 percent for the local fallback. That is a weakness, not something I want to hide. It shows that the deterministic fallback misses implicit threats and should not be treated as the final classifier.

This result supports the final architecture: use a contextual foundation model for severity judgement, then use the deterministic policy table for action selection.

I also include cost per 1,000 comments. The current repo reports it as an estimate below USD 0.10 for short comments with a low-cost hosted model, but in a production run this should be replaced by measured token usage.

## 3:40-4:35 Critique and Responsible Use

The biggest risk is silent failure. If the system classifies a severe harassment case as normal, nothing visibly breaks, but the user is left unprotected. That is why high-risk and uncertain cases should be escalated to human moderators.

The other risk is over-prompting. If Shield interrupts normal criticism too often, users will stop trusting the product. That is why I added the normal-criticism false-positive ceiling.

This prototype is English-only and uses a small eval set. It does not yet fully test multilingual abuse, coded language, demographic bias, or adversarial spelling.

## 4:35-5:00 Closing

The main contribution of Shield is the product design: contextual AI judgement combined with a deterministic, auditable policy layer.

The next step would be to replace the local fallback with a measured foundation-model classifier, run the full 150 hand-relabelled cases, and keep reporting the same pair of metrics: severe false-negative rate and normal-criticism false-positive rate, plus cost per 1,000 comments.
