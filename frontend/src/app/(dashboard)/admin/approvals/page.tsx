"use client";

import { api } from "@/lib/api";
import React, { useEffect, useState } from "react";
import { CheckCircle2 } from "lucide-react";

import { useAuthStore } from "@/lib/auth-store";
import { Card, CardHeader } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { FormError } from "@/components/ui/field";
import { DataTable, type Column } from "@/components/ui/data-table";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";

interface PendingUser {
  id: string;
  email: string;
  full_name: string;
  created_at?: string;
}

export default function AdminApprovalsPage() {
  const [users, setUsers] = useState<PendingUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const { token } = useAuthStore();
  const toast = useToast();

  useEffect(() => {
    if (token) {
      fetchPendingUsers();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const fetchPendingUsers = async () => {
 

  try {
    setLoading(true);

    const response = await fetch(api("/users/pending"), {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      throw new Error("Pending registrations couldn't be loaded.");
    }

    const data = await response.json();
    setUsers(data);
  } catch (err: any) {
    setError(err.message || "Pending registrations couldn't be loaded.");
  } finally {
    setLoading(false);
  }
};

  const handleApprove = async (userId: string) => {
    try {
      setApprovingId(userId);
     
      const response = await fetch(api(`/users/${userId}/approve`), {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error("The user couldn't be approved.");
      }

      setUsers((prev) => prev.filter((u) => u.id !== userId));
      toast("success", "User approved.");
    } catch (err: any) {
      toast("danger", err.message || "The user couldn't be approved.");
    } finally {
      setApprovingId(null);
    }
  };

  const columns: Column<PendingUser>[] = [
    {
      key: "name",
      header: "Name",
      mobile: "title",
      render: (u) => <span className="font-medium text-ink">{u.full_name}</span>,
    },
    {
      key: "email",
      header: "Email",
      render: (u) => <span className="text-ink-2">{u.email}</span>,
    },
    {
      key: "registered",
      header: "Registered",
      render: (u) => (
        <span className="text-ink-2">
          {u.created_at ? new Date(u.created_at).toLocaleDateString("en-IN") : "—"}
        </span>
      ),
    },
    {
      key: "action",
      header: "",
      align: "right",
      mobile: "trailing",
      render: (u) => (
        <Button
          variant="primary"
          size="sm"
          loading={approvingId === u.id}
          onClick={() => handleApprove(u.id)}
        >
          <CheckCircle2 className="w-3.5 h-3.5" />
          Approve
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6 pt-2">
      <PageHeader
        title="Pending approvals"
        sub="New officer, banker, and admin registrations waiting for review."
      />

      <FormError>{error}</FormError>

      <Card>
        <CardHeader
          title="Registrations"
          sub={loading ? undefined : `${users.length} waiting`}
        />
        {loading ? (
          <TableSkeleton rows={4} />
        ) : users.length === 0 ? (
          <EmptyState
            icon={CheckCircle2}
            title="All caught up"
            body="There are no registrations waiting for approval."
          />
        ) : (
          <DataTable columns={columns} rows={users} rowKey={(u) => u.id} />
        )}
      </Card>
    </div>
  );
}
