<script setup>
import { dataRightsBadgeClass, formatBytes } from "../lib/ui";

const props = defineProps({
  selectedObservation: {
    type: Object,
    default: null,
  },
  productsState: {
    type: Object,
    required: true,
  },
  products: {
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
});

defineEmits(["download-product", "plot-product"]);

function downloadStateFor(productId) {
  return props.productDownloads[productId] ?? { loading: false, error: "" };
}

function plotActionStateFor(productId) {
  return props.productPlots[productId] ?? { loading: false, error: "" };
}
</script>

<template>
  <div
    class="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-panel backdrop-blur-xl sm:p-6"
  >
    <div class="flex flex-col gap-3">
      <div class="flex items-center justify-between gap-3">
        <h2 class="text-lg font-semibold text-white">Products & Actions</h2>
        <span class="text-xs uppercase tracking-[0.14em] text-slate-300">
          Right panel
        </span>
      </div>
      <div class="rounded-lg border border-white/10 bg-slate-950/40 p-3 text-sm">
        <p class="font-medium text-slate-200">Selected observation</p>
        <div v-if="selectedObservation" class="mt-2 grid gap-2 sm:grid-cols-2">
          <div>
            <p class="text-xs uppercase tracking-[0.12em] text-slate-400">Target</p>
            <p class="text-slate-200">{{ selectedObservation.target_name || "—" }}</p>
          </div>
          <div>
            <p class="text-xs uppercase tracking-[0.12em] text-slate-400">Instrument</p>
            <p class="text-slate-200">{{ selectedObservation.instrument_name || "—" }}</p>
          </div>
          <div>
            <p class="text-xs uppercase tracking-[0.12em] text-slate-400">Obsid</p>
            <p class="font-mono text-xs text-slate-200">{{ selectedObservation.obsid || "—" }}</p>
          </div>
          <div>
            <p class="text-xs uppercase tracking-[0.12em] text-slate-400">Proposal</p>
            <p class="text-slate-200">{{ selectedObservation.proposal_id || "—" }}</p>
          </div>
          <div class="sm:col-span-2">
            <p class="text-xs uppercase tracking-[0.12em] text-slate-400">Data Rights</p>
            <span
              class="mt-1 inline-flex rounded-full border px-2 py-0.5 text-xs"
              :class="dataRightsBadgeClass(selectedObservation.data_rights)"
            >
              {{ selectedObservation.data_rights || "Unknown" }}
            </span>
          </div>
        </div>
        <p v-else class="mt-2 text-slate-400">
          Click a search result row to select an observation.
        </p>
      </div>
    </div>

    <div class="mt-4 grid gap-3 sm:grid-cols-2">
      <button
        type="button"
        class="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-slate-300 disabled:cursor-not-allowed disabled:opacity-60"
        disabled
      >
        {{ selectedObservation ? "Auto-loading products" : "Select observation" }}
      </button>
      <button
        type="button"
        class="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-slate-300 disabled:cursor-not-allowed disabled:opacity-60"
        disabled
      >
        Download Selected
      </button>
    </div>

    <div class="mt-5 rounded-xl border border-dashed border-white/10 bg-slate-950/30 p-4">
      <p class="text-sm font-medium text-slate-200">Product List</p>
      <p class="mt-2 text-sm leading-6 text-slate-400">
        Filtered JWST products from
        <code class="rounded bg-white/10 px-1 py-0.5">GET /api/obs/{obsid}/products</code>
        load automatically when an observation is selected.
      </p>
      <div class="mt-4 rounded-lg border border-white/10 bg-slate-950/40 p-3">
        <p
          v-if="!selectedObservation"
          class="text-sm text-slate-400"
        >
          Select an observation to load products.
        </p>

        <p
          v-else-if="productsState.loading"
          class="text-sm text-slate-300"
        >
          Loading products for obsid
          <span class="font-mono text-xs">{{ selectedObservation.obsid }}</span>
          ...
        </p>

        <p
          v-else-if="productsState.error"
          class="text-sm text-rose-200"
        >
          {{ productsState.error }}
        </p>

        <p
          v-else-if="products.length === 0"
          class="text-sm leading-6 text-amber-100/90"
        >
          No Level 3 FITS products returned. This API currently filters to
          calib_level==3 only; some observations may only have relevant products
          at Level 2.
        </p>

        <div
          v-else
          class="max-h-[20rem] overflow-auto rounded-lg border border-white/10"
        >
          <table class="min-w-full text-left text-sm">
            <thead class="sticky top-0 bg-slate-900/95 text-xs uppercase tracking-[0.12em] text-slate-400">
              <tr>
                <th class="px-3 py-2 font-medium">Filename</th>
                <th class="px-3 py-2 font-medium">Kind</th>
                <th class="px-3 py-2 font-medium">Size</th>
                <th class="px-3 py-2 font-medium">Cache</th>
                <th class="px-3 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="product in products"
                :key="product.product_id"
                class="border-t border-white/5 text-slate-200"
              >
                <td class="px-3 py-2 align-top">
                  <div class="max-w-[18rem]">
                    <p class="truncate font-mono text-xs" :title="product.productFilename || ''">
                      {{ product.productFilename || "—" }}
                    </p>
                    <p class="mt-1 text-xs text-slate-400" :title="product.description || ''">
                      {{ product.description || "No description" }}
                    </p>
                  </div>
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
                  {{ formatBytes(product.size) }}
                </td>
                <td class="px-3 py-2 align-top">
                  <span
                    class="inline-flex rounded-full border px-2 py-0.5 text-xs"
                    :class="
                      product.is_cached
                        ? 'border-emerald-300/40 bg-emerald-300/10 text-emerald-100'
                        : 'border-amber-300/40 bg-amber-300/10 text-amber-100'
                    "
                  >
                    {{ product.is_cached ? "Cached" : "Not cached" }}
                  </span>
                </td>
                <td class="px-3 py-2 align-top">
                  <div class="flex flex-wrap gap-2">
                    <button
                      type="button"
                      class="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-slate-200 disabled:cursor-not-allowed disabled:opacity-50"
                      :disabled="downloadStateFor(product.product_id).loading"
                      :title="product.product_id"
                      @click="$emit('download-product', product)"
                    >
                      {{
                        downloadStateFor(product.product_id).loading
                          ? "Downloading..."
                          : product.is_cached
                            ? "Re-download"
                            : "Download"
                      }}
                    </button>
                    <button
                      v-if="product.kind === 'spectrum1d' && product.is_cached"
                      type="button"
                      class="rounded-lg border border-cyan-200/20 bg-cyan-400/10 px-2.5 py-1 text-xs text-cyan-100 disabled:cursor-not-allowed disabled:opacity-50"
                      :disabled="plotActionStateFor(product.product_id).loading"
                      :title="
                        plotActionStateFor(product.product_id).loading
                          ? 'Loading spectrum...'
                          : 'Plot cached spectrum'
                      "
                      @click="$emit('plot-product', product)"
                    >
                      {{
                        plotActionStateFor(product.product_id).loading
                          ? "Plotting..."
                          : "Plot"
                      }}
                    </button>
                  </div>
                  <p
                    v-if="downloadStateFor(product.product_id).error"
                    class="mt-2 text-xs text-rose-200"
                  >
                    {{ downloadStateFor(product.product_id).error }}
                  </p>
                  <p
                    v-if="plotActionStateFor(product.product_id).error"
                    class="mt-2 text-xs text-rose-200"
                  >
                    {{ plotActionStateFor(product.product_id).error }}
                  </p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

