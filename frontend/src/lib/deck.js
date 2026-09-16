/** Fisher-Yates, in place. */
export function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** Cards move draw -> table -> discard, so nothing repeats until the pile is exhausted. */
export function openingDeck(cards, startIndex) {
  return shuffle(cards.map((_, i) => i).filter((i) => i !== startIndex));
}
