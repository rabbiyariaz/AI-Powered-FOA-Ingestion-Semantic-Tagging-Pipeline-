# AI-Powered Funding Intelligence  

## FOA Ingestion + Semantic Tagging Pipeline
A production-ready FOA ingestion pipeline that converts unstructured grant data into structured, searchable intelligence.

## 🎥 Demo

[Watch Demo](https://youtu.be/zb7ml9n1hDg)

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

```markdown
## Why This Matters

- FOAs are scattered and unstructured across multiple sources  
- Researchers spend hours manually searching  
- This system automates discovery and enables structured intelligence  


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

## 📊 Sample Output

```json

{
  "foa_id": "AFPMB-BAA-26-01",
  "title": "Opportunity Listing - Deployed Warfighter Protection (DWFP) Program for the Protection of Deployed Military Personnel from Threats Posed by Arthropod Disease Vectors",
  "agency": "ACC-APG-Detrick",
  "open_date": "2025-11-19",
  "close_date": "",
  "eligibility": "Unrestricted",
  "description": "The DWFP Program’s mission is to protect deployed military personnel from arthropod vectors of medically relevant disease pathogens, including (but not limited to) arthropod disease vectors of tick-borne pathogens and mosquito-borne arboviruses, as well as nuisance biting arthropods and emerging arthropod threats such as the New World Screwworm fly. The DWFP Program seeks to fund original and innovative research that supports the Advanced Technology Development of new insecticides, or improved formulations of existing insecticides for vector control, new technology or enhanced modalities of personal protection from biting arthropods, or improved efficacy and sustainability of equipment for application of pesticides.",
  "award_range": "$-- - $975,000",
  "url": "https://simpler.grants.gov/opportunity/a9f27238-998f-47f7-81f3-6dab3247d79b",
  "tags": [
    "Healthcare",
    "Environment",
    "Defense/Security",
    "Research"
  ],
  "extraction_status": "complete"
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



# Traditional format
python main.py --url "https://www.grants.gov/search-results-detail/350094" --out_dir ./out


### Tested URLs

| URL | Result | Reason |
|-----|--------|--------|
| `simpler.grants.gov/opportunity/77242ec4...` | ✅ complete | HTML scraper (4/4 fields) |
| `simpler.grants.gov/opportunity/a9f27238...` | ✅ complete | HTML scraper (4/4 fields) |
| `simpler.grants.gov/opportunity/ca2f980d...` | ✅ complete | HTML scraper (4/4 fields) |
| `grants.gov/search-results-detail/350094` | ⚠️ failed | API backend down + bot protection |

## Key Strengths

- Handles real-world edge cases (API failure, UUID routing, bot protection)
- Deterministic and reproducible pipeline
- Modular and extensible architecture

## Future Improvements
Add additional FOA sources (NIH, NSF)
Integrate embedding-based semantic tagging
Add vector search (FAISS / Chroma)
Build lightweight search interface
