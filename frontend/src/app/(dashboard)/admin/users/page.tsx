"use client";

import { api } from "@/lib/api";
import React, { useEffect, useState } from "react";
import { Users, Plus, Edit2, Trash2 } from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import axios from "axios";
import { cn } from "@/lib/utils";
import { Card, CardHeader } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Label, Select, FormError, FormNotice } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { DataTable, type Column } from "@/components/ui/data-table";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

const ROLE_OPTIONS = [
  { value: "citizen", label: "Citizen" },
  { value: "police", label: "Police officer" },
  { value: "banker", label: "Banker" },
  { value: "cyber_cell", label: "Cyber cell" },
  { value: "admin", label: "Administrator" },
];

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { token, user: currentUser } = useAuthStore();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    role: "citizen",
    is_active: true,
  });
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState("");

  const fetchUsers = async () => {
    if (!token) return;
    try {
      const response = await fetch(api("/users/"), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error("The user list couldn't be loaded.");
      }
      const data = await response.json();
      setUsers(data);
    } catch (err: any) {
      setError(err.message || "The user list couldn't be loaded.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError("");
    try {
      await axios.post(api("/users/"), formData, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setIsCreateModalOpen(false);
      fetchUsers();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || "The user couldn't be created.");
    } finally {
      setFormLoading(false);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    setFormLoading(true);
    setFormError("");
    try {
      await axios.put(
        api(`/users/${selectedUser.id}`),
        {
          full_name: formData.full_name,
          email: formData.email,
          role: formData.role,
          is_active: formData.is_active,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setIsEditModalOpen(false);
      fetchUsers();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || "The changes couldn't be saved.");
    } finally {
      setFormLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedUser) return;
    setFormLoading(true);
    setFormError("");
    try {
      await axios.delete(api(`/users/${selectedUser.id}`), {
        headers: { Authorization: `Bearer ${token}` },
      });
      setIsDeleteModalOpen(false);
      fetchUsers();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || "The user couldn't be deleted.");
    } finally {
      setFormLoading(false);
    }
  };

  const openEditModal = (u: User) => {
    setSelectedUser(u);
    setFormData({
      full_name: u.full_name,
      email: u.email,
      role: u.role,
      is_active: u.is_active,
    });
    setFormError("");
    setIsEditModalOpen(true);
  };

  const openDeleteModal = (u: User) => {
    setSelectedUser(u);
    setFormError("");
    setIsDeleteModalOpen(true);
  };

  const columns: Column<User>[] = [
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
        u.is_active ? <Badge tone="success">Active</Badge> : <Badge tone="danger">Disabled</Badge>,
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (u) => (
        <div className="flex justify-end gap-1.5">
          <Button variant="ghost" size="sm" onClick={() => openEditModal(u)} aria-label={`Edit ${u.full_name}`}>
            <Edit2 className="w-3.5 h-3.5" />
            Edit
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => openDeleteModal(u)}
            disabled={u.id === currentUser?.id}
            title={u.id === currentUser?.id ? "You can't delete your own account" : undefined}
            className="text-danger hover:bg-danger-tint"
            aria-label={`Delete ${u.full_name}`}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
      ),
    },
  ];

  const userFormFields = (
    <>
      <div>
        <Label htmlFor="userFullName">Full name</Label>
        <Input
          id="userFullName"
          required
          type="text"
          value={formData.full_name}
          onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
        />
      </div>
      <div>
        <Label htmlFor="userEmail">Email</Label>
        <Input
          id="userEmail"
          required
          type="email"
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
        />
      </div>
      <div>
        <Label htmlFor="userRole">Role</Label>
        <Select
          id="userRole"
          value={formData.role}
          onChange={(e) => setFormData({ ...formData, role: e.target.value })}
        >
          {ROLE_OPTIONS.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </Select>
      </div>
    </>
  );

  return (
    <div className="space-y-6 pt-2">
      <PageHeader
        title="User management"
        sub="Create, edit, and deactivate platform accounts."
        actions={
          <Button
            variant="primary"
            onClick={() => {
              setFormData({ full_name: "", email: "", role: "citizen", is_active: true });
              setFormError("");
              setIsCreateModalOpen(true);
            }}
          >
            <Plus className="w-4 h-4" />
            Create user
          </Button>
        }
      />

      <FormError>{error}</FormError>

      <Card>
        <CardHeader title="All users" sub={loading ? undefined : `${users.length} accounts`} />
        {loading ? (
          <TableSkeleton rows={6} />
        ) : users.length === 0 ? (
          <EmptyState icon={Users} title="No users yet" />
        ) : (
          <DataTable columns={columns} rows={users} rowKey={(u) => u.id} />
        )}
      </Card>

      {/* create */}
      <Modal open={isCreateModalOpen} onClose={() => setIsCreateModalOpen(false)} title="Create user">
        <form onSubmit={handleCreate} className="space-y-4">
          <FormError>{formError}</FormError>
          <FormNotice>
            A secure password is generated automatically and emailed to the user.
          </FormNotice>
          {userFormFields}
          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="ghost" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={formLoading}>
              Create user
            </Button>
          </div>
        </form>
      </Modal>

      {/* edit */}
      <Modal open={isEditModalOpen} onClose={() => setIsEditModalOpen(false)} title="Edit user">
        <form onSubmit={handleUpdate} className="space-y-4">
          <FormError>{formError}</FormError>
          {userFormFields}
          <div className="flex items-center justify-between p-3.5 bg-surface-2 rounded-control">
            <div className="text-sm">
              <p className="font-medium text-ink">Account active</p>
              <p className="text-ink-2 text-xs mt-0.5">Disabled accounts can't sign in.</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={formData.is_active}
              onClick={() => setFormData({ ...formData, is_active: !formData.is_active })}
              className={cn(
                "relative inline-flex h-6 w-11 shrink-0 rounded-pill transition-colors duration-150",
                formData.is_active ? "bg-accent" : "bg-surface-3"
              )}
            >
              <span
                className={cn(
                  "pointer-events-none inline-block h-5 w-5 mt-0.5 ml-0.5 rounded-pill bg-surface shadow-card transition-transform duration-150",
                  formData.is_active && "translate-x-5"
                )}
              />
            </button>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="ghost" onClick={() => setIsEditModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={formLoading}>
              Save changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* delete */}
      <Modal open={isDeleteModalOpen} onClose={() => setIsDeleteModalOpen(false)} title="Delete user?">
        <div className="space-y-4">
          <p className="text-sm text-ink-2">
            This permanently deletes <strong className="text-ink">{selectedUser?.full_name}</strong>{" "}
            and notifies them by email. It can't be undone.
          </p>
          <FormError>{formError}</FormError>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setIsDeleteModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" loading={formLoading} onClick={handleDelete}>
              Delete user
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
