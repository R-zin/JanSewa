/**
 * Popup Script for Government Services Assistant Extension
 */

// Load settings when popup opens
document.addEventListener('DOMContentLoaded', async () => {
  // Load saved settings
  const settings = await chrome.storage.sync.get(['guidanceEnabled', 'autofillEnabled']);
  
  document.getElementById('guidance-toggle').checked = settings.guidanceEnabled !== false;
  document.getElementById('autofill-toggle').checked = settings.autofillEnabled !== false;
  
  // Check current tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  updatePortalStatus(tab.url);
  
  // Add event listeners
  document.getElementById('guidance-toggle').addEventListener('change', handleGuidanceToggle);
  document.getElementById('autofill-toggle').addEventListener('change', handleAutofillToggle);
  document.getElementById('open-dashboard').addEventListener('click', openDashboard);
  document.getElementById('help-link').addEventListener('click', openHelp);
});

// Update portal status
function updatePortalStatus(url) {
  const portalName = document.getElementById('portal-name');
  const guidanceStatus = document.getElementById('guidance-status');
  
  const portals = {
    'myaadhaar.uidai.gov.in': 'UIDAI Aadhaar',
    'onlineservices.nsdl.com': 'NSDL PAN',
    'parivahan.gov.in': 'Parivahan',
    'voters.eci.gov.in': 'ECI Voter',
    'edistrict.gov.in': 'e-District',
    'crsorgi.gov.in': 'CRS'
  };
  
  let detected = false;
  for (const [domain, name] of Object.entries(portals)) {
    if (url && url.includes(domain)) {
      portalName.textContent = name;
      guidanceStatus.textContent = 'Active';
      guidanceStatus.style.color = '#10b981';
      detected = true;
      break;
    }
  }
  
  if (!detected) {
    portalName.textContent = 'Not detected';
    guidanceStatus.textContent = 'Inactive';
    guidanceStatus.style.color = '#6b7280';
  }
}

// Handle guidance toggle
async function handleGuidanceToggle(event) {
  const enabled = event.target.checked;
  
  await chrome.storage.sync.set({ guidanceEnabled: enabled });
  
  // Send message to content script
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  chrome.tabs.sendMessage(tab.id, {
    action: 'toggleGuidance',
    enabled: enabled
  });
}

// Handle autofill toggle
async function handleAutofillToggle(event) {
  const enabled = event.target.checked;
  
  await chrome.storage.sync.set({ autofillEnabled: enabled });
  
  // Send message to content script
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  chrome.tabs.sendMessage(tab.id, {
    action: 'toggleAutofill',
    enabled: enabled
  });
}

// Open dashboard
function openDashboard() {
  chrome.tabs.create({ url: 'http://localhost:3000/dashboard' });
}

// Open help
function openHelp(event) {
  event.preventDefault();
  chrome.tabs.create({ url: 'http://localhost:3000/help' });
}
