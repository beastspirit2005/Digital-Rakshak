"use client";

import { api } from "@/lib/api";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CheckCircle2 } from "lucide-react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input, Label, FormError, FormNotice, OtpInput } from "@/components/ui/field";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState<"email" | "reset">("email");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const reduced = useReducedMotion();

  const handleRequestOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      await axios.post(api("/auth/forgot-password"), { email });
      setStep("reset");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Couldn't send the reset code. Try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      await axios.post(api("/auth/reset-password"), {
        email,
        otp,
        new_password: newPassword,
      });
      setSuccess(true);
      setTimeout(() => {
        router.push("/auth/login");
      }, 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Couldn't reset the password. Try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="rise-in text-center">
        <div className="w-12 h-12 rounded-pill bg-success-tint flex items-center justify-center mx-auto mb-5">
          <CheckCircle2 className="w-5 h-5 text-success" />
        </div>
        <h2 className="font-display font-semibold text-xl tracking-tight text-ink">
          Password updated
        </h2>
        <p className="text-sm text-ink-2 mt-2">Taking you back to sign in…</p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="font-display font-semibold text-xl tracking-tight text-ink">
        Reset your password
      </h2>
      <p className="text-sm text-ink-2 mt-1.5 mb-8">
        {step === "email"
          ? "Enter your email and we'll send you a reset code."
          : "Enter the code from your inbox and pick a new password."}
      </p>

      <AnimatePresence mode="wait" initial={false}>
        {step === "email" ? (
          <motion.form
            key="email-form"
            initial={{ opacity: 0, y: reduced ? 0 : 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            onSubmit={handleRequestOTP}
            className="space-y-5"
          >
            <FormError>{error}</FormError>

            <div>
              <Label htmlFor="resetEmail">Email</Label>
              <Input
                id="resetEmail"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>

            <Button type="submit" variant="primary" size="lg" loading={isLoading} className="w-full">
              Send reset code
            </Button>
          </motion.form>
        ) : (
          <motion.form
            key="reset-form"
            initial={{ opacity: 0, y: reduced ? 0 : 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            onSubmit={handleResetPassword}
            className="space-y-5"
          >
            <FormNotice>
              We sent a reset code to <span className="font-medium">{email}</span>.
            </FormNotice>

            <FormError>{error}</FormError>

            <div>
              <Label htmlFor="otp">Code</Label>
              <OtpInput id="otp" value={otp} onChange={setOtp} />
            </div>

            <div>
              <Label htmlFor="newPassword">New password</Label>
              <Input
                id="newPassword"
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="8+ characters with a digit and a symbol"
                autoComplete="new-password"
              />
            </div>

            <Button type="submit" variant="primary" size="lg" loading={isLoading} className="w-full">
              Reset password
            </Button>

            <button
              type="button"
              onClick={() => setStep("email")}
              className="w-full text-sm text-ink-2 hover:text-ink transition-colors"
            >
              Didn&apos;t get the code? Send it again
            </button>
          </motion.form>
        )}
      </AnimatePresence>

      <p className="text-center text-sm text-ink-2 mt-8">
        Remembered it?{" "}
        <Link href="/auth/login" className="text-ink font-medium underline underline-offset-4 hover:text-accent-text">
          Sign in
        </Link>
      </p>
    </div>
  );
}
