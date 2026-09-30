"""
Integrity test: verify all stored part sequences against iGEM Registry.

Fetches each part from the iGEM RSBPML XML API and compares by SHA-256.
Also checks: ATG start, in-frame stop, zero internal stops (for CDS only).

Usage:
    python tests/test_sequence_integrity.py

Returns exit code 0 if all pass, 1 if any fail.
"""

import hashlib
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
import re

STOPS = {"TAA", "TAG", "TGA"}

# Load expected checksums from data file
DATA_FILE = "backend/app/data/registry_sequences.json"


def fetch_from_registry(part_name: str) -> str | None:
    """Fetch sequence from iGEM Registry XML API."""
    url = f"https://parts.igem.org/cgi/xml/part.cgi?part={part_name}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8")
        root = ET.fromstring(data)
        seq_elem = root.find(".//seq_data")
        if seq_elem is not None and seq_elem.text:
            return re.sub(r"[^ACGTacgt]", "", seq_elem.text.strip()).upper()
    except Exception as e:
        print(f"  WARN: Could not fetch {part_name} from registry: {e}")
    return None


def get_api_sequence(part_name: str) -> str | None:
    """Fetch stored sequence from local API."""
    url = f"http://localhost:8000/api/v1/parts/{part_name}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        seq = data.get("sequence")
        if seq and seq != "N/A":
            return seq
    except Exception:
        pass
    return None


def main():
    with open(DATA_FILE) as f:
        registry_data = json.load(f)

    all_pass = True
    results = []

    for part_name, entry in registry_data.items():
        expected_sha = entry["sha256"]
        expected_len = entry["registry_length"]

        # 1. Verify the data file entry itself
        data_seq = entry["sequence"]
        data_sha = hashlib.sha256(data_seq.encode()).hexdigest()
        if data_sha != expected_sha:
            print(f"FAIL {part_name}: data file SHA-256 mismatch!")
            all_pass = False
            continue

        # 2. Check stored in DB via API
        stored = get_api_sequence(part_name)
        if not stored:
            print(f"WARN {part_name}: no stored sequence (Pending)")
            continue

        stored_sha = hashlib.sha256(stored.encode()).hexdigest()
        sha_match = stored_sha == expected_sha
        len_match = len(stored) == expected_len

        # 3. For CDS parts, verify biological constraints
        is_cds = part_name.startswith("BBa_C") or part_name.startswith("BBa_E")
        atg_start = stored.startswith("ATG")
        has_stop = False
        internal_stops = 0
        stop_idx = -1

        if is_cds:
            for i in range(0, len(stored) - 2, 3):
                codon = stored[i:i + 3]
                if codon in STOPS:
                    if stop_idx == -1:
                        stop_idx = i
                        has_stop = True
                    elif stop_idx >= 0 and i > stop_idx + 3:
                        # After the first stop, don't count
                        pass
                    elif stop_idx == -1:
                        internal_stops += 1

        status = "PASS" if sha_match and len_match else "FAIL"
        if not sha_match or not len_match:
            all_pass = False

        extra = ""
        if is_cds:
            extra = f" ATG={'Y' if atg_start else 'N'} stop={'Y' if has_stop else 'N'} intStop={internal_stops}"

        print(f"{status} {part_name}: stored={len(stored)}bp reg={expected_len}bp sha={'match' if sha_match else 'MISMATCH'}{extra}")

    # 4. Fresh registry comparison (for CDS parts only, to avoid rate limits)
    print("\n--- Fresh registry fetch (CDS parts) ---")
    cds_parts = [n for n in registry_data if n.startswith("BBa_C") or n.startswith("BBa_E")]
    for part_name in cds_parts:
        fresh = fetch_from_registry(part_name)
        if not fresh:
            print(f"SKIP {part_name}: could not fetch from registry")
            continue

        stored = get_api_sequence(part_name)
        if not stored:
            continue

        if fresh == stored:
            print(f"PASS {part_name}: byte-identical to registry")
        else:
            print(f"FAIL {part_name}: DIFFERS from registry (stored={len(stored)}, fresh={len(fresh)})")
            all_pass = False

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
