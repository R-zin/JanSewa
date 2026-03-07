/**
 * Background Service Worker for Government Services Assistant Extension
 */

// Listen for extension installation
chrome.runtime.onInstalled.addListener(() => {
  console.log('Government Services Assistant Extension installed');
});

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'syncProgress') {
    syncProgressWithBackend(request.data)
      .then(result => sendResponse({ success: true, result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }
  
  if (request.action === 'getWorkflow') {
    fetchWorkflow(request.workflowId)
      .then(workflow => sendResponse({ success: true, workflow }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }
});

// Sync progress with backend
async function syncProgressWithBackend(data) {
  try {
    const response = await fetch('http://localhost:8000/api/v1/extension/progress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    return await response.json();
  } catch (error) {
    console.error('Error syncing progress:', error);
    throw error;
  }
}

// Fetch workflow from backend
async function fetchWorkflow(workflowId) {
  try {
    const response = await fetch(`http://localhost:8000/api/v1/workflows/${workflowId}`);
    return await response.json();
  } catch (error) {
    console.error('Error fetching workflow:', error);
    throw error;
  }
}

// Listen for tab updates to detect page changes
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    // Check if on supported portal
    const supportedPortals = [
      'myaadhaar.uidai.gov.in',
      'onlineservices.nsdl.com',
      'parivahan.gov.in',
      'voters.eci.gov.in',
      'edistrict.gov.in'
    ];
    
    const isSupported = supportedPortals.some(portal => tab.url.includes(portal));
    
    if (isSupported) {
      // Inject content script if not already injected
      chrome.scripting.executeScript({
        target: { tabId: tabId },
        files: ['content.js']
      });
    }
  }
});
