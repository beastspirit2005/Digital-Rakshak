  "use client";

  import { Suspense, useState } from "react";
  import { api } from "@/lib/api";
  import Link from "next/link";
  import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
  import axios from "axios";
  import { useAuthStore } from "@/lib/auth-store";
  import { useRouter, useSearchParams } from "next/navigation";
  import { Button } from "@/components/ui/button";
  import { Input, Label, FormError, FormNotice, OtpInput } from "@/components/ui/field";
  import { Segmented } from "@/components/ui/tabs";
  import { Mail, Lock as LockIcon } from "lucide-react";

  function routeForRole(role: string) {
    if (role === "admin") return "/admin";
    if (role === "citizen") return "/citizen";
    if (role === "banker") return "/banker";
    return "/workbench";
  }
  function canAccessRoute(role: string, path: string) {
    if (path.startsWith("/admin")) {
      return role === "admin";
    }

    if (
      path.startsWith("/workbench") ||
      path.startsWith("/copilot") ||
      path.startsWith("/police")
    ) {
      return ["admin", "police", "cyber_cell"].includes(role);
    }

    if (path.startsWith("/banker")) {
      return ["admin", "banker", "bank_employee"].includes(role);
    }

    if (path.startsWith("/citizen")) {
      return ["admin", "citizen"].includes(role);
    }

    return true;
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
          const role = response.data.user.role;

          const destination =
            nextParam && canAccessRoute(role, nextParam)
              ? nextParam
              : routeForRole(role);

          router.replace(destination);
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
        const role = response.data.user.role;

        const destination =
          nextParam && canAccessRoute(role, nextParam)
            ? nextParam
            : routeForRole(role);

        router.replace(destination);
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
      <div className="text-left">
      <h2 className="font-display font-bold text-[44px] leading-tight tracking-tight text-ink">Sign in</h2>
        <p className="text-sm text-ink-2 mt-2 mb-8">
          New here?{" "}
          <Link href="/auth/register" className="text-accent-text font-semibold hover:text-accent-text/80 hover:underline transition-colors duration-200">
            Create an account
          </Link>
        </p>

        <div className="relative">
          {step === "email" ? (
            <motion.form
              key="email-form"
              initial={{ opacity: 0, y: reduced ? 0 : 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              onSubmit={handleLogin}
              className="space-y-6"
            >
              <div className="p-0.5 rounded-xl">
                <Segmented
                  className="w-full vercel-segmented"
                  items={[
                    { id: "password", label: "Password" },
                    { id: "otp", label: "Email code" },
                  ]}
                  value={loginMethod}
                  onChange={(id) => setLoginMethod(id as "password" | "otp")}
                />
              </div>

              {error && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="p-3.5 rounded-xl border border-red-500/20 bg-red-500/10 text-red-400 text-xs sm:text-sm font-medium flex items-center gap-2.5 shadow-[0_4px_12px_rgba(239,68,68,0.15)] leading-relaxed"
                >
                  <span className="text-base leading-none">⚠️</span>
                  <div className="flex-1 text-left">{error}</div>
                </motion.div>
              )}

              {/* Hidden component to support legacy integration requirements */}
              <div className="hidden">
                <FormError>{error}</FormError>
              </div>

              {/* Email field stagger animated */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05, duration: 0.35, ease: "easeOut" }}
                className="space-y-2"
              >
                <Label htmlFor="email" className="text-xs font-semibold text-ink-2 uppercase tracking-wider block">
                  Email
                </Label>
                <div className="relative flex items-center">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 z-20 text-ink-3 pointer-events-none">
                    <Mail className="w-5 h-5" />
                  </div>
                  <Input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    autoComplete="email"
                    className="w-full bg-surface border-line hover:border-ink-3/50 focus:border-accent focus:ring-1 focus:ring-accent rounded-xl text-ink placeholder:text-ink-3 pl-11 transition-all duration-300 h-12"
                  />
                </div>
              </motion.div>

              {/* Password field stagger animated */}
              {loginMethod === "password" && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1, duration: 0.35, ease: "easeOut" }}
                  className="space-y-2"
                >
                  <div className="flex justify-between items-center mb-1">
                    <Label htmlFor="password" className="text-xs font-semibold text-ink-2 uppercase tracking-wider mb-0">
                      Password
                    </Label>
                    <Link
                      href="/auth/reset-password"
                      className="text-xs text-ink-2 hover:text-accent hover:underline underline-offset-4 transition-colors"
                    >
                      Forgot password?
                    </Link>
                  </div>
                  <div className="relative flex items-center">
    <div className="absolute left-4 top-1/2 -translate-y-1/2 z-20 text-ink-3 pointer-events-none">
      <LockIcon className="w-5 h-5" />
    </div>

    <Input
      id="password"
      type="password"
      required
      value={password}
      onChange={(e) => setPassword(e.target.value)}
      placeholder="••••••••"
      autoComplete="current-password"
      className="w-full h-12 rounded-xl bg-surface border border-line text-ink placeholder:text-ink-3 pl-12 pr-4  focus:border-accent focus:ring-1 focus:ring-accent hover:border-ink-3/50"
    />
  </div>              </motion.div>
              )}

              {/* Stagger animated trigger button */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15, duration: 0.35, ease: "easeOut" }}
              >
                <Button 
                  type="submit" 
                  variant="primary" 
                  size="lg" 
                  loading={isLoading} 
                  className="w-full h-[56px] relative overflow-hidden bg-accent hover:bg-accent-hover text-accent-ink font-bold rounded-xl shadow-[0_4px_24px_rgba(245,158,11,0.2)] active:scale-[0.98] transition-all duration-300 text-sm tracking-wider uppercase"
                >
                  {loginMethod === "password" ? "Sign in" : "Send code"}
                </Button>
              </motion.div>
            </motion.form>
          ) : (
            <motion.form
              key="otp-form"
              initial={{ opacity: 0, y: reduced ? 0 : 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              onSubmit={handleVerifyOTP}
              className="space-y-6"
            >
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
              >
                <FormNotice className="p-3.5 rounded-xl border border-line bg-surface-2 text-ink-2 text-xs sm:text-sm text-left">
                  We sent a six-digit code to <span className="font-semibold text-ink">{email}</span>.
                </FormNotice>
              </motion.div>

              {error && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="p-3.5 rounded-xl border border-red-500/20 bg-red-500/10 text-red-400 text-xs sm:text-sm font-medium flex items-center gap-2.5 shadow-[0_4px_12px_rgba(239,68,68,0.15)] leading-relaxed"
                >
                  <span className="text-base leading-none">⚠️</span>
                  <div className="flex-1 text-left">{error}</div>
                </motion.div>
              )}

              {/* Hidden component to support legacy integration requirements */}
              <div className="hidden">
                <FormError>{error}</FormError>
              </div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.35 }}
                className="space-y-2 text-left"
              >
                <Label htmlFor="otp" className="text-xs font-semibold text-ink-2 uppercase tracking-wider block">Code</Label>
                <div className="flex justify-center py-2 otp-input-centered-wrapper">
                  <OtpInput id="otp" value={otp} onChange={setOtp} />
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15, duration: 0.35 }}
                className="space-y-4"
              >
                <Button 
                  type="submit" 
                  variant="primary" 
                  size="lg" 
                  loading={isLoading} 
                  className="w-full h-[56px] relative overflow-hidden bg-accent hover:bg-accent-hover text-accent-ink font-bold rounded-xl shadow-[0_4px_24px_rgba(245,158,11,0.2)] active:scale-[0.98] transition-all duration-300 text-sm tracking-wider uppercase"
                >
                  Verify and sign in
                </Button>

                <button
                  type="button"
                  onClick={() => setStep("email")}
                  className="w-full text-sm text-ink-3 hover:text-ink transition-colors py-1 block"
                >
                  Use a different email
                </button>
              </motion.div>
            </motion.form>
          )}
        </div>
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