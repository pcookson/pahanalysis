<script setup>
import { computed, onMounted, ref } from "vue";

const backendState = ref("checking");

const statusLabel = computed(() => {
  if (backendState.value === "connected") {
    return "Connected";
  }
  if (backendState.value === "disconnected") {
    return "Disconnected";
  }
  return "Checking";
});

const badgeClass = computed(() => {
  if (backendState.value === "connected") {
    return "border-emerald-300/60 bg-emerald-400/15 text-emerald-100";
  }
  if (backendState.value === "disconnected") {
    return "border-rose-300/60 bg-rose-400/15 text-rose-100";
  }
  return "border-slate-300/40 bg-slate-400/10 text-slate-100";
});

async function checkBackend() {
  try {
    const response = await fetch("http://localhost:8000/health");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    backendState.value = data?.status === "ok" ? "connected" : "disconnected";
  } catch {
    backendState.value = "disconnected";
  }
}

onMounted(() => {
  checkBackend();
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

      <header class="relative mx-auto max-w-6xl px-6 pt-10">
        <h1 class="text-2xl font-semibold tracking-tight sm:text-3xl">
          JWST Spectrum Viewer
        </h1>
      </header>

      <main class="relative mx-auto grid min-h-[calc(100vh-6rem)] place-items-center px-6 py-10">
        <section
          class="w-full max-w-xl rounded-2xl border border-white/10 bg-white/5 p-6 shadow-panel backdrop-blur-xl sm:p-8"
        >
          <div class="flex items-center justify-between gap-4">
            <div>
              <p class="text-sm uppercase tracking-[0.16em] text-slate-300/90">
                Backend Status
              </p>
              <p class="mt-2 text-lg font-medium text-white">
                FastAPI @ :8000
              </p>
            </div>

            <span
              class="inline-flex items-center rounded-full border px-3 py-1 text-sm font-medium"
              :class="badgeClass"
            >
              <span class="mr-2 inline-block h-2 w-2 rounded-full bg-current" />
              {{ statusLabel }}
            </span>
          </div>

          <p class="mt-5 text-sm leading-6 text-slate-300">
            This frontend checks <code class="rounded bg-white/10 px-1 py-0.5">GET /health</code>
            on load to confirm the backend is reachable.
          </p>

          <p
            v-if="backendState === 'disconnected'"
            class="mt-3 text-sm text-rose-200"
          >
            Backend not reachable on :8000
          </p>
        </section>
      </main>
    </div>
  </div>
</template>
