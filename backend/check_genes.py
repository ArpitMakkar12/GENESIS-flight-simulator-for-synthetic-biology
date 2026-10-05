"""Fold change of chosen genes under one condition, straight from the predictor.

Usage: python check_genes.py <carbon_source> <oxygen> <locus_tag> [<locus_tag> ...]
"""
import asyncio
import sys

from app.api.simulate import get_runner
from contracts.interfaces import PredictionInput

carbon, oxygen, *genes = sys.argv[1:]
r = get_runner()
env = dict(temperature=37.0, ph=7.0, carbon_source=carbon, nitrogen_source="ammonium")
tf = asyncio.run(r.tf_resolver.resolve(oxygen_level=oxygen, **env))
act = {name: s.is_active for name, s in tf.items()}

out = r._get_predictor().predict(PredictionInput(
    gene_ids=genes, gene_sequences=[""] * len(genes),
    tf_activation=act, oxygen=oxygen, **env,
))
for g in out.results:
    print(f"{g.gene_id}  fold {g.relative_expression:>7}  ref {g.reference_expression_tpm} TPM")