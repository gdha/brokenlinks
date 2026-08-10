# brokenlinks

A Python script to detect broken links in a given URL.

## Requirements

- Python 3.10+
- [requests](https://pypi.org/project/requests/)
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)

Install dependencies:

```bash
pip install requests beautifulsoup4
```

## Usage

```
python brokenlinks.py <url> [--depth N] [--timeout SEC] [--no-same-domain]
```

### Arguments

| Argument          | Default | Description                                                      |
|-------------------|---------|------------------------------------------------------------------|
| `url`             | —       | Starting URL to check                                            |
| `--depth N`       | `2`     | Maximum crawl depth (`0` = single page only)                     |
| `--timeout SEC`   | `10`    | HTTP request timeout in seconds                                  |
| `--no-same-domain`| off     | Also follow links that lead to external domains                  |

### Examples

Check all links on a single page (no crawling):

```bash
python brokenlinks.py https://example.com --depth 0
```

Crawl up to 3 levels deep, following only same-domain links:

```bash
python brokenlinks.py https://example.com --depth 3
```

Crawl and also check external links:

```bash
python brokenlinks.py https://example.com --no-same-domain
```

## Output

Each checked URL is printed with an `OK` or `BROKEN` label and its HTTP status code:

```
OK      [200]  https://example.com/page
BROKEN  [404]  https://example.com/missing
BROKEN  [ERR]  https://example.com/timeout  (Timeout)
```

A summary is printed at the end:

```
============================================================
Total links checked : 42
Broken links found  : 2

Broken links summary:
  [404] https://example.com/missing  (found on: https://example.com/)
  [ERR] https://example.com/timeout  (found on: https://example.com/page)
```

The script exits with code `1` if any broken links are found, `0` otherwise.