# Kanji Drill Card

A single-screen kanji study app built as a card table: a face-up draw pile, the card
you are studying, and a face-down-ish discard. Draw a card, study it, turn it over to
check the readings, draw again.

The card itself is modelled on a physical Japanese 漢字ドリル card — landscape, with a
numbered list of compound words, a cross-reference box, a `strokes-radical-remainder`
code, and a practice strip.

All 2,136 jōyō kanji are included, dealt as five decks by JLPT level. Pick a level on
load and that deck — and only that deck — is downloaded, then shuffled.

```
open frontend/index.html          # no build step, no server needed
```

## Layout

```
frontend/
  index.html          markup and script tags
  src/styles.css      everything visual
  src/app.js          deck loading, deck state, painting, and the flight animations
  data/levels.js      the five levels and their card counts (loaded on every visit)
  data/levels/n5.js   one deck per level, loaded only when picked
  data/levels/n1.js   …
tools/
  build_cards.py      regenerates everything under frontend/data/
```

`tools/` sits outside `frontend/` on purpose: it is a data pipeline, not app code. It
runs when the card content changes, not when the page loads.

## Regenerating the data

```
python3 tools/build_cards.py          # ~10s once the sources are cached
```

Writes `frontend/data/levels.js` and `frontend/data/levels/n*.js`. Downloads are cached
in `tools/cache/` (gitignored, ~30MB), so reruns are offline.

Nothing on a card is hand-written any more. Every field is derived: the example words
and their glosses from JMdict, readings and meanings and radicals from KANJIDIC2, stroke
paths from KanjiVG, and the cross-references from KanjiVG's component decomposition.

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

## Why the data is static files, not a database

Card content is read-only at runtime and changes only when the pipeline is rerun, which
makes it a build artifact, not records. Keeping it in files means content edits arrive as
reviewable diffs, the page still opens from `file://`, hosting is a static bucket, and
there is nothing to back up that `build_cards.py` could not regenerate.

Splitting by level is what keeps that honest at 2,136 cards. The whole set is about 3MB
of mostly stroke geometry; one deck is not:

| deck | cards | gzipped |
|------|------:|--------:|
| N5   |    79 |   26 KB |
| N4   |   168 |   68 KB |
| N3   |   377 |  165 KB |
| N2   |   368 |  163 KB |
| N1   | 1,144 |  555 KB |

Decks load through a `<script>` tag rather than `fetch`, so the app still runs from
`file://` with no server. Each file calls `KANJI_DECK(id, cards)`.

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
- **KanjiVG** — per-stroke paths and radicals. © Ulrich Apel, CC BY-SA 3.0.
  <https://kanjivg.tagaini.net>
- **JLPT kanji levels** — via
  [davidluzgouveia/kanji-data](https://github.com/davidluzgouveia/kanji-data), CC BY 4.0.
- **JLPT vocabulary lists** — used only to rank example words, from
  [open-anki-jlpt-decks](https://github.com/jamsinclair/open-anki-jlpt-decks), MIT.
- **Klee One** — typeface, SIL Open Font License 1.1.

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
- **Drag to draw.** The pile responds to click only.
