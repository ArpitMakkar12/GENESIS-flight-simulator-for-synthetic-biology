"""Validation: does GENESIS agree with published experiments?

Two checks, each a script you run inside the backend container:

    python -m validation.essentiality   # which single-gene knockouts kill the cell
    python -m validation.growth_rates   # how fast wild-type cells grow on each carbon source

Both compare GENESIS against PRECISE-1K (Palsson lab, the same group that
built iML1515), pinned to one commit so the numbers are reproducible.
Results are written to validation/results/. See validation/README.md.
"""