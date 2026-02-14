# Origami Agents -- Deep Dive (Product + Blog Content)

YC F24 | $2M seed | $50K MRR in 50 days | 200+ B2B customers
Founded by Finn Mallery (CEO) + Kenson Chung (CTO), San Francisco

---

## Product: 6 Core Flow Types (from rendered pages)

### 1. Account Flows (`/account-flows`)

**"Be Confident You're Targeting Your Best-Fit Accounts"**

Three sub-capabilities:

**A. Buying Moment Tracking** -- "See buying triggers as they happen"
Monitors news, funding, hiring, product launches, new hires, and any publicly available info. Example workflow:
- Find Tier 1 Accounts (CRM search)
- Find All Contacts associated
- Find Engineering Leaders (managers, directors, VPs)
- Phone Number Exists? -> Waterfall contact enrichment
- Is Extra Contact? (only add net-new)
- Sync to CRM
- Generate Outreach Email (based on templates)
- Add to Sequence (of correct rep)

**B. Expansion Tracking** -- "Never miss an upsell or partnership opportunity"
Flags when existing customers expand (new offices, acquisitions, hiring surge). Example workflow:
- Find Target Accounts
- 25% MoM GTM Growth?
- Hiring 5+ GTM Roles?
- Has Relevant Shipping Policy? (check docs for pain points)
- Find Payments Provider (click checkout to detect)
- Relevant Product Details (search page)
- Relevant Tech Stack (find integration partners)
- Hiring for Relevant Roles
- Relevant News (pricing increases, marketing campaigns, product launches)
- Find Decision Makers (operations leaders, managers+)
- Enrich Personal Phone Number (waterfall)
- CRM Sync -> Summarize Research -> Create Custom Script -> Add to Sequencer

**C. Niche Account Discovery** -- "Find the hidden accounts that fit your ICP"
Goes beyond databases. Custom research workflows using niche websites, registries, marketplaces, social feeds. Example:
- Scrape Restaurant Registries (custom scraper)
- Find GMaps Restaurants (US, 3-20 locations)
- Scrape Yelp Restaurants
- Account in CRM?
- Find Contact Owner (people enrichment)
- Find Phone Number (waterfall)
- Sync to CRM (assign to SMB rep)

### 2. People Flows (`/people-flows`)

**"Always Know Who to Reach Out To"**

Three sub-capabilities:

**A. Signal Tracking** -- "Spot the right people at the right time"
Monitors social posts, reviews, public data to detect interest/frustration/buying intent. Example (Complaining About a Competitor):
- Monitor Social Mentions (LinkedIn, X, G2, forums for competitor frustrations)
- Is Competitor Complaint? (classify sentiment + intent)
- Identify Poster Details (title, company, buying authority)
- Match To CRM
- Enrich Contact Info (verify email + phone across providers)
- Draft Personal Outreach (reference complaint, value prop, next steps)
- Assign To Rep Sequence (with context)

**B. Pre-Qualified Lead Discovery** -- "Automate the manual research behind great lists"
Find hard-to-find contacts matching qualification criteria across niche sites, job boards, directories, PDFs. Example (New 2x Founder):
- Find Recent Founders (LinkedIn bio changed to "founder" in last month)
- Check if 2-Time Founder (previous bio history)
- Check for Investors (search for investors present)
- Is B2B? (website analysis)
- Is Tech Company? (website analysis)
- Find Mobile Phone Number (waterfall)
- CRM Sync -> Add to Sequencer

**C. Proactive Contact Refresh** -- "Keep every contact accurate, automatically"
Validates, refreshes, enriches contact info directly in CRM:
- Find Tier 1 Contacts
- Still at Company? -> If no: Remove Contact, Find Relevant Contacts on LinkedIn
- Has Phone Number? -> If no: Enrich Phone Number (waterfall)
- Contact in CRM? -> Enrich Contact Information -> Add to CRM -> Add to Sequencer

### 3. CRM Flows (`/crm-flows`)

**"Don't Let Your CRM Go Stale"**

Three sub-capabilities:

**A. Automated Enrichment** -- detect duplicates, missing fields, decayed contact info
Example workflows: Auto Contact Refresh, M&A CRM Mapping, Pre-Call Research

**B. Champion Tracking** -- alert reps when key champions change jobs
Example workflow:
- Find Closed-Won Accounts
- Find Operations Managers (people search)
- Find Relevant Contacts associated with account
- Potential User? (relevant title + was part of org after closed-won date)
- Moved to ICP Company? (200+ employees)
- De-Dupe against CRM
- In CRM? -> Add Account
- Create/Draft Email (based on template + signals)
- Add to Sequence of assigned rep

**C. Pipeline Revival** -- re-surface closed-lost opportunities
Monitor signals, funding, hiring momentum. When timing shifts, rebuild context:
- Find Closed Lost Accounts
- Find Relevant Account Notes (notes, email history, closed-loss summary for timing)
- Find Extra Decision Makers (VPs of Engineering)
- Create Email Draft (data + persona templates)
- Add to Sequence

### 4. Signals (`/signals`) -- Complete List (17 signals)

| Signal | Description |
|--------|-------------|
| Started a new role | Flag new hires who fit buyer persona |
| Champion moved jobs | Track when past champions/users switch companies |
| Received a promotion | Notify when persona match gets promoted |
| Launched a new product | Product launch = new budgets/needs |
| Hiring for ICP roles | Companies hiring roles matching your ICP |
| Revisit closed lost | Revisit with full context + updated signals |
| Upsell new seats | New team members join customer account |
| Mentioned in the news | Company in relevant news/PR |
| Warm intros to partners | Mutual customers/overlapping ICPs for warm intros |
| Raised funding | **Detect SEC Form D filings before public announcements (9-70 days early)** |
| Social media post | Detect relevant social posts |
| M&A | Mergers/acquisitions (auto-update CRM) |
| New office announcement | New office/location (expansion signal) |
| Competitor's top customers | Build list of competitor's biggest public customers |
| Recent hiring spree | Rapid hiring increase relative to size |
| International expansion | New regions/markets |
| Recent layoffs | Headcount reductions |

### 5. Custom Research / Data Enrichment (`/custom-research`) -- 25 Data Points

| Data Point | Description |
|------------|-------------|
| Person visited website | Identify website visitors |
| Google Reviews | Negative reviews tied to your value prop |
| Geography | HQ and regional offices |
| Industry / Sector | Custom industry classifications |
| Headcount | Employee count and size ranges |
| Revenue | Estimated/reported annual revenue |
| PE Backed | Private equity ownership details |
| Headcount Growth | Recent growth trends |
| Team Size (by Department) | Department-level counts |
| Custom Tech Stack | Proprietary technologies on websites |
| General Tech Stack | Core tools/platforms used |
| Job Posting | Live + historical postings, hiring trends |
| New Hire | Recent hires across target departments |
| **10-K / Earnings Data** | Financial filings, earnings calls, investor disclosures |
| Email Contact | Verified emails (waterfall providers) |
| Phone Number Contact | Verified direct dials/mobile (waterfall) |
| CRM Data | Closed-lost revival, champion tracking, stale deals |
| Partner CRM | Partner data for co-sell opportunities |
| Company Websites | Custom data scraped from company sites |
| Web Search | Custom data from targeted web searches |
| Yelp | Reviews, ratings, location data |
| **SEC Form D** | Early funding disclosures (before public announcements) |
| X (Twitter) | Real-time social insights, announcements, sentiment |
| Instagram | Brand, product, engagement insights |
| Custom Data Source | Any government, marketplace, or public database (custom scraper) |

### 6. Enrichment / CRM Cleanup (`/enrichment`, `/crm-cleanup`)

**Enrichment Agent** monitors thousands of data sources:
- Job boards, LinkedIn, company websites, SEC filings, industry publications, customer reviews, social sentiment
- Contact intel: personal/mobile phones, verified emails, job titles, role changes, social profiles
- Company intel: size, tech stack, executive team, hiring patterns, funding history
- Buying signals: customer-service job postings (support stress), refund policy changes, sentiment, growth, product launches, pricing changes, tech migrations
- 40% higher conversion rates, 60% less manual research time

**CRM Cleanup Agent** operations:
- Deduplication across spellings/formats
- Format standardization (phones, addresses)
- Auto-fill missing emails from LinkedIn + sources
- Job title updates
- Relationship mapping (contacts to correct companies)
- Data quality scoring
- Outdated info detection
- 24-48 hour initial cleanup, then real-time

**Key quote:** "We used to find these manually, one by one. You just pieced it together from blog articles and PDFs. Origami found four to five times more leads, people not even on LinkedIn." -- Leland Brewster, Director of Venture Traction at Redesign Health

---

## How Their System Works (from blog content)

### Signal Detection Pipeline

1. **Signal Detection:** Proprietary scrapers + Sales Navigator APIs scan **12,000+ accounts every 2 hours** across **47 signal types**
2. **Human Review:** Analysts validate context, disqualify false positives -- **94% accuracy** on qualified leads
3. **Brief Creation:** One-slide narrative with trigger, pain hypothesis, recommended CTA, conversation hooks
4. **CRM Delivery:** Opportunities sync to HubSpot/Salesforce with owner/priority pre-populated. **Average 4.2-hour lag** from signal to delivery
5. **Feedback Loop:** Closed-won/lost data improves scoring quarterly

### Scoring Model

- Recency: **50%** weight
- Intent Strength: **30%** weight
- Account Fit: **20%** weight
- Multi-signal leads: **94% accuracy**
- Single-signal leads: only **23% accuracy**

---

## The 12 LinkedIn Buying Signals They Track

### 1. New Executive Hire (< 90 days)
- **Detection:** Sales Navigator "Changed job in last 90 days" + VP/C-level seniority
- **Action:** Detects within 24hrs, researches prior company's tech stack, delivers "Executive Ramp-Up Brief" with inherited bottlenecks and conversation starters
- **Window:** 60-120 days post-hire

### 2. Department Hiring Spree (5+ open roles in 30 days)
- **Detection:** Job posting frequency clustering by function on LinkedIn Jobs
- **Action:** Generates lead with hiring context, budget signals, ramp-time reduction hooks

### 3. Funding Round Announcement
- **Detection:** Crunchbase, TechCrunch, LinkedIn feed, press releases
- **Action:** Extracts expansion goals from press language, delivers lead 2-4 weeks post-announcement
- **Window:** 30-90 days post-announcement

### 4. Tech Stack Callouts in Job Descriptions
- **Detection:** Boolean searches for tool mentions ("Salesforce required") in LinkedIn job postings
- **Action:** Scans weekly, identifies current tools + expansion areas, suggests complementary solutions

### 5. Conference/Event RSVP
- **Detection:** LinkedIn Events attendee tabs, conference hashtag monitoring, speaker engagement
- **Action:** Pre-event guides, during-event follow-ups, post-event implementation resources

### 6. LinkedIn Live Viewer Engagement
- **Detection:** Comments, reactions, chat participation during live streams
- **Action:** Tracks active research behavior, sends resources tied to questions raised

### 7. Professional Certificate Completion Posts
- **Detection:** LinkedIn search for "certified," "completed," "earned" + tool name within past month
- **Action:** Recognizes skill development precedes tool adoption, offers implementation support within 48hrs

### 8. Vendor Recommendation Polls
- **Detection:** "looking for recommendations" or "evaluating X vs Y" posts
- **Action:** Responds via DM with case studies and neutral comparison frameworks

### 9. Executive #OpenToWork Status
- **Detection:** LinkedIn profile banner tracking for target account leaders
- **Action:** 30-60 day outreach window after new start date, delivers GTM assessment frameworks

### 10. Competitor Complaint Threads
- **Detection:** Competitor brand mentions, problem hashtags, G2/Capterra reviews
- **Action:** Non-confrontational migration case studies, cost comparisons, implementation timelines

### 11. Niche LinkedIn Group Participation
- **Detection:** New joins + active participation in high-intent groups (RevOps Professionals, SaaS Growth Hackers)
- **Action:** Builds relationship context, shares value before selling

### 12. Dark Funnel Ad Engagement (Repeat Visits)
- **Detection:** LinkedIn Insight Tag, repeat ad clicks, pricing page scrolls, IP intelligence (6sense/Demandbase)
- **Action:** Acknowledges research phase, provides pricing clarity without pressure

---

## Top 10 Sales Signals (Ranked by Conversion Impact)

| # | Signal | Conversion Lift | Detection Difficulty | Sources |
|---|--------|----------------|---------------------|---------|
| 1 | Funding announcements | 350% | Easy | Crunchbase, TechCrunch, SEC filings |
| 2 | Executive hiring | 280% | Medium | LinkedIn job changes, company announcements |
| 3 | Technology stack changes | 250% | Hard | Job postings, GitHub, BuiltWith/Wappalyzer |
| 4 | Rapid hiring growth | 220% | Easy | Career pages, LinkedIn headcount |
| 5 | Competitor dissatisfaction | 200% | Medium | Social media, G2/Capterra, forums |
| 6 | Leadership transitions | 190% | Easy | Company news, press releases, LinkedIn |
| 7 | Office expansions | 180% | Easy | Real estate news, location job posts |
| 8 | Regulatory compliance | 170% | Medium | Regulatory bodies, compliance announcements |
| 9 | Partnership announcements | 160% | Easy | Press releases, partner programs |
| 10 | Public earnings calls | 150% | Easy | Earnings transcripts, SEC filings |

### Timing Windows

- Funding: 30-90 days post-announcement
- Executive hiring: 60-120 days post-hire
- Tech stack: 90-180 days during implementation
- Leadership transitions: 90-180 days post-transition
- Office expansions: 60-120 days before opening
- Earnings calls: 30-120 days post-earnings

---

## Top 10 AI Research Workflows for Sales

1. **Funding Round Alerts** -- Monitor + auto-add funded companies to pipeline. 3-5x higher reply rates.
2. **Job Change Tracking** -- Track contacts changing roles via LinkedIn. 40-60% response rate increase.
3. **Technology Stack Monitoring** -- Track tech adoption/migration via job posts, GitHub, websites. 2-3x qualified conversations.
4. **Competitor Sentiment Analysis** -- Scan social/review sites for competitor frustration. 25-35% shorter cycles.
5. **Company Growth Signals** -- Monitor hiring velocity, expansions, acquisitions. 20-30% larger deals.
6. **Leadership Transition Tracking** -- Monitor C-suite appointments. 50-70% higher meeting acceptance.
7. **Industry News Correlation** -- Connect regulatory/market events to prospect context. 15-25% conversation quality.
8. **SEC Filing Analysis** -- Parse 10-K/10-Q for solution keywords. 30-40% better qualification.
9. **Social Media Engagement Mapping** -- Track prospect social behavior. 20-30% higher response rates.
10. **Customer Success Story Matching** -- Auto-match prospects to similar case studies. 25-35% faster POC approvals.

---

## Their Recommended AI GTM Stack (40+ Tools, 8 Categories)

### 1. Visitor Intent & Traffic Intelligence
- **Split.dev** -- AI attribution, turns AI-crawler visits into named leads
- **Warmly** -- Deanonymizes site visitors via firmographic/intent matching
- **TrafficID** -- Anonymous visits to named leads with behavior timelines
- **Clearbit Reveal** -- Enriches IP/email with firmographics
- **6sense** -- De-anonymization + external intent signals

### 2. Lead Capture & Form Conversion
- **Unbounce** -- AI landing pages, Smart Traffic optimization
- **Intercom** -- AI chatbots, qualify + route
- **Qualified** -- Conversational marketing, Salesforce integration
- **Lindy AI** -- Multi-channel chatbots (web, WhatsApp, email)
- **OptinMonster** -- AI-driven pop-up targeting

### 3. CRM & Pipeline Intelligence
- **Clari** -- Deal health scoring, real-time forecasting, risk alerts
- **Gong** -- Conversation intelligence (calls + emails)
- **People.ai** -- Auto-captures sales activities, engagement patterns
- **RevSure** -- Predictive funnel analytics
- **Affinity** -- Relationship intelligence CRM

### 4. Data Enrichment & Signal Detection
- **Origami Agents** -- Autonomous AI agents crawling news, SEC, social, regulatory
- **ZoomInfo** -- B2B database, firmographics, direct dials, intent
- **Clearbit** -- Real-time enrichment API
- **Floqer** -- 75+ data sources aggregation
- **Demandbase** -- Bombora intent + firmographics for ABM

### 5. Sales Engagement & Outreach
- **Apollo.io** -- All-in-one: 210M+ contacts, sequences (email, call, LinkedIn), AI
- **Outreach** -- Multi-step cadences, AI call coaching
- **Salesloft** -- AI-driven call summaries and next-step suggestions
- **HubSpot Sales Hub** -- Native CRM outreach + sequences
- **Regie.ai** -- GPT-4 powered sequence generator

### 6. AI SDR & Qualification Agents
- **Persana AI** -- 24/7 autonomous SDR agents (lists, emails, follow-up)
- **Conversica** -- AI Revenue Digital Assistants (email dialog nurture)
- **Exceed.ai** -- Email + chatbots with NLP objection handling
- **Salesforce Einstein GPT** -- Built-in AI SDR in Sales Cloud
- **Drift Automation** -- Conversational bots qualifying + scheduling

### 7. Forecasting & Deal Inspection
- **Clari** -- AI forecasting waterfall, deal health scores
- **BoostUp.ai** -- Revenue intelligence, win probability
- **Aviso** -- Deep learning forecasts, scenario simulation
- **Gong Forecast** -- Conversational-signal forecasting
- **Forecast.io** -- AI forecasts for HubSpot users

### 8. Marketing Automation & Personalization
- **HubSpot Marketing Hub** -- All-in-one with generative AI
- **ActiveCampaign** -- Email/SMS automation with AI content recs
- **Customer.io** -- Behavior-based multi-channel messaging
- **Marketo Engage** -- Enterprise campaign orchestration
- **Mutiny** -- No-code AI content personalization

---

## Top 10 AI Sales Agents (Their Rankings)

1. **Origami Agents** -- Custom lead research + live buying signals. Custom pricing.
2. **Clay** -- Flexible waterfall enrichment workflows. From $149/mo.
3. **Apollo.io** -- All-in-one prospecting + engagement. Freemium.
4. **ZoomInfo** -- Enterprise company/contact data. Enterprise pricing.
5. **Humantic AI** -- Personality-driven outreach (DISC profiling). From $69/mo.
6. **6sense** -- Account-level intent + ABM. Custom pricing.
7. **Cognism** -- GDPR-first phone/email data (EU focus). Quote-based.
8. **SalesIntel** -- Human-verified B2B contacts. Quote-based.
9. **Clearbit** -- Firmographic enrichment APIs. Usage-based.
10. **Seamless.ai** -- Budget-friendly contact sourcing. Tiered plans.

---

## B2B Lead Gen Strategies Without Paid Ads

1. **AI-Powered Outbound** -- Research agents discover ICP matches, enrich, personalize. 3-5x response rates.
2. **Content Marketing** -- SEO blog, LinkedIn thought leadership, webinars, newsletters.
3. **Strategic Partnerships** -- Co-market with complementary tools, warm intros, integration partnerships.
4. **Customer-Led Growth** -- Case studies, referral programs, user-generated content.
5. **SEO + Answer Engine Optimization** -- Commercial intent keywords, resource centers.
6. **Community & Events** -- Virtual roundtables, Slack communities, speaking, user conferences.
7. **Product-Led Growth** -- Free trials, self-serve onboarding, in-product virality.

### Implementation Phases
- Months 1-3: Define ICP, plan 20 content pieces, configure AI agents, identify 10 partners, SEO audit
- Months 3-6: Publish 2-3x/week, launch outbound, initiate partnerships, join 5 communities
- Months 6+: Scale winners, eliminate losers, automate, test new channels

---

## Top 10 B2B Lead Gen Strategies (2025)

1. **AI Research Agents** -- Autonomous web scanning for ICP + signals. 3-5x response rates.
2. **Intent Data + ABM** -- Third-party intent + targeted account campaigns. 50-70% shorter cycles.
3. **Social Selling 2.0** -- Systematic LinkedIn engagement with AI insights. 45-60% connection acceptance.
4. **SEO + Answer Engine Optimization** -- Content for search + AI engines. 200-400% organic traffic growth.
5. **Community-Led Growth** -- Industry communities where prospects self-identify. 60-80% higher conversion.
6. **Referral Automation** -- Systematic customer referral programs. 5-10x conversion rates.
7. **Event + Podcast Targeting** -- Target attendees/guests with timely outreach. 25-40% response rates.
8. **Video Prospecting** -- Personalized <90s videos (Loom/Vidyard). 15-25% higher response.
9. **LinkedIn Automation** -- Systematic LinkedIn outreach. 10-20% connection acceptance, 5-10% meeting conversion.
10. **Content Syndication** -- Distribute via partner networks. 100-200% reach increase.

---

## Key Data Sources They Monitor

- **SEC filings** (10-K, 10-Q, Form D, proxy statements, earnings transcripts)
- **LinkedIn** (job changes, hiring sprees, posts, groups, events, live streams, certificates, #OpenToWork)
- **Job boards** (tech stack callouts, hiring velocity, department growth)
- **Crunchbase / TechCrunch** (funding rounds, acquisitions)
- **Review sites** (G2, Capterra -- competitor sentiment)
- **Company websites** (tech stack via BuiltWith/Wappalyzer)
- **News / press releases** (partnerships, expansions, regulatory)
- **GitHub repositories** (tech stack changes)
- **Real estate announcements** (office expansions)
- **Earnings call transcripts** (strategic priorities)
- **Industry publications** (regulatory changes)
- **Social media** (engagement patterns, content consumption)

---

## Integrations

- Salesforce
- HubSpot
- Outreach
- Slack (notifications)
- Email (notifications)
- Custom CRMs via OpenAPI

---

## Key Takeaways for air1

1. **Multi-signal scoring is critical** -- single signals only 23% accurate, multi-signal hits 94%. Need to combine SEC + LinkedIn + hiring + tech stack signals.

2. **Human-in-the-loop matters** -- Origami uses analyst review to maintain quality. Pure automation has too many false positives.

3. **Timing windows are specific** -- each signal type has an optimal outreach window (30-180 days depending on type). Outreach too early or too late kills conversion.

4. **"Why now" context is the differentiator** -- not just finding leads, but delivering the *reason* to reach out with conversation hooks.

5. **47 signal types across 12,000 accounts every 2 hours** -- this is the scale/frequency to target for competitive parity.

6. **4.2-hour average signal-to-delivery** -- speed matters. First mover advantage on buying signals.

7. **SEC filing analysis for keywords** -- parsing 10-K/10-Q for solution-related keywords reveals strategic priorities. 30-40% better qualification.

8. **Certification completion posts** -- creative signal: people getting certified in a tool = their company is about to adopt it.

9. **Vendor recommendation polls** -- people asking "evaluating X vs Y" on LinkedIn are in active buying mode.

10. **The stack they recommend** is basically: Serper/Google for discovery -> Apollo/ZoomInfo for contacts -> Origami/Clay for enrichment + signals -> Outreach/Apollo for engagement. air1 can replicate this with Serper + Apollo free tier + SEC EDGAR + existing LinkedIn automation.

---

## Modern GTM Newsletter (`moderngtm.origamiagents.com`)

Hosted on Beehiiv. Interview series with sales leaders. Published interviews:

| # | Guest | Topic |
|---|-------|-------|
| 14 | Joshua Bruton | 3x Global SD Leader on leading sales teams through change |
| 13 | Reading Harmon | Scaling from 6 to 118 reps in 6 months |
| 12 | Simona Gatta | 4 lessons from running Docebo's SD org |
| 11 | Steve Waters | ZoomInfo sales leader on storytelling, tone, trust bank |
| 10 | Pete Hancock | Taking Yelp $1-750M ARR |
| 9 | Umar Farooq Adam | Hitachi Vantara's Head of GTME on global RevOps |
| 4 | Ron Halbert | Sales Development legend on timeless principles |

Tags: Enterprise Sales, Sales Development, AI x Sales, Sales Fundamentals, Team Building, Sales Leadership, Consultative Selling, Culture

---

## Full Resources Catalog (27 Articles)

### Featured / Cornerstone Content
1. **The Ultimate AI Go-to-Market Stack for 2025** -- 16 min, 3,200 words. 40+ tools across 8 categories.
2. **AI-Powered Sales Research Workflow Setup Guide for Revenue Teams 2025** -- 16 min. Step-by-step implementation.
3. **Origami Agents vs Clay for Prospecting: Complete 2025 Comparison** -- 9 min. By Luke Clancy.
4. **Real-Time Lead Scoring with Origami Agents: Complete Implementation Guide 2025** -- 14 min.
5. **Series A Startup Sales Automation Guide** -- 12 min. By Luke Clancy.
6. **AI Signal Detection vs Traditional Lead Scoring** -- claims 400% outperformance.

### Signal & Intent Content
7. **Top 10 Sales Signals to Track in 2025** -- 8 min. Ranked by conversion lift (350% for funding down to 150% for earnings).
8. **12 Enterprise-Grade LinkedIn Signals That Scream Buy Now** -- 14 min, 2,800 words. Their most detailed technical article.
9. **Why Signal-Based Prospecting Beats Lead Lists Every Time** -- 8 min. "Lead lists miss 80% of buying intent signals."

### Strategy & Workflow Content
10. **Top 10 AI Research Workflows for Sales Teams in 2025** -- 7 min. The 10 workflows with expected impact.
11. **Top 10 B2B Lead Generation Strategies That Work in 2025** -- 9 min, 1,800 words.
12. **B2B Lead Generation Strategies That Don't Rely on Paid Ads** -- 8 min. 7 organic strategies.
13. **How to Automate Lead Research Using AI Agents** -- 7 min.
14. **The Complete Guide to AI-Powered Lead Qualification in 2025** -- 11 min. "Reduces scoring from 2 hours to 2 minutes."

### Tool Comparison Content
15. **Top 10 AI Sales Agents and Prospecting Tools in 2025** -- 5 min. Rankings.
16. **Top AI Sales Prospecting Tools to Use in 2025** -- 7 min. Detailed comparison table.
17. **Top 25 AI Startups Transforming the GTM Stack in 2025** -- 5 min.

### Thought Leadership
18. **The Future of AI in Sales: Empowering Professionals, Not Replacing Them** -- 5 min. "AI as force multiplier, not substitute."
19. **What is an AI Go-to-Market (GTM) Engineer?** -- 17 min. Longest article. Defines the emerging role.
20. **What Are AI Research Agents? Complete Definition & Examples 2025** -- 10 min.
21. **How AI Research Agents Replace Manual Sales Prospecting** -- 10 min. "3-5 hours per prospect -> 15 minutes."
22. **Embracing AI GTM Engineers: Revolutionizing Sales Strategy** -- 3 min.
23. **AI Research Agents: Revolutionizing B2B Sales Prospecting** -- 4 min.

### Key Tool Mentions Across All Content

**Discovery/Intelligence:** Origami, Clay, Apollo, ZoomInfo, 6sense, Demandbase, Clearbit, Warmly, Split.dev, TrafficID
**Outreach/Engagement:** Apollo, Outreach, Salesloft, HubSpot, Regie.ai, Valley
**AI SDRs:** Persana AI, Conversica, Exceed.ai, Salesforce Einstein, Drift
**Data:** ListKit, Cognism, SalesIntel, Seamless.ai, Floqer, People.ai
**Personalization:** Humantic AI (DISC profiling), Mutiny
**Forecasting:** Clari, BoostUp.ai, Aviso, Gong
**CRM:** Salesforce, HubSpot, Affinity

---

## Origami's Competitive Positioning

They position themselves against:
- **Clay** -- "Clay is DIY workflows, Origami is done-for-you with human review"
- **Apollo** -- "Apollo is database + sequences, Origami is signal intelligence"
- **ZoomInfo** -- "ZoomInfo is static data, Origami is dynamic signals"

Their differentiator is the **human-reviewed AI agent** model: agents do the research, humans validate quality (94% accuracy), then deliver as actionable briefs with "why now" context.

Price point is custom/enterprise, likely $1K-5K+/month based on volume. Not competing on price with free tools like Apollo -- competing on quality and time savings.
