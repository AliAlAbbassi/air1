# SEC EDGAR + LinkedIn Scraping Research

## Current Codebase Capabilities

Already have a production-grade LinkedIn B2B lead gen platform:
- 11 workflows (scraping, connecting, outreach, profile details)
- Playwright browser automation + Voyager API hybrid
- PostgreSQL (Prisma + aiosql) with leads, profiles, companies, contact tracking
- CrewAI agents for prospect research, outreach messaging, company finding
- Email outreach via Resend with rate limiting
- Dual session cookies (`LINKEDIN_READ_SID` / `LINKEDIN_WRITE_SID`)

Missing: top-of-funnel company ingestion from SEC EDGAR and unauthenticated LinkedIn enrichment.

---

## SEC EDGAR - Free Company Database

All SEC data is **free, no API key, no auth**. Requires `User-Agent: YourCompany email@example.com` header. Rate limit: 10 req/sec.

### Key APIs

| API | URL | What You Get |
|-----|-----|-------------|
| **Company Submissions** | `data.sec.gov/submissions/CIK{cik_padded_10}.json` | Name, address, phone, website, SIC code, tickers, full filing history |
| **Company Tickers** | `sec.gov/files/company_tickers_exchange.json` | ~10,000 public companies (CIK, ticker, name, exchange) |
| **Full-Text Search** | `efts.sec.gov/LATEST/search-index/` (POST) | Search all filings since 2001 by keyword, form type, date range |
| **XBRL Company Facts** | `data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json` | All XBRL facts (every financial line item ever reported) |
| **XBRL Frames** | `data.sec.gov/api/xbrl/frames/us-gaap/{concept}/{unit}/{period}.json` | Cross-company financial comparison (e.g. all companies' revenue) |
| **Bulk Submissions ZIP** | `data.sec.gov/submissions/submissions.zip` | All company submission metadata, republished nightly ~3AM ET |

### Submissions API Response Fields

```
cik, entityType, sic, sicDescription, name, tickers[], exchanges[],
ein, website, investorWebsite, category, fiscalYearEnd,
stateOfIncorporation, phone, formerNames[],
addresses.mailing{street1, street2, city, stateOrCountry, zipCode},
addresses.business{...},
filings.recent{accessionNumber[], filingDate[], form[], primaryDocument[], ...}
```

### Full-Text Search API (EFTS)

```python
POST https://efts.sec.gov/LATEST/search-index/
Headers:
  User-Agent: YourCompany email@example.com
  origin: https://www.sec.gov
Body (JSON):
  q: search keywords
  entityName: company name or CIK
  forms: ["10-K", "DEF 14A"]
  dateRange: "all" | "10y" | "5y" | "1y" | "30d" | "custom"
  startdt: "YYYY-MM-DD" (when dateRange=custom)
  enddt: "YYYY-MM-DD"
  locationCodes: ["CA", "NY"]
  from: pagination offset (increments by 100)
```

### Filing Types for Lead Generation

| Filing | Volume | Value |
|--------|--------|-------|
| **Form D** | ~30k/year | Startups/private companies raising capital. **Structured XML** with officer names, addresses, offering amounts. Gold mine for early-stage companies. |
| **DEF 14A** (proxy) | ~8k/year | Executive names, titles, compensation, board members for public companies |
| **10-K** (annual) | ~8-10k/year | Company overview, executive officer list, business addresses, subsidiary list |
| **Form 4** (insider) | High volume | Officer/director names, titles, stock transactions |
| **13F** (holdings) | ~5k/quarter | Institutional investors, fund managers, investment firms |
| **S-1** (IPO) | Varies | Detailed company info for companies going public |

### Recommended Library: `edgartools`

```
pip install edgartools
```

Best Python library for EDGAR. 10-30x faster than alternatives (lxml + PyArrow). Auto rate limiting, caching, DataFrame output.

```python
from edgar import Company, set_identity, find

set_identity("admin@mycompany.com")

company = Company("AAPL")
print(company.name, company.sic, company.industry, company.city, company.state, company.phone)

filings_10k = company.get_filings(form="10-K")
filings_def14a = company.get_filings(form="DEF 14A")
filings_form_d = company.get_filings(form="D")

results = find("artificial intelligence")
financials = Company("MSFT").get_financials()
```

### Other Libraries

- **sec-edgar-api** -- Lightweight wrapper for data.sec.gov
- **sec-edgar-downloader** -- Bulk downloading filings to disk
- **python-edgar** -- Index file processing, building local DB

### Practical Bootstrap Approach

```
1. BOOTSTRAP: company_tickers_exchange.json -> company master table (CIK, ticker, name, exchange)
2. ENRICH: data.sec.gov/submissions/ -> company profiles (address, SIC, phone, website)
3. OFFICERS: Form D XML -> officers/directors (private cos); DEF 14A HTML -> executives (public cos)
4. FINANCIALS: XBRL companyfacts API -> financial metrics; Frames API -> industry comparisons
5. MONITOR: EFTS search API -> new filings alerts; Daily index files -> daily ingestion
```

### Rate Limiting

- Max 10 req/sec. Exceeding triggers temporary IP block (lifts after 10 min).
- Best practice: 0.1-0.15s delay between requests.
- Async with semaphore of 8 (margin under 10).

---

## LinkedIn Scraping - Unauthenticated Methods

### What Works Without Login

| Method | Volume | Quality | Cost |
|--------|--------|---------|------|
| **Google dorking** (`site:linkedin.com/in/ "Company" "CEO"`) | 100/day free (Google CSE) | Good for discovering profiles | Free to $5/1k queries |
| **Bing Web Search API** | 1000/month free | Good, Microsoft owns LinkedIn | Free to $3/1k |
| **DuckDuckGo** (`duckduckgo-search` lib) | ~50-100 queries before throttle | Decent | Free |
| **Common Crawl** | Huge but stale | Historical only | Free |

Direct public profile scraping hits authwall after a few requests - not viable at scale.

### Google Dorking Patterns

```
site:linkedin.com/in/ "company name" "title"
site:linkedin.com/in/ "Acme Corp" "CEO"
site:linkedin.com/in/ "Acme Corp" ("CTO" OR "VP Engineering" OR "Head of Engineering")
site:linkedin.com/company/ "Acme Corp"
```

**Google Custom Search JSON API:** 100 free queries/day, $5/1k after. Max 100 results per search term.
- Endpoint: `https://www.googleapis.com/customsearch/v1?key=KEY&cx=CX&q=...`
- Create engine at https://programmablesearchengine.google.com/

**Bing Web Search API:** 1000 calls/month free, then $3/1k.
- Endpoint: `https://api.bing.microsoft.com/v7.0/search`
- Header: `Ocp-Apim-Subscription-Key: KEY`
- Advantage: Microsoft owns LinkedIn, often fresher data

**DuckDuckGo:**
```python
from duckduckgo_search import DDGS
with DDGS() as ddgs:
    results = list(ddgs.text('site:linkedin.com/in/ "Acme" "CEO"', max_results=20))
```

### Public Profile Data (without login)

Available: full name, headline, current company, location, profile photo (sometimes), about (sometimes), ~connections count.
NOT available: full work history, education, skills, contact info, connections list, activity.

### LinkedIn Voyager API (Authenticated, Unofficial)

Base URL: `https://www.linkedin.com/voyager/api`
Auth: `li_at` cookie + `JSESSIONID` cookie + `csrf-token` header

Key endpoints:
```
GET /identity/dash/profiles?q=memberIdentity&memberIdentity=slug&decorationId=...
GET /organization/companies?q=universalName&universalName=slug&decorationId=...
GET /search/dash/clusters?q=all&query=(keywords:...,resultType:List(PEOPLE),currentCompany:List(id))&start=0&count=10
POST /growth/normInvitations  (connection requests)
```

### Rate Limits for LinkedIn Automation

| Action | Safe/Day | Aggressive (risky) |
|--------|----------|-------------------|
| Profile views | 80-100 | 200 |
| Search queries | 30-50 | 100 |
| Connection requests | 20-30 | 50 |
| Messages | 50-75 | 150 |
| Page loads | 200-300 | 500 |

### Open Source: `linkedin-api` (Python)

```python
from linkedin_api import Linkedin
api = Linkedin("email", "password")  # or use cookie auth
profile = api.get_profile("slug")
contact = api.get_profile_contact_info("slug")
people = api.search_people(keyword_company="Acme", keyword_title="CEO")
company = api.get_company("acme-corp")
```

GitHub: https://github.com/tomquirk/linkedin-api (~7k+ stars)
Caveat: username/password auth triggers 2FA. Cookie auth is safer.

---

## Third-Party Enrichment APIs

### Tier 1: Recommended

| Service | Free Tier | Best For | Paid |
|---------|-----------|----------|------|
| **Apollo.io** | 10,000 email credits/mo | People search + email finding | $49/mo+ |
| **Proxycurl** | 10 credits (trial) | Highest quality LinkedIn data | ~$0.01/lookup |
| **Hunter.io** | 25 searches + 50 verifications/mo | Email patterns + verification | $49/mo for 500 |

### Tier 2: Alternatives

| Service | Free Tier | Best For | Paid |
|---------|-----------|----------|------|
| **People Data Labs** | 100 records/mo | Bulk person data (1.5B+ records) | $0.01-0.10/record |
| **Clearbit** (HubSpot) | Via HubSpot | Company enrichment | Varies |
| **RocketReach** | 5 lookups/mo | Emails + phone numbers | $53/mo |
| **Snov.io** | 50 credits/mo | Email finding + drip campaigns | $39/mo |
| **Kaspr** | 5 credits/mo | Chrome extension, phone numbers | Varies |
| **Lusha** | 5 credits/mo | Direct phone numbers | Varies |
| **Dropcontact** | 25 credits/mo | GDPR-compliant email enrichment | Varies |

### Apollo.io API (Best Free Option)

```python
# People search
POST https://api.apollo.io/v1/mixed_people/search
{
  "api_key": KEY,
  "q_organization_name": "Acme Corp",
  "person_titles": ["CEO", "CTO", "CFO", "VP"],
  "per_page": 25
}
# Returns: people[{first_name, last_name, title, linkedin_url, email, organization{...}}]

# Person enrichment
POST https://api.apollo.io/v1/people/match
{"api_key": KEY, "linkedin_url": "https://linkedin.com/in/slug"}

# Company enrichment
POST https://api.apollo.io/v1/organizations/enrich
{"api_key": KEY, "domain": "acme.com"}
```

### Proxycurl API (Best LinkedIn Quality)

```python
# Profile lookup (1 credit)
GET https://nubela.co/proxycurl/api/v2/linkedin
  ?url=https://linkedin.com/in/slug
  Authorization: Bearer KEY

# Company lookup (1 credit)
GET https://nubela.co/proxycurl/api/linkedin/company
  ?url=https://linkedin.com/company/slug

# Role lookup (3 credits) - find CEO/CTO/etc at a company
GET https://nubela.co/proxycurl/api/find/company/role/
  ?company_name=Acme&role=ceo&enrich_profile=enrich

# Employee search
GET https://nubela.co/proxycurl/api/linkedin/company/employees/
  ?linkedin_company_profile_url=...&role_search=engineering

# Personal email lookup
GET https://nubela.co/proxycurl/api/contact-api/personal-email
  ?linkedin_profile_url=...
```

### Hunter.io API

```python
# Domain search - find all emails at a domain + detect pattern
GET https://api.hunter.io/v2/domain-search?domain=acme.com&api_key=KEY
# Returns: emails[{value, type, confidence, first_name, last_name, position}], pattern

# Email finder - specific person
GET https://api.hunter.io/v2/email-finder?domain=acme.com&first_name=John&last_name=Doe&api_key=KEY

# Email verifier
GET https://api.hunter.io/v2/email-verifier?email=john@acme.com&api_key=KEY
```

---

## Email Finding & Verification

### Common Email Patterns (by frequency)

1. `first.last@domain.com` -- 45% of companies
2. `firstlast@` -- 15%
3. `first@` -- 10%
4. `flast@` (first initial + last) -- 10%
5. `first_last@` -- 5%
6. Other -- 15%

### Email Verification Pipeline

1. **Syntax check** (regex)
2. **MX record check** (DNS lookup - does domain receive email?)
3. **SMTP RCPT TO check** (does recipient exist?) -- use with caution, many catch-all servers
4. **Service verification** (ZeroBounce, NeverBounce, MillionVerifier)

### Verification Services

| Service | Price | Notes |
|---------|-------|-------|
| **MillionVerifier** | $0.0005/email | Cheapest batch option |
| **ZeroBounce** | $0.008/email | Very high accuracy |
| **NeverBounce** | $0.008/email | Very high accuracy |
| **Debounce** | $0.005/email | Good accuracy |
| **Kickbox** | $0.01/email | Good accuracy |

---

## Recommended Pipeline Architecture

```
SEC EDGAR                    Enrichment                      Existing System
---------                    ----------                      ---------------
company_tickers.json ---+
                        +--> Company DB --> LinkedIn URL --> Company enrichment
Form D XML parsing -----+    (Prisma)      (Bing/DDG)       (Apollo/Proxycurl)
                                               |
                                               v
                                         People discovery --> Email enrichment
                                         (Apollo free tier)   (Hunter/Apollo)
                                               |
                                               v
                                         Existing outreach workflows
                                         + browser automation + CrewAI
```

### Cost-Optimized Stack

| Stage | Primary (Free) | Fallback (Paid) |
|-------|---------------|-----------------|
| Company LinkedIn URL | DuckDuckGo/Bing | Google CSE ($5/1k) |
| Company enrichment | Apollo free tier | Proxycurl ($0.01/lookup) |
| People discovery | Apollo (10k credits/mo) | Google dorking |
| Email finding | Apollo free | Hunter.io ($49/mo) |
| Email verification | MillionVerifier ($0.0005/ea) | Hunter (included) |
| LinkedIn profile data | Proxycurl ($0.01/ea) | Voyager API (free, risky) |

**Estimated monthly cost for 1000 companies:**
- Free tier only: $0
- With verification: ~$5
- Full stack (all services): ~$100-200/mo

### Integration with air1 Codebase

1. **New service:** `air1/services/enrichment/` -- pipeline.py, sec_edgar.py, linkedin_enrichment.py, email_enrichment.py
2. **New workflow:** `air1/workflows/sec_to_outreach.py`
3. **New Prisma models:** CompanyLead (CIK, pipeline stage), PersonLead
4. **New CLI commands:** `air1 ingest-sec`, `air1 enrich-companies`, `air1 find-people`, `air1 pipeline`
5. **New SQL queries:** `air1/db/query/enrichment.sql`
6. Feeds into existing `outreach_to_companies.py` and `connect_with_company_members.py`

### Suggested DB Schema Additions

```prisma
model CompanyLead {
  id              String       @id @default(cuid())
  cik             String       @unique
  companyName     String
  sicCode         String?
  state           String?
  linkedinUrl     String?
  website         String?
  domain          String?
  industry        String?
  companySize     String?
  description     String?
  headquarters    String?
  pipelineStage   String       @default("ingested")  // ingested|enriched|people_found|emails_found|ready|sent|responded
  enrichedAt      DateTime?
  createdAt       DateTime     @default(now())
  updatedAt       DateTime     @updatedAt
  people          PersonLead[]
}

model PersonLead {
  id              String       @id @default(cuid())
  name            String
  title           String?
  linkedinUrl     String?
  email           String?
  emailVerified   Boolean      @default(false)
  emailConfidence Float        @default(0)
  companyLeadId   String
  companyLead     CompanyLead  @relation(fields: [companyLeadId], references: [id])
  outreachStatus  String       @default("pending")
  createdAt       DateTime     @default(now())
  updatedAt       DateTime     @updatedAt
}
```

---

## Legal Considerations

- **hiQ v. LinkedIn (2022):** Scraping publicly available LinkedIn data is NOT a CFAA violation (9th Circuit).
- **LinkedIn ToS:** Prohibits scraping. Contractual (civil), not criminal. Account ban risk.
- **GDPR/CCPA:** Personal data from scraping still subject to privacy laws. Need legitimate basis, honor opt-outs.
- **Using third-party APIs (Proxycurl, Apollo):** Low risk -- they assume scraping liability.
- **Best practice:** Use third-party enrichment APIs, only use direct LinkedIn automation for outreach actions.
