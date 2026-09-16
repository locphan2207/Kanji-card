<script>
  import '../app.css';
  let { children } = $props();
</script>

<svelte:head>
  <title>Kanji Drill Card</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    rel="stylesheet"
    href="https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&display=swap"
  />
</svelte:head>

{@render children()}
