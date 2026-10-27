# -*- coding: utf-8 -*-
"""
Starsector PT-BR translation toolkit.

Replicates the approach of the Chinese localization project
(TruthOriginem/Starsector-Localization-CN): a whitelist map
(ref/para_tranz_map.json) says which CSV columns, lenient-JSON paths, txt
files, data/*.java literals and jar class strings are player-visible text.
Jars are first passed through jar-string-decoupler (ref/decoupled/*.jar).

Commands:
  python -X utf8 tools/sstr.py extract   -> units/*.json (unique English strings to translate)
  python -X utf8 tools/sstr.py status    -> translation progress
  python -X utf8 tools/sstr.py validate  -> placeholder checks on translations
  python -X utf8 tools/sstr.py build     -> build/ (translated starsector-core files)
"""
import codecs, csv, fnmatch, glob, hashlib, io, json, os, re, struct, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backup")  # pristine originals saved before the first install; the installed game is already translated
REF = os.path.join(ROOT, "ref")
UNITS = os.path.join(ROOT, "units")
BUILD = os.path.join(ROOT, "build")
CHUNK_WORDS = 1800
CHUNK_MAX_ITEMS = 250

# Things the user asked NOT to translate (ship and weapon names).
EXCLUDE_CSV_COLS = {
    ("data/hulls/ship_data.csv", "name"),
    ("data/weapons/weapon_data.csv", "name"),
}
EXCLUDE_JSON_PATHS = {("data/hulls/skins/*.skin", "$.hullName")}
# Columns whose value is a comma separated tag list: translate tag by tag.
TAGLIST_COLS = {("data/hullmods/hull_mods.csv", "uiTags")}
# reports.csv is not in the CN map but its text is shown in intel/comm messages.
EXTRA_CSV = [
    {"type": "csv", "path": "data/campaign/reports.csv",
     "id_column_name": ["event_type", "event_stage", "channels", "target_rel"],
     "text_column_names": ["subject", "summary", "assessment"]},
]
# rules.csv script commands whose quoted strings must stay untouched.
SCRIPT_KEEP_CMDS = {"SetShortcut", "SetPersonPortrait", "NGCAddShip", "$global.jethroName",
                    "AddPotentialContact", "SetPersonHidden"}


# ----------------------------------------------------------------- encoding
def _cp_fallback(e):
    return (bytes(e.object[e.start:e.end]).decode("cp1252", errors="replace"), e.end)


codecs.register_error("cp1252fallback", _cp_fallback)


def read_text(path):
    with open(path, "rb") as f:
        b = f.read()
    if b.startswith(codecs.BOM_UTF8):
        b = b[3:]
    return b.decode("utf-8", errors="cp1252fallback")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))


def rel(p):
    return os.path.relpath(p, GAME).replace("\\", "/")


def has_letters(s):
    return re.search(r"[A-Za-z]{2,}", s) is not None


# ----------------------------------------------------------------- unit store
class Units:
    def __init__(self):
        self.items = []  # (category, key, en, ctx)

    def add(self, cat, key, en, ctx=""):
        if en is None:
            return
        if not has_letters(en):
            return
        self.items.append((cat, key, en, ctx))


# ----------------------------------------------------------------- CSV
def csv_read(path):
    text = read_text(path)
    rows = list(csv.reader(io.StringIO(text, newline="")))
    return rows


def csv_write(path, rows):
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    for r in rows:
        w.writerow(r)
    write_text(path, buf.getvalue())


def csv_row_keys(header, rows, idcols):
    if isinstance(idcols, str):
        idcols = [idcols]
    idx = [header.index(c) for c in idcols]
    seen = {}
    keys = []
    for r in rows:
        base = "/".join((r[i] if i < len(r) else "") for i in idx)
        n = seen.get(base, 0)
        seen[base] = n + 1
        keys.append(base if n == 0 else f"{base}#{n}")
    return keys


OPTION_RE = re.compile(r"^(\s*(?:\d+:)?[^:\s]+:)(.*)$", re.S)
QUOTED_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def rules_script_literals(line):
    s = line.strip()
    if not s or s.startswith("#"):
        return []
    cmd = re.split(r'[\s"]', s, 1)[0]
    if cmd in SCRIPT_KEEP_CMDS:
        return []
    out = []
    for m in QUOTED_RE.finditer(line):
        lit = m.group(1)
        if not has_letters(lit):
            continue
        # debug output like "canScanGates = $global.canScanGates"
        if re.fullmatch(r"[\w.$]+\s*=\s*[\w.$]+", lit):
            continue
        # identifiers / ids without spaces (portrait ids, keys...)
        if " " not in lit and re.fullmatch(r"[\w.$:/-]+", lit) and not re.match(r"^[A-Z][a-z]+[.!?]*$", lit):
            continue
        out.append((m.start(1), m.end(1), lit))
    return out


def process_csv(entry, units=None, tm=None):
    """Extract (tm None) or apply translation (tm given). Returns rows when applying."""
    relpath = entry["path"]
    path = os.path.join(GAME, relpath)
    rows = csv_read(path)
    header = rows[0]
    body = rows[1:]
    keys = csv_row_keys(header, body, entry["id_column_name"])
    is_rules = relpath.endswith("rules.csv")
    for col in entry["text_column_names"]:
        if (relpath, col) in EXCLUDE_CSV_COLS or col not in header:
            continue
        ci = header.index(col)
        for rk, r in zip(keys, body):
            if ci >= len(r) or not r[ci]:
                continue
            if r[0].startswith("#"):
                continue
            val = r[ci]
            kbase = f"csv|{relpath}|{rk}|{col}"
            if is_rules and col == "options":
                lines = val.split("\n")
                for li, line in enumerate(lines):
                    m = OPTION_RE.match(line)
                    if not m:
                        continue
                    if units is not None:
                        units.add("rules", f"{kbase}|{li}", m.group(2), rk)
                    elif m.group(2) in tm:
                        lines[li] = m.group(1) + tm[m.group(2)] + ("\r" if m.group(2).endswith("\r") and not tm[m.group(2)].endswith("\r") else "")  # keep CRLF of the English option line
                if tm is not None:
                    r[ci] = "\n".join(lines)
            elif is_rules and col == "script":
                lines = val.split("\n")
                for li, line in enumerate(lines):
                    lits = rules_script_literals(line)
                    if units is not None:
                        for qi, (_, _, lit) in enumerate(lits):
                            units.add("rules", f"{kbase}|{li}|{qi}", lit, f"{rk}: {line.strip()[:120]}")
                    else:
                        for s, e, lit in reversed(lits):
                            if lit in tm:
                                rep = tm[lit] if '\\"' in lit else tm[lit].replace('"', "'")
                                line = line[:s] + rep + line[e:]
                        lines[li] = line
                if tm is not None:
                    r[ci] = "\n".join(lines)
            elif (relpath, col) in TAGLIST_COLS:
                parts = [p.strip() for p in val.split(",")]
                if units is not None:
                    for p in parts:
                        units.add("data", f"{kbase}|tag|{p}", p, "hullmod UI filter tag")
                else:
                    r[ci] = ", ".join(tm.get(p, p) for p in parts)
            else:
                cat = "rules" if is_rules else ("desc" if relpath.endswith("descriptions.csv") else "data")
                if units is not None:
                    units.add(cat, kbase, val, f"{relpath} {rk} [{col}]")
                elif val in tm:
                    r[ci] = tm[val].replace("\r\n", "\n").replace("\n", "\r\n") if "\r\n" in val else tm[val]  # Starsector CSV keeps CRLF inside quoted text
    return rows


# ----------------------------------------------------------------- lenient JSON
def json_string_tokens(text):
    """Yield (path, start, end, raw, is_key) for every string-ish token in Starsector's lenient JSON.
    start/end span the raw content (without quotes for quoted strings)."""
    i, n = 0, len(text)
    stack = []  # frames: [kind, key, index, expect_key]
    pending_key = None
    out = []

    def cur_path():
        p = []
        for fr in stack:
            if fr[0] == "o":
                if fr[1] is not None:
                    p.append(fr[1])
            else:
                p.append(fr[2])
        return p

    def value_path():
        # path for a value at current position
        return cur_path()

    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
            continue
        if c == "#" or text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "{":
            stack.append(["o", None, 0, True])
            i += 1
            continue
        if c == "[":
            stack.append(["a", None, 0, False])
            i += 1
            continue
        if c in "}]":
            if stack:
                stack.pop()
            i += 1
            if stack and stack[-1][0] == "o":
                stack[-1][1] = None
            continue
        if c == ":":
            i += 1
            if stack:
                stack[-1][3] = False
            continue
        if c == ",":
            i += 1
            if stack:
                if stack[-1][0] == "a":
                    stack[-1][2] += 1
                else:
                    stack[-1][1] = None
                    stack[-1][3] = True
            continue
        # string or bare token
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            raw, s, e = text[i + 1:j], i + 1, j
            i = j + 1
            quoted = True
        else:
            m = re.compile(r"[^,:\[\]{}\s#]+(?:[ \t]+[^,:\[\]{}\s#]+)*").match(text, i)
            if not m:
                i += 1
                continue
            raw, s, e = m.group(0), m.start(), m.end()
            i = m.end()
            quoted = False
        top = stack[-1] if stack else None
        if top is not None and top[0] == "o" and top[3]:
            top[1] = raw
            out.append((cur_path()[:-1], s, e, raw, True, quoted))
        else:
            out.append((cur_path(), s, e, raw, False, quoted))
    return out


def path_match(pattern, path, is_key):
    segs = re.findall(r"\.(\$key|\*|[^.\[]+)|(\[\*\])", pattern[1:])
    pat = [a or b for a, b in segs]
    want_key = pat and pat[-1] == "$key"
    if want_key:
        pat = pat[:-1]
        if not is_key:
            return False
    elif is_key:
        return False
    if len(pat) != len(path):
        return False
    for p, x in zip(pat, path):
        if p == "[*]":
            if not isinstance(x, int):
                return False
        elif p == "*":
            if isinstance(x, int):
                return False
        elif p != x:
            return False
    return True


def process_json_file(relpath, text_paths, excl_glob, units=None, tm=None, cat="data"):
    path = os.path.join(GAME, relpath)
    text = read_text(path)
    toks = json_string_tokens(text)
    repl = []
    for (p, s, e, raw, is_key, quoted) in toks:
        for tp in text_paths:
            if (excl_glob, tp) in EXCLUDE_JSON_PATHS:
                continue
            if path_match(tp, p, is_key):
                if not quoted and raw in ("true", "false", "null"):
                    break
                key = f"json|{relpath}|{'.'.join(map(str, p))}{'|$key' if is_key else ''}"
                if units is not None:
                    units.add(cat, key, raw, f"{relpath} {'.'.join(map(str, p))}")
                elif raw in tm:
                    t = tm[raw]
                    t = re.sub(r'(?<!\\)"', r'\\"', t)
                    repl.append((s, e, t if quoted else '"' + t + '"'))
                break
    if tm is not None:
        for s, e, t in sorted(repl, reverse=True):
            text = text[:s] + t + text[e:]
        return text


# ----------------------------------------------------------------- txt
def process_txt(relpath, units=None, tm=None):
    text = read_text(os.path.join(GAME, relpath))
    lines = text.split("\n")
    for li, line in enumerate(lines):
        body = line.rstrip("\r")
        if not body.strip() or body.lstrip().startswith("#"):
            continue
        if units is not None:
            units.add("txt", f"txt|{relpath}|{li}", body, relpath)
        elif body in tm:
            lines[li] = tm[body] + ("\r" if line.endswith("\r") else "")
    if tm is not None:
        return "\n".join(lines)


# ----------------------------------------------------------------- java sources
def norm_includes(inc):
    out = {}
    for x in inc:
        if isinstance(x, str):
            out[x] = None
        else:
            out[x["val"]] = set(x["occurs"])
    return out


def process_java(relpath, include, units=None, tm=None):
    text = read_text(os.path.join(GAME, relpath))
    inc = norm_includes(include)
    counts = {}
    repl = []
    for m in QUOTED_RE.finditer(text):
        lit = m.group(1)
        if lit not in inc:
            continue
        n = counts.get(lit, 0)
        counts[lit] = n + 1
        if inc[lit] is not None and n not in inc[lit]:
            continue
        if units is not None:
            units.add("java", f"java|{relpath}|{n}|{lit}", lit, relpath)
        elif lit in tm:
            repl.append((m.start(1), m.end(1), re.sub(r'(?<!\\)"', r'\\"', tm[lit])))
    if tm is not None:
        for s, e, t in sorted(repl, reverse=True):
            text = text[:s] + t + text[e:]
        return text


# ----------------------------------------------------------------- class files
def mutf8_decode(b):
    # Java modified UTF-8 -> str (handles C0 80 null and surrogate pairs leniently)
    b = b.replace(b"\xc0\x80", b"\x00")
    return b.decode("utf-8", errors="surrogatepass").encode("utf-16", "surrogatepass").decode("utf-16")


def mutf8_encode(s):
    out = bytearray()
    for ch in s.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "surrogatepass"):
        cp = ord(ch)
        if cp == 0:
            out += b"\xc0\x80"
        elif cp < 0x80:
            out.append(cp)
        elif cp < 0x800:
            out += bytes([0xC0 | cp >> 6, 0x80 | cp & 0x3F])
        elif cp < 0x10000:
            out += bytes([0xE0 | cp >> 12, 0x80 | (cp >> 6) & 0x3F, 0x80 | cp & 0x3F])
        else:  # encode as surrogate pair, each 3 bytes
            cp -= 0x10000
            for u in (0xD800 + (cp >> 10), 0xDC00 + (cp & 0x3FF)):
                out += bytes([0xE0 | u >> 12, 0x80 | (u >> 6) & 0x3F, 0x80 | u & 0x3F])
    return bytes(out)


class ClassFile:
    def __init__(self, data):
        self.data = data
        count = struct.unpack(">H", data[8:10])[0]
        self.entries = [None] * count  # (tag, raw bytes incl tag)
        i, k = 10, 1
        while k < count:
            t = data[i]
            if t == 1:
                ln = struct.unpack(">H", data[i + 1:i + 3])[0]
                size = 3 + ln
            elif t in (3, 4, 9, 10, 11, 12, 17, 18):
                size = 5
            elif t in (5, 6):
                size = 9
            elif t in (7, 8, 16, 19, 20):
                size = 3
            elif t == 15:
                size = 4
            else:
                raise ValueError(f"bad cp tag {t}")
            self.entries[k] = (t, data[i:i + size])
            i += size
            k += 2 if t in (5, 6) else 1
        self.pool_end = i
        self.extra = []

    def utf8(self, idx):
        return mutf8_decode(self.entries[idx][1][3:])

    def string_constants(self):
        """[(string_const_index, utf8_index)]"""
        out = []
        for k, e in enumerate(self.entries):
            if e and e[0] == 8:
                out.append((k, struct.unpack(">H", e[1][1:3])[0]))
        return out

    def occurrences(self):
        """{(text, n): [string_const_indices]} with n by ascending utf8 index (CN definition)."""
        sc = self.string_constants()
        by_utf = {}
        for si, ui in sc:
            by_utf.setdefault(ui, []).append(si)
        res = {}
        counter = {}
        for ui in sorted(by_utf):
            s = self.utf8(ui)
            n = counter.get(s, 0)
            counter[s] = n + 1
            res[(s, n)] = by_utf[ui]
        return res, counter

    def retarget(self, string_const_indices, new_text):
        idx = len(self.entries) + len(self.extra)
        b = mutf8_encode(new_text)
        if len(b) > 65535:
            raise ValueError("string too long")
        self.extra.append(b"\x01" + struct.pack(">H", len(b)) + b)
        for si in string_const_indices:
            self.entries[si] = (8, b"\x08" + struct.pack(">H", idx))

    def tobytes(self):
        count = len(self.entries) + len(self.extra)
        if count > 65535:
            raise ValueError("constant pool overflow")
        out = bytearray(self.data[:8])
        out += struct.pack(">H", count)
        for e in self.entries[1:]:
            if e is not None:
                out += e[1]
        for x in self.extra:
            out += x
        out += self.data[self.pool_end:]
        return bytes(out)


def jar_class_selection(entry):
    for cf in entry["class_files"]:
        yield cf["path"], norm_includes(cf.get("include_strings", []))


def process_jar(entry, units=None, tm=None):
    jarname = entry["path"]
    src = os.path.join(REF, "decoupled", jarname)
    zin = zipfile.ZipFile(src)
    changed = {}
    missing = 0
    for cpath, inc in jar_class_selection(entry):
        try:
            data = zin.read(cpath)
        except KeyError:
            missing += 1
            continue
        cf = ClassFile(data)
        occ, counter = cf.occurrences()
        did = False
        for s, allowed in inc.items():
            total = counter.get(s, 0)
            for n in range(total):
                if allowed is not None and n not in allowed:
                    continue
                if units is not None:
                    units.add("jar", f"jar|{jarname}|{cpath}|{n}|{s}", s, f"{jarname}:{cpath}")
                elif s in tm and tm[s] != s:
                    cf.retarget(occ[(s, n)], tm[s])
                    did = True
        if did:
            changed[cpath] = cf.tobytes()
    if missing:
        print(f"  warning: {missing} mapped classes missing in {jarname}")
    if tm is not None:
        out = os.path.join(BUILD, jarname)
        os.makedirs(BUILD, exist_ok=True)
        with zipfile.ZipFile(out, "w") as zout:
            for info in zin.infolist():
                data = changed.get(info.filename)
                if data is None:
                    data = zin.read(info.filename)
                zout.writestr(info, data, compress_type=info.compress_type)
        print(f"  {jarname}: {len(changed)} classes patched")


# ----------------------------------------------------------------- map driver
def load_map():
    with open(os.path.join(REF, "para_tranz_map.json"), encoding="utf-8") as f:
        m = json.load(f)
    return m + EXTRA_CSV


def expand_glob(pattern):
    full = os.path.join(GAME, pattern)
    return sorted(rel(p) for p in glob.glob(full, recursive=True))


def run_all(units=None, tm=None):
    written = {}
    for entry in load_map():
        t = entry["type"]
        if t == "csv":
            rows = process_csv(entry, units, tm)
            if tm is not None:
                written[entry["path"]] = ("csv", rows)
        elif t == "json":
            cat = "data"
            if "strings/" in entry["path"]:
                cat = "ui"
            for rp in expand_glob(entry["path"]):
                r = process_json_file(rp, entry["text_paths"], entry["path"], units, tm, cat)
                if tm is not None:
                    written[rp] = ("text", r)
        elif t == "txt":
            for rp in expand_glob(entry["path"]):
                r = process_txt(rp, units, tm)
                if tm is not None:
                    written[rp] = ("text", r)
        elif t == "java":
            rp = entry["path"]
            if os.path.exists(os.path.join(GAME, rp)):
                r = process_java(rp, entry["include_strings"], units, tm)
                if tm is not None:
                    written[rp] = ("text", r)
        elif t == "jar":
            process_jar(entry, units, tm)
    return written


# ----------------------------------------------------------------- commands
CAT_ORDER = ["ui", "jar", "data", "java", "desc", "txt", "rules"]


def cmd_extract():
    u = Units()
    run_all(units=u)
    # keys -> en, for reference
    os.makedirs(UNITS, exist_ok=True)
    with open(os.path.join(UNITS, "_keys.jsonl"), "w", encoding="utf-8") as f:
        for cat, key, en, ctx in u.items:
            f.write(json.dumps({"cat": cat, "k": key, "en": en}, ensure_ascii=False) + "\n")
    # unique strings, first category/context wins
    seen = {}
    for cat, key, en, ctx in sorted(u.items, key=lambda x: CAT_ORDER.index(x[0])):
        if en not in seen:
            seen[en] = (cat, ctx)
    # keep existing chunk files untouched; only add new strings
    existing = set()
    for p in glob.glob(os.path.join(UNITS, "*.en.json")):
        with open(p, encoding="utf-8") as f:
            for it in json.load(f)["items"]:
                existing.add(it["en"])
    todo = [(en, c, x) for en, (c, x) in seen.items() if en not in existing]
    nums = [int(os.path.basename(p)[:4]) for p in glob.glob(os.path.join(UNITS, "*.en.json"))]
    nxt = max(nums, default=0) + 1
    by_cat = {}
    for en, c, x in todo:
        by_cat.setdefault(c, []).append((en, x))
    made = 0
    for cat in CAT_ORDER:
        items, words = [], 0
        for en, ctx in by_cat.get(cat, []):
            items.append({"i": len(items) + 1, "en": en, "ctx": ctx})
            words += len(en.split())
            if words >= CHUNK_WORDS or len(items) >= CHUNK_MAX_ITEMS:
                _write_chunk(nxt, cat, items); nxt += 1; made += 1; items, words = [], 0
        if items:
            _write_chunk(nxt, cat, items); nxt += 1; made += 1
    tot_words = sum(len(en.split()) for en in seen)
    print(f"units: {len(u.items)}  unique strings: {len(seen)}  words: {tot_words}  new chunks: {made}")
    for cat in CAT_ORDER:
        lst = [en for en, (c, _) in seen.items() if c == cat]
        print(f"  {cat:6} strings={len(lst):6} words={sum(len(e.split()) for e in lst)}")


def _write_chunk(n, cat, items):
    p = os.path.join(UNITS, f"{n:04d}_{cat}.en.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"chunk": n, "cat": cat, "items": items}, f, ensure_ascii=False, indent=1)


def load_tm():
    tm = {}
    for p in sorted(glob.glob(os.path.join(UNITS, "*.en.json"))):
        ptp = p[:-8] + ".pt.json"
        if not os.path.exists(ptp):
            continue
        with open(p, encoding="utf-8") as f:
            items = json.load(f)["items"]
        with open(ptp, encoding="utf-8") as f:
            pt = json.load(f)
        for it in items:
            t = pt.get(str(it["i"]))
            if t is not None:
                tm[it["en"]] = t
    ov = os.path.join(UNITS, "_overrides.json")
    if os.path.exists(ov):
        with open(ov, encoding="utf-8") as f:
            tm.update(json.load(f))
    return tm


TOKEN_RES = [r"\$[A-Za-z_][\w.]*", r"%[-+0-9.,]*[sdfx%]", r"\\n", r"\\\"", r"\n"]
BRACE_RE = re.compile(r"\{([^{}]*)\}")


def brace_tokens(s):
    """Game highlight markup: {{...}}. Words are translatable and skipped; numbers and rel:key links must survive."""
    out = []
    for m in BRACE_RE.finditer(s):
        c = m.group(1)
        if c.startswith("rel:"):
            out.append("{" + c.split("|")[0] + "}")
        else:
            out += ["{" + n + "}" for n in re.findall(r"\d[\d.,]*%?", c)]
    return out


def tokens(s):
    out = []
    for r in TOKEN_RES:
        out += re.findall(r, s)
    out += brace_tokens(s)
    return sorted(out)


def or_lines(text):
    """Lines that are exactly 'OR' (rules.csv random-alternative separators) must survive translation."""
    return [ln.strip() for ln in text.split("\n") if ln.strip() == "OR"]


# Gender variables are filled by the game with English words (his/her, brother/sister, man/woman, sir/madam),
# so PT text must not use them. They are ignored in the EN token comparison; PT must not contain them.
GENDER_VARS = {"$hisorher", "$himorher", "$heorshe", "$brotherorsister", "$manorwoman", "$sirormadam",
               "$playersirormadam", "$aoran", "$onorat", "$factionisorare", "$playerbrotherorsister",
               "$himorherself", "$factionaoran", "$playerhimorher", "$playerhisorher", "$playerheorshe",
               "$entity.ttli_hisorher", "$entity.dmi_hisorher", "$entity.dmi_himorher", "$saic_heorshe", "$saic_marketonorat",
               "$gafc_kbaheorshe", "$gafc_kbahisorher", "$gavip_viphisorher", "$gaop_leaderheorshe", "$gaop_leaderhisorher", "$gaba_onorat", "$garr_onorat", "$gatj_heorshe", "$gatj_hisorher", "$gatj_himorher", "$cheapcom_manorwoman", "$procom_manorwoman", "$cheapcom_marketonorat", "$procom_marketonorat", "$cpc_manorwoman", "$cpm_manorwoman", "$dcom_manorwoman", "$psb_manorwoman", "$hmdf_hisorher", "$dcom_marketonorat", "$dcom_marketfactionarticle", "$sship_rankaoran", "$ssat_manorwoman", "$extr_manorwoman", "$extr_marketonorat", "$extr_marketfactionarticle", "$bcb_targetheorshe", "$bcb_targethimorher", "$ucb_manorwoman", "$locrlf_manorwoman", "$locrlf_heorshe", "$locrlf_hisorher", "$lpt_manorwoman", "$lpt_heorshe", "$lpt_hisorher", "$lpt_himorher", "$smug_manorwoman", "$dhi_marketonorat", "$dsp_marketonorat", "$seco_manorwoman", "$seco_heorshe", "$hijack_manorwoman", "$hijack_hisorher", "$jabr_manorwoman", "$jabr_heorshe", "$jabr_marketonorat", "$jabr_marketfactionarticle", "$ddro_manorwoman", "$ddro_aoranthing", "$sitm_aoranitem", "$fwt_itorthem", "$playerbrotherorsister", "$mcb_manorwoman"}


def is_gender(x):
    # a trailing period is part of the regex token when a sentence ends right after the variable
    return x.lower().rstrip(".") in GENDER_VARS


def strip_gender(ts):
    return [x for x in ts if not is_gender(x)]


def canon_tokens(s):
    """Comparison form: gender variables dropped; article variants '$X_aOrAnY' match the noun variable '$X_Y'."""
    return sorted(re.sub(r"_aoran", "_", x.lower()) for x in strip_gender(tokens(s)))


def cmd_validate(quiet=False):
    bad = 0
    for p in sorted(glob.glob(os.path.join(UNITS, "*.en.json"))):
        ptp = p[:-8] + ".pt.json"
        if not os.path.exists(ptp):
            continue
        with open(p, encoding="utf-8") as f:
            items = json.load(f)["items"]
        try:
            with open(ptp, encoding="utf-8") as f:
                pt = json.load(f)
        except Exception as e:
            print(f"{os.path.basename(ptp)}: INVALID JSON {e}")
            bad += 1
            continue
        for it in items:
            t = pt.get(str(it["i"]))
            if t is None:
                continue
            pt_all = tokens(t)
            leak = [x for x in pt_all if is_gender(x)]
            if leak or canon_tokens(it["en"]) != canon_tokens(t) or or_lines(it["en"]) != or_lines(t):
                bad += 1
                if not quiet:
                    extra = f"\n   gender variable in PT (game would show English): {leak}" if leak else ""
                    print(f"{os.path.basename(ptp)} #{it['i']}: tokens differ\n   EN {tokens(it['en'])}\n   PT {pt_all}{extra}")
    print(f"validate: {bad} problems")
    return bad


def cmd_status():
    tot = done = wt = wd = 0
    pending = []
    for p in sorted(glob.glob(os.path.join(UNITS, "*.en.json"))):
        with open(p, encoding="utf-8") as f:
            items = json.load(f)["items"]
        ptp = p[:-8] + ".pt.json"
        pt = {}
        if os.path.exists(ptp):
            with open(ptp, encoding="utf-8") as f:
                pt = json.load(f)
        w = sum(len(i["en"].split()) for i in items)
        d = sum(len(i["en"].split()) for i in items if str(i["i"]) in pt)
        tot += len(items); done += sum(1 for i in items if str(i["i"]) in pt); wt += w; wd += d
        if d < w:
            pending.append(os.path.basename(p))
    print(f"strings {done}/{tot}  words {wd}/{wt} ({100*wd/max(wt,1):.1f}%)  chunks pending: {len(pending)}")
    if pending:
        print("next:", ", ".join(pending[:10]))


def cmd_build():
    tm = load_tm()
    print(f"translation memory: {len(tm)} strings")
    if os.path.isdir(BUILD):
        import shutil
        shutil.rmtree(BUILD)
    written = run_all(tm=tm)
    for rp, (kind, val) in written.items():
        out = os.path.join(BUILD, rp)
        if kind == "csv":
            csv_write(out, val)
        else:
            write_text(out, val)
    print(f"build: {len(written)} data files + jars in {BUILD}")
    # fontes com letras acentuadas (tools/fontfix.py)
    import subprocess
    subprocess.run([sys.executable, "-X", "utf8", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fontfix.py")], check=True)


def cmd_show():
    """show <chunk-number>: compact listing for translating (newlines shown as ⏎)."""
    n = int(sys.argv[2])
    p = glob.glob(os.path.join(UNITS, f"{n:04d}_*.en.json"))[0]
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    print(f"== {os.path.basename(p)} ({len(d['items'])} items)")
    for it in d["items"]:
        ctx = it["ctx"]
        if d["cat"] == "jar":
            ctx = ctx.split(":")[-1].rsplit("/", 1)[-1]
        print(f"{it['i']}\t[{ctx[:70]}]\t{it['en'].replace(chr(10), '⏎')}")


def cmd_verifyjar():
    """Structural check of built jars against the decoupled originals: same entries, every patched class
    re-parses, bytes after the constant pool are identical, and only String constants were retargeted."""
    for jar in ("starfarer.api.jar", "starfarer_obf.jar"):
        a = zipfile.ZipFile(os.path.join(REF, "decoupled", jar))
        b = zipfile.ZipFile(os.path.join(BUILD, jar))
        assert a.namelist() == b.namelist(), "entry list differs"
        diff = errs = 0
        for n in a.namelist():
            x, y = a.read(n), b.read(n)
            if x == y:
                continue
            diff += 1
            try:
                ca, cb = ClassFile(x), ClassFile(y)
                assert x[ca.pool_end:] == y[cb.pool_end:]
                assert len(cb.entries) >= len(ca.entries)
                for k in range(1, len(ca.entries)):
                    ea, eb = ca.entries[k], cb.entries[k]
                    if ea != eb:
                        assert ea[0] == 8 and eb[0] == 8
                        ui = struct.unpack(">H", eb[1][1:3])[0]
                        assert cb.entries[ui][0] == 1
                        cb.utf8(ui)
            except Exception as e:
                errs += 1
                print("  BAD", n, repr(e))
        print(f"{jar}: {diff} classes changed, {errs} structural errors")


if __name__ == "__main__":
    {"extract": cmd_extract, "status": cmd_status, "validate": cmd_validate, "build": cmd_build,
     "verifyjar": cmd_verifyjar, "show": cmd_show}[sys.argv[1]]()
