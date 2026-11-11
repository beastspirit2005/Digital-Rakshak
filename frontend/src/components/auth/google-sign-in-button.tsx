"use client";

import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";
import { api, formatApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { Loader2, AlertTriangle, ShieldCheck, Info } from "lucide-react";

declare global {
  interface Window {
    google?: any;
  }
}

interface GoogleSignInButtonProps {
  nextParam?: string | null;
  mode?: "login" | "register";
  onError?: (err: string) => void;
}

export function GoogleSignInButton({
  nextParam,
  mode = "login",
  onError,
}: GoogleSignInButtonProps) {
  const router = useRouter();
  const { login } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [originPending, setOriginPending] = useState(false);
  const buttonContainerRef = useRef<HTMLDivElement>(null);

  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

  const handleCredentialResponse = async (response: any) => {
    if (!response?.credential) return;

    setLoading(true);
    setErrorMsg("");

    try {
      const res = await axios.post(api("/auth/google"), {
        credential: response.credential,
      });

      const { access_token, user } = res.data;
      login(access_token, user);

      const destination =
        nextParam && nextParam.startsWith("/")
          ? nextParam
          : user.role === "citizen"
          ? "/personal"
          : "/citizen";

      router.replace(destination);
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ||
        formatApiError(err, "Google sign-in failed. Please try again.");
      setErrorMsg(msg);
      if (onError) onError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!googleClientId) return;

    const initializeGoogleGSI = () => {
      if (!window.google?.accounts?.id) return;

      try {
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: handleCredentialResponse,
          auto_select: false,
          cancel_on_tap_outside: true,
        });

        if (buttonContainerRef.current) {
          buttonContainerRef.current.innerHTML = "";
          window.google.accounts.id.renderButton(buttonContainerRef.current, {
            theme: "outline",
            size: "large",
            width: 380,
            text: mode === "register" ? "signup_with" : "continue_with",
            shape: "rectangular",
            logo_alignment: "left",
          });
        }

        // Trigger One Tap prompt non-intrusively with status inspection
        window.google.accounts.id.prompt((notification: any) => {
          if (notification?.isNotDisplayed?.()) {
            const reason = notification.getNotDisplayedReason?.();
            if (reason === "origin_mismatch") {
              setOriginPending(true);
            }
          }
        });
      } catch (err) {
        console.warn("Google One Tap initialization notice:", err);
      }
    };

    if (window.google?.accounts?.id) {
      initializeGoogleGSI();
    } else {
      const existingScript = document.getElementById("google-gsi-client");
      if (!existingScript) {
        const script = document.createElement("script");
        script.id = "google-gsi-client";
        script.src = "https://accounts.google.com/gsi/client";
        script.async = true;
        script.defer = true;
        script.onload = initializeGoogleGSI;
        document.body.appendChild(script);
      } else {
        existingScript.addEventListener("load", initializeGoogleGSI);
      }
    }
  }, [googleClientId, mode]);

  const handleDevOrFallbackClick = async () => {
    if (process.env.NODE_ENV !== "production") {
      setLoading(true);
      setErrorMsg("");
      try {
        const res = await axios.post(api("/auth/google"), {
          credential: "mock_google_token_citizen.dev@digitalrakshak.in|Dev Citizen",
        });
        const { access_token, user } = res.data;
        login(access_token, user);
        router.replace(nextParam || "/personal");
      } catch (err: any) {
        setErrorMsg(err.response?.data?.detail || "Google Dev Auth failed.");
      } finally {
        setLoading(false);
      }
    } else {
      setErrorMsg("Google Sign-In is configuring. Please use Email Code / Password sign-in below.");
    }
  };

  return (
    <div className="w-full space-y-3">
      {errorMsg && (
        <div className="p-3.5 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-400 text-xs sm:text-sm font-medium flex items-center gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          <div className="flex-1 text-left">{errorMsg}</div>
        </div>
      )}

      {originPending && (
        <div className="p-3 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs font-medium flex items-start gap-2">
          <Info className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="flex-1 text-left">
            Google OAuth origins recently updated take 5–15 minutes to propagate across Google edge servers. In the meantime, use Email sign-in below or Developer Sandbox login.
          </div>
        </div>
      )}

      {loading ? (
        <div className="w-full h-12 rounded-xl border border-line bg-surface flex items-center justify-center gap-2 text-ink-2 text-sm">
          <Loader2 className="w-4 h-4 animate-spin text-accent" />
          <span>Authenticating with Google...</span>
        </div>
      ) : googleClientId ? (
        <div className="flex flex-col items-center justify-center w-full min-h-[44px] space-y-2">
          <div ref={buttonContainerRef} className="w-full flex justify-center" />
          {process.env.NODE_ENV !== "production" && (
            <button
              type="button"
              onClick={handleDevOrFallbackClick}
              className="text-[11px] text-ink-3 hover:text-ink-2 transition-colors flex items-center gap-1.5 pt-1"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-accent" />
              <span>Sandbox Dev Instant Citizen Login</span>
            </button>
          )}
        </div>
      ) : (
        <button
          type="button"
          onClick={handleDevOrFallbackClick}
          className="w-full h-12 px-4 rounded-xl border border-line bg-surface hover:bg-surface-2 text-ink text-sm font-medium flex items-center justify-center gap-3 transition-colors shadow-sm active:scale-[0.99]"
        >
          <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
            />
          </svg>
          <span>Continue with Google (Citizen)</span>
        </button>
      )}
    </div>
  );
}
