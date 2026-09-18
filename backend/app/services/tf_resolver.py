"""Resolves which transcription factors are active under given conditions.

Uses the expanded PRECISE-1K TRN data (10,783 regulations, 371 TFs)
plus the seeded active_conditions JSONB to determine TF activation
states from environmental parameters.

Owned by: Arpit
"""

from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings


@dataclass
class TFActivationState:
    tf_name: str
    is_active: bool
    confidence: float
    reason: str


# Default TF states under reference conditions (37°C, pH 7, aerobic, glucose)
# These are the well-characterized master regulators
ENVIRONMENT_RULES: dict[str, dict] = {
    # Carbon catabolite repression
    "CRP": {
        "rule": "active when glucose is absent",
        "activation": lambda env: env["carbon_source"] != "glucose",
    },
    "LacI": {
        "rule": "active (represses) when lactose is absent",
        "activation": lambda env: env["carbon_source"] != "lactose",
    },
    "GalR": {
        "rule": "active (represses) when galactose is absent",
        "activation": lambda env: env["carbon_source"] != "galactose",
    },
    "AraC": {
        "rule": "activator mode when arabinose present",
        "activation": lambda env: env["carbon_source"] == "arabinose",
    },
    # Oxygen response
    "FNR": {
        "rule": "active under anaerobic conditions",
        "activation": lambda env: env["oxygen"] == "anaerobic",
    },
    "ArcA": {
        "rule": "active under anaerobic/microaerobic conditions",
        "activation": lambda env: env["oxygen"] in ("anaerobic", "microaerobic"),
    },
    # Nitrogen regulation
    "NtrC": {
        "rule": "active under nitrogen limitation",
        "activation": lambda env: env["nitrogen_source"] == "limiting",
    },
    "NarL": {
        "rule": "active when nitrate is the nitrogen source",
        "activation": lambda env: env["nitrogen_source"] == "nitrate",
    },
    # Stress responses
    "OxyR": {
        "rule": "active under oxidative stress",
        "activation": lambda env: env.get("stress") == "oxidative",
    },
    "SoxR": {
        "rule": "active under superoxide stress",
        "activation": lambda env: env.get("stress") == "superoxide",
    },
    "RpoH": {
        "rule": "active under heat shock (>42°C)",
        "activation": lambda env: env["temperature"] > 42.0,
    },
    "RpoS": {
        "rule": "active in stationary phase or under general stress",
        "activation": lambda env: env.get("growth_phase") == "stationary"
                                  or env["temperature"] >= 42.0
                                  or env["ph"] < 5.0 or env["ph"] > 9.0,
    },
    # Phosphate regulation
    "PhoB": {
        "rule": "active under phosphate limitation",
        "activation": lambda env: env.get("phosphate") == "limiting",
    },
    # Iron regulation
    "Fur": {
        "rule": "active (represses) when iron is sufficient",
        "activation": lambda env: env.get("iron") != "limiting",
    },
    # DNA damage
    "LexA": {
        "rule": "active (represses) when no DNA damage",
        "activation": lambda env: env.get("stress") != "dna_damage",
    },
    # Growth phase
    "Fis": {
        "rule": "active during exponential growth",
        "activation": lambda env: env.get("growth_phase", "exponential") == "exponential",
    },
    "IHF": {
        "rule": "active during stationary phase",
        "activation": lambda env: env.get("growth_phase") == "stationary",
    },
    "H-NS": {
        "rule": "active at low temperature",
        "activation": lambda env: env["temperature"] < 30.0,
    },
}


class TFResolver:
    """Resolves which transcription factors are active under given conditions.

    Uses a combination of:
    1. Hard-coded rules for well-characterized TFs
    2. active_conditions JSONB from the database
    3. Default assumption: TF is active (conservative)
    """

    def __init__(self):
        self._db_conditions: dict[str, dict] = {}
        self._loaded = False

    def _load_db_conditions(self) -> None:
        """Load active_conditions from transcription_factors table."""
        if self._loaded:
            return

        engine = create_engine(settings.DATABASE_URL_SYNC)
        with Session(engine) as session:
            rows = session.execute(
                text("SELECT name, active_conditions FROM transcription_factors WHERE active_conditions IS NOT NULL")
            ).fetchall()
            for name, conditions in rows:
                if conditions:
                    self._db_conditions[name] = conditions
        self._loaded = True

    async def resolve(
        self,
        temperature: float,
        ph: float,
        oxygen_level: str,
        carbon_source: str,
        nitrogen_source: str,
    ) -> dict[str, TFActivationState]:
        """Determine active TFs under the given environmental conditions.

        Returns a dict of {tf_name: TFActivationState} for all 371 TFs.
        """
        self._load_db_conditions()

        env = {
            "temperature": temperature,
            "ph": ph,
            "oxygen": oxygen_level,
            "carbon_source": carbon_source,
            "nitrogen_source": nitrogen_source,
        }

        # Get all TF names from database
        engine = create_engine(settings.DATABASE_URL_SYNC)
        with Session(engine) as session:
            all_tfs = session.execute(
                text("SELECT name FROM transcription_factors")
            ).fetchall()

        results: dict[str, TFActivationState] = {}

        for (tf_name,) in all_tfs:
            # Priority 1: Hard-coded rules (well-characterized TFs)
            if tf_name in ENVIRONMENT_RULES:
                rule = ENVIRONMENT_RULES[tf_name]
                is_active = rule["activation"](env)
                results[tf_name] = TFActivationState(
                    tf_name=tf_name,
                    is_active=is_active,
                    confidence=0.9,
                    reason=rule["rule"],
                )
                continue

            # Priority 2: DB active_conditions JSONB matching
            if tf_name in self._db_conditions:
                conditions = self._db_conditions[tf_name]
                is_active = self._match_conditions(conditions, env)
                results[tf_name] = TFActivationState(
                    tf_name=tf_name,
                    is_active=is_active,
                    confidence=0.6,
                    reason=f"matched from active_conditions: {conditions}",
                )
                continue

            # Default: assume active (conservative — lets genes be regulated)
            results[tf_name] = TFActivationState(
                tf_name=tf_name,
                is_active=True,
                confidence=0.3,
                reason="default: assumed active (no environmental rule)",
            )

        return results

    @staticmethod
    def _match_conditions(conditions: dict, env: dict) -> bool:
        """Match active_conditions JSONB against environment."""
        for key, values in conditions.items():
            if key == "oxygen" and env["oxygen"] in values:
                return True
            if key == "carbon_source" and env["carbon_source"] in values:
                return True
            if key == "nitrogen_source" and env["nitrogen_source"] in values:
                return True
            if key == "temperature":
                if env["temperature"] in values:
                    return True
        return False
