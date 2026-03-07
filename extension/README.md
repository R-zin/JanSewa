# Government Services Assistant - Browser Extension

Chrome/Edge extension that provides step-by-step guidance for government portal navigation.

## Features

- **Automatic Activation**: Activates on supported government portals
- **Step-by-Step Guidance**: Shows current step and instructions
- **Field Highlighting**: Highlights required form fields
- **Progress Tracking**: Syncs progress with main dashboard
- **Document Checklist**: Shows required documents for each step
- **Tooltips**: Hover guidance for form fields
- **Mode Switching**: Toggle between manual and automated modes

## Supported Portals

- UIDAI Aadhaar Portal (myaadhaar.uidai.gov.in)
- NSDL PAN Services (onlineservices.nsdl.com)
- Parivahan (parivahan.gov.in)
- Election Commission (voters.eci.gov.in)
- e-District Portals (edistrict.gov.in)
- Civil Registration System (crsorgi.gov.in)
- Passport Seva (passportindia.gov.in)

## Installation

### Development Mode

1. Open Chrome/Edge and navigate to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `extension` directory

### Production Build

```bash
# Create a zip file for Chrome Web Store
cd extension
zip -r gov-services-extension.zip . -x "*.git*" "README.md"
```

## Usage

1. Navigate to a supported government portal
2. The extension will automatically activate
3. A guidance panel will appear on the right side
4. Follow the step-by-step instructions
5. Required fields will be highlighted
6. Click "Next Step" to progress through the workflow

## Configuration

The extension connects to the backend API at `http://localhost:8000` by default.

To change the API URL, edit `content.js` and update the fetch URLs.

## Permissions

- **activeTab**: Access current tab content
- **storage**: Store user preferences
- **scripting**: Inject guidance scripts
- **host_permissions**: Access supported government portals

## Architecture

### Files

- `manifest.json` - Extension configuration
- `content.js` - Content script injected into portals
- `content.css` - Styles for guidance panel
- `background.js` - Background service worker
- `popup.html` - Extension popup UI
- `popup.js` - Popup logic

### Communication Flow

1. Content script detects portal and loads workflow
2. Displays guidance panel with current step
3. Highlights required fields
4. Syncs progress with backend via background script
5. Updates dashboard in real-time

## Development

### Testing

1. Load extension in developer mode
2. Navigate to a test portal
3. Check console for errors
4. Verify guidance panel appears
5. Test step navigation

### Debugging

- Open DevTools on the portal page to debug content script
- Open DevTools on the extension popup to debug popup script
- Check `chrome://extensions/` for background script errors

## Privacy

- No data is collected by the extension
- All communication is with your own backend
- Credentials are never stored in the extension
- Progress data is synced with your dashboard only

## Troubleshooting

### Extension not activating
- Check if you're on a supported portal
- Verify backend is running
- Check browser console for errors

### Fields not highlighting
- Ensure portal HTML structure matches expected selectors
- Check if portal has updated their form IDs

### Progress not syncing
- Verify backend API is accessible
- Check network tab for failed requests
- Ensure CORS is configured correctly

## Future Enhancements

- Offline mode with cached workflows
- Custom workflow creation
- Screenshot capture for support
- Multi-language UI
- Voice command integration
- Mobile browser support
