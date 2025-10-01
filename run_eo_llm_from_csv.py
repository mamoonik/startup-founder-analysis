

import os, csv, re, time, argparse, requests, json
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit
from eo_scorer.llm_scorer import score_with_llm  

PROFILE_API = "https://enrichlayer.com/api/v2/profile"
COMPANY_API = "https://enrichlayer.com/api/v2/company"

### Authorization

def _auth_headers() -> Dict[str, str]: ##-> Dict[str, str]: This is a type hint. 
    ##It specifies that the function is expected to return a dictionary (Dict) where both the keys and values are strings (str).

    key = os.getenv("ENRICHLAYER_API_KEY")
    if not key:
        raise RuntimeError("ENRICHLAYER_API_KEY not set")
    return {'Authorization': f'Bearer {key}'}

#### URL cleansing to convert linkedin.com/in/werdna --> https://www.linkedin.com/in/werdna needed by API

_URL_LIKE = re.compile(r'(https?://)|(^www\.)|(^|\b)linkedin\.', re.I)

def _looks_like_url(x: Any) -> bool:
    return isinstance(x, str) and bool(_URL_LIKE.search(x.strip()))

def _canon_profile_url(u: str) -> str:
    if not u:
        return ""
    u = u.strip()
    if not re.match(r'^https?://', u, re.I):
        # accept "www." or bare "linkedin.com/..."
        u = "https://" + u.lstrip("/")
    return u

# def _canon_linkedin_company_url(u: str) -> str:
#     """
#     Normalize LinkedIn company URLs so we can de-dupe reliably.
#     - add https:// if missing
#     - lower-case host/path
#     - strip query/fragment
#     - ensure a single trailing slash
#     """
#     if not u:
#         return ""
#     if not re.match(r'^https?://', u, re.I):
#         u = "https://" + u.lstrip("/")
#     parts = urlsplit(u.strip())
#     path = parts.path.rstrip("/").lower()
#     netloc = parts.netloc.lower()
#     norm = urlunsplit((parts.scheme or "https", netloc, path, "", ""))
#     if not norm.endswith("/"):
#         norm += "/"
#     return norm

def _canon_linkedin_company_url(u: str) -> str:
    """
    Normalize LinkedIn company URLs so we can de-dupe reliably.
    - add https:// if missing
    - lower-case host/path
    - strip query/fragment
    - ensure a single trailing slash
    """
    if not u:
        return ""
    if not re.match(r'^https?://', u, re.I):
        u = "https://" + u.lstrip("/")
    parts = urlsplit(u.strip())
    path = parts.path.rstrip("/").lower()
    netloc = parts.netloc.lower()
    norm = urlunsplit((parts.scheme or "https", netloc, path, "", ""))
    if not norm.endswith("/"):
        norm += "/"
    return norm

def _safe(d: Any, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

####  EnrichLayer fetchers 

def fetch_profile(linkedin_url: str) -> Dict[str, Any]:
    headers = _auth_headers()
    params = {
        'profile_url': _canon_profile_url(linkedin_url),
        'extra': 'include',
        'github_profile_id': 'include',
        'facebook_profile_id': 'include',
        'twitter_profile_id': 'include',
        'personal_contact_number': 'include',
        'personal_email': 'include',
        'inferred_salary': 'include',
        'skills': 'include',
        'use_cache': 'if-present',
        'fallback_to_cache': 'on-error',
        # 'live_fetch': 'force', ## Keeping this off as this causes a lot of delay but it useful fi a profile is not returned by the API from the cached profiles database
    }
    r = requests.get(PROFILE_API, params=params, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()

def fetch_company(linkedin_company_url: str) -> Dict[str, Any]:
    headers = _auth_headers()
    params = {
        'url': _canon_linkedin_company_url(linkedin_company_url),
        'categories': 'include',
        'funding_data': 'include',
        'exit_data': 'include',
        'acquisitions': 'include',
        'extra': 'include',
        'use_cache': 'if-present',
        'fallback_to_cache': 'on-error',
    }
    ## Givesa lot of ocmpany information but not all is important to me
    ## and I want to be conservative with token usage and latency
    r = requests.get(COMPANY_API, params=params, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()

###  Company payload cleansing 

def compact_company_payload(raw: Dict[str, Any], source_linkedin_url: Optional[str] = None) -> Dict[str, Any]:
    # Funding summary (from raw["extra"] and raw["funding_data"])
    number_of_funding_rounds = _safe(raw, "extra", "number_of_funding_rounds")
    total_funding_amount = _safe(raw, "extra", "total_funding_amount")
    stock_symbol = _safe(raw, "extra", "stock_symbol")
    ipo_date = _safe(raw, "extra", "ipo_date")
    number_of_investors = _safe(raw, "extra", "number_of_investors")

    funding_rounds = []
    for fr in (raw.get("funding_data") or []):
        funding_rounds.append({
            "funding_type": fr.get("funding_type"),
            "money_raised": fr.get("money_raised"),
            "announced_date": fr.get("announced_date"),
            "number_of_investor": fr.get("number_of_investor"),
            "investor_list": [
                {"name": inv.get("name"),
                 "type": inv.get("type"),
                 "linkedin_profile_url": inv.get("linkedin_profile_url")}
                for inv in (fr.get("investor_list") or [])
            ]
        })

    out: Dict[str, Any] = {
        "query_linkedin_url": source_linkedin_url,
        "name": raw.get("name"),
        "description": raw.get("description"),   # <- added
        "website": raw.get("website"),
        "industry": raw.get("industry"),
        "categories": (raw.get("categories") or [])[:10],
        "company_size": raw.get("company_size"),
        "company_type": raw.get("company_type"),
        "founded_year": raw.get("founded_year") or _safe(raw, "extra", "founding_date", "year"),
        "hq": {
            "country": _safe(raw, "hq", "country"),
            "state": _safe(raw, "hq", "state"),
            "city": _safe(raw, "hq", "city"),
        },
        "follower_count": raw.get("follower_count"),
        "public_markets": {
            "ipo_status": _safe(raw, "extra", "ipo_status"),
            "stock_symbol": stock_symbol,
            "ipo_date": ipo_date,
        },
        "external_refs": {
            "crunchbase_profile_url": _safe(raw, "extra", "crunchbase_profile_url"),
        },
        "funding_summary": {
            "number_of_funding_rounds": number_of_funding_rounds,
            "total_funding_amount": total_funding_amount,
            "number_of_investors": number_of_investors,
        },
        "funding_rounds": funding_rounds,  # detailed list
    }
    return out

### Enrich companies information back into the person's profile data

def enrich_companies_in_profile(profile: Dict[str, Any], sleep_between: float = 0.2) -> Dict[str, Any]:
    """
    - Collect volunteer company URLs (to skip).
    - For each experience entry with company_linkedin_profile_url, enrich & attach.
    - De-dupe company API calls across experiences.
    """
    experiences: List[Dict[str, Any]] = profile.get("experiences") or []
    volunteer_urls = set()
    for vw in (profile.get("volunteer_work") or []):
        u = _safe(vw, "company_linkedin_profile_url") or _safe(vw, "company", "company_linkedin_profile_url")
        if u:
            volunteer_urls.add(_canon_linkedin_company_url(u))

    cache: Dict[str, Dict[str, Any]] = {}
    for exp in experiences:
        url = exp.get("company_linkedin_profile_url") or _safe(exp, "company", "company_linkedin_profile_url")
        if not url:
            continue
        canon = _canon_linkedin_company_url(url)
        if canon in volunteer_urls:
            # explicitly skip volunteer companies
            continue

        try:
            if canon not in cache:
                raw = fetch_company(canon)
                cache[canon] = compact_company_payload(raw, source_linkedin_url=canon)
                time.sleep(sleep_between)
            exp["company_enrichment"] = cache[canon]
        except Exception as e:
            # Attach a non-fatal error note so you can see what failed downstream,
            # but DON'T stop the pipeline.
            exp["company_enrichment_error"] = f"{type(e).__name__}: {e}"

    return profile

### CSV loading with header detection 

def _load_rows_auto(input_csv: str, explicit_url_col: Optional[str]) -> (List[Dict[str, Any]], str):
    """
    Returns (rows_in, url_col).
    Detects headerless single-column CSVs (list of URLs) and normalizes them to [{'url': ...}, ...].
    """
    # First try DictReader to preserve normal headered files
    with open(input_csv, newline="", encoding="utf-8") as f:
        dr = csv.DictReader(f)
        rows = list(dr)
        fieldnames = list(dr.fieldnames or [])

    # If user explicitly provided the column, keep DictReader path
    if explicit_url_col:
        return rows, explicit_url_col

    # Detect headerless (first "fieldname" looks like a URL and there's only one column)
    header_is_url = any(_looks_like_url(fn) for fn in fieldnames if fn)
    if header_is_url and len(fieldnames) == 1:
        # Re-read as plain reader and treat each row as a url cell
        clean_rows: List[Dict[str, Any]] = []
        with open(input_csv, newline="", encoding="utf-8") as f2:
            rr = csv.reader(f2)
            for r in rr:
                if not r:
                    continue
                cell = (r[0] or "").strip()
                if not cell:
                    continue
                clean_rows.append({"url": cell})
        return clean_rows, "url"

    # Otherwise, use the header we got and auto-pick the URL column
    url_col: Optional[str] = None
    for c in fieldnames:
        if isinstance(c, str) and re.search(r'link|url', c, re.I):
            url_col = c
            break
    if url_col is None:
        # Fall back to the first non-empty string fieldname
        for c in fieldnames:
            if isinstance(c, str) and c.strip():
                url_col = c
                break
    if url_col is None:
        # As a last resort, try the first key from the first row
        if rows and isinstance(rows[0], dict):
            for k in rows[0].keys():
                if isinstance(k, str) and k.strip():
                    url_col = k
                    break
    if url_col is None:
        raise RuntimeError("Could not determine URL column. Use --url_col to specify it.")

    return rows, url_col

#  Main LLM scoring pipeline 

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_csv")
    ap.add_argument("--out", default="LINKEDIN_SCRAPING/output_llm_analysis.csv")
    ap.add_argument("--url_col", default=None)
    args = ap.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print(" OPENAI_API_KEY not set — LLM scorer will return a stub.")

    try:
        rows_in, url_col = _load_rows_auto(args.input_csv, args.url_col)
    except Exception as e:
        print(f"Failed to load CSV: {e}")
        return

    if not rows_in:
        print("No rows in input.")
        return

    results = []
    for i, row in enumerate(rows_in, 1):
        # pull URL
        raw_url = row.get(url_col, "")
        url = raw_url.strip() if isinstance(raw_url, str) else ""
        if not url:
            results.append({"score": 0, "reason": "No URL", "band": "No/Negative", "confidence": 0.2, **row})
            continue

        # 1) Fetch profile
        try:
            prof = fetch_profile(url)
        except Exception as e:
            results.append({"score": 0, "reason": f"Fetch error: {e}", "band": "No/Negative", "confidence": 0.2, **row})
            continue

        # 2) Enrich profile with company info (skip volunteer companies automatically)
        try:
            prof = enrich_companies_in_profile(prof, sleep_between=0.2)
        except Exception as e:
            # Non-fatal: still try to score with what we have
            if isinstance(prof, dict):
                prof["company_enrichment_pipeline_error"] = f"{type(e).__name__}: {e}"

        # 3) LLM SCORING
        llm = score_with_llm(prof)
        results.append({
            "score": llm.get("score", 0),
            "reason": " | ".join(llm.get("reasons", [])) or "(no reason)",
            "band": llm.get("band", ""),
            "confidence": llm.get("confidence", ""),
            **row
        })
        time.sleep(0.2)

    # write output
    orig_cols = [c for c in results[0].keys() if c not in ("score", "reason", "band", "confidence")]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["score", "reason", "band", "confidence"] + orig_cols)
        w.writeheader()
        for r in results:
            w.writerow(r)
    print(f"✅ LLM pipeline: {len(results)} rows → {args.out}")

if __name__ == "__main__":
    main()



###############
################
#################
###############
################
#################
###############
################
#################
###############
################
#################
###############
################
#################










# #  python run_eo_native_from_csv.py "[Priv. and Conf.] RH Founder Signal Sample - Example Profiles.csv" --out output_native.csv