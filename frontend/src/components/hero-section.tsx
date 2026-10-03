import { useEffect, useState } from "react";
import type { UsagePayload, MetricKey } from "@/types";
import {
  formatDateLabel,
  formatMetricValue,
  getRangeLabel,
} from "@/lib/format";
import { CalendarRangeIcon, HashIcon, ActivityIcon } from "lucide-react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n";

interface HeroSectionProps {
  payload: UsagePayload;
  metric: MetricKey;
}
type LimitStatus = { provider: string; model: string; recorded_at?: string; used_percent: number | null; resets_at: number | null; status: string };

export function HeroSection({ payload, metric }: HeroSectionProps) {
  const { locale, t } = useLocale();
  const [limits, setLimits] = useState<LimitStatus[]>([]);
  useEffect(() => {
    fetch("/api/limits").then(r => r.json()).then(d => setLimits(d.providers || [])).catch(() => {});
  }, [payload.meta.generatedAt]);
  const { meta } = payload;
  const metricLabel = t(`metric.${metric}`);

  const days = payload.days;
  const startDate = days[0]?.date.slice(0, 10) || meta.firstDay || "—";
  const endDate = days.at(-1)?.date.slice(0, 10) || meta.lastDay || "—";
  const totalValue = payload.summary[metric] || 0;

  return (
    <div className="glass-panel glow-border relative overflow-hidden rounded-2xl p-3 md:p-4 animate-fade-in">
      <div className="pointer-events-none absolute -right-20 -top-20 size-60 rounded-full bg-primary/6 blur-[80px] animate-glow-pulse dark:block hidden" />
      <div className="pointer-events-none absolute -bottom-12 -left-12 size-44 rounded-full bg-chart-2/4 blur-[80px] dark:block hidden" />

      <div className="relative grid gap-3 md:grid-cols-[1.2fr_0.8fr]">
        <div className="animate-slide-up">
          <h1 className="text-xl font-bold leading-tight tracking-tight text-foreground md:text-4xl">
            <span className="accent-gradient-text">Modelmeter</span>
          </h1>
          <p className="mt-1.5 max-w-xl text-sm text-muted-foreground">
            {t("hero.description")}
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5" aria-label="Recorded provider limits">
            {limits.filter(item => meta.provider === "all" || item.provider === meta.provider).map(item => {
              const current = typeof item.used_percent === "number" && (!item.resets_at || item.resets_at * 1000 > new Date(meta.generatedAt).getTime());
              return <div key={item.provider} className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-primary/15 bg-primary/5 px-3 py-1 text-[11px] text-foreground" title={`${item.status}${item.recorded_at ? ` · last recorded ${new Date(item.recorded_at).toLocaleString()}` : ""}`}>
                <span className={`size-1.5 shrink-0 rounded-full ${current ? "bg-primary" : "bg-muted-foreground"}`} />
                <span className="truncate">{item.provider} · {item.model}</span>
                <strong className="shrink-0">{current ? `${Math.max(0, 100 - item.used_percent!).toFixed(0)}% left` : "limit unavailable"}</strong>
                {current && item.resets_at && <span className="shrink-0 text-muted-foreground">· resets {new Date(item.resets_at * 1000).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}</span>}
              </div>;
            })}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 animate-slide-up stagger-2">
          <MetaCard
            icon={<CalendarRangeIcon className="size-3 text-chart-2" />}
            label={t("hero.statRange")}
          >
            {formatDateLabel(startDate, "long", locale)} — {formatDateLabel(endDate, "long", locale)}
          </MetaCard>
          <MetaCard
            icon={<ActivityIcon className="size-3 text-primary" />}
            label={t("hero.currentRange")}
          >
            {getRangeLabel(meta.range, t)}
          </MetaCard>
          <MetaCard
            icon={<HashIcon className="size-3 text-chart-3" />}
            label={t("hero.assistantMessages")}
          >
            {new Intl.NumberFormat(locale === "en" ? "en-US" : "zh-CN").format(meta.assistantMessageCount)}
          </MetaCard>
          <MetaCard
            icon={<ActivityIcon className="size-3 text-chart-4" />}
            label={t("hero.currentRangeMetric", { metric: metricLabel })}
          >
            {formatMetricValue(metric, totalValue)}
          </MetaCard>
        </div>
      </div>

    </div>
  );
}

function MetaCard({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <Card size="sm" className="border-border bg-secondary/20 p-0 py-0 transition-colors hover:border-primary/30 hover:shadow-sm">
      <CardHeader className="p-2 pb-0">
        <div className="flex items-center gap-1.5">
          {icon}
          <span className="text-[11px] text-muted-foreground">{label}</span>
        </div>
      </CardHeader>
      <CardContent className="p-2 pt-0">
        <strong className="block truncate text-[13px] font-semibold leading-snug font-mono">
          {children}
        </strong>
      </CardContent>
    </Card>
  );
}
