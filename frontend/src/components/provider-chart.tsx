import { useMemo } from "react";
import { Pie, PieChart, Cell } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { ProviderEntry, MetricKey } from "@/types";
import { useLocale } from "@/lib/i18n";
import { formatMetricValue } from "@/lib/format";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface ProviderChartProps {
  items: ProviderEntry[];
  metric: MetricKey;
  loading: boolean;
}

const PALETTE = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--chart-1)",
  "var(--muted)",
];

export function ProviderChart({ items, metric, loading }: ProviderChartProps) {
  const { t } = useLocale();
  const chartData = useMemo(() => {
    const sorted = [...items].sort((a, b) => (b[metric] || 0) - (a[metric] || 0));
    const topItems = sorted.slice(0, 6);
    const remainingValue = sorted
      .slice(6)
      .reduce((total, item) => total + Number(item[metric] || 0), 0);

    const data = topItems.map((item, index) => ({
      name: item.name,
      value: Number(item[metric] || 0),
      fill: PALETTE[index],
    }));

    if (remainingValue > 0) {
      data.push({
        name: t("chart.other"),
        value: remainingValue,
        fill: PALETTE[PALETTE.length - 1],
      });
    }

    return data;
  }, [items, metric, t]);
  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  const chartConfig = useMemo<ChartConfig>(() => {
    const cfg: ChartConfig = {};
    chartData.forEach((item) => {
      cfg[item.name] = { label: item.name, color: item.fill };
    });
    return cfg;
  }, [chartData]);

  if (!loading && metric === "cache_hit_rate") {
    const ranked = [...items].sort((a, b) => (b.cache_hit_rate || 0) - (a.cache_hit_rate || 0));
    return <Card className="glass-panel glow-border overflow-hidden rounded-xl border-0 animate-fade-in">
      <CardHeader className="pb-2"><p className="mb-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-chart-2">Comparison</p><CardTitle className="text-base font-semibold">Cache hit rate by provider</CardTitle><CardDescription className="text-xs">Cached input divided by all recorded input</CardDescription></CardHeader>
      <CardContent className="space-y-3 py-3">
        {ranked.length ? ranked.map(item => <div key={item.name} className="space-y-1.5"><div className="flex justify-between gap-2 text-xs"><span className="truncate">{item.name}</span><strong className="tabular-nums">{item.cache_hit_rate.toFixed(1)}%</strong></div><div className="h-2 overflow-hidden rounded-full bg-secondary"><div className="h-full rounded-full bg-chart-2" style={{ width: `${Math.min(100, item.cache_hit_rate)}%` }} /></div></div>) : <p className="py-10 text-center text-xs text-muted-foreground">{t("chart.noProviderData")}</p>}
      </CardContent>
    </Card>;
  }

  if (loading) {
    return (
      <Card className="glass-panel glow-border overflow-hidden rounded-xl border-0 animate-fade-in">
        <CardHeader className="pb-2">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-3 w-36" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[280px] w-full rounded-lg" />
        </CardContent>
      </Card>
    );
  }

  if (!chartData.length || chartData.every((d) => d.value === 0)) {
    return (
      <Card className="glass-panel glow-border hover:border-primary/15 transition overflow-hidden rounded-xl border-0 animate-fade-in">
        <CardHeader>
          <CardDescription className="pt-36 text-center">{t("chart.noProviderData")}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="glass-panel glow-border hover:border-primary/15 transition overflow-hidden rounded-xl border-0 animate-fade-in stagger-6">
      <CardHeader className="pb-2">
        <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-chart-2">
          Distribution
        </p>
        <CardTitle className="text-base font-semibold">{t("chart.providerTitle")}</CardTitle>
        <CardDescription className="text-xs">{t("chart.providerDesc")}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="relative">
        <div className="pointer-events-none absolute inset-x-0 top-[93px] z-10 text-center">
          <div className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">{t(`metric.${metric}`)}</div>
          <div className="text-lg font-bold tabular-nums text-foreground">{formatMetricValue(metric, total)}</div>
        </div>
        <ChartContainer config={chartConfig} className="h-[250px] w-full">
          <PieChart>
            <ChartTooltip
              content={
                <ChartTooltipContent
                  nameKey="name"
                  formatter={(value) => formatMetricValue(metric, value as number)}
                />
              }
            />
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              innerRadius="57%"
              outerRadius="76%"
              strokeWidth={3}
              stroke="var(--background)"
              animationBegin={200}
              animationDuration={600}
              label={false}
            >
              {chartData.map((entry, index) => (
                <Cell key={`${entry.name}-${index}`} fill={entry.fill} />
              ))}
            </Pie>
          </PieChart>
        </ChartContainer>
        </div>
        <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-2">
          {chartData.map(item => <div key={item.name} className="flex min-w-0 items-center gap-2 text-xs"><span className="size-2.5 shrink-0 rounded-full" style={{ background: item.fill }} /><span className="min-w-0 flex-1 truncate text-muted-foreground" title={item.name}>{item.name}</span><span className="tabular-nums font-medium">{total ? Math.round(item.value / total * 100) : 0}%</span></div>)}
        </div>
      </CardContent>
    </Card>
  );
}
