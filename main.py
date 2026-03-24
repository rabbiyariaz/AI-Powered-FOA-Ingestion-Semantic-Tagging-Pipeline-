"""
FOA Ingestion + Semantic Tagging Pipeline

==========================================
Usage:
    python main.py --url "<grants.gov URL>" --out_dir ./out
Strategy:
    1. Grants.gov URLs  → fetchOpportunity REST API 
                        → requests + BeautifulSoup   (fallback)
    2. Generic URLs     → requests + BeautifulSoup
Outputs:
    out/foa.json   -- structured FOA record
    out/foa.csv    -- same record as a single-row CSV
"""

import argparse
import json
import re
import os
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import csv
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────

def clean_text(value: str) -> str:
    """Collapse whitespace and strip."""
    return re.sub(r"\s+", " ", value or "").strip()

def find_first(text: str, patterns: list[str]) -> str:
    """Return the first regex group match across a list of patterns."""
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1))
    return ""

def normalize_date(date_str: str) -> str:
    """Parse any recognisable date string to ISO-8601 (YYYY-MM-DD)."""
    if not date_str:
        return ""
    try:
        return date_parser.parse(str(date_str)).date().isoformat()
    except Exception:
        return ""

def generate_id() -> str:
    return f"AUTO_{str(uuid.uuid4())[:8]}"

def empty_record(url: str) -> dict:
    return {
        "foa_id":      generate_id(),
        "title":       "",
        "agency":      "Unknown",
        "open_date":   "",
        "close_date":  "",
        "eligibility": "",
        "description": "",
        "award_range": "",
        "url":         url,
        "tags":        [],
        "extraction_status": "failed"
    }
# ──────────────────────────────────────────────────────────────────────────────
# Semantic Tagging  (rule-based, ontology-aligned)
# ──────────────────────────────────────────────────────────────────────────────
TAG_ONTOLOGY: dict[str, list[str]] = {
    # Research domains
    "AI/ML":            ["artificial intelligence", " ai ", "machine learning",
                         "deep learning", "neural network", "llm", "large language"],
    "Healthcare":       ["health", "clinical", "medical", "disease", "patient",
                         "biomedical", "public health", "epidemiology", "mental health"],
    "Environment":      ["environment", "climate", "energy", "sustainability",
                         "ecology", "conservation", "renewable", "carbon"],
    "Education":        ["education", "training", "workforce", "student",
                         "curriculum", "learning", "higher education", "k-12"],
    "Social Science":   ["social", "community", "public policy", "equity",
                         "humanities", "sociology", "economics", "poverty"],
    "STEM":             ["stem", "engineering", "mathematics", "physics",
                         "chemistry", "biology", "computer science"],
    "Defense/Security": ["defense", "military", "national security",
                         "cybersecurity", "darpa", "dod", "homeland"],
    "Data Science":     ["data science", "data analytics", "big data",
                         "database", "data infrastructure", "informatics"],
    # Methods / approaches
    "Research":         ["research", "investigation", "study", "discovery",
                         "scientific", "experimental"],
    "Clinical Trial":   ["clinical trial", "randomized", "phase i", "phase ii",
                         "phase iii", "interventional", "placebo"],
    # Sponsor themes
    "Funding":          ["grant", "funding", "award", "fellowship",
                         "cooperative agreement", "subaward"],
    "Small Business":   ["small business", "sbir", "sttr", "startup",
                         "entrepreneur"],
    # Populations
    "Minority-Serving": ["minority", "underrepresented", "historically black",
                         "hbcu", "tribal", "hispanic serving", "diversity"],
    "International":    ["international", "global", "developing countries",
                         "foreign", "overseas"],
}

def get_tags(record: dict) -> list[str]:
    """Apply ontology-based rule tagging against combined record text."""
    text = " ".join([
        record.get("title", ""),
        record.get("description", ""),
        record.get("eligibility", ""),
        record.get("agency", ""),
        record.get("award_range", ""),
    ]).lower()

    return [tag for tag, keywords in TAG_ONTOLOGY.items()
            if any(kw in text for kw in keywords)]


# ──────────────────────────────────────────────────────────────────────────────
# Source A: Grants.gov  fetchOpportunity API
# ──────────────────────────────────────────────────────────────────────────────
GRANTS_GOV_API = "https://api.grants.gov/v1/api/fetchOpportunity"

def _extract_grants_gov_id(url: str) -> str | None:
    """Extract opportunity identifier from various Grants.gov URL formats"""
    
    # New format: simpler.grants.gov/opportunity/{uuid}
    m = re.search(r"simpler\.grants\.gov/opportunity/([a-f0-9-]+)", url)
    if m:
        return m.group(1)  # This returns: 77242ec4-56ad-4784-84ca-066b30d01fae
    
    # Traditional format: view-opportunity.html?oppId=XXXXXX
    params = parse_qs(urlparse(url).query)
    if params.get("oppId"):
        return params["oppId"][0]
    
    # Format: /search-results-detail/XXXXXX
    m = re.search(r"/search-results-detail/(\d+)", url)
    if m:
        return m.group(1)
    
    # Format: oppId=XXXXXX anywhere in URL
    m = re.search(r"oppId=(\d+)", url)
    if m:
        return m.group(1)
    
    return None

def fetch_grants_gov_api(url: str) -> dict | None:
    opp_id = _extract_grants_gov_id(url)
    if not opp_id:
        return None

    # Skip API for UUIDs — it only accepts numeric IDs
    if re.search(r'[a-f0-9]{8}-[a-f0-9]{4}', opp_id):
        print("  [grants.gov API] UUID detected — skipping API, going to HTML scraper")
        return None

    
    # NOTE: simpler.grants.gov uses UUID format (e.g. 77242ec4-...) which is
    # incompatible with the fetchOpportunity API that expects numeric oppIds.
    # These will intentionally return None here and fall through to HTML scraper.

    print(f"  [grants.gov API] Trying fetchOpportunity API with ID: {opp_id}")
    
    try:
        r = requests.post(
            "https://api.grants.gov/v1/api/fetchOpportunity",
            json={"oppId": opp_id},
            timeout=15
        )

        data = r.json()
        # Grants.gov backend server unavailable
        if isinstance(data.get("data"), dict) and "not available" in data["data"].get("message", "").lower():
            print("  [grants.gov API] Backend server unavailable")
            return None
        
        title = data.get("opportunityTitle", "")
        
        # Check if we got valid data
        if not title or title == "Lock":
            print(f"  [grants.gov API] No valid opportunity found")
            return None
            
        print(f"  [grants.gov API] Successfully retrieved: {title[:50]}...")
        
        # Get synopsis data
        synopsis = data.get("synopsis", {})
        
        # Return using the correct structure from fetchOpportunity
        return {
            "foa_id": opp_id,
            "title": clean_text(title),
            "agency": clean_text(data.get("agencyName", "Unknown")),
            "open_date": normalize_date(synopsis.get("postDate", "")),
            "close_date": normalize_date(synopsis.get("closeDate", "")),
            "eligibility": clean_text(synopsis.get("applicantEligibilityDesc", "")),
            "description": clean_text(synopsis.get("description", "") or synopsis.get("synopsisDesc", ""))[:2000],
            "award_range": clean_text(synopsis.get("awardCeiling", "")),
            "url": url,
            "tags": []  # Will be populated by get_tags later
        }
    except Exception as e:
        print(f"  [grants.gov API] Failed: {e}")
        return None
# ──────────────────────────────────────────────────────────────────────────────
# Source B: Generic HTML scraper (BeautifulSoup fallback)
# ──────────────────────────────────────────────────────────────────────────────
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/"

}

def _get_title(soup: BeautifulSoup) -> str:
    for candidate in (soup.find("h1"), soup.find("title")):
        if candidate:
            text = clean_text(candidate.get_text(" ", strip=True))
            if text:
                return text
    og = soup.find("meta", attrs={"property": "og:title"})
    return clean_text(og.get("content", "")) if og else ""

def _get_description(soup: BeautifulSoup) -> str:
    # 1. Try meta (fast path)
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content") and len(meta["content"]) > 50:
        return clean_text(meta["content"])

    # 2. Look for Description section (BEST METHOD)
    desc_header = soup.find(["h2", "h3"], string=re.compile("Description", re.I))
    if desc_header:
        parts = []
        for sibling in desc_header.find_next_siblings():
            if sibling.name in ["h2", "h3"]:
                break
            if sibling.name == "p":
                text = clean_text(sibling.get_text())
                if len(text) > 40:
                    parts.append(text)

        if parts:
            return " ".join(parts)[:2000]

    # 3. Fallback: collect meaningful paragraphs from main
    main = soup.find("main") or soup.find("article") or soup.body
    if not main:
        return ""

    paras = [
        clean_text(p.get_text(" ", strip=True))
        for p in main.find_all("p")
        if len(p.get_text(strip=True)) > 80  # stricter filter
    ]

    if paras:
        return " ".join(paras[:3])[:2000]  # take top 2–3, not just first

    # 4. Last fallback
    return clean_text(main.get_text(" ", strip=True))[:2000]

def _get_agency(text: str) -> str:
    agency = find_first(text, [
        r"agency\s*name\s*[:\-]\s*([^\n\r|]{2,120})",
        r"agency\s*[:\-]\s*([^\n\r|]{2,120})",
    ])
    if agency:
        return agency
    known = {
        "national institutes of health": "National Institutes of Health",
        "nih": "National Institutes of Health",
        "national science foundation": "National Science Foundation",
        "department of energy": "Department of Energy",
        "doe": "Department of Energy",
        "nasa": "NASA",
        "cdc": "Centers for Disease Control and Prevention",
        "hhs": "Department of Health and Human Services",
        "usda": "U.S. Department of Agriculture",
        "epa": "Environmental Protection Agency",
        "department of education": "Department of Education",
    }
    tl = text.lower()
    for key, value in known.items():
        if key in tl:
            return value
    return "Unknown"

def extract_foa_id_from_html(soup):
    label = soup.find(string=re.compile(r"Funding opportunity number", re.I))
    
    if not label:
        return ""

    parent = label.parent

    # look for value in next container
    next_div = parent.find_next_sibling("div")
    
    if next_div:
        p = next_div.find("p")
        if p:
            return clean_text(p.get_text())

    return ""

def _get_foa_id(url: str, text: str, soup=None) -> str:
    # 1. URL-based ID
    params = parse_qs(urlparse(url).query)
    if params.get("oppId"):
        return clean_text(params["oppId"][0])

    m = re.search(r"/search-results-detail/(\d+)", url)
    if m:
        return m.group(1)

    # 2. HTML extraction (NEW — important)
    if soup:
        foa_html = extract_foa_id_from_html(soup)
        if foa_html:
            return foa_html

    # 3. Regex fallback
    extracted = find_first(text, [
        r"(?:opportunity|foa)\s*(?:number|id)\s*[:\-]?\s*([A-Za-z0-9\-_.]+)"
    ])

    return extracted if extracted else generate_id()
def extract_award_value(soup, label):
    node = soup.find(string=re.compile(label, re.I))
    
    if not node:
        return ""

    parent = node.parent

    # Case 1: value is PREVIOUS sibling
    prev_p = parent.find_previous_sibling("p")
    if prev_p:
        val = clean_text(prev_p.get_text())
        if "$" in val:
            return val

    # Case 2: value is NEXT sibling (other layouts)
    next_p = parent.find_next_sibling("p")
    if next_p:
        val = clean_text(next_p.get_text())
        if "$" in val:
            return val

    return ""

def scrape_html(url: str) -> dict | None:
    """Enhanced scraper for simpler.grants.gov format"""
    print(f"  [HTML scraper] Fetching: {url}")
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()

        if "protect your privacy" in resp.text.lower():
            print("[HTML scraper] Blocked page detected - attempting minimal extraction")

            soup = BeautifulSoup(resp.text, "html.parser")
            title = _get_title(soup)

            # Filter useless titles that indicate blocking rather than actual content
            if title.lower() in ["lock", "access denied", "just a moment"]:
                title = ""

            return {
                "foa_id": generate_id(),
                "title": title,
                "agency": "Unknown",
                "open_date": "",
                "close_date": "",
                "eligibility": "",
                "description": "",
                "award_range": "",
                "url": url,
                "tags": [],
                "extraction_status": "blocked_partial"
            }

            
    except Exception as e:
        print(f"  [HTML scraper] Request failed: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    text = clean_text(soup.get_text(" ", strip=True))
    
    # Extract title from h1
    title = ""
    h1 = soup.find("h1")
    if h1:
        title = clean_text(h1.get_text())
    
    # Extract agency from the Agency: field
    agency = ""

    agency_label = soup.find(string=re.compile(r"Agency", re.I))

    if agency_label:
        parent = agency_label.parent  # <span>
        container = parent.parent     # <p>

        full_text = clean_text(container.get_text())

        # Remove the label
        agency = re.sub(r"Agency\s*:?\s*", "", full_text, flags=re.I)
    # Extract close date from the Closing: field
    close_date = ""
    closing_label = soup.find(string=re.compile("Closing:"))
    if closing_label:
        close_date = normalize_date(closing_label.find_next().get_text() if closing_label.find_next() else "")

    open_date = ""

    label = soup.find(string=re.compile(r"Posted\s*date", re.I))

    if label:
        parent = label.parent

        # Find next <p> sibling (this contains the date)
        next_p = parent.find_next_sibling("p")

        if next_p:
            open_date = normalize_date(next_p.get_text())
    # Extract eligibility from the Eligible applicants section
    
    eligibility = ""

    eligibility_header = soup.find("h2", string=re.compile("Eligibility", re.I))

    items = []

    if eligibility_header:
        for sibling in eligibility_header.find_next_siblings():

            # stop only at next major section
            if sibling.name == "h2":
                break

            for li in sibling.find_all("li"):
                text = clean_text(li.get_text())
                if text:
                    items.append(text)

    eligibility =  " | ".join(items)
                    
    description = ""

    container = soup.find("div", attrs={"data-testid": "opportunity-description"})

    if container:
        paragraphs = container.select("p")

        elements = []
        for p in paragraphs:
            text = clean_text(p.get_text())

            # 🚫 filter garbage (emails, contacts)
            if len(text) > 40 and "@" not in text.lower():
                elements.append(text)

        description = " ".join(elements)
    min_val = extract_award_value(soup, r"Award Minimum")
    max_val = extract_award_value(soup, r"Award Maximum")

    award_range = ""
    if min_val and max_val:
        award_range = f"{min_val} - {max_val}"
    elif max_val:
        award_range = f"Up to {max_val}"
    elif min_val:
        award_range = f"From {min_val}"
    record = {
        "foa_id": _get_foa_id(url, text, soup),
        "title": title or _get_title(soup),
        "agency": agency or _get_agency(text),
        "open_date": open_date,  
        "close_date": close_date,
        "eligibility": eligibility[:500] if eligibility else "",
        "description": description[:2000] if description else _get_description(soup),
        "award_range": award_range,
        "url": url,
        "tags": [],
    }
    
    # 1. Clean description
    if "read detailed information" in record["description"].lower():
        record["description"] = ""
    # 3. Generate tags AFTER cleaning
    record["tags"] = get_tags(record)

    # 4. Set extraction status LAST
    

    missing = []
    for field in ["title", "description", "eligibility"]:
        if not record.get(field):
            missing.append(field)
    record["extraction_status"] = (
        "complete" if not missing else f"partial_missing_{'_'.join(missing)}"
    )
    filled = sum(1 for k in ("title", "agency", "open_date", "close_date")
                    if record.get(k) not in ("", "Unknown"))
    print(f"  [HTML scraper] Done - {filled}/4 key fields populated.")
    return record

# ──────────────────────────────────────────────────────────────────────────────
# Router: pick the right fetcher for the URL
# ──────────────────────────────────────────────────────────────────────────────
def is_grants_gov(url: str) -> bool:
    return "grants.gov" in urlparse(url).netloc

def is_valid_record(record: dict) -> bool:
    """Check if extracted record has meaningful content."""
    if not record:
        return False

    critical_fields = ["title", "description", "agency"]
    filled = sum(1 for f in critical_fields if record.get(f) not in ("", "Unknown"))

    return filled >= 2  # minimum quality threshold

def ingest(url: str) -> dict:
    """
    Route the URL to the best available fetcher, with semantic validation.
    """
    record = None

    if is_grants_gov(url):
        print("[Router] Detected Grants.gov URL - trying API first.")
        record = fetch_grants_gov_api(url)
        
        if not is_valid_record(record):
            print("[Router] Falling back to HTML scraper.")
            record = scrape_html(url)
    else:
        print("[Router] Generic URL - using HTML scraper.")
        record = scrape_html(url)

    if not is_valid_record(record):
        print("[Router] WARNING: Extraction failed → returning empty structured record.")
        return empty_record(url)


    return record
# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    arg_parser = argparse.ArgumentParser(
        description=(
            "FOA ingestion + semantic tagging pipeline.\n"
            "Supports Grants.gov (API) and generic URLs with HTML fallback."
        )
    )
    arg_parser.add_argument("--url",     required=True,  help="FOA page URL")
    arg_parser.add_argument("--out_dir", required=True,  help="Output directory")
    args = arg_parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nIngesting: {args.url}\n{'─'*60}")
    data = ingest(args.url)

    # ── Outputs ───────────────────────────────────────────────────────────────
    json_path = out_dir / "foa.json"
    csv_path  = out_dir / "foa.csv"

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Append to CSV
    file_exists = csv_path.exists()

    with open(csv_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(data)

    # ✅ Print summary ONCE (outside the loop)
    print(f"\n{'─'*60}")
    print(f"Saved JSON -> {json_path}")
    print(f"Saved CSV  -> {csv_path} ({'appended' if file_exists else 'created'})")
    print("\nExtracted record:")
    for k, v in data.items():
        display = ", ".join(v) if isinstance(v, list) else v
        print(f"  {k:<15} {display}")

if __name__ == "__main__":
    main()
