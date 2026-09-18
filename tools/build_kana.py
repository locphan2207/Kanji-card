#!/usr/bin/env python3
"""Build the kana decks. Imported by build_cards.py, which owns the manifest.

A kana card asks a different question from a kanji card. A kanji card asks "which of
this character's readings does each compound use"; a kana card asks "what sound is
this", and the answer is one syllable. So the front carries no romaji at all - the
glyph, words written in the deck's own script, the strokes, and a warning about the
kana it gets mixed up with - and the back carries the sound, where the kana sits in the
gojuon table, the kanji it was cursived down from, and its counterpart in the other
script.

Example words come from JMdict the same way the kanji cards' do, but ranked on kana
terms: a word is only useful here if it is written in the deck's script, is short
enough to read at a glance, and does not lean on kana the learner has not met yet -
there is no point teaching あ with じゃあ.
"""
import re
from collections import Counter, defaultdict

import kana_tables as T

HIRA_WORD = re.compile(r"^[ぁ-ゖ]+$")
KATA_WORD = re.compile(r"^[ァ-ヺー]+$")
BAD_SENSE = {"arch", "obs", "rare", "derog", "vulg", "X", "sl"}
NAME_SENSE = {"place", "surname", "given", "organization", "work", "product", "person"}

LEVELS = [5, 4, 3, 2, 1]                      # index 0 is N5, the easiest

# How far into the syllabary a character sits. A word is a bad example for a card when it
# needs kana from further in than the card's own deck reaches.
BASIC_CHARS = {c for s in T.BASIC for c in s[:2]}
DAKUTEN_CHARS = {c for s in T.DAKUTEN for c in s[:2]}
SMALL_CHARS = set("ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ")
TIER_3_CHARS = set("ゔヴゐゑヰヱヵヶ")


def char_tier(c):
    if c in TIER_3_CHARS:
        return 3
    if c in SMALL_CHARS:
        return 2
    if c in DAKUTEN_CHARS or c == "ー":   # a katakana word can hardly avoid ー
        return 1
    return 0 if c in BASIC_CHARS else 3


def word_tier(text):
    return max((char_tier(c) for c in text), default=0)


def jlpt_gloss(meaning, cap=24):
    """The JLPT lists write a meaning as several clauses with parenthetical asides
    ("rice (cooked); meal"); a card's gloss column has room for one clause."""
    plain = re.sub(r"\s*\([^)]*\)", "", meaning)
    parts = [p.strip() for p in re.split(r"[;,]", plain) if p.strip()]
    return (parts or [meaning])[0].lower()[:cap]


PHRASE_POS = {"exp", "conj"}
PARTICLE_TAIL = ("は", "へ")


def build_pool(jmdict, jlpt_readings, word_gloss):
    """Every dictionary entry that can be written in one kana script, indexed by the
    characters in it. Two-kana targets (きゃ, ファ) are found by filtering the bucket of
    their rarest character, which is always the small one.

    A kana spelling is usually several dictionary entries - あか is 赤 and 垢, かてい is
    家庭 and three others - and the card can only show one of them, so the entry the JLPT
    lists point at wins, and only failing that the commonest one. Where even that does not
    single an entry out (the lists write たて in kana), their own gloss is used instead."""
    by_char = defaultdict(list)
    best = {}
    for w in jmdict["words"]:
        senses = [s for s in w["sense"] if not set(s["misc"]) & BAD_SENSE
                  and any(g["lang"] == "eng" for g in s["gloss"])]
        if not senses:
            continue
        glosses = [g["text"] for g in senses[0]["gloss"] if g["lang"] == "eng"]
        if not glosses:
            continue
        gloss = word_gloss(glosses, cap=24)
        is_name = bool(set(senses[0]["misc"]) & NAME_SENSE)
        pos = senses[0]["partOfSpeech"]
        kanji_common = any(f.get("common") for f in w["kanji"])
        for k in w["kana"]:
            text = k["text"]
            script = ("hira" if HIRA_WORD.match(text) else
                      "kata" if KATA_WORD.match(text) else None)
            if not script:
                continue
            level, expr, taught = jlpt_readings.get(text, (None, "", ""))
            # the entry the JLPT list means: 赤 rather than 垢, 家庭 rather than 仮定
            listed = bool(expr) and (any(f["text"] == expr for f in w["kanji"])
                                     or (not w["kanji"] and text == expr))
            phrase = bool(set(pos) & PHRASE_POS)
            entry = {
                "w": text, "script": script,
                "m": gloss if listed or not taught else jlpt_gloss(taught),
                "common": bool(k.get("common")), "name": is_name, "phrase": phrase,
                "tested": LEVELS.index(level) if level else None,
                "content": any(p.startswith(("n", "v", "adj")) for p in pos),
                "tier": word_tier(text),
                # こんにちは and では end in the topic particle, which is said wa, not ha.
                "tail_wa": text.endswith(PARTICLE_TAIL) and (phrase or "int" in pos),
            }
            rank = (listed, bool(k.get("common")), kanji_common, not is_name)
            key = (text, script)
            if key not in best or rank > best[key][0]:
                best[key] = (rank, entry)
    for _, entry in best.values():
        for c in set(entry["w"]):
            by_char[c].append(entry)
    return by_char


def pick_words(target, script, tier, by_char, want=6):
    """Up to `want` example words for one kana, best first.

    Ranked on how soon a learner meets the word (the JLPT lists again), how short it is,
    and whether it stays inside the kana this deck has taught. The quotas are the kana
    version of the kanji card's: cap the words that simply start with the target, because
    six of those teach you nothing about spotting か in the middle of なかなか."""
    bucket = min((by_char.get(c, []) for c in target), key=len, default=[])
    cands = [e for e in bucket if e["script"] == script and target in e["w"]]

    def score(e):
        s = 0.0
        if e["tested"] is not None:
            s += 100 - 22 * e["tested"]        # N5 word: +100, N1 word: +12
        s += 40 if e["common"] else 0
        s += 12 if e["content"] else 0
        s -= 15 if e["name"] else 0
        s -= 20 if e["phrase"] else 0           # a card teaches words before it teaches では
        s -= 10 * max(0, len(e["w"]) - 4)      # long words crowd the card's word column
        s -= 25 * max(0, len(e["w"]) - 6)      # and past six kana they simply do not fit
        s -= 18 * max(0, e["tier"] - tier)     # do not teach あ with じゃあ
        s -= 30 if len(e["w"]) == len(target) else 0
        return -s

    ranked = sorted(cands, key=score)
    caps = {"lead": 3, "solo": 1}
    chosen, kept, used = [], set(), Counter()
    for relaxed in (False, True):              # drop the quotas rather than leave it short
        for i, e in enumerate(ranked):
            if len(chosen) >= want:
                break
            if i in kept:
                continue
            shape = ("solo" if len(e["w"]) == len(target)
                     else "lead" if e["w"].startswith(target) else "")
            if not relaxed and shape and used[shape] >= caps[shape]:
                continue
            chosen.append(e)
            kept.add(i)
            if shape:
                used[shape] += 1
    return [{"w": e["w"], "m": e["m"], "tail_wa": e["tail_wa"]} for e in chosen[:want]]


# Where the two halves of a two-kana card go inside one 109x109 practice cell, as
# (dx, dy, scale): the base kana keeps most of the square and the small one sits to its
# right, on the same baseline. Numbers rather than an SVG transform string so the page
# can divide the scale back out of the stroke weight - left alone, ァ at 0.42 would be
# drawn with a pen less than half as wide as フ's and all but vanish.
TX_BASE = (0, 18, 0.62)
TX_SMALL = (64, 40, 0.42)


def strokes_for(text, vg):
    """Stroke paths for the card's character(s), each with the placement that puts it in
    the cell. KanjiVG draws every kana including the voiced ones, so が is five real
    strokes rather than か with a mark bolted on; only the two-kana forms need composing."""
    if len(text) == 1:
        return [(p, 0) for p in vg.get(text)[0]]
    base, small = text[0], text[1]
    return ([(p, TX_BASE) for p in vg.get(base)[0]]
            + [(p, TX_SMALL) for p in vg.get(small)[0]])


ROW_ORDER = ["あ", "か", "さ", "た", "な", "は", "ま", "や", "ら", "わ"]
COL_ORDER = ["あ", "い", "う", "え", "お"]
ROW_ROMAJI = {"あ": "a", "か": "ka", "さ": "sa", "た": "ta", "な": "na", "は": "ha",
              "ま": "ma", "や": "ya", "ら": "ra", "わ": "wa",
              "が": "ga", "ざ": "za", "だ": "da", "ば": "ba", "ぱ": "pa"}
COL_ROMAJI = dict(zip(COL_ORDER, "aiueo"))
BASIC_BY_HIRA = {s[0]: s for s in T.BASIC}
# Which row and column any plain or voiced kana sits in: じ is ざ行 い段, not さ行 い段.
CELL_OF = {s[0]: (s[4], s[5]) for s in T.BASIC if s[4]}
MARK_OF = {}
DAKUTEN_ROW = {"か": "が", "さ": "ざ", "た": "だ", "は": "ば"}
SAME_SOUND = {"じ": "ぢ", "ぢ": "じ", "ず": "づ", "づ": "ず",
              "ジ": "ヂ", "ヂ": "ジ", "ズ": "ヅ", "ヅ": "ズ"}
MARK_NAME = {"゛": "゛", "゜": "゜"}


def grid_cell(base_hira):
    """Which cell of the gojuon table to ink. Every card has one, because even ファ is
    built on フ - the table is the map the whole syllabary is read against."""
    if base_hira == "ん":
        return "n"
    slot = BASIC_BY_HIRA.get(base_hira)
    if not slot or not slot[4]:
        return None
    return [ROW_ORDER.index(slot[4]), COL_ORDER.index(slot[5])]


def lookalikes(ch, script):
    """The kana this one gets mistaken for, with the sound of each so the back can say
    what the difference actually is. Kanji in the list keep their meaning instead."""
    out = []
    for other in T.LOOKALIKE.get(ch, "")[:2]:
        if other in T.KANJI_LOOKALIKE:
            out.append({"c": other, "l": "漢", "g": T.KANJI_LOOKALIKE[other]})
        else:
            out.append({"c": other, "l": "似", "g": sound_of(other)})
    return out


_SOUND = {}


def sound_of(ch):
    if not _SOUND:
        for group in (T.BASIC, T.DAKUTEN, T.YOON):
            for h, k, hep, *_ in group:
                _SOUND[h] = _SOUND[k] = hep
        for h, k, hep, *_ in T.SPECIAL:
            if h:
                _SOUND[h] = hep
            _SOUND[k] = hep
        for k, hep, _ in T.FOREIGN:
            _SOUND[k] = hep
    return _SOUND.get(ch, "")


KATA_TO_HIRA_EXTRA = {"ヴ": "ゔ", "ヰ": "ゐ", "ヱ": "ゑ", "ヵ": "か", "ヶ": "か", "ヮ": "わ"}
# ゔ is not in the dakuten table - it is a twentieth-century addition - but it peels back
# to う the same way が peels back to か.
DAKUTEN_TO_SEION = dict({s[0]: s[4] for s in T.DAKUTEN}, **{"ゔ": "う"})


def to_hira(c):
    if c in KATA_TO_HIRA_EXTRA:
        return KATA_TO_HIRA_EXTRA[c]
    return chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c


def seion_base(c):
    """Peel a kana back to the plain gojuon character underneath it: グ -> ぐ -> く."""
    h = to_hira(c)
    return DAKUTEN_TO_SEION.get(h, h)


def slots():
    """Every kana slot in one numbered sequence. Numbering is by slot rather than by
    deck, so a kana and its counterpart carry the same number - か and カ are both 11 -
    and the two scripts read as one syllabary seen twice."""
    out = []
    for h, k, hep, kun, row, col in T.BASIC:
        out.append(dict(kind="basic", hira=h, kata=k, hep=hep, kun=kun,
                        base=h, small="", mark="", row=row, col=col))
    for h, k, hep, kun, base, mark in T.DAKUTEN:
        base_row, base_col = BASIC_BY_HIRA[base][4], BASIC_BY_HIRA[base][5]
        out.append(dict(kind="dakuten", hira=h, kata=k, hep=hep, kun=kun,
                        base=base, small="", mark=MARK_NAME[mark],
                        row=DAKUTEN_ROW[base_row] if mark == "゛" else "ぱ",
                        col=base_col))
    for h, k, hep, kun, base, small in T.YOON:
        out.append(dict(kind="yoon", hira=h, kata=k, hep=hep, kun=kun,
                        base=base, small=small, mark="", row="", col=""))
    for h, k, hep, kun, base in T.SPECIAL:
        out.append(dict(kind="special", hira=h, kata=k, hep=hep, kun=kun,
                        base=base, small="", mark="", row="", col=""))
    for k, hep, base in T.FOREIGN:
        out.append(dict(kind="foreign", hira=None, kata=k, hep=hep, kun="",
                        base=base, small=k[1], mark="", row="", col=""))
    for s in out:
        if s["kind"] == "dakuten":
            CELL_OF[s["hira"]] = (s["row"], s["col"])
            MARK_OF[s["hira"]] = s["mark"]
    CELL_OF["ゔ"] = CELL_OF["う"]
    MARK_OF["ゔ"] = "゛"
    for n, s in enumerate(out, 1):
        s["no"] = n
    return out


DECKS = [
    # id, script, group, label, romaji, kinds, tier
    ("hira-sei",    "hira", "ひらがな", "清音",   "seion",    ("basic",),   0),
    ("hira-daku",   "hira", "ひらがな", "濁音",   "dakuon",   ("dakuten",), 1),
    ("hira-yoon",   "hira", "ひらがな", "拗音",   "yoon",     ("yoon",),    2),
    ("hira-toku",   "hira", "ひらがな", "特殊",   "tokushu",  ("special",), 2),
    ("kata-sei",    "kata", "カタカナ", "清音",   "seion",    ("basic",),   0),
    ("kata-daku",   "kata", "カタカナ", "濁音",   "dakuon",   ("dakuten",), 1),
    ("kata-yoon",   "kata", "カタカナ", "拗音",   "yoon",     ("yoon",),    2),
    ("kata-toku",   "kata", "カタカナ", "特殊",   "tokushu",  ("special",), 2),
    ("kata-gairai", "kata", "カタカナ", "外来音", "gairaion", ("foreign",), 3),
]

# A whole script in one pile, for drilling ひらがな as ひらがな rather than a class of
# form at a time. A merged deck holds no cards of its own: it names the decks it gathers
# and the loader deals their files as one pile, so the same cards are not written out a
# second time under a second id, and 清音 is not downloaded twice by someone who drilled
# it before picking 全部.
MERGED = [
    # id, group, label, romaji, the decks it gathers, in chooser order
    ("hira-all", "ひらがな", "全部", "zenbu",
     ("hira-sei", "hira-daku", "hira-yoon", "hira-toku")),
    ("kata-all", "カタカナ", "全部", "zenbu",
     ("kata-sei", "kata-daku", "kata-yoon", "kata-toku", "kata-gairai")),
]
MERGED_IDS = {deck_id for deck_id, *_ in MERGED}
SCRIPT_NAME = {"hira": "ひらがな", "kata": "カタカナ"}


def position(slot, script):
    """Where the card sits in the gojuon table, named. Composed kana have no cell of
    their own, so they borrow their base's and say whose it is - and it is the real base
    that gets named, so ジョ reads ジ：ザ行 イ段 rather than シ：サ行 イ段."""
    cast = (lambda c: c) if script == "hira" else to_kata
    if slot["row"]:
        row, col, prefix = slot["row"], slot["col"], ""
    else:
        base = to_hira(slot["base"] or "")
        if base not in CELL_OF:
            return "", ""
        (row, col), prefix = CELL_OF[base], cast(base) + "："
    return (f"{prefix}{cast(row)}行 {cast(col)}段",
            f"{ROW_ROMAJI.get(row, '')}-row · {COL_ROMAJI.get(col, '')}-vowel")


def composition(slot, script):
    """なりたち: what the character is made of, in the script the card is written in."""
    ch = slot["hira"] if script == "hira" else slot["kata"]
    base = slot["base"] if script == "hira" else (slot["base"] and to_kata(slot["base"]))
    if slot["kind"] == "dakuten":
        return f"{base} ＋ {slot['mark']}"
    if slot["kind"] in ("yoon", "foreign"):
        return f"{ch[0]} ＋ {ch[1]}"
    if slot["kind"] == "special" and slot["base"]:
        if ch in "ゔヴ":                     # ゔ is not a small anything - it is う voiced
            return f"{base} ＋ ゛"
        return f"小さい {base}"
    return ""


def to_kata(c):
    return chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c


def note_for(slot, script, ch):
    if ch in T.NOTES:
        return T.NOTES[ch]
    if slot["kind"] == "special" and slot["base"]:
        if slot["hira"] in ("ゃ", "ゅ", "ょ"):
            ki = "キ" if script == "kata" else "き"
            vowel = slot["hep"][-1]
            return T.SMALL_YA_NOTE.format(small=ch, base=ki, joined="ky" + vowel,
                                          apart="ki-y" + vowel)
        return T.SMALL_VOWEL_NOTE
    if slot["kind"] == "dakuten":
        was, now = sound_of(slot["base"]), slot["hep"]
        verb = "voices" if slot["mark"] == "゛" else "hardens"
        return (f"The mark {slot['mark']} {verb} {head(was)} into {head(now)}: "
                f"{was} becomes {now}.")
    if slot["kind"] == "yoon":
        return (f"One beat, not two: {ch} is {slot['hep']}, never "
                f"{sound_of(ch[0])}-{sound_of(ch[1]) or 'ya'}.")
    if slot["kind"] == "foreign":
        return (f"{ch[0]} plus a small {ch[1]} spells {slot['hep']}, a sound the "
                f"gojuon table has no cell for.")
    return ""


def head(romaji):
    """The consonant a romaji syllable starts with: shi -> sh, tsu -> ts, a -> a vowel."""
    stem = romaji.rstrip("aiueo")
    return stem or romaji


def related(slot, script):
    """The cross-reference box. On a plain kana it warns about the characters this one is
    mistaken for; on a built-up one it shows what it is built from, which is the same
    question the kanji cards ask of their components."""
    ch = slot["hira"] if script == "hira" else slot["kata"]
    cast = (lambda c: c) if script == "hira" else to_kata
    if slot["kind"] == "basic":
        return [{"c": e["c"], "l": e["l"]} for e in lookalikes(ch, script)]
    if slot["kind"] == "dakuten":
        out = [{"c": cast(slot["base"]), "l": "元"}]
        partner = SAME_SOUND.get(ch)
        if partner:
            out.append({"c": partner, "l": "同"})
        elif slot["mark"] == "゜":
            out.append({"c": cast(DAKUTEN_ROW_FORM[slot["base"]]), "l": "濁"})
        elif slot["base"] in DAKUTEN_ROW_FORM and slot["mark"] == "゛" \
                and slot["base"] in ("は", "ひ", "ふ", "へ", "ほ"):
            out.append({"c": cast(HANDAKU_FORM[slot["base"]]), "l": "半"})
        return out
    if slot["kind"] in ("yoon", "foreign"):
        return [{"c": ch[0], "l": "元"}, {"c": ch[1], "l": "小"}]
    if slot["kind"] == "special":
        if slot["base"]:
            return [{"c": cast(slot["base"]), "l": "元"}]
        if ch in RETIRED:
            return [{"c": cast(RETIRED[ch]), "l": "同"}]
        return [{"c": e["c"], "l": e["l"]} for e in lookalikes(ch, script)]
    return []


# What the 1946 reform put in their place. ー is the one kana with nothing to point at.
RETIRED = {"ゐ": "い", "ヰ": "い", "ゑ": "え", "ヱ": "え"}


# は/ひ/ふ/へ/ほ carry both marks, so each voiced form has a half-voiced twin and vice versa.
HANDAKU_FORM = dict(zip("はひふへほ", "ぱぴぷぺぽ"))
DAKUTEN_ROW_FORM = dict(zip("はひふへほ", "ばびぶべぼ"))


# ---------------------------------------------------------------------- romaji
# Built from the tables above, longest match first so きゃ beats き.
def _romaji_map():
    m = {}
    for group in (T.BASIC, T.DAKUTEN, T.YOON):
        for h, k, hep, *_ in group:
            m[h] = m[k] = hep
    for h, k, hep, kun, base in T.SPECIAL:
        if k in "っッー":
            continue
        if h:
            m[h] = hep
        m[k] = hep
    for k, hep, base in T.FOREIGN:
        m[k] = hep
    m["を"] = m["ヲ"] = "o"
    return m


ROMAJI = _romaji_map()
MACRON = {"a": "ā", "i": "ī", "u": "ū", "e": "ē", "o": "ō"}


def romaji(text, tail_wa=False):
    """Hepburn, one kana at a time. Deliberately kana-transparent: がっこう comes out
    gakkou, not gakkō, because the column exists to say what each character sounds like
    and nothing in the data can tell おう the long vowel (こう) from おう the two vowels
    (おう, to chase). ー is the one length mark that is never ambiguous, so it gets a
    macron."""
    if tail_wa:                 # こんにちは ends in the topic particle: konnichiwa
        return romaji(text[:-1]) + ("wa" if text[-1] in "はハ" else "e")
    out, i, pending_sokuon = [], 0, False
    while i < len(text):
        two = text[i:i + 2]
        if two in ROMAJI and len(two) == 2:
            syl, step = ROMAJI[two], 2
        elif text[i] in "っッ":
            pending_sokuon, i = True, i + 1
            continue
        elif text[i] == "ー":
            if out and out[-1][-1] in MACRON:
                out[-1] = out[-1][:-1] + MACRON[out[-1][-1]]
            i += 1
            continue
        elif text[i] in "んン":
            nxt = text[i + 1:i + 2]
            follows_vowel = nxt and ROMAJI.get(nxt, "x")[0] in "aiueoy"
            out.append("n'" if follows_vowel else "n")
            i += 1
            continue
        else:
            syl, step = ROMAJI.get(text[i], text[i]), 1
        if pending_sokuon:
            # Hepburn doubles the consonant, but ch doubles as t: まっちゃ is matcha.
            syl = ("t" if syl.startswith("ch") else syl[0]) + syl
            pending_sokuon = False
        out.append(syl)
        i += step
    return "".join(out) + ("tsu" if pending_sokuon else "")


# ------------------------------------------------------------------- assembly
def make_card(slot, script, no, vg, by_char, tier, kanji_gloss):
    ch = slot["hira"] if script == "hira" else slot["kata"]
    other = slot["kata"] if script == "hira" else slot["hira"]
    origin_table = T.ORIGIN_HIRA if script == "hira" else T.ORIGIN_KATA
    pos_jp, pos_rom = position(slot, script)

    facts = []
    if pos_jp:
        facts.append(["五十音", pos_jp, pos_rom])
    built = composition(slot, script)
    if built:
        facts.append(["なりたち", built, ""])
    origin = origin_table.get(ch, "")
    if origin:
        facts.append(["字源", origin, kanji_gloss(origin)])
    if other:
        facts.append([SCRIPT_NAME["kata" if script == "hira" else "hira"], other, ""])

    strokes = strokes_for(ch, vg)
    counts = [len(vg.get(c)[0]) for c in ch]
    words = pick_words(ch, script, tier, by_char)
    rel = related(slot, script)
    for e in rel:
        e["g"] = (T.KANJI_LOOKALIKE.get(e["c"]) if e["l"] == "漢" else sound_of(e["c"]))

    card = {
        "c": ch, "no": no, "hep": slot["hep"], "kun": slot["kun"],
        "code": "+".join(str(n) for n in counts) + "画",
        "paths": [p for p, _ in strokes],
        # left out entirely when every stroke is drawn where KanjiVG put it
        "tx": [t for _, t in strokes] if any(t for _, t in strokes) else 0,
        "map": grid_cell(seion_base(slot["base"])) if slot["base"] else None,
        # A composed kana inherits its base's mark, so the gojuon map can ink シ and
        # still say that this card is ジョ.
        "mark": slot["mark"] or MARK_OF.get(to_hira(slot["base"] or ""), ""),
        "facts": facts,
        "rel": rel,
        "vocab": [{"w": w["w"], "r": romaji(w["w"], w["tail_wa"]), "m": w["m"]}
                  for w in words],
        "note": note_for(slot, script, ch),
    }
    return card


def build_decks(vg, jmdict, jlpt_readings, word_gloss, kanji_gloss, log=print):
    """Every kana deck, in chooser order, as (manifest entry, cards) pairs. A merged
    deck's cards are None: it is dealt from the files its parts write."""
    by_char = build_pool(jmdict, jlpt_readings, word_gloss)
    all_slots = slots()
    out, thin = [], []
    for deck_id, script, group, label, rom, kinds, tier in DECKS:
        cards = []
        for slot in all_slots:
            if slot["kind"] not in kinds:
                continue
            if script == "hira" and not slot["hira"]:
                continue
            card = make_card(slot, script, slot["no"], vg, by_char, tier, kanji_gloss)
            if len(card["vocab"]) < 6:
                thin.append(card["c"])
            cards.append(card)
        out.append(({"id": deck_id, "label": label, "rom": rom, "group": group,
                     "kind": "kana", "n": len(cards)}, cards))
    if thin:
        log(f"  {len(thin)} kana have fewer than 6 example words: {''.join(thin)}")
    return splice_merged(out)


def splice_merged(decks):
    """The merged decks, each spliced in after the decks it gathers, so the chooser offers
    the whole script at the end of the row it completes. A merged deck carries no cards of
    its own - it names its parts, and the loader deals their files as one pile in slot
    order - so あ reads in 全部 exactly as it reads in 清音, rather than having its example
    words picked over again against a wider syllabary."""
    out = list(decks)
    for deck_id, group, label, rom, members in MERGED:
        at = max(i for i, (meta, _) in enumerate(out) if meta["id"] in members)
        n = sum(meta["n"] for meta, _ in out if meta["id"] in members)
        out.insert(at + 1, ({"id": deck_id, "label": label, "rom": rom, "group": group,
                             "kind": "kana", "n": n, "parts": list(members)}, None))
    return out
