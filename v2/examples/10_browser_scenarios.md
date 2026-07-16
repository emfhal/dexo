# 10 Top Browser Automation Examples for Local LLMs

This document contains 10 few-shot examples for the local LLM. Each example maps a user request ("go to website x and do something y") to the exact `browser_action` JSON payload required.

## Example 1
**User**: Go to website https://news.ycombinator.com/ and extract the main body text.
**Agent Tool Call (`browser_action`)**:
```json
[
  {"action": "goto", "url": "https://news.ycombinator.com/"},
  {"action": "wait", "timeout": 2000},
  {"action": "extract_text", "selector": "table.itemlist"}
]
```

## Example 2
**User**: Go to website https://en.wikipedia.org/ and search for "Artificial Intelligence", then extract the first paragraph.
**Agent Tool Call (`browser_action`)**:
```json
[
  {"action": "goto", "url": "https://en.wikipedia.org/"},
  {"action": "fill", "selector": "input#searchInput", "value": "Artificial Intelligence"},
  {"action": "click", "selector": "button[type='submit']"},
  {"action": "wait", "timeout": 3000},
  {"action": "extract_text", "selector": "div.mw-parser-output > p:not(.mw-empty-elt)"}
]
```

## Example 3
**User**: Go to website https://www.bbc.com/, accept the cookie banner, and extract the top story.
**Agent Tool Call (`browser_action`)**:
```json
[
  {"action": "goto", "url": "https://www.bbc.com/"},
  {"action": "wait", "timeout": 2000},
  {"action": "click", "selector": "button#sp-cc-accept"},
  {"action": "wait", "timeout": 1000},
  {"action": "extract_text", "selector": "div[data-testid='top-story']"}
]
```

## Example 4
**User**: Go to website https://example.com/login and log in with username 'agent_user' and password 'secure_pass123', then extract the welcome message.
**Agent Tool Call (`browser_action`)**:
```json
[
  {"action": "goto", "url": "https://example.com/login"},
  {"action": "fill", "selector": "input[name='username']", "value": "agent_user"},
  {"action": "fill", "selector": "input[name='password']", "value": "secure_pass123"},
  {"action": "click", "selector": "button[type='submit']"},
  {"action": "wait", "timeout": 5000},
  {"action": "extract_text", "selector": ".dashboard-welcome-message"}
]
```

## Example 5
**User**: Go to website https://techcrunch.com/ and click "Load More" to get more articles, then extract the feed.
**Agent Tool Call (`browser_action`)**:
```json
[
  {"action": "goto", "url": "https://techcrunch.com/"},
  {"action": "wait", "timeout": 3000},
  {"action": "click", "selector": "button.load-more"},
  {"action": "wait", "timeout": 4000},
  {"action": "extract_text", "selector": ".river"}
]
```

## Example 6
**User**: Go to website https://example-store.com/search?q=laptops and navigate to page 2 of the results, then extract the product list.
**Agent Tool Call (`browser_action`)**:
```json
[
  {"action": "goto", "url": "https://example-store.com/search?q=laptops"},
  {"action": "wait", "timeout": 2000},
  {"action": "click", "selector": "a.pagination-next"},
  {"action": "wait", "timeout": 3000},
  {"action": "extract_text", "selector": ".product-list"}
]
```

## Example 7
**User**: Go to website https://example.com/contact and submit a message saying "Hello, this is an automated message."
**Agent Tool Call (`browser_action`)**:
```json
[
  {"action": "goto", "url": "https://example.com/contact"},
  {"action": "fill", "selector": "#name", "value": "Agent Smith"},
  {"action": "fill", "selector": "#email", "value": "agent@example.com"},
  {"action": "fill", "selector": "#message", "value": "Hello, this is an automated message."},
  {"action": "click", "selector": "#submit-btn"},
  {"action": "wait", "timeout": 2000},
  {"action": "extract_text", "selector": ".success-message"}
]
```

## Example 8
**User**: Go to website https://retail-site.com/ and close the newsletter popup before searching for "shoes".
**Agent Tool Call (`browser_action`)**:
```json
[
  {"action": "goto", "url": "https://retail-site.com/"},
  {"action": "wait", "timeout": 5000},
  {"action": "click", "selector": "button.close-modal"},
  {"action": "wait", "timeout": 1000},
  {"action": "fill", "selector": "#search-bar", "value": "shoes"},
  {"action": "click", "selector": "#search-submit"}
]
```

## Example 9
**User**: Go to website https://example.com/settings and select "dark-mode" from the dropdown.
**Agent Tool Call (`browser_action`)**:
```json
[
  {"action": "goto", "url": "https://example.com/settings"},
  {"action": "wait", "timeout": 2000},
  {"action": "click", "selector": ".dropdown-toggle"},
  {"action": "wait", "timeout": 500},
  {"action": "click", "selector": ".dropdown-menu li[data-value='dark-mode']"},
  {"action": "extract_text", "selector": ".status-indicator"}
]
```

## Example 10
**User**: Go to website https://finance.example.com/stocks and sort the table by price, then extract the data.
**Agent Tool Call (`browser_action`)**:
```json
[
  {"action": "goto", "url": "https://finance.example.com/stocks"},
  {"action": "wait", "timeout": 3000},
  {"action": "click", "selector": "th.sort-by-price"},
  {"action": "wait", "timeout": 2000},
  {"action": "extract_text", "selector": "table#stock-data tbody"}
]
```
