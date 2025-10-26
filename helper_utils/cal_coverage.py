import json, re
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd

# ================== Helpers ==================

def clean_code(x: str) -> str:
    """Normalize response code: remove spaces, convert '4 04' -> '404'."""
    s = str(x).strip().replace(" ", "")
    digits = re.findall(r'\d', s)
    if len(digits) == 3:
        return ''.join(digits)
    return s

def load_observed(csv_path: str) -> Tuple[Dict[str, List[str]], pd.DataFrame]:
    """
    Read run results CSV with at least columns:
      - endpoint (e.g., 'get-/pets/{id}')
      - response_status (e.g., '200', '404', 'default')
    Returns:
      observed: dict endpoint -> sorted unique list of codes (strings)
      df: the cleaned dataframe
    """
    df = pd.read_csv(
        csv_path,
        dtype={"response_status": "string"},   # keep as string
        keep_default_na=False,                 # don't convert to NaN
        na_filter=False                        # keep raw text like "nan"
    )
    need = {"endpoint", "response_status"}
    miss = need - set(df.columns)
    if miss:
        raise ValueError(f"CSV missing columns: {miss}")

    df["response_status"] = df["response_status"].apply(clean_code)

    # keep only 3-digit codes or 'default'
    df = df[df["response_status"].str.fullmatch(r"(default|\d{3})", na=False)]

    observed = (
        df.groupby("endpoint")["response_status"]
          .apply(lambda s: sorted(set(s)))
          .to_dict()
    )
    return observed, df


def load_documented(doc_json_path: str) -> Dict[str, List[str]]:
    """
    Read documented JSON: { "get-/path": {"status_codes": ["200","400","default"]}, ... }
    Returns dict endpoint -> list(status_codes)
    """
    data = json.loads(Path(doc_json_path).read_text(encoding="utf-8"))
    documented = {k: list(v.get("status_codes", [])) for k, v in data.items()}
    return documented

def is_5xx(code: str) -> bool:
    return re.fullmatch(r"5\d\d", str(code)) is not None

def is_2xx(code: str) -> bool:
    return re.fullmatch(r"2\d\d", str(code)) is not None

def is_4xx(code: str) -> bool:
    return re.fullmatch(r"4\d\d", str(code)) is not None


# ================== Core analysis ==================

def analyze(observed: Dict[str, List[str]],
            documented: Dict[str, List[str]],
            count_default_in_denominator: bool = False):
    """
    Paper-aligned coverage:
      - Only 2xx and 4xx are counted in denominators and numerators.
      - 'default' is never counted in denominators or numerators.
      - A status code counts once per endpoint even if many tests hit it.
      - Overall coverage = (matched 2xx + matched 4xx) / (doc 2xx + doc 4xx).
    """
    rows = []

    # Service-level totals (paper uses totals, not avg of per-endpoint pcts)
    total_doc_2xx = total_doc_4xx = 0
    total_hit_2xx = total_hit_4xx = 0

    for ep, doc_codes_list in documented.items():
        doc_set = {c for c in doc_codes_list if c != "default"}  # strip 'default'
        obs_set = set(observed.get(ep, []))

        # partition documented into classes the paper measures
        doc_2xx = {c for c in doc_set if is_2xx(c)}
        doc_4xx = {c for c in doc_set if is_4xx(c)}

        # matches (unique codes observed ∩ documented)
        hit_2xx = obs_set & doc_2xx
        hit_4xx = obs_set & doc_4xx

        # per-endpoint coverage (reported for convenience)
        denom_2xx = len(doc_2xx)
        denom_4xx = len(doc_4xx)
        pct_2xx = (len(hit_2xx) / denom_2xx * 100.0) if denom_2xx else 0.0
        pct_4xx = (len(hit_4xx) / denom_4xx * 100.0) if denom_4xx else 0.0

        # overall per-endpoint (2xx+4xx only, no 'default')
        denom_total = denom_2xx + denom_4xx
        matched_total = len(hit_2xx) + len(hit_4xx)
        pct_total = (matched_total / denom_total * 100.0) if denom_total else 0.0

        # accumulate service-level totals (paper's "Average" per service is totals-based)
        total_doc_2xx += denom_2xx
        total_doc_4xx += denom_4xx
        total_hit_2xx += len(hit_2xx)
        total_hit_4xx += len(hit_4xx)

        rows.append({
            "endpoint": ep,
            "documented_codes": sorted(doc_set),           # explicit documented (no 'default')
            "observed_codes": sorted(obs_set),             # what you actually triggered (unique)
            "matched_codes": sorted((hit_2xx | hit_4xx)),  # matches counted for coverage

            "documented_2xx": sorted(doc_2xx),
            "matched_2xx": sorted(hit_2xx),
            "coverage_2xx_pct": round(pct_2xx, 1),

            "documented_4xx": sorted(doc_4xx),
            "matched_4xx": sorted(hit_4xx),
            "coverage_4xx_pct": round(pct_4xx, 1),

            "coverage_pct": round(pct_total, 1),           # per-endpoint overall (2xx+4xx)
        })

    # --- service-level paper metrics (totals) ---
    denom_service_total = total_doc_2xx + total_doc_4xx
    matched_service_total = total_hit_2xx + total_hit_4xx

    overall_pct = (matched_service_total / denom_service_total * 100.0) if denom_service_total else 0.0
    overall_2xx_pct = (total_hit_2xx / total_doc_2xx * 100.0) if total_doc_2xx else 0.0
    overall_4xx_pct = (total_hit_4xx / total_doc_4xx * 100.0) if total_doc_4xx else 0.0

    # endpoints present only in observed (not in documented)
    untracked_eps = sorted(set(observed.keys()) - set(documented.keys()))

    # discovered new codes per endpoint (excluding 'default' comparison)
    discovered = []
    for ep, obs_list in observed.items():
        obs_codes = set(obs_list)
        if ep in documented:
            doc_explicit = {c for c in documented[ep] if c != "default"}
            new_codes = sorted(obs_codes - doc_explicit)
        else:
            new_codes = sorted(obs_codes)
        if new_codes:
            discovered.append({"endpoint": ep, "new_codes": new_codes})

    # 5xx stats (unchanged; paper’s RQ3 tracks server errors separately)
    five_rows = []
    total_5xx_unique = 0
    for ep, obs_list in observed.items():
        fives = sorted({c for c in obs_list if is_5xx(c)})
        if fives:
            five_rows.append({"endpoint": ep, "5xx_codes": fives, "count": len(fives)})
            total_5xx_unique += len(fives)

    summary = {
        # Paper-aligned service totals
        "overall_coverage_pct": round(overall_pct, 2),          # (hit_2xx+hit_4xx)/(doc_2xx+doc_4xx)
        "total_documented_codes": int(denom_service_total),     # counts only 2xx+4xx
        "total_matched_codes": int(matched_service_total),      # counts only 2xx+4xx

        "overall_2xx_coverage_pct": round(overall_2xx_pct, 2),
        "total_documented_2xx_codes": int(total_doc_2xx),
        "total_matched_2xx_codes": int(total_hit_2xx),

        "overall_4xx_coverage_pct": round(overall_4xx_pct, 2),
        "total_documented_4xx_codes": int(total_doc_4xx),
        "total_matched_4xx_codes": int(total_hit_4xx),

        # extras
        "untracked_endpoints_count": int(len(untracked_eps)),
        "total_5xx_unique_codes": int(total_5xx_unique),

        # kept for compatibility but no longer used in the paper’s math:
        "count_default_in_denominator": False,
    }
    return rows, untracked_eps, discovered, five_rows, summary



# ================== Output ==================

def write_outputs(outdir: str, rows, untracked_eps, discovered, five_rows, summary):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(rows).to_csv(out / "coverage_by_endpoint.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"endpoint": untracked_eps}).to_csv(out / "untracked_endpoints.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(discovered).to_csv(out / "discovered_new_codes.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(five_rows).to_csv(out / "5xx_codes.csv", index=False, encoding="utf-8-sig")

    (out / "coverage_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ================== Main ==================

def main():
    service_name = "GitLab Issues"
    csv_file_name = "20251026151111"

    csv_path = f"../database/{service_name}/results/{csv_file_name}.csv"
    doc_json_path = f"../database/{service_name}/response_code/response_codes_normalized.json"
    outdir = f"../database/{service_name}/coverage_results"


    COUNT_DEFAULT_IN_DENOMINATOR = False  # include 'default' in overall denominator

    observed, _ = load_observed(csv_path)
    documented = load_documented(doc_json_path)

    rows, untracked_eps, discovered, five_rows, summary = analyze(
        observed, documented, count_default_in_denominator=COUNT_DEFAULT_IN_DENOMINATOR
    )
    write_outputs(outdir, rows, untracked_eps, discovered, five_rows, summary)

    print("Done.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
