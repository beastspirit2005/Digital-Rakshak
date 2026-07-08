"use client";

import { api } from "@/lib/api";
import { useEffect, useState } from "react";
import Link from "next/link";
import axios from "axios";
import { FileText, Plus, AlertTriangle } from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { StatBlock } from "@/components/ui/stat";
import { StatusBadge, PriorityBadge } from "@/components/ui/badge";
import { DataTable, type Column } from "@/components/ui/data-table";
import { TableSkeleton, StatSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Rise } from "@/components/ui/motion";

interface Case {
  id: string | number;
  case_number: string;
  created_at: string;
  scam_type: string;
  scam_type_code?: string;
  priority: string;
  status: string;
}

const normalizeStatus = (status: string) => (status || "").toLowerCase().replace(/_/g, " ");

const columns: Column<Case>[] = [
  {
    key: "case_number",
    header: "Case",
    mobile: "title",
    render: (c) => <span className="font-medium text-ink tabular">{c.case_number}</span>,
  },
  {
    key: "created_at",
    header: "Filed",
    render: (c) =>
      new Date(c.created_at).toLocaleDateString("en-IN", {
        year: "numeric",
        month: "short",
        day: "numeric",
      }),
  },
  {
    key: "scam_type",
    header: "Type",
    render: (c) => (
      <span className="capitalize">
        {(c.scam_type_code || c.scam_type || "Unknown").replace(/_/g, " ")}
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

export default function CitizenDashboard() {
  const { token, user } = useAuthStore();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCases = async () => {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        setLoading(true);
        const response = await axios.get(api("/cases/my"), {
          headers: { Authorization: `Bearer ${token}` },
        });
        setCases(response.data.cases || []);
      } catch (err) {
        console.error("Failed to fetch cases:", err);
        setError("We couldn't load your reports. Try again in a moment.");
      } finally {
        setLoading(false);
      }
    };
    fetchCases();
  }, [token]);

  const totalReports = cases.length;
  const underReview = cases.filter((c) =>
    ["under review", "pending", "submitted", "analyzing"].includes(normalizeStatus(c.status))
  ).length;
  const resolved = cases.filter((c) =>
    ["resolved", "closed", "completed"].includes(normalizeStatus(c.status))
  ).length;

  const firstName = (user?.full_name || "").split(" ")[0];

  return (
    <div className="space-y-6 pt-2">
      <Rise>
        <PageHeader
          title={firstName ? `Hello, ${firstName}` : "Your reports"}
          sub="Track what you've filed and where each case stands."
          actions={
            <Link href="/report">
              <Button variant="primary" size="lg">
                <Plus className="w-4 h-4" />
                Report a scam
              </Button>
            </Link>
          }
        />
      </Rise>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {loading ? (
          <>
            <StatSkeleton />
            <StatSkeleton />
            <StatSkeleton />
          </>
        ) : (
          <>
            <Rise index={1}>
              <StatBlock label="Reports filed" value={totalReports} />
            </Rise>
            <Rise index={2}>
              <StatBlock label="Being reviewed" value={underReview} />
            </Rise>
            <Rise index={3}>
              <StatBlock label="Resolved" value={resolved} />
            </Rise>
          </>
        )}
      </div>

      <Rise index={4}>
        <Card>
          <CardHeader title="My reports" sub={!loading && cases.length > 0 ? `${cases.length} total` : undefined} />
          {loading ? (
            <TableSkeleton rows={4} />
          ) : error ? (
            <EmptyState
              icon={AlertTriangle}
              title="Something went wrong"
              body={error}
            />
          ) : cases.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No reports yet"
              body="If you've been targeted by a scam or spotted something suspicious, filing a report takes about two minutes."
              action={
                <Link href="/report">
                  <Button variant="secondary">File your first report</Button>
                </Link>
              }
            />
          ) : (
            <DataTable columns={columns} rows={cases} rowKey={(c) => c.id} />
          )}
        </Card>
      </Rise>
    </div>
  );
}
