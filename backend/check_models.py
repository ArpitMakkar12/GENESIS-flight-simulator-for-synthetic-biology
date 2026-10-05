"""Which of the three model-loading steps is failing for a novel sequence."""
from app.api.simulate import get_runner

p = get_runner()._get_predictor()
print("predictor class: ", type(p).__name__)
print("expression_model:", p.registry.expression_model())
print("hyenadna:        ", p.registry.hyenadna())

seq = "ATGCGTACG" + "TAGC" * 99
print("sequence length: ", len(seq))
print("predict_novel:   ", p._predict_novel(seq[:300], seq))
print("last error:      ", getattr(p, "_last_model_error", None))