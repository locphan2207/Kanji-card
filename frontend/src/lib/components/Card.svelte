<script>
  import { katakana, okurigana, READING_GROUPS } from '$lib/readings.js';

  /**
   * One card, used three ways: the card on the table (`only` unset, so it has both
   * faces and can flip), a pile's top card (`only="front"|"back"`, a single flat face),
   * and the card in flight, which flight.js mounts detached. Painting all three from
   * the same component is what keeps them from drifting apart visually.
   */
  let {
    card,
    flipped = false,
    only = null,
    hidden = false,
    interactive = false,
    onclick = undefined,
    label = undefined
  } = $props();

  const on = $derived(card.on.map(katakana).join('・'));
  const kun = $derived(card.kun.map(okurigana).join('・'));
  const groups = $derived(
    READING_GROUPS.map(({ key, label }) => ({
      label,
      reading: key === 'on' ? on : key === 'kun' ? kun : '',
      rows: card.vocab.filter((v) => v.t === key)
    })).filter((g) => g.rows.length)
  );
</script>

{#snippet front()}
  <div class="face front" class:flat={only === 'front'}>
    <div class="no">{card.no}</div>
    <div class="glyph">{card.k}</div>
    <ol class="vocab">
      {#each card.vocab as v, i (v.w)}
        <li><span class="n">{i + 1}.</span>{v.w}</li>
      {/each}
    </ol>
    <div class="related">
      {#each card.rel as r (r.k)}
        <div class="rel">
          <span class="rn">{r.no}</span>
          <span class="rk">{r.k}</span>
          <!-- printed only when this relative shares the main kanji's on-reading -->
          {#if r.s}<span class="rs">{r.s}</span>{/if}
          <span class="rg">{r.g}</span>
        </div>
      {/each}
    </div>
    <div class="code">
      <span>{card.strokes}-{card.radN}-{card.restN}</span><span class="rad">{card.rad}</span>
    </div>
    <div class="strip">
      <!-- one cell per stroke: the finished kanji in grey, strokes 1..n in black over it -->
      {#each card.paths as _, i}
        <div class="cell">
          <svg viewBox="0 0 109 109" aria-hidden="true">
            <g class="gh">{#each card.paths as s}<path d={s.d} />{/each}</g>
            <g class="dr">{#each card.paths.slice(0, i + 1) as s}<path d={s.d} />{/each}</g>
          </svg>
        </div>
      {/each}
    </div>
    <div class="turn" aria-hidden="true">裏</div>
  </div>
{/snippet}

{#snippet back()}
  <!-- `.back` normally carries rotateY(180deg) for the flip; on its own it has to be
       turned to face the viewer or backface-visibility erases it -->
  <div class="face back" class:flat={only === 'back'}>
    <div class="no">{card.no}</div>
    <div class="bk-k">{card.k}</div>
    <div class="bk-m">{card.mean}</div>
    <hr />
    <div class="bk-groups">
      {#each groups as g (g.label)}
        <div>
          <div class="bk-head"><b>{g.label}</b><span>{g.reading}</span></div>
          {#each g.rows as v (v.w)}
            <div class="bk-row">
              <span class="r">{v.r}</span><span class="w">{v.w}</span><span class="g">{v.m}</span>
            </div>
          {/each}
        </div>
      {/each}
    </div>
  </div>
{/snippet}

{#if only === 'front'}
  {@render front()}
{:else if only === 'back'}
  {@render back()}
{:else}
  <svelte:element
    this={interactive ? 'button' : 'div'}
    class="card"
    class:flipped
    class:hidden
    type={interactive ? 'button' : undefined}
    aria-label={label}
    aria-live={interactive ? 'polite' : undefined}
    {onclick}
  >
    {@render front()}
    {@render back()}
  </svelte:element>
{/if}
