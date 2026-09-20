const $ = id => document.getElementById(id);
const card = $("card"), stage = $("stage");
const drawPile = $("drawPile"), usedPile = $("usedPile");
/* Whether a move is flown across the table or simply made. Asked at the start of each
   move rather than settled once at load, because the room has a switch for it now and it
   can be thrown between one draw and the next. What it asks is at the foot of this file,
   beside the lamp — the other switch on the same wall. */
const prefersStill = matchMedia("(prefers-reduced-motion: reduce)");
const still = () => motionNow() === "none";

const kata = s => s.replace(/[ぁ-ゖ]/g, c => String.fromCharCode(c.charCodeAt(0) + 0x60));
const okuri = s => s.replace(/^-/, "〜").replace(/\.(.+)$/, "（$1）");
const shuffle = a => { for (let i = a.length - 1; i > 0; i--) {
  const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const settle = ms => new Promise(resolve => setTimeout(resolve, ms));

let CARDS = [], DECK = null, KIND = "kanji";
let deck = [], used = [], current = -1, busy = false, flipped = false;
/* Which deal is on the table. Only a reshuffle reads it: it is the one thing here that
   outlives the click that started it by long enough for the table to have been given a
   different deck underneath it. */
let hand = 0;

/* Two card shapes, kept as templates rather than one live node, because a deck is all
   one kind and the table only ever holds cards from one deck. */
const faces = kind => $(kind === "kana" ? "tplKana" : "tplKanji").content.cloneNode(true);

function cardNode() {
  const el = document.createElement("div");
  el.className = "card";
  el.appendChild(faces(KIND));
  return el;
}

/* One cell of the practice strip: a grey ghost of the finished character with the
   cumulative build painted over it. `tx` places each stroke as (dx, dy, scale), which is
   how a two-kana card draws きゃ as one drawing — き at size beside a small ゃ. The scale
   goes to CSS as well as to the transform, so the pen stays the same width at both
   sizes instead of thinning out with the glyph. */
function cell(paths, tx, n) {
  const d = ss => ss.map((s, i) => {
    const t = tx && tx[i];
    return t
      ? `<path transform="translate(${t[0]},${t[1]}) scale(${t[2]})" style="--s:${t[2]}"`
        + ` d="${s}"/>`
      : `<path d="${s}"/>`;
  }).join("");
  return `<div class="cell"><svg viewBox="0 0 109 109" aria-hidden="true">` +
    `<g class="gh">${d(paths)}</g><g class="dr">${d(paths.slice(0, n))}</g></svg></div>`;
}

/* Paints any card-shaped node, so the table card, the pile tops and the flying card
   are all produced by the same code and can't drift apart visually. */
function paint(root, c) {
  (KIND === "kana" ? paintKana : paintKanji)(root, c);
}

function paintKanji(root, c) {
  const q = s => root.querySelector(s);
  q(".front .no").textContent = c.no;
  q(".glyph").textContent = c.k;
  q(".vocab").innerHTML = c.vocab
    .map((v, i) => `<li><span class="n">${i + 1}.</span>${v.w}</li>`).join("");
  q(".related").innerHTML = c.rel.map(r =>
    `<div class="rel"><span class="rn">${r.no}</span><span class="rk">${r.k}</span>` +
    (r.s ? `<span class="rs">${r.s}</span>` : "") +
    `<span class="rg">${r.g}</span></div>`).join("");
  q(".code").innerHTML =
    `<span>${c.strokes}-${c.radN}-${c.restN}</span><span class="rad">${c.rad}</span>`;
  q(".strip").innerHTML = c.paths.map((_, i) => cell(c.paths, null, i + 1)).join("");

  const on = c.on.map(kata).join("・"), kun = c.kun.map(okuri).join("・");
  q(".back .no").textContent = c.no;
  q(".bk-k").textContent = c.k;
  q(".bk-m").textContent = c.mean;
  const GROUPS = [["on", "音読み", on], ["kun", "訓読み", kun],
                  ["irr", "特別な読み", ""]];
  q(".bk-groups").innerHTML = GROUPS.map(([key, label, reading]) => {
    const rows = c.vocab.filter(v => v.t === key);
    if (!rows.length) return "";
    return `<div><div class="bk-head"><b>${label}</b><span>${reading}</span></div>` +
      rows.map(v => `<div class="bk-row"><span class="r">${v.r}</span>` +
        `<span class="w">${v.w}</span><span class="g">${v.m}</span></div>`).join("") +
    `</div>`;
  }).join("");
}

/* The gojuon table's shape: which of the fifty cells the syllabary actually filled.
   や never took い or え, わ kept only あ and を, and ん sits outside the table. */
const GOJUON = [        // あ か さ た な は ま や ら わ, each read as あいうえお
  [1, 1, 1, 1, 1], [1, 1, 1, 1, 1], [1, 1, 1, 1, 1], [1, 1, 1, 1, 1], [1, 1, 1, 1, 1],
  [1, 1, 1, 1, 1], [1, 1, 1, 1, 1], [1, 0, 1, 0, 1], [1, 1, 1, 1, 1], [1, 0, 0, 0, 1],
];

/* A thumbnail of that table with this card's cell inked, drawn beside the row that names
   the position in words — seeing where か sits lands differently from reading "か行 あ段".
   The table is printed in columns running right to left, so a 行 is a column, not a row. */
function gojuon(c) {
  const S = 3, G = 1;                   // cell and gap, in viewBox units
  let out = "";
  for (let dan = 0; dan < 5; dan++) {
    for (let col = 0; col <= 10; col++) {
      const gyou = 10 - col;            // column 0 is ん, then わ ら や … あ
      const there = col === 0 ? dan === 0 : GOJUON[gyou][dan];
      if (!there) continue;
      const here = c.map === "n" ? col === 0 && dan === 0
        : Array.isArray(c.map) && c.map[0] === gyou && c.map[1] === dan;
      out += `<rect class="${here ? "here" : "on"}" width="${S}" height="${S}"` +
        ` x="${col * (S + G)}" y="${dan * (S + G)}"/>`;
    }
  }
  // One <svg> rather than a grid of elements: at phone width a 0.8cqw grid track rounds
  // up to the next pixel, and five of those made the row tall enough to push the word
  // list off the bottom of the card. A viewBox scales exactly.
  return `<svg class="map" viewBox="0 0 ${11 * (S + G) - G} ${5 * (S + G) - G}"` +
    ` aria-hidden="true">${out}</svg>` +
    (c.mark ? `<span class="mmark">${c.mark}</span>` : "");
}

/* The front is the character and how to write it, and nothing else. Everything a kana
   card used to carry here — the example words, the kana it is confused with — is the
   answer to the question the front is asking, and the back already had all of it. */
function paintKana(root, c) {
  const q = s => root.querySelector(s);
  const two = c.c.length > 1;
  q(".front .no").textContent = c.no;
  // one text run, not a span per character: きゃ is one unit, and the font already knows
  // how big a small kana is beside a full one
  q(".kn-glyph").className = "kn-glyph" + (two ? " two" : "");
  q(".kn-glyph").textContent = c.c;
  q(".strip").innerHTML = c.paths.map((_, i) => cell(c.paths, c.tx, i + 1)).join("");

  q(".back .no").textContent = c.no;
  q(".kn-c").className = "kn-c" + (two ? " two" : "");
  q(".kn-c").textContent = c.c;
  // sokuon and chouon are names rather than sounds, and too long to set at full size
  q(".kn-rom").className = "kn-rom" + (c.hep.length > 4 ? " long" : "");
  q(".kn-rom").textContent = c.hep;
  q(".kn-alt").textContent =
    [c.code, c.kun && `kunrei ${c.kun}`].filter(Boolean).join(" \u00b7 ");
  // 元 and 小 are already spelled out by the なりたち fact, so only the lookalikes and
  // the kanji they collide with are worth a row of their own.
  const sim = c.rel.filter(r => r.l === "似" || r.l === "漢");
  q(".kn-facts").innerHTML = c.facts.map(([label, value, hint]) =>
    `<div class="kn-fact"><b>${label}</b><span class="v">${value}</span>` +
    `<span class="h">${hint}${label === "五十音" && c.map ? gojuon(c) : ""}</span>` +
    `</div>`).join("") +
    (sim.length ? `<div class="kn-fact"><b>似た字</b><span class="v">` +
      sim.map(r => `<span class="sim"><b>${r.c}</b>${r.g}</span>`).join("") +
      `</span><span class="h"></span></div>` : "");
  q(".kn-words").innerHTML = c.vocab.length
    ? `<div class="kn-wh">ことば</div>` + c.vocab.map(v =>
        `<div class="bk-row"><span class="r">${v.w}</span>` +
        `<span class="w">${v.r}</span><span class="g">${v.m}</span></div>`).join("")
    : "";
  q(".kn-note").textContent = c.note || "";
}

function setFlipped(next) {
  flipped = next;
  card.classList.toggle("flipped", flipped);
  const back = KIND === "kana"
    ? "Card back: the sound, and where the character sits in the syllabary."
    : "Card back: readings and meanings.";
  card.setAttribute("aria-label", flipped
    ? back + " Activate to turn it back."
    : "Drill card. Activate to turn it over.");
}

/* A pile's top card is a real face at full size, scaled down — the same object you
   are about to pick up, not a stand-in. */
function miniFace(idx, which) {
  const node = cardNode();
  paint(node, CARDS[idx]);
  const face = node.querySelector(which === "back" ? ".face.back" : ".face.front");
  face.style.transform = "none";          // .back normally carries rotateY(180deg)
  const wrap = document.createElement("div");
  wrap.className = "mini";
  wrap.appendChild(face);
  return wrap;
}

/* How many cards a pile is holding and which one is on top, which is the whole of what a
   pile shows. The count is part of that and not a separate thing the caller remembers to
   update — a reshuffle paints the two piles a dozen times while the deck is in the air
   and the tags have to follow the layers exactly. */
function renderPile(el, count, topIdx, which) {
  const stack = el.querySelector(".stack");
  stack.innerHTML = "";
  const layers = Math.min(count, 5);
  for (let i = 0; i < layers; i++) {
    const l = document.createElement("div");
    l.className = "layer";
    if (i === layers - 1 && topIdx != null) l.appendChild(miniFace(topIdx, which));
    stack.appendChild(l);
  }
  el.querySelector(".tag b").textContent = count;
  el.classList.toggle("empty", count === 0);
}

function renderPiles() {
  renderPile(drawPile, deck.length, deck.length ? deck[0] : null, "front");
  renderPile(usedPile, used.length, used.length ? used[used.length - 1] : null, "back");
  const empty = deck.length === 0;
  drawPile.setAttribute("aria-label", empty
    ? "Draw pile is empty. Activate to finish with this card, shuffle the discards back"
      + " in and deal the next one."
    : `Draw pile, ${deck.length} cards. Activate to draw.`);
  // Nothing has been finished with yet, so there is nothing to take back: the discard is
  // a button that is simply not offered rather than one that does nothing when pressed.
  usedPile.disabled = !used.length;
  usedPile.setAttribute("aria-label", used.length
    ? `Discard pile, ${used.length} cards. Activate to take the last one back.`
    : "Discard pile is empty.");
  // the third line only appears once there is something behind you to go back to
  $("hint").innerHTML = (empty
    ? "the pile is out — click it to shuffle the discards back in and carry on"
    : "click the pile or press <kbd>space</kbd> · <kbd>f</kbd> turns the card over") +
    (used.length ? " · <kbd>z</kbd> takes the last card back" : "");
}

const flight = (from, to) => ({
  dx: (to.left + to.width / 2) - (from.left + from.width / 2),
  dy: (to.top + to.height / 2) - (from.top + from.height / 2),
  s: to.width / from.width,
});

function makeFlyer(box, idx) {
  const f = cardNode();
  paint(f, CARDS[idx]);
  f.className = "card flyer";
  Object.assign(f.style, {
    left: box.left + "px", top: box.top + "px",
    width: box.width + "px", height: box.height + "px",
  });
  document.body.appendChild(f);
  return f;
}

const P = "perspective(1800px) ";

function drawCard() {
  if (busy) return;
  if (!deck.length) return reshuffle();
  busy = true;

  const box = card.getBoundingClientRect();
  const outgoing = current;
  const incoming = deck.shift();
  const wasFlipped = flipped;

  if (still()) {
    if (outgoing >= 0) used.push(outgoing);
    current = incoming; setFlipped(false); paint(card, CARDS[current]); renderPiles();
    busy = false;
    return;
  }

  // 1 — the finished card is turned over onto the discard, landing readings-up
  if (outgoing >= 0) {
    const g = makeFlyer(box, outgoing);
    const f = flight(box, usedPile.getBoundingClientRect());
    g.animate([
      { transform: P + `translate(0,0) scale(1) rotateY(${wasFlipped ? 180 : 0}deg)` },
      { transform: P + `translate(${f.dx}px,${f.dy}px) scale(${f.s}) rotateY(180deg) rotate(5deg)` },
    ], { duration: 460, easing: "cubic-bezier(.4,0,.25,1)", fill: "forwards" })
      .finished.then(() => {
        g.remove();
        used.push(outgoing);        // the pile grows only once the card has landed
        renderPiles();
      }).catch(() => g.remove());
  }

  // 2 — the next card is already face-up on the pile, so it simply slides across
  setTimeout(() => {
    current = incoming;
    setFlipped(false);
    paint(card, CARDS[current]);
    card.classList.add("hidden");
    renderPiles();                  // the pile loses its top card as that card leaves

    const g = makeFlyer(box, incoming);
    const f = flight(box, drawPile.getBoundingClientRect());
    g.animate([
      { transform: P + `translate(${f.dx}px,${f.dy}px) scale(${f.s}) rotate(-3deg)` },
      { transform: P + "translate(0,0) scale(1) rotate(0deg)" },
    ], { duration: 520, easing: "cubic-bezier(.2,.86,.3,1)", fill: "forwards" })
      .finished.then(() => {
        g.remove();
        card.classList.remove("hidden");
        busy = false;
      }).catch(() => { card.classList.remove("hidden"); busy = false; });
  }, 150);
}

/* A draw, run backwards. The card in hand goes back on top of the draw pile it came off,
   and the last card you finished with comes back off the discard — so a draw taken by
   mistake, or a card turned over before you had really answered it, costs one click
   rather than a lap of the whole deck.

   It comes back readings-up, because that is how it was lying. The discard holds cards
   readings-up and a card sliding off a pile does not turn over on the way, which is the
   same rule that has drawing not flip; and going back to a card you have just finished
   with is going back to look at its answer. Pressing f turns it over to the question
   again. The card going the other way unflips for the same reason: the draw pile holds
   cards front-up, so putting one back is exactly the turn that discarding it made. */
function revertCard() {
  if (busy || !used.length) return;
  busy = true;

  const box = card.getBoundingClientRect();
  const outgoing = current;
  const incoming = used.pop();
  const wasFlipped = flipped;

  if (still()) {
    if (outgoing >= 0) deck.unshift(outgoing);
    current = incoming; setFlipped(true); paint(card, CARDS[current]); renderPiles();
    busy = false;
    return;
  }

  // 1 — the card in hand is turned back over onto the draw pile, landing front-up and on
  // top, so the next draw deals it again
  if (outgoing >= 0) {
    const g = makeFlyer(box, outgoing);
    const f = flight(box, drawPile.getBoundingClientRect());
    g.animate([
      { transform: P + `translate(0,0) scale(1) rotateY(${wasFlipped ? 180 : 0}deg)` },
      { transform: P + `translate(${f.dx}px,${f.dy}px) scale(${f.s}) rotateY(0deg) rotate(-3deg)` },
    ], { duration: 460, easing: "cubic-bezier(.4,0,.25,1)", fill: "forwards" })
      .finished.then(() => {
        g.remove();
        deck.unshift(outgoing);     // the pile grows only once the card has landed
        renderPiles();
      }).catch(() => g.remove());
  }

  // 2 — and the last finished card slides back off the discard, still readings-up: it is
  // already lying that way there, so the flight carries rotateY(180deg) throughout
  setTimeout(() => {
    current = incoming;
    setFlipped(true);
    paint(card, CARDS[current]);
    card.classList.add("hidden");
    renderPiles();                  // the discard loses its top card as that card leaves

    const g = makeFlyer(box, incoming);
    const f = flight(box, usedPile.getBoundingClientRect());
    g.animate([
      { transform: P + `translate(${f.dx}px,${f.dy}px) scale(${f.s}) rotateY(180deg) rotate(5deg)` },
      { transform: P + "translate(0,0) scale(1) rotateY(180deg) rotate(0deg)" },
    ], { duration: 520, easing: "cubic-bezier(.2,.86,.3,1)", fill: "forwards" })
      .finished.then(() => {
        g.remove();
        card.classList.remove("hidden");
        busy = false;
      }).catch(() => { card.classList.remove("hidden"); busy = false; });
  }, 150);
}

/* ============ the pile runs out ============
   Everything you have finished with is turned over and becomes the pile you draw from
   again, which is what a person does with a discard: put down the card in your hand,
   pick the pile up, turn it over, shuffle it, set it down, and deal. So it is animated
   as those things in that order, and one press of the pile is the whole of it.

   The card in your hand goes first. It is the last card of the lap and you have finished
   with it, so it belongs on the discard before the discard can become the deck — a pile
   gathered around the card still in your hand would be everything you had seen except
   the one you had just seen. It travels by the same flight a draw sends a finished card
   on, to the same pile, landing readings-up.

   That empties the table, so the last thing the reshuffle does is deal off the pile it
   has just made. A full deck and nothing to study is not a state this table has, and it
   is the reason the opening deal sends a card to the stage while the pile is still
   landing rather than after.

   Six cards stand in for the whole pile, as in the deal, and each carries its share of
   the count across: the discard gives its share up as the card leaves and the draw pile
   takes it as the card lands, so the difference is in the air, which is where the cards
   are.

   A gather cannot be honest at both ends. What leaves the discard is what is lying on
   it, top card first; what the pile is left holding is whatever the shuffle decides. So
   the pile shows the card that really landed on it right up to the riffle, and from
   there it shows no top card at all — a pile being shuffled has none to show, and a pile
   being dealt off has the dealt card covering it. The face it is left with is the one
   the shuffle put there, uncovered by the card leaving for the stage. Nothing untrue is
   on screen at rest. */
const GATHER_N = 6, GATHER_GAP = 48;

/* One card off the discard and onto the draw pile. Built on the pile it lands on and
   animated back from the pile it left, like every other flight here.

   It turns over on the way, because the discard lies readings-up and the draw pile lies
   front-up — the same rule that has a draw not flip and a discard flip, applied to a
   whole pile one card at a time. The turn is done by the time the card is a third of the
   way across, so the second half of the flight shows the face the pile is about to be
   holding rather than an edge. */
function gatherFly(dest, f, idx, lean) {
  const g = makeFlyer(dest, idx);
  return g.animate([
    { transform: P + `translate(${f.dx}px,${f.dy}px) scale(${f.s})`
      + ` rotateY(180deg) rotate(${lean}deg)` },
    { transform: P + `translate(${f.dx * .52}px,${f.dy * .52 - 34}px)`
      + ` scale(${(f.s + 1) / 2}) rotateY(14deg) rotate(${lean * .45}deg)`, offset: .46 },
    { transform: P + "translate(0,0) scale(1) rotateY(0deg) rotate(0deg)" },
  ], { duration: 360, easing: "cubic-bezier(.33,.66,.3,1)", fill: "forwards" })
    .finished.catch(() => {}).finally(() => g.remove());
}

/* The card in your hand, put down before anything is picked up. This is drawCard's first
   half on its own — the same flight, the same pile, landing readings-up — and everything
   it touches it touches now, synchronously, so that what is left to run is a flight and
   nothing else. The index comes back rather than being pushed onto the discard here,
   because by the time it lands the discard may belong to a different deck. */
function finishLast() {
  const outgoing = current;
  if (outgoing < 0) return Promise.resolve(-1);
  const box = card.getBoundingClientRect(), wasFlipped = flipped;
  const g = makeFlyer(box, outgoing);
  const f = flight(box, usedPile.getBoundingClientRect());
  current = -1;
  card.classList.add("hidden");
  setFlipped(false);              // the turn happens under the flyer, where it is not seen
  return g.animate([
    { transform: P + `translate(0,0) scale(1) rotateY(${wasFlipped ? 180 : 0}deg)` },
    { transform: P + `translate(${f.dx}px,${f.dy}px) scale(${f.s})`
      + " rotateY(180deg) rotate(5deg)" },
  ], { duration: 400, easing: "cubic-bezier(.4,0,.25,1)", fill: "forwards" })
    .finished.catch(() => {}).finally(() => g.remove()).then(() => outgoing);
}

/* The discard crossing the table. The flyers are made at the moment each one leaves
   rather than up front, so the one on its way is always the one painted over the rest —
   a card waiting its turn on top of the discard would be showing a face that is two or
   three cards down.

   Each step asks whether it is still drawing to the table it started on: these paint
   `pending`'s indices into the piles, and after a different deck has been dealt those
   indices mean nothing, or nothing that exists. */
function gather(pending, mine) {
  const N = pending.length, n = Math.min(GATHER_N, N);
  const dest = drawPile.getBoundingClientRect();
  const f = flight(dest, usedPile.getBoundingClientRect());
  const share = k => Math.round(N * k / n);

  return Promise.all(Array.from({ length: n }, (_, i) => new Promise(done => {
    setTimeout(() => {
      if (mine !== hand) return done();
      const idx = pending[N - 1 - i], left = N - share(i + 1);
      renderPile(usedPile, left, left ? pending[left - 1] : null, "back");
      gatherFly(dest, f, idx, -6 + i * 2.2).then(() => {
        if (mine === hand) renderPile(drawPile, share(i + 1), idx, "front");
        done();
      });
    }, i * GATHER_GAP);
  })));
}

/* A riffle, drawn with the pile's own layers: the stack splits in two, the halves lean
   apart, and the cards fall back one at a time rather than together. The cascade is most
   of what a riffle looks like, and the packets falling alternately is the rest of it —
   without that it is two halves rejoining, which is a cut.

   composite:"add" lays this over the 1.5px step each layer already carries, so the pile
   keeps its thickness while it is shuffled. A browser that does not understand it
   riffles a flat pile, which is the whole of what it costs. */
function riffle(dir, duration, delay) {
  const layers = [...drawPile.querySelectorAll(".layer")];
  if (!layers.length) return Promise.resolve();
  // Far enough apart to read as two packets rather than one pile bulging: five cream
  // rectangles 1.5px apart have no texture to riffle, so the separation is the only
  // signal there is and it has to be taken.
  const spread = drawPile.getBoundingClientRect().width * .19;
  const half = Math.ceil(layers.length / 2), last = Math.max(layers.length - 1, 1);
  // deepest card of one packet, deepest of the other, and up: 0,3,1,4,2 for a five-layer
  // pile, which is the order a riffle actually drops them in
  const rank = i => i < half ? i * 2 : (i - half) * 2 + 1;

  return Promise.all(layers.map((l, i) => {
    const side = (i < half ? -1 : 1) * dir;
    const lean = side * (2.4 + (i % 3) * 1.2);
    const fall = .5 + (rank(i) / last) * .36;
    return l.animate([
      { transform: "translate(0,0) rotate(0deg)" },
      { transform: `translate(${side * spread}px,${-4 - i * 1.4}px) rotate(${lean}deg)`,
        offset: .3, easing: "cubic-bezier(.2,.9,.35,1)" },
      { transform: `translate(${side * spread * .28}px,${-2 - i * .5}px)`
        + ` rotate(${lean * .3}deg)`, offset: fall },
      { transform: "translate(0,0) rotate(0deg)" },
    ], { duration, delay, composite: "add", easing: "cubic-bezier(.4,.05,.25,1)" })
      .finished.catch(() => {});
  }));
}

/* and set down: the pile is squared against the table once, which is what stops the
   riffle rather than it simply ending. */
function squareUp() {
  return drawPile.querySelector(".stack").animate([
    { transform: "translateY(-5px)" }, { transform: "translateY(1.5px)" },
    { transform: "none" },
  ], { duration: 200, easing: "cubic-bezier(.3,.8,.35,1)" }).finished.catch(() => {});
}

/* and dealt off, because the table cannot be left with a full deck on it and nothing to
   study. This is drawCard's second half on its own: the top card slides across to the
   stage, front-up, since that is how it is lying.

   It is also what uncovers the pile. The face has been hidden since the riffle started,
   and the flyer sets off from exactly the box the pile occupies, so the card underneath
   is revealed by the card on top of it leaving — which is the one moment in a reshuffle
   where showing a new top card needs nothing to cover the change. */
function dealOne() {
  const incoming = deck.shift();
  current = incoming;
  setFlipped(false);
  paint(card, CARDS[current]);
  drawPile.classList.remove("shuffling");
  renderPiles();

  const box = card.getBoundingClientRect();
  const g = makeFlyer(box, incoming);
  const f = flight(box, drawPile.getBoundingClientRect());
  return g.animate([
    { transform: P + `translate(${f.dx}px,${f.dy}px) scale(${f.s}) rotate(-3deg)` },
    { transform: P + "translate(0,0) scale(1) rotate(0deg)" },
  ], { duration: 460, easing: "cubic-bezier(.2,.86,.3,1)", fill: "forwards" })
    .finished.catch(() => {}).finally(() => {
      g.remove();
      card.classList.remove("hidden");
    });
}

async function reshuffle() {
  if (busy || !used.length) return;
  busy = true;

  if (still()) {
    if (current >= 0) used.push(current);
    deck = shuffle(used); used = [];
    current = deck.shift();
    setFlipped(false); paint(card, CARDS[current]); renderPiles();
    busy = false;
    return;
  }

  // A reshuffle runs for a couple of seconds and the chooser is one click away for all
  // of it, so every step asks whether the table it started on is still there: a gather
  // that lands after a different deck has been dealt has to land on nothing rather than
  // put the old deck back.
  const mine = hand;
  try {
    const last = await finishLast();
    if (mine !== hand) return;
    if (last >= 0) { used.push(last); renderPiles(); }
    await settle(50);               // the pile is whole for a beat before it is picked up

    const pending = used;           // the pile being picked up, bottom card first
    used = [];
    await gather(pending, mine);
    if (mine !== hand) return;

    drawPile.classList.add("shuffling");
    await Promise.all([riffle(1, 280, 0), riffle(-1, 240, 280)]);
    if (mine !== hand) return;

    deck = shuffle(pending);        // the pile is holding what the shuffle decided
    renderPiles();
    squareUp();                     // the deal sets off into the tail of the square-up
    await settle(90);
    if (mine !== hand) return;
    await dealOne();
  } finally {
    if (mine === hand) {            // a new deal has already set its own
      drawPile.classList.remove("shuffling");
      card.classList.remove("hidden");
      busy = false;
    }
  }
}

drawPile.addEventListener("click", drawCard);
usedPile.addEventListener("click", revertCard);
card.addEventListener("click", () => setFlipped(!flipped));
addEventListener("keydown", e => {
  if (chooser.hidden === false) return;
  if (e.key === "f" || e.key === "F") { e.preventDefault(); return setFlipped(!flipped); }
  if (e.key === "z" || e.key === "Z") { e.preventDefault(); return revertCard(); }
  // Any button that has focus is activated by space itself, so space must not fall
  // through to a draw as well — the piles and the card, and equally `change deck` and
  // the two switches in the room, which are buttons that are only ever reached by tab
  // and would otherwise deal a card when pressed the one way they can be.
  if (e.target.closest("button")) return;
  if (e.key === " " || e.key === "Enter") { e.preventDefault(); drawCard(); }
});

/* ============ decks ============
   One file per deck, fetched only when that deck is picked: the kanji half alone is
   about 3MB of stroke paths and nobody studies five levels at once. They load through a
   <script> tag rather than fetch() so the page still runs from file:// with no server,
   which is the whole point of the data being static. Each file calls KANJI_DECK — the
   name the loader has always had, kept so the generated kanji files stay untouched. */
const chooser = $("chooser"), groupList = $("groupList"), note = $("chooserNote");
const table = $("table"), controls = $("controls");
const decks = {}, waiting = {};
/* The name of each category in English. It is a label, not deck data — nothing on a
   card changes — so it lives here rather than in the generated manifest. Only the
   category is named: 清音 and 濁音 are classes of kana with no English name that is
   shorter than a sentence, and the box already prints their romaji. */
const GROUP_EN = { "ひらがな": "Hiragana", "カタカナ": "Katakana", "漢字": "Kanji" };
/* Which of the three series a group is, as one hook for the stylesheet. Both things
   that vary by category hang off it — the 和柄 ground printed on the box and the spot
   ink the whole scope is mixed from — because they are the same fact said twice. */
const GROUP_CAT = { "ひらがな": "hiragana", "カタカナ": "katakana", "漢字": "kanji" };

window.KANJI_DECK = (id, cards) => {
  decks[id] = cards;
  (waiting[id] || []).forEach(resolve => resolve(cards));
  delete waiting[id];
};

function loadDeck(id) {
  if (decks[id]) return Promise.resolve(decks[id]);
  if (waiting[id]) return new Promise(resolve => waiting[id].push(resolve));
  return new Promise((resolve, reject) => {
    waiting[id] = [resolve];
    const tag = document.createElement("script");
    tag.src = `data/decks/${id}.js`;
    tag.onerror = () => { delete waiting[id]; reject(new Error(`could not load ${id}`)); };
    document.head.appendChild(tag);
  });
}

/* A merged deck has no file of its own. It names the decks it gathers and is dealt from
   their files, so the whole script can be drilled in one shuffle without a second copy
   of the same cards on disk — and without fetching 清音 again to meet it inside 全部. */
const parts = d => d.parts || [d.id];
const held = d => parts(d).every(id => decks[id]);
const loadCards = d => Promise.all(parts(d).map(loadDeck)).then(lists => lists.flat());

function deal(cards, meta) {
  CARDS = cards; DECK = meta; KIND = meta.kind;
  card.replaceChildren(faces(KIND));
  used = []; busy = false; hand++;
  current = Math.floor(Math.random() * CARDS.length);
  deck = shuffle(CARDS.map((_, i) => i).filter(i => i !== current));
  setFlipped(false);
  paint(card, CARDS[current]);
  renderPiles();
  $("relevel").textContent = `${meta.group} ${meta.label} · change deck`;
  // On <body> rather than on .table: the card in flight is appended to the body, so a
  // scope any tighter than this would have it change stock halfway to the pile.
  document.body.dataset.cat = GROUP_CAT[meta.group] || "";
  // The tile of the 和柄 in the head band, stepping through the volumes exactly as the
  // box's ground does — same series, same volume, same printing. It is the card's own
  // cqw and not the box's, because a card is five times the width of a box and the two
  // are each measured against themselves; what is carried across is the step, not the
  // number. A box states its own --ps inline, so this one never reaches the chooser.
  document.body.style.setProperty("--ps", `${(1.5 + (meta.vol || 0) * .28).toFixed(2)}cqw`);
  chooser.hidden = true; table.hidden = false; controls.hidden = false;
  card.focus();
}

/* Opening a box. The lid comes off where the box is standing, the table takes its place,
   and the deck it held flies over: most of it stacks up as the pile it will be drawn
   from, and one card carries on to the stage. They overlap rather than queue, because
   dealing the pile first left the top two-thirds of the screen empty for the length of
   it, which reads as a broken layout rather than as a deal.

   The cards in flight are real cards. makeFlyer paints them with the same code the pile
   and the table use, and they are the actual indices at the top of the shuffled deck, so
   the card you watch land is the card that is there when it stops. Six of them, because
   the pile is five layers deep and a sixth reads as "and the rest".

   The flyers are sized to the pile and animated from the box rather than the other way
   round: the pile is where they finish, and a flight that ends on its target's exact box
   cannot land crooked however the viewport is sized. */
const DEAL_N = 6;

/* One flight: a real card, sized to where it lands and animated back from where it came,
   because a flight that ends on its target's own box cannot land crooked however the
   viewport is sized. */
function fly(dest, f, idx, lean, duration, delay) {
  const g = makeFlyer(dest, idx);
  return g.animate([
    { transform: P + `translate(${f.dx}px,${f.dy}px) scale(${f.s}) rotate(${lean}deg)`,
      opacity: 0 },
    { opacity: 1, offset: .2 },
    { transform: P + "translate(0,0) scale(1) rotate(0deg)", opacity: 1 },
  ], { duration, delay, easing: "cubic-bezier(.22,.72,.3,1)", fill: "forwards" })
    .finished.catch(() => {}).finally(() => g.remove());
}

function dealFromBox(cards, meta, from) {
  deal(cards, meta);
  if (still()) return;
  busy = true;                      // no drawing out of a pile that has not landed yet

  const pileBox = drawPile.getBoundingClientRect();
  const cardBox = card.getBoundingClientRect();
  const stack = drawPile.querySelector(".stack");
  // both are held back and revealed under the cards that land on them, so the swap is
  // invisible: a flyer finishes on exactly the box the real thing occupies
  stack.style.visibility = "hidden";
  card.classList.add("hidden");
  table.classList.add("dealing");

  const toPile = flight(pileBox, from), toStage = flight(cardBox, from);
  const n = Math.min(DEAL_N, deck.length);

  // The deck stacks up as the pile, each card leaving the box at its own angle. Dealt
  // back to front — deck[0] is the pile's top card, so it has to be the last one down,
  // or the card you watched land is not the card sitting there when it stops.
  const piled = Promise.all(Array.from({ length: n },
    (_, i) => fly(pileBox, toPile, deck[n - 1 - i], -7 + i * 2.4, 430, i * 60)));
  // and one is dealt to the middle while the rest are still landing, so the stage is not
  // an empty two-thirds of the screen for the length of the deal
  const dealt = fly(cardBox, toStage, current, -4, 520, 120);

  piled.finally(() => { stack.style.visibility = ""; });
  dealt.finally(() => { card.classList.remove("hidden"); });
  Promise.all([piled, dealt]).finally(() => {
    table.classList.remove("dealing");
    busy = false;
  });
}

/* A deck is a box of cards, so it is drawn as one. Every box is the same size and
   only the printing differs: a 和柄 ground per script over which the drill workbook's
   block of type sits on a pasted label. The ground says which of the three series a
   box belongs to from across the room; the label says everything else.

   Nothing on the box is invented. 第80–247番 is the run of card numbers the deck
   actually holds, and because the three groups each tile their numbering with no
   gaps, the boxes in a row read as volumes of one set — か and カ share a card
   number, so ひらがな清音 and カタカナ清音 print the same range, which is the point. */
const VOLUMES = "一二三四五六七八九";

function deckBox(d, vol) {
  const slot = document.createElement("div");
  slot.className = "slot";

  // a three-character name sets smaller, and a kanji box prints no romaji so its
  // name centres in the plate instead of sitting above one
  const nm = "bx-nm" + (d.label.length > 2 ? " lng" : "") + (d.rom ? "" : " solo");
  // 全部 gathers the volumes beside it rather than being the next one, so it is
  // stamped 全 — a boxed set's omnibus is not volume five.
  const seal = d.parts ? "全" : VOLUMES[vol] || vol + 1;

  const b = document.createElement("button");
  b.className = "box";
  // The pattern's scale steps through a series, so 拗音 is not the same object as 清音.
  // In cqw rather than px, like everything else printed on a box: the ground is part of
  // the drawing, and a wider box on a phone gets a larger tile, not more tiles.
  b.style.setProperty("--ps", `${(8.33 + vol * 2.65).toFixed(2)}cqw`);
  b.setAttribute("aria-label",
    `${d.group}${GROUP_EN[d.group] ? ` ${GROUP_EN[d.group]}` : ""} ` +
    `${d.label}${d.rom ? ` (${d.rom})` : ""}, ${d.n} cards, ` +
    `numbers ${d.lo} to ${d.hi}`);
  // the two turned-away planes first, so the printed front paints over their edges
  b.innerHTML =
    `<span class="bx-top"></span><span class="bx-side"></span>
     <span class="bx-face">
       <span class="bx-pat wagara"></span>
       <span class="bx-series">${d.group}ドリル</span>
       <span class="bx-plate">
         <span class="${nm}">${d.label}</span>` +
         (d.rom ? `<span class="bx-rom">${d.rom}</span>` : "") +
        `<span class="bx-foot"><span>第${d.lo}–${d.hi}番</span><span>全${d.n}枚</span></span>
       </span>
       <span class="bx-flap"></span>
       <span class="bx-seal">${seal}</span>
     </span>`;

  b.addEventListener("click", () => {
    if (groupList.classList.contains("busy")) return;
    groupList.classList.add("busy");
    slot.classList.add("loading");     // the lid comes off
    note.textContent = held(d) ? "" : "shuffling the deck…";
    // A deck already in hand resolves in the same tick, which would cut the lid off
    // mid-flight. Hold the table back until the box has actually opened.
    // where the box is standing, caught before the chooser gives way to the table
    const from = b.querySelector(".bx-face").getBoundingClientRect();
    Promise.all([loadCards(d), settle(still() ? 0 : 240)])
      .then(([cards]) => {
        groupList.classList.remove("busy");
        dealFromBox(cards, d, from);
      })
      .catch(err => {
        groupList.classList.remove("busy");
        slot.classList.remove("loading");
        note.textContent = `${err.message}. Check that frontend/data/decks/ was built.`;
      });
  });

  const shade = document.createElement("span");
  shade.className = "bx-shade";
  slot.append(shade, b);
  return slot;
}

function renderChooser() {
  chooser.hidden = false; table.hidden = true; controls.hidden = true;
  // each row prints its own series from here on, and each box its own tile
  delete document.body.dataset.cat;
  document.body.style.removeProperty("--ps");
  note.textContent = "";
  groupList.innerHTML = "";
  const groups = [];
  DECKS.forEach(d => {
    let g = groups.find(x => x.name === d.group);
    if (!g) groups.push(g = { name: d.group, decks: [] });
    g.decks.push(d);
  });
  groups.forEach(g => {
    const row = document.createElement("div");
    row.className = "group";
    row.dataset.cat = GROUP_CAT[g.name] || "";
    const name = document.createElement("div");
    name.className = "group-name";
    name.innerHTML = `<span>${g.name}</span>` +
      (GROUP_EN[g.name] ? `<span class="en">${GROUP_EN[g.name]}</span>` : "");
    const list = document.createElement("div");
    list.className = "levels";
    // The index within a group is the volume number, and the step of its pattern. It is
    // written back onto the deck because the card wears the same ground its box does,
    // and deal() is handed the deck rather than the box it was picked from.
    g.decks.forEach((d, vol) => { d.vol = vol; list.appendChild(deckBox(d, vol)); });
    row.append(name, list);
    groupList.appendChild(row);
  });
}

/* ============ the lamp ============
   The stylesheet already draws both rooms and already knows how to choose between them:
   `prefers-color-scheme` picks one, and `[data-theme]` on <html> overrides it. So the
   switch is one attribute, and the only work here is which room it names, remembering
   it, and saying on the button which one it is not.

   No attribute is the third state, and it is the one the page starts in: the system's
   choice, live. A page nobody has switched follows the OS over at dusk and moves with
   it; pressing the button is what stops it following, because from then on the page has
   been told. That is why nothing is written until the button is pressed — a value
   stored on load would freeze whatever the OS happened to be saying at the time into a
   choice the reader never made.

   The button offers the room you are not in, so what it shows is the light you would be
   switching on rather than the one that is already on. */
const THEME_KEY = "drill-card:theme";
const lamp = $("lamp"), prefersDark = matchMedia("(prefers-color-scheme: dark)");
/* A store can refuse: Safari throws on localStorage in a blocked third-party frame and
   file:// has been an opaque origin in more than one browser. Either switch works either
   way; the choice just does not carry over to the next visit. */
const remember = (key, value) => { try { localStorage.setItem(key, value); } catch (e) {} };

// What the page is showing: the choice, if one has been made, and the system's if not.
const themeNow = () =>
  document.documentElement.dataset.theme || (prefersDark.matches ? "dark" : "light");

function paintLamp() {
  const other = themeNow() === "dark" ? "light" : "dark";
  $("lampMark").textContent = other === "dark" ? "夜" : "昼";
  $("lampName").textContent = other;
  lamp.setAttribute("aria-label", `Switch to the ${other} theme.`);
  // A phone paints the chrome above the page itself, and the desk should not stop at
  // the top of the viewport. Read back off :root rather than restated here, so the
  // stylesheet stays the one place either desk is written down.
  $("themeColor").setAttribute("content",
    getComputedStyle(document.documentElement).getPropertyValue("--desk").trim());
}

lamp.addEventListener("click", () => {
  const next = themeNow() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  remember(THEME_KEY, next);
  paintLamp();
});

// Only matters while the page is still following the system — once the attribute is set
// themeNow() stops reading this and the repaint is a no-op — but while it is following,
// the room changing under the page has to change what the button offers.
prefersDark.addEventListener("change", paintLamp);

paintLamp();

/* ============ the switch beside it ============
   The same switch again, for movement instead of light, and built the same way for the
   same reason: the page already knew how to do without the animations, and what was
   missing was a way to say so from the page. `prefers-reduced-motion` has skipped every
   flight since the flights existed, but it is an operating system setting, three menus
   deep, and it is all or nothing for every site — which is a strange thing to have to
   change because one table of cards deals them too theatrically for you.

   So: one attribute on <html>, `data-motion`, no attribute as the third state, and the
   system's preference live underneath it. The stylesheet reads it for the card's turn
   and the lid, and `still()` at the head of this file reads it for the flights — the
   animations here are written in JavaScript, so a media query alone could never have
   been the whole of the answer.

   Nothing is stopped mid-flight. A card already in the air lands and the pile it was
   going to still takes it; it is the next move that is simply made rather than dealt,
   which is what `still()` being asked per move rather than once at load buys.

   The face is 動 / 静 beside the lamp's 昼 / 夜, and like the lamp it offers the table
   you are not at rather than the one you are — 静 NO MOTION while the cards are flying.
   The two words are a pair on purpose. STILL was here first and was the wrong word: in
   English it is an adverb before it is an adjective, so STILL next to a deck of cards
   reads as "still going" at least as readily as "motionless" — and on a page teaching
   its reader to read, a label they have to work out is a label that has failed. NO
   MOTION cannot be read as anything but the other half of MOTION. */
const MOTION_KEY = "drill-card:motion";
const motion = $("motion");

// What the table is doing: the choice, if one has been made, and the system's if not.
function motionNow() {
  return document.documentElement.dataset.motion ||
    (prefersStill.matches ? "none" : "full");
}

function paintMotion() {
  const other = motionNow() === "none" ? "full" : "none";
  $("motionMark").textContent = other === "none" ? "静" : "動";
  $("motionName").textContent = other === "none" ? "no motion" : "motion";
  motion.setAttribute("aria-label", other === "none"
    ? "Turn the card animations off. Cards change without being dealt."
    : "Turn the card animations on. Cards are dealt across the table.");
}

motion.addEventListener("click", () => {
  const next = motionNow() === "none" ? "full" : "none";
  document.documentElement.dataset.motion = next;
  remember(MOTION_KEY, next);
  paintMotion();
});

// As with the lamp: this only matters while the page is still following the system, and
// while it is, a system that changes its mind has to change what the button offers.
prefersStill.addEventListener("change", paintMotion);

paintMotion();

$("relevel").addEventListener("click", renderChooser);
renderChooser();
