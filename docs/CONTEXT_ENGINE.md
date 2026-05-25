# Context Engine

The context engine follows this flow:

1. Detect task type and query intent.
2. Find seed nodes by exact match and SQLite FTS.
3. Expand the graph around seed nodes.
4. Include docs, configs, tests, and source chunks when relevant.
5. Add user-approved memories and diff snippets when the workflow provides them.
6. Rank by match quality, graph confidence, and graph distance.
7. Pack results into the selected token budget.

Budgets:

- `tiny`: about 700 tokens.
- `normal`: about 4000 tokens.
- `deep`: about 12000 tokens.
- `full`: no strict limit.

Context packs use this structure:

```markdown
# DevGraph Context Pack
## Task
## Summary
## High-confidence facts
## Relevant files
## Relevant symbols
## Graph paths
## Changed code snippets
## Tests
## Project memories
## Docs/configs
## Risks / uncertainty
## Suggested next actions
```
