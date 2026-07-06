"use client";

import { api } from "@/lib/api";
import { useEffect, useState } from "react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { RefreshCw } from "lucide-react";
import { useReducedMotion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Card, CardHeader } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { StatBlock } from "@/components/ui/stat";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatSkeleton, Skeleton } from "@/components/ui/skeleton";
import { Rise } from "@/components/ui/motion";
import { useToast } from "@/components/ui/toast";
import {
  chartSeries,
  axisTick,
  tooltipStyle,
  tooltipItemStyle,
  tooltipLabelStyle,
  useDrawInOnce,
} from "@/components/ui/chart";

// Fixed categorical assignment; anything past the third slice folds to neutral.
const sliceColor = (index: number) =>
  index < chartSeries.length ? chartSeries[index] : "var(--ink-3)";

export default function PolicyMakerDashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const { token } = useAuthStore();
  const toast = useToast();
  const reduced = useReducedMotion();
  const drawIn = useDrawInOnce();

  const fetchAnalytics = async () => {
    try {
      const res = await axios.get(api("/analytics/dashboard"), {
        headers: { Authorization: `Bearer ${token}` },
      });
      setData(res.data);
    } catch (err) {
      console.error("Failed to load analytics", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchAnalytics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleOsintSync = async () => {
    setSyncing(true);
    try {
      await axios.post(api("/admin/osint/sync"), {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast("success", "OSINT feeds synced. The AI now has the latest threat data.");
      await fetchAnalytics();
    } catch (err) {
      toast("danger", "The OSINT feeds couldn't be synced.");
    } finally {
      setSyncing(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="space-y-6 pt-2">
        <PageHeader title="National analytics" sub="Live aggregated intelligence." />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatSkeleton />
          <StatSkeleton />
          <StatSkeleton />
        </div>
        <Skeleton className="h-80 rounded-card" />
      </div>
    );
  }

  const threatCritical = data.stats.threat_level === "CRITICAL";

  return (
    <div className="space-y-6 pt-2">
      <Rise>
        <PageHeader
          title="National analytics"
          sub="Live aggregated intelligence for policy decisions."
          actions={
            <Badge tone={threatCritical ? "danger" : "warning"}>
              National threat: {String(data.stats.threat_level || "—").toLowerCase()}
            </Badge>
          }
        />
      </Rise>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Rise index={1}>
          <StatBlock label="Total incidents" value={data.stats.total_cases} />
        </Rise>
        <Rise index={2}>
          <StatBlock label="Resolved" value={data.stats.resolved_cases} />
        </Rise>
        <Rise index={3}>
          <StatBlock label="High priority" value={data.stats.high_priority} />
        </Rise>
      </div>

      <Rise index={4}>
        <Card className="px-6 py-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="font-display font-semibold text-base text-ink">Public threat feeds</h3>
            <p className="text-sm text-ink-2 mt-0.5 max-w-xl">
              Pull known malicious indicators and scam scripts from external databases like MHA
              and PhishTank into the AI's knowledge.
            </p>
          </div>
          <Button loading={syncing} onClick={handleOsintSync}>
            <RefreshCw className="w-4 h-4" />
            Sync OSINT feeds
          </Button>
        </Card>
      </Rise>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Rise index={5}>
          <Card className="flex flex-col h-80">
            <CardHeader title="Incidents" sub="Reports per day, last 7 days" />
            <div className="flex-1 min-h-0 px-4 pb-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.timeline} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={axisTick} dy={8} />
                  <YAxis axisLine={false} tickLine={false} tick={axisTick} width={40} />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    itemStyle={tooltipItemStyle}
                    labelStyle={tooltipLabelStyle}
                  />
                  <Line
                    type="monotone"
                    dataKey="reports"
                    name="Reports"
                    stroke="var(--chart-1)"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--surface)" }}
                    isAnimationActive={drawIn && !reduced}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Rise>

        <Rise index={6}>
          <Card className="flex flex-col h-80">
            <CardHeader title="Threat mix" sub="Cases by scam type" />
            <div className="flex-1 min-h-0 flex items-center px-4 pb-4 gap-4">
              <div className="flex-1 h-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data.scam_types}
                      cx="50%"
                      cy="50%"
                      innerRadius="58%"
                      outerRadius="85%"
                      paddingAngle={2}
                      dataKey="value"
                      stroke="var(--surface)"
                      strokeWidth={2}
                      isAnimationActive={drawIn && !reduced}
                    >
                      {data.scam_types.map((entry: any, index: number) => (
                        <Cell key={entry.name} fill={sliceColor(index)} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={tooltipStyle}
                      itemStyle={tooltipItemStyle}
                      labelStyle={tooltipLabelStyle}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-2 pr-2 max-w-[45%]">
                {data.scam_types.map((entry: any, index: number) => (
                  <div key={entry.name} className="flex items-center gap-2 text-sm min-w-0">
                    <span
                      className="w-2.5 h-2.5 rounded-[3px] shrink-0"
                      style={{ backgroundColor: sliceColor(index) }}
                    />
                    <span className="text-ink-2 truncate">{entry.name}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </Rise>
      </div>

      <Rise index={7}>
        <Card className="flex flex-col h-80">
          <CardHeader title="Incidents by state" />
          <div className="flex-1 min-h-0 px-4 pb-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.state_distribution} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <XAxis dataKey="state" axisLine={false} tickLine={false} tick={axisTick} dy={8} />
                <YAxis axisLine={false} tickLine={false} tick={axisTick} width={40} />
                <Tooltip
                  contentStyle={tooltipStyle}
                  itemStyle={tooltipItemStyle}
                  labelStyle={tooltipLabelStyle}
                  cursor={{ fill: "var(--surface-2)" }}
                />
                <Bar
                  dataKey="cases"
                  name="Cases"
                  fill="var(--chart-1)"
                  radius={[4, 4, 0, 0]}
                  maxBarSize={40}
                  isAnimationActive={drawIn && !reduced}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </Rise>
    </div>
  );
}
