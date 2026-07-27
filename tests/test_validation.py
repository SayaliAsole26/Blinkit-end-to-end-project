"""Validation agreement rate calculation."""

from models.friction import ClusterAnalysis, CrossShoppingFrictionAnalysis
from pipeline.validate import field_agreement, simple_kappa


def _analysis(
    cluster_id: str,
    barrier: str = "AWARENESS_DEFICIT",
    funnel: str = "DISCOVERY",
    entity: str | None = None,
) -> ClusterAnalysis:
    return ClusterAnalysis(
        cluster_id=cluster_id,
        friction=CrossShoppingFrictionAnalysis(
            user_cognitive_barrier=barrier,  # type: ignore[arg-type]
            funnel_leak_stage=funnel,  # type: ignore[arg-type]
            competitor_entity=entity,
            competitor_advantage="ASSORTMENT" if entity else None,
            price_sensitivity_detected=False,
        ),
        theme_label="Test theme",
        related_RQs=["RQ2"],
    )


def test_field_agreement_all_match() -> None:
    a = _analysis("c1")
    b = _analysis("c1")
    detail = field_agreement(a, b)
    assert detail.overall_match is True
    assert detail.barrier_match is True


def test_field_agreement_barrier_mismatch() -> None:
    a = _analysis("c1", barrier="AWARENESS_DEFICIT")
    b = _analysis("c1", barrier="ASSORTMENT_GAP")
    detail = field_agreement(a, b)
    assert detail.barrier_match is False
    assert detail.overall_match is False


def test_simple_kappa_perfect() -> None:
    assert simple_kappa([True, True, True]) == 1.0
