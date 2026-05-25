"""Review risk scoring."""

from __future__ import annotations

from devgraph.core.schema import Node

SECURITY_HINTS = ("auth", "token", "secret", "password", "permission", "crypto")
CONFIG_HINTS = (".env", "docker", "terraform", "kubernetes", "workflow", "settings")


def score_risk(changed_files: list[str], changed_nodes: list[Node], impacted_nodes: list[Node]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    if len(changed_files) > 5:
        score += 15
        reasons.append("Change spans more than five files.")
    if len(changed_nodes) > 20:
        score += 15
        reasons.append("Large number of changed graph nodes.")
    if len(impacted_nodes) > 20:
        score += 20
        reasons.append("Broad blast radius through import/call dependents.")
    public_nodes = [node for node in changed_nodes if node.type in {"api_endpoint", "service", "schema"}]
    if public_nodes:
        score += 15
        reasons.append("Public API, service, or schema nodes changed.")
    if any(any(hint in path.lower() for hint in SECURITY_HINTS) for path in changed_files):
        score += 20
        reasons.append("Security-sensitive file path changed.")
    if any(any(hint in path.lower() for hint in CONFIG_HINTS) for path in changed_files):
        score += 10
        reasons.append("Configuration or infrastructure file changed.")
    if not any(node.type == "test" for node in changed_nodes):
        score += 10
        reasons.append("No tests changed with this diff.")
    return min(100, score), reasons or ["Low graph-derived risk."]


def risk_level(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 35:
        return "medium"
    return "low"

