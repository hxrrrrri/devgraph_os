"""Review risk scoring."""

from __future__ import annotations

from devgraph.core.schema import Node

SECURITY_HINTS = ("auth", "token", "secret", "password", "permission", "crypto")
CONFIG_HINTS = (".env", "docker", "terraform", "kubernetes", "workflow", "settings", ".github")
DB_HINTS = ("schema", "migration", "sql", "database", "prisma", "alembic")


def score_risk(
    changed_files: list[str],
    changed_nodes: list[Node],
    impacted_nodes: list[Node],
    changed_line_count: int = 0,
    affected_tests: list[str] | None = None,
    recent_churn: int = 0,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    if len(changed_files) > 5:
        score += 15
        reasons.append("Change spans more than five files.")
    elif len(changed_files) > 1:
        score += 5
        reasons.append("Change spans multiple files.")
    if len(changed_nodes) > 20:
        score += 15
        reasons.append("Large number of changed graph nodes.")
    elif len(changed_nodes) > 5:
        score += 8
        reasons.append("Multiple changed symbols detected.")
    if len(impacted_nodes) > 20:
        score += 20
        reasons.append("Broad blast radius through import/call dependents.")
    elif len(impacted_nodes) > 5:
        score += 10
        reasons.append("Several dependent graph nodes may be impacted.")
    public_nodes = [node for node in changed_nodes if node.type in {"api_endpoint", "service", "schema"}]
    if public_nodes:
        score += 15
        reasons.append("Public API, service, or schema nodes changed.")
    exported = [
        node
        for node in changed_nodes
        if node.type in {"class", "function", "type"} and not node.name.startswith("_")
    ]
    if exported:
        score += min(12, len(exported) * 2)
        reasons.append("Exported or public-looking symbols changed.")
    if any(any(hint in path.lower() for hint in SECURITY_HINTS) for path in changed_files):
        score += 20
        reasons.append("Security-sensitive file path changed.")
    if any(any(hint in path.lower() for hint in CONFIG_HINTS) for path in changed_files):
        score += 10
        reasons.append("Configuration or infrastructure file changed.")
    if any(any(hint in path.lower() for hint in DB_HINTS) for path in changed_files):
        score += 15
        reasons.append("Database or schema-related file changed.")
    db_nodes = [node for node in changed_nodes if node.type in {"database_table", "schema"}]
    if db_nodes:
        score += 15
        reasons.append("Database table or schema graph nodes changed.")
    if changed_line_count > 250:
        score += 15
        reasons.append("Large diff with more than 250 changed lines.")
    elif changed_line_count > 80:
        score += 8
        reasons.append("Moderate-size diff with more than 80 changed lines.")
    ambiguous = [node for node in [*changed_nodes, *impacted_nodes] if node.confidence_tier == "ambiguous"]
    if ambiguous:
        score += 8
        reasons.append("Some impacted dependencies are ambiguous parser facts.")
    if recent_churn > 5:
        score += 8
        reasons.append("Changed area has recent git churn.")
    if not affected_tests and not any(node.type == "test" for node in changed_nodes):
        score += 10
        reasons.append("No tests changed with this diff.")
    return min(100, score), reasons or ["Low graph-derived risk."]


def risk_level(score: int) -> str:
    if score >= 90:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 35:
        return "medium"
    return "low"
