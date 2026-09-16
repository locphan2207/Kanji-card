const $ = id => document.getElementById(id);
const card = $("card"), stage = $("stage");
const drawPile = $("drawPile"), usedPile = $("usedPile");
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

const kata = s => s.replace(/[ぁ-ゖ]/g, c => String.fromCharCode(c.charCodeAt(0) + 0x60));
const okuri = s => s.replace(/^-/, "〜").replace(/\.(.+)$/, "（$1）");
const shuffle = a => { for (let i = a.length - 1; i > 0; i--) {
  const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };

// an empty copy of the card, taken before anything is painted into it
const TEMPLATE = card.cloneNode(true);
TEMPLATE.removeAttribute("id");

let deck = [], used = [], current = -1, busy = false, flipped = false;

function cell(paths, n) {
  const d = ss => ss.map(s => `<path d="${s.d}"/>`).join("");
  return `<div class="cell"><svg viewBox="0 0 109 109" aria-hidden="true">` +
    `<g class="gh">${d(paths)}</g><g class="dr">${d(paths.slice(0, n))}</g></svg></div>`;
}

/* Paints any card-shaped node, so the table card, the pile tops and the flying card
   are all produced by the same code and can't drift apart visually. */
function paint(root, c) {
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
  q(".strip").innerHTML = c.paths.map((_, i) => cell(c.paths, i + 1)).join("");

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

function setFlipped(next) {
  flipped = next;
  card.classList.toggle("flipped", flipped);
  card.setAttribute("aria-label", flipped
    ? "Card back: readings and meanings. Activate to turn it back."
    : "Kanji card. Activate to turn it over.");
}

/* A pile's top card is a real face at full size, scaled down — the same object you
   are about to pick up, not a stand-in. */
function miniFace(idx, which) {
  const node = TEMPLATE.cloneNode(true);
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
  const f = TEMPLATE.cloneNode(true);
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
  if (e.key === "f" || e.key === "F") { e.preventDefault(); return setFlipped(!flipped); }
  if (e.target === card || e.target === drawPile) return;
  if (e.key === " " || e.key === "Enter") { e.preventDefault(); drawCard(); }
});

current = CARDS.findIndex(c => c.k === "者");
deck = shuffle(CARDS.map((_, i) => i).filter(i => i !== current));
paint(card, CARDS[current]);
renderPiles();
