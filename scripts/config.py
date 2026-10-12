"""Portable paths; use W99_DATA and W99_OUTPUT to override local defaults."""
from pathlib import Path
import os, json
from zipfile import ZipFile
import numpy as np
import pyreadstat
ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("W99_DATA", str(ROOT / "data/ATP W99.sav"))).expanduser().resolve()
OUT = Path(os.environ.get("W99_OUTPUT", str(ROOT / "results"))).expanduser().resolve()
OUT.mkdir(parents=True, exist_ok=True)
REFERENCE = ROOT / "reference_results"
def read_reference(name):
    """Read a reference JSON from the local expanded folder or public archive."""
    local = REFERENCE / name
    if local.is_file():
        return json.loads(local.read_text(encoding="utf-8"))
    with ZipFile(REFERENCE / "full_precision_reference.zip") as archive:
        return json.loads(archive.read(name).decode("utf-8"))
def load():
    if not SOURCE.is_file():
        raise FileNotFoundError("Obtain ATP Wave 99 SPSS data from Pew, then set W99_DATA to its SAV path.")
    frame, meta = pyreadstat.read_sav(str(SOURCE))
    assert len(frame) == 10260, "Wrong release or changed input row count"
    frame = frame.loc[frame.FORM_W99.eq(1)].replace(99, np.nan)
    assert len(frame) == 5153
    assert np.isfinite(frame.WEIGHT_W99).all() and (frame.WEIGHT_W99 > 0).all()
    return frame, meta
def save(name, value):
    """Write public-safe outputs without case-position diagnostics."""
    def public_value(item):
        if isinstance(item, dict):
            excluded = {
                "influence_row_index",
                "deleted_row_position_zero_based",
                "targeted_case_deletion_details",
                "deletion",
            }
            return {k: public_value(v) for k, v in item.items() if k not in excluded}
        if isinstance(item, list):
            return [public_value(v) for v in item]
        return item

    (OUT / name).write_text(json.dumps(public_value(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

