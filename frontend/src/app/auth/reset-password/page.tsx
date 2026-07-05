"use client";

import { api } from "@/lib/api";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Shield, ArrowRight, Loader2, CheckCircle2, AlertCircle, KeyRound } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState<"email" | "reset">("email");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleRequestOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      await axios.post(api("/auth/forgot-password"), { email });
      setStep("reset");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to request password reset. Please try again.");
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
      setError(err.response?.data?.detail || "Failed to reset password. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-panel p-8 md:p-10 rounded-3xl w-full text-center space-y-6"
      >
        <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto border border-emerald-500/20">
          <CheckCircle2 className="w-8 h-8 text-emerald-500" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight">Password Reset!</h2>
        <p className="text-muted-foreground">
          Your password has been successfully reset. Redirecting you to login...
        </p>
      </motion.div>
    );
  }

  return (
    <div className="glass-panel p-8 md:p-10 rounded-3xl w-full overflow-hidden">
      <div className="flex justify-center mb-8">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center border border-primary/20 shadow-inner">
          <KeyRound className="w-8 h-8 text-primary" />
        </div>
      </div>

      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold tracking-tight mb-2">Reset Password</h2>
        <p className="text-sm text-muted-foreground">
          {step === "email" ? "Enter your email to receive a reset OTP" : "Enter the OTP and your new password"}
        </p>
      </div>

      <AnimatePresence mode="wait">
        {step === "email" ? (
          <motion.form 
            key="email-form"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            onSubmit={handleRequestOTP} 
            className="space-y-6"
          >
            {error && (
              <div className="bg-red-500/10 text-red-600 dark:text-red-400 p-3 rounded-xl flex items-center gap-2 text-sm border border-red-500/20">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <p>{error}</p>
              </div>
            )}

            <div className="space-y-2">
              <label htmlFor="resetEmail" className="text-sm font-medium">Email Address</label>
              <input 
                id="resetEmail"
                type="email" 
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none"
              />
            </div>
            
            <button 
              type="submit" 
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground py-3 rounded-xl font-medium hover:bg-primary/90 transition-all active:scale-[0.98] disabled:opacity-70"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>Send Reset OTP <ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          </motion.form>
        ) : (
          <motion.form 
            key="reset-form"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            onSubmit={handleResetPassword} 
            className="space-y-6"
          >
            <div className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 p-4 rounded-xl flex items-start gap-3 border border-emerald-500/20">
              <CheckCircle2 className="w-5 h-5 mt-0.5 shrink-0" />
              <div className="text-sm">
                <p className="font-medium">OTP Sent Successfully</p>
                <p className="opacity-90">Check your inbox for the reset code.</p>
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 text-red-600 dark:text-red-400 p-3 rounded-xl flex items-center gap-2 text-sm border border-red-500/20">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <p>{error}</p>
              </div>
            )}

            <div className="space-y-2">
              <label htmlFor="otp" className="text-sm font-medium">Enter OTP</label>
              <input 
                id="otp"
                type="text" 
                required
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                placeholder="• • • • • •"
                className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none text-center tracking-[0.5em] text-lg font-mono"
                maxLength={6}
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="newPassword" className="text-sm font-medium">New Password</label>
              <input 
                id="newPassword"
                type="password" 
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none"
              />
              <p className="text-xs text-muted-foreground mt-1">Must be at least 8 chars, 1 digit, and 1 special char.</p>
            </div>
            
            <button 
              type="submit" 
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground py-3 rounded-xl font-medium hover:bg-primary/90 transition-all active:scale-[0.98] disabled:opacity-70"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                "Reset Password"
              )}
            </button>

            <button 
              type="button"
              onClick={() => setStep("email")}
              className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Didn't receive the code? Try again.
            </button>
          </motion.form>
        )}
      </AnimatePresence>

      <p className="text-center text-sm text-muted-foreground mt-6">
        Remembered your password?{" "}
        <Link href="/auth/login" className="text-primary hover:underline font-medium">
          Sign in
        </Link>
      </p>
    </div>
  );
}
