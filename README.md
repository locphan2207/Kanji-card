# Kanji Drill Card

A single-screen kanji study app built as a card table: a face-up draw pile, the card
you are studying, and a face-down-ish discard. Draw a card, study it, turn it over to
check the readings, draw again.

The card itself is modelled on a physical Japanese 漢字ドリル card — landscape, with a
numbered list of compound words, a cross-reference box, a `strokes-radical-remainder`
code, and a practice strip.

```
open frontend/index.html          # no build step, no server needed
```

## Layout

```
frontend/
  index.html          markup and script tags
  src/styles.css      everything visual
  src/app.js          deck state, painting, and the flight animations
  data/cards.js       generated card data (see below)
tools/
  deck.json           the curated half: words, readings, glosses, component pairs
  build_cards.py      regenerates frontend/data/cards.js
```

`tools/` sits outside `frontend/` on purpose: it is a data pipeline, not app code, and
it is the part a backend will eventually absorb when card data moves into a database.

## Regenerating the data

```
python3 tools/build_cards.py
```

Writes `frontend/data/cards.js`. Downloads are cached in `tools/cache/`
(gitignored), so reruns are offline.

`tools/deck.json` is the hand-written content — the six example words per kanji with
their readings and glosses, and which kanji to cross-reference. Everything else is
derived: stroke paths, stroke types, radicals, readings, meanings, grades, frequencies.

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

## Data sources

Card data is derived from open datasets and inherits their licences:

- **KANJIDIC2** — readings, meanings, stroke counts, grades, frequencies.
  © [EDRDG](https://www.edrdg.org/), CC BY-SA 4.0. Obtained via
  [davidluzgouveia/kanji-data](https://github.com/davidluzgouveia/kanji-data).
- **KanjiVG** — per-stroke paths, stroke types, radicals.
  © Ulrich Apel, CC BY-SA 3.0. <https://kanjivg.tagaini.net>
- **Klee One** — typeface, SIL Open Font License 1.1.

Both data licences are share-alike, so `data/cards.js` and anything derived from it must
carry the same terms.

## Planned

When a second screen appears (deck selection, progress, settings), this moves to
**SvelteKit** — which runs on Vite, so `data/cards.js` becomes a real `fetch` and the
card table stays an imperative module that Svelte mounts. Until then the buildless
version is deliberate: the flight animations measure live DOM and append cloned nodes
outside any component tree, which is awkward to express declaratively and costs nothing
to keep as plain DOM code.

## Not done yet

- **20 kanji, not 2,136.** Readings, stroke data and radicals scale from open data for
  the full jōyō set. The example words do not — six good compounds per kanji is the
  real remaining work, and the reason `tools/deck.json` exists as a separate file.
- **Deck numbers are frequency ranks** standing in for a real ordering. The reference
  card numbers 者 as 240 and 考 as 239 because that deck groups by shared component.
- **No backend.** `frontend/data/cards.js` is the seam: replace it with a fetch that
  assigns the same shape to `CARDS`.
- **Drag to draw.** The pile responds to click only.
