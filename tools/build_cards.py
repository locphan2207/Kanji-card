#!/usr/bin/env python3
"""Build frontend/data/ from open Japanese language data: one file per deck.

    python3 tools/build_cards.py

Every jouyou kanji, and every other kanji a JLPT source places at a level, becomes a
card, grouped into the five levels; every kana slot becomes a card, grouped by script and
by how far past the plain syllabary it sits. One file per deck, so the app downloads only
the deck you pick.

The kana half lives in build_kana.py and kana_tables.py; this file owns the sources, the
manifest, and the writing, so there is one place that knows what a deck file looks like.

Sources (all cached under tools/cache/, so reruns are offline)
  KANJIDIC2 (radical, grade, frequency, readings, meanings)  EDRDG, CC BY-SA 4.0
    via github.com/scriptin/jmdict-simplified releases
  JMdict, English (the example words on each card)           EDRDG, CC BY-SA 4.0
    via the same releases
  KanjiVG (per-stroke paths, stroke types, radical form)     CC BY-SA 3.0
    github.com/KanjiVG/kanjivg releases
  kanji-data (JLPT N5-N1 levels, WaniKani levels)            CC BY 4.0
    github.com/davidluzgouveia/kanji-data
  open-anki-jlpt-decks (the JLPT vocabulary lists)           MIT
    github.com/jamsinclair/open-anki-jlpt-decks

The JLPT has not published official kanji lists since 2010; the N5-N1 grouping is the
usual community reconstruction, not an official list, and no single reconstruction covers
every kanji a learner meets. Four sources are asked in turn instead - see kanji_levels.
"""
import csv, json, os, re, statistics, sys, unicodedata, urllib.request, zipfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_kana

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", "cache")
OUT   = os.path.join(ROOT, "frontend", "data")

JMDICT_TAG = "3.6.2+20260713141310"
KANJIVG_TAG = "r20250816"
REL = "https://github.com/scriptin/jmdict-simplified/releases/download"
SOURCES = {
    "kanjidic2.zip": f"{REL}/{JMDICT_TAG}/kanjidic2-en-{JMDICT_TAG}.json.zip",
    "jmdict.zip":    f"{REL}/{JMDICT_TAG}/jmdict-eng-{JMDICT_TAG}.json.zip",
    "kanjivg.zip":   f"https://github.com/KanjiVG/kanjivg/releases/download/{KANJIVG_TAG}"
                     f"/kanjivg-{KANJIVG_TAG[1:]}-main.zip",
    "jlpt.json":     "https://raw.githubusercontent.com/davidluzgouveia/kanji-data/master/kanji.json",
    **{f"vocab-n{n}.csv":
       f"https://raw.githubusercontent.com/jamsinclair/open-anki-jlpt-decks/main/src/n{n}.csv"
       for n in (5, 4, 3, 2, 1)},
}

JOUYOU_GRADES = (1, 2, 3, 4, 5, 6, 8)
LEVELS = [5, 4, 3, 2, 1]                       # N5 first: the deck order learners meet
# The pre-2010 levels on the new scale, from the JLPT's own note on the 2010 rewrite:
# N5 is about old 4, N4 about old 3, N2 about old 2, N1 about old 1, and N3 is the level
# that was added in between - which is why no old list ever places a kanji at N3.
OLD_LEVEL = {4: 5, 3: 4, 2: 2, 1: 1}
# Last resort, and only for jouyou kanji: the commonest JLPT level of their school grade.
GRADE_LEVEL = {1: 5, 2: 4, 3: 3, 4: 3, 5: 2, 6: 1, 8: 1}

# Radical numbers whose Kangxi form is not the shape used in Japanese.
JP_RADICAL = {63: "戸", 162: "辶", 174: "青"}

# Word forms and senses that do not belong on a study card.
BAD_FORM  = {"rK", "sK", "iK", "oK"}
BAD_SENSE = {"arch", "obs", "rare", "derog", "vulg", "X", "sl", "proverb", "quote"}
NAME_SENSE = {"place", "surname", "given", "organization", "work", "product", "person"}
# A study card wants kanji, not 9日 or CDプレーヤー.
NOT_A_WORD = re.compile(r"[0-9\uff10-\uff19A-Za-z\uff21-\uff3a\uff41-\uff5a]")
ALL_KATAKANA = re.compile(r"^[\u30a1-\u30fc]+$")
BAD_MEANING = re.compile(r"radical|\(no\.|counter for", re.I)

VOICED = dict(zip("かきくけこさしすせそたちつてとはひふへほ",
                  "がぎぐげございずぜぞだぢづでどばびぶべぼ"))
PLOSIVE = dict(zip("はひふへほ", "ぱぴぷぺぽ"))


def fetch(name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        print(f"  fetching {name}", file=sys.stderr)
        urllib.request.urlretrieve(SOURCES[name], path)
    return path


def load_json_zip(name):
    with zipfile.ZipFile(fetch(name)) as z:
        inner = next(n for n in z.namelist() if n.endswith(".json"))
        with z.open(inner) as fh:
            return json.load(fh)


def load_jlpt_vocab():
    """Which words the JLPT actually tests, and at which level. JMdict marks a word common
    or not with nothing in between, so this is the signal that decides which of a kanji's
    hundreds of compounds a learner should meet first.

    Keyed by how a word is written, which is the form a kanji card shows. The kana cards
    need it keyed by how it is read instead; that is load_jlpt_readings below."""
    levels = {}
    for n in (1, 2, 3, 4, 5):                 # easiest level wins, so read hardest first
        with open(fetch(f"vocab-n{n}.csv"), encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                expr = (row.get("expression") or "").strip()
                if expr:
                    levels[expr] = n
    return levels


def load_jlpt_readings():
    """reading -> (level, the form it is written in, the meaning the list tests it with).

    A kana card can only show a word as it is read, and a reading is usually several
    dictionary entries: あか is 赤 and 垢, かてい is 家庭 and 仮定 and 課程 and 過程.
    JMdict cannot rank its own homographs, but the JLPT lists can, because they pair each
    reading with a level and a written form - あか is 赤 at N5 and 垢 at N1. The easiest
    level's form is the one a kana card means, and it is enough to pick the right JMdict
    entry, whose glosses are ordered by prominence where the lists' are not (the lists
    gloss 甘い as "generous, sweet")."""
    out = {}
    for n in (1, 2, 3, 4, 5):                 # easiest level wins, so read hardest first
        with open(fetch(f"vocab-n{n}.csv"), encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                reading = (row.get("reading") or "").strip()
                if reading:
                    out[reading] = (n, (row.get("expression") or "").strip(),
                                    (row.get("meaning") or "").strip())
    return out


def is_kanji(ch):
    return "\u4e00" <= ch <= "\u9fff"


def kanji_levels(chars, jlpt_src, jlpt_vocab):
    """Which of the five levels each kanji belongs to, asking every source that has an
    opinion. Returns kanji -> (level, the source that placed it).

    No one list is enough. The N5-N1 kanji list everybody works from (Jonathan Waller's,
    via kanji-data) reconstructs the exam as it stood before the 2010 rewrite, so it is
    silent on 172 jouyou kanji - 誰 and 箸 and 鍵 among them, added to the jouyou set that
    same year - and silent on every kanji outside that set which a learner still meets on
    a menu. Falling back to school grade, as this used to, puts 誰 in N1.

    So four sources are asked in turn, and the first that knows a kanji places it:

      1. the N5-N1 kanji list      2,211 kanji at the level the reconstruction tests them
      2. the pre-2010 JLPT levels  4-1 read onto the new scale, from KANJIDIC2
      3. the JLPT vocabulary       the easiest level of a word written with the kanji
      4. WaniKani                  its own teaching order, 1-60, read off against (1)

    The order is the whole design. A kanji list says where a kanji is *tested*; a word
    list only says where it is *met*, and the two sit a level or two apart - 綺麗 is an N5
    word, 麗 is not an N5 kanji. Let the vocabulary outvote the lists and 1,280 kanji move
    down a deck; let it speak only where no list does and it places 誰 at N5, 箸 at N5 and
    頃 at N4, which is where a learner actually meets them. WaniKani comes last because it
    is not teaching to the exam at all, and it shows: where both speak it agrees with the
    vocabulary on a third of the kanji and calls the rest N1.
    """
    levels = {}
    for ch, e in jlpt_src.items():                           # 1. the N5-N1 kanji list
        if e.get("jlpt_new"):
            levels[ch] = (e["jlpt_new"], "list")
    for ch, c in chars.items():                              # 2. the pre-2010 levels
        old = c["misc"].get("jlptLevel")
        if old and ch not in levels:
            levels[ch] = (OLD_LEVEL[old], "old")

    met = {}                                                 # 3. the vocabulary lists
    for word, n in jlpt_vocab.items():        # the loader already kept the easiest level
        for ch in word:
            if is_kanji(ch) and n > met.get(ch, 0):
                met[ch] = n
    for ch, n in met.items():
        levels.setdefault(ch, (n, "vocab"))

    # 4. WaniKani teaches these kanji in its own order, 1-60, which is not the JLPT's.
    # Reading one scale off the other needs no hand-written table: take the median
    # WaniKani level of the kanji each JLPT level already holds, and give a kanji the
    # level whose median its own WaniKani level is nearest. Ties fall to the harder one.
    known = defaultdict(list)
    for ch, e in jlpt_src.items():
        if e.get("wk_level") and levels.get(ch, (0, ""))[1] in ("list", "old"):
            known[levels[ch][0]].append(e["wk_level"])
    mid = {lvl: statistics.median(v) for lvl, v in known.items()}
    for ch, e in jlpt_src.items():
        if e.get("wk_level") and ch not in levels:
            near = min(mid, key=lambda l: (abs(mid[l] - e["wk_level"]), l))
            levels[ch] = (near, "wanikani")
    return levels


def hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def surface_forms(reading):
    """A reading shifts inside compounds: rendaku voices the first kana (かわ->がわ),
    sokuon clips the last (がく->がっ)."""
    r = reading.split(".")[0].strip("-〜")
    if not r:
        return set()
    out = {r}
    if r[0] in VOICED:
        out.add(VOICED[r[0]] + r[1:])
    if r[0] in PLOSIVE:
        out.add(PLOSIVE[r[0]] + r[1:])
    if len(r) > 1:
        out.add(r[:-1] + "っ")
    return out


def reading_kind(word_reading, on_readings, kun_readings):
    """Which reading a compound uses, or 'irr' for jukujikun/ateji, where the compound's
    reading cannot be derived from its characters at all (今日 きょう, 梅雨 つゆ)."""
    on  = {v for r in on_readings  for v in surface_forms(r)}
    kun = {v for r in kun_readings for v in surface_forms(r)}
    hit_on  = [v for v in on  if v and v in word_reading]
    hit_kun = [v for v in kun if v and v in word_reading]
    if hit_on and not hit_kun:
        return "on"
    if hit_kun and not hit_on:
        return "kun"
    if hit_on and hit_kun:
        return "on" if max(map(len, hit_on)) >= max(map(len, hit_kun)) else "kun"
    return "irr"


class KanjiVG:
    """Stroke paths, stroke types, the radical as actually drawn, and the component list
    (which is what lets cards cross-reference each other)."""

    def __init__(self):
        self.z = zipfile.ZipFile(fetch("kanjivg.zip"))
        self.names = {}
        for n in self.z.namelist():
            base = n.rsplit("/", 1)[-1]
            if base.endswith(".svg") and "-" not in base:       # skip -Kaisho variants
                self.names[base[:-4]] = n
        self.cache = {}

    def has(self, ch):
        return "%05x" % ord(ch) in self.names

    def get(self, ch):
        if ch in self.cache:
            return self.cache[ch]
        code = "%05x" % ord(ch)
        svg = self.z.read(self.names[code]).decode("utf-8")

        hits = re.findall(r'<path id="kvg:%s-s(\d+)"[^>]*?\sd="([^"]+)"' % code, svg)
        if len(hits) != svg.count(f'id="kvg:{code}-s'):          # a few glyphs carry no type
            hits = [(n, "", d) for n, d in
                    re.findall(r'<path id="kvg:%s-s(\d+)"[^>]*?\sd="([^"]+)"' % code, svg)]
        hits.sort(key=lambda h: int(h[0]))
        # Only the path itself is kept: the strip draws it and nothing reads the stroke
        # type, which at 22k strokes is a quarter of a megabyte of nothing.
        strokes = [trim(d) for _, d in hits]

        radical, radical_strokes = "", 0
        m = re.search(r'<g[^>]*kvg:element="([^"]+)"[^>]*kvg:radical="general"[^>]*>', svg)
        if m:                            # count the paths the radical's own group encloses
            radical, depth, i = m.group(1), 1, m.end()
            while depth and i < len(svg):
                nxt = re.search(r"<g\b|</g>", svg[i:])
                if not nxt:
                    break
                depth += 1 if nxt.group(0) == "<g" else -1
                i += nxt.end()
            radical_strokes = svg[m.end():i].count("<path")

        parts = set(re.findall(r'kvg:element="([^"]+)"', svg)) - {ch}
        out = (strokes, radical, radical_strokes, parts)
        self.cache[ch] = out
        return out

    def stroke_count(self, ch):
        return len(self.get(ch)[0]) if self.has(ch) else 0


def trim(d):
    """KanjiVG paths carry two decimals; the strip draws them about 40px wide on a 109
    grid, so one decimal is already sub-pixel and saves roughly a fifth of the payload."""
    return re.sub(r"\d+\.\d+",
                  lambda m: ("%.1f" % float(m.group())).rstrip("0").rstrip("."), d)


def kangxi_table(vg):
    """Radical number -> (character, stroke count). The Kangxi Radicals block is in
    radical order and each character decomposes to its ordinary CJK form."""
    table = {}
    for n in range(1, 215):
        dec = unicodedata.decomposition(chr(0x2F00 + n - 1))
        ch = JP_RADICAL.get(n) or (chr(int(dec.split()[-1], 16)) if dec else chr(0x2F00 + n - 1))
        table[n] = (ch, vg.stroke_count(ch))
    return table


def pick_gloss(meanings, avoid=()):
    """Shortest usable meaning, skipping any that collides with the kanji shown beside it
    (洋's meanings lead with 'sea', which is 海's own gloss)."""
    ms = [m.lower() for m in meanings if not BAD_MEANING.search(m)]
    ms = ms or [m.lower() for m in meanings] or ["?"]
    return min(([m for m in ms if m not in avoid] or ms)[:4], key=len)


def make_kanji_gloss(chars):
    """A short meaning for any character KANJIDIC knows. The kana cards need it for their
    字源 kanji, which are mostly outside the jouyou set (无, 尔, 祢, 曽)."""
    cache = {}

    def gloss(ch):
        if ch not in cache:
            c = chars.get(ch) or {}
            rm = c.get("readingMeaning") or {}
            means = [m["value"] for g in (rm.get("groups") or [])
                     for m in g.get("meanings", []) if m.get("lang") == "en"]
            cache[ch] = pick_gloss(means) if means else ""
        return cache[ch]

    return gloss


def word_gloss(glosses, cap=26):
    """JMdict orders glosses by prominence, so the leading one is the meaning to show.
    Only reach past it when it will not fit the card's column ('cant' and 'DOB' are what
    picking the shortest gloss gets you)."""
    first = glosses[0]
    if len(first) <= cap:
        return first.lower()
    fits = [g for g in glosses[:4] if len(g) <= cap]
    return (fits[0] if fits else first[:cap - 1] + "\u2026").lower()


def word_difficulty(text, info):
    """How advanced a word is, taken from its hardest kanji. JMdict marks words common or
    not with nothing in between, so this stands in for a frequency rank - and it is the
    pedagogically useful axis anyway: an N4 card should not lean on an N1 kanji."""
    hard = 0
    for c in text:
        if is_kanji(c):
            e = info.get(c)
            hard = max(hard, LEVELS.index(e["level"]) if e else len(LEVELS))
    return hard


def index_vocab(jmdict, info, jlpt_vocab):
    """Every usable dictionary entry, filed under each wanted kanji it contains."""
    by_kanji = defaultdict(list)
    for w in jmdict["words"]:
        senses = [s for s in w["sense"]
                  if not set(s["misc"]) & BAD_SENSE and any(g["lang"] == "eng" for g in s["gloss"])]
        if not senses:
            continue
        glosses = [g["text"] for g in senses[0]["gloss"] if g["lang"] == "eng"]
        if not glosses:
            continue
        gloss = word_gloss(glosses)
        is_name = bool(set(senses[0]["misc"]) & NAME_SENSE)
        pos = senses[0]["partOfSpeech"]
        for form in w["kanji"]:
            if set(form["tags"]) & BAD_FORM:
                continue
            text = form["text"]
            if NOT_A_WORD.search(text):
                continue
            kana = next((k for k in w["kana"]
                         if not set(k["tags"]) & BAD_FORM
                         and ("*" in k["appliesToKanji"] or text in k["appliesToKanji"])), None)
            if not kana:
                continue
            score = (120 if form["common"] else 0) + (40 if kana["common"] else 0)
            score += 25 if len(text) > 1 else 0       # the card lists compounds
            score -= 20 if is_name else 0             # 埼 needs 埼玉, but only as a last resort
            score += 12 if any(p.startswith("n") for p in pos) else 0
            score -= 8 * max(0, len(text) - 3)        # two- and three-kanji compounds read best
            # 上海 reads シャンハイ: a foreign name teaches nothing about the kanji's readings.
            score -= 40 if ALL_KATAKANA.match(kana["text"]) else 0
            tested = jlpt_vocab.get(text)
            score += 90 if tested else 0              # a word the JLPT actually tests
            # Kanji frequency only breaks ties among words the lists say nothing about.
            ranks = [(info[c]["freq"] or 3000) for c in text if c in info]
            score -= (sum(ranks) / len(ranks) / 400) if ranks else 8
            entry = {"w": text, "r": kana["text"], "m": gloss, "score": score,
                     "hard": word_difficulty(text, info),
                     "tested": LEVELS.index(tested) if tested else None}
            for ch in set(text) & info.keys():
                by_kanji[ch].append(entry)
    return by_kanji
NUMERAL = set("一二三四五六七八九十百千万〇零")
# One row of the card's back sets the reading in a column six kana wide and the word in
# one five characters wide. Past either, the row wraps onto a second line, and the block
# under the rule has room for two rows that do - 琉's every compound reads りゅうきゅう
# something, and six of those run off the bottom of the card.
READING_FITS, WORD_FITS, WRAPPED_ROWS = 6, 5, 2


def pick_words(ch, candidates, on, kun, level, want=6):
    """Up to `want` example words, best first, under quotas that stop one shape of word
    from taking the whole card - left alone, 日 fills with 一日 二日 三日 and never gets
    round to 日本 - and reaching for a second reading type before a sixth word of the
    first, because the card's back groups them by reading."""
    here = LEVELS.index(level)

    def rank(e):
        # A word that drags in a harder kanji than the card's own is a worse example, and
        # one tested above this level is a word the learner has not met yet either.
        penalty = 30 * max(0, e["hard"] - here)
        if e["tested"] is not None:
            penalty += 15 * max(0, e["tested"] - here)
        return -(e["score"] - penalty)

    seen, ranked = set(), []
    for e in sorted(candidates, key=rank):
        if e["w"] in seen:              # one slot per written word, whatever its readings
            continue
        seen.add(e["w"])
        ranked.append(dict(e, t=reading_kind(e["r"], on, kun)))

    caps = {"solo": 1, "numeral": 2}

    def shape(e):
        if len(e["w"]) == 1:
            return "solo"               # the card is for compounds; one bare reading is plenty
        if ch not in NUMERAL and any(c in NUMERAL for c in e["w"]):
            return "numeral"            # counters and dates crowd out ordinary vocabulary
        return ""

    def wraps(e):
        return len(e["r"]) > READING_FITS or len(e["w"]) > WORD_FITS

    chosen, taken, kinds, used, wrapped = [], set(), Counter(), Counter(), 0
    for relaxed in (False, True):       # drop the quotas rather than leave the card short
        for i, e in enumerate(ranked):
            if len(chosen) >= want:
                break
            if i in taken:
                continue
            if wraps(e) and wrapped >= WRAPPED_ROWS:
                continue                # the one quota that is never relaxed: it is the
                                        # card's own height, and a short card beats a
                                        # card that prints past its own edge
            s = shape(e)
            if not relaxed:
                if s and used[s] >= caps[s]:
                    continue
                if kinds[e["t"]] >= want - 1 and len(ranked) > want:
                    continue
            chosen.append(e)
            taken.add(i)
            kinds[e["t"]] += 1
            wrapped += wraps(e)
            if s:
                used[s] += 1
    return [{k: e[k] for k in ("w", "r", "m", "t")} for e in chosen[:want]]


def pick_related(ch, vg, info, part_index, want=2):
    """Cross-references to kanji built from the same component - or, when the kanji is
    itself a building block and so has no siblings, to the kanji built out of it
    (日 has no parts of its own, but 明 and 早 are made from it).

    A shared component that also carries a shared on-reading is a phonetic series, which
    is the pairing worth showing."""
    parts, mine = vg.get(ch)[3], info[ch]
    scored = {}

    def consider(other, pool, weight):
        if other == ch or other not in info:
            return
        shared = set(mine["on"]) & set(info[other]["on"])
        s = weight * 60 / max(pool, 1) ** 0.5          # rarer component, stronger link
        s += 45 if shared else 0
        s += 12 if info[other]["level"] >= mine["level"] else 0   # prefer one they know
        s += 10 if info[other]["freq"] else 0
        s -= min(info[other]["no"], 2000) / 400
        if s > scored.get(other, (0,))[0]:
            scored[other] = (s, shared)

    for p in parts:                      # siblings: other kanji sharing this component
        others = part_index.get(p, ())
        if others and len(others) <= 120:   # 口 and 一 would relate everything to everything
            for other in others:
                consider(other, len(others), 1.0)

    kids = part_index.get(ch, ())        # descendants: kanji this one is a component of
    for other in kids:
        consider(other, min(len(kids), 40), 0.8)

    if not scored:                       # 休 is 亻 plus 木, and nothing is built from it
        shared_parts = [p for p in parts if len(part_index.get(p, ())) > 1]
        if shared_parts:
            rarest = min(shared_parts, key=lambda p: len(part_index[p]))
            for other in part_index[rarest]:
                consider(other, len(part_index[rarest]), 0.6)

    best = sorted(scored, key=lambda o: -scored[o][0])[:want]
    return [{
        "k": other,
        "no": info[other]["no"],
        "g": pick_gloss(info[other]["meanings"], avoid={info[ch]["gloss"]}),
        "s": "\u30fb".join(sorted(hira_to_kata(r) for r in scored[other][1])),
    } for other in best]


def hira_to_kata(s):
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)


def main():
    print("sources", file=sys.stderr)
    kd2 = load_json_zip("kanjidic2.zip")
    jm  = load_json_zip("jmdict.zip")
    jlpt_src = json.load(open(fetch("jlpt.json"), encoding="utf-8"))
    jlpt_vocab = load_jlpt_vocab()
    vg = KanjiVG()
    kangxi = kangxi_table(vg)

    chars = {c["literal"]: c for c in kd2["characters"]}
    levels = kanji_levels(chars, jlpt_src, jlpt_vocab)
    info = {}
    for ch, c in chars.items():
        grade = c["misc"].get("grade")
        placed = levels.get(ch)
        # A jouyou kanji is on the syllabus whether or not a list remembers it; anything
        # else is here because a source put it on one. Both need a glyph to draw.
        if not vg.has(ch) or not (placed or grade in JOUYOU_GRADES):
            continue
        if not placed:
            placed = (GRADE_LEVEL[grade], "grade")
        rm = c.get("readingMeaning") or {}
        groups = rm.get("groups") or [{}]
        reads = [r for g in groups for r in g.get("readings", [])]
        means = [m["value"] for g in groups for m in g.get("meanings", [])
                 if m.get("lang") == "en"]
        info[ch] = {
            "grade": grade, "level": placed[0], "src": placed[1],
            "freq": c["misc"].get("frequency"),
            "on":  [hira(r["value"]) for r in reads if r["type"] == "ja_on"],
            "kun": [r["value"] for r in reads if r["type"] == "ja_kun"],
            "meanings": means or ["?"],
            "radical": next((r["value"] for r in c["radicals"] if r["type"] == "classical"), 0),
        }
    for ch, e in info.items():
        e["gloss"] = pick_gloss(e["meanings"])

    extra = sum(1 for e in info.values() if e["grade"] not in JOUYOU_GRADES)
    print(f"  {len(info)} kanji ({extra} from outside the jouyou set), "
          f"indexing {len(jm['words'])} dictionary entries", file=sys.stderr)
    vocab = index_vocab(jm, info, jlpt_vocab)
    chosen = {ch: pick_words(ch, vocab.get(ch, []), e["on"], e["kun"], e["level"])
              for ch, e in info.items()}

    # The front of a kanji card is its list of compounds, so a kanji JMdict can show
    # nothing for has no card to print. A jouyou kanji is on the syllabus either way and
    # keeps its place; one from outside the set has only its words to be here for.
    for ch in [c for c, w in chosen.items()
               if not w and info[c]["grade"] not in JOUYOU_GRADES]:
        del info[ch], chosen[ch]

    # A stable card number per kanji: easiest level first, commonest kanji first.
    order = sorted(info, key=lambda c: (LEVELS.index(info[c]["level"]),
                                        info[c]["freq"] or 9999, c))
    for n, ch in enumerate(order, 1):
        info[ch]["no"] = n

    part_index = defaultdict(list)
    for ch in info:
        for p in vg.get(ch)[3]:
            part_index[p].append(ch)

    decks, tally, thin = defaultdict(list), Counter(), []
    for ch in order:
        e = info[ch]
        strokes, rad, rad_n, _ = vg.get(ch)
        if not rad:                                  # KanjiVG tags ~83%; Kangxi covers the rest
            rad, rad_n = kangxi[e["radical"]]
        total = len(strokes)                         # match the strip the card actually draws
        if rad_n >= total:                           # 才 is filed under 手 but written as itself
            rad, rad_n = ch, total
        words = chosen[ch]
        if len(words) < 6:
            thin.append(ch)
        for w in words:
            tally[w["t"]] += 1
        decks[e["level"]].append({
            "k": ch, "no": e["no"], "strokes": total,
            "rad": rad, "radN": rad_n, "restN": max(total - rad_n, 0),
            "vocab": words,
            "rel": pick_related(ch, vg, info, part_index),
            "paths": strokes,
            "on": e["on"][:3], "kun": e["kun"][:3], "mean": e["gloss"],
        })

    print("kana", file=sys.stderr)
    kana_decks = build_kana.build_decks(
        vg, jm, load_jlpt_readings(), word_gloss, make_kanji_gloss(chars),
        log=lambda m: print(m, file=sys.stderr))

    os.makedirs(os.path.join(OUT, "decks"), exist_ok=True)
    manifest = []
    # Kana first: it is where a learner starts, and the chooser reads top to bottom.
    written = list(kana_decks)
    written += [({"id": f"n{lvl}", "label": f"N{lvl}", "rom": "", "group": "漢字",
                  "kind": "kanji", "n": len(decks[lvl])}, decks[lvl]) for lvl in LEVELS]
    for meta, cards in written:
        manifest.append(meta)
        if cards is None:          # a merged deck is dealt from the files its parts write
            # and spans everything they hold. Its parts are written before it, so their
            # ranges are already on the manifest by the time it is reached.
            spans = [m for m in manifest if m["id"] in meta["parts"]]
            meta["lo"] = min(m["lo"] for m in spans)
            meta["hi"] = max(m["hi"] for m in spans)
            print(f"  {meta['id']:11} {meta['n']:4} cards  {'merged':>7}", file=sys.stderr)
            continue
        path = os.path.join(OUT, "decks", f"{meta['id']}.js")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("/* Generated by tools/build_cards.py - do not edit by hand. */\n")
            fh.write(f"KANJI_DECK({json.dumps(meta['id'])}," + json.dumps(
                cards, ensure_ascii=False, separators=(",", ":")) + ");\n")
        kb = os.path.getsize(path) / 1024
        # The chooser prints the run of card numbers a deck holds - 第80-247番 - so
        # a box can say what it contains without the deck being downloaded. Two
        # numbers rather than a list because every deck's numbers are contiguous:
        # a card number is the slot in the syllabary or the jouyou index, and the
        # decks partition those in order.
        nos = [c["no"] for c in cards]
        meta["lo"], meta["hi"] = min(nos), max(nos)
        print(f"  {meta['id']:11} {len(cards):4} cards  {kb:7.0f} KB", file=sys.stderr)

    with open(os.path.join(OUT, "decks.js"), "w", encoding="utf-8") as fh:
        fh.write("/* Generated by tools/build_cards.py - do not edit by hand. */\n")
        fh.write("const DECKS = " + json.dumps(manifest, ensure_ascii=False) + ";\n")

    # the merged decks re-deal cards their parts already carry, so counting them here
    # would count the syllabary twice
    kana_n = sum(m["n"] for m, _ in kana_decks if m["id"] not in build_kana.MERGED_IDS)
    print(f"{sum(len(d) for d in decks.values())} kanji cards and {kana_n} kana cards "
          f"across {len(manifest)} decks")
    placed = Counter(e["src"] for e in info.values())
    print("levels placed by: " + ", ".join(
        f"{placed[k]} {name}" for k, name in
        (("list", "the N5-N1 kanji list"), ("old", "the pre-2010 levels"),
         ("vocab", "the vocabulary lists"), ("wanikani", "WaniKani"),
         ("grade", "school grade")) if placed[k]))
    print(f"readings classified: {tally['on']} on, {tally['kun']} kun, {tally['irr']} irregular")
    if thin:
        print(f"{len(thin)} kanji have fewer than 6 example words: {''.join(thin[:20])}"
              + (" ..." if len(thin) > 20 else ""))


if __name__ == "__main__":
    main()
