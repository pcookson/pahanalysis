<script setup>
import { computed } from "vue";

import { dataRightsBadgeClass } from "../lib/ui";

const props = defineProps({
  searchForm: {
    type: Object,
    required: true,
  },
  searchState: {
    type: Object,
    required: true,
  },
  searchResults: {
    type: Array,
    required: true,
  },
  searchCacheMeta: {
    type: Object,
    required: true,
  },
  selectedObservation: {
    type: Object,
    default: null,
  },
});

defineEmits(["run-search", "refetch-search", "select-observation"]);

const formattedLastFetched = computed(() => {
  const raw = props.searchCacheMeta?.lastFetchedAt;
  if (!raw) return null;
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleString();
});
</script>

<template>
  <div
    class="h-full rounded-2xl border border-white/10 bg-white/5 p-5 shadow-panel backdrop-blur-xl sm:p-6"
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
          v-model="searchForm.target"
          type="text"
          placeholder="e.g. NGC 7027"
          class="w-full rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-cyan-300/60 focus:outline-none"
          :disabled="searchState.loading"
        />
      </div>

      <div>
        <label class="mb-2 block text-sm font-medium text-slate-200">
          Radius (arcsec)
        </label>
        <input
          v-model.number="searchForm.radiusArcsec"
          type="number"
          placeholder="30"
          class="w-full rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-cyan-300/60 focus:outline-none"
          :disabled="searchState.loading"
          min="0.1"
          max="3600"
          step="0.1"
        />
      </div>

      <div class="grid gap-2 sm:grid-cols-2">
        <button
          type="button"
          class="rounded-xl border border-cyan-200/20 bg-cyan-400/10 px-4 py-2.5 text-sm font-medium text-cyan-100 transition hover:bg-cyan-400/15 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="searchState.loading"
          @click="$emit('run-search')"
        >
          {{ searchState.loading ? "Searching..." : "Search" }}
        </button>
        <button
          type="button"
          class="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="searchState.loading"
          @click="$emit('refetch-search')"
        >
          Re-fetch
        </button>
      </div>

      <p class="text-xs text-slate-400">
        Last time data fetched:
        <span v-if="formattedLastFetched" class="text-slate-200">
          {{ formattedLastFetched }}
        </span>
        <span v-else class="text-slate-500">Not fetched yet</span>
      </p>
      <p
        v-if="searchCacheMeta?.hasCache"
        class="text-xs text-slate-500"
      >
        Cached for current query ({{ searchCacheMeta.rowCount }} row<span v-if="searchCacheMeta.rowCount !== 1">s</span>)
      </p>
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
              @click="$emit('select-observation', row)"
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
</template>
