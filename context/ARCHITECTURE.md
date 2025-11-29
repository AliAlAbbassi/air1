# Air1 Architecture & Context

This document provides context for AI agents working on the Air1 codebase - a multi-user B2B SaaS for LinkedIn automation and outreach.

## Product Overview

Air1 is a LinkedIn automation platform that supports:
- **B2B sellers**: Outreach to prospects, manage campaigns, send personalized messages
- **Job hunters**: Connect with recruiters, pitch themselves using sender profiles

### Core Features
- Dashboard showing: connects sent, approvals required, messages scheduled, InMails sent
- Analytics: total messages, connections accepted, replies, meetings booked
- Campaigns with programmable sequences (multi-step outreach)
- AI-powered message personalization using prospect research
- Multi-channel: LinkedIn messages, InMails, and email
- Lookalike prospect search using embeddings

## Domain Model

### Users & Their Assets

**Users** own:
- **Products** - What B2B sellers are pitching (value prop, ICP, use cases, results/testimonials)
- **Sender Profiles** - What job hunters use to pitch themselves (headline, summary, talking points)
- **Writing Styles** - Tone, example messages, instructions for AI personalization
- **Campaigns** - Outreach campaigns targeting specific prospects

### Prospects (Shared)

Prospects are LinkedIn profiles - they're shared across users, not owned by any single user.

- `user_prospect` - Tracks which users have added which prospects
- Research, scores, intent signals are all user-specific (different users may score the same prospect differently)

### Campaigns & Sequences

A **Campaign** targets a set of prospects with a defined outreach strategy:
- Links to a product (what you're selling) or sender_profile (who you are)
- Links to a writing_style (how AI writes messages)
- Contains one or more **Sequences**

A **Sequence** is a programmable series of steps:
- Step 1: Send connection request
- Step 2: Wait 3 days
- Step 3: Send follow-up message
- Step 4: Wait 5 days
- Step 5: Send InMail if no response

### Outreach Actions & Messages

**Outreach Action** = An attempt to reach a prospect (connection request, message, InMail, email)
- Can be part of a campaign/sequence or standalone (manual one-off)
- Tracks: scheduled time, execution time, status, email tracking (opens/clicks/bounces)

**Message** = The actual content sent
- Linked to an outreach action
- Supports threading via `parent_message_id`
- Direction: outbound (you sent) or inbound (they replied)

### Companies

Companies are also shared (like prospects). Used to:
- Track where prospects work (current and past roles)
- Scrape company employee lists for lead generation

## Key Business Logic

### Prospect Scoring (ICP Fit)
User-specific scores (0-100):
- `overall` - Combined ICP fit score
- `problem_intensity` - How much they need your solution
- `relevance` - How relevant your product is to them
- `likelihood_to_respond` - Engagement probability

### Intent Signals
Tracks prospect "temperature":
- 1 = cold (no engagement)
- 2 = warm (some signals)
- 3 = hot (high intent - visited pricing page, opened emails, etc.)

### Campaign Prospect Status
- 1 = pending (not started)
- 2 = in_sequence (actively being worked)
- 3 = completed (sequence finished)
- 4 = replied (got a response)
- 5 = opted_out (unsubscribed/declined)

### Outreach Status Flow
scheduled → pending_approval → sent → delivered → opened → clicked → replied/accepted/meeting_booked

Or failure paths: bounced, declined, no_response, not_interested, failed, rate_limited

## LinkedIn Automation

### Rate Limits (per day)
- Connection requests: 25
- Messages: 40
- InMails: 20

### Anti-Detection
- Random 5-15 second delays between profile visits
- Random 2-5 second delays when paginating results
- Human-like behavior patterns

### Channels
- `linkedin_message` - Direct message (requires connection)
- `linkedin_inmail` - InMail (can reach non-connections, costs credits)
- `email` - Traditional email via Resend

## AI Features

### Lookalike Search
Find prospects similar to your best customers using vector embeddings on prospect bios.

### Deep Research
AI agents research prospects and store findings:
- LinkedIn activity analysis (recent posts, engagement patterns, topics of interest)
- Company news (funding rounds, product launches, job postings)
- Talking points (AI-generated conversation starters)
- Pain points (inferred challenges based on role/industry)

Implementation: LangGraph agents with multiple research specialists per prospect.

### Voice Cloning
Clone user's writing style for authentic message generation that sounds like them, not generic AI.

Implementation: Fish Audio API (6x cheaper than ElevenLabs, best-in-class quality).

### Message Personalization
AI generates personalized messages using:
- Prospect research
- Product/sender profile info
- Writing style preferences
- Voice cloning for authentic tone

## Outreach Strategies

### 1. Retargeting (Warm Outreach)
The holy grail - reach out to prospects already showing intent:
- **Website visitors** - De-anonymize and identify who's browsing your site
- **Content engagers** - People who liked/commented on your posts
- **Email openers** - Prospects who engaged with previous emails
- **Ad clickers** - Retarget people who clicked your ads

Intent signals to track:
- Pricing page visits (high intent)
- Multiple page views (researching)
- Return visits (considering)
- Specific feature page visits (has a problem)

Why it works: De-anonymized visitors convert 3-5x better than cold prospects.

### 2. Cold Outreach with Lead Magnets
Valid strategy for businesses without existing traffic/content:
- Target ICP-fit prospects with valuable lead magnets
- Offer something useful (guides, templates, tools, insights)
- Build relationship before pitching

Both strategies coexist - retargeting for warm leads, lead magnets for net-new prospecting.

## Competitive Insights (Valley Analysis)

Valley ($347-400/seat/month) key features worth noting:

1. **Signal-based outbound** - Focus on intent signals, not spray-and-pray
2. **Website visitor de-anonymization** - 98% of visitors leave without trace, identify them
3. **20+ research agents** - Deep prospect intelligence, not basic enrichment
4. **Voice cloning** - AI that sounds like you, not generic
5. **Intent scoring** - Signal strength, recency, and clustering

Their claimed results:
- 60% connection acceptance rate (vs ~30% typical)
- 46-71% response rates (vs 5-15% for template tools)
- 3-5x better conversion on warm vs cold prospects

Key insight: "Awareness-led outbound" - reach out when someone visits your pricing page, not randomly.
