<script>
  import Card from './Card.svelte';

  /**
   * A stack of up to five card edges. The top one is a real card face scaled down —
   * the same object you are about to pick up, not a stand-in graphic. Both faces of
   * these cards carry content, so there is no generic back: the draw pile holds cards
   * front-up (unstudied) and the discard holds them readings-up (finished).
   */
  let {
    count,
    top = null,
    face = 'front',
    label,
    mark,
    onclick = undefined,
    ariaLabel,
    // the page measures this element to aim each flight at it
    element = $bindable()
  } = $props();

  const layers = $derived(Math.min(count, 5));
</script>

<svelte:element
  this={onclick ? 'button' : 'div'}
  bind:this={element}
  class="pile"
  class:draw={!!onclick}
  class:used={!onclick}
  class:empty={count === 0}
  type={onclick ? 'button' : undefined}
  aria-label={ariaLabel}
  aria-hidden={onclick ? undefined : 'true'}
  {onclick}
>
  <div class="stack">
    {#each { length: layers } as _, i}
      <div class="layer">
        {#if i === layers - 1 && top}
          <div class="mini"><Card card={top} only={face} /></div>
        {/if}
      </div>
    {/each}
  </div>
  <span class="mark">{mark}</span>
  <span class="tag">{label} <b>{count}</b></span>
</svelte:element>
