<script setup>
import { formatBytes } from "../lib/ui";

const props = defineProps({
  cachedProductsState: {
    type: Object,
    required: true,
  },
  cachedProducts: {
    type: Array,
    required: true,
  },
  productDownloads: {
    type: Object,
    required: true,
  },
  productPlots: {
    type: Object,
    required: true,
  },
  productScores: {
    type: Object,
    required: true,
  },
});

defineEmits(["refresh", "download-product", "plot-product", "score-product"]);

function downloadStateFor(productId) {
  return props.productDownloads[productId] ?? { loading: false, error: "" };
}

function plotActionStateFor(productId) {
  return props.productPlots[productId] ?? { loading: false, error: "" };
}

function scoreStateFor(productId) {
  return props.productScores[productId] ?? { loading: false, error: "", data: null };
}

function scoreBadgeClass(grade) {
  if (grade === "HIGH") return "border-emerald-300/40 bg-emerald-300/10 text-emerald-100";
  if (grade === "MED") return "border-amber-300/40 bg-amber-300/10 text-amber-100";
  return "border-rose-300/40 bg-rose-300/10 text-rose-100";
}
</script>

<template>
  <div class="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-panel backdrop-blur-xl sm:p-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold text-white">Cached Products (All Observations)</h2>
        <p class="mt-1 text-sm text-slate-400">
          Downloaded files currently in the local JWST cache.
        </p>
      </div>
      <button
        type="button"
        class="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:bg-white/10 disabled:opacity-60"
        :disabled="cachedProductsState.loading"
        @click="$emit('refresh')"
      >
        {{ cachedProductsState.loading ? "Refreshing..." : "Refresh cached list" }}
      </button>
    </div>

    <div class="mt-4 rounded-lg border border-white/10 bg-slate-950/40 p-3">
      <p v-if="cachedProductsState.error" class="text-sm text-rose-200">
        {{ cachedProductsState.error }}
      </p>
      <p v-else-if="cachedProductsState.loading && cachedProducts.length === 0" class="text-sm text-slate-300">
        Loading cached products...
      </p>
      <p v-else-if="cachedProducts.length === 0" class="text-sm text-slate-400">
        No cached products found yet.
      </p>

      <div
        v-else
        class="max-h-[24rem] overflow-auto rounded-lg border border-white/10"
      >
        <table class="min-w-full text-left text-sm">
          <thead class="sticky top-0 bg-slate-900/95 text-xs uppercase tracking-[0.12em] text-slate-400">
            <tr>
              <th class="px-3 py-2 font-medium">Target</th>
              <th class="px-3 py-2 font-medium">Filename</th>
              <th class="px-3 py-2 font-medium">Kind</th>
              <th class="px-3 py-2 font-medium">Size</th>
              <th class="px-3 py-2 font-medium">PAH</th>
              <th class="px-3 py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="product in cachedProducts"
              :key="product.product_id"
              class="border-t border-white/5 text-slate-200"
            >
              <td class="px-3 py-2 align-top">
                <p class="max-w-[18rem] truncate text-xs" :title="product.target_name || 'N/A'">
                  {{ product.target_name || "N/A" }}
                </p>
              </td>
              <td class="px-3 py-2 align-top">
                <p class="max-w-[40rem] truncate font-mono text-xs" :title="product.productFilename || ''">
                  {{ product.productFilename || "—" }}
                </p>
              </td>
              <td class="px-3 py-2 align-top">
                <span
                  class="inline-flex rounded-full border px-2 py-0.5 text-xs"
                  :class="
                    product.kind === 'spectrum1d'
                      ? 'border-cyan-300/40 bg-cyan-300/10 text-cyan-100'
                      : product.kind === 'cube3d'
                        ? 'border-violet-300/40 bg-violet-300/10 text-violet-100'
                        : 'border-white/10 bg-white/5 text-slate-200'
                  "
                >
                  {{ product.kind || "other" }}
                </span>
              </td>
              <td class="px-3 py-2 align-top whitespace-nowrap">
                {{ formatBytes(product.size ?? product.cached_bytes) }}
              </td>
              <td class="px-3 py-2 align-top">
                <template v-if="product.kind === 'spectrum1d'">
                  <p v-if="scoreStateFor(product.product_id).loading" class="text-xs text-slate-300">
                    Scoring...
                  </p>
                  <div v-else-if="scoreStateFor(product.product_id).data" class="flex flex-wrap items-center gap-2">
                    <span class="text-xs font-medium text-slate-100">
                      {{ Math.round((scoreStateFor(product.product_id).data.confidence ?? 0) * 100) }}%
                    </span>
                    <span
                      class="inline-flex rounded-full border px-2 py-0.5 text-xs"
                      :class="scoreBadgeClass(scoreStateFor(product.product_id).data.grade)"
                    >
                      {{ scoreStateFor(product.product_id).data.grade }}
                    </span>
                    <button
                      type="button"
                      class="rounded-lg border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-slate-300"
                      @click="$emit('score-product', product)"
                    >
                      Re-score
                    </button>
                  </div>
                  <div v-else class="flex flex-wrap items-center gap-2">
                    <span class="text-xs text-slate-400">Not scored</span>
                    <button
                      type="button"
                      class="rounded-lg border border-cyan-200/20 bg-cyan-400/10 px-2 py-0.5 text-xs text-cyan-100"
                      @click="$emit('score-product', product)"
                    >
                      Score
                    </button>
                  </div>
                  <p v-if="scoreStateFor(product.product_id).error" class="mt-1 text-xs text-rose-200">
                    {{ scoreStateFor(product.product_id).error }}
                  </p>
                </template>
                <span v-else class="text-xs text-slate-500">—</span>
              </td>
              <td class="px-3 py-2 align-top">
                <div class="flex flex-wrap gap-2">
                  <button
                    type="button"
                    class="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-slate-200 disabled:opacity-50"
                    :disabled="downloadStateFor(product.product_id).loading"
                    :title="product.product_id"
                    @click="$emit('download-product', product)"
                  >
                    {{
                      downloadStateFor(product.product_id).loading ? "Downloading..." : "Re-download"
                    }}
                  </button>
                  <button
                    v-if="product.kind === 'spectrum1d'"
                    type="button"
                    class="rounded-lg border border-cyan-200/20 bg-cyan-400/10 px-2.5 py-1 text-xs text-cyan-100 disabled:opacity-50"
                    :disabled="plotActionStateFor(product.product_id).loading"
                    @click="$emit('plot-product', product)"
                  >
                    {{ plotActionStateFor(product.product_id).loading ? "Plotting..." : "Plot" }}
                  </button>
                </div>
                <p v-if="downloadStateFor(product.product_id).error" class="mt-2 text-xs text-rose-200">
                  {{ downloadStateFor(product.product_id).error }}
                </p>
                <p v-if="plotActionStateFor(product.product_id).error" class="mt-2 text-xs text-rose-200">
                  {{ plotActionStateFor(product.product_id).error }}
                </p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
