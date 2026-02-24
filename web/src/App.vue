<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  ApiError,
  downloadProduct,
  fetchSpectrum,
  health,
  listProducts,
  mastPing,
  searchObservations,
} from "./lib/api";
import PlotPanel from "./components/PlotPanel.vue";
import ProductsPanel from "./components/ProductsPanel.vue";
import SearchPanel from "./components/SearchPanel.vue";
import StatusHeader from "./components/StatusHeader.vue";

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

      <StatusHeader
        :backend-status="backendStatus"
        :mast-status="mastStatus"
        @refresh-status="refreshStatus"
      />

      <main class="relative mx-auto max-w-7xl px-6 py-8 sm:py-10">
        <section
          class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]"
        >
          <SearchPanel
            :search-form="searchForm"
            :search-state="searchState"
            :search-results="searchResults"
            :selected-observation="selectedObservation"
            @run-search="runSearch"
            @select-observation="selectObservation"
          />

          <div class="grid gap-6">
            <ProductsPanel
              :selected-observation="selectedObservation"
              :products-state="productsState"
              :products="products"
              :product-downloads="productDownloads"
              :product-plots="productPlots"
              @download-product="handleDownloadProduct"
              @plot-product="handlePlotProduct"
            />

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
          </div>
        </section>
      </main>
    </div>
  </div>
</template>
