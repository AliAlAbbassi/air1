// Popup script for managing collected companies

let companies = [];

// Load companies from storage
async function loadCompanies() {
  const result = await chrome.storage.local.get(['companies']);
  companies = result.companies || [];
  renderCompanies();
}

// Save companies to storage
async function saveCompanies() {
  await chrome.storage.local.set({ companies });
  renderCompanies();
}

// Render the company list
function renderCompanies() {
  const listEl = document.getElementById('companyList');
  const countEl = document.getElementById('companyCount');

  countEl.textContent = `${companies.length} ${companies.length === 1 ? 'company' : 'companies'}`;

  if (companies.length === 0) {
    listEl.innerHTML = '<li class="empty-state">No companies collected yet</li>';
    return;
  }

  listEl.innerHTML = companies.map((company, index) => `
    <li class="company-item">
      <span class="company-name">${company}</span>
      <button class="btn-remove" data-index="${index}">×</button>
    </li>
  `).join('');

  // Add click handlers for remove buttons
  document.querySelectorAll('.btn-remove').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const index = parseInt(e.target.getAttribute('data-index'));
      removeCompany(index);
    });
  });
}

// Remove a company from the list
function removeCompany(index) {
  companies.splice(index, 1);
  saveCompanies();
}

// Add companies to the list
function addCompanies(newCompanies) {
  const uniqueNew = newCompanies.filter(c => !companies.includes(c));
  companies.push(...uniqueNew);
  saveCompanies();
  return uniqueNew.length;
}

// Show notification
function showNotification(message, type = 'success') {
  const notification = document.getElementById('notification');
  notification.textContent = message;
  notification.className = `notification ${type}`;

  setTimeout(() => {
    notification.classList.add('hidden');
  }, 3000);
}

// Extract companies from current tab
async function extractFromPage() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (!tab.url?.includes('linkedin.com')) {
    showNotification('Please navigate to a LinkedIn page first', 'error');
    return;
  }

  // Check if debug mode is enabled
  const debugMode = document.getElementById('debugMode').checked;

  try {
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'extractCompanies',
      debug: debugMode
    });
    const extracted = response.companies || [];

    if (extracted.length === 0) {
      showNotification('No companies found on this page', 'warning');
      if (debugMode) {
        console.log('[Hodhod] No companies found. Check the page console for details.');
      }
      return;
    }

    const addedCount = addCompanies(extracted);
    const totalCount = extracted.length;
    showNotification(
      `Found ${totalCount} total, added ${addedCount} new ${addedCount === 1 ? 'company' : 'companies'}!`,
      'success'
    );

    if (debugMode) {
      console.log('[Hodhod] Extracted companies:', extracted);
      console.log('[Hodhod] Added new companies:', addedCount);
    }
  } catch (error) {
    console.error('[Hodhod] Error extracting companies:', error);
    showNotification('Error extracting companies. Try refreshing the page.', 'error');
  }
}

// Copy companies as Python array
function copyAsPythonArray() {
  if (companies.length === 0) {
    showNotification('No companies to copy', 'warning');
    return;
  }

  const pythonArray = `company_usernames=[\n    "${companies.join('",\n    "')}",\n]`;

  navigator.clipboard.writeText(pythonArray).then(() => {
    showNotification('Copied as Python array!', 'success');
  });
}

// Copy companies as simple list
function copyAsList() {
  if (companies.length === 0) {
    showNotification('No companies to copy', 'warning');
    return;
  }

  const list = companies.join('\n');

  navigator.clipboard.writeText(list).then(() => {
    showNotification('Copied as list!', 'success');
  });
}

// Clear all companies
function clearAll() {
  if (companies.length === 0) return;

  if (confirm('Are you sure you want to clear all companies?')) {
    companies = [];
    saveCompanies();
    showNotification('All companies cleared', 'success');
  }
}

// Wait for DOM to be ready before adding event listeners
document.addEventListener('DOMContentLoaded', () => {
  // Event listeners
  document.getElementById('extractBtn').addEventListener('click', extractFromPage);
  document.getElementById('clearBtn').addEventListener('click', clearAll);
  document.getElementById('copyArrayBtn').addEventListener('click', copyAsPythonArray);
  document.getElementById('copyListBtn').addEventListener('click', copyAsList);

  // Initialize
  loadCompanies();
});
