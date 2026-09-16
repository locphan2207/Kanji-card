#!/usr/bin/env python3
"""Build frontend/data/cards.js from open kanji data plus the curated deck in tools/deck.json.

    python3 tools/build_cards.py

Sources
  KANJIDIC2 (readings, meanings, stroke counts, grade, frequency), via
    github.com/davidluzgouveia/kanji-data  — EDRDG, CC BY-SA 4.0
  KanjiVG (per-stroke paths, stroke types, radical), CC BY-SA 3.0
    kanjivg.tagaini.net

Downloads are cached under tools/cache/ so reruns are offline and fast.
"""
import json, os, re, sys, urllib.request

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", "cache")
KANJIDIC_URL = "https://raw.githubusercontent.com/davidluzgouveia/kanji-data/master/kanji.json"
KANJIVG_URL  = "https://raw.githubusercontent.com/KanjiVG/kanjivg/master/kanji/{code}.svg"

# 夢's radical is not tagged in KanjiVG; Kangxi gives 夕 (3 strokes)
RADICAL_FALLBACK = {"夢": ("夕", 3)}

# Stroke types that shift when a kanji sits inside a compound.
VOICED = dict(zip("かきくけこさしすせそたちつてとはひふへほ",
                  "がぎぐげございずぜぞだぢづでどばびぶべぼ"))
PLOSIVE = dict(zip("はひふへほ", "ぱぴぷぺぽ"))

BAD_MEANING = re.compile(r"radical|\(no\.|counter for", re.I)


def fetch(url, name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        print(f"  fetching {name}", file=sys.stderr)
        urllib.request.urlretrieve(url, path)
    return path


def kanjivg(ch):
    """Stroke paths in order, each tagged with its type, plus the radical."""
    code = "%05x" % ord(ch)
    svg = open(fetch(KANJIVG_URL.format(code=code), f"{code}.svg"), encoding="utf-8").read()

    hits = re.findall(r'<path id="kvg:%s-s(\d+)"[^>]*?kvg:type="([^"]*)"[^>]*?\sd="([^"]+)"' % code, svg)
    if len(hits) != svg.count(f'id="kvg:{code}-s'):          # a few glyphs carry no type
        hits = [(n, "", d) for n, d in
                re.findall(r'<path id="kvg:%s-s(\d+)"[^>]*?\sd="([^"]+)"' % code, svg)]
    hits.sort(key=lambda h: int(h[0]))
    strokes = [{"d": d, "t": t[:1]} for _, t, d in hits]

    radical, radical_strokes = "", 0
    m = re.search(r'<g[^>]*kvg:element="([^"]+)"[^>]*kvg:radical="general"[^>]*>', svg)
    if m:                                                    # count the paths the radical group encloses
        radical, depth, i = m.group(1), 1, m.end()
        while depth and i < len(svg):
            nxt = re.search(r"<g\b|</g>", svg[i:])
            if not nxt:
                break
            depth += 1 if nxt.group(0) == "<g" else -1
            i += nxt.end()
        radical_strokes = svg[m.end():i].count("<path")
    if not radical:
        radical, radical_strokes = RADICAL_FALLBACK[ch]
    return strokes, radical, radical_strokes


def gloss(kd, ch, avoid=()):
    """Shortest usable meaning, skipping any that collides with the kanji shown beside it
    (洋's meanings lead with 'sea', which is 海's own gloss)."""
    ms = [m.lower() for m in kd[ch]["meanings"] if not BAD_MEANING.search(m)]
    ms = ms or [kd[ch]["meanings"][0].lower()]
    return min(([m for m in ms if m not in avoid] or ms)[:4], key=len)


def katakana(s):
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)


def surface_forms(reading):
    """A reading shifts inside compounds: rendaku voices the first kana (かわ→がわ),
    sokuon clips the last (がく→がっ)."""
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


def main():
    kd = json.load(open(fetch(KANJIDIC_URL, "kanjidic.json"), encoding="utf-8"))
    deck = json.load(open(os.path.join(ROOT, "tools", "deck.json"), encoding="utf-8"))

    cards, tally = [], {"on": 0, "kun": 0, "irr": 0}
    for ch, entry in deck.items():
        e = kd[ch]
        strokes, radical, radical_strokes = kanjivg(ch)
        if len(strokes) != e["strokes"]:
            print(f"  ! {ch}: KanjiVG has {len(strokes)} strokes, KANJIDIC says {e['strokes']}",
                  file=sys.stderr)

        vocab = []
        for word, reading, meaning in entry["vocab"]:
            kind = reading_kind(reading, e["readings_on"], e["readings_kun"])
            tally[kind] += 1
            vocab.append({"w": word, "r": reading, "m": meaning, "t": kind})

        mine = gloss(kd, ch)
        cards.append({
            "k": ch,
            "no": e["freq"],                       # stands in for a deck sequence number
            "strokes": e["strokes"],
            "rad": radical, "radN": radical_strokes,
            "restN": e["strokes"] - radical_strokes,
            "vocab": vocab,
            "rel": [{
                "k": other,
                "no": kd[other]["freq"],
                "g": gloss(kd, other, avoid={mine}),
                # a shared on-reading means the shared component is phonetic, not just visual
                "s": katakana("・".join(sorted(
                    set(e["readings_on"]) & set(kd[other]["readings_on"])))),
            } for other in entry["related"]],
            "paths": strokes,
            "on": e["readings_on"][:3],
            "kun": e["readings_kun"][:3],
            "mean": mine,
        })

    out = os.path.join(ROOT, "frontend", "data", "cards.js")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("/* Generated by tools/build_cards.py — do not edit by hand.\n"
                 "   This is the seam where a backend will take over: replace this file with a\n"
                 "   fetch that assigns the same shape to CARDS. */\n")
        fh.write("const CARDS = " + json.dumps(cards, ensure_ascii=False,
                                               separators=(",", ":")) + ";\n")
    print(f"{len(cards)} cards -> frontend/data/cards.js")
    print(f"readings classified: {tally['on']} on, {tally['kun']} kun, {tally['irr']} irregular")


if __name__ == "__main__":
    main()
