import { useEffect, useState, type FormEvent } from "react";
import { BrainCircuitIcon, SearchIcon } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type Fact = { id: string; text: string; tokens: number };
type Forecast = { status: string; forecast: number | null; holdout_mae?: number; baseline_mae?: number; target_day?: string };
type Insights = { forecast: Forecast; topEvidence: Fact[]; note: string };
type Answer = { answer: string; evidence: Fact[]; method: string };

export function UsageIntelligence({ refreshKey, ollamaModels }: { refreshKey: string; ollamaModels: string[] }) {
  const [insights, setInsights] = useState<Insights | null>(null);
  const [question, setQuestion] = useState("");
  const [model, setModel] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    fetch("/api/insights").then(response => response.json()).then(result => { if (active) setInsights(result); }).catch(() => {});
    return () => { active = false; };
  }, [refreshKey]);
  async function ask(event: FormEvent) {
    event.preventDefault();
    if (!question.trim() || busy) return;
    setBusy(true); setError(""); setAnswer(null);
    try {
      const response = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: question.trim(), model: model || null }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not answer");
      setAnswer(result);
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setBusy(false); }
  }
  return <Card className="glass-panel glow-border mt-3 rounded-xl border-0">
    <CardHeader>
      <div className="flex items-center gap-2"><BrainCircuitIcon className="size-4 text-primary" /><CardTitle className="text-base">Usage intelligence</CardTitle></div>
      <CardDescription>Evidence from recorded counters. An optional local model can explain it; estimates never alter totals.</CardDescription>
    </CardHeader>
    <CardContent className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-lg border bg-secondary/15 p-3">
        <p className="text-sm font-semibold">Neural usage forecast</p>
        {insights?.forecast.forecast != null ? <><p className="mt-2 text-2xl font-bold tabular-nums">{insights.forecast.forecast.toLocaleString()} <span className="text-xs font-normal text-muted-foreground">tokens estimated for {insights.forecast.target_day}</span></p><p className="mt-1 text-xs text-muted-foreground">Shown only because its last seven-day holdout error ({insights.forecast.holdout_mae?.toLocaleString()}) beat a previous-week baseline ({insights.forecast.baseline_mae?.toLocaleString()}). Actual usage may differ.</p></> : <p className="mt-2 text-xs text-muted-foreground">No reliable forecast yet{insights ? `: ${insights.forecast.status}` : "."} Recorded totals remain available.</p>}
        <p className="mt-3 text-xs font-semibold">Top recorded evidence</p>
        <ul className="mt-1 space-y-1 text-xs text-muted-foreground">{(insights?.topEvidence || []).slice(0, 4).map(fact => <li key={fact.id}>{fact.text}</li>)}</ul>
      </div>
      <div className="rounded-lg border bg-secondary/15 p-3">
        <p className="text-sm font-semibold">Ask about recorded usage</p>
        <p className="mt-1 text-xs text-muted-foreground">Only aggregate counters are retrieved. Choosing Ollama sends those counters and your question to that local model.</p>
        <form onSubmit={ask} className="mt-3 flex flex-wrap gap-2">
          <input aria-label="Usage question" value={question} onChange={event => setQuestion(event.target.value)} maxLength={300} placeholder="Which model used the most tokens?" className="h-9 min-w-48 flex-1 rounded-md border bg-background px-2 text-sm" />
          <select aria-label="Explanation method" value={model} onChange={event => setModel(event.target.value)} className="h-9 max-w-full rounded-md border bg-background px-2 text-xs"><option value="">Recorded facts</option>{ollamaModels.map(name => <option key={name} value={name}>Local Ollama · {name}</option>)}</select>
          <Button type="submit" size="sm" disabled={busy || !question.trim()}><SearchIcon className="size-3.5" />{busy ? "Explaining…" : "Ask"}</Button>
        </form>
        {error && <p role="alert" className="mt-2 text-xs text-destructive">{error}</p>}
        {answer && <div className="mt-3 rounded-md border bg-background/60 p-3 text-sm"><p>{answer.answer}</p><p className="mt-2 text-[11px] text-muted-foreground">Method: {answer.method}</p><ul className="mt-1 space-y-0.5 text-[11px] text-muted-foreground">{answer.evidence.map(fact => <li key={fact.id}>[{fact.id}] {fact.text}</li>)}</ul></div>}
      </div>
    </CardContent>
  </Card>;
}
