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

const stats = [
  { name: "High priority", value: 156, delta: "-8.3%", positive: true },
  { name: "Under review", value: 342, delta: "+4.1%", positive: false },
  { name: "Resolved", value: 750, delta: "+15.2%", positive: true },
];

const trendData = [
  { name: "22 May", upi: 120, digital: 80 },
  { name: "23 May", upi: 132, digital: 90 },
  { name: "24 May", upi: 101, digital: 70 },
  { name: "25 May", upi: 145, digital: 110 },
  { name: "26 May", upi: 190, digital: 130 },
  { name: "27 May", upi: 150, digital: 100 },
  { name: "28 May", upi: 165, digital: 115 },
];

// Fixed categorical order; long tail folds into "Other" (neutral by convention).
const categoryData = [
  { name: "UPI fraud", value: 35, color: chartSeries[0] },
  { name: "Digital arrest", value: 22, color: chartSeries[1] },
  { name: "Phishing", value: 18, color: chartSeries[2] },
  { name: "Other", value: 25, color: "var(--ink-3)" },
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
  const [loading, setLoading] = useState(true);
  const { token } = useAuthStore();
  const reduced = useReducedMotion();
  const drawIn = useDrawInOnce();

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const res = await axios.get(api("/cases/?limit=10"), {
          headers: { Authorization: `Bearer ${token}` },
        });
        setRecentCases(res.data.cases);
      } catch (err) {
        console.error("Failed to fetch recent cases", err);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchCases();
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
                <CountUp value={1248} />
              </p>
              <p className="text-xs opacity-70 mt-1">+12.5% vs last week</p>
            </div>
          </Card>
        </Rise>
        {stats.map((stat, i) => (
          <Rise key={stat.name} index={i + 2}>
            <StatBlock
              label={stat.name}
              value={stat.value}
              delta={stat.delta}
              deltaPositive={stat.positive}
              hint="vs last 7 days"
            />
          </Rise>
        ))}
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
                    dataKey="name"
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
                    dataKey="upi"
                    name="UPI fraud"
                    stroke="var(--chart-1)"
                    strokeWidth={2}
                    fill="url(#fillUpi)"
                    isAnimationActive={drawIn && !reduced}
                  />
                  <Area
                    type="monotone"
                    dataKey="digital"
                    name="Digital arrest"
                    stroke="var(--chart-2)"
                    strokeWidth={2}
                    fill="url(#fillDigital)"
                    isAnimationActive={drawIn && !reduced}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="px-6 pb-5">
              <ChartLegend
                items={[
                  { label: "UPI fraud", color: "var(--chart-1)" },
                  { label: "Digital arrest", color: "var(--chart-2)" },
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
                <span className="font-display font-semibold text-xl text-ink tabular">1,248</span>
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
