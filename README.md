# AI-Powered Funding Intelligence  

## FOA Ingestion + Semantic Tagging Pipeline
A production-ready FOA ingestion pipeline that converts unstructured grant data into structured, searchable intelligence.



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
  "foa_id": "BAA-AFRL-AFOSR-2016-0008",
  "title": "Opportunity Listing - Air Force Defense Research Sciences Conference and Workshop Support",
  "agency": "Air Force Office of Scientific Research",
  "open_date": "2016-07-22",
  "close_date": "",
  "eligibility": "Nonprofits non-higher education without 501(c)(3) | Nonprofits non-higher education with 501(c)(3) | Public and state institutions of higher education | Private institutions of higher education | Other",
  "description": "Broad Agency Announcement FA955025S0001 and BAA-AFRL-AFOSR-2016-0008 are closed as of 23 March 2026 due to a new mandatory review process, as required by Executive Order 14332 Improving Oversight of Federal Grantmaking – March 2026. The upcoming Open BAA will be posted at a date later to be determined. ATTENTION ALL GRANTEES: If you submitted your proposal to BAA FA955025S0001 and BAA-AFRL-AFOSR-2016-0008 during the dates 18 March 2026 – 23 March 2026, you must resubmit your proposal to the upcoming Open BAA. The new Open BAA will ensure that all Department of the Air Force (DAF) assistance awards align with Department of War (DoW) priorities, serve the national interest, and adhere to applicable laws and regulations. The Air Force Office of Scientific Research manages the basic research investment for the U.S. Air Force. Conferences and workshops constitute key forums for research and technology interchange. We provide partial support for conferences and workshops as defined in the DoD Joint Travel Regulations in special areas of science that bring experts together to discuss recent research or educational findings, or to expose other researchers or advanced graduate students to new research and educational techniques in our areas of research interest. Our research interests are described in the most recent version of our general Broad Agency Announcement titled, “Research Interests of the Air Force Office of Scientific Research” posted on Grants.gov. We can only consider funding requests from U.S. institutions of higher education (IHE) or nonprofit organizations as described in 2 CFR 25.345, including foreign public entities and foreign organizations operated primarily for scientific, educational, service, charitable, or similar purposes in the public interest. We do not award grants to organizations with a for-profit organization type. Our support for a workshop or conference is not an endorsement of any organization.Our financial support through grants for confe",
  "award_range": "$1 - $1,000,000",
  "url": "https://simpler.grants.gov/opportunity/77242ec4-56ad-4784-84ca-066b30d01fae",
  "tags": [
    "Education",
    "Defense/Security",
    "Research",
    "Funding",
    "International"
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
