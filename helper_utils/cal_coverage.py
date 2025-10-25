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
    Returns: (rows, untracked_eps, discovered, five_rows, summary)

    rows: per-endpoint records with:
      - documented_codes, observed_codes, matched_codes, coverage_pct
      - documented_2xx, matched_2xx, coverage_2xx_pct
      - documented_4xx, matched_4xx, coverage_4xx_pct

    summary: overall coverage + split by 2xx/4xx, untracked endpoints count, etc.

    Coverage rules:
    - Overall coverage can optionally count 'default' in the denominator, controlled by
      count_default_in_denominator. If counted, 'default' is considered matched if any
      observed code exists that's NOT in documented explicit codes.
    - 2xx / 4xx coverage do NOT consider 'default' in their denominators.
    """
    rows = []

    # Totals for overall coverage (with optional default handling)
    total_doc = 0
    total_match = 0

    # Totals for split coverage (default excluded)
    total_doc_2xx = 0
    total_match_2xx = 0
    total_doc_4xx = 0
    total_match_4xx = 0

    for ep, doc_codes_list in documented.items():
        # Remove 'default' for class-specific checks
        doc_codes_no_default = {c for c in doc_codes_list if c != "default"}
        obs_codes = set(observed.get(ep, []))

        # --- Overall coverage (optionally includes 'default' in denominator) ---
        doc_total_set = set(doc_codes_no_default)
        matched_total = obs_codes.intersection(doc_total_set)
        matched_total_count = len(matched_total)
        denom_total = len(doc_total_set)

        if "default" in doc_codes_list and count_default_in_denominator:
            denom_total += 1
            # 'default' matched if any observed code NOT in explicit documented set
            if any((c not in doc_codes_no_default) for c in obs_codes):
                matched_total_count += 1

        pct_total = (matched_total_count / denom_total * 100.0) if denom_total else 0.0
        total_doc += denom_total
        total_match += matched_total_count

        # --- 2xx coverage (default excluded) ---
        doc_2xx = {c for c in doc_codes_no_default if is_2xx(c)}
        matched_2xx = obs_codes.intersection(doc_2xx)
        denom_2xx = len(doc_2xx)
        pct_2xx = (len(matched_2xx) / denom_2xx * 100.0) if denom_2xx else 0.0
        total_doc_2xx += denom_2xx
        total_match_2xx += len(matched_2xx)

        # --- 4xx coverage (default excluded) ---
        doc_4xx = {c for c in doc_codes_no_default if is_4xx(c)}
        matched_4xx = obs_codes.intersection(doc_4xx)
        denom_4xx = len(doc_4xx)
        pct_4xx = (len(matched_4xx) / denom_4xx * 100.0) if denom_4xx else 0.0
        total_doc_4xx += denom_4xx
        total_match_4xx += len(matched_4xx)

        rows.append({
            "endpoint": ep,
            "documented_codes": sorted(doc_codes_list),
            "observed_codes": sorted(obs_codes),
            "matched_codes": sorted(list(matched_total)),   # explicit matches only
            "coverage_pct": round(pct_total, 1),

            "documented_2xx": sorted(doc_2xx),
            "matched_2xx": sorted(matched_2xx),
            "coverage_2xx_pct": round(pct_2xx, 1),

            "documented_4xx": sorted(doc_4xx),
            "matched_4xx": sorted(matched_4xx),
            "coverage_4xx_pct": round(pct_4xx, 1),
        })

    # Overall summaries
    overall_pct = (total_match / total_doc * 100.0) if total_doc else 0.0
    overall_2xx_pct = (total_match_2xx / total_doc_2xx * 100.0) if total_doc_2xx else 0.0
    overall_4xx_pct = (total_match_4xx / total_doc_4xx * 100.0) if total_doc_4xx else 0.0

    # Endpoints present in observed only (not in documented)
    untracked_eps = sorted(set(observed.keys()) - set(documented.keys()))

    # Discovered new codes per endpoint
    discovered = []
    for ep, obs_list in observed.items():
        obs_set = set(obs_list)
        if ep in documented:
            doc_set = set([c for c in documented[ep] if c != "default"])
            new_codes = sorted(list(obs_set - doc_set))
        else:
            new_codes = sorted(list(obs_set))  # all are "new" against the spec
        if new_codes:
            discovered.append({"endpoint": ep, "new_codes": new_codes})

    # 5xx stats
    five_rows = []
    total_5xx = 0
    for ep, obs_list in observed.items():
        fives = sorted(list({c for c in obs_list if is_5xx(c)}))
        if fives:
            five_rows.append({"endpoint": ep, "5xx_codes": fives, "count": len(fives)})
            total_5xx += len(fives)

    summary = {
        # overall
        "overall_coverage_pct": round(overall_pct, 2),
        "total_documented_codes": int(total_doc),
        "total_matched_codes": int(total_match),

        # split by class (default excluded)
        "overall_2xx_coverage_pct": round(overall_2xx_pct, 2),
        "total_documented_2xx_codes": int(total_doc_2xx),
        "total_matched_2xx_codes": int(total_match_2xx),

        "overall_4xx_coverage_pct": round(overall_4xx_pct, 2),
        "total_documented_4xx_codes": int(total_doc_4xx),
        "total_matched_4xx_codes": int(total_match_4xx),

        "untracked_endpoints_count": int(len(untracked_eps)),
        "total_5xx_unique_codes": int(total_5xx),
        "count_default_in_denominator": bool(count_default_in_denominator),
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
    # >>> EDIT THESE 3 PATHS <<<
    csv_path = r"/Users/npt/Documents/NCKH/restful-api-testing-framework/database/Pet Store/results/20251025134017.csv"
    doc_json_path = r"/Users/npt/Documents/NCKH/restful-api-testing-framework/Dataset/Pet Store/response_codes_normalized.json"
    outdir = r"/Users/npt/Documents/NCKH/restful-api-testing-framework/helper_utils/cal_coverage_output"

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
