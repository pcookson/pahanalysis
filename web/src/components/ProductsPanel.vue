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
  displayedProducts: {
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
  productAnnotations: {
    type: Object,
    required: true,
  },
  annotationDrafts: {
    type: Object,
    required: true,
  },
  productListOptions: {
    type: Object,
    required: true,
  },
});

defineEmits([
  "download-product",
  "plot-product",
  "score-product",
  "update-annotation-draft",
  "save-annotation",
  "update-only-likely-pah",
]);

function downloadStateFor(productId) {
  return props.productDownloads[productId] ?? { loading: false, error: "" };
}

function plotActionStateFor(productId) {
  return props.productPlots[productId] ?? { loading: false, error: "" };
}

function scoreStateFor(productId) {
  return props.productScores[productId] ?? { loading: false, error: "", data: null };
}

function annotationStateFor(productId) {
  return (
    props.productAnnotations[productId] ?? {
      loading: false,
      saving: false,
      error: "",
      data: null,
    }
  );
}

function annotationDraftFor(productId) {
  return (
    props.annotationDrafts[productId] ?? {
      user_label: "unknown",
      user_confidence: null,
      note: "",
    }
  );
}

function scoreBadgeClass(grade) {
  if (grade === "HIGH") {
    return "border-emerald-300/40 bg-emerald-300/10 text-emerald-100";
  }
  if (grade === "MED") {
    return "border-amber-300/40 bg-amber-300/10 text-amber-100";
  }
  return "border-rose-300/40 bg-rose-300/10 text-rose-100";
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
      <div class="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/10 bg-slate-950/40 p-3">
        <label class="inline-flex items-center gap-2 text-sm text-slate-200">
          <input
            type="checkbox"
            class="h-4 w-4 rounded border-white/20 bg-slate-950/60 text-cyan-300"
            :checked="Boolean(productListOptions.onlyLikelyPah)"
            @change="$emit('update-only-likely-pah', $event.target.checked)"
          />
          Show only likely PAH
        </label>
        <p class="text-xs text-slate-400">
          Sorted by PAH confidence (desc)
          <span v-if="products.length !== displayedProducts.length">
            · showing {{ displayedProducts.length }}/{{ products.length }}
          </span>
        </p>
      </div>
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

        <p
          v-else-if="displayedProducts.length === 0"
          class="text-sm leading-6 text-slate-300"
        >
          No products match the current PAH filter.
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
                <th class="px-3 py-2 font-medium">PAH</th>
                <th class="px-3 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="product in displayedProducts"
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
                  <template v-if="product.kind === 'spectrum1d'">
                    <div class="space-y-2 min-w-[16rem]">
                      <div>
                        <p
                          v-if="scoreStateFor(product.product_id).loading"
                          class="text-xs text-slate-300"
                        >
                          Scoring...
                        </p>
                        <div
                          v-else-if="scoreStateFor(product.product_id).data"
                          class="flex flex-wrap items-center gap-2"
                        >
                          <span class="text-xs font-medium text-slate-100">
                            {{
                              Math.round(
                                (scoreStateFor(product.product_id).data.confidence ?? 0) * 100,
                              )
                            }}%
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
                            :disabled="!product.is_cached"
                            @click="$emit('score-product', product)"
                          >
                            Re-score
                          </button>
                        </div>
                        <div v-else class="flex flex-wrap items-center gap-2">
                          <span class="text-xs text-slate-400">Not scored</span>
                          <button
                            type="button"
                            class="rounded-lg border border-cyan-200/20 bg-cyan-400/10 px-2 py-0.5 text-xs text-cyan-100 disabled:cursor-not-allowed disabled:opacity-50"
                            :disabled="!product.is_cached || scoreStateFor(product.product_id).loading"
                            @click="$emit('score-product', product)"
                          >
                            Score
                          </button>
                          <span v-if="!product.is_cached" class="text-xs text-slate-500">
                            cache file first
                          </span>
                        </div>
                        <p
                          v-if="scoreStateFor(product.product_id).error"
                          class="mt-1 text-xs text-rose-200"
                        >
                          {{ scoreStateFor(product.product_id).error }}
                        </p>
                      </div>

                      <div class="rounded-lg border border-white/10 bg-slate-950/30 p-2">
                        <div class="mb-2 flex items-center justify-between gap-2">
                          <p class="text-xs font-medium text-slate-200">User Override</p>
                          <span
                            v-if="annotationStateFor(product.product_id).data"
                            class="inline-flex rounded-full border border-emerald-300/40 bg-emerald-300/10 px-2 py-0.5 text-xs text-emerald-100"
                          >
                            User override active
                          </span>
                        </div>

                        <div class="space-y-2">
                          <select
                            class="w-full rounded-md border border-white/10 bg-slate-950/60 px-2 py-1 text-xs text-slate-100"
                            :value="annotationDraftFor(product.product_id).user_label"
                            @change="
                              $emit('update-annotation-draft', product.product_id, {
                                user_label: $event.target.value,
                              })
                            "
                          >
                            <option value="unknown">Unknown</option>
                            <option value="yes">Yes</option>
                            <option value="no">No</option>
                          </select>

                          <div>
                            <label class="mb-1 block text-[11px] uppercase tracking-[0.08em] text-slate-400">
                              Override confidence
                            </label>
                            <input
                              type="range"
                              min="0"
                              max="1"
                              step="0.01"
                              class="w-full"
                              :disabled="annotationDraftFor(product.product_id).user_label === 'unknown'"
                              :value="
                                annotationDraftFor(product.product_id).user_confidence ?? 0.5
                              "
                              @input="
                                $emit('update-annotation-draft', product.product_id, {
                                  user_confidence: Number($event.target.value),
                                })
                              "
                            />
                            <p class="mt-1 text-xs text-slate-400">
                              {{
                                annotationDraftFor(product.product_id).user_label === "unknown"
                                  ? "Disabled for Unknown"
                                  : `${Math.round((annotationDraftFor(product.product_id).user_confidence ?? 0.5) * 100)}%`
                              }}
                            </p>
                          </div>

                          <textarea
                            class="min-h-14 w-full rounded-md border border-white/10 bg-slate-950/60 px-2 py-1 text-xs text-slate-100 placeholder:text-slate-500"
                            placeholder="Optional note"
                            :value="annotationDraftFor(product.product_id).note"
                            @input="
                              $emit('update-annotation-draft', product.product_id, {
                                note: $event.target.value,
                              })
                            "
                          />

                          <button
                            type="button"
                            class="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                            :disabled="annotationStateFor(product.product_id).saving"
                            @click="$emit('save-annotation', product)"
                          >
                            {{
                              annotationStateFor(product.product_id).saving ? "Saving..." : "Save"
                            }}
                          </button>
                          <p
                            v-if="annotationStateFor(product.product_id).loading"
                            class="text-xs text-slate-400"
                          >
                            Loading override...
                          </p>
                          <p
                            v-if="annotationStateFor(product.product_id).error"
                            class="text-xs text-rose-200"
                          >
                            {{ annotationStateFor(product.product_id).error }}
                          </p>
                        </div>
                      </div>
                    </div>
                  </template>
                  <span v-else class="text-xs text-slate-500">—</span>
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
