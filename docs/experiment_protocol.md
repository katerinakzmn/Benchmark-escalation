# Experiment Protocol: Real-LLM Evaluation of Escalation Policies

## 1. Research question

Which escalation policy provides the best cost–quality trade-off for
function- and module-level Python bug-fixing tasks when using real LLMs
with two capability tiers?

## 2. Scope

This study evaluates escalation decisions in a controlled benchmark
environment. It does not claim to measure all software-engineering tasks
or the general coding ability of a particular model.

The benchmark dataset contains original or derived-and-validated Python
bug-fixing tasks. Each task has buggy code, a task description, unit tests,
a validated reference solution, and metadata from a predefined taxonomy.

## 3. Model tiers

- Weak tier: OpenAI GPT-5 Mini
- Strong tier: OpenAI GPT-5
- Human tier: a simulated reliable fallback, reported separately and not
  interpreted as real human-performance evidence.

The exact model identifiers, API date, and pricing snapshot are stored in
the experiment manifest.

## 4. Policies

Primary policies:
- FixedWeak
- FixedStrong
- RetryThenEscalate
- ConfidenceThreshold
- ProgressHeuristic
- HumanFallback

Reference policies:
- Random
- Oracle, only for mock-based validation and not as a real-LLM upper bound.

## 5. Controlled conditions

All policies use:
- the same task description and initial buggy code;
- the same system prompt and test-feedback format;
- the same maximum number of attempts;
- the same maximum output-token limit;
- the same timeout and API-error handling rules;
- temperature set to 0, where supported.

No reference solution or hidden test content is included in an LLM prompt.

## 6. Dataset construction

Tasks are selected or generated according to a predefined taxonomy covering:
- defect type;
- task domain;
- difficulty;
- code scope;
- reasoning requirement;
- feedback type;
- context size.

The dataset is stratified across these dimensions. It does not claim
exhaustive coverage of all software-engineering problems.

Every task must satisfy:
1. The buggy implementation fails at least one test.
2. The reference implementation passes all tests.
3. Required task metadata is present.
4. The task has no duplicate identifier.

## 7. Primary metrics

- Solve rate
- Average and median actual API cost in USD
- Average input and output tokens
- Average number of attempts
- Strong-escalation rate
- Human-fallback rate
- Wall-clock latency
- Failure-type distribution

## 8. Definition of preferred policy

The preferred policy is the policy with the lowest mean actual API cost
among policies whose solve rate is within 2 percentage points of the
highest observed solve rate.

If no policy satisfies this criterion robustly, results will be reported
as an observed trade-off rather than a single winner.

## 9. Repetitions and uncertainty

Each task-policy combination is executed three times. Results are reported
with the number of episodes and 95% bootstrap confidence intervals for
solve rate and mean cost.

## 10. Budget and stopping rules

- A maximum total API budget is fixed before the main experiment.
- Each episode has a maximum number of model attempts.
- Each episode has a maximum USD cost.
- A failed API request is logged as an API error and is not silently retried
  beyond the specified retry policy.

## 11. Reproducibility

Each run saves:
- git commit hash;
- timestamp;
- task dataset version;
- prompt version;
- model identifiers;
- pricing snapshot;
- random seed;
- full per-step token usage and cost;
- per-task outcomes and aggregate metrics.