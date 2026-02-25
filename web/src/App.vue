<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  ApiError,
  downloadProduct,
  fetchSpectrum,
  getPahScore,
  getProductAnnotation,
  health,
  listCachedProducts,
  listProducts,
  mastPing,
  putProductAnnotation,
  searchObservations,
} from "./lib/api";
import CachedProductsPanel from "./components/CachedProductsPanel.vue";
import PlotPanel from "./components/PlotPanel.vue";
import ProductsPanel from "./components/ProductsPanel.vue";
import SearchPanel from "./components/SearchPanel.vue";
import StatusHeader from "./components/StatusHeader.vue";

const OBS_SEARCH_CACHE_STORAGE_KEY = "pah-analysis:observation-search-cache:v1";

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
const observationSearchCache = ref({});
const leftPanelTab = ref("search");
const selectedCachedQueryKey = ref("");
const selectedObservation = ref(null);
const productsState = ref({
  loading: false,
  error: "",
});
const products = ref([]);
const cachedProductsState = ref({
  loading: false,
  error: "",
});
const cachedProducts = ref([]);
const productDownloads = ref({});
const productScores = ref({});
const productAnnotations = ref({});
const annotationDrafts = ref({});
const productListOptions = ref({
  onlyLikelyPah: false,
});
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

const displayedProducts = computed(() => {
  const rows = Array.isArray(products.value) ? [...products.value] : [];
  const filtered = productListOptions.value.onlyLikelyPah
    ? rows.filter((product) => isLikelyPahProduct(product))
    : rows;

  filtered.sort((a, b) => {
    const diff = scoreConfidenceFor(b) - scoreConfidenceFor(a);
    if (diff !== 0) return diff;
    return String(a.productFilename || "").localeCompare(String(b.productFilename || ""));
  });

  return filtered;
});

const displayedCachedProducts = computed(() => {
  const rows = Array.isArray(cachedProducts.value) ? [...cachedProducts.value] : [];
  rows.sort((a, b) => {
    const diff = scoreConfidenceFor(b) - scoreConfidenceFor(a);
    if (diff !== 0) return diff;
    return String(a.productFilename || "").localeCompare(String(b.productFilename || ""));
  });
  return rows;
});

const searchCacheMeta = computed(() => {
  const key = searchCacheKey(searchForm.value);
  const entry = observationSearchCache.value[key] ?? null;
  return {
    key,
    hasCache: Boolean(entry),
    lastFetchedAt: entry?.fetchedAt ?? null,
    rowCount: Array.isArray(entry?.results) ? entry.results.length : 0,
  };
});

const cachedQueryOptions = computed(() => {
  const entries = Object.entries(observationSearchCache.value ?? {});
  return entries
    .map(([key, entry]) => {
      const query = normalizeSearchQuery(entry?.query, key);
      if (!query?.target) return null;
      return {
        key,
        target: query.target,
        radiusArcsec: query.radiusArcsec,
        fetchedAt: entry?.fetchedAt ?? null,
        rowCount: Array.isArray(entry?.results) ? entry.results.length : 0,
      };
    })
    .filter(Boolean)
    .sort((a, b) => String(b.fetchedAt || "").localeCompare(String(a.fetchedAt || "")));
});

const cachedSelectionMeta = computed(() => {
  const key = selectedCachedQueryKey.value;
  if (!key) {
    return { hasSelection: false, lastFetchedAt: null, rowCount: 0 };
  }
  const entry = observationSearchCache.value[key] ?? null;
  return {
    hasSelection: Boolean(entry),
    lastFetchedAt: entry?.fetchedAt ?? null,
    rowCount: Array.isArray(entry?.results) ? entry.results.length : 0,
  };
});

watch(
  observationSearchCache,
  (cache) => {
    try {
      localStorage.setItem(
        OBS_SEARCH_CACHE_STORAGE_KEY,
        JSON.stringify(cache ?? {}),
      );
    } catch {
      // Ignore storage quota/private mode failures.
    }
  },
  { deep: true },
);

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

function searchCacheKey(form) {
  const target = String(form?.target ?? "").trim().toLowerCase();
  const radiusValue = Number(form?.radiusArcsec);
  const radius = Number.isFinite(radiusValue) ? radiusValue : "";
  return JSON.stringify({ target, radius });
}

function parseSearchCacheKey(key) {
  try {
    const parsed = JSON.parse(String(key));
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    const target = typeof parsed.target === "string" ? parsed.target : "";
    const radiusRaw = parsed.radius;
    const radiusValue = Number(radiusRaw);
    return {
      target: target.trim(),
      radiusArcsec: Number.isFinite(radiusValue) ? radiusValue : null,
    };
  } catch {
    return null;
  }
}

function normalizeSearchQuery(query, key) {
  if (query && typeof query === "object" && !Array.isArray(query)) {
    const target = String(query.target ?? "").trim();
    const radiusRaw = Number(query.radiusArcsec);
    return {
      target,
      radiusArcsec: Number.isFinite(radiusRaw) ? radiusRaw : null,
    };
  }
  return parseSearchCacheKey(key);
}

function normalizeObservationSearchCache(cache) {
  if (!cache || typeof cache !== "object" || Array.isArray(cache)) {
    return {};
  }

  const normalized = {};
  for (const [key, entry] of Object.entries(cache)) {
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) continue;
    const query = normalizeSearchQuery(entry.query, key);
    normalized[key] = {
      query,
      results: Array.isArray(entry.results) ? entry.results : [],
      fetchedAt:
        typeof entry.fetchedAt === "string" && entry.fetchedAt.trim()
          ? entry.fetchedAt
          : null,
    };
  }
  return normalized;
}

function applySearchResults(results) {
  searchResults.value = Array.isArray(results) ? results : [];
  if (
    selectedObservation.value &&
    !searchResults.value.some((row) => row.obsid === selectedObservation.value.obsid)
  ) {
    selectedObservation.value = null;
  }
}

async function runSearch(options = {}) {
  return runSearchForQuery(
    {
      target: searchForm.value.target,
      radiusArcsec: searchForm.value.radiusArcsec,
    },
    options,
  );
}

async function runSearchForQuery(query, options = {}) {
  const force = options.force === true;
  const cacheKey = searchCacheKey(query);
  const cached = observationSearchCache.value[cacheKey];

  if (!force && cached) {
    searchState.value = {
      ...searchState.value,
      loading: false,
      error: "",
      hasSearched: true,
    };
    applySearchResults(cached.results);
    selectedCachedQueryKey.value = cacheKey;
    return;
  }

  searchState.value.loading = true;
  searchState.value.error = "";
  searchState.value.hasSearched = true;

  try {
    const results = await searchObservations(
      query.target,
      query.radiusArcsec,
    );
    const normalizedResults = Array.isArray(results) ? results : [];
    observationSearchCache.value = {
      ...observationSearchCache.value,
      [cacheKey]: {
        query: {
          target: String(query.target ?? "").trim(),
          radiusArcsec: Number(query.radiusArcsec),
        },
        results: normalizedResults,
        fetchedAt: new Date().toISOString(),
      },
    };
    applySearchResults(normalizedResults);
    selectedCachedQueryKey.value = cacheKey;
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

function refetchSearch() {
  return runSearch({ force: true });
}

function setLeftPanelTab(tab) {
  leftPanelTab.value = tab === "cached" ? "cached" : "search";
}

function selectCachedQuery(key) {
  selectedCachedQueryKey.value = key;
  const entry = observationSearchCache.value[key];
  if (!entry) return;

  const query = normalizeSearchQuery(entry.query, key);
  if (query?.target) {
    searchForm.value = {
      target: query.target,
      radiusArcsec: query.radiusArcsec ?? searchForm.value.radiusArcsec,
    };
  }

  searchState.value = {
    ...searchState.value,
    loading: false,
    error: "",
    hasSearched: true,
  };
  applySearchResults(entry.results);
}

function refetchCachedSearch() {
  const key = selectedCachedQueryKey.value;
  const entry = observationSearchCache.value[key];
  if (!entry) return;
  const query = normalizeSearchQuery(entry.query, key);
  if (!query?.target) return;
  return runSearchForQuery(query, { force: true });
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
    seedAnnotationDrafts(products.value);
    preloadPahMetadata(products.value);
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

async function loadCachedProductsCatalog() {
  cachedProductsState.value = {
    ...cachedProductsState.value,
    loading: true,
    error: "",
  };

  try {
    const rows = await listCachedProducts();
    cachedProducts.value = Array.isArray(rows) ? rows : [];
    seedAnnotationDrafts(cachedProducts.value);
    preloadPahMetadata(cachedProducts.value);
    cachedProductsState.value = { loading: false, error: "" };
  } catch (error) {
    cachedProductsState.value = {
      loading: false,
      error:
        error instanceof ApiError || error instanceof Error
          ? error.message
          : "Failed to load cached products",
    };
  }
}

function isSpectrum1dProduct(product) {
  return product?.kind === "spectrum1d";
}

function isScorableProduct(product) {
  return isSpectrum1dProduct(product) && Boolean(product?.is_cached);
}

function scoreStateFor(productId) {
  return (
    productScores.value[productId] ?? {
      loading: false,
      error: "",
      data: null,
    }
  );
}

function annotationStateFor(productId) {
  return (
    productAnnotations.value[productId] ?? {
      loading: false,
      saving: false,
      error: "",
      data: null,
    }
  );
}

function annotationDraftFor(productId) {
  return (
    annotationDrafts.value[productId] ?? {
      user_label: "unknown",
      user_confidence: null,
      note: "",
    }
  );
}

function seedAnnotationDrafts(rows) {
  const next = { ...annotationDrafts.value };
  for (const product of rows || []) {
    if (!product?.product_id || !isSpectrum1dProduct(product)) continue;
    if (!next[product.product_id]) {
      next[product.product_id] = {
        user_label: "unknown",
        user_confidence: null,
        note: "",
      };
    }
  }
  annotationDrafts.value = next;
}

async function preloadPahMetadata(rows) {
  const spectrumRows = (rows || []).filter((row) => isSpectrum1dProduct(row));
  for (const product of spectrumRows) {
    void loadAnnotation(product.product_id);
    if (isScorableProduct(product)) {
      void loadPahScore(product, { silentIfMissing: true });
    }
  }
}

async function loadPahScore(product, options = {}) {
  const productId = product?.product_id;
  if (!productId) return null;

  const current = scoreStateFor(productId);
  productScores.value = {
    ...productScores.value,
    [productId]: {
      ...current,
      loading: true,
      error: "",
    },
  };

  try {
    const data = await getPahScore(productId, { force: options.force === true });
    productScores.value = {
      ...productScores.value,
      [productId]: {
        loading: false,
        error: "",
        data,
      },
    };
    return data;
  } catch (error) {
    let message = error instanceof ApiError || error instanceof Error ? error.message : "Scoring failed";
    if (options.silentIfMissing && error instanceof ApiError && error.status === 404) {
      message = "";
    }
    productScores.value = {
      ...productScores.value,
      [productId]: {
        loading: false,
        error: message,
        data: current?.data ?? null,
      },
    };
    return null;
  }
}

async function loadAnnotation(productId) {
  if (!productId) return null;

  const current = annotationStateFor(productId);
  productAnnotations.value = {
    ...productAnnotations.value,
    [productId]: {
      ...current,
      loading: true,
      error: "",
    },
  };

  try {
    const data = await getProductAnnotation(productId);
    productAnnotations.value = {
      ...productAnnotations.value,
      [productId]: {
        loading: false,
        saving: false,
        error: "",
        data,
      },
    };
    if (data) {
      annotationDrafts.value = {
        ...annotationDrafts.value,
        [productId]: {
          user_label: data.user_label ?? "unknown",
          user_confidence:
            typeof data.user_confidence === "number" ? data.user_confidence : null,
          note: data.note ?? "",
        },
      };
    }
    return data;
  } catch (error) {
    productAnnotations.value = {
      ...productAnnotations.value,
      [productId]: {
        loading: false,
        saving: false,
        error: error instanceof ApiError || error instanceof Error ? error.message : "Failed to load annotation",
        data: current?.data ?? null,
      },
    };
    return null;
  }
}

function handleScoreProduct(product) {
  if (!product?.product_id) return;
  loadPahScore(product, { force: false });
}

function updateAnnotationDraft(productId, patch) {
  if (!productId) return;
  const current = annotationDraftFor(productId);
  const nextLabel = patch.user_label ?? current.user_label;
  const next = {
    ...current,
    ...patch,
  };
  if (nextLabel === "unknown") {
    next.user_confidence = null;
  } else if (
    patch.user_label &&
    current.user_label === "unknown" &&
    (current.user_confidence === null || current.user_confidence === undefined)
  ) {
    next.user_confidence = 0.5;
  }
  annotationDrafts.value = {
    ...annotationDrafts.value,
    [productId]: next,
  };
}

async function handleSaveAnnotation(product) {
  const productId = product?.product_id;
  if (!productId) return;
  const draft = annotationDraftFor(productId);
  const current = annotationStateFor(productId);

  productAnnotations.value = {
    ...productAnnotations.value,
    [productId]: {
      ...current,
      saving: true,
      error: "",
    },
  };

  try {
    const payload = {
      product_id: productId,
      user_label: draft.user_label,
      user_confidence:
        draft.user_label === "unknown"
          ? null
          : draft.user_confidence === null || draft.user_confidence === ""
            ? null
            : Number(draft.user_confidence),
      note: draft.note?.trim() ? draft.note.trim() : null,
    };
    const data = await putProductAnnotation(payload);
    productAnnotations.value = {
      ...productAnnotations.value,
      [productId]: {
        loading: false,
        saving: false,
        error: "",
        data,
      },
    };
    annotationDrafts.value = {
      ...annotationDrafts.value,
      [productId]: {
        user_label: data.user_label ?? "unknown",
        user_confidence:
          typeof data.user_confidence === "number" ? data.user_confidence : null,
        note: data.note ?? "",
      },
    };
  } catch (error) {
    productAnnotations.value = {
      ...productAnnotations.value,
      [productId]: {
        ...current,
        saving: false,
        error:
          error instanceof ApiError || error instanceof Error
            ? error.message
            : "Failed to save annotation",
      },
    };
  }
}

function scoreConfidenceFor(product) {
  const data = scoreStateFor(product?.product_id).data;
  return typeof data?.confidence === "number" ? data.confidence : -1;
}

function isLikelyPahProduct(product) {
  if (!isSpectrum1dProduct(product)) return false;
  const annotation = annotationStateFor(product.product_id).data;
  if (annotation?.user_label === "yes") {
    return true;
  }
  return scoreConfidenceFor(product) >= 0.6;
}

function updateOnlyLikelyPah(value) {
  productListOptions.value = {
    ...productListOptions.value,
    onlyLikelyPah: Boolean(value),
  };
}

async function handleDownloadProduct(product) {
  if (!product?.product_id) {
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
    if (selectedObservation.value) {
      await loadProductsForObservation(selectedObservation.value);
    }
    await loadCachedProductsCatalog();
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
  try {
    const raw = localStorage.getItem(OBS_SEARCH_CACHE_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        observationSearchCache.value = normalizeObservationSearchCache(parsed);
      }
    }
  } catch {
    // Ignore malformed or unavailable localStorage.
  }
  refreshStatus();
  loadCachedProductsCatalog();
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

      <StatusHeader
        :backend-status="backendStatus"
        :mast-status="mastStatus"
        @refresh-status="refreshStatus"
      />

      <main class="relative mx-auto w-full max-w-[1800px] px-6 py-8 sm:py-10">
        <section class="grid gap-6">
          <div
            class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:items-stretch"
          >
          <SearchPanel
            :active-tab="leftPanelTab"
            :search-form="searchForm"
            :search-state="searchState"
            :search-results="searchResults"
            :search-cache-meta="searchCacheMeta"
            :cached-query-options="cachedQueryOptions"
            :selected-cached-query-key="selectedCachedQueryKey"
            :cached-selection-meta="cachedSelectionMeta"
            :selected-observation="selectedObservation"
            @set-active-tab="setLeftPanelTab"
            @run-search="runSearch"
            @refetch-search="refetchCachedSearch"
            @select-cached-query="selectCachedQuery"
            @select-observation="selectObservation"
          />

            <ProductsPanel
              :selected-observation="selectedObservation"
              :products-state="productsState"
              :products="products"
              :displayed-products="displayedProducts"
              :product-downloads="productDownloads"
              :product-plots="productPlots"
              :product-scores="productScores"
              :product-annotations="productAnnotations"
              :annotation-drafts="annotationDrafts"
              :product-list-options="productListOptions"
              @download-product="handleDownloadProduct"
              @plot-product="handlePlotProduct"
              @score-product="handleScoreProduct"
              @update-annotation-draft="updateAnnotationDraft"
              @save-annotation="handleSaveAnnotation"
              @update-only-likely-pah="updateOnlyLikelyPah"
            />
          </div>

          <PlotPanel :plot-state="plotState">
            <div
              ref="plotContainerEl"
              class="min-h-72 w-full"
            />
            <div
              v-if="!plotState.productId && !plotState.loading && !plotState.error"
              class="pointer-events-none absolute"
            />
          </PlotPanel>

          <CachedProductsPanel
            :cached-products-state="cachedProductsState"
            :cached-products="displayedCachedProducts"
            :product-downloads="productDownloads"
            :product-plots="productPlots"
            :product-scores="productScores"
            @refresh="loadCachedProductsCatalog"
            @download-product="handleDownloadProduct"
            @plot-product="handlePlotProduct"
            @score-product="handleScoreProduct"
          />
        </section>
      </main>
    </div>
  </div>
</template>
