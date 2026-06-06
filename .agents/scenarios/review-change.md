# Scenario: Review Change

Default to a code-review mindset:

- prioritize correctness issues
- then regression risks
- then missing tests or validation gaps
- then maintainability concerns

- use current repo truth as the baseline, not generic preference alone
- use the relevant feature map and governance docs; if the task is about AI collaboration itself, also use `.agents/project/agent-strategy.md`
- classify findings using `.agents/rules/review-closure.md`
- call out open assumptions explicitly
- stop when the closure standard is met; do not keep editing for polish alone
- keep summaries brief after the findings
