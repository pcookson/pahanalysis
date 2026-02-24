export function badgeViewModel(kind, status) {
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

export function formatBytes(bytes) {
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

export function dataRightsBadgeClass(value) {
  const rights = String(value || "").toUpperCase();
  if (rights === "PUBLIC") {
    return "border-emerald-300/40 bg-emerald-300/10 text-emerald-100";
  }
  if (!rights) {
    return "border-white/10 bg-white/5 text-slate-300";
  }
  return "border-amber-300/40 bg-amber-300/10 text-amber-100";
}

