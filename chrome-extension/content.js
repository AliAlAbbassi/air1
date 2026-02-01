// Content script that runs on LinkedIn pages
// Extracts company usernames from various LinkedIn pages

function extractCompanyUsernames(debug = false) {
  const companies = new Set();
  const log = debug ? console.log.bind(console, '[Hodhod]') : () => {};

  log('Starting extraction...');

  // Method 1: Extract ALL links with /company/ in href
  const allLinks = document.querySelectorAll('a[href*="/company/"]');
  log(`Found ${allLinks.length} links with /company/`);

  allLinks.forEach(link => {
    const href = link.href;
    // Match pattern: https://www.linkedin.com/company/{username}
    // Exclude tracking params and fragments
    const match = href.match(/\/company\/([^/?#]+)/);
    if (match && match[1] && match[1] !== 'undefined') {
      companies.add(match[1]);
      log(`Extracted from link: ${match[1]}`);
    }
  });

  // Method 2: Extract from job cards (multiple selector patterns for different LinkedIn UIs)
  const jobCardSelectors = [
    '[data-job-id]',
    '.job-card-container',
    '.jobs-search-results__list-item',
    '.scaffold-layout__list-item',
    'li.jobs-search-results__list-item',
  ];

  jobCardSelectors.forEach(selector => {
    const jobCards = document.querySelectorAll(selector);
    log(`Selector "${selector}" found ${jobCards.length} job cards`);

    jobCards.forEach(card => {
      // Try multiple ways to find company link within the card
      const companyLink =
        card.querySelector('a[href*="/company/"]') ||
        card.querySelector('.job-card-container__company-name a') ||
        card.querySelector('[data-tracking-control-name*="company"] a');

      if (companyLink && companyLink.href) {
        const match = companyLink.href.match(/\/company\/([^/?#]+)/);
        if (match && match[1]) {
          companies.add(match[1]);
          log(`Extracted from job card: ${match[1]}`);
        }
      }
    });
  });

  // Method 3: Extract from company search results
  const companyResultSelectors = [
    '.reusable-search__result-container',
    '.entity-result',
    '.search-result__wrapper',
  ];

  companyResultSelectors.forEach(selector => {
    const results = document.querySelectorAll(selector);
    log(`Selector "${selector}" found ${results.length} search results`);

    results.forEach(result => {
      const companyLink = result.querySelector('a[href*="/company/"]');
      if (companyLink) {
        const match = companyLink.href.match(/\/company\/([^/?#]+)/);
        if (match && match[1]) {
          companies.add(match[1]);
          log(`Extracted from search result: ${match[1]}`);
        }
      }
    });
  });

  // Method 4: Extract from current page if it's a company page
  const currentUrl = window.location.href;
  const currentMatch = currentUrl.match(/\/company\/([^/?#]+)/);
  if (currentMatch) {
    companies.add(currentMatch[1]);
    log(`Extracted from current URL: ${currentMatch[1]}`);
  }

  // Method 5: Extract from company name elements (job search specific)
  const companyNameSelectors = [
    '.job-card-container__primary-description',
    '.artdeco-entity-lockup__subtitle',
    'a.app-aware-link[href*="/company/"]',
  ];

  companyNameSelectors.forEach(selector => {
    const elements = document.querySelectorAll(selector);
    log(`Selector "${selector}" found ${elements.length} company name elements`);

    elements.forEach(el => {
      const link = el.tagName === 'A' ? el : el.querySelector('a[href*="/company/"]');
      if (link && link.href) {
        const match = link.href.match(/\/company\/([^/?#]+)/);
        if (match && match[1]) {
          companies.add(match[1]);
          log(`Extracted from company name: ${match[1]}`);
        }
      }
    });
  });

  // Method 6: Deep search in all text content for company URLs (last resort)
  // This catches companies in JSON/data attributes
  const bodyText = document.body.innerHTML;
  const urlMatches = bodyText.matchAll(/\/company\/([a-zA-Z0-9_-]+)(?=[\/?"#])/g);
  for (const match of urlMatches) {
    if (match[1] && match[1] !== 'undefined' && match[1].length > 2) {
      companies.add(match[1]);
    }
  }

  const result = Array.from(companies);
  log(`Total unique companies found: ${result.length}`);
  log('Companies:', result);

  return result;
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extractCompanies') {
    const debug = request.debug || false;
    const companies = extractCompanyUsernames(debug);
    sendResponse({ companies });
  }
  return true; // Keep the message channel open for async response
});

// Add visual indicator when hovering over company links
document.addEventListener('mouseover', (e) => {
  const target = e.target.closest('a[href*="/company/"]');
  if (target) {
    const match = target.href.match(/\/company\/([^/?#]+)/);
    if (match) {
      target.setAttribute('title', `Company: ${match[1]}`);
    }
  }
});
