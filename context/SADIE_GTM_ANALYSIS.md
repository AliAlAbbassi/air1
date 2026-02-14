# sadie-gtm Codebase Analysis

Source: https://github.com/aliabbassi-1337/sadie-gtm

## What It Does

Automated lead generation pipeline for **hotel booking engine detection at scale**. Built for a company selling booking engine software to independent hotels.

1. Discovers hotels across geographic regions (US, starting with Florida)
2. Detects what booking engine software each hotel uses (Cloudbeds, Mews, RMS Cloud, SiteMinder, etc.)
3. Enriches with room counts, customer proximity, contact info, location
4. Exports qualified leads as Excel reports

Core insight: if a hotel uses a competitor's booking engine, it's a sales lead.

## Architecture

```
Workflows (CLI scripts)
    |
Services (business logic)
    |
Repositories (data access via aiosql)
    |
PostgreSQL + PostGIS (asyncpg)
```

### Services

| Service | Purpose |
|---------|---------|
| `services/leadgen/` | Grid-based hotel scraping via Serper API, Playwright detection |
| `services/enrichment/` | Room counts (Groq LLM), customer proximity (PostGIS), websites, booking pages |
| `services/reporting/` | Excel generation (openpyxl), S3 upload, Slack notifications |
| `services/ingestor/` | Florida DBPR licenses, Texas hotel tax, CSV, Common Crawl archives |

### Libraries

| Lib | Purpose |
|-----|---------|
| `lib/cloudbeds/` | Cloudbeds API client (property_info endpoint) |
| `lib/rms/` | RMS Cloud client with proxy support |
| `lib/mews/` | Mews booking engine API |
| `lib/siteminder/` | SiteMinder GraphQL API (direct-book.com) |
| `lib/browser.py` | Managed Playwright browser pool for concurrent scraping |
| `lib/archive/` | Wayback Machine + Common Crawl slug enumeration |

### Infrastructure

| Component | Purpose |
|-----------|---------|
| `infra/sqs.py` | AWS SQS for distributed detection |
| `infra/s3.py` | Excel report uploads |
| `infra/slack.py` | Pipeline notifications |

## Pipeline Steps

```
1. Ingest Regions  -> OSM city polygons -> DB
2. Scrape Hotels   -> Serper Maps API grid search -> hotels table (status=0)
3. Deduplicate     -> Mark duplicates by placeId/location/name
4. Enqueue         -> Hotel IDs -> SQS in batches of 20
5. Detect          -> EC2 workers poll SQS, visit websites with Playwright
                   -> Detect booking engine by URL patterns, network requests, DOM
                   -> Store in hotel_booking_engines table
6. Enrich          -> Room counts (Groq LLM), customer proximity (PostGIS)
                   -> Website enrichment (Serper), booking page scraping
7. Launch          -> Hotels with all enrichments -> status=1
8. Export          -> Excel reports -> S3 -> Slack notification
```

## Tech Stack

- Python 3.9+ (async throughout)
- uv (package manager)
- PostgreSQL + PostGIS (asyncpg + aiosql, no ORM)
- Playwright + playwright-stealth
- httpx (async HTTP)
- Pydantic v2
- AWS SQS + S3
- Groq API (Llama 3.1 8B)
- Serper API (Google Maps)
- OpenStreetMap Nominatim
- Brightdata proxies (datacenter, residential, unlocker tiers)
- loguru, pytest, openpyxl

## Data Sources

1. **Serper API (Google Maps)** -- Primary hotel discovery via geographic grid ($0.001/query)
2. **Florida DBPR** -- State business licenses (~193K records)
3. **Texas Comptroller** -- Hotel occupancy tax records
4. **Common Crawl CDX API** -- Archive index for booking engine URLs
5. **Wayback Machine** -- Archive slug discovery
6. **TheGuestbook API** -- Cloudbeds partner directory (800+ hotels)
7. **Cloudbeds Sitemap** -- hotels.cloudbeds.com/sitemap.xml
8. **Cloudbeds property_info API** -- Structured hotel data
9. **RMS Cloud API** -- Hotel data with proxy support
10. **Mews Booking Engine API** -- Hotel configuration data
11. **SiteMinder GraphQL** -- Property data
12. **Groq LLM** -- Room count extraction from scraped text
13. **OpenStreetMap Nominatim** -- Geocoding

## Key Design Patterns

### Adaptive Grid Scraping

Starts with coarse 2km grid cells over a region. If a cell returns 20 results (API max), subdivide to 1km, then 500m. Skip/dedup logic for chains and non-hotels.

### HTTP Pre-check + Playwright Detection

Fast HTTP HEAD/GET first to check if website is reachable. Only launch Playwright for sites that respond. Saves expensive browser sessions.

### Reverse Lookup

Instead of find hotels -> detect engines, search Google for booking engine URLs directly:
`site:hotels.cloudbeds.com Florida`
Pre-qualified leads with known booking engine.

### Distributed Processing

Local machine handles cheap API calls (Serper scraping). EC2 workers handle expensive Playwright detection. SQS decouples them. `FOR UPDATE SKIP LOCKED` for multi-worker DB safety.

### Status-based Pipeline

Integer status codes (0=pending, 1=live, -1=error). Detection completion tracked by presence of `hotel_booking_engines` record. Separate `detection_errors` table for error classification (retriable vs permanent).

### Brightdata Proxy Integration

Three-tier proxy rotation: datacenter (cheapest) -> residential (better) -> unlocker (anti-bot bypass). Automatic failover on rate limits.

## Database Schema (Key Tables)

| Table | Purpose |
|-------|---------|
| `hotels` | Core hotel data (name, website, location, status, source) |
| `booking_engines` | Reference table of known engines |
| `hotel_booking_engines` | Junction: hotels -> detected engines |
| `hotel_room_count` | Enrichment: room counts (source, confidence) |
| `hotel_customer_proximity` | Enrichment: nearest Sadie customer |
| `existing_customers` | Current Sadie customer locations |
| `detection_errors` | Error tracking |
| `scrape_target_cities` | Cities to scrape |
| `scrape_regions` | PostGIS polygon regions |
| `jobs` | Job execution tracking |

## Booking Engines Tracked (15+)

Cloudbeds, Mews, RMS Cloud, SiteMinder, Guesty, Little Hotelier, WebRezPro, Lodgify, Hostaway, innRoad, ResNexus, Clock PMS, eviivo, Beds24, Sirvoy, ThinkReservations

---

## Patterns Reusable in air1

### 1. Serper API Integration

sadie-gtm's Serper Maps/Places/Search integration is production-tested at $0.001/query. Can be directly adapted for LinkedIn profile discovery in air1.

### 2. Adaptive Grid / Systematic Coverage

The concept of systematic geographic subdivision could work for region-based LinkedIn company/people discovery.

### 3. Reverse Lookup via Google Dorks

Search for known URL patterns (booking engine URLs in sadie, LinkedIn company URLs in air1) to find pre-qualified leads.

### 4. BrowserPool

Managed Playwright pool with concurrent page processing, stealth mode, batch processing. air1's browser.py could adopt this for parallelizing LinkedIn operations.

### 5. Brightdata Proxy Rotation

Three-tier proxy rotation with automatic failover. Critical for LinkedIn scraping where IP rotation prevents blocks.

### 6. HTTP Pre-check Before Playwright

Fast HTTP check before launching expensive browser sessions. Could improve air1's LinkedIn profile scraping efficiency.

### 7. SQS Work Distribution

If air1 needs to scale outreach across workers, the SQS pattern is proven.

### 8. Detection Error Tracking

Separate error table with classification (retriable vs permanent) and error types. More sophisticated than logging alone.

### 9. Ingestor Registry Pattern

Pluggable data source ingestors with unified interface. Could adapt for air1 to ingest from multiple sources (LinkedIn, Apollo, SEC, CSV).

### 10. Common Crawl / Archive Discovery

Using CDX APIs to find URLs matching known patterns in web archives. Creative supplementary data source.

### 11. Status-based Pipeline with `FOR UPDATE SKIP LOCKED`

Multi-worker safe pipeline processing. Each record has a status, workers claim unclaimed records atomically.

### 12. Stealth Browser Configuration

User agent rotation, `playwright-stealth`, anti-automation-detection flags. Directly applicable to air1's LinkedIn browser sessions.
