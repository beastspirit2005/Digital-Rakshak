"use client";

import { api } from "@/lib/api";
import { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import Link from "next/link";
import { useReducedMotion } from "framer-motion";
import { Card, CardHeader } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { StatBlock, CountUp } from "@/components/ui/stat";
import { StatusBadge, PriorityBadge } from "@/components/ui/badge";
import { DataTable, type Column } from "@/components/ui/data-table";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Rise } from "@/components/ui/motion";
import {
  chartSeries,
  axisTick,
  tooltipStyle,
  tooltipItemStyle,
  tooltipLabelStyle,
  ChartLegend,
  useDrawInOnce,
} from "@/components/ui/chart";

// Hardcoded definitions removed. Data will be fetched from API.
const chartColors = [
  chartSeries[0],
  chartSeries[1],
  chartSeries[2],
  "var(--ink-3)",
  "var(--chart-3)",
  "var(--chart-4)"
];

interface CaseRow {
  id: string;
  case_number: string;
  scam_type_code?: string;
  city?: string;
  state?: string;
  priority: string;
  status: string;
}

const caseColumns: Column<CaseRow>[] = [
  {
    key: "case_number",
    header: "Case",
    mobile: "title",
    render: (c) => (
      <Link href="/workbench/reports" className="font-medium text-ink hover:text-accent-text tabular">
        {c.case_number}
      </Link>
    ),
  },
  {
    key: "type",
    header: "Type",
    render: (c) => <span className="capitalize">{(c.scam_type_code || "Unknown").replace(/_/g, " ")}</span>,
  },
  {
    key: "location",
    header: "Location",
    render: (c) => (
      <span className="text-ink-2">
        {c.city ? `${c.city}${c.state ? `, ${c.state}` : ""}` : "Unknown"}
      </span>
    ),
  },
  {
    key: "priority",
    header: "Priority",
    render: (c) => <PriorityBadge priority={c.priority} />,
  },
  {
    key: "status",
    header: "Status",
    align: "right",
    mobile: "trailing",
    render: (c) => <StatusBadge status={c.status} />,
  },
];

export default function WorkbenchDashboard() {
  const [recentCases, setRecentCases] = useState<CaseRow[]>([]);
  const [statsData, setStatsData] = useState<any>({ total_cases: 0, resolved_cases: 0, high_priority: 0, under_review: 0 });
  const [trendData, setTrendData] = useState<any[]>([]);
  const [categoryData, setCategoryData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { token } = useAuthStore();
  const reduced = useReducedMotion();
  const drawIn = useDrawInOnce();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [casesRes, analyticsRes] = await Promise.all([
          axios.get(api("/cases/?limit=10"), { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(api("/analytics/dashboard"), { headers: { Authorization: `Bearer ${token}` } })
        ]);
        
        setRecentCases(casesRes.data.cases);
        
        const analytics = analyticsRes.data;
        setStatsData({
          ...analytics.stats,
          under_review: analytics.stats.total_cases - analytics.stats.resolved_cases
        });
        
        // Map timeline. We just map 'reports' as the total volume for the trendline
        setTrendData(analytics.timeline || []);
        
        // Map scam types
        const types = analytics.scam_types || [];
        const totalCases = analytics.stats.total_cases || 1; // avoid division by zero
        setCategoryData(types.map((t: any, idx: number) => ({
          name: (t.name || "Unknown").replace(/_/g, " "),
          value: Math.round((t.value / totalCases) * 100),
          count: t.value,
          color: chartColors[idx % chartColors.length]
        })));
        
      } catch (err) {
        console.error("Failed to fetch dashboard data", err);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchData();
  }, [token]);

  return (
    <div className="space-y-6 pt-2">
      <Rise>
        <PageHeader
          title="Workbench"
          sub="Case activity across your jurisdiction, past seven days."
        />
      </Rise>

      {/* hero + secondary stats */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <Rise index={1} className="lg:col-span-1">
            <Card className="px-6 py-5 h-full flex flex-col justify-between bg-accent text-accent-ink">
              <p className="text-sm opacity-80">Total cases</p>
              <div>
                <p className="font-display font-semibold text-2xl tracking-tight tabular">
                  <CountUp value={statsData.total_cases} />
                </p>
                <p className="text-xs opacity-70 mt-1">Real-time stats</p>
              </div>
            </Card>
          </Rise>
          
          <Rise index={2}>
            <StatBlock label="High priority" value={statsData.high_priority} delta="-" deltaPositive={false} hint="Requires immediate action" />
          </Rise>
          <Rise index={3}>
            <StatBlock label="Under review" value={statsData.under_review} delta="-" deltaPositive={false} hint="Pending investigation" />
          </Rise>
          <Rise index={4}>
            <StatBlock label="Resolved" value={statsData.resolved_cases} delta="-" deltaPositive={true} hint="Successfully closed cases" />
          </Rise>
      </div>

      {/* charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Rise index={5} className="lg:col-span-2">
          <Card className="h-full flex flex-col">
            <CardHeader title="Threat trend" sub="Reports per day by vector" />
            <div className="flex-1 min-h-64 px-4 pb-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="fillUpi" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="fillDigital" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="date"
                    axisLine={false}
                    tickLine={false}
                    tick={axisTick}
                    dy={8}
                  />
                  <YAxis axisLine={false} tickLine={false} tick={axisTick} width={40} />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    itemStyle={tooltipItemStyle}
                    labelStyle={tooltipLabelStyle}
                  />
                  <Area
                    type="monotone"
                    dataKey="reports"
                    name="Daily Reports"
                    stroke="var(--chart-1)"
                    strokeWidth={2}
                    fill="url(#fillUpi)"
                    isAnimationActive={drawIn && !reduced}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="px-6 pb-5">
              <ChartLegend
                items={[
                  { label: "Daily Reports", color: "var(--chart-1)" }
                ]}
              />
            </div>
          </Card>
        </Rise>

        <Rise index={6}>
          <Card className="h-full flex flex-col">
            <CardHeader title="Scam categories" sub="Share of all cases" />
            <div className="flex-1 relative min-h-52 flex items-center justify-center px-4">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    innerRadius="62%"
                    outerRadius="85%"
                    paddingAngle={2}
                    dataKey="value"
                    stroke="var(--surface)"
                    strokeWidth={2}
                    isAnimationActive={drawIn && !reduced}
                  >
                    {categoryData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={tooltipStyle}
                    itemStyle={tooltipItemStyle}
                    labelStyle={tooltipLabelStyle}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="font-display font-semibold text-xl text-ink tabular">{statsData.total_cases}</span>
                <span className="text-xs text-ink-3 mt-0.5">total</span>
              </div>
            </div>
            <div className="px-6 pb-5 pt-2 grid grid-cols-2 gap-x-4 gap-y-2">
              {categoryData.map((cat) => (
                <div key={cat.name} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2 text-ink-2">
                    <span className="w-2.5 h-2.5 rounded-[3px]" style={{ backgroundColor: cat.color }} />
                    {cat.name}
                  </span>
                  <span className="text-ink font-medium tabular">{cat.value}%</span>
                </div>
              ))}
            </div>
          </Card>
        </Rise>
      </div>

      {/* recent cases */}
      <Rise index={7}>
        <Card>
          <CardHeader
            title="Recent cases"
            action={
              <Link
                href="/workbench/reports"
                className="text-sm text-ink-2 hover:text-ink underline underline-offset-4"
              >
                View all
              </Link>
            }
          />
          {loading ? (
            <TableSkeleton rows={5} />
          ) : recentCases.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No recent cases"
              body="New reports from your jurisdiction will show up here."
            />
          ) : (
            <DataTable columns={caseColumns} rows={recentCases} rowKey={(c) => c.id} />
          )}
        </Card>
      </Rise>
    </div>
  );
}
