import cards from '$lib/data/cards.json';

export const prerender = true;

/**
 * The seam a backend replaces. Once cards live in a table this becomes
 *
 *   export async function load({ fetch }) {
 *     return { cards: await fetch('/api/cards').then((r) => r.json()) };
 *   }
 *
 * and nothing else in the app changes — the page only ever sees `data.cards`.
 */
export function load() {
  return { cards };
}
