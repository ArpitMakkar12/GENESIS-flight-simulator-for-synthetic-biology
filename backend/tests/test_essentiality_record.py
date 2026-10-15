"""The per-gene track record the knockout card shows.

Reads validation/results/essentiality_genes.csv, which is committed.
"""

from app.services import essentiality_record
from app.services.essentiality_record import record_for


def test_record_file_is_committed():
    assert essentiality_record.RECORD_PATH.exists(), (
        "Run `python -m validation.essentiality` and commit validation/results/"
    )


def test_gene_the_model_gets_wrong():
    # eno: lab says essential in LB; the model reroutes through serine
    rec = record_for("b2779")
    assert rec == {"lab_essential": True, "model_essential": False, "outcome": "FN", "agrees": False}


def test_gene_the_model_gets_right():
    rec = record_for("b0720")   # gltA: not essential in LB, model agrees
    assert rec["lab_essential"] is False
    assert rec["agrees"] is True


def test_unknown_gene_has_no_record():
    assert record_for("b9999") is None


def test_missing_file_means_no_records(monkeypatch, tmp_path):
    monkeypatch.setattr(essentiality_record, "RECORD_PATH", tmp_path / "missing.csv")
    essentiality_record._load.cache_clear()
    try:
        assert record_for("b2779") is None
    finally:
        essentiality_record._load.cache_clear()   # the next test reads the real file again