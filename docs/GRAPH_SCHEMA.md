# Graph Schema

## Node Types

`repository`, `file`, `module`, `function`, `class`, `type`, `test`, `api_endpoint`, `database_table`, `schema`, `config`, `service`, `pipeline`, `resource`, `document`, `section`, `article`, `claim`, `entity`, `domain`, `flow`, `step`, `commit`, `pull_request`, `session`, `decision`.

## Edge Types

`contains`, `imports`, `calls`, `inherits`, `implements`, `tested_by`, `depends_on`, `reads_from`, `writes_to`, `routes_to`, `configures`, `deploys`, `documents`, `belongs_to`, `cites`, `contradicts`, `builds_on`, `affects`, `changed_in`, `discussed_in`, `similar_to`.

## Confidence Tiers

- `extracted`: deterministic parser result.
- `inferred`: deterministic but indirect inference.
- `llm`: model-generated semantic enrichment.
- `ambiguous`: uncertain result needing user review.
- `user`: user-approved or manually added knowledge.

Every node and edge stores its confidence tier. Deterministic facts and model-generated claims must not be mixed without labeling.

