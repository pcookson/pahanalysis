<script setup>
import { computed } from "vue";

import { badgeViewModel } from "../lib/ui";

const props = defineProps({
  backendStatus: {
    type: Object,
    required: true,
  },
  mastStatus: {
    type: Object,
    required: true,
  },
});

defineEmits(["refresh-status"]);

const healthBadge = computed(() => badgeViewModel("health", props.backendStatus));
const mastBadge = computed(() => badgeViewModel("mast", props.mastStatus));
</script>

<template>
  <header class="relative mx-auto w-full max-w-[1800px] px-6 pt-8 sm:pt-10">
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
            @click="$emit('refresh-status')"
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
</template>
