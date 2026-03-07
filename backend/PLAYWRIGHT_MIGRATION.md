# Playwright Migration Guide

## Overview

Migrated browser automation from Selenium to Playwright for better performance, reliability, and modern web app support.

## Why Playwright?

### Advantages over Selenium

1. **Faster Execution**
   - Auto-waiting for elements
   - Parallel browser contexts
   - Better network handling

2. **More Reliable**
   - Built-in retry logic
   - Better handling of dynamic content
   - Fewer flaky tests

3. **Modern Features**
   - Network interception
   - Better debugging tools
   - Video recording
   - Trace viewer

4. **Better API**
   - Async/await support
   - Cleaner syntax
   - Better error messages

## Installation

```bash
# Install Playwright
pip install playwright pytest-playwright

# Install browsers
python -m playwright install chromium
```

## Usage

### Basic Example

```python
from app.services.browser_automation_playwright import playwright_automation

# Create session
session_id = playwright_automation.create_session(
    user_id="user123",
    service_id="passport",
    portal_url="https://portal.example.gov.in",
    workflow=workflow_definition
)

# Start session (async)
await playwright_automation.start_session(session_id, headless=True)

# Navigate
await playwright_automation.navigate_to(session_id, "https://example.com")

# Fill form
await playwright_automation.fill_field(
    session_id,
    selector="#username",
    value="user@example.com",
    field_name="Username"
)

# Click button
await playwright_automation.click_element(
    session_id,
    selector="button[type='submit']",
    wait_for_navigation=True
)

# Upload file
await playwright_automation.upload_file(
    session_id,
    selector="input[type='file']",
    file_path="/path/to/document.pdf"
)

# Take screenshot
await playwright_automation.take_screenshot(
    session_id,
    path="screenshot.png",
    full_page=True
)

# Close session
await playwright_automation.close_session(session_id)
```

### Advanced Features

#### Wait for Elements

```python
# Wait for element to be visible
await playwright_automation.wait_for_element(
    session_id,
    selector="#dynamic-content",
    state='visible',
    timeout=30000
)
```

#### Get Text Content

```python
text = await playwright_automation.get_text(
    session_id,
    selector=".confirmation-message"
)
```

#### Execute JavaScript

```python
result = await playwright_automation.evaluate_javascript(
    session_id,
    script="document.title"
)
```

#### Cookie Management

```python
# Get cookies
cookies = await playwright_automation.get_cookies(session_id)

# Set cookies
await playwright_automation.set_cookies(session_id, cookies)
```

## Selector Strategies

Playwright supports multiple selector strategies:

```python
# CSS selector
"#username"
".form-control"
"button[type='submit']"

# Text selector
"text=Login"
"text=/Sign in/i"

# XPath
"xpath=//button[@type='submit']"

# Data attributes
"[data-testid='login-button']"

# Chaining
"form >> input[name='username']"
```

## Best Practices

### 1. Use Auto-Waiting

Playwright automatically waits for elements to be ready:

```python
# No need for explicit waits
await page.click("button")  # Waits for button to be clickable
```

### 2. Use Specific Selectors

```python
# Good
"[data-testid='submit-button']"
"#login-form >> button[type='submit']"

# Avoid
"button"  # Too generic
".btn"    # May match multiple elements
```

### 3. Handle Errors Gracefully

```python
try:
    await playwright_automation.fill_field(session_id, "#field", "value")
except Exception as e:
    # Log error and continue
    logger.error(f"Failed to fill field: {e}")
```

### 4. Use Headless Mode in Production

```python
# Development
await playwright_automation.start_session(session_id, headless=False)

# Production
await playwright_automation.start_session(session_id, headless=True)
```

## Migration Checklist

- [x] Install Playwright and dependencies
- [x] Create new PlaywrightBrowserAutomation class
- [x] Implement core methods (navigate, fill, click, upload)
- [x] Add advanced features (screenshots, cookies, JavaScript)
- [x] Update requirements.txt
- [ ] Update API endpoints to use Playwright
- [ ] Migrate existing tests
- [ ] Update documentation
- [ ] Remove Selenium dependencies

## Performance Comparison

| Feature | Selenium | Playwright |
|---------|----------|------------|
| Page Load | 3-5s | 1-2s |
| Element Wait | Manual | Automatic |
| Parallel Execution | Limited | Excellent |
| Network Control | Basic | Advanced |
| Debugging | Basic | Excellent |

## Troubleshooting

### Browser Not Found

```bash
python -m playwright install chromium
```

### Permission Denied

```bash
chmod +x ~/.cache/ms-playwright/chromium-*/chrome-linux/chrome
```

### Timeout Errors

Increase timeout:

```python
await page.wait_for_selector(selector, timeout=60000)  # 60 seconds
```

## Resources

- [Playwright Documentation](https://playwright.dev/python/)
- [API Reference](https://playwright.dev/python/docs/api/class-playwright)
- [Best Practices](https://playwright.dev/python/docs/best-practices)
- [Debugging Guide](https://playwright.dev/python/docs/debug)

## Support

For issues or questions:
- Check Playwright documentation
- Review error logs
- Contact development team
