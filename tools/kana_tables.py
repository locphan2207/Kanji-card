#!/usr/bin/env python3
"""The kana themselves: every slot in the syllabary, hand-written.

Unlike the kanji tables, which have to be derived from KANJIDIC and JMdict because
nobody can write out 2,524 entries by hand, the kana are a closed set of 263 slots that
has not changed since 1946. Writing them out is the honest way to get them right - the
things a kana card wants (which row it sits in, which kanji it was cursived down from,
which other kana it is mistaken for) are not in any machine-readable source.

A slot is (hiragana, katakana). One side may be None: ー and the foreign-sound
combinations are katakana-only. Card numbers are assigned per slot in the order the
groups appear below, so a kana and its counterpart share a number - か and カ are both
card 11.
"""

# ---------------------------------------------------------------- 清音 (46 slots)
# (hiragana, katakana, hepburn, kunrei-if-different, row, column)
BASIC = [
    ("あ", "ア", "a",   "",    "あ", "あ"), ("い", "イ", "i",   "",   "あ", "い"),
    ("う", "ウ", "u",   "",    "あ", "う"), ("え", "エ", "e",   "",   "あ", "え"),
    ("お", "オ", "o",   "",    "あ", "お"),
    ("か", "カ", "ka",  "",    "か", "あ"), ("き", "キ", "ki",  "",   "か", "い"),
    ("く", "ク", "ku",  "",    "か", "う"), ("け", "ケ", "ke",  "",   "か", "え"),
    ("こ", "コ", "ko",  "",    "か", "お"),
    ("さ", "サ", "sa",  "",    "さ", "あ"), ("し", "シ", "shi", "si", "さ", "い"),
    ("す", "ス", "su",  "",    "さ", "う"), ("せ", "セ", "se",  "",   "さ", "え"),
    ("そ", "ソ", "so",  "",    "さ", "お"),
    ("た", "タ", "ta",  "",    "た", "あ"), ("ち", "チ", "chi", "ti", "た", "い"),
    ("つ", "ツ", "tsu", "tu",  "た", "う"), ("て", "テ", "te",  "",   "た", "え"),
    ("と", "ト", "to",  "",    "た", "お"),
    ("な", "ナ", "na",  "",    "な", "あ"), ("に", "ニ", "ni",  "",   "な", "い"),
    ("ぬ", "ヌ", "nu",  "",    "な", "う"), ("ね", "ネ", "ne",  "",   "な", "え"),
    ("の", "ノ", "no",  "",    "な", "お"),
    ("は", "ハ", "ha",  "",    "は", "あ"), ("ひ", "ヒ", "hi",  "",   "は", "い"),
    ("ふ", "フ", "fu",  "hu",  "は", "う"), ("へ", "ヘ", "he",  "",   "は", "え"),
    ("ほ", "ホ", "ho",  "",    "は", "お"),
    ("ま", "マ", "ma",  "",    "ま", "あ"), ("み", "ミ", "mi",  "",   "ま", "い"),
    ("む", "ム", "mu",  "",    "ま", "う"), ("め", "メ", "me",  "",   "ま", "え"),
    ("も", "モ", "mo",  "",    "ま", "お"),
    ("や", "ヤ", "ya",  "",    "や", "あ"), ("ゆ", "ユ", "yu",  "",   "や", "う"),
    ("よ", "ヨ", "yo",  "",    "や", "お"),
    ("ら", "ラ", "ra",  "",    "ら", "あ"), ("り", "リ", "ri",  "",   "ら", "い"),
    ("る", "ル", "ru",  "",    "ら", "う"), ("れ", "レ", "re",  "",   "ら", "え"),
    ("ろ", "ロ", "ro",  "",    "ら", "お"),
    ("わ", "ワ", "wa",  "",    "わ", "あ"), ("を", "ヲ", "o",   "wo", "わ", "お"),
    ("ん", "ン", "n",   "",    "",   ""),
]

# ------------------------------------------------- 濁音・半濁音 (25 slots)
# (hiragana, katakana, hepburn, kunrei-if-different, base-hiragana, mark)
DAKUTEN = [
    ("が", "ガ", "ga", "",   "か", "゛"), ("ぎ", "ギ", "gi", "",   "き", "゛"),
    ("ぐ", "グ", "gu", "",   "く", "゛"), ("げ", "ゲ", "ge", "",   "け", "゛"),
    ("ご", "ゴ", "go", "",   "こ", "゛"),
    ("ざ", "ザ", "za", "",   "さ", "゛"), ("じ", "ジ", "ji", "zi", "し", "゛"),
    ("ず", "ズ", "zu", "",   "す", "゛"), ("ぜ", "ゼ", "ze", "",   "せ", "゛"),
    ("ぞ", "ゾ", "zo", "",   "そ", "゛"),
    ("だ", "ダ", "da", "",   "た", "゛"), ("ぢ", "ヂ", "ji", "di", "ち", "゛"),
    ("づ", "ヅ", "zu", "du", "つ", "゛"), ("で", "デ", "de", "",   "て", "゛"),
    ("ど", "ド", "do", "",   "と", "゛"),
    ("ば", "バ", "ba", "",   "は", "゛"), ("び", "ビ", "bi", "",   "ひ", "゛"),
    ("ぶ", "ブ", "bu", "",   "ふ", "゛"), ("べ", "ベ", "be", "",   "へ", "゛"),
    ("ぼ", "ボ", "bo", "",   "ほ", "゛"),
    ("ぱ", "パ", "pa", "",   "は", "゜"), ("ぴ", "ピ", "pi", "",   "ひ", "゜"),
    ("ぷ", "プ", "pu", "",   "ふ", "゜"), ("ぺ", "ペ", "pe", "",   "へ", "゜"),
    ("ぽ", "ポ", "po", "",   "ほ", "゜"),
]

# ------------------------------------------------------------- 拗音 (36 slots)
# The い-column kana plus a small ゃゅょ. One mora, not two.
YOON_BASES = [
    ("き", "キ", "ky"),  ("し", "シ", "sh"), ("ち", "チ", "ch"), ("に", "ニ", "ny"),
    ("ひ", "ヒ", "hy"),  ("み", "ミ", "my"), ("り", "リ", "ry"), ("ぎ", "ギ", "gy"),
    ("じ", "ジ", "j"),   ("ぢ", "ヂ", "j"),  ("び", "ビ", "by"), ("ぴ", "ピ", "py"),
]
YOON_SMALL = [("ゃ", "ャ", "a"), ("ゅ", "ュ", "u"), ("ょ", "ョ", "o")]
# Hepburn writes the し/ち/じ series without the y; kunrei keeps the column letter.
YOON_KUNREI = {"sh": "sy", "ch": "ty", "j": "zy"}
YOON_KUNREI_DJI = "dy"          # ぢゃ is dya in kunrei, ja in Hepburn


def yoon_slots():
    out = []
    for i, (bh, bk, stem) in enumerate(YOON_BASES):
        kun_stem = YOON_KUNREI_DJI if bh == "ぢ" else YOON_KUNREI.get(stem, "")
        for sh, sk, vowel in YOON_SMALL:
            hep = stem + vowel
            kun = (kun_stem + vowel) if kun_stem else ""
            out.append((bh + sh, bk + sk, hep, kun if kun != hep else "", bh, sh))
    return out


YOON = yoon_slots()

# ------------------------------------------------- 特殊 (16 slots, 12 of them hiragana)
# Characters that are not syllables: the pause, the vowel-lengthener, the small kana
# that only ever attach to another, the two kana the 1946 reform retired, and ゔ/ヴ.
SPECIAL = [
    ("っ", "ッ", "sokuon", "", "つ"),
    ("ぁ", "ァ", "a", "", "あ"), ("ぃ", "ィ", "i", "", "い"), ("ぅ", "ゥ", "u", "", "う"),
    ("ぇ", "ェ", "e", "", "え"), ("ぉ", "ォ", "o", "", "お"),
    ("ゃ", "ャ", "ya", "", "や"), ("ゅ", "ュ", "yu", "", "ゆ"), ("ょ", "ョ", "yo", "", "よ"),
    ("ゔ", "ヴ", "vu", "", "う"),
    ("ゐ", "ヰ", "i", "wi", ""), ("ゑ", "ヱ", "e", "we", ""),
    (None, "ー", "chōon", "", ""),
    (None, "ヮ", "wa", "", "わ"),
    (None, "ヵ", "ka", "", "か"),
    (None, "ヶ", "ka", "", "か"),
]

# --------------------------------------------------------- 外来音 (31 slots, katakana)
# Sounds Japanese borrowed and the gojuon table has no cell for, written as a kana plus
# a small vowel. The set follows the 1991 cabinet notice on writing loanwords.
FOREIGN = [
    ("イェ", "ye", "イ"), ("ウィ", "wi", "ウ"), ("ウェ", "we", "ウ"), ("ウォ", "wo", "ウ"),
    ("クァ", "kwa", "ク"), ("クィ", "kwi", "ク"), ("クェ", "kwe", "ク"), ("クォ", "kwo", "ク"),
    ("グァ", "gwa", "グ"),
    ("シェ", "she", "シ"), ("ジェ", "je", "ジ"), ("チェ", "che", "チ"),
    ("ツァ", "tsa", "ツ"), ("ツィ", "tsi", "ツ"), ("ツェ", "tse", "ツ"), ("ツォ", "tso", "ツ"),
    ("ティ", "ti", "テ"), ("テュ", "tyu", "テ"), ("トゥ", "tu", "ト"),
    ("ディ", "di", "デ"), ("デュ", "dyu", "デ"), ("ドゥ", "du", "ド"),
    ("ファ", "fa", "フ"), ("フィ", "fi", "フ"), ("フェ", "fe", "フ"), ("フォ", "fo", "フ"),
    ("フュ", "fyu", "フ"),
    ("ヴァ", "va", "ヴ"), ("ヴィ", "vi", "ヴ"), ("ヴェ", "ve", "ヴ"), ("ヴォ", "vo", "ヴ"),
]

# ------------------------------------------------------------------------ 字源
# Each kana is a man'yougana kanji worn down: hiragana is the whole character in cursive,
# katakana a piece of it lifted out. This is the mnemonic that actually explains a shape,
# and the two scripts often disagree about which kanji they came from (え 衣 but エ 江).
ORIGIN_HIRA = {
    "あ": "安", "い": "以", "う": "宇", "え": "衣", "お": "於",
    "か": "加", "き": "幾", "く": "久", "け": "計", "こ": "己",
    "さ": "左", "し": "之", "す": "寸", "せ": "世", "そ": "曽",
    "た": "太", "ち": "知", "つ": "川", "て": "天", "と": "止",
    "な": "奈", "に": "仁", "ぬ": "奴", "ね": "祢", "の": "乃",
    "は": "波", "ひ": "比", "ふ": "不", "へ": "部", "ほ": "保",
    "ま": "末", "み": "美", "む": "武", "め": "女", "も": "毛",
    "や": "也", "ゆ": "由", "よ": "与",
    "ら": "良", "り": "利", "る": "留", "れ": "礼", "ろ": "呂",
    "わ": "和", "を": "遠", "ん": "无", "ゐ": "為", "ゑ": "恵",
}
ORIGIN_KATA = {
    "ア": "阿", "イ": "伊", "ウ": "宇", "エ": "江", "オ": "於",
    "カ": "加", "キ": "幾", "ク": "久", "ケ": "介", "コ": "己",
    "サ": "散", "シ": "之", "ス": "須", "セ": "世", "ソ": "曽",
    "タ": "多", "チ": "千", "ツ": "川", "テ": "天", "ト": "止",
    "ナ": "奈", "ニ": "二", "ヌ": "奴", "ネ": "祢", "ノ": "乃",
    "ハ": "八", "ヒ": "比", "フ": "不", "ヘ": "部", "ホ": "保",
    "マ": "万", "ミ": "三", "ム": "牟", "メ": "女", "モ": "毛",
    "ヤ": "也", "ユ": "由", "ヨ": "与",
    "ラ": "良", "リ": "利", "ル": "流", "レ": "礼", "ロ": "呂",
    "ワ": "和", "ヲ": "乎", "ン": "尔", "ヰ": "井", "ヱ": "恵",
    "ヵ": "箇", "ヶ": "箇",
}

# ----------------------------------------------------------------------- 似た字
# The pairs that actually get mixed up, which is the one thing a kana card can warn about
# that no dataset knows. Ordered worst-offender first; the card shows the first two.
# Kanji are in here on purpose: カ/力 and ロ/口 are the same mistake as シ/ツ.
LOOKALIKE = {
    # hiragana
    "あ": "おめ",  "い": "りこ",  "う": "つらフ", "え": "ん",    "お": "あむ",
    "か": "カや",  "き": "さち",  "く": "へし",   "こ": "いに",  "さ": "きち",
    "し": "つも",  "す": "むお",  "そ": "ろんを", "た": "なに",  "ち": "さらき",
    "つ": "うし",  "と": "ト",    "な": "たは",   "に": "こけ",  "ぬ": "めねわ",
    "ね": "れわぬ", "の": "めあ",  "は": "ほまけ", "ふ": "らう",  "へ": "ヘく",
    "ほ": "はま",  "ま": "はほ",  "み": "ゐそ",  "む": "すお",  "め": "ぬのあ",
    "も": "ちモ",  "や": "ヤか",  "ら": "うち",   "り": "リい",  "る": "ろぬ",
    "れ": "ねわ",  "ろ": "るそ",  "わ": "れねぬ", "を": "そお",  "ん": "そ",
    # katakana
    "ア": "マヤ",  "イ": "リノ",  "ウ": "ワクフ", "エ": "工ユ",  "オ": "才ホ",
    "カ": "力か",  "ク": "ワケタ", "ケ": "クタ",   "コ": "ユロ",  "サ": "セヤ",
    "シ": "ツソン", "ス": "ヌフ",  "セ": "サヤ",   "ソ": "ンシノ", "タ": "クワ夕",
    "チ": "テ千",  "ツ": "シソ",  "テ": "チラ",   "ト": "卜と",  "ナ": "メ十",
    "ニ": "二コ",  "ヌ": "スメヲ", "ネ": "ホ",     "ノ": "ソメン", "ハ": "八ル",
    "フ": "ワウス", "ヘ": "へ",    "ホ": "木ネ",   "マ": "アム",  "ミ": "三",
    "ム": "マヨ",  "メ": "ノヌナ", "モ": "毛も",   "ヤ": "セサ",  "ユ": "コヱ",
    "ヨ": "ムヲ",  "ラ": "テフウ", "リ": "ソり",   "ル": "レハ",  "レ": "ルノ",
    "ロ": "口コ",  "ワ": "クウフ", "ヲ": "ラフヨ", "ン": "ソシノ",
}

# Glosses for the kanji that turn up in 似た字, so the back can say what they are.
KANJI_LOOKALIKE = {
    "力": "power", "口": "mouth", "工": "craft", "才": "talent", "二": "two",
    "八": "eight", "三": "three", "十": "ten", "千": "thousand", "川": "river",
    "夕": "evening", "木": "tree", "毛": "hair", "卜": "divination", "匕": "spoon",
}

# ------------------------------------------------------------------------ 注
# The handful of kana whose behaviour a card has to state outright, because the glyph
# and the romaji together still do not tell you how it is used.
NOTES = {
    "は": "Read wa when it is the topic particle: わたしは.",
    "へ": "Read e when it is the direction particle: がっこうへ.",
    "を": "Written only as the object particle, and said exactly like お.",
    "ん": "The one kana that is not a syllable. It is a beat of its own and never starts a word.",
    "ン": "The one kana that is not a syllable. It is a beat of its own and never starts a word.",
    "ぢ": "Said like じ. Kept only after ち (ちぢむ) and in compounds (はなぢ).",
    "づ": "Said like ず. Kept only after つ (つづく) and in compounds (みかづき).",
    "ヂ": "Said like ジ, and almost never written in modern Japanese.",
    "ヅ": "Said like ズ, and almost never written in modern Japanese.",
    "っ": "Not a sound but a stop: it doubles the consonant after it and takes a full beat.",
    "ッ": "Not a sound but a stop: it doubles the consonant after it and takes a full beat.",
    "ー": "Holds the vowel before it for one more beat. Katakana only - hiragana repeats the vowel.",
    "ゐ": "Retired by the 1946 spelling reform. Read like い; survives in old signage.",
    "ヰ": "Retired by the 1946 spelling reform. Read like イ; survives in old signage.",
    "ゑ": "Retired by the 1946 spelling reform. Read like え; survives in old signage.",
    "ヱ": "Retired by the 1946 spelling reform. Read like エ; survives in old signage.",
    "ゔ": "Writes a foreign v. Rare in hiragana - katakana ヴ does nearly all the work.",
    "ヴ": "Writes a foreign v. Often replaced by the バ row: ヴァイオリン or バイオリン.",
    "ヮ": "Small ワ. Survives only in a few old spellings such as クヮ.",
    "ヵ": "Not a kana but a shrunken 箇, used to count: 三ヵ月. Read ka.",
    "ヶ": "Not a kana but a shrunken 箇, used to count: 三ヶ月. Read ka, never ke.",
}

SMALL_VOWEL_NOTE = ("Small vowel. Fuses with the kana before it into one beat, "
                    "mostly to spell foreign sounds.")
SMALL_YA_NOTE = ("Small {small}. Fuses with an い-column kana into one beat: "
                 "{base} + {small} = {joined}, never {apart}.")
