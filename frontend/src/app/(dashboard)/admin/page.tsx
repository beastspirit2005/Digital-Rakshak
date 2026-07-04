"use client";


import { api } from "@/lib/api";
import { useState, useEffect } from "react";
import { CheckCircle2, XCircle, Search, Loader2, Users, ShieldCheck, Clock } from "lucide-react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { useRouter } from "next/navigation";

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
    try {
      const response = await axios.get(api("/users/"), {
        headers: { Authorization: `Bearer ${token}` },
      });
      setUsers(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch users.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchUsers();
  }, [token]);

  const handleApprove = async (userId: string) => {
    setApprovingId(userId);
    try {
      await axios.post(
        api(`/users/${userId}/approve`),
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      // Update local state
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_approved: true } : u))
      );
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to approve user.");
    } finally {
      setApprovingId(null);
    }
  };

  const handleSimulateAttack = async () => {
    setIsSimulating(true);
    setError("");
    try {
      await axios.post(
        api("/cases/simulate-attack"),
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      router.push("/workbench/map");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Simulation failed.");
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-col sm:flex-row gap-4 mb-8 items-start sm:items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Admin Dashboard</h1>
          <p className="text-muted-foreground">Manage users, approvals, and platform settings.</p>
        </div>
        <button
          onClick={handleSimulateAttack}
          disabled={isSimulating}
          className="flex items-center gap-2 px-4 py-2 bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 rounded-xl hover:bg-red-500/20 transition-all font-bold"
        >
          {isSimulating ? <Loader2 className="w-4 h-4 animate-spin" /> : <span className="animate-pulse">🚨</span>}
          {isSimulating ? "Injecting Threats..." : "Simulate National Cyber Attack"}
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 text-red-600 dark:text-red-400 p-4 rounded-xl flex items-center gap-2 text-sm border border-red-500/20 mb-6">
          <XCircle className="w-4 h-4 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="glass-panel p-5 rounded-2xl border border-border">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-muted-foreground">Total Users</p>
            <Users className="w-4 h-4 text-muted-foreground" />
          </div>
          <h3 className="text-2xl font-bold">{users.length}</h3>
        </div>
        <div className="glass-panel p-5 rounded-2xl border border-border">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-muted-foreground">Approved</p>
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
          </div>
          <h3 className="text-2xl font-bold text-emerald-600">{approvedCount}</h3>
        </div>
        <div className="glass-panel p-5 rounded-2xl border border-border">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-muted-foreground">Pending Approval</p>
            <Clock className="w-4 h-4 text-orange-500" />
          </div>
          <h3 className="text-2xl font-bold text-orange-500">{pendingCount}</h3>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search users by name, email, or role..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-11 pr-4 py-3 bg-card border border-border rounded-xl text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
        />
      </div>

      {/* Users Table */}
      <div className="glass-panel rounded-2xl border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-muted-foreground uppercase bg-muted/50 border-b border-border">
              <tr>
                <th className="px-6 py-4 font-medium">Name</th>
                <th className="px-6 py-4 font-medium">Email</th>
                <th className="px-6 py-4 font-medium">Role</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Registered</th>
                <th className="px-6 py-4 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-muted-foreground">
                    No users found.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-6 py-4 font-medium">{user.full_name || "—"}</td>
                    <td className="px-6 py-4 text-muted-foreground">{user.email}</td>
                    <td className="px-6 py-4">
                      <span className="px-2.5 py-1 rounded-md text-xs font-medium bg-primary/10 text-primary capitalize">
                        {user.role.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {user.is_approved ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                          <CheckCircle2 className="w-3 h-3" /> Approved
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20">
                          <Clock className="w-3 h-3" /> Pending
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-muted-foreground text-xs">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4">
                      {!user.is_approved && (
                        <button
                          onClick={() => handleApprove(user.id)}
                          disabled={approvingId === user.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500 text-foreground hover:bg-emerald-600 transition-colors disabled:opacity-50"
                        >
                          {approvingId === user.id ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <CheckCircle2 className="w-3 h-3" />
                          )}
                          Approve
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
