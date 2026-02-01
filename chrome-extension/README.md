# 🐦 Hodhod - LinkedIn Company Collector

Chrome extension to easily collect LinkedIn company usernames for outreach campaigns.

## Features

- 📋 **Extract companies** from LinkedIn job search results, company pages, and search results
- 💾 **Persistent storage** - your collected companies are saved across browser sessions
- 📄 **Export options**:
  - Copy as Python array (ready to paste into your workflow)
  - Copy as simple list
- ✨ **Smart deduplication** - automatically removes duplicates
- 🎨 **Beautiful UI** - modern, clean interface

## Installation

### Option 1: Load Unpacked (Development)

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `chrome-extension` folder from this repository
5. The extension should now appear in your toolbar!

### Option 2: Create Icons (Optional)

The extension references icons that don't exist yet. You can either:
- Remove the icon references from `manifest.json`
- Create simple icons using any design tool
- Use placeholder icons from online

## Usage

### 1. Navigate to LinkedIn

Go to any of these LinkedIn pages:
- Job search results: `https://www.linkedin.com/jobs/search/...`
- Company search results
- Individual company pages

### 2. Extract Companies

Click the Hodhod extension icon and click **"Extract from Page"**

The extension will automatically find all company usernames on the current page.

### 3. Manage Your List

- **Remove companies**: Click the × button next to any company
- **Clear all**: Click "Clear All" to start fresh
- View count of collected companies

### 4. Export

#### Copy as Python Array
Perfect for pasting directly into your workflow:

```python
company_usernames=[
    "core-code-io",
    "arcus-search",
    "cntxtai",
]
```

#### Copy as List
Simple line-separated list:
```
core-code-io
arcus-search
cntxtai
```

## How It Works

The extension scans LinkedIn pages for company links in multiple ways:

1. **Job search results**: Extracts from job card company links
2. **Company pages**: Detects current company page URL
3. **Search results**: Finds company links in search results
4. **About sections**: Extracts from "About this company" sections

Company usernames are extracted from URLs like:
- `https://www.linkedin.com/company/{username}/`

## Tips

- Browse multiple pages of job search results to collect more companies
- The extension automatically deduplicates, so extracting from the same page multiple times is safe
- Use the Python array export to quickly update your `connect_with_company_members.py` workflow

## Example Workflow

1. Go to LinkedIn job search: `https://www.linkedin.com/jobs/search/?keywords=software`
2. Click through several pages of results
3. On each page, click Hodhod → "Extract from Page"
4. After collecting enough companies, click "Copy as Python Array"
5. Paste into your `air1/workflows/connect_with_company_members.py`
6. Run your outreach workflow!

## Troubleshooting

**"No companies found on this page"**
- Make sure you're on a LinkedIn page with company information
- Try a job search results page or company search

**"Error extracting companies"**
- Refresh the LinkedIn page and try again
- LinkedIn may have updated their HTML structure

**Extension not working**
- Make sure you're on `https://www.linkedin.com/*`
- Check that the extension has permissions for LinkedIn
- Reload the extension from `chrome://extensions/`

## Privacy

This extension:
- Only runs on LinkedIn pages
- Stores company data locally in your browser
- Does not send any data to external servers
- Does not track your browsing

## Future Enhancements

- [ ] Bulk import from CSV
- [ ] Filter companies by size/industry
- [ ] Export with company metadata (name, industry, size)
- [ ] Integration with air1 API
- [ ] Auto-extract while scrolling

## Contributing

Found a bug or have a feature request? Open an issue!
