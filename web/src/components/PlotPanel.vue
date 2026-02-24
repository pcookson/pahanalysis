<script setup>
defineProps({
  plotState: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div
    class="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-panel backdrop-blur-xl sm:p-6"
  >
    <h2 class="text-lg font-semibold text-white">Plot Area</h2>
    <p class="mt-3 text-sm leading-6 text-slate-400">
      Spectrum segments from
      <code class="rounded bg-white/10 px-1 py-0.5">GET /api/products/spectrum</code>
      are plotted here for cached `x1d/c1d` products.
    </p>
    <div class="mt-4 rounded-lg border border-white/10 bg-slate-950/40 p-3">
      <p v-if="plotState.loading" class="text-sm text-slate-300">
        Loading spectrum for plotting...
      </p>
      <p v-else-if="plotState.error" class="text-sm text-rose-200">
        {{ plotState.error }}
      </p>
      <p
        v-else-if="plotState.productId"
        class="text-sm text-slate-300"
      >
        {{ plotState.filename || plotState.productId }}
        <span class="text-slate-500"> · {{ plotState.segmentCount }} segment<span v-if="plotState.segmentCount !== 1">s</span></span>
      </p>
      <p v-else class="text-sm text-slate-400">
        Click Plot on a cached `spectrum1d` product to render the spectrum.
      </p>
    </div>

    <div
      class="mt-4 overflow-hidden rounded-xl border border-dashed border-cyan-200/15 bg-gradient-to-br from-cyan-400/5 via-transparent to-emerald-300/5"
    >
      <slot />
    </div>
  </div>
</template>

