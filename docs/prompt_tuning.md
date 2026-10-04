# Prompt Tuning Log

## Split

Fresh candidate rows were split once with fixed seed `6201`, stratified by `shield_label`. The saved split file is `data/split_ids.csv`.

## Prompt v1 Dev Observation

Before changing the prompt, only dev-set failures were inspected. The main action-level failures were:

- Direct insults such as "Shut up...", "stupid point", and "You are an idiot" were often predicted as `low`, which maps to `allow`; the gold label is `medium`, which maps to `prompt_reconsider`.
- Implicit threats and location/routine intimidation such as "You will regret...", "I found your workplace", and "I have been watching... your route" were often predicted below `high`, which avoids moderator escalation.
- Some `critical` examples were predicted as `high`; this is a severity error but not an action error because both escalate.

## Prompt v2 Hypothesis

A single calibration paragraph should improve action accuracy and reduce high/critical false negatives on held-out fresh data by making the decision boundary more explicit:

- targeted direct insults should be at least `medium`, not `low`;
- location, schedule, route, workplace, watching, or regret cues directed at a person should be at least `high`;
- private-address/private-message exposure or explicit offline danger should be `critical` when severe.

Expected trade-off: this may increase severity on borderline hostile comments, so the held-out normal-criticism FPR must be checked rather than assumed.

## Prompt v2 Result

The prompt was changed exactly once. Prompt v2 was then evaluated on both dev and held-out test rows using the saved split ids.

| Prompt | Split | n | Action accuracy | Severity accuracy | High/critical FNR | Normal FPR | Abstention |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| v1 | dev | 44 | 77.3% | 59.1% | 29.4% | 0.0% | 0.0% |
| v1 | test | 46 | 78.3% | 63.0% | 22.2% | 0.0% | 0.0% |
| v2 | dev | 44 | 90.9% | 75.0% | 5.9% | 0.0% | 0.0% |
| v2 | test | 46 | 87.0% | 73.9% | 5.6% | 0.0% | 0.0% |

Held-out judgement: v2 matched the hypothesis. It reduced high/critical misses on the test split without increasing the normal-criticism false-positive rate. The submitted prompt is therefore `prompt_v2`.
