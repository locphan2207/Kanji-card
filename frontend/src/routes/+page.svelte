<script>
  import Card from '$lib/components/Card.svelte';
  import Pile from '$lib/components/Pile.svelte';
  import { openingDeck, shuffle } from '$lib/deck.js';
  import { discardTo, dealFrom, bumpPile } from '$lib/flight.js';

  let { data } = $props();
  const CARDS = data.cards;
  const OPENING = Math.max(
    0,
    CARDS.findIndex((c) => c.k === '者') // the card from the reference photo
  );

  let deck = $state(openingDeck(CARDS, OPENING));
  let used = $state([]);
  let current = $state(OPENING);
  let flipped = $state(false);
  let hiding = $state(false);
  let busy = false;

  let dealerEl = $state(),
    drawEl = $state(),
    usedEl = $state();

  const empty = $derived(deck.length === 0);
  const cardLabel = $derived(
    flipped
      ? 'Card back: readings and meanings. Activate to turn it back.'
      : 'Kanji card. Activate to turn it over.'
  );
  const drawLabel = $derived(
    empty
      ? 'Draw pile is empty. Activate to shuffle the discards back in.'
      : `Draw pile, ${deck.length} cards. Activate to draw.`
  );

  const prefersReducedMotion = () =>
    typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

  async function draw() {
    if (busy) return;
    if (empty) return reshuffleDeck();

    busy = true;
    const box = dealerEl.getBoundingClientRect();
    const outgoing = current;
    const incoming = deck[0];
    const wasFlipped = flipped;

    if (prefersReducedMotion()) {
      deck = deck.slice(1);
      used = [...used, outgoing];
      current = incoming;
      flipped = false;
      busy = false;
      return;
    }

    // The pile only grows once the card has actually landed on it.
    discardTo(usedEl, box, CARDS[outgoing], wasFlipped).then(() => {
      used = [...used, outgoing];
    });

    // A beat later: clear the table first, then deal. Both cards are in the air at once.
    await new Promise((resolve) => setTimeout(resolve, 150));
    deck = deck.slice(1); // the pile loses its top card as that card leaves
    current = incoming;
    flipped = false;
    hiding = true;
    await dealFrom(drawEl, box, CARDS[incoming]);
    hiding = false;
    busy = false;
  }

  async function reshuffleDeck() {
    if (busy || !used.length) return;
    busy = true;
    deck = shuffle([...used]);
    used = [];
    await bumpPile(drawEl);
    busy = false;
  }

  function onKeydown(e) {
    if (e.key === 'f' || e.key === 'F') {
      e.preventDefault();
      flipped = !flipped;
      return;
    }
    // let the buttons handle their own activation when focused
    if (e.target === dealerEl?.firstElementChild || e.target === drawEl) return;
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      draw();
    }
  }
</script>

<svelte:window onkeydown={onKeydown} />

<div class="table">
  <div class="stage">
    <div class="drop" aria-hidden="true"></div>
    <div class="dealer" bind:this={dealerEl}>
      <Card
        card={CARDS[current]}
        {flipped}
        hidden={hiding}
        interactive
        label={cardLabel}
        onclick={() => (flipped = !flipped)}
      />
    </div>
  </div>

  <div class="piles">
    <Pile
      bind:element={usedEl}
      count={used.length}
      top={used.length ? CARDS[used[used.length - 1]] : null}
      face="back"
      label="済み"
      mark="済"
    />
    <Pile
      bind:element={drawEl}
      count={deck.length}
      top={deck.length ? CARDS[deck[0]] : null}
      face="front"
      label="山札"
      mark="漢"
      ariaLabel={drawLabel}
      onclick={draw}
    />
  </div>
</div>

<div class="controls">
  <div class="hint">
    {#if empty}
      the pile is out — click it to shuffle the discards back in
    {:else}
      click the pile or press <kbd>space</kbd> · <kbd>f</kbd> turns the card over
    {/if}
  </div>
</div>
