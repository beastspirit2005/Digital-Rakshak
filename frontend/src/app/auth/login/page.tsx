"use client";

import { Suspense } from "react";

import { api } from "@/lib/api";
import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input, Label, FormError, FormNotice, OtpInput } from "@/components/ui/field";
import { Segmented } from "@/components/ui/tabs";

function routeForRole(role: string) {
  if (role === "admin") return "/admin";
  if (role === "citizen") return "/citizen";
  if (role === "banker") return "/banker";
  return "/workbench";
}
function LoginForm() {
  const [loginMethod, setLoginMethod] = useState<"password" | "otp">("password");
  const [step, setStep] = useState<"email" | "otp">("email");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuthStore();
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextParam = searchParams.get("next");
  const reduced = useReducedMotion();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    if (loginMethod === "otp") {
      try {
        await axios.post(api("/auth/request-otp"), { email });
        setStep("otp");
      } catch (err: any) {
        setError(err.response?.data?.detail || "Couldn't send the code. Try again.");
      } finally {
        setIsLoading(false);
      }
    } else {
      try {
        const response = await axios.post(api("/auth/login-password"), { email, password });
        login(response.data.access_token, response.data.user);
        router.push(nextParam || routeForRole(response.data.user.role));
      } catch (err: any) {
        const status = err.response?.status;
        const detail = err.response?.data?.detail;
        if (status === 403) setError(detail || "Your account hasn't been approved yet.");
        else if (status === 401) setError("That email or password doesn't match.");
        else setError(detail || "Sign-in failed. Try again.");
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const response = await axios.post(api("/auth/verify-otp"), { email, otp });
      login(response.data.access_token, response.data.user);
      router.push(nextParam || routeForRole(response.data.user.role));
    } catch (err: any) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      if (status === 403) setError(detail || "Your account hasn't been approved yet.");
      else if (status === 401) setError("That code is invalid or has expired.");
      else setError(detail || "Sign-in failed. Try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <h2 className="font-display font-semibold text-xl tracking-tight text-ink">Sign in</h2>
      <p className="text-sm text-ink-2 mt-1.5 mb-8">
        New here?{" "}
        <Link href="/auth/register" className="text-ink font-medium underline underline-offset-4 hover:text-accent-text">
          Create an account
        </Link>
      </p>

      <AnimatePresence mode="wait" initial={false}>
        {step === "email" ? (
          <motion.form
            key="email-form"
            initial={{ opacity: 0, y: reduced ? 0 : 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            onSubmit={handleLogin}
            className="space-y-5"
          >
            <Segmented
              className="w-full"
              items={[
                { id: "password", label: "Password" },
                { id: "otp", label: "Email code" },
              ]}
              value={loginMethod}
              onChange={(id) => setLoginMethod(id as "password" | "otp")}
            />

            <FormError>{error}</FormError>

            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>

            {loginMethod === "password" && (
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <Label htmlFor="password" className="mb-0">Password</Label>
                  <Link
                    href="/auth/reset-password"
                    className="text-xs text-ink-2 hover:text-ink underline underline-offset-4"
                  >
                    Forgot password?
                  </Link>
                </div>
                <Input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
              </div>
            )}

            <Button type="submit" variant="primary" size="lg" loading={isLoading} className="w-full">
              {loginMethod === "password" ? "Sign in" : "Send code"}
            </Button>
          </motion.form>
        ) : (
          <motion.form
            key="otp-form"
            initial={{ opacity: 0, y: reduced ? 0 : 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            onSubmit={handleVerifyOTP}
            className="space-y-5"
          >
            <FormNotice>
              We sent a six-digit code to <span className="font-medium">{email}</span>.
            </FormNotice>

            <FormError>{error}</FormError>

            <div>
              <Label htmlFor="otp">Code</Label>
              <OtpInput id="otp" value={otp} onChange={setOtp} />
            </div>

            <Button type="submit" variant="primary" size="lg" loading={isLoading} className="w-full">
              Verify and sign in
            </Button>

            <button
              type="button"
              onClick={() => setStep("email")}
              className="w-full text-sm text-ink-2 hover:text-ink transition-colors"
            >
              Use a different email
            </button>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
