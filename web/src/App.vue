<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  ApiError,
  downloadProduct,
  fetchSpectrum,
  health,
  listProducts,
  mastPing,
  searchObservations,
} from "./lib/api";

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
const productDownloads = ref({});
const plotState = ref({
  loading: false,
  error: "",
  productId: "",
  filename: "",
  segmentCount: 0,
});
const productPlots = ref({});
const plotContainerEl = ref(null);
let plotlyModulePromise = null;

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
    clearPlot();
    return;
  }

  products.value = [];
  clearPlot();
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

async function handleDownloadProduct(product) {
  if (!product?.product_id || !selectedObservation.value) {
    return;
  }

  const productId = product.product_id;
  productDownloads.value = {
    ...productDownloads.value,
    [productId]: {
      loading: true,
      error: "",
    },
  };

  try {
    await downloadProduct(productId);
    await loadProductsForObservation(selectedObservation.value);
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.status === 403 && error.data?.requires_auth
          ? "This product is not public yet (exclusive access)."
          : error.message
        : error instanceof Error
          ? error.message
          : "Download failed";

    productDownloads.value = {
      ...productDownloads.value,
      [productId]: {
        loading: false,
        error: message,
      },
    };
    return;
  }

  productDownloads.value = {
    ...productDownloads.value,
    [productId]: {
      loading: false,
      error: "",
    },
  };
}

function downloadStateFor(productId) {
  return productDownloads.value[productId] ?? { loading: false, error: "" };
}

function plotActionStateFor(productId) {
  return productPlots.value[productId] ?? { loading: false, error: "" };
}

async function handlePlotProduct(product) {
  if (!product?.product_id) {
    return;
  }

  const productId = product.product_id;
  productPlots.value = {
    ...productPlots.value,
    [productId]: { loading: true, error: "" },
  };
  plotState.value = {
    ...plotState.value,
    loading: true,
    error: "",
    productId,
    filename: product.productFilename || "",
    segmentCount: 0,
  };

  try {
    const spectrum = await fetchSpectrum(productId);
    await renderSpectrumPlot(spectrum);
    plotState.value = {
      loading: false,
      error: "",
      productId,
      filename: spectrum?.filename || product.productFilename || "",
      segmentCount: Array.isArray(spectrum?.segments) ? spectrum.segments.length : 0,
    };
    productPlots.value = {
      ...productPlots.value,
      [productId]: { loading: false, error: "" },
    };
  } catch (error) {
    let message = "Failed to load spectrum";
    if (error instanceof ApiError) {
      if (error.status === 404) {
        message = "Please download the file first.";
      } else if (error.status === 422) {
        const hduHint = Array.isArray(error.data?.available_hdus)
          ? ` Available HDUs: ${error.data.available_hdus
              .map((hdu) => `${hdu.index}:${hdu.name || hdu.type}`)
              .join(", ")}`
          : "";
        message = `Spectrum table not found.${hduHint}`.trim();
      } else {
        message = error.message;
      }
    } else if (error instanceof Error) {
      message = error.message;
    }

    plotState.value = {
      ...plotState.value,
      loading: false,
      error: message,
      productId,
      filename: product.productFilename || "",
      segmentCount: 0,
    };
    productPlots.value = {
      ...productPlots.value,
      [productId]: { loading: false, error: message },
    };
  }
}

async function getPlotly() {
  if (!plotlyModulePromise) {
    plotlyModulePromise = import("plotly.js-dist-min");
  }
  const mod = await plotlyModulePromise;
  return mod.default ?? mod;
}

async function renderSpectrumPlot(spectrum) {
  await nextTick();
  if (!plotContainerEl.value) {
    throw new Error("Plot container not ready");
  }

  const Plotly = await getPlotly();
  const segments = Array.isArray(spectrum?.segments) ? spectrum.segments : [];

  const traces = segments.map((segment, index) => ({
    x: segment?.data?.wavelength ?? [],
    y: segment?.data?.flux ?? [],
    type: "scattergl",
    mode: "lines",
    name: segment?.label || `Segment ${index + 1}`,
    line: { width: 1.5 },
  }));

  const firstSegment = segments[0] ?? null;
  const wavelengthUnit = firstSegment?.units?.wavelength || null;
  const fluxUnit = firstSegment?.units?.flux || null;

  await Plotly.react(
    plotContainerEl.value,
    traces,
    {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(2,6,23,0.35)",
      margin: { t: 36, r: 18, b: 56, l: 64 },
      font: { color: "#dbeafe" },
      xaxis: {
        title: wavelengthUnit ? `Wavelength (${wavelengthUnit})` : "Wavelength",
        gridcolor: "rgba(148,163,184,0.16)",
        zeroline: false,
      },
      yaxis: {
        title: fluxUnit ? `Flux (${fluxUnit})` : "Flux",
        gridcolor: "rgba(148,163,184,0.16)",
        zeroline: false,
      },
      legend: {
        orientation: "h",
        y: 1.18,
        x: 0,
        bgcolor: "rgba(0,0,0,0)",
      },
    },
    {
      displaylogo: false,
      responsive: true,
    },
  );
}

async function clearPlot() {
  plotState.value = {
    loading: false,
    error: "",
    productId: "",
    filename: "",
    segmentCount: 0,
  };
  if (!plotContainerEl.value) return;
  try {
    const Plotly = await getPlotly();
    Plotly.purge(plotContainerEl.value);
  } catch {
    // Ignore cleanup errors (e.g. dependency not installed yet).
  }
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

function dataRightsBadgeClass(value) {
  const rights = String(value || "").toUpperCase();
  if (rights === "PUBLIC") {
    return "border-emerald-300/40 bg-emerald-300/10 text-emerald-100";
  }
  if (!rights) {
    return "border-white/10 bg-white/5 text-slate-300";
  }
  return "border-amber-300/40 bg-amber-300/10 text-amber-100";
}

watch(
  () => selectedObservation.value,
  (observation) => {
    loadProductsForObservation(observation);
  },
);

onBeforeUnmount(async () => {
  if (!plotContainerEl.value) return;
  try {
    const Plotly = await getPlotly();
    Plotly.purge(plotContainerEl.value);
  } catch {
    // no-op
  }
});

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
                      <td class="px-3 py-2 align-top">
                        <span
                          class="inline-flex rounded-full border px-2 py-0.5 text-xs"
                          :class="dataRightsBadgeClass(row.data_rights)"
                        >
                          {{ row.data_rights || "—" }}
                        </span>
                      </td>
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
                                @click="handleDownloadProduct(product)"
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
                                type="button"
                                class="rounded-lg border border-cyan-200/20 bg-cyan-400/10 px-2.5 py-1 text-xs text-cyan-100 disabled:cursor-not-allowed disabled:opacity-50"
                                v-if="product.kind === 'spectrum1d' && product.is_cached"
                                :disabled="plotActionStateFor(product.product_id).loading"
                                :title="
                                  plotActionStateFor(product.product_id).loading
                                    ? 'Loading spectrum...'
                                    : 'Plot cached spectrum'
                                "
                                @click="handlePlotProduct(product)"
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
                <div
                  ref="plotContainerEl"
                  class="min-h-72 w-full"
                />
                <div
                  v-if="!plotState.productId && !plotState.loading && !plotState.error"
                  class="pointer-events-none absolute"
                />
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>
