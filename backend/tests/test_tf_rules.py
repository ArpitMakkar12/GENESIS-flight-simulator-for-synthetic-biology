"""Master-regulator rules, checked against textbook E. coli behaviour.

Each case is a condition whose answer is well established, e.g. CRP is
off on glucose (catabolite repression) and FNR is on without oxygen.
These rules drive the expression predictions, so a wrong rule shifts
hundreds of genes at once.
"""

import pytest

from app.services.tf_resolver import ENVIRONMENT_RULES


def env(**changes):
    """The reference condition (glucose, aerobic, 37 °C, pH 7), with changes."""
    base = {"temperature": 37.0, "ph": 7.0, "oxygen": "aerobic",
            "carbon_source": "glucose", "nitrogen_source": "ammonium"}
    return {**base, **changes}


def active(tf, **changes):
    return ENVIRONMENT_RULES[tf]["activation"](env(**changes))


def test_reference_condition():
    assert not active("CRP")      # glucose present: catabolite repression
    assert not active("FNR")      # oxygen present
    assert not active("ArcA")
    assert not active("RpoH")     # no heat shock
    assert not active("RpoS")     # no general stress
    assert active("LacI")         # no lactose: lac operon repressed
    assert active("IclR")         # glyoxylate shunt repressed on glucose


@pytest.mark.parametrize("carbon", ["acetate", "glycerol", "succinate", "lactose"])
def test_crp_on_without_glucose(carbon):
    assert active("CRP", carbon_source=carbon)


def test_acetate_opens_the_glyoxylate_shunt():
    assert not active("IclR", carbon_source="acetate")
    assert active("Cra", carbon_source="acetate")    # gluconeogenic substrate


def test_sugar_regulators_release_on_their_sugar():
    assert not active("LacI", carbon_source="lactose")
    assert not active("GalR", carbon_source="galactose")
    assert active("AraC", carbon_source="arabinose")


@pytest.mark.parametrize("oxygen, fnr, arca", [
    ("anaerobic", True, True),
    ("microaerobic", False, True),   # ArcA responds earlier than FNR
    ("aerobic", False, False),
])
def test_oxygen_regulators(oxygen, fnr, arca):
    assert active("FNR", oxygen=oxygen) is fnr
    assert active("ArcA", oxygen=oxygen) is arca


def test_heat_shock_at_42():
    assert active("RpoH", temperature=42.0)
    assert active("RpoS", temperature=42.0)
    assert not active("RpoH", temperature=41.0)


def test_acid_stress():
    assert active("RpoS", ph=4.5)
    assert not active("RpoS", ph=5.5)    # mild acid alone does not trigger it


def test_cold_turns_on_hns():
    assert active("H-NS", temperature=25.0)
    assert not active("H-NS", temperature=37.0)


def test_nitrate():
    assert active("NarL", nitrogen_source="nitrate")
    assert not active("NarL")