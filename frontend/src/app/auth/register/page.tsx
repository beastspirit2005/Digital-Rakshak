"use client";

import { api } from "@/lib/api";
import { useState } from "react";
import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import axios from "axios";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input, Label, FormError } from "@/components/ui/field";
import { Badge } from "@/components/ui/badge";

const ROLES = [
  { value: "citizen", label: "Citizen", description: "Report scams and check suspicious links" },
  { value: "police", label: "Police officer", description: "Investigate cases and manage evidence", requiresApproval: true },
  { value: "banker", label: "Banker", description: "Review fraud flags and freeze requests", requiresApproval: true },
  { value: "admin", label: "Administrator", description: "Manage the platform and approve users", requiresApproval: true },
];

export default function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("citizen");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      await axios.post(api("/auth/register"), {
        email,
        full_name: fullName,
        role,
        password,
      });
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Registration failed. Try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    const needsApproval = role !== "citizen";
    return (
      <div className="rise-in text-center">
        <div className="w-12 h-12 rounded-pill bg-success-tint flex items-center justify-center mx-auto mb-5">
          <CheckCircle2 className="w-5 h-5 text-success" />
        </div>
        <h2 className="font-display font-semibold text-xl tracking-tight text-ink">
          Account created
        </h2>
        <p className="text-sm text-ink-2 mt-2 max-w-sm mx-auto">
          {needsApproval
            ? "An administrator will review your registration. You'll get an email once you're approved."
            : "You're all set — sign in with your email to get started."}
        </p>
        <Link href="/auth/login" className="inline-block mt-6">
          <Button variant="primary" size="lg">Go to sign in</Button>
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h2 className="font-display font-semibold text-xl tracking-tight text-ink">
        Create an account
      </h2>
      <p className="text-sm text-ink-2 mt-1.5 mb-8">
        Already registered?{" "}
        <Link href="/auth/login" className="text-ink font-medium underline underline-offset-4 hover:text-accent-text">
          Sign in
        </Link>
      </p>

      <form onSubmit={handleRegister} className="space-y-5">
        <FormError>{error}</FormError>

        <div>
          <Label htmlFor="fullName">Full name</Label>
          <Input
            id="fullName"
            type="text"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Asha Verma"
            autoComplete="name"
          />
        </div>

        <div>
          <Label htmlFor="registerEmail">Email</Label>
          <Input
            id="registerEmail"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
          />
        </div>

        <div>
          <Label htmlFor="registerPassword">Password</Label>
          <Input
            id="registerPassword"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="8+ characters with a digit and a symbol"
            autoComplete="new-password"
          />
        </div>

        <fieldset>
          <legend className="block text-sm font-medium text-ink mb-1.5">I am a</legend>
          <div className="grid grid-cols-1 gap-2">
            {ROLES.map((r) => (
              <label
                key={r.value}
                className={cn(
                  "flex items-start gap-3 p-3.5 rounded-control border cursor-pointer transition-colors duration-150",
                  role === r.value
                    ? "border-accent-text bg-surface"
                    : "border-line bg-surface hover:border-ink-3"
                )}
              >
                <input
                  type="radio"
                  name="role"
                  value={r.value}
                  checked={role === r.value}
                  onChange={(e) => setRole(e.target.value)}
                  className="mt-1 accent-(--accent-text)"
                />
                <div>
                  <span className="text-sm font-medium text-ink">{r.label}</span>
                  {r.requiresApproval && (
                    <Badge tone="warning" className="ml-2">Needs approval</Badge>
                  )}
                  <p className="text-xs text-ink-2 mt-0.5">{r.description}</p>
                </div>
              </label>
            ))}
          </div>
        </fieldset>

        <Button type="submit" variant="primary" size="lg" loading={isLoading} className="w-full">
          Create account
        </Button>
      </form>
    </div>
  );
}
