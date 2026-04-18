# AI-Powered Funding Intelligence  

## FOA Ingestion + Semantic Tagging Pipeline

### Overview
Funding Opportunity Announcements (FOAs) are distributed across multiple sources, often in inconsistent formats and structures. This project implements a modular pipeline that ingests FOAs from public sources, extracts structured fields, and applies ontology-based semantic tagging to support downstream research discovery and grant matching.

---

### Features

- API-first ingestion for Grants.gov
- Automatic fallback to HTML scraping
- Structured extraction into a normalized FOA schema
- Rule-based semantic tagging using a controlled ontology
- JSON and CSV export for reproducibility
- Robust handling of incomplete or restricted data sources

---

### Architecture

![Architecture Diagram](Picture3.png)


## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py --url "https://simpler.grants.gov/opportunity/77242ec4-56ad-4784-84ca-066b30d01fae" --out_dir ./out
```

## Output

- `out/foa.json`: pretty-formatted JSON
- `out/foa.csv`: single-row CSV

Example schema:

```json

{
  "foa_id": "...",
  "title": "...",
  "agency": "...",
  "open_date": "...",
  "close_date": "...",
  "eligibility": "...",
  "description": "...",
  "award_range": "...",
  "url": "...",
  "tags": ["..."],
  "extraction_status": "complete | partial | failed"
}

```

### Semantic Tagging

Tags are assigned using a rule-based ontology covering:

Research domains (AI/ML, Healthcare, Environment, etc.)
Methods (Research, Clinical Trial)
Sponsor themes (Funding, Small Business)
Populations (Minority-Serving, International)

Tagging is applied on combined textual fields (title, description, eligibility, agency, award range).


### Design Decisions
API-first approach: More reliable than scraping when available
Fallback mechanism: Ensures resilience when API fails or is incomplete
Validation layer: Prevents propagation of empty or misleading data
Rule-based tagging: Deterministic baseline for semantic classification
Structured outputs: Enables downstream automation and analysis

### Limitations

- `simpler.grants.gov` URLs use UUID identifiers incompatible with the 
  `fetchOpportunity` API (expects numeric oppIds) — handled via HTML scraper fallback.

- `grants.gov/search-results-detail/` pages return an anti-bot interstitial 
  and cannot be scraped — returns `extraction_status: failed` gracefully.

- `grants.gov` API backend (`apply07.grants.gov`) is currently unavailable, 
  returning a 200 OK with an internal failure message — detected and handled explicitly.

- Newer `simpler.grants.gov` pages are client-side rendered, limiting HTML extraction 
  of some fields.

- Multiple “Description” sections in legacy pages require structural parsing 
instead of simple header matching.

#### Example Test Case

Tested on:


# Simpler.grants.gov format  
python main.py --url "https://simpler.grants.gov/opportunity/77242ec4-56ad-4784-84ca-066b30d01fae" --out_dir ./out


python main.py --url "https://simpler.grants.gov/opportunity/a9f27238-998f-47f7-81f3-6dab3247d79b" --out_dir ./out


python main.py --url "https://simpler.grants.gov/opportunity/ca2f980d-ecba-45f8-ae68-2c49eda57b92" --out_dir ./out



# Traditional format
python main.py --url "https://www.grants.gov/search-results-detail/350094" --out_dir ./out


### Tested URLs

| URL | Result | Reason |
|-----|--------|--------|
| `simpler.grants.gov/opportunity/77242ec4...` | ✅ complete | HTML scraper (4/4 fields) |
| `simpler.grants.gov/opportunity/a9f27238...` | ✅ complete | HTML scraper (4/4 fields) |
| `simpler.grants.gov/opportunity/ca2f980d...` | ✅ complete | HTML scraper (4/4 fields) |
| `grants.gov/search-results-detail/350094` | ⚠️ failed | API backend down + bot protection |

## Future Improvements
Add additional FOA sources (NIH, NSF)
Integrate embedding-based semantic tagging
Add vector search (FAISS / Chroma)
Build lightweight search interface
