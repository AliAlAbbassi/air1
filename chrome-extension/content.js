// Content script that runs on LinkedIn pages
// Extracts company usernames from various LinkedIn pages

function extractCompanyUsernames() {
  const companies = new Set();

  // Method 1: Extract from job search results
  // Pattern: /jobs/view/{jobId}/?..company={companyUsername}
  const jobLinks = document.querySelectorAll('a[href*="/jobs/"]');
  jobLinks.forEach(link => {
    const href = link.href;
    const match = href.match(/\/company\/([^/?]+)/);
    if (match) {
      companies.add(match[1]);
    }
  });

  // Method 2: Extract from company links in search results
  // Pattern: /company/{username}
  const companyLinks = document.querySelectorAll('a[href*="/company/"]');
  companyLinks.forEach(link => {
    const href = link.href;
    const match = href.match(/\/company\/([^/?#]+)/);
    if (match && match[1] !== 'undefined') {
      companies.add(match[1]);
    }
  });

  // Method 3: Extract from job cards (new LinkedIn UI)
  const jobCards = document.querySelectorAll('[data-job-id]');
  jobCards.forEach(card => {
    const companyLink = card.querySelector('a[href*="/company/"]');
    if (companyLink) {
      const match = companyLink.href.match(/\/company\/([^/?#]+)/);
      if (match) {
        companies.add(match[1]);
      }
    }
  });

  // Method 4: Extract from current page if it's a company page
  const currentUrl = window.location.href;
  const currentMatch = currentUrl.match(/\/company\/([^/?#]+)/);
  if (currentMatch) {
    companies.add(currentMatch[1]);
  }

  // Method 5: Extract from "About this company" sections
  const aboutSections = document.querySelectorAll('[data-entity-urn*="company"]');
  aboutSections.forEach(section => {
    const urn = section.getAttribute('data-entity-urn');
    const match = urn?.match(/company:(\d+)/);
    if (match) {
      // Try to find the company link to get the username
      const link = section.querySelector('a[href*="/company/"]');
      if (link) {
        const usernameMatch = link.href.match(/\/company\/([^/?#]+)/);
        if (usernameMatch) {
          companies.add(usernameMatch[1]);
        }
      }
    }
  });

  return Array.from(companies);
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extractCompanies') {
    const companies = extractCompanyUsernames();
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
