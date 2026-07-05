"use client";

import { api } from "@/lib/api";
import React, { useEffect, useState } from "react";
import { Users, Shield, Loader2, AlertCircle, Plus, Edit2, Trash2, X, CheckCircle2 } from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import axios from "axios";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { token, user: currentUser } = useAuthStore();

  // Modal States
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  
  // Form States
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    role: "citizen",
    is_active: true
  });
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState("");

  const fetchUsers = async () => {
    if (!token) return;
    try {
      const response = await fetch(api("/users/"), {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (!response.ok) {
        throw new Error("Failed to fetch users");
      }
      const data = await response.json();
      setUsers(data);
    } catch (err: any) {
      setError(err.message || "An error occurred while fetching users");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [token]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError("");
    try {
      await axios.post(api("/users/"), formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setIsCreateModalOpen(false);
      fetchUsers();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || "Failed to create user");
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
      await axios.put(api(`/users/${selectedUser.id}`), {
        full_name: formData.full_name,
        email: formData.email,
        role: formData.role,
        is_active: formData.is_active
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setIsEditModalOpen(false);
      fetchUsers();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || "Failed to update user");
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
        headers: { Authorization: `Bearer ${token}` }
      });
      setIsDeleteModalOpen(false);
      fetchUsers();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || "Failed to delete user");
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
      is_active: u.is_active
    });
    setIsEditModalOpen(true);
  };

  const openDeleteModal = (u: User) => {
    setSelectedUser(u);
    setIsDeleteModalOpen(true);
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role?.toLowerCase()) {
      case 'admin': return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'police': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'banker': return 'bg-green-100 text-green-800 border-green-200';
      case 'citizen': return 'bg-amber-100 text-amber-800 border-amber-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px] p-8">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary/10 text-primary rounded-xl">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">User Management</h1>
            <p className="text-muted-foreground">View, edit, and manage all platform users.</p>
          </div>
        </div>
        <button
          onClick={() => {
            setFormData({ full_name: "", email: "", role: "citizen", is_active: true });
            setIsCreateModalOpen(true);
          }}
          className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-xl font-medium hover:bg-primary/90 transition-all shadow-sm"
        >
          <Plus className="w-4 h-4" /> Create User
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 px-4 py-3 rounded-xl flex items-center gap-3">
          <AlertCircle className="w-5 h-5" />
          <p>{error}</p>
        </div>
      )}

      <div className="bg-card rounded-2xl shadow-sm border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted/50 border-b border-border text-muted-foreground">
              <tr>
                <th className="px-6 py-4 font-semibold">Name</th>
                <th className="px-6 py-4 font-semibold">Email</th>
                <th className="px-6 py-4 font-semibold">Role</th>
                <th className="px-6 py-4 font-semibold">Status</th>
                <th className="px-6 py-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {users.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-muted-foreground">
                    No users found.
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-6 py-4 font-medium text-foreground">{user.full_name || "N/A"}</td>
                    <td className="px-6 py-4 text-muted-foreground">{user.email}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${getRoleBadgeColor(user.role)}`}>
                        {user.role?.toLowerCase() === 'admin' && <Shield className="w-3 h-3" />}
                        {user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-semibold ${
                        user.is_active ? 'bg-emerald-500/10 text-emerald-600' : 'bg-red-500/10 text-red-600'
                      }`}>
                        {user.is_active ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button 
                          onClick={() => openEditModal(user)}
                          className="p-2 text-blue-600 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 rounded-lg transition-colors"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button 
                          onClick={() => openDeleteModal(user)}
                          disabled={user.id === currentUser?.id}
                          className="p-2 text-red-600 bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title={user.id === currentUser?.id ? "Cannot delete yourself" : "Delete user"}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* --- Create Modal --- */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">Create New User</h2>
              <button onClick={() => setIsCreateModalOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {formError && (
              <div className="mb-4 bg-red-500/10 text-red-600 p-3 rounded-lg text-sm">{formError}</div>
            )}
            <div className="mb-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 p-3 rounded-lg text-sm flex gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <p>A secure password will be auto-generated and emailed to the user.</p>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Full Name</label>
                <input required type="text" value={formData.full_name} onChange={e => setFormData({...formData, full_name: e.target.value})} className="w-full px-4 py-2 bg-muted border border-border rounded-xl focus:border-primary outline-none" />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Email</label>
                <input required type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} className="w-full px-4 py-2 bg-muted border border-border rounded-xl focus:border-primary outline-none" />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Role</label>
                <select value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})} className="w-full px-4 py-2 bg-muted border border-border rounded-xl focus:border-primary outline-none">
                  <option value="citizen">Citizen</option>
                  <option value="police">Police Officer</option>
                  <option value="banker">Banker</option>
                  <option value="admin">Administrator</option>
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-border">
                <button type="button" onClick={() => setIsCreateModalOpen(false)} className="px-4 py-2 rounded-xl text-muted-foreground hover:bg-muted font-medium transition-colors">Cancel</button>
                <button type="submit" disabled={formLoading} className="px-4 py-2 bg-primary text-primary-foreground rounded-xl font-medium hover:bg-primary/90 flex items-center gap-2">
                  {formLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create User"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- Edit Modal --- */}
      {isEditModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">Edit User Details</h2>
              <button onClick={() => setIsEditModalOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {formError && (
              <div className="mb-4 bg-red-500/10 text-red-600 p-3 rounded-lg text-sm">{formError}</div>
            )}

            <form onSubmit={handleUpdate} className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Full Name</label>
                <input required type="text" value={formData.full_name} onChange={e => setFormData({...formData, full_name: e.target.value})} className="w-full px-4 py-2 bg-muted border border-border rounded-xl focus:border-primary outline-none" />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Email</label>
                <input required type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} className="w-full px-4 py-2 bg-muted border border-border rounded-xl focus:border-primary outline-none" />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Role</label>
                <select value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})} className="w-full px-4 py-2 bg-muted border border-border rounded-xl focus:border-primary outline-none">
                  <option value="citizen">Citizen</option>
                  <option value="police">Police Officer</option>
                  <option value="banker">Banker</option>
                  <option value="admin">Administrator</option>
                </select>
              </div>
              <div className="flex items-center justify-between p-3 bg-muted rounded-xl border border-border mt-2">
                <div className="text-sm">
                  <p className="font-medium">Account Status</p>
                  <p className="text-muted-foreground text-xs">Enable or disable this account.</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked={formData.is_active} onChange={e => setFormData({...formData, is_active: e.target.checked})} className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-border">
                <button type="button" onClick={() => setIsEditModalOpen(false)} className="px-4 py-2 rounded-xl text-muted-foreground hover:bg-muted font-medium transition-colors">Cancel</button>
                <button type="submit" disabled={formLoading} className="px-4 py-2 bg-primary text-primary-foreground rounded-xl font-medium hover:bg-primary/90 flex items-center gap-2">
                  {formLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- Delete Modal --- */}
      {isDeleteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-card w-full max-w-sm rounded-2xl border border-border shadow-2xl p-6 text-center space-y-6">
            <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mx-auto text-red-500">
              <Trash2 className="w-8 h-8" />
            </div>
            
            <div>
              <h2 className="text-xl font-bold mb-2">Delete User?</h2>
              <p className="text-muted-foreground text-sm">
                Are you sure you want to permanently delete <strong>{selectedUser?.full_name}</strong>? An email will be sent to them notifying them of this action. This cannot be undone.
              </p>
            </div>

            {formError && (
              <div className="bg-red-500/10 text-red-600 p-3 rounded-lg text-sm text-left">{formError}</div>
            )}

            <div className="flex gap-3">
              <button type="button" onClick={() => setIsDeleteModalOpen(false)} className="flex-1 py-2.5 rounded-xl text-muted-foreground hover:bg-muted font-medium transition-colors">Cancel</button>
              <button onClick={handleDelete} disabled={formLoading} className="flex-1 py-2.5 bg-red-500 text-white rounded-xl font-medium hover:bg-red-600 flex items-center justify-center gap-2">
                {formLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
