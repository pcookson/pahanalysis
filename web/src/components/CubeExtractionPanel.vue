<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  cubeMapState: {
    type: Object,
    required: true,
  },
  cubeMapData: {
    type: Object,
    default: null,
  },
  cubeExtractionState: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["load-cube-map", "extract-spectrum", "close"]);

// Aperture inputs
const apertureCx = ref(0);
const apertureCy = ref(0);
const apertureRadius = ref(3);

// Wavelength filter inputs
const waveMinInput = ref(null);
const waveMaxInput = ref(null);

// Plotly container
const heatmapContainerEl = ref(null);
let plotlyModule = null;
let lastInitProductId = null;

// ── Derived display values ────────────────────────────────────────────────────

const waveUnit = computed(() => props.cubeMapData?.wavelength_range?.unit ?? "um");

const waveRangeLabel = computed(() => {
  if (!props.cubeMapData) return "";
  const { min, max, unit } = props.cubeMapData.wavelength_range;
  return `${min.toFixed(3)}–${max.toFixed(3)} ${unit}`;
});

const pixelScaleArcsec = computed(() => props.cubeMapData?.pixel_scale_arcsec ?? null);

// ── Plotly helpers ────────────────────────────────────────────────────────────

async function getPlotly() {
  if (!plotlyModule) {
    const mod = await import("plotly.js-dist-min");
    plotlyModule = mod.default ?? mod;
  }
  return plotlyModule;
}

function makeCircleTrace(cx, cy, r) {
  const n = 64;
  const angles = Array.from({ length: n + 1 }, (_, i) => (i / n) * 2 * Math.PI);
  return {
    type: "scatter",
    x: angles.map((a) => cx + r * Math.cos(a)),
    y: angles.map((a) => cy + r * Math.sin(a)),
    mode: "lines",
    line: { color: "#22d3ee", width: 2 },
    hoverinfo: "skip",
    showlegend: false,
  };
}

function computeColorRange(map) {
  const flat = map
    .flat()
    .filter((v) => v !== null && Number.isFinite(v))
    .sort((a, b) => a - b);
  if (flat.length === 0) return { zmin: 0, zmax: 1 };
  const p = (pct) => flat[Math.max(0, Math.floor((pct / 100) * (flat.length - 1)))];
  return { zmin: p(2), zmax: p(98) };
}

async function renderHeatmap() {
  if (!heatmapContainerEl.value || !props.cubeMapData) return;
  const Plotly = await getPlotly();

  const { zmin, zmax } = computeColorRange(props.cubeMapData.map);
  const { nx, ny } = props.cubeMapData.shape;

  const traces = [
    {
      type: "heatmap",
      z: props.cubeMapData.map,
      x0: 0,
      dx: 1,
      y0: 0,
      dy: 1,
      colorscale: "Viridis",
      zmin,
      zmax,
      colorbar: {
        tickfont: { color: "#94a3b8", size: 10 },
        len: 0.85,
      },
      hovertemplate: "x: %{x}<br>y: %{y}<br>flux: %{z:.4g}<extra></extra>",
    },
    makeCircleTrace(apertureCx.value, apertureCy.value, apertureRadius.value),
  ];

  await Plotly.react(
    heatmapContainerEl.value,
    traces,
    {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(2,6,23,0.5)",
      margin: { t: 20, r: 20, b: 48, l: 52 },
      font: { color: "#dbeafe" },
      xaxis: {
        title: "x (pixels)",
        gridcolor: "rgba(148,163,184,0.16)",
        zeroline: false,
        range: [-0.5, nx - 0.5],
      },
      yaxis: {
        title: "y (pixels)",
        gridcolor: "rgba(148,163,184,0.16)",
        zeroline: false,
        range: [-0.5, ny - 0.5],
        scaleanchor: "x",
      },
    },
    { displaylogo: false, responsive: true },
  );

  // Register click handler to set aperture center (Plotly deduplicates listeners).
  heatmapContainerEl.value.on("plotly_click", (eventData) => {
    if (eventData?.points?.length > 0) {
      const pt = eventData.points[0];
      apertureCx.value = parseFloat(Number(pt.x).toFixed(1));
      apertureCy.value = parseFloat(Number(pt.y).toFixed(1));
    }
  });
}

// ── Initialisation ────────────────────────────────────────────────────────────

function initInputsFromData(data) {
  apertureCx.value = parseFloat((data.shape.nx / 2).toFixed(1));
  apertureCy.value = parseFloat((data.shape.ny / 2).toFixed(1));
  apertureRadius.value = 3;
  waveMinInput.value = parseFloat(data.wavelength_range.min.toFixed(4));
  waveMaxInput.value = parseFloat(data.wavelength_range.max.toFixed(4));
  lastInitProductId = data.product_id;
}

// ── Watchers ──────────────────────────────────────────────────────────────────

watch(
  () => props.cubeMapData,
  async (newData) => {
    if (!newData) return;
    if (newData.product_id !== lastInitProductId) {
      initInputsFromData(newData);
    }
    await nextTick();
    await renderHeatmap();
  },
);

watch(
  [apertureCx, apertureCy, apertureRadius],
  async () => {
    if (props.cubeMapData && heatmapContainerEl.value) {
      await nextTick();
      await renderHeatmap();
    }
  },
);

// ── Lifecycle ─────────────────────────────────────────────────────────────────

onMounted(async () => {
  if (props.cubeMapData) {
    initInputsFromData(props.cubeMapData);
    await nextTick();
    await renderHeatmap();
  }
});

onBeforeUnmount(async () => {
  if (heatmapContainerEl.value && plotlyModule) {
    try {
      plotlyModule.purge(heatmapContainerEl.value);
    } catch {
      // no-op
    }
  }
});

// ── Handlers ──────────────────────────────────────────────────────────────────

function handleReloadMap() {
  emit("load-cube-map", {
    productId: props.cubeMapData.product_id,
    waveMin: waveMinInput.value,
    waveMax: waveMaxInput.value,
  });
}

function handleExtract() {
  if (!props.cubeMapData) return;
  emit("extract-spectrum", {
    productId: props.cubeMapData.product_id,
    centerX: parseFloat(apertureCx.value),
    centerY: parseFloat(apertureCy.value),
    radius: parseFloat(apertureRadius.value),
  });
}
</script>

<template>
  <div
    class="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-panel backdrop-blur-xl sm:p-6"
  >
    <div class="flex items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <h2 class="text-lg font-semibold text-white">Cube Viewer</h2>
        <span
          v-if="cubeMapData"
          class="inline-flex rounded-full border border-violet-300/40 bg-violet-300/10 px-2 py-0.5 text-xs text-violet-100"
        >
          IFU
        </span>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-xs uppercase tracking-[0.14em] text-slate-300">Aperture extraction</span>
        <button
          type="button"
          class="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200"
          title="Close cube viewer"
          @click="$emit('close')"
        >
          ✕
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="cubeMapState.loading" class="mt-6 text-sm text-slate-300">
      Loading spatial map…
    </div>

    <!-- Error state -->
    <p v-else-if="cubeMapState.error" class="mt-6 text-sm text-rose-200">
      {{ cubeMapState.error }}
    </p>

    <!-- Loaded state -->
    <div
      v-else-if="cubeMapData"
      class="mt-5 grid gap-6 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]"
    >
      <!-- Heatmap -->
      <div
        class="overflow-hidden rounded-xl border border-dashed border-violet-200/15 bg-gradient-to-br from-violet-400/5 via-transparent to-indigo-300/5"
      >
        <div ref="heatmapContainerEl" class="min-h-72 w-full" />
      </div>

      <!-- Controls column -->
      <div class="flex flex-col gap-4">
        <!-- File info -->
        <div class="rounded-lg border border-white/10 bg-slate-950/40 p-3 text-xs">
          <p class="truncate font-mono text-slate-200" :title="cubeMapData.filename">
            {{ cubeMapData.filename }}
          </p>
          <p class="mt-1 text-slate-400">
            {{ cubeMapData.shape.nx }}&thinsp;×&thinsp;{{ cubeMapData.shape.ny }} spaxels
            &middot; {{ cubeMapData.shape.nwave }} wavelengths
          </p>
          <p class="mt-0.5 text-slate-400">λ {{ waveRangeLabel }}</p>
          <p v-if="pixelScaleArcsec" class="mt-0.5 text-slate-400">
            {{ pixelScaleArcsec.toFixed(3) }}″ / pixel
          </p>
          <p v-if="cubeMapData.flux_unit" class="mt-0.5 text-slate-400">
            {{ cubeMapData.flux_unit }}
          </p>
        </div>

        <!-- Wavelength filter -->
        <div class="rounded-lg border border-white/10 bg-slate-950/30 p-3">
          <p class="mb-2 text-xs font-medium text-slate-200">
            Collapse λ range ({{ waveUnit }})
          </p>
          <div class="flex items-center gap-2">
            <input
              v-model.number="waveMinInput"
              type="number"
              step="any"
              class="w-full rounded-md border border-white/10 bg-slate-950/60 px-2 py-1 text-xs text-slate-100"
              placeholder="min"
            />
            <span class="shrink-0 text-slate-400">–</span>
            <input
              v-model.number="waveMaxInput"
              type="number"
              step="any"
              class="w-full rounded-md border border-white/10 bg-slate-950/60 px-2 py-1 text-xs text-slate-100"
              placeholder="max"
            />
          </div>
          <button
            type="button"
            class="mt-2 w-full rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-slate-200 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="cubeMapState.loading"
            @click="handleReloadMap"
          >
            {{ cubeMapState.loading ? "Loading…" : "Reload Map" }}
          </button>
          <p class="mt-1.5 text-[11px] text-slate-500">
            Showing median {{ cubeMapData.wave_min_used.toFixed(3) }}–{{
              cubeMapData.wave_max_used.toFixed(3)
            }}
            {{ waveUnit }}
          </p>
        </div>

        <!-- Aperture -->
        <div class="rounded-lg border border-white/10 bg-slate-950/30 p-3">
          <p class="mb-1 text-xs font-medium text-slate-200">Circular aperture</p>
          <p class="mb-3 text-[11px] text-slate-500">Click the heatmap to set center</p>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label
                class="mb-1 block text-[11px] uppercase tracking-[0.08em] text-slate-400"
              >
                Center X (px)
              </label>
              <input
                v-model.number="apertureCx"
                type="number"
                step="0.5"
                min="0"
                :max="cubeMapData.shape.nx - 1"
                class="w-full rounded-md border border-white/10 bg-slate-950/60 px-2 py-1 text-xs text-slate-100"
              />
            </div>
            <div>
              <label
                class="mb-1 block text-[11px] uppercase tracking-[0.08em] text-slate-400"
              >
                Center Y (px)
              </label>
              <input
                v-model.number="apertureCy"
                type="number"
                step="0.5"
                min="0"
                :max="cubeMapData.shape.ny - 1"
                class="w-full rounded-md border border-white/10 bg-slate-950/60 px-2 py-1 text-xs text-slate-100"
              />
            </div>
          </div>
          <div class="mt-2">
            <label
              class="mb-1 block text-[11px] uppercase tracking-[0.08em] text-slate-400"
            >
              Radius (px)
            </label>
            <input
              v-model.number="apertureRadius"
              type="number"
              step="0.5"
              min="0.5"
              max="200"
              class="w-full rounded-md border border-white/10 bg-slate-950/60 px-2 py-1 text-xs text-slate-100"
            />
          </div>
        </div>

        <!-- Extract button -->
        <button
          type="button"
          class="rounded-lg border border-cyan-200/20 bg-cyan-400/10 px-4 py-2 text-sm font-medium text-cyan-100 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="cubeExtractionState.loading"
          @click="handleExtract"
        >
          {{ cubeExtractionState.loading ? "Extracting…" : "Extract Spectrum" }}
        </button>

        <p v-if="cubeExtractionState.error" class="text-xs text-rose-200">
          {{ cubeExtractionState.error }}
        </p>

        <p
          v-if="!cubeExtractionState.loading && !cubeExtractionState.error"
          class="text-[11px] text-slate-500"
        >
          Result appears in the spectrum plot below. It can be scored for PAHs via
          the PAH score endpoint.
        </p>
      </div>
    </div>
  </div>
</template>
