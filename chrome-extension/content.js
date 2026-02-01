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

    jobCards.forEach((card, idx) => {
      // Try multiple ways to find company link within the card
      const companyLink =
        card.querySelector('a[href*="/company/"]') ||
        card.querySelector('.job-card-container__company-name a') ||
        card.querySelector('[data-tracking-control-name*="company"] a') ||
        card.querySelector('.artdeco-entity-lockup__subtitle a') ||
        card.querySelector('[class*="company"] a');

      if (companyLink && companyLink.href) {
        const match = companyLink.href.match(/\/company\/([^/?#]+)/);
        if (match && match[1]) {
          companies.add(match[1]);
          log(`Extracted from job card ${idx + 1}: ${match[1]}`);
        }
      } else {
        // No company link found - log for debugging
        if (debug) {
          const allLinks = card.querySelectorAll('a');
          log(`Job card ${idx + 1} has ${allLinks.length} links but no company link`);
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

  // Method 6: Deep search in all text content for company URLs (aggressive)
  // This catches companies in JSON/data attributes and any inline URLs
  const bodyText = document.body.innerHTML;

  // Pattern 1: /company/{username} with various endings
  const urlMatches = bodyText.matchAll(/linkedin\.com\/company\/([a-zA-Z0-9_-]+)/g);
  let deepSearchCount = 0;
  for (const match of urlMatches) {
    if (match[1] && match[1] !== 'undefined' && match[1].length > 2) {
      companies.add(match[1]);
      deepSearchCount++;
    }
  }
  log(`Deep search found ${deepSearchCount} additional companies`);

  // Method 7: Check data attributes and JSON blobs
  const elementsWithData = document.querySelectorAll('[data-entity-urn], [data-urn]');
  log(`Found ${elementsWithData.length} elements with data attributes`);

  elementsWithData.forEach(el => {
    const dataUrn = el.getAttribute('data-entity-urn') || el.getAttribute('data-urn') || '';
    // Extract company ID from URNs
    const companyMatch = dataUrn.match(/company[:/](\d+)/i);
    if (companyMatch) {
      // Try to find the associated company link nearby
      const nearbyLink = el.querySelector('a[href*="/company/"]') ||
                        el.closest('[data-entity-urn]')?.querySelector('a[href*="/company/"]');
      if (nearbyLink) {
        const match = nearbyLink.href.match(/\/company\/([^/?#]+)/);
        if (match && match[1]) {
          companies.add(match[1]);
          log(`Extracted from data-urn: ${match[1]}`);
        }
      }
    }
  });

  const result = Array.from(companies);
  log(`Total unique companies found: ${result.length}`);
  log('Companies:', result);

  // If we found very few companies, log a warning
  if (result.length < 5 && debug) {
    console.warn('[Hodhod] Only found', result.length, 'companies. This seems low.');
    console.warn('[Hodhod] Page URL:', window.location.href);
    console.warn('[Hodhod] Try scrolling down to load more results, then extract again.');
  }

  return result;
}

// Auto-extract from multiple pages
async function autoExtractPages(maxPages = 5, debug = false) {
  const log = debug ? console.log.bind(console, '[Hodhod Auto]') : () => {};
  const allCompanies = new Set();
  let currentPage = 1;

  while (currentPage <= maxPages) {
    log(`Extracting page ${currentPage}/${maxPages}...`);

    // Extract from current page
    const companies = extractCompanyUsernames(debug);
    companies.forEach(c => allCompanies.add(c));

    log(`Page ${currentPage} found ${companies.length} companies (${allCompanies.size} total unique)`);

    // Try to find and click the "Next" button
    const nextButton =
      document.querySelector('button[aria-label*="next" i]') ||
      document.querySelector('button[aria-label*="View next page" i]') ||
      document.querySelector('.artdeco-pagination__button--next') ||
      document.querySelector('button.jobs-search-pagination__button--next') ||
      document.querySelector('[data-test-pagination-page-btn].selected + [data-test-pagination-page-btn]');

    if (!nextButton || nextButton.disabled || nextButton.getAttribute('aria-disabled') === 'true') {
      log(`No more pages (stopped at page ${currentPage})`);
      break;
    }

    // Click next button
    log('Clicking next button...');
    nextButton.click();

    // Wait for page to load (2 seconds)
    await new Promise(resolve => setTimeout(resolve, 2000));

    currentPage++;
  }

  log(`Auto-extraction complete: ${allCompanies.size} total companies from ${currentPage} pages`);
  return Array.from(allCompanies);
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extractCompanies') {
    const debug = request.debug || false;
    const companies = extractCompanyUsernames(debug);
    sendResponse({ companies });
    return false; // Sync response
  } else if (request.action === 'autoExtractPages') {
    const debug = request.debug || false;
    const maxPages = request.maxPages || 5;

    // Run async extraction
    (async () => {
      try {
        const companies = await autoExtractPages(maxPages, debug);
        sendResponse({ companies, success: true });
      } catch (error) {
        console.error('[Hodhod] Auto-extract error:', error);
        sendResponse({ companies: [], success: false, error: error.message });
      }
    })();

    return true; // Keep message channel open for async response
  }
  return false;
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
