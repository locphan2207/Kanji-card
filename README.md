# Kana & Kanji Drill Card

A single-screen Japanese study app built as a card table: a face-up draw pile, the card
you are studying, and a face-down-ish discard. Draw a card, study it, turn it over to
check the answer, draw again.

The kanji card is modelled on a physical Japanese 漢字ドリル card — landscape, with a
numbered list of compounds, a cross-reference box, a code line, and a practice strip. The
kana card is the same stock asking a much smaller question, so its front is the character
and the stroke order and nothing else.

Two kinds of card, because they ask different questions. A **kanji card** asks which
reading each compound uses; all 2,136 jōyō kanji are here, dealt as five decks by JLPT
level. A **kana card** asks what one character sounds like; the whole syllabary is here —
263 slots across both scripts, dealt as nine decks, and not just the 46 you start with
but the voiced kana, the 拗音 combinations, the sokuon and the long mark, the foreign
sounds katakana borrowed, and the two kana the 1946 reform retired.

Pick a deck on load and that deck — and only that deck — is downloaded, then shuffled.

```
open frontend/index.html          # no build step, no server needed
```

## Layout

```
frontend/
  index.html               markup, and a <template> per kind of card
  src/styles.css           everything visual
  src/app.js               deck loading, deck state, painting, and the flight animations
  data/decks.js            the fourteen decks and their card counts (loaded on every visit)
  data/decks/hira-sei.js   one file per deck, loaded only when picked
  data/decks/n1.js         …
tools/
  build_cards.py           the entry point: sources, the kanji decks, and the manifest
  build_kana.py            the kana decks
  kana_tables.py           the syllabary itself, written out by hand
```

`tools/` sits outside `frontend/` on purpose: it is a data pipeline, not app code. It
runs when the card content changes, not when the page loads.

## Regenerating the data

```
python3 tools/build_cards.py          # ~10s once the sources are cached
```

Writes `frontend/data/decks.js` and `frontend/data/decks/*.js` — both halves, in one
run, from one entry point. Downloads are cached in `tools/cache/` (gitignored, ~30MB), so
reruns are offline. Output is deterministic: rebuilding without changing the sources
leaves the tree untouched.

Nothing on a *kanji* card is hand-written. Every field is derived: the example words and
their glosses from JMdict, readings and meanings and radicals from KANJIDIC2, stroke
paths from KanjiVG, and the cross-references from KanjiVG's component decomposition.

The kana are the exception, and `kana_tables.py` is where they are written out. That is
not laziness in reverse — it is the same argument the other way round. Nobody can hand-
write 2,136 kanji, so those have to be derived; the kana are a closed set of 263 slots
that has not changed since 1946, and the things a kana card actually wants are in no
machine-readable source. Which kanji あ was cursived down from, that シ and ツ are the
pair everyone mixes up, that を is only ever the object particle — none of that is in
KANJIDIC. Writing it out is the honest way to get it right. The stroke paths and the
example words still come from the same pipeline as the kanji cards'.

**Choosing the six example words** is the part with judgement in it. JMdict marks a word
common or not and stops there, so the ranking leans on the JLPT vocabulary lists first,
then prefers words whose kanji the learner has already met, and applies quotas so one
shape of word cannot take the whole card — without them 日 fills with 一日 二日 三日 and
never gets round to 日本. 22 rare kanji (朕, 劾, 摯 …) genuinely have fewer than six
compounds and get what exists.

## Design notes worth keeping

**The card geometry is measured, not invented.** Every position in `src/styles.css` is
a pixel value from the perspective-corrected reference photo divided by 13.8, i.e. a
percentage of card width. The card scales as one drawing.

**Row heights are measured too, which is less obvious.** A card back is a list pinned
inside a box with a top and a bottom, so what the list adds up to has to be known. Left at
`line-height: normal` it isn't: leading comes out of the font file, Klee One leads taller
than the system faces it falls back to, and a card that fitted while the web font was
still loading stopped fitting once it arrived. Four facts and six words at Klee One's
leading stood taller than the box, and `.face{overflow:hidden}` cut the last word in half
— む, which carries the most of both, lost its sixth word outright. So the rows state
their own heights: 4.5cqw for a fact, 3.95cqw for a word, the cells inside leaded tight so
that baseline alignment is reconciling letters rather than three fonts' ideas of leading.
The kana back's stack is 48.5cqw of the 52.5cqw it has, on every card, in any font, at any
width. The kanji back states a floor rather than a height, because a long gloss wraps
there and a wrapped row has to be allowed to grow.

**The stroke strip is KanjiVG vector paths, not type.** A font can't be taken apart into
strokes. This is also why the typeface is Klee One throughout — it is a pen/textbook
design whose letterforms agree with the KanjiVG skeleton. A mincho would disagree with
it (花's 艹 is one connected bar in print, separate strokes by hand).

**Both faces carry content, so the deck has no generic back.** The draw pile holds cards
front-up (unstudied), the discard holds them readings-up (finished). So drawing does not
flip, and discarding does — turning the card over is the act of finishing with it.

**Flight paths are measured at runtime**, centre-to-centre between the card's box and the
pile's box, so they stay correct at any viewport and would survive moving the piles.

**Reading classification.** Each compound is tagged `on` / `kun` / `irr` by checking
whether its reading contains one of the kanji's readings, allowing for rendaku
(かわ→がわ) and sokuon (がく→がっ). What survives is genuine 熟字訓/ateji — 今日 きょう,
梅雨 つゆ — where the compound's reading cannot be derived from its characters. The card
labels that group 特別な読み rather than 熟字訓, because it also catches readings
KANJIDIC simply does not list (日本's 日 = に).

**Cross-references** come from KanjiVG's component decomposition, in both directions: a
kanji is linked to others built from the same component, or — when it is itself a
building block and so has no siblings — to the kanji built out of it. 日 has no parts of
its own, but 明 and 早 are made from it. A shared component that also carries a shared
on-reading is a phonetic series, which is the pairing worth showing, so it scores highest.

## The kana card

A kanji card and a kana card are the same piece of card stock — same stock, same shadow,
same practice strip — but they ask questions of very different size, and the fronts show
it.

**The front is the character and how to write it.** Nothing else. A kanji card's front
has to be dense, because asking which reading each compound takes means printing six
compounds to ask it with; the radical code and the cross-reference box are part of the
same question. A kana card asks what one character sounds like. The glyph and the stroke
order is the whole question, so the front is a large character and a row of practice
squares, and that is the entire design.

It did not start that way. The front also carried the six example words with 圏点 over the
target kana, a 似た字 box, the stroke count and a thumbnail of the gojūon table — a kanji
card's density applied to a card that had nothing like a kanji card's question. Every one
of those was either the answer the back already gave, or decoration. They came off.

**Everything else is the answer, so it is on the back.** The sound in romaji (and kunrei
where the two disagree — し is shi or si), the stroke count, where it sits in the gojūon
table both named and drawn, the kanji it was cursived down from, its counterpart in the
other script, the characters it gets mistaken for with their sounds, six example words
with romaji and glosses, and for the dozen kana that need it a note. The front withholds
exactly one thing, and the back is where you go to get it.

**The gojūon thumbnail is drawn next to the row that names the position.** "か行 あ段"
and a picture of the table with か lit are not the same information; the picture shows you
the shape of the syllabary, with its notches where や lost い and え and where わ kept only
two. It is printed the way the table is printed — a 行 is a column, columns run right to
left, ん sits outside. Built-up kana light the cell of the character underneath them and
hang the ゛or ゜beside it, so ジョ lights シ and still says it is ジョ. It is one `<svg>`
rather than a grid of elements, because at phone width a 0.8cqw grid track rounds up to
the next whole pixel and five of those made the row tall enough to push the word list off
the bottom of the card.

**似た字 is the one thing on the card that no dataset knows.** A kanji card cross-
references kanji sharing a component. A plain kana has no components, so what is worth
saying is which characters it is *confused* with — し／つ, シ／ツ, ソ／ン, and カ／力,
ロ／口, エ／工 where the collision is with a kanji. Those pairs are written out by hand,
because there is nowhere to derive them from. A built-up kana has components after all,
so it gets なりたち instead: が is か plus ゛, きゃ is き plus ゃ. じ and ぢ point at each
other, because that is the pair that actually needs explaining.

**A two-kana card is drawn as one character, because it is one beat.** きゃ is not き then
ゃ; the strip builds き stroke by stroke and then adds ゃ's three, all inside one practice
cell, over a ghost of the finished pair. The two halves are placed by a `(dx, dy, scale)`
triple rather than an SVG transform string so the page can divide the scale back out of
the stroke weight — left alone, ァ at 0.42 would be drawn with a pen less than half as
wide as フ's and all but vanish at card size.

**The strip ends where the strokes do.** A kanji card spreads eight to twenty cells
across the full card width; a kana card has one to nine, so its cells are square, centred
under the character, and the box stops after the last stroke rather than stretching. The
strip is anchored by its bottom edge, because keeping the cells square means its height
follows how many of them there are. Padding the row out to a fixed
width instead — the spare cells carrying the ghost alone, as practice squares to trace —
was tried and read as a rendering failure: on し, five of six cells showed the same
finished kana and taught nothing, and on half the kana the padding was most of the strip.

**A kana and its counterpart share a card number.** か and カ are both 11. The number is
the slot in the syllabary, not the position in a deck, so the two scripts read as one
system seen twice — which is what they are.

**Romaji is kana-transparent.** がっこう comes out `gakkou`, not `gakkō`. The column exists
to say what each character sounds like, and nothing in the data can tell おう the long
vowel (こう) from おう the two vowels (追う, to chase), so spelling it out is the only
answer that is never wrong. ー is the one length mark that is never ambiguous, so it gets
a macron: コーヒー is `kōhī`. Sokuon doubles the next consonant and ち doubles as `t`
(まっちゃ → `matcha`), ん before a vowel takes an apostrophe (しんや → `shin'ya`), and a
word ending in the fossilised topic particle is read `wa` (こんにちは → `konnichiwa`).

**Picking the right homograph is the judgement call.** A kana spelling is usually several
dictionary entries — あか is 赤 and 垢, かてい is 家庭 and 仮定 and 課程 and 過程 — and the
card can show only one. JMdict cannot rank its own homographs, but the JLPT lists pair
each reading with the form it is written in and the level it is tested at, so the easiest
level's form picks the entry and JMdict supplies the wording. It has to be that way
round: the lists gloss 甘い as "generous, sweet", while JMdict orders glosses by
prominence and leads with "sweet".

**Some kana have no words, and the card says so rather than inventing any.** を is only
ever the object particle, so its examples are phrases — えをかく, としをとる — and that is
the truth about を. ヶ is not a kana at all but a shrunken 箇 used for counting. 19 slots
(ぢゃ, ヮ, グァ, the two retired kana …) have fewer than six examples and get what exists,
the same way 22 rare kanji do.

## Why the data is static files, not a database

Card content is read-only at runtime and changes only when the pipeline is rerun, which
makes it a build artifact, not records. Keeping it in files means content edits arrive as
reviewable diffs, the page still opens from `file://`, hosting is a static bucket, and
there is nothing to back up that `build_cards.py` could not regenerate.

Splitting by deck is what keeps that honest at 2,409 cards. The whole set is about 3MB
of mostly stroke geometry; one deck is not:

| deck                  | cards | gzipped |
|-----------------------|------:|--------:|
| kana, each of nine    | 12–46 | 3–11 KB |
| N5                    |    79 |   26 KB |
| N4                    |   168 |   68 KB |
| N3                    |   377 |  165 KB |
| N2                    |   368 |  163 KB |
| N1                    | 1,144 |  555 KB |

The kana half is 254 KB of the 3MB, so a learner who only wants ひらがな 清音 downloads
11 KB. Decks load through a `<script>` tag rather than `fetch`, so the app still runs from
`file://` with no server. Each file calls `KANJI_DECK(id, cards)` — the name the loader
has had since there were only kanji decks, kept so that adding the kana half left the 3MB
of generated kanji files byte-for-byte untouched.

If study progress is ever added, that is the thing with a genuine storage question —
`localStorage` for one device, a database only once progress has to follow a user across
devices. Card content would stay in these files either way.

## Data sources

Card data is derived from open datasets and inherits their licences:

- **KANJIDIC2** — readings, meanings, stroke counts, grades, frequencies, radicals.
  © [EDRDG](https://www.edrdg.org/), CC BY-SA 4.0.
- **JMdict** — the example words, their readings and glosses.
  © [EDRDG](https://www.edrdg.org/), CC BY-SA 4.0.
  Both obtained via [jmdict-simplified](https://github.com/scriptin/jmdict-simplified).
- **KanjiVG** — per-stroke paths and radicals, for the kana as much as the kanji: it
  draws every hiragana and katakana form including the voiced ones, the small ones, ー,
  and the two the 1946 reform retired. © Ulrich Apel, CC BY-SA 3.0.
  <https://kanjivg.tagaini.net>
- **JLPT kanji levels** — via
  [davidluzgouveia/kanji-data](https://github.com/davidluzgouveia/kanji-data), CC BY 4.0.
- **JLPT vocabulary lists** — used to rank example words on every card, and on the kana
  cards also to decide which dictionary entry a kana spelling means, from
  [open-anki-jlpt-decks](https://github.com/jamsinclair/open-anki-jlpt-decks), MIT.
- **Klee One** — typeface, SIL Open Font License 1.1.

The syllabary tables in `tools/kana_tables.py` — the gojūon grid, the 字源 kanji, the
似た字 pairs, the notes — have no upstream. They are written out here.

The EDRDG and KanjiVG licences are share-alike, so `frontend/data/` and anything derived
from it must carry the same terms.

The JLPT has published no official kanji or vocabulary lists since 2010. The N5–N1
grouping here is the usual community reconstruction, not an official list, and the 172
jōyō kanji it does not cover are placed by school grade.

## Not done yet

- **No progress.** Which cards you have seen is not remembered; a reload deals a fresh
  shuffle. This is the one part that needs somewhere to write, and `localStorage` covers
  it long before a database does.
- **N1 is one 555KB download.** Fine on a laptop, heavy on a phone. Stroke paths are
  about two thirds of it and are only needed for the practice strip, so splitting them
  into a second file the deck pulls after the text would cut first paint a lot.
- **Stroke types are dropped.** KanjiVG tags each stroke ㇐/㇑/㇒; nothing reads it, so
  it is no longer emitted. Restoring it is one line in `KanjiVG.get`.
- **Example words are ranked, not chosen.** The quotas stop the obvious failures, but a
  real frequency corpus would beat a JLPT list plus heuristics.
- **No sound.** A kana card is about what a character sounds like and the app never says
  it. This is the largest gap in the kana half; the romaji column is standing in for
  audio it cannot replace.
- **似た字 is one person's list.** Which kana get mixed up is a real, testable thing, and
  the table here is judgement rather than evidence. Confusion data from a real learner
  corpus would beat it.
- **The scripts never mix.** Every deck is one script and one class of form, so nothing
  drills あ against ア, or the whole syllabary at once. Both are small changes to the
  deck definitions in `build_kana.py`, and the card numbers are already shared so a mixed
  deck would number consistently.
- **Drag to draw.** The pile responds to click only.
