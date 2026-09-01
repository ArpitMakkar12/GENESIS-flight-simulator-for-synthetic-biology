from dataclasses import dataclass


@dataclass
class ReactionBound:
    reaction_id: str
    lower_bound: float
    upper_bound: float
    source: str  # 'expression', 'kinetics', 'transport', 'default'


class BoundCompiler:
    """Converts AI expression predictions + BRENDA kinetics into FBA reaction bounds.

    This is the bridge between Pillar 2 (AI) and Pillar 3 (FBA).
    Formula: bound = expression_level * kcat * activity_factor(T, pH) * saturation
    """

    def compile(
        self,
        expression_results: list[dict],
        temperature: float,
        ph: float,
    ) -> list[ReactionBound]:
        """Compile FBA bounds from expression predictions and enzyme kinetics."""
        # TODO: Implement using BRENDA kinetics data
        raise NotImplementedError

    def get_activity_factor(self, ec_number: str, temperature: float, ph: float) -> float:
        """Get enzyme activity scaling factor at given T and pH from BRENDA data."""
        # TODO: Look up BRENDA activity curves
        return 1.0  # Default: full activity
