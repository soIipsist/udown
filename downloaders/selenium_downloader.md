# Selenium Downloader

A lightweight event-driven Selenium downloader/scraper with support for:

- Multiple browsers (`chrome`, `firefox`, `edge`, `safari`, `uc`)
- Proxies and custom user agents
- Automated downloads
- Screenshots
- DOM extraction
- JavaScript execution
- Cookie handling
- Structured scraping workflows using simple event strings

---

# Basic Usage

```bash
python selenium_downloader.py "https://example.com" \
  -e "sleep(2)" \
     "btn=xpath(//button)" \
     "click(btn)" \
     "extract(output.html)"
```

---

# Event System

The downloader works by executing a sequence of **events**.

Each event is a string formatted like:

```text
variable=action(arguments)
```

Example:

```text
search=id(search)
type(search,hello world)
submit(search)
```

Variables can store outputs from previous actions and reuse them later.

---

# Core Selenium Actions

## Open a Page

```text
get(https://example.com)
```

Opens a URL in the browser.

---

## Find Elements

### XPath

```text
btn=xpath(//button)
```

### CSS Selector

```text
item=selector(.download-btn)
```

### ID

```text
search=id(search-input)
```

### Class Name

```text
rows=class_name(table-row)
```

### Link Text

```text
link=link_text(Download)
```

---

# Interacting With Elements

## Click

```text
click(btn)
```

Clicks a previously stored element.

---

## Type / Send Keys

```text
type(search,hello world)
```

or

```text
keys(search,hello world)
```

Types text into an input field.

---

## Clear Input

```text
clear(search)
```

Clears an input element.

---

## Submit Form

```text
submit(search)
```

Submits a form/input element.

---

# Waiting & Timing

## Sleep

```text
sleep(5)
```

Hard delay in seconds.

---

## Implicit Wait

```text
wait(10)
```

Sets Selenium implicit wait timeout.

---

## Explicit Wait

```text
explicit_wait(10,presence_of_element_located,[id,results])
```

Waits for a specific condition.

---

# Extracting Data

## Extract Single Element

```text
extract(//title,,xpath,output.txt)
```

Extracts text from a single element.

---

## Extract Multiple Elements

```text
extract_all(.item-text,,css selector,items.json)
```

Extracts multiple matching elements.

---

## Structured Extraction

```text
extract_structured(.title,titles,,css selector,data.json)
```

Creates structured JSON output.

---

# Screenshots

```text
screenshot(page.png)
```

Saves a screenshot to the output directory.

---

# Execute JavaScript

```text
js(alert('hello'))
```

You can also pass a `.js` file path.

---

# Cookies

## Add Cookies

```text
add_cookies([{'name':'token','value':'123'}])
```

## Read Cookies

```text
cookies()
```

## Delete Cookies

```text
delete_cookies()
```

---

# Select Dropdowns

## Select Option

```text
select(country,2)
```

Selects by index.

---

## Deselect

```text
deselect(country)
```

---

# Drag and Drop

```text
dnd(source,target)
```

Drags one element onto another.

---

# Save Page Source

```text
save(page.html)
```

Saves the current page HTML.

---

# Example Workflow

```bash
python selenium_downloader.py "https://example.com/login" \
  -e "user=id(username)" \
     "pass=id(password)" \
     "type(user,myuser)" \
     "type(pass,mypass)" \
     "submit(pass)" \
     "sleep(3)" \
     "screenshot(logged_in.png)" \
     "extract_all(.title,,css selector,titles.json)"
```

---

# Browser Configuration

Supports:

- Chrome
- Firefox
- Edge
- Safari
- Internet Explorer
- Undetected Chrome (`uc`)

Browser options can be loaded from JSON config files.

Example:

```json
{
  "browser_type": "chrome",
  "browser_options": {
    "arguments": [
      "--headless",
      "--disable-gpu"
    ]
  }
}
```

---

# Features

- Event-driven automation
- Download automation
- File extraction
- Screenshot capture
- Proxy support
- User-Agent spoofing
- Cookie management
- JavaScript execution
- Structured scraping

---

# Output

Most extraction actions generate output files inside the configured output directory:

- `.html`
- `.json`
- `.txt`
- `.png`

Each event also returns structured metadata:

```json
{
  "url": "https://example.com",
  "status": 0,
  "progress": "100%",
  "output_filename": "output.json",
  "path": "/downloads/output.json"
}
```