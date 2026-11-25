"""Text helpers. Mirrors twin-b-express/src/text.js.

The two runtimes disagree on what counts as whitespace, how strings are
lower-cased and how URLs are encoded, so both builds use these explicit
rules instead of library defaults.
"""

# ASCII whitespace only. Python's str.strip() and JavaScript's trim() differ on exotic characters.
_WS = " \t\n\r\f\v"

# Characters that are never percent-encoded in query strings we generate.
_SAFE = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.")


def clean(value):
    """Return value trimmed of ASCII whitespace; anything that is not a string becomes ''."""
    if not isinstance(value, str):
        return ""
    return value.strip(_WS)


def char_len(value):
    """Length in Unicode code points (JavaScript counts UTF-16 units, so Twin B uses [...s].length)."""
    return len(value)


def fold(value):
    """Case-fold for search (FR-07): Unicode lower-case, identical to String.prototype.toLowerCase()."""
    return value.lower()


def encode(value):
    """Percent-encode one query-string component: space -> '+', everything outside [A-Za-z0-9-_.] -> %XX."""
    out = []
    for ch in value:
        if ch in _SAFE:
            out.append(ch)
        elif ch == " ":
            out.append("+")
        else:
            out.extend("%{:02X}".format(b) for b in ch.encode("utf-8"))
    return "".join(out)


def query(pairs):
    """Build '?a=1&b=2' from (key, value) pairs, skipping empty values. Returns '' when nothing is left."""
    parts = ["{}={}".format(encode(k), encode(v)) for k, v in pairs if v != ""]
    return "?" + "&".join(parts) if parts else ""


def plural(count, singular, plural_form):
    """'1 expense' / '13 expenses'. Counts use thousands separators."""
    return "{:,} {}".format(count, singular if count == 1 else plural_form)
