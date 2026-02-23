<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { ApiError, health, listProducts, mastPing, searchObservations } from "./lib/api";

const backendStatus = ref({
  state: "checking",
  message: "",
});
const mastStatus = ref({
  state: "checking",
  message: "",
});
const searchForm = ref({
  target: "NGC 7027",
  radiusArcsec: 30,
});
const searchState = ref({
  loading: false,
  error: "",
  hasSearched: false,
});
const searchResults = ref([]);
const selectedObservation = ref(null);
const productsState = ref({
  loading: false,
  error: "",
});
const products = ref([]);

const healthBadge = computed(() => badgeViewModel("health", backendStatus.value));
const mastBadge = computed(() => badgeViewModel("mast", mastStatus.value));

function badgeViewModel(kind, status) {
  if (status.state === "ok") {
    return {
      label: kind === "health" ? "Connected" : "MAST ok",
      classes: "border-emerald-300/60 bg-emerald-400/15 text-emerald-100",
      dot: "bg-emerald-300",
      title: status.message || "",
    };
  }
  if (status.state === "error") {
    return {
      label: kind === "health" ? "Disconnected" : "MAST error",
      classes: "border-rose-300/60 bg-rose-400/15 text-rose-100",
      dot: "bg-rose-300",
      title: status.message || "",
    };
  }
  return {
    label: kind === "health" ? "Checking" : "MAST checking",
    classes: "border-slate-300/40 bg-slate-400/10 text-slate-100",
    dot: "bg-slate-300",
    title: "",
  };
}

async function refreshStatus() {
  try {
    const data = await health();
    backendStatus.value = {
      state: data?.status === "ok" ? "ok" : "error",
      message: data?.status === "ok" ? "" : "Unexpected health response",
    };
  } catch (error) {
    backendStatus.value = {
      state: "error",
      message: error instanceof Error ? error.message : "Backend not reachable on :8000",
    };
  }

  try {
    const data = await mastPing();
    mastStatus.value = {
      state: data?.status === "ok" ? "ok" : "error",
      message: data?.status === "ok" ? "" : "Unexpected MAST ping response",
    };
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : error instanceof Error
          ? error.message
          : "MAST ping failed";
    mastStatus.value = {
      state: "error",
      message,
    };
  }
}

async function runSearch() {
  searchState.value.loading = true;
  searchState.value.error = "";
  searchState.value.hasSearched = true;

  try {
    const results = await searchObservations(
      searchForm.value.target,
      searchForm.value.radiusArcsec,
    );
    searchResults.value = Array.isArray(results) ? results : [];
    if (
      selectedObservation.value &&
      !searchResults.value.some((row) => row.obsid === selectedObservation.value.obsid)
    ) {
      selectedObservation.value = null;
    }
  } catch (error) {
    searchResults.value = [];
    searchState.value.error =
      error instanceof ApiError || error instanceof Error
        ? error.message
        : "Search failed";
  } finally {
    searchState.value.loading = false;
  }
}

function selectObservation(observation) {
  selectedObservation.value = observation;
}

async function loadProductsForObservation(observation) {
  if (!observation?.obsid) {
    products.value = [];
    productsState.value = { loading: false, error: "" };
    return;
  }

  productsState.value = { loading: true, error: "" };
  try {
    const rows = await listProducts(observation.obsid);
    products.value = Array.isArray(rows) ? rows : [];
  } catch (error) {
    products.value = [];
    productsState.value = {
      loading: false,
      error:
        error instanceof ApiError || error instanceof Error
          ? error.message
          : "Failed to load products",
    };
    return;
  }

  productsState.value = { loading: false, error: "" };
}

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined || Number.isNaN(Number(bytes))) {
    return "—";
  }
  const value = Number(bytes);
  if (value < 1024) return `${value} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let size = value;
  let unitIndex = -1;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size >= 100 ? size.toFixed(0) : size.toFixed(1)} ${units[unitIndex]}`;
}

watch(
  () => selectedObservation.value,
  (observation) => {
    loadProductsForObservation(observation);
  },
);

onMounted(() => {
  refreshStatus();
});
</script>

<template>
  <div
    class="min-h-screen bg-slate-950 text-slate-100 selection:bg-cyan-300 selection:text-slate-900"
  >
    <div class="relative isolate min-h-screen overflow-hidden">
      <div
        class="absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(56,189,248,0.18),transparent_40%),radial-gradient(circle_at_85%_15%,rgba(34,197,94,0.16),transparent_42%),radial-gradient(circle_at_50%_90%,rgba(59,130,246,0.14),transparent_48%)]"
      />

      <header class="relative mx-auto max-w-7xl px-6 pt-8 sm:pt-10">
        <div
          class="rounded-2xl border border-white/10 bg-white/5 px-5 py-4 shadow-panel backdrop-blur-xl sm:px-6"
        >
          <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p class="text-xs uppercase tracking-[0.18em] text-cyan-200/80">
                PAH Analysis
              </p>
              <h1 class="mt-1 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                PAH Analysis — JWST Viewer
              </h1>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                class="inline-flex items-center rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 transition hover:bg-white/10"
                @click="refreshStatus"
              >
                Refresh status
              </button>

              <span
                class="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium"
                :class="healthBadge.classes"
                :title="healthBadge.title"
              >
                <span class="h-2 w-2 rounded-full" :class="healthBadge.dot" />
                {{ healthBadge.label }}
              </span>

              <span
                class="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium"
                :class="mastBadge.classes"
                :title="mastStatus.message || ''"
              >
                <span class="h-2 w-2 rounded-full" :class="mastBadge.dot" />
                {{ mastBadge.label }}
              </span>
            </div>
          </div>

          <p
            v-if="backendStatus.state === 'error'"
            class="mt-3 text-sm text-rose-200"
          >
            {{ backendStatus.message || "Backend not reachable on :8000" }}
          </p>
          <p
            v-if="mastStatus.state === 'error'"
            class="mt-2 text-sm text-amber-100/90"
          >
            MAST: {{ mastStatus.message }}
          </p>
        </div>
      </header>

      <main class="relative mx-auto max-w-7xl px-6 py-8 sm:py-10">
        <section
          class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]"
        >
          <div
            class="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-panel backdrop-blur-xl sm:p-6"
          >
            <div class="flex items-center justify-between gap-3">
              <h2 class="text-lg font-semibold text-white">Search & Results</h2>
              <span class="text-xs uppercase tracking-[0.14em] text-slate-300">
                Left panel
              </span>
            </div>

            <div class="mt-5 space-y-4">
              <div>
                <label class="mb-2 block text-sm font-medium text-slate-200">
                  Target Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. NGC 7027"
                  class="w-full rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-cyan-300/60 focus:outline-none"
                  v-model="searchForm.target"
                  :disabled="searchState.loading"
                />
              </div>

              <div>
                <label class="mb-2 block text-sm font-medium text-slate-200">
                  Radius (arcsec)
                </label>
                <input
                  type="number"
                  placeholder="30"
                  class="w-full rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-cyan-300/60 focus:outline-none"
                  v-model.number="searchForm.radiusArcsec"
                  :disabled="searchState.loading"
                  min="0.1"
                  max="3600"
                  step="0.1"
                />
              </div>

              <button
                type="button"
                class="w-full rounded-xl border border-cyan-200/20 bg-cyan-400/10 px-4 py-2.5 text-sm font-medium text-cyan-100 transition hover:bg-cyan-400/15 disabled:cursor-not-allowed disabled:opacity-60"
                :disabled="searchState.loading"
                @click="runSearch"
              >
                {{ searchState.loading ? "Searching..." : "Search" }}
              </button>
            </div>

            <div class="mt-6 rounded-xl border border-white/10 bg-slate-950/30 p-4">
              <div class="flex items-center justify-between gap-3">
                <p class="text-sm font-medium text-slate-200">Observation Results</p>
                <span
                  v-if="searchState.hasSearched && !searchState.loading && !searchState.error"
                  class="text-xs text-slate-400"
                >
                  {{ searchResults.length }} row<span v-if="searchResults.length !== 1">s</span>
                </span>
              </div>

              <p
                v-if="searchState.error"
                class="mt-3 text-sm leading-6 text-rose-200"
              >
                {{ searchState.error }}
              </p>

              <p
                v-else-if="searchState.loading"
                class="mt-3 text-sm leading-6 text-slate-300"
              >
                Searching JWST observations...
              </p>

              <p
                v-else-if="searchState.hasSearched && searchResults.length === 0"
                class="mt-3 text-sm leading-6 text-slate-300"
              >
                No JWST observations found.
              </p>

              <p
                v-else-if="!searchState.hasSearched"
                class="mt-3 text-sm leading-6 text-slate-400"
              >
                Search by target name using
                <code class="rounded bg-white/10 px-1 py-0.5">GET /api/search</code>.
              </p>

              <div
                v-else
                class="mt-4 max-h-[26rem] overflow-auto rounded-lg border border-white/10"
              >
                <table class="min-w-full text-left text-sm">
                  <thead class="sticky top-0 bg-slate-900/95 text-xs uppercase tracking-[0.12em] text-slate-400">
                    <tr>
                      <th class="px-3 py-2 font-medium">Target</th>
                      <th class="px-3 py-2 font-medium">Instrument</th>
                      <th class="px-3 py-2 font-medium">Obsid</th>
                      <th class="px-3 py-2 font-medium">Proposal</th>
                      <th class="px-3 py-2 font-medium">Rights</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="row in searchResults"
                      :key="`${row.obsid}-${row.instrument_name || 'unknown'}`"
                      class="cursor-pointer border-t border-white/5 text-slate-200 transition hover:bg-white/5"
                      :class="
                        selectedObservation?.obsid === row.obsid
                          ? 'bg-cyan-300/10 ring-1 ring-inset ring-cyan-300/30'
                          : ''
                      "
                      @click="selectObservation(row)"
                    >
                      <td class="px-3 py-2 align-top">{{ row.target_name || "—" }}</td>
                      <td class="px-3 py-2 align-top">{{ row.instrument_name || "—" }}</td>
                      <td class="px-3 py-2 align-top font-mono text-xs">{{ row.obsid || "—" }}</td>
                      <td class="px-3 py-2 align-top">{{ row.proposal_id || "—" }}</td>
                      <td class="px-3 py-2 align-top">{{ row.data_rights || "—" }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div class="grid gap-6">
            <div
              class="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-panel backdrop-blur-xl sm:p-6"
            >
              <div class="flex items-center justify-between gap-3">
                <h2 class="text-lg font-semibold text-white">Products & Actions</h2>
                <span class="text-xs uppercase tracking-[0.14em] text-slate-300">
                  Right panel
                </span>
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
                <div class="mt-3 rounded-lg border border-white/5 bg-white/5 p-3 text-sm text-slate-300">
                  <p class="font-medium text-slate-200">Selected observation</p>
                  <p v-if="selectedObservation" class="mt-2 leading-6">
                    <span class="font-mono text-xs">{{ selectedObservation.obsid }}</span>
                    · {{ selectedObservation.target_name || "Unknown target" }}
                    <span v-if="selectedObservation.instrument_name">
                      · {{ selectedObservation.instrument_name }}
                    </span>
                  </p>
                  <p v-else class="mt-2 text-slate-400">
                    Click a search result row to select an observation.
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
                                :disabled="false"
                                :title="product.product_id"
                              >
                                {{ product.is_cached ? "Re-download" : "Download" }}
                              </button>
                              <button
                                type="button"
                                class="rounded-lg border border-cyan-200/20 bg-cyan-400/10 px-2.5 py-1 text-xs text-cyan-100 disabled:cursor-not-allowed disabled:opacity-50"
                                :disabled="!product.is_plottable_candidate"
                                :title="
                                  product.is_plottable_candidate
                                    ? (product.is_cached ? 'Ready to plot after wiring action' : 'Download required before plotting')
                                    : 'Not plottable'
                                "
                              >
                                Plot
                              </button>
                            </div>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>

            <div
              class="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-panel backdrop-blur-xl sm:p-6"
            >
              <h2 class="text-lg font-semibold text-white">Plot Area</h2>
              <p class="mt-3 text-sm leading-6 text-slate-400">
                Spectrum segments from
                <code class="rounded bg-white/10 px-1 py-0.5">GET /api/products/spectrum</code>
                will be plotted here in the MVP flow.
              </p>

              <div
                class="mt-4 grid min-h-52 place-items-center rounded-xl border border-dashed border-cyan-200/15 bg-gradient-to-br from-cyan-400/5 via-transparent to-emerald-300/5"
              >
                <div class="text-center">
                  <p class="text-sm font-medium text-slate-200">Plot placeholder</p>
                  <p class="mt-1 text-xs uppercase tracking-[0.16em] text-slate-500">
                    Awaiting selected x1d/c1d product
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>
