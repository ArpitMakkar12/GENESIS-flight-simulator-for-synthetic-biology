"""Environment conditioner — turns growth conditions into numbers.

Owned by: Keshav

WHAT THIS IS
------------
The model cannot read the words "42 degrees" or "anaerobic". This module
converts the five environment settings into numeric features, and — more
importantly — defines which master regulators are switched on under
REFERENCE conditions.

WHY THE REFERENCE STATE MATTERS
-------------------------------
Our contract says relative_expression is a fold-change versus reference
(37C, pH 7.0, aerobic, glucose, ammonium). A fold-change is a
comparison, so we need to know what the reference looked like.

Example: LacI is the repressor that keeps the lactose genes switched off.

    reference (glucose)  -> LacI ACTIVE   -> lacZ off, ~3 TPM
    query     (lactose)  -> LacI INACTIVE -> lacZ on,  ~900 TPM

Same DNA. 300x difference. That difference comes entirely from knowing
LacI changed state — not from the sequence.

Only the master regulators below respond to environment. The other ~350
transcription factors in our database have no condition rules, so they
are treated as constant and cancel out of the comparison.
"""

from __future__ import annotations

from dataclasses import dataclass

# Reference growth condition, as defined in contracts/interfaces.py
REF_TEMPERATURE = 37.0
REF_PH = 7.0
REF_OXYGEN = "aerobic"
REF_CARBON = "glucose"
REF_NITROGEN = "ammonium"

# Which master regulators are ON at reference conditions.
#
# These mirror the rules in backend/app/services/tf_resolver.py. We
# duplicate the reference values here rather than importing Arpit's
# async resolver, to keep the AI layer free of backend dependencies.
# If his rules change, this dict needs the same change.
REFERENCE_TF_STATE: dict[str, bool] = {
    "CRP":   False,   # glucose present -> cAMP low -> CRP inactive
    "LacI":  True,    # no lactose -> repressor bound, lac operon off
    "FNR":   False,   # aerobic -> oxygen-sensing regulator inactive
    "ArcA":  False,   # aerobic
    "OxyR":  False,   # no oxidative stress
    "RpoH":  False,   # 37C -> no heat shock response
    "RpoS":  False,   # no general stress
    "H-NS":  False,   # not cold
    "Fur":   True,    # iron sufficient -> repressing iron uptake
    "PhoB":  False,   # phosphate sufficient
    "NarL":  False,   # no nitrate present
    "NtrC":  False,   # ammonium is a good nitrogen source
}

OXYGEN_LEVELS = ("aerobic", "microaerobic", "anaerobic")
CARBON_SOURCES = ("glucose", "glycerol", "lactose", "acetate", "succinate")
NITROGEN_SOURCES = ("ammonium", "nitrate", "glutamine", "urea")


@dataclass(frozen=True)
class Environment:
    """One set of growth conditions."""
    temperature: float = REF_TEMPERATURE
    ph: float = REF_PH
    oxygen: str = REF_OXYGEN
    carbon_source: str = REF_CARBON
    nitrogen_source: str = REF_NITROGEN

    @property
    def is_reference(self) -> bool:
        return (
            abs(self.temperature - REF_TEMPERATURE) < 0.5
            and abs(self.ph - REF_PH) < 0.1
            and self.oxygen == REF_OXYGEN
            and self.carbon_source == REF_CARBON
            and self.nitrogen_source == REF_NITROGEN
        )

    def describe(self) -> str:
        return (f"{self.temperature:.0f}C pH{self.ph:.1f} {self.oxygen} "
                f"{self.carbon_source}/{self.nitrogen_source}")


def _one_hot(value: str, options: tuple[str, ...]) -> list[float]:
    v = (value or "").lower().strip()
    return [1.0 if v == o else 0.0 for o in options]


def encode(env: Environment) -> list[float]:
    """Turn an Environment into a fixed-length numeric feature vector.

    Temperature and pH are given twice: once scaled, once as distance
    from the optimum. The distance matters because stress is symmetric —
    30C and 44C are both "off optimum", even though one is above and
    one below.
    """
    feats: list[float] = [
        (env.temperature - 37.0) / 10.0,          # signed, scaled
        abs(env.temperature - 37.0) / 10.0,       # distance from optimum
        (env.ph - 7.0) / 2.0,
        abs(env.ph - 7.0) / 2.0,
        1.0 if env.temperature >= 42.0 else 0.0,  # heat shock threshold
        1.0 if env.ph <= 5.5 else 0.0,            # acid stress threshold
        1.0 if env.ph >= 8.5 else 0.0,            # alkaline stress
    ]
    feats += _one_hot(env.oxygen, OXYGEN_LEVELS)
    feats += _one_hot(env.carbon_source, CARBON_SOURCES)
    feats += _one_hot(env.nitrogen_source, NITROGEN_SOURCES)
    return feats


FEATURE_NAMES = (
    ["temp_signed", "temp_distance", "ph_signed", "ph_distance",
     "heat_shock", "acid_stress", "alkaline_stress"]
    + [f"o2_{o}" for o in OXYGEN_LEVELS]
    + [f"c_{c}" for c in CARBON_SOURCES]
    + [f"n_{n}" for n in NITROGEN_SOURCES]
)


def tf_state_changes(
    current: dict[str, bool],
    reference: dict[str, bool] | None = None,
) -> dict[str, str]:
    """Which master regulators changed versus reference conditions.

    Returns {tf_name: "on" | "off"} for regulators whose state flipped.
    "on" means it became active; "off" means it became inactive.

    Regulators not in the reference table, or whose state did not
    change, are left out — they cannot contribute to a fold-change.
    """
    ref = reference or REFERENCE_TF_STATE
    changes: dict[str, str] = {}

    for tf, ref_active in ref.items():
        now = current.get(tf)
        if now is None or now == ref_active:
            continue
        changes[tf] = "on" if now else "off"

    return changes


if __name__ == "__main__":
    presets = {
        "reference":    Environment(),
        "anaerobic":    Environment(oxygen="anaerobic"),
        "heat shock":   Environment(temperature=42.0),
        "acid stress":  Environment(ph=5.5, carbon_source="glycerol"),
        "glycerol":     Environment(carbon_source="glycerol"),
    }

    print("=" * 66)
    print("ENVIRONMENT CONDITIONER")
    print("=" * 66)
    print(f"\n{len(FEATURE_NAMES)} features per condition\n")

    for name, env in presets.items():
        vec = encode(env)
        active = [FEATURE_NAMES[i] for i, v in enumerate(vec) if v != 0]
        print(f"  {name:12} {env.describe()}")
        print(f"               nonzero: {', '.join(active[:6])}")
        print(f"               is_reference={env.is_reference}")
        print()

    print("-" * 66)
    print("TF state changes for a heat shock condition")
    print("-" * 66)
    heat = dict(REFERENCE_TF_STATE)
    heat["RpoH"] = True      # heat shock sigma factor fires above 42C
    heat["RpoS"] = True      # general stress response
    print(f"  {tf_state_changes(heat)}")
    print("\n  Those two flips are what make a 42C simulation differ")
    print("  from a 37C one. The DNA is identical.")