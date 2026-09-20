# Kana & Kanji Drill Card

A single-screen Japanese study app built as a card table: a face-up draw pile, the card
you are studying, and a face-down-ish discard. Draw a card, study it, turn it over to
check the answer, draw again. Click the discard to take the last one back.

The kanji card is modelled on a physical Japanese 漢字ドリル card — landscape, with a
numbered list of compounds, a cross-reference box, a code line, and a practice strip. The
kana card is the same stock asking a much smaller question, so its front is the character
and the stroke order and nothing else.

Two kinds of card, because they ask different questions. A **kanji card** asks which
reading each compound uses; all 2,136 jōyō kanji are here, dealt as five decks by JLPT
level. A **kana card** asks what one character sounds like; the whole syllabary is here —
263 slots across both scripts, dealt as nine decks by class of form — not just the 46 you
start with but the voiced kana, the 拗音 combinations, the sokuon and the long mark, the
foreign sounds katakana borrowed, and the two kana the 1946 reform retired — plus a 全部
deck per script that gathers all of them, for drilling ひらがな as ひらがな.

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
  data/decks.js            the sixteen decks and their card counts (loaded on every visit)
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

**The discard is the way back.** Clicking it takes the last card you finished with off the
top and deals it to the table, and the card that was on the table goes back on top of the
draw pile — so a draw taken by mistake, or a card turned over before you had really
answered it, costs one click rather than a lap of the whole deck. `revertCard` is
`drawCard` with the two piles swapped: `used.pop()` where the draw took `deck.shift()`,
`deck.unshift()` where the draw pushed onto the discard. Putting it back on *top* is what
makes it an undo rather than a reshuffle — the next draw deals the same card again.

It comes back readings-up, because that is how it was lying. The discard holds cards
readings-up and a card sliding off a pile does not turn over on the way, which is the same
rule that has drawing not flip; and going back to a card you have just finished with is
going back to look at its answer. `f` turns it to the question again. The card travelling
the other way unflips for the same reason: the draw pile holds cards front-up, so putting
one back is exactly the turn that discarding it made, run backwards.

The discard is a `<button>` that is disabled while it is empty, rather than one that does
nothing when pressed — there is no way back from the first card of a deal, and the pile
says so by not offering itself. The same fact drives the third line of the hint, which
only appears once there is something behind you to go back to.

**The pile runs out, and the discard becomes the deck.** Everything you have finished with
is turned over and put back, which is what a person does with a discard: put down the card
in your hand, pick the pile up, turn it over, shuffle it, set it down, and deal. So it is
animated as those things in that order — a discard, a gather, two riffles, a square-up and
a deal — a little over two seconds in all, which a deck earns once a lap, and one press of
the pile is the whole of it.

The card in your hand goes first. It is the last card of the lap and you have finished
with it, so it belongs on the discard before the discard can become the deck: a pile
gathered around the card still in your hand would be everything you had seen except the
one you had just seen. It travels by the same flight a draw sends a finished card on, to
the same pile, landing readings-up.

That empties the table, which is why the reshuffle ends by dealing off the pile it has
just made. A full deck and nothing to study is not a state this table has — it is the same
reason the opening deal sends a card to the stage while the pile is still landing rather
than after it.

The card you just finished with is in that shuffle like any other, so it can come back on
top: one lap in twelve on 特殊, one in seventy-nine on N5, one in 1,144 on N1. That is
what a shuffle is, and moving it would be the animation telling you a shuffle happened
while quietly arranging that it hadn't.

Six cards stand in for the whole pile, as in the deal, and each carries its share of the
count across — the discard gives its share up as the card leaves, the pile takes it as the
card lands, so for a moment the two tags do not add up to the deck. That difference is the
cards in the air, which is where they are.

Each one turns over on the way, because the discard lies readings-up and the draw pile
lies front-up: a card crossing between them is exactly the turn that discarding it made,
run backwards. It is the rule the undo already runs on, applied to a whole pile one card
at a time. The turn is finished by the time the card is a third of the way across, so what
the rest of the flight shows is the face the pile is about to be holding.

**A gather cannot be honest at both ends**, and that decides the shape of the rest of it.
What leaves the discard is what is lying on it, top card first. What the pile is left
holding is whatever the shuffle decides, and those are not the same cards. So the pile
shows the card that really landed on it right up to the moment the riffle starts, and from
there it shows no top card at all — a pile being shuffled has none to show, and a pile
being dealt off has the dealt card covering it. The face it is left with is the one the
shuffle put there, uncovered by the card leaving for the stage rather than faded in over
it: the deal is the one moment in a reshuffle where changing the top card needs nothing to
hide the change, because the card on top of it is already leaving. Nothing untrue is on
screen at rest.

**The riffle is drawn with the pile's own layers.** A pile here is already one layer per
card, so a shuffle is those layers splitting into two packets, leaning apart and falling
back. The packets falling *alternately* — deepest card of one, then deepest of the other —
is what makes it a riffle rather than two halves rejoining, which is a cut. Two passes,
mirrored, because nobody shuffles a deck once.

What five flat rectangles 1.5px apart do not have is texture, so the separation is the
only signal there is and it has to be taken: the packets part by a fifth of the pile's
width, far enough to read as two objects and not so far that the pile stops being one.
The layers keep their own stacking offsets underneath — `composite:"add"` lays the riffle
over the 1.5px step each one already carries, and a browser that does not understand it
riffles a flat pile, which is the whole of what that costs.

A reshuffle also outlives the click that started it by long enough for the chooser to have
been opened and a different deck dealt underneath it, which nothing else here does. `hand`
counts deals, and a gather that lands after the table has changed hands lands on nothing
rather than putting the old deck back.

**The empty draw pile was painted black, and had been for as long as the pile was the
thing you click.** There was a Draw button once, styled `.draw`; it went when the pile
took its job, and its rules stayed. The draw pile is `class="pile draw"` — same
specificity as `.pile`, further down the file — so `background:var(--ink)`, a 2px radius,
30px of padding and a hover transform were all landing on it, and the black showed through
the moment the layers went. Which is precisely the pile you are looking at when the deck
runs out, and the one a gather flies cards onto. Two piles that are one object in two
states now compute as one, and the ids on the count tags went the same way: `renderPile`
finds the count inside the pile it is drawing, because the count is part of what a pile
shows and not a thing the caller remembers to update.

**Flight paths are measured at runtime**, centre-to-centre between the card's box and the
pile's box, so they stay correct at any viewport and would survive moving the piles. A
flyer is always built at the size of where it *lands* and animated back from where it came
— a flight that finishes on its target's own box cannot land crooked however the viewport
is sized.

**Picking a deck deals it.** The lid lifts off the box where the box is standing, the
table fades up in the chooser's place, and the deck that was inside flies over: six cards
stack up as the pile, and one carries on to the stage. The two overlap rather than queue.
Dealing the pile first and the stage card after was the obvious order and it left the top
two-thirds of the screen empty for the length of the deal, which reads as a broken layout
rather than as a deal.

The cards in flight are real cards — `makeFlyer` paints them with the same code the pile
and the table use — and they are the actual indices from the top of the shuffled deck, so
the card you watch land is the card sitting there when it stops. That is also why they are
dealt back to front: `deck[0]` is the pile's top card, so it has to be the last one down.
Six, because the pile is five layers deep and a sixth reads as "and the rest".

The pile and the stage card are held hidden and revealed underneath the flyers that land
on them. Since a flyer finishes on exactly the box the real thing occupies, the swap has
nothing to show. `busy` is held for the length of it, so the pile cannot be drawn from
before it has arrived, and `prefers-reduced-motion` skips the whole thing — the table is
simply there.

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

**A deck is a box, and the boxes are all the same size.** The chooser used to show a deck
as a small card with its name on it, which said nothing a line of text could not. A deck
of cards comes in a box, so it is drawn as one — as a solid, not as a picture of one.
The printed front, the top and the left wall, in cabinet projection, at the footprint the
flat drawing always had: the front gives up exactly the projected depth in width and
height, so a box occupies its slot the way it did before it had volume.

It recedes up and to the left because that is the direction the deck recedes on the table.
The piles stack their layers up-left, so a pile shows its card edges along its top and
left; a box that showed its depth on the right would be the same object turned two
different ways on two screens.

**The walls are 2D skews, and that is the whole reason this is usable.** Rotating the
front in 3D was tried first and it is the obvious way to build a box: `preserve-3d` on the
button, `rotateX`/`rotateY`, a wall hinged on each edge. It looks right and it destroys the
type. A 3D-transformed element is rasterised once and then resampled, and at 132px that
turns 漢字ドリル and 第993–2136番 into mush — the deck's name, which is the one thing the
chooser exists to show. Skewing only the two turned-away walls leaves the front
untransformed, so every glyph on it is drawn at the device's own resolution. It also keeps
what was true of the flat version: no perspective, no 3D context, no compositing layer per
box, and a hover that is still one `translateY`.

The front is a container of its own, so the printing is measured against the front rather
than against the slot. That is what lets the depth be a single number: change `--bx-d` and
the front, both walls and everything printed on the front resize together.

Two earlier attempts got this wrong. The first drew a landscape panel with a sliver along
its foot and printed the sliver with a repeating 1.5px rule to suggest depth — but evenly
spaced cut edges are the picture of *a pile of cards*, so the one detail meant to say "box"
was the detail saying "stack". The second replaced the sliver with a lid sitting in a
tray, which reads as a container, but the container it reads as is a gift box. Both were
drawing a box flat and hoping a detail would carry it. Nothing had to carry it once the
box was actually drawn as a solid. A thumb notch was tried and taken off as well — the
right detail on a real box, but it took a bite out of every label.

**What is printed on a box is the deck's own data.** A 和柄 ground says which of the three
series a box belongs to from across the room — 青海波 for ひらがな, 鱗 for カタカナ, 格子 for
漢字, which on the kanji boxes reads as the 方眼紙 the practice is done on — and its scale
steps through the volumes, so 拗音 is not the same object as 清音. Over it sits the drill
workbook's block of type: the deck name, the romaji, and along the foot `第80–247番` and
`全168枚`. The range is real. Every deck's card numbers are contiguous, because a card
number is the slot in the syllabary or the jōyō index and the decks partition those in
order, so `build_cards.py` writes each deck's `lo` and `hi` into the manifest and a box can
say what it holds without the deck being downloaded. The five kanji boxes tile 1–2136 with
no gaps; か and カ share a card number, so ひらがな清音 and カタカナ清音 print the same range,
which is the two scripts being one system seen twice, printed on the packaging. A merged
deck has no cards of its own to measure, so it takes the span of its parts — `第1–119番`
for ひらがな 全部, which is the only line on the box that says outright that it holds
everything the four beside it do.

The 印 stamped with the volume numeral is 朱 on every box in every series. 全部 is stamped
全 instead: it gathers 巻一 to 巻四 rather than following them, and a boxed set's omnibus is
not volume five.

**A series is printed on its own stock.** A workbook series is the same design on a
different coloured cover per volume, and that is what the three categories are — 藍 for
ひらがな, because 青海波 has 青 in its name; 青磁 for カタカナ, the glaze 鱗 (scale armour)
is drawn in; 山吹 for 漢字, gold, which is what makes 格子 read as the 方眼紙 the practice
is done on rather than as brown lines. They are a progression rather than three unrelated
hues, because the rows are stacked and read in order.

A series states two values, `--spot` and `--wash`, because ink and stock are two
different choices. The ink is saturated, since it is mixed into warm greys and a grey
eats chroma — a muted ink mixed into a muted grey came out as the grey, which was the
first attempt and looked like nothing had been done. The wash is the same hue at the
paper's own lightness, so the stock changes colour without changing how dark it is;
mixing the ink into the paper instead made each deck's card as much darker as its ink
happened to be, which is a difference nobody chose. Everything else is mixed from those
two, so a series is two lines of CSS and the rest follows.

**A card is printed on the stock its box is, at 40% of the weight.** The box no longer
owns the colour; the series does, and a card that comes out of an indigo box is an
indigo card. But a box and a card are not the same object, so the wash is not applied at
the same strength to both. A box is packaging, seen once from across a grid of sixteen
at 132px, and the wash at full strength is what carries the series across that screen. A
card is read for minutes at a time, and the same wash, once it is the page rather than
the cover, stops being a stock with a colour and becomes a coloured surface. So
`[data-cat]` states the card's stock at 40% and `[data-cat] .slot` restates the box's at
82%, and the card, the pile layers and the card in flight all take the first from one
place.

40% is where three things are true at once: the stock still says plainly which deck this
is, the black type keeps its bite, and — the one that actually fixes the number — the
head band stays clear of the card it is printed on. The band is mixed from `--wash`
rather than from `--stock`, so its colour does not move when the wash does; the stronger
the card's wash, the less of a band the band is. At 82% it stood about 24 points of
luminance off the card, which is the same step the tracing ghost has; at 40% it stands
38 apart and reads as printing again.

It was cream first, and the argument for that was a good one — the one restated above,
that a page read for minutes should not be a colour. So the card kept its cream and the
series showed **on its edge**: a stack of cards presents its edges and nothing else, and
the piles here are built from real offset layers, so colouring the edge made the draw
pile and the discard come out striped in the series' colour with nothing drawn for them.

What that misses is that a card is only ever looked at inside the deck it belongs to.
You pick one box, and from then on every card on the table is from it, so a cream card
was not standing next to anything for its cream to be read against — the colour had one
job left, which was to be noticed, and an edge thick enough to be noticed (`.4cqw`, so
that it read as the cut edge of coloured card rather than as a keyline) is a frame
round the page. A frame is the one thing on a card that is always in your eye and never
what you are reading. The wash is the opposite: it is everywhere, and so nowhere in
particular — and, held to 40%, it is a tinted paper rather than a colour. The rim went
back to the 1px hairline the box's own front has, and the piles are still striped,
because the layers are this stock now.

Cream with the band alone was tried at this point too, and it is the one that looks
wrong: a solid coloured strip across the top of a white rectangle with a number in the
corner is the shape of an app's title bar, and that is what it reads as. A band is
printing only when the card under it is already printed stock.

The tracing ghost is the one grey a series does not touch, and that is the rule the
scheme runs on now: **the colour is the stock and the printing on it, never the thing
being read.** The ghost is a guide you draw over — the answer laid on the paper before
you write it — so a tinted one read as a second ink competing with the stroke being
taught, which was also what ruled out the tinted practice strip tried early on. It is
`--ghost-0` in all three series. It did have to change once: it was mixed for cream, and
a warm grey on an indigo card goes tan and on a celadon one goes pink, so it is near
enough to neutral now to stay grey on any of the three, and 30 points of luminance
darker to keep the same step under a stock that is no longer cream.

**The band across the head is the box's own ground.** The other half of what the edge
used to do was to say *which* deck, and the stock only says which of three. So the top
of every face carries a strip of the 和柄 its box is printed with, on the wash pulled a
step further towards the ink — and the tile steps through the volumes exactly as the
box's does, so a 拗音 card is printed with the coarser wave the 拗音 box is. `deal()`
sets `--ps` on `<body>` the way `deckBox()` sets it on a box, in the card's own `cqw`
rather than the box's: what carries across is the step, not the number, because a card
is five times the width of a box and each is measured against itself. The tile is kept
under the band's height there, because a band is one course of a pattern and a tile
taller than the band is a row of cropped halves rather than 鱗.

A band was tried once before, when the card was still cream, and it read as a title bar
rather than as print. Two things are different now. It is not a coloured bar on white —
it is the same stock as the rest of the card, printed heavier, so the card has no edge
inside it for a bar to have. And it carries the pattern rather than being a plain fill,
which is what makes it a 和柄 border and not a header. The hairline under it is the rule
at the head of a printed page. It is one element on each face, `aria-hidden`, holding no
text: it is stock, not content. The head is also the one part of the stock every face
already left empty — a ground behind the type would be a ground you read through, and
青海波 behind 天気予報 is a texture in the way.

**The band is the top of the card now, so the head margins are measured from it.** Every
face was laid out against the stock's own edge, and dropping a 3.2cqw band on top of
that left the four of them with wildly different head margins: 2.8cqw of clear stock on
both fronts, where the first mark is the card number, but 1.0cqw on the kana back and
0.49cqw on the kanji back, where the first mark is a display character that all but
touched the band. The fix is the obvious one — move the header blocks down — and the
only interesting part is where the room came from.

The kana back had room below: its header, its rule and its body all drop 1.6cqw
together, so the face keeps its proportions and only its head margin changes. That costs
`.kn-body` 1.6cqw of the 3.95cqw the fullest card in either syllabary leaves it.

The kanji back had none. 傲 (#2042) is the tightest card in the jōyō set and leaves
`.bk-groups` 0.83cqw of slack, so the rule and the list under it cannot move at all
without costing a compound its row — which means the 1.4cqw the header moves has to come
out of the air above the rule. It ends up with about 1.8cqw of clear stock under the
band and 1.2cqw above the rule, and that asymmetry is right rather than a compromise:
the band is a solid and the rule is a hairline, so the heavier edge takes the wider gap.
The kana front's glyph box moved for a different reason — it began 0.2cqw *under* the
band, which was invisible, because the character is centred in a box far taller than it
is, but a box the band overlaps is one bad font away from being clipped by it.

A corner index was the other alternative, and it still collides with the big character
on both backs. The desk keeps out of all of it, because the desk is the room the cards
are in, not one of them.

**The three grounds do not take the same amount of ink.** 青海波 is a field of thin arcs,
鱗 is solid triangles that fill half the box, and 格子 is a grid of single pixels. Given
one alpha, the katakana boxes printed twice as heavy as the kanji ones, which read as that
series being louder rather than as that pattern being denser — and only the second was
true. So each ground states its own strength: what is matched across the three is how dark
the box looks, not what the ink is set to.

The colour earns most at phone width, which is not where it was designed. On a desktop the
three rows are stacked with their names beside them and you can see all sixteen boxes at
once. On a phone the name column is gone, the rows are two boxes wide and a screen apart,
and the thing that tells you which series you are scrolling through is that the boxes went
from blue to green.

**A box is measured against its own width, like the card.** Every position printed on a
box is in `cqw` against the slot — 132px wide is 100cqw, so 11px of margin is 8.33cqw and
the ground's tile scales with it too. This is what lets the chooser be laid out for a
phone by changing nothing but how wide a box is. Under 560px the name column goes, since
74px of a 343px screen is a quarter of it spent on three characters, and the row stops
being a queue of 132px boxes with the leftover width sitting beside them: the boxes divide
the row between them, two to a row on a phone and three by 560px. A box at 165px is the
same drawing as a box at 132px, printed larger — not the same small box with its type left
at the size it was set for a mouse pointer. The page was also held to `height:100%` while
centring its contents, which on a phone put the title and the first row of boxes above the
top of the document, where no scroll could reach them; it is a `min-height` now.

**The category is named in English as well.** ひらがな HIRAGANA, カタカナ KATAKANA, 漢字
KANJI, set beside the row the way the romaji is set under a deck name. Someone who cannot
yet read kana cannot tell the three rows apart, which is the state everyone using this
starts in. Only the category is named: 清音 and 濁音 are classes of kana with no English
name shorter than a sentence, and the box already prints their romaji. The names live in
`GROUP_EN` in `app.js` rather than in the manifest, because they label the screen and not
the cards — nothing in `data/` changes.

**The lamp switches the room, not the table.** Both desks were always drawn — the
stylesheet has had a `prefers-color-scheme` block since the beginning — and what was
missing was a way to disagree with the system. So the switch is one attribute,
`data-theme` on `<html>`, which the stylesheet already honours: `[data-theme="dark"]`
restates the dark desk, and the media query is scoped `:not([data-theme="light"])` so a
pinned light desk survives a dark OS.

No attribute is a third state, and it is the one the page starts in — the system's
choice, live. A page nobody has switched follows the OS over at dusk, and the button's
label follows it too. Pressing the button is what stops it following, which is why
nothing is written to `localStorage` until then: a value stored on load would freeze
whatever the OS happened to be saying into a choice the reader never made.

The button offers the room you are not in, so its face is the light you would switch on
rather than the one that is already on — 夜 DARK on a light desk, 昼 LIGHT on a dark one,
the kanji and the word for it together the way a pile carries both 済 and 済み. Two
things fall out of the switch existing rather than being inferred from the OS. A theme
forced against the system has to pin `color-scheme` as well, or the one part of the page
the page does not draw — scrollbars, the UA's own focus ring — stays in the room the rest
of it just left. And the remembered choice has to be on `<html>` before first paint, so
that much runs from a `<script>` in the `<head>`; a dark room that opens as a flash of a
light one is worse than no switch at all.

It is a child of `<body>` rather than of either screen, which keeps it in one place while
the chooser gives way to the table and back, and it is in the flow rather than fixed to a
corner: the card is `min(94vw,680px)`, so on a phone a corner is the corner of the card.
It sizes itself to the chooser's 960px rather than the table's 680px so that picking a
deck does not move it — the two screens are different widths and the switch belongs to
neither.

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
| ひらがな 全部         |   119 |   28 KB |
| カタカナ 全部         |   154 |   34 KB |
| N5                    |    79 |   26 KB |
| N4                    |   168 |   68 KB |
| N3                    |   377 |  165 KB |
| N2                    |   368 |  163 KB |
| N1                    | 1,144 |  555 KB |

The kana half is 254 KB of the 3MB, so a learner who only wants ひらがな 清音 downloads
11 KB. The two 全部 decks add nothing to that total: a merged deck has no file of its own
but names the decks it gathers, and the loader deals their files as one pile — so the
whole of ひらがな costs its four parts and nothing more, and those parts are already in
hand for anyone who drilled 清音 before picking 全部. Decks load through a `<script>` tag
rather than `fetch`, so the app still runs from `file://` with no server. Each file calls
`KANJI_DECK(id, cards)` — the name the loader has had since there were only kanji decks,
kept so that adding the kana half left the 3MB of generated kanji files byte-for-byte
untouched.

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
  shuffle. This is the part that most wants somewhere to write, and `localStorage` — which
  the theme switch already uses — covers it long before a database does.
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
- **The scripts never mix.** A 全部 deck gathers one script, so nothing drills あ against
  ア. That is one more row in `MERGED` in `build_kana.py` naming all nine decks, and the
  card numbers are already shared — あ and ア are both 1 — so a mixed deck would number
  consistently, but it would also deal the same syllable twice in two costumes, which is
  a different exercise and wants thinking about before it is a deck.
- **Drag to draw.** Both piles respond to click only.
