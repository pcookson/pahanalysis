<script setup>
import { computed } from "vue";

import { dataRightsBadgeClass } from "../lib/ui";

const props = defineProps({
  activeTab: {
    type: String,
    required: true,
  },
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
  cachedQueryOptions: {
    type: Array,
    required: true,
  },
  selectedCachedQueryKey: {
    type: String,
    default: "",
  },
  cachedSelectionMeta: {
    type: Object,
    required: true,
  },
  selectedObservation: {
    type: Object,
    default: null,
  },
});

defineEmits([
  "set-active-tab",
  "run-search",
  "refetch-search",
  "select-cached-query",
  "select-observation",
]);

const formattedLastFetched = computed(() => {
  const raw = props.cachedSelectionMeta?.lastFetchedAt;
  if (!raw) return null;
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleString();
});

const coverageTooltipText =
  "Nominal instrument coverage; actual product coverage may differ.";
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
      <div class="inline-flex rounded-xl border border-white/10 bg-slate-950/40 p-1">
        <button
          type="button"
          class="rounded-lg px-3 py-1.5 text-sm transition"
          :class="
            activeTab === 'search'
              ? 'bg-cyan-400/15 text-cyan-100'
              : 'text-slate-300 hover:bg-white/5'
          "
          @click="$emit('set-active-tab', 'search')"
        >
          Search
        </button>
        <button
          type="button"
          class="rounded-lg px-3 py-1.5 text-sm transition"
          :class="
            activeTab === 'cached'
              ? 'bg-cyan-400/15 text-cyan-100'
              : 'text-slate-300 hover:bg-white/5'
          "
          @click="$emit('set-active-tab', 'cached')"
        >
          Cached
        </button>
      </div>

      <template v-if="activeTab === 'search'">
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

        <button
          type="button"
          class="w-full rounded-xl border border-cyan-200/20 bg-cyan-400/10 px-4 py-2.5 text-sm font-medium text-cyan-100 transition hover:bg-cyan-400/15 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="searchState.loading"
          @click="$emit('run-search')"
        >
          {{ searchState.loading ? "Searching..." : "Search" }}
        </button>

        <p
          v-if="searchCacheMeta?.hasCache"
          class="text-xs text-slate-500"
        >
          Current query is cached ({{ searchCacheMeta.rowCount }} row<span v-if="searchCacheMeta.rowCount !== 1">s</span>).
        </p>
      </template>

      <template v-else>
        <div>
          <label class="mb-2 block text-sm font-medium text-slate-200">
            Cached Target
          </label>
          <select
            class="w-full rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2.5 text-sm text-white focus:border-cyan-300/60 focus:outline-none"
            :value="selectedCachedQueryKey"
            :disabled="searchState.loading || cachedQueryOptions.length === 0"
            @change="$emit('select-cached-query', $event.target.value)"
          >
            <option value="">
              {{ cachedQueryOptions.length ? "Select cached target..." : "No cached targets" }}
            </option>
            <option
              v-for="option in cachedQueryOptions"
              :key="option.key"
              :value="option.key"
            >
              {{ option.target }} (r={{ option.radiusArcsec ?? "?" }})
            </option>
          </select>
        </div>

        <button
          type="button"
          class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="searchState.loading || !selectedCachedQueryKey"
          @click="$emit('refetch-search')"
        >
          {{ searchState.loading ? "Fetching..." : "Re-fetch" }}
        </button>

        <p class="text-xs text-slate-400">
          Last time data fetched:
          <span v-if="formattedLastFetched" class="text-slate-200">
            {{ formattedLastFetched }}
          </span>
          <span v-else class="text-slate-500">Not fetched yet</span>
        </p>
        <p class="text-xs text-slate-500">
          <template v-if="cachedSelectionMeta?.hasSelection">
            Cached rows: {{ cachedSelectionMeta.rowCount }}
          </template>
          <template v-else>
            Select a cached target to view cached observation results.
          </template>
        </p>
      </template>
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
        v-if="activeTab === 'cached' && !selectedCachedQueryKey"
        class="mt-3 text-sm leading-6 text-slate-400"
      >
        Select a cached target to view cached observation results.
      </p>

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
              <td class="px-3 py-2 align-top">
                <p>{{ row.instrument_name || "—" }}</p>
                <div
                  v-if="row.instrumentCoverageLabel"
                  class="mt-1 flex flex-wrap items-center gap-1.5"
                >
                  <span
                    class="inline-flex rounded-full border border-cyan-200/20 bg-cyan-400/10 px-2 py-0.5 text-xs text-cyan-100"
                  >
                    {{ row.instrumentCoverageLabel }}
                  </span>
                  <span
                    class="inline-flex h-4 w-4 items-center justify-center rounded-full border border-white/15 text-[10px] text-slate-300"
                    :title="coverageTooltipText"
                    :aria-label="coverageTooltipText"
                  >
                    ?
                  </span>
                </div>
              </td>
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
