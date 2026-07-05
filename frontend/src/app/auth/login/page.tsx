"use client";


import { api } from "@/lib/api";
import { useState } from "react";
import Link from "next/link";
import { Shield, ArrowRight, Loader2, CheckCircle2, AlertCircle, KeyRound, Mail } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [loginMethod, setLoginMethod] = useState<"password" | "otp">("password");
  const [step, setStep] = useState<"email" | "otp">("email");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuthStore();
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    
    if (loginMethod === "otp") {
      try {
        await axios.post(api("/auth/request-otp"), { email });
        setStep("otp");
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to request OTP. Please try again.");
      } finally {
        setIsLoading(false);
      }
    } else {
      try {
        const response = await axios.post(api("/auth/login-password"), { email, password });
        login(response.data.access_token, response.data.user);
        
        const role = response.data.user.role;
        if (role === 'admin') router.push("/admin");
        else if (role === 'citizen') router.push("/citizen");
        else router.push("/workbench");
      } catch (err: any) {
        const status = err.response?.status;
        const detail = err.response?.data?.detail;
        if (status === 403) setError(detail || "Account not approved yet.");
        else if (status === 401) setError("Invalid email or password.");
        else setError(detail || "Login failed. Please try again.");
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
      const response = await axios.post(api("/auth/verify-otp"), { 
        email,
        otp
      });
      login(response.data.access_token, response.data.user);
      
      const role = response.data.user.role;
      if (role === 'admin') {
        router.push("/admin");
      } else if (role === 'citizen') {
        router.push("/citizen");
      } else {
        router.push("/workbench");
      }
    } catch (err: any) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      if (status === 403) setError(detail || "Account not approved yet.");
      else if (status === 401) setError("Invalid or expired OTP.");
      else setError(detail || "Login failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel p-8 md:p-10 rounded-3xl w-full">
      <div className="flex justify-center mb-8">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center border border-primary/20 shadow-inner">
          <Shield className="w-8 h-8 text-primary" />
        </div>
      </div>
      
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold tracking-tight mb-2">Welcome Back</h2>
        <p className="text-sm text-muted-foreground">
          Enter your credentials to access the platform
        </p>
      </div>

      <AnimatePresence mode="wait">
        {step === "email" ? (
          <motion.form 
            key="email-form"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            onSubmit={handleLogin} 
            className="space-y-6"
          >
            <div className="flex p-1 bg-background border border-border rounded-xl">
              <button
                type="button"
                onClick={() => setLoginMethod("password")}
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-lg transition-all ${
                  loginMethod === "password" ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-white"
                }`}
              >
                <KeyRound className="w-4 h-4" /> Password
              </button>
              <button
                type="button"
                onClick={() => setLoginMethod("otp")}
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-lg transition-all ${
                  loginMethod === "otp" ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-white"
                }`}
              >
                <Mail className="w-4 h-4" /> Email OTP
              </button>
            </div>

            {error && (
              <div className="bg-red-500/10 text-red-600 dark:text-red-400 p-3 rounded-xl flex items-center gap-2 text-sm border border-red-500/20">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <p>{error}</p>
              </div>
            )}
            
            <div className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium">Email Address</label>
                <input 
                  id="email"
                  type="email" 
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@agency.gov"
                  className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none"
                />
              </div>

              {loginMethod === "password" && (
                <div className="space-y-2">
                  <label htmlFor="password" className="text-sm font-medium">Password</label>
                  <input 
                    id="password"
                    type="password" 
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none"
                  />
                </div>
              )}
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
                  {loginMethod === "password" ? "Login" : "Continue"} <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </motion.form>
        ) : (
          <motion.form 
            key="otp-form"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            onSubmit={handleVerifyOTP} 
            className="space-y-6"
          >
            <div className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 p-4 rounded-xl flex items-start gap-3 border border-emerald-500/20">
              <CheckCircle2 className="w-5 h-5 mt-0.5 shrink-0" />
              <div className="text-sm">
                <p className="font-medium">OTP Sent Successfully</p>
                <p className="opacity-90">We've sent a one-time password to {email}</p>
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
            
            <button 
              type="submit" 
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground py-3 rounded-xl font-medium hover:bg-primary/90 transition-all active:scale-[0.98] disabled:opacity-70"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                "Verify & Login"
              )}
            </button>

            <button 
              type="button"
              onClick={() => setStep("email")}
              className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Use a different email
            </button>
          </motion.form>
        )}
      </AnimatePresence>

      <p className="text-center text-sm text-muted-foreground mt-6">
        Don't have an account?{" "}
        <Link href="/auth/register" className="text-primary hover:underline font-medium">
          Register
        </Link>
      </p>
    </div>
  );
}
