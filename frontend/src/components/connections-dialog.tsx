import { useEffect, useState, type ChangeEvent } from "react";
import { CableIcon, UploadIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

type Connection = { id: string; name: string; path: string; enabled: boolean; detected: boolean; events: number };
type LimitWindow = { used_percent?: number; window_minutes?: number; resets_at?: number };
type CodexLimits = { primary?: LimitWindow; secondary?: LimitWindow; recorded_at?: string };
type SourceId = "claude" | "codex" | "gemini" | "opencode";

function parseCsv(source: string): Record<string, string>[] {
  const lines: string[][] = [];
  let row: string[] = [], field = "", quoted = false;
  for (let i = 0; i < source.length; i++) {
    const ch = source[i];
    if (ch === '"') {
      if (quoted && source[i + 1] === '"') { field += '"'; i++; } else quoted = !quoted;
    } else if (ch === "," && !quoted) { row.push(field); field = ""; }
    else if ((ch === "\n" || ch === "\r") && !quoted) {
      if (ch === "\r" && source[i + 1] === "\n") i++;
      row.push(field); if (row.some(Boolean)) lines.push(row); row = []; field = "";
    } else field += ch;
  }
  row.push(field); if (row.some(Boolean)) lines.push(row);
  const headers = (lines.shift() || []).map(x => x.trim().toLowerCase());
  return lines.map((values, index) => Object.fromEntries(headers.map((key, i) => [key, values[i] || ""]).concat([["id", values[headers.indexOf("id")] || `csv-${index}-${values.join("|")}`]])));
}

export function ConnectionsDialog({ onChanged }: { onChanged: () => void }) {
  const [open, setOpen] = useState(false);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [limits, setLimits] = useState<CodexLimits | null>(null);
  const [customPaths, setCustomPaths] = useState<Partial<Record<SourceId, string[]>>>({});
  const [pathSource, setPathSource] = useState<SourceId>("claude");
  const [newPath, setNewPath] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (open) fetch("/api/overview?days=1").then(r => r.json()).then(d => { setConnections(d.connections || []); setLimits(d.codex_limits || null); setCustomPaths(d.customPaths || {}); }).catch(() => setError("Could not load connections"));
  }, [open]);
  async function toggle(id: string) {
    const enabled = connections.filter(c => c.id !== id && c.enabled).map(c => c.id);
    if (!connections.find(c => c.id === id)?.enabled) enabled.push(id);
    setBusy(true); setError("");
    try {
      const res = await fetch("/api/connections", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled }) });
      if (!res.ok) throw new Error("Could not save connection");
      setConnections(current => current.map(c => c.id === id ? { ...c, enabled: !c.enabled } : c)); onChanged();
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  async function importFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; if (!file) return;
    setBusy(true); setError("");
    try {
      const rows = parseCsv(await file.text());
      if (!rows.length || rows.length > 5000) throw new Error("CSV must contain 1–5,000 data rows");
      const required = ["provider", "model", "timestamp", "input", "output"];
      if (required.some(key => !(key in rows[0]))) throw new Error(`CSV needs ${required.join(", ")} columns`);
      const res = await fetch("/api/import", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(rows) });
      const result = await res.json();
      if (!res.ok) throw new Error(result.error || "Import failed");
      onChanged(); setOpen(false);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); event.target.value = ""; }
  }
  async function savePaths(source: SourceId, paths: string[]) {
    setBusy(true); setError("");
    try {
      const res = await fetch("/api/source-paths", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source, paths }) });
      const result = await res.json();
      if (!res.ok) throw new Error(result.error || "Could not save source folders");
      setCustomPaths(current => ({ ...current, [source]: paths }));
      setNewPath("");
      const overview = await fetch("/api/overview?days=1").then(response => response.json());
      setConnections(overview.connections || []);
      onChanged();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  }
  return <>
    <Button onClick={() => setOpen(true)} variant="outline" size="sm" className="h-8 rounded-lg px-3"><CableIcon className="size-3.5" /><span className="text-xs">Connections</span></Button>
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-h-[85vh] overflow-auto sm:max-w-xl">
        <DialogHeader><DialogTitle>Connections</DialogTitle><DialogDescription>Local session sources and usage imports. Subscription balances require provider supported access.</DialogDescription></DialogHeader>
        <div className="grid gap-2">
          {connections.map(c => <div key={c.id} className="flex items-center justify-between gap-3 rounded-lg border p-3">
            <div className="min-w-0"><div className="text-sm font-semibold">{c.name}</div><div className="truncate text-xs text-muted-foreground" title={c.path}>{c.detected ? `${c.events.toLocaleString()} records` : "Source not found"} · {c.path}</div></div>
            {["claude", "codex", "gemini", "opencode"].includes(c.id) && <Button variant={c.enabled ? "default" : "outline"} size="sm" disabled={busy} onClick={() => toggle(c.id)}>{c.enabled ? "On" : "Off"}</Button>}
          </div>)}
        </div>
        <div className="rounded-lg border p-3">
          <p className="text-sm font-semibold">Additional session folders</p>
          <p className="mt-1 text-xs text-muted-foreground">Modelmeter also checks supported tool home folders and their environment overrides. Add another folder if a tool stores its session logs elsewhere. Project files alone do not contain reliable token counts.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <select aria-label="Source for additional folder" value={pathSource} onChange={event => setPathSource(event.target.value as SourceId)} className="h-8 rounded-md border border-input bg-background px-2 text-xs">
              <option value="claude">Claude Code</option><option value="codex">Codex CLI</option><option value="gemini">Gemini CLI</option><option value="opencode">OpenCode</option>
            </select>
            <input aria-label="Additional session folder" value={newPath} onChange={event => setNewPath(event.target.value)} placeholder="C:\\path\\to\\sessions" className="h-8 min-w-56 flex-1 rounded-md border border-input bg-background px-2 text-xs" />
            <Button size="sm" variant="outline" disabled={busy || !newPath.trim()} onClick={() => savePaths(pathSource, [...(customPaths[pathSource] || []), newPath.trim()])}>Add folder</Button>
          </div>
          {(customPaths[pathSource] || []).map(path => <div key={path} className="mt-2 flex items-center justify-between gap-2 text-xs"><span className="min-w-0 truncate font-mono" title={path}>{path}</span><Button size="sm" variant="ghost" disabled={busy} onClick={() => savePaths(pathSource, (customPaths[pathSource] || []).filter(item => item !== path))}>Remove</Button></div>)}
        </div>
        {limits && <div className="rounded-lg border bg-secondary/20 p-3"><p className="mb-2 text-sm font-semibold">Codex rate limits <span className="font-normal text-muted-foreground">· last recorded {limits.recorded_at ? new Date(limits.recorded_at).toLocaleString() : "time unavailable"}</span></p><div className="grid gap-2 sm:grid-cols-2">{(["primary", "secondary"] as const).map(key => {
          const window = limits[key]; if (!window || typeof window.used_percent !== "number") return null;
          const remaining = Math.max(0, 100 - window.used_percent);
          const reset = window.resets_at ? new Date(window.resets_at * 1000).toLocaleString() : "Unavailable";
          return <div key={key} className="rounded-md border bg-background p-2 text-xs"><div className="font-medium">{window.window_minutes === 300 ? "5-hour" : window.window_minutes === 10080 ? "Weekly" : `${window.window_minutes || "Unknown"}-minute`} window</div><div className="mt-1 font-mono">{window.used_percent.toFixed(0)}% used · {remaining.toFixed(0)}% remaining</div><div className="mt-1 h-1.5 rounded-full bg-secondary"><div className="h-1.5 rounded-full bg-primary" style={{ width: `${window.used_percent}%` }} /></div><div className="mt-1 text-muted-foreground">Resets {reset}</div></div>;
        })}</div></div>}
        <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed p-4 text-sm hover:bg-secondary/50"><UploadIcon className="size-4" />Import usage CSV<input type="file" accept=".csv,text/csv" onChange={importFile} disabled={busy} className="sr-only" /></label>
        <p className="text-xs text-muted-foreground">CSV columns: provider, model, timestamp, input, output. Optional: cache_read, cache_write, session, id. Supported provider names include OpenAI, Anthropic, Google, Antigravity, and xAI. Data stays on this computer.</p>
        {error && <p role="alert" className="text-xs text-destructive">{error}</p>}
      </DialogContent>
    </Dialog>
  </>;
}
