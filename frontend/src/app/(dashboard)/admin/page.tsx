"use client";

import { api } from "@/lib/api";

import { useState, useEffect } from "react";
import { CheckCircle2, Search, Users, Siren } from "lucide-react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { useRouter } from "next/navigation";
import { Card, CardHeader } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { StatBlock } from "@/components/ui/stat";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FormError } from "@/components/ui/field";
import { DataTable, type Column } from "@/components/ui/data-table";
import { TableSkeleton, StatSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Rise } from "@/components/ui/motion";

interface UserRecord {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_approved: boolean;
  created_at: string;
}

export default function AdminPage() {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSimulating, setIsSimulating] = useState(false);
  const { token } = useAuthStore();
  const router = useRouter();

  const fetchUsers = async () => {
  if (!token) return;

  try {
    setLoading(true);
    setError("");

    const response = await axios.get(
      api("/users")
    );

    setUsers(
      Array.isArray(response.data)
        ? response.data
        : []
    );
  } catch (err: any) {
    console.error("Failed to load users:", err);

    setUsers([]);

    setError(
      err.response?.data?.detail ||
        "The user list couldn't be loaded."
    );
  } finally {
    setLoading(false);
  }
};
useEffect(() => {
  if (token) {
    fetchUsers();
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [token]);

  const handleApprove = async (userId: string) => {
  if (!token) return;

  setApprovingId(userId);
  setError("");

  try {
    await axios.post(
      api(`/users/${userId}/approve`),
      {}
    );

    await fetchUsers();
  } catch (err: any) {
    console.error("Failed to approve user:", err);

    setError(
      err.response?.data?.detail ||
        "The user couldn't be approved."
    );
  } finally {
    setApprovingId(null);
  }
};

  const handleSimulateAttack = async () => {
  if (!token) return;

  setIsSimulating(true);
  setError("");

  try {
    await axios.post(
      api("/cases/simulate-attack"),
      {}
    );

    router.push("/workbench/map");
  } catch (err: any) {
    console.error(
      "Failed to simulate attack:",
      err
    );

    setError(
      err.response?.data?.detail ||
        "The simulation couldn't be started."
    );
  } finally {
    setIsSimulating(false);
  }
};

  const filteredUsers = users.filter(
    (u) =>
      u.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.role.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const pendingCount = users.filter((u) => !u.is_approved).length;
  const approvedCount = users.filter((u) => u.is_approved).length;

  const columns: Column<UserRecord>[] = [
    {
      key: "name",
      header: "Name",
      mobile: "title",
      render: (u) => <span className="font-medium text-ink">{u.full_name || "—"}</span>,
    },
    {
      key: "email",
      header: "Email",
      render: (u) => <span className="text-ink-2">{u.email}</span>,
    },
    {
      key: "role",
      header: "Role",
      render: (u) => <Badge tone="lilac" className="capitalize">{u.role.replace(/_/g, " ")}</Badge>,
    },
    {
      key: "status",
      header: "Status",
      mobile: "trailing",
      render: (u) =>
        u.is_approved ? (
          <Badge tone="success">Approved</Badge>
        ) : (
          <Badge tone="warning">Pending</Badge>
        ),
    },
    {
      key: "registered",
      header: "Registered",
      render: (u) => (
        <span className="text-ink-2 text-xs">
          {u.created_at ? new Date(u.created_at.endsWith("Z") ? u.created_at : u.created_at + "Z").toLocaleDateString("en-IN") : "—"}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (u) =>
        !u.is_approved ? (
          <Button
            size="sm"
            loading={approvingId === u.id}
            onClick={() => handleApprove(u.id)}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            Approve
          </Button>
        ) : null,
    },
  ];

  return (
    <div className="space-y-6 pt-2">
      <Rise>
        <PageHeader
          title="Admin"
          sub="Users, approvals, and platform controls."
          actions={
            <Button variant="danger" loading={isSimulating} onClick={handleSimulateAttack}>
              <Siren className="w-4 h-4" />
              {isSimulating ? "Injecting threats…" : "Simulate attack wave"}
            </Button>
          }
        />
      </Rise>

      <FormError>{error}</FormError>

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
              <StatBlock label="Total users" value={users.length} />
            </Rise>
            <Rise index={2}>
              <StatBlock label="Approved" value={approvedCount} />
            </Rise>
            <Rise index={3}>
              <StatBlock
                label="Awaiting approval"
                value={pendingCount}
                hint={pendingCount > 0 ? "needs your review" : undefined}
              />
            </Rise>
          </>
        )}
      </div>

      <Rise index={4}>
        <Card>
          <CardHeader
            title="Users"
            action={
              <div className="relative hidden sm:block">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-3" />
                <input
                  type="search"
                  placeholder="Search name, email, or role"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-9 pl-10 pr-4 w-64 rounded-pill bg-surface-2 text-sm text-ink placeholder:text-ink-3 border border-transparent focus:border-accent-text focus:outline-none transition-colors"
                />
              </div>
            }
          />
          {loading ? (
            <TableSkeleton rows={6} />
          ) : filteredUsers.length === 0 ? (
            <EmptyState
              icon={Users}
              title={searchQuery ? "No matches" : "No users yet"}
              body={searchQuery ? `Nothing matches "${searchQuery}".` : undefined}
            />
          ) : (
            <DataTable columns={columns} rows={filteredUsers} rowKey={(u) => u.id} />
          )}
        </Card>
      </Rise>
    </div>
  );
}
