import { mount, unmount } from 'svelte';
import Card from './components/Card.svelte';

/**
 * The card flights stay imperative on purpose. They measure live DOM boxes and drive a
 * detached element that deliberately sits outside the component tree, which is awkward
 * to express declaratively and gains nothing from it. Svelte's `mount` lets a real Card
 * be rendered into that detached node, so the flying card is the same component as the
 * one on the table and the one on the pile.
 */
const PERSPECTIVE = 'perspective(1800px) ';

/** Centre-to-centre offset and scale between two on-screen boxes. Measured per flight,
 *  so the paths stay correct at any viewport and survive moving the piles. */
function geometry(from, to) {
  return {
    dx: to.left + to.width / 2 - (from.left + from.width / 2),
    dy: to.top + to.height / 2 - (from.top + from.height / 2),
    scale: to.width / from.width
  };
}

function flyer(box, card, flipped = false) {
  const host = document.createElement('div');
  host.className = 'flyer';
  Object.assign(host.style, {
    left: `${box.left}px`,
    top: `${box.top}px`,
    width: `${box.width}px`,
    height: `${box.height}px`
  });
  document.body.appendChild(host);
  const app = mount(Card, { target: host, props: { card, flipped } });
  return {
    host,
    destroy() {
      unmount(app);
      host.remove();
    }
  };
}

/** `fill: forwards` matters: without it the element snaps back to its untransformed base
 *  the instant the animation ends, which is a one-frame flash of a full-size card. */
async function run(el, frames, options) {
  try {
    await el.animate(frames, { fill: 'forwards', ...options }).finished;
  } catch {
    // interrupted — the caller still cleans up
  }
}

/** The finished card is turned over onto the discard pile, landing readings-up.
 *  Turning it over *is* the act of finishing with it, so this flight carries a flip. */
export async function discardTo(pileEl, box, card, wasFlipped) {
  const f = flyer(box, card, wasFlipped);
  const g = geometry(box, pileEl.getBoundingClientRect());
  await run(
    f.host,
    [
      { transform: `${PERSPECTIVE}translate(0,0) scale(1) rotateY(${wasFlipped ? 180 : 0}deg)` },
      {
        transform: `${PERSPECTIVE}translate(${g.dx}px,${g.dy}px) scale(${g.scale}) rotateY(180deg) rotate(5deg)`
      }
    ],
    { duration: 460, easing: 'cubic-bezier(.4,0,.25,1)' }
  );
  f.destroy();
}

/** The next card is already face-up on the draw pile, so it simply slides across and
 *  grows. No flip — inventing one here was the thing that read as fake. */
export async function dealFrom(pileEl, box, card) {
  const f = flyer(box, card);
  const g = geometry(box, pileEl.getBoundingClientRect());
  await run(
    f.host,
    [
      {
        transform: `${PERSPECTIVE}translate(${g.dx}px,${g.dy}px) scale(${g.scale}) rotate(-3deg)`
      },
      { transform: `${PERSPECTIVE}translate(0,0) scale(1) rotate(0deg)` }
    ],
    { duration: 520, easing: 'cubic-bezier(.2,.86,.3,1)' }
  );
  f.destroy();
}

/** A small settle when the discards are shuffled back into the draw pile. */
export async function bumpPile(el) {
  await run(
    el,
    [
      { transform: 'translateY(0)' },
      { transform: 'translateY(-10px) rotate(-2deg)' },
      { transform: 'none' }
    ],
    { duration: 420, easing: 'ease-out', fill: 'none' }
  );
}
