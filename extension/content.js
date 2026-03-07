/**
 * Content Script for Government Services Assistant Extension
 * Provides step-by-step guidance on government portals
 */

let guidancePanel = null;
let currentWorkflow = null;
let currentStep = 0;

// Initialize extension on supported portals
function initializeExtension() {
  const hostname = window.location.hostname;
  
  // Check if on supported portal
  const supportedPortals = [
    'myaadhaar.uidai.gov.in',
    'onlineservices.nsdl.com',
    'parivahan.gov.in',
    'voters.eci.gov.in',
    'edistrict.gov.in',
    'crsorgi.gov.in',
    'passportindia.gov.in'
  ];
  
  if (supportedPortals.some(portal => hostname.includes(portal))) {
    createGuidancePanel();
    loadWorkflow();
  }
}

// Create floating guidance panel
function createGuidancePanel() {
  if (guidancePanel) return;
  
  guidancePanel = document.createElement('div');
  guidancePanel.id = 'gov-services-guidance-panel';
  guidancePanel.innerHTML = `
    <div class="guidance-header">
      <h3>Government Services Assistant</h3>
      <button id="toggle-guidance">−</button>
    </div>
    <div class="guidance-content">
      <div id="step-instructions"></div>
      <div id="field-checklist"></div>
      <div class="guidance-controls">
        <button id="prev-step">Previous</button>
        <button id="next-step">Next Step</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(guidancePanel);
  
  // Add event listeners
  document.getElementById('toggle-guidance').addEventListener('click', togglePanel);
  document.getElementById('prev-step').addEventListener('click', previousStep);
  document.getElementById('next-step').addEventListener('click', nextStep);
}

// Load workflow from backend
async function loadWorkflow() {
  try {
    // Get workflow based on current portal
    const hostname = window.location.hostname;
    const pathname = window.location.pathname;
    
    // Determine workflow ID based on URL
    let workflowId = detectWorkflowFromUrl(hostname, pathname);
    
    if (!workflowId) return;
    
    // Fetch workflow from backend
    const response = await fetch(`http://localhost:8000/api/v1/workflows/${workflowId}`);
    currentWorkflow = await response.json();
    
    // Display first step
    displayStep(0);
  } catch (error) {
    console.error('Error loading workflow:', error);
  }
}

// Detect workflow from URL
function detectWorkflowFromUrl(hostname, pathname) {
  if (hostname.includes('myaadhaar.uidai.gov.in')) {
    if (pathname.includes('update-name')) return 'aadhaar_name_change';
    if (pathname.includes('update-address')) return 'aadhaar_address_update';
    if (pathname.includes('update-mobile')) return 'aadhaar_mobile_update';
  }
  
  if (hostname.includes('onlineservices.nsdl.com')) {
    if (pathname.includes('correction')) return 'pan_correction';
  }
  
  if (hostname.includes('parivahan.gov.in')) {
    if (pathname.includes('renewal')) return 'dl_renewal';
  }
  
  return null;
}

// Display step instructions
function displayStep(stepNumber) {
  if (!currentWorkflow || stepNumber >= currentWorkflow.steps.length) return;
  
  currentStep = stepNumber;
  const step = currentWorkflow.steps[stepNumber];
  
  const instructionsDiv = document.getElementById('step-instructions');
  instructionsDiv.innerHTML = `
    <div class="step-header">
      <span class="step-number">Step ${step.step_number} of ${currentWorkflow.steps.length}</span>
      <h4>${step.name}</h4>
    </div>
    <p class="step-description">${step.description}</p>
    <div class="step-progress">
      <div class="progress-bar" style="width: ${(stepNumber / currentWorkflow.steps.length) * 100}%"></div>
    </div>
  `;
  
  // Highlight expected fields
  highlightFields(step.expected_elements);
  
  // Show field checklist
  displayFieldChecklist(step);
}

// Highlight form fields
function highlightFields(fieldIds) {
  // Remove previous highlights
  document.querySelectorAll('.gov-services-highlight').forEach(el => {
    el.classList.remove('gov-services-highlight');
  });
  
  // Add highlights to expected fields
  fieldIds.forEach(fieldId => {
    const element = document.getElementById(fieldId) || 
                    document.querySelector(`[name="${fieldId}"]`);
    
    if (element) {
      element.classList.add('gov-services-highlight');
      
      // Add tooltip
      const tooltip = document.createElement('div');
      tooltip.className = 'gov-services-tooltip';
      tooltip.textContent = 'Fill this field';
      element.parentElement.appendChild(tooltip);
    }
  });
}

// Display field checklist
function displayFieldChecklist(step) {
  const checklistDiv = document.getElementById('field-checklist');
  
  if (!step.actions || step.actions.length === 0) {
    checklistDiv.innerHTML = '';
    return;
  }
  
  const items = step.actions
    .filter(action => action.type === 'fill_field' || action.type === 'upload_document')
    .map(action => {
      const fieldName = action.field_name || action.field_id;
      const isCompleted = checkFieldCompleted(action.field_id);
      
      return `
        <div class="checklist-item ${isCompleted ? 'completed' : ''}">
          <input type="checkbox" ${isCompleted ? 'checked' : ''} disabled>
          <span>${fieldName}</span>
        </div>
      `;
    })
    .join('');
  
  checklistDiv.innerHTML = `
    <div class="checklist-header">Required Fields:</div>
    ${items}
  `;
}

// Check if field is completed
function checkFieldCompleted(fieldId) {
  const element = document.getElementById(fieldId) || 
                  document.querySelector(`[name="${fieldId}"]`);
  
  if (!element) return false;
  
  if (element.tagName === 'INPUT' && element.type === 'file') {
    return element.files && element.files.length > 0;
  }
  
  return element.value && element.value.trim() !== '';
}

// Navigation functions
function nextStep() {
  if (currentStep < currentWorkflow.steps.length - 1) {
    displayStep(currentStep + 1);
    
    // Sync progress with backend
    syncProgress();
  }
}

function previousStep() {
  if (currentStep > 0) {
    displayStep(currentStep - 1);
  }
}

function togglePanel() {
  const content = document.querySelector('.guidance-content');
  const button = document.getElementById('toggle-guidance');
  
  if (content.style.display === 'none') {
    content.style.display = 'block';
    button.textContent = '−';
  } else {
    content.style.display = 'none';
    button.textContent = '+';
  }
}

// Sync progress with backend
async function syncProgress() {
  try {
    await fetch('http://localhost:8000/api/v1/extension/progress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workflow_id: currentWorkflow.workflow_id,
        current_step: currentStep,
        url: window.location.href
      })
    });
  } catch (error) {
    console.error('Error syncing progress:', error);
  }
}

// Initialize when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeExtension);
} else {
  initializeExtension();
}

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'updateStep') {
    displayStep(request.stepNumber);
    sendResponse({ success: true });
  }
});
