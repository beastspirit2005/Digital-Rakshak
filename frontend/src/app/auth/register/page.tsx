"use client";


import { api } from "@/lib/api";
import { useState } from "react";
import Link from "next/link";
import { Shield, ArrowRight, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";
import axios from "axios";

const ROLES = [
  { value: "citizen", label: "Citizen", description: "Report scams and check suspicious links" },
  { value: "police", label: "Police Officer", description: "Investigate cases and manage evidence", requiresApproval: true },
  { value: "banker", label: "Banker", description: "Financial fraud analysis and account freeze requests", requiresApproval: true },
  { value: "admin", label: "Administrator", description: "Platform management and user approvals", requiresApproval: true },
];

export default function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("citizen");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const selectedRole = ROLES.find(r => r.value === role);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const payload: any = {
        email,
        full_name: fullName,
        role,
        password,
      };
      const response = await axios.post(api("/auth/register"), payload);
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Registration failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    const needsApproval = role !== "citizen";
    return (
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-panel p-8 md:p-10 rounded-3xl w-full text-center space-y-6"
      >
        <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto border border-emerald-500/20">
          <CheckCircle2 className="w-8 h-8 text-emerald-500" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight">Registration Successful!</h2>
        <p className="text-muted-foreground">
          {needsApproval
            ? "Your account is pending admin approval. You'll receive a welcome email once approved."
            : "Your account is active! You can now log in using your email."
          }
        </p>
        <Link
          href="/auth/login"
          className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-xl font-medium hover:bg-primary/90 transition-all"
        >
          Go to Login <ArrowRight className="w-4 h-4" />
        </Link>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel p-8 md:p-10 rounded-3xl w-full"
    >
      <div className="flex justify-center mb-8">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center border border-primary/20 shadow-inner">
          <Shield className="w-8 h-8 text-primary" />
        </div>
      </div>

      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold tracking-tight mb-2">Create Account</h2>
        <p className="text-sm text-muted-foreground">
          Join Digital Rakshak to fight digital fraud
        </p>
      </div>

      <form onSubmit={handleRegister} className="space-y-5">
        {error && (
          <div className="bg-red-500/10 text-red-600 dark:text-red-400 p-3 rounded-xl flex items-center gap-2 text-sm border border-red-500/20">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <div className="space-y-2">
          <label htmlFor="fullName" className="text-sm font-medium">Full Name</label>
          <input
            id="fullName"
            type="text"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="John Doe"
            className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="registerEmail" className="text-sm font-medium">Email Address</label>
          <input
            id="registerEmail"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="registerPassword" className="text-sm font-medium">Password</label>
          <input
            id="registerPassword"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min 8 chars, 1 digit, 1 special char"
            className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Role</label>
          <div className="grid grid-cols-1 gap-2">
            {ROLES.map((r) => (
              <label
                key={r.value}
                className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                  role === r.value
                    ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                    : "border-border hover:border-primary/30"
                }`}
              >
                <input
                  type="radio"
                  name="role"
                  value={r.value}
                  checked={role === r.value}
                  onChange={(e) => setRole(e.target.value)}
                  className="mt-1 accent-primary"
                />
                <div>
                  <span className="text-sm font-medium">{r.label}</span>
                  {r.requiresApproval && (
                    <span className="ml-2 text-xs text-orange-500 bg-orange-500/10 px-1.5 py-0.5 rounded">Requires Approval</span>
                  )}
                  <p className="text-xs text-muted-foreground mt-0.5">{r.description}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground py-3 rounded-xl font-medium hover:bg-primary/90 transition-all active:scale-[0.98] disabled:opacity-70"
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <>
              Create Account <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>

        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/auth/login" className="text-primary hover:underline font-medium">
            Sign in
          </Link>
        </p>
      </form>
    </motion.div>
  );
}
