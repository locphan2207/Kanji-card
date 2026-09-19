const $ = id => document.getElementById(id);
const card = $("card"), stage = $("stage");
const drawPile = $("drawPile"), usedPile = $("usedPile");
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

const kata = s => s.replace(/[ぁ-ゖ]/g, c => String.fromCharCode(c.charCodeAt(0) + 0x60));
const okuri = s => s.replace(/^-/, "〜").replace(/\.(.+)$/, "（$1）");
const shuffle = a => { for (let i = a.length - 1; i > 0; i--) {
  const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const settle = ms => new Promise(resolve => setTimeout(resolve, ms));

let CARDS = [], DECK = null, KIND = "kanji";
let deck = [], used = [], current = -1, busy = false, flipped = false;

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
  el.classList.toggle("empty", count === 0);
}

function renderPiles() {
  renderPile(drawPile, deck.length, deck.length ? deck[0] : null, "front");
  renderPile(usedPile, used.length, used.length ? used[used.length - 1] : null, "back");
  $("drawN").textContent = deck.length;
  $("usedN").textContent = used.length;
  const empty = deck.length === 0;
  drawPile.setAttribute("aria-label", empty
    ? "Draw pile is empty. Activate to shuffle the discards back in."
    : `Draw pile, ${deck.length} cards. Activate to draw.`);
  $("hint").innerHTML = empty
    ? "the pile is out — click it to shuffle the discards back in"
    : "click the pile or press <kbd>space</kbd> · <kbd>f</kbd> turns the card over";
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

  if (reduced) {
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

function reshuffle() {
  if (busy || !used.length) return;
  busy = true;
  deck = shuffle(used);
  used = [];
  renderPiles();
  drawPile.animate([
    { transform: "translateY(0)" }, { transform: "translateY(-10px) rotate(-2deg)" },
    { transform: "none" },
  ], { duration: 420, easing: "ease-out" })
    .finished.then(() => { busy = false; }).catch(() => { busy = false; });
}

drawPile.addEventListener("click", drawCard);
card.addEventListener("click", () => setFlipped(!flipped));
addEventListener("keydown", e => {
  if (chooser.hidden === false) return;
  if (e.key === "f" || e.key === "F") { e.preventDefault(); return setFlipped(!flipped); }
  if (e.target === card || e.target === drawPile) return;
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
/* In first-appearance order, which is the order the chooser lays the rows out and
   the order the three 和柄 grounds are numbered in. */
const GROUPS = [...new Set(DECKS.map(d => d.group))];

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
  used = []; busy = false;
  current = Math.floor(Math.random() * CARDS.length);
  deck = shuffle(CARDS.map((_, i) => i).filter(i => i !== current));
  setFlipped(false);
  paint(card, CARDS[current]);
  renderPiles();
  $("relevel").textContent = `${meta.group} ${meta.label} · change deck`;
  chooser.hidden = true; table.hidden = false; controls.hidden = false;
  card.focus();
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
  // the pattern's scale steps through a series, so 拗音 is not the same object as 清音
  b.style.setProperty("--ps", `${11 + vol * 3.5}px`);
  b.setAttribute("aria-label",
    `${d.group} ${d.label}${d.rom ? ` (${d.rom})` : ""}, ${d.n} cards, ` +
    `numbers ${d.lo} to ${d.hi}`);
  b.innerHTML =
    `<span class="bx-lid">
       <span class="bx-pat g${GROUPS.indexOf(d.group)}"></span>
       <span class="bx-series">${d.group}ドリル</span>
       <span class="bx-plate">
         <span class="${nm}">${d.label}</span>` +
         (d.rom ? `<span class="bx-rom">${d.rom}</span>` : "") +
        `<span class="bx-foot"><span>第${d.lo}–${d.hi}番</span><span>全${d.n}枚</span></span>
       </span>
       <span class="bx-flap"></span>
       <span class="bx-seal">${seal}</span>
     </span>
     <span class="bx-depth"></span>`;

  b.addEventListener("click", () => {
    if (groupList.classList.contains("busy")) return;
    groupList.classList.add("busy");
    slot.classList.add("loading");     // the lid comes off
    note.textContent = held(d) ? "" : "shuffling the deck…";
    // A deck already in hand resolves in the same tick, which would cut the lid off
    // mid-flight. Hold the table back until the box has actually opened.
    Promise.all([loadCards(d), settle(reduced ? 0 : 240)])
      .then(([cards]) => { groupList.classList.remove("busy"); deal(cards, d); })
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
    const name = document.createElement("div");
    name.className = "group-name";
    name.textContent = g.name;
    const list = document.createElement("div");
    list.className = "levels";
    // the index within a group is the volume number, and the step of its pattern
    g.decks.forEach((d, vol) => list.appendChild(deckBox(d, vol)));
    row.append(name, list);
    groupList.appendChild(row);
  });
}

$("relevel").addEventListener("click", renderChooser);
renderChooser();
