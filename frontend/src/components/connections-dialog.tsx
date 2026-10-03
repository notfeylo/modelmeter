import { useEffect, useState, type ChangeEvent } from "react";
import { CableIcon, RefreshCwIcon, UploadIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

type Connection = { id: string; name: string; path: string; enabled: boolean; detected: boolean; events: number };
type LimitWindow = { used_percent?: number; window_minutes?: number; resets_at?: number };
type CodexLimits = { primary?: LimitWindow; secondary?: LimitWindow; recorded_at?: string };
type ClaudeLimits = { model: string; recorded_at: string; windows: { five_hour?: LimitWindow; seven_day?: LimitWindow } };
type SourceId = "claude" | "codex" | "gemini" | "opencode";
type LocalInventory = { models: { provider: string; model: string; state: string; evidence: string }[]; vaults: { name: string; path: string; status: string }[]; note: string };

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

export function ConnectionsDialog({ onChanged, inventory, onInventoryChanged }: { onChanged: () => void; inventory: LocalInventory; onInventoryChanged: () => void }) {
  const [open, setOpen] = useState(false);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [limits, setLimits] = useState<CodexLimits | null>(null);
  const [claudeLimits, setClaudeLimits] = useState<ClaudeLimits | null>(null);
  const [claudeCommand, setClaudeCommand] = useState("");
  const [customPaths, setCustomPaths] = useState<Partial<Record<SourceId, string[]>>>({});
  const [pathSource, setPathSource] = useState<SourceId>("claude");
  const [newPath, setNewPath] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (open) fetch("/api/overview?days=1").then(r => r.json()).then(d => { setConnections(d.connections || []); setLimits(d.codex_limits || null); setClaudeLimits(d.claude_limits || null); setClaudeCommand(d.claude_bridge_command || ""); setCustomPaths(d.customPaths || {}); }).catch(() => setError("Could not load connections"));
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
      <DialogContent className="connections-scroll max-h-[90vh] w-[min(900px,calc(100vw-24px))] max-w-none overflow-x-hidden overflow-y-auto overscroll-contain sm:max-w-[900px]">
        <DialogHeader><DialogTitle>Connections & local models</DialogTitle><DialogDescription>Recorded usage, discovered model installs, and known source folders. Installed models alone do not provide token counts or subscription limits.</DialogDescription></DialogHeader>
        <div className="grid gap-2 md:grid-cols-2">
          {connections.map(c => <div key={c.id} className="flex items-center justify-between gap-3 rounded-lg border p-3">
            <div className="min-w-0"><div className="text-sm font-semibold">{c.name}</div><div className="truncate text-xs text-muted-foreground" title={c.path}>{c.detected ? `${c.events.toLocaleString()} records` : "Source not found"} · {c.path}</div></div>
            {["claude", "codex", "gemini", "opencode"].includes(c.id) && <Button variant={c.enabled ? "default" : "outline"} size="sm" disabled={busy} onClick={() => toggle(c.id)}>{c.enabled ? "On" : "Off"}</Button>}
          </div>)}
        </div>
        <section className="min-w-0 rounded-lg border p-3">
          <div className="flex items-center justify-between gap-2"><p className="text-sm font-semibold">Installed local models <span className="text-muted-foreground">({inventory.models.length})</span></p><Button size="sm" variant="ghost" onClick={onInventoryChanged}><RefreshCwIcon className="size-3.5" /> Rescan</Button></div>
          <p className="mt-1 text-xs text-muted-foreground">Read from local Ollama, LM Studio, and Hugging Face stores. A downloaded model is listed even when no token log exists.</p>
          {inventory.models.length ? <div className="mt-3 grid max-h-44 gap-2 overflow-y-auto connections-scroll sm:grid-cols-2">{inventory.models.map(item => <div key={`${item.provider}:${item.model}`} className="min-w-0 rounded-md border bg-secondary/20 px-2 py-1.5 text-xs" title={`${item.evidence} · ${item.state}`}><span className="block text-muted-foreground">{item.provider} · {item.state}</span><span className="block truncate font-medium">{item.model}</span></div>)}</div> : <p className="mt-3 text-xs text-muted-foreground">No local models detected in supported stores.</p>}
        </section>
        <section className="min-w-0 rounded-lg border p-3">
          <p className="text-sm font-semibold">Claude Code limits</p>
          <p className="mt-1 text-xs text-muted-foreground">Claude Code can pass its reported 5-hour and weekly windows through a status line command. Configure this only if you do not already use a custom status line.</p>
          {claudeLimits ? <p className="mt-2 text-xs">{claudeLimits.model} · 5h {claudeLimits.windows.five_hour ? `${claudeLimits.windows.five_hour.used_percent}% used` : "unavailable"} · 7d {claudeLimits.windows.seven_day ? `${claudeLimits.windows.seven_day.used_percent}% used` : "unavailable"} · recorded {new Date(claudeLimits.recorded_at).toLocaleString()}</p> : <p className="mt-2 text-xs text-muted-foreground">No recent Claude limit snapshot.</p>}
          {claudeCommand && <div className="mt-2 flex min-w-0 items-center gap-2"><code className="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap rounded border bg-background px-2 py-1 text-xs" title={claudeCommand}>{claudeCommand}</code><Button type="button" size="sm" variant="outline" onClick={() => navigator.clipboard.writeText(claudeCommand).catch(() => setError("Could not copy command"))}>Copy command</Button></div>}
          <p className="mt-1 text-xs text-muted-foreground">Use this as the `statusLine.command` in Claude Code settings. The companion saves limit percentages only. Existing status lines need manual integration.</p>
        </section>
        <section className="min-w-0 rounded-lg border p-3">
          <p className="text-sm font-semibold">Obsidian vaults <span className="text-muted-foreground">({inventory.vaults.length})</span></p>
          <p className="mt-1 text-xs text-muted-foreground">Vault paths are detected from Obsidian’s local registry. Notes are not read for token totals.</p>
          {inventory.vaults.map(vault => <div key={vault.path} className="mt-2 min-w-0 rounded-md border bg-secondary/20 px-2 py-1.5 text-xs"><span className="block font-medium">{vault.name}</span><span className="block truncate text-muted-foreground" title={vault.path}>{vault.status} · {vault.path}</span></div>)}
        </section>
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
