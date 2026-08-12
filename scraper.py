import sys
import threading
from collections import OrderedDict
from urllib.parse import quote

import cloudscraper
import requests
from bs4 import BeautifulSoup
from cloudscraper.exceptions import CloudflareException

_BASE_URL = "https://tureng.com/tr/turkce-ingilizce"
_TIMEOUTS = ((4.0, 6.0), (4.0, 12.0))  # (connect, read) per attempt
_SUGGESTION_MAX = 8
_CACHE_MAX = 200

_scraper = cloudscraper.create_scraper()

_cache: OrderedDict = OrderedDict()  # casefolded word -> {"results": [...], "suggestions": [...]}
_cache_lock = threading.Lock()


class SearchError(Exception):
    """Search failed in a known way; str(e) is a user-presentable one-liner.

    The underlying technical exception is chained as __cause__.
    """


def search(word: str, on_retry=None) -> dict:
    """Look up `word`. Returns {"results": [{category, en, tr, type}, ...],
    "suggestions": [str, ...]} — suggestions are filled only when results are
    empty. Raises SearchError (only) on failure. on_retry(attempt) is invoked
    on the calling thread before each attempt after the first; exceptions from
    it are swallowed.
    """
    term = word.strip()
    key = term.casefold()
    if not key:
        return {"results": [], "suggestions": []}

    cached = _cache_get(key)
    if cached is not None:
        return cached

    # safe="" so "#" and "/" percent-encode instead of truncating/changing the route
    url = f"{_BASE_URL}/{quote(term, safe='')}"

    last_exc = None
    response = None
    for attempt, timeout in enumerate(_TIMEOUTS, start=1):
        if attempt > 1 and on_retry is not None:
            try:
                on_retry(attempt)
            except Exception:
                pass  # a UI callback must never kill the fetch
        try:
            response = _scraper.get(url, timeout=timeout)
            if response.status_code >= 500:
                # transient origin trouble; retryable like a timeout
                last_exc = requests.exceptions.HTTPError(
                    f"HTTP {response.status_code}", response=response
                )
                print(f"tureng: attempt {attempt}: HTTP {response.status_code}", file=sys.stderr)
                response = None
                continue
            response.raise_for_status()
            break
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
        ) as exc:
            # ConnectTimeout subclasses both Timeout and ConnectionError; this
            # retryable tuple must stay ahead of the RequestException net below
            last_exc = exc
            print(f"tureng: attempt {attempt}: {type(exc).__name__}: {exc}", file=sys.stderr)
        except requests.exceptions.HTTPError as exc:
            raise SearchError(_http_message(exc.response)) from exc
        except CloudflareException as exc:
            _restore_tracebacklimit()
            print(f"tureng: {type(exc).__name__}: {exc}", file=sys.stderr)
            raise SearchError(
                "Cloudflare is challenging the app right now — please try again in a minute."
            ) from exc
        except requests.exceptions.RequestException as exc:
            print(f"tureng: {type(exc).__name__}: {exc}", file=sys.stderr)
            raise SearchError("Couldn't complete the search — press Enter to retry.") from exc
    else:
        raise SearchError(_failure_message(last_exc)) from last_exc

    soup = BeautifulSoup(response.text, "html.parser")
    results = _parse_results(soup)
    payload = {
        "results": results,
        "suggestions": _parse_suggestions(soup) if not results else [],
    }
    _cache_put(key, payload)
    return {"results": list(results), "suggestions": list(payload["suggestions"])}


def warm_up() -> None:
    """Prime DNS + TCP + TLS (+ any Cloudflare clearance cookie) on the shared
    session. Best-effort: called once from a daemon thread at launch."""
    try:
        _scraper.get("https://tureng.com/robots.txt", timeout=(4.0, 6.0))
    except Exception:
        pass


def _parse_results(soup: BeautifulSoup) -> list[dict]:
    tables = soup.find_all("table", id="englishResultsTable")
    if not tables:
        return []

    results = []
    for table in tables[:2]:  # first two: direct + reverse direction
        for row in table.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) != 5:
                continue

            category = tds[1].get_text(strip=True)
            en_anchor = tds[2].find("a")
            tr_anchor = tds[3].find("a")
            type_tag = tds[2].find("i")

            if not en_anchor or not tr_anchor:
                continue

            results.append({
                "category": category,
                "en": en_anchor.get_text(strip=True),
                "tr": tr_anchor.get_text(strip=True),
                "type": type_tag.get_text(strip=True) if type_tag else "",
            })

    return results


def _parse_suggestions(soup: BeautifulSoup) -> list[str]:
    words: list[str] = []
    for anchor in soup.select("ol.suggestion-list a"):
        text = anchor.get_text(strip=True)
        if text and text not in words:
            words.append(text)
        if len(words) >= _SUGGESTION_MAX:
            break
    return words


def _cache_get(key: str) -> dict | None:
    with _cache_lock:
        payload = _cache.get(key)
        if payload is None:
            return None
        _cache.move_to_end(key)
        return {
            "results": list(payload["results"]),
            "suggestions": list(payload["suggestions"]),
        }


def _cache_put(key: str, payload: dict) -> None:
    with _cache_lock:
        _cache[key] = payload
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)


def _failure_message(exc) -> str:
    if isinstance(exc, requests.exceptions.HTTPError):
        return _http_message(exc.response)
    if isinstance(exc, requests.exceptions.ReadTimeout):
        return "Tureng didn't respond — press Enter to retry."
    if isinstance(exc, (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError)):
        return "Can't reach Tureng — check your internet connection, then press Enter to retry."
    return "Tureng didn't respond — press Enter to retry."


def _http_message(response) -> str:
    code = response.status_code if response is not None else 0
    if code == 403:
        return "Tureng is blocking automated access right now — please try again later."
    if code == 429:
        return "Too many searches — wait a moment, then press Enter."
    if code >= 500:
        return "Tureng is having trouble right now — press Enter to retry."
    return f"Tureng returned an error (HTTP {code}) — press Enter to retry."


def _restore_tracebacklimit() -> None:
    # cloudscraper's simpleException sets sys.tracebacklimit = 0 process-wide,
    # which would silence every later traceback in the app
    if getattr(sys, "tracebacklimit", None) == 0:
        del sys.tracebacklimit


if __name__ == "__main__":
    import time

    term = " ".join(sys.argv[1:]) or "merhaba"
    start = time.perf_counter()
    try:
        payload = search(term, on_retry=lambda a: print(f"...retrying (attempt {a})", file=sys.stderr))
    except SearchError as e:
        print(f"error: {e}\ncause: {e.__cause__!r}", file=sys.stderr)
        sys.exit(1)
    elapsed = time.perf_counter() - start

    for r in payload["results"][:20]:
        line = f'{r["category"]:<30} {r["en"]}  ->  {r["tr"]}'
        if r["type"]:
            line += f'  [{r["type"]}]'
        print(line)
    if not payload["results"] and payload["suggestions"]:
        print("did you mean:", ", ".join(payload["suggestions"]))
    print(f'\n{len(payload["results"])} rows in {elapsed:.3f}s')

    start = time.perf_counter()
    search(term)
    print(f"cache hit in {(time.perf_counter() - start) * 1000:.2f}ms")
