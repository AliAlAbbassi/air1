# Crawler/Indexer Sources & Data Providers Research

## Serper.dev (Google Search API) -- TOP PICK

The single most useful tool for unauthenticated LinkedIn profile discovery at scale. Queries Google directly in real-time, returns structured JSON.

### API

- **Endpoint:** `POST https://google.serper.dev/search`
- **Auth:** Header `X-API-KEY: <key>`
- **Rate limit:** 300 queries/second
- **Response time:** 1-2 seconds

Other endpoints: `/images`, `/news`, `/places`, `/videos`, `/scholar`, `/shopping`, `/patents`, `/autocomplete`

### Pricing

| Tier | Cost | Queries | Per 1K |
|------|------|---------|--------|
| Free | $0 | 2,500 | $0 (no card needed) |
| Starter | $50 | 50,000 | $1.00 |
| Standard | $375 | 500,000 | $0.75 |
| Scale | $1,250 | 2,500,000 | $0.50 |
| Ultimate | $3,750 | 12,500,000 | $0.30 |

Credits last 6 months. Pay-as-you-go, not subscription.

### vs Google Custom Search API

| Feature | Serper.dev | Google CSE |
|---------|-----------|------------|
| Cost/1K queries | $0.30-1.00 | $5.00 |
| Free tier | 2,500 queries | 100/day |
| Rate limit | 300 QPS | 10 QPS |
| Setup | API key, instant | CSE engine config |
| Response | Full SERP JSON | Limited fields |

**Serper is 10-16x cheaper with 30x higher rate limits.**

### Usage for LinkedIn Discovery

```python
import requests, json

def search_linkedin_profiles(query: str, api_key: str, num: int = 10) -> dict:
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f"site:linkedin.com/in/ {query}", "num": num})
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    return requests.post(url, headers=headers, data=payload).json()

# Parse SERP results -- LinkedIn titles follow: "FirstName LastName - Title - Company | LinkedIn"
def parse_linkedin_serp(result: dict) -> dict:
    title = result.get("title", "").replace(" | LinkedIn", "")
    parts = title.split(" - ")
    return {
        "name": parts[0].strip() if len(parts) > 0 else "",
        "title": parts[1].strip() if len(parts) > 1 else "",
        "company": parts[2].strip() if len(parts) > 2 else "",
        "linkedin_url": result.get("link", ""),
        "snippet": result.get("snippet", ""),
    }

# Batch search with asyncio
async def batch_search(queries: list[str], api_key: str) -> list[dict]:
    import aiohttp
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    async def _search(session, q):
        payload = json.dumps({"q": f"site:linkedin.com/in/ {q}", "num": 10})
        async with session.post(url, headers=headers, data=payload) as resp:
            return await resp.json()
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(*[_search(session, q) for q in queries])
```

**LinkedIn utility: 9/10** -- Google indexes LinkedIn public profiles extensively. Best unauthenticated approach at scale.

---

## Common Crawl -- NOT USEFUL for LinkedIn

LinkedIn's `robots.txt` blocks CCBot. Common Crawl respects this. **Virtually no LinkedIn profile data exists in Common Crawl.**

### CDX API (for reference)

```
GET https://index.commoncrawl.org/CC-MAIN-{YYYY-WW}-index?url=linkedin.com/company/&matchType=prefix&output=json&limit=1000
```

### What IS useful

- Finding company websites that link TO LinkedIn profiles (indirect discovery)
- Historical web archive data for non-LinkedIn sites

### Used in sadie-gtm

sadie-gtm uses Common Crawl CDX API to discover booking engine URLs (Cloudbeds, RMS, Mews). Pattern: search for known URL patterns in the archive index to find properties.

**LinkedIn utility: 1/10**

---

## Wayback Machine

### CDX API

```
GET https://web.archive.org/cdx/search/cdx?url=linkedin.com/in/{slug}&output=json&matchType=prefix&collapse=timestamp:6&limit=100&fl=timestamp,original,statuscode,mimetype
```

### Availability API

```
GET https://archive.org/wayback/available?url=linkedin.com/in/{slug}&timestamp={yyyyMMddhhmmss}
```

### Fetch archived page

```
GET https://web.archive.org/web/{timestamp}id_/{url}
```

### Rate Limits

- CDX API: ~1 request/second (IP-based, enforced)
- Snapshot fetching: ~30 req/sec
- No API keys -- IP throttling only

### LinkedIn Data

- **Pre-2018 snapshots:** Some public profiles archived (name, headline, position, summary, experience)
- **Recent snapshots:** Very limited. LinkedIn blocks archival crawlers. Most return 999 status or login redirects
- **Company pages:** Slightly more available than personal profiles

**LinkedIn utility: 3/10** -- Only useful for historical research on known profiles. Too slow (1 req/sec) and too stale for lead discovery.

---

## AlienVault OTX -- NOT USEFUL for LinkedIn

Threat intelligence platform. Free API, no LinkedIn data.

### API

```
GET https://otx.alienvault.com/api/v1/indicators/domain/{domain}/{section}
Sections: general, geo, malware, url_list, passive_dns, whois
Header: X-OTX-API-KEY: <key>
Rate: 1K/hr (no key), 10K/hr (with key)
```

### Only B2B use

- WHOIS data: map domain to company name, registrant email
- Passive DNS: find subdomains, infrastructure size
- Reverse WHOIS: find all domains by same registrant

**LinkedIn utility: 1/10**

---

## Ahrefs -- Expensive Indirect Discovery

SEO tool with one of the largest backlink indexes. API requires Enterprise plan ($1,499+/mo).

### API v3

```
GET https://api.ahrefs.com/v3/site-explorer/backlinks?target={domain}
Authorization: Bearer <key>
```

### LinkedIn use case

Find company team pages that link to individual LinkedIn profiles via backlink analysis. Cannot get LinkedIn page content, only link relationships.

**Alternatives:** SEMrush ($499/mo), Majestic ($399/mo), Moz ($49-299/mo), DataForSEO ($0.60-1.20/1K queries)

**LinkedIn utility: 5/10** -- Good for indirect discovery but expensive for this use case alone.

---

## Other Useful Sources

### Crunchbase -- Company & Founder Data

- Company database with funding, founders, executives, industry
- Often stores LinkedIn URLs for companies and founders
- API: $49/mo (Pro), $199/mo (Business), $10K+/year (Enterprise/API)
- Rate: 200 req/min

```python
GET https://api.crunchbase.com/api/v4/entities/organizations/{permalink}?user_key=KEY&field_ids=short_description,linkedin,website,num_employees_enum,founded_on,funding_total,categories
```

**LinkedIn utility: 6/10**

### BuiltWith -- Technology Profiling

- What technologies 250M+ websites use
- $295+/mo for API access
- Great for "find all companies using Salesforce and React" type queries

```python
GET https://api.builtwith.com/v21/api.json?KEY={key}&LOOKUP={domain}
GET https://api.builtwith.com/lists/v7/api.json?KEY={key}&TECH={tech_name}
```

**LinkedIn utility: 2/10** -- No LinkedIn data, but useful for technology-based company targeting.

### PhantomBuster -- Direct LinkedIn Automation

- Cloud automation with pre-built "Phantoms" for LinkedIn
- $59-439/month
- LinkedIn Profile Scraper, Company Scraper, Search Export, Network Booster
- **Violates LinkedIn ToS** -- account ban risk

**LinkedIn utility: 8/10** -- Directly scrapes LinkedIn. High risk.

### ZoomInfo -- Enterprise Contact DB

- 1.3B+ contacts, 100M+ companies
- $15K-25K+/year minimum
- Has LinkedIn URLs, emails, phones, org charts, intent data

**LinkedIn utility: 8/10** -- Purpose-built for this. Price is prohibitive for small teams.

### Shodan EntityDB

- `entitydb.shodan.io` has company financial overviews and executive info for US-listed entities
- Data from SEC filings, not LinkedIn

### Censys.io

- Internet-wide host/certificate scanning
- Free tier + $69-1,099/mo
- Infrastructure mapping only, no LinkedIn data

---

## Origami Agents (origamiagents.com)

**Y Combinator F24 batch. $2M seed. $50K MRR in 50 days.**

### What it is

AI-powered B2B sales intelligence platform that deploys autonomous AI agents to find and qualify high-intent leads. Founded by Finn Mallery (CEO) and Kenson Chung (CTO).

### What it does

- **Account Flows:** Identify target companies matching your ICP
- **People Flows:** Find decision-makers at qualified accounts
- **CRM Flows:** Enrich and score existing CRM data
- **Signals:** Monitor real-time buying triggers (SEC filings, press, job posts, funding, LinkedIn, equipment purchases)

### Example workflow

> "Find B2B AI startups that filed SEC Form D last week for over $6M. Match them to similar customers, check investor partnerships, enrich contact info, draft an email from my templates, and assign to my SMB reps."

### Key details

- Serves 200+ B2B companies (healthcare, fintech, SaaS, professional services)
- SOC 2 Type II + ISO 27001 certified
- Integrations: Salesforce, HubSpot, Outreach, OpenAPI
- **No public API** -- managed SaaS only, configured through their UI
- Custom pricing (contact sales)
- Tech stack: Next.js, React, Vercel, NextAuth

### Customer results

- Stellar: $200K ARR/month, 4x email close rates
- Redesign Health: 8 hrs/week saved per rep, 5x more decision makers than ZoomInfo
- MightyCause: 32 qualified meetings in 2 months

### Comparison to air1

| | Origami | air1 |
|--|---------|------|
| Model | Managed SaaS | Self-hosted code |
| API | No public API | Full code control |
| Data sources | 7+ (SEC, LinkedIn, news, jobs, CRM) | LinkedIn + (adding SEC) |
| LinkedIn | Signal monitoring | Direct Playwright scraping |
| Price | Custom (likely $$$) | Free (self-hosted) |
| AI | Built-in agent orchestration | CrewAI agents |
| Strength | Hands-off, multi-source signals | Full control, no vendor lock-in |

**Relevance: Competitor/inspiration.** They do exactly what you're building (SEC + LinkedIn + enrichment) but as a managed service. No APIs to integrate with.

---

## Final Rankings for LinkedIn B2B Lead Gen

| Rank | Source | LinkedIn Utility | Cost | Best For |
|------|--------|-----------------|------|----------|
| 1 | **Serper.dev** | 9/10 | $0.30-1.00/1K | Primary discovery via Google index |
| 2 | **Proxycurl** | 10/10 | ~$0.01/profile | Profile enrichment from known URLs |
| 3 | **Apollo.io** | 7/10 | Free-$119/mo | All-in-one with huge free tier |
| 4 | **PhantomBuster** | 8/10 | $59-439/mo | Direct LinkedIn automation (risky) |
| 5 | **Crunchbase** | 6/10 | $49-199/mo | Company + founder discovery |
| 6 | **ZoomInfo** | 8/10 | $15K+/yr | Enterprise full contact DB |
| 7 | **Ahrefs** | 5/10 | $1,499+/mo | Indirect via backlink analysis |
| 8 | **BuiltWith** | 2/10 | $295+/mo | Tech-based company targeting |
| 9 | **Wayback Machine** | 3/10 | Free | Historical profile research |
| 10 | **AlienVault OTX** | 1/10 | Free | Domain/WHOIS only |
| 11 | **Common Crawl** | 1/10 | Free | LinkedIn blocked by robots.txt |

### Recommended Unauthenticated Pipeline

1. **Serper.dev** ($50-375/mo) -- Discover LinkedIn profile URLs via Google dorking at scale
2. **Proxycurl** (~$0.01/profile) -- Enrich discovered URLs with full profile data
3. **Apollo.io** (free tier) -- Cross-reference with company data + email finding
4. **Hunter.io** ($49/mo) -- Email pattern detection + verification
5. **BuiltWith** (optional) -- Technology-based company filtering

**Total: under $500/mo for thousands of profiles/day, entirely without LinkedIn API access.**

---

## sadie-gtm Codebase Analysis

See [SADIE_GTM_ANALYSIS.md](./SADIE_GTM_ANALYSIS.md) for full analysis.
