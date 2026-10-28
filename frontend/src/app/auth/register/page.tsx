"use client";

import { api, formatApiError } from "@/lib/api";
import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  ShieldCheck,
  ShieldAlert,
  Building,
  KeyRound,
  Compass,
  FileCheck2,
  UploadCloud,
  AlertTriangle,
  RefreshCw,
  ArrowRight,
  MapPin,
  Lock
} from "lucide-react";
import axios from "axios";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input, Label, FormError } from "@/components/ui/field";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/lib/auth-store";
import { useRouter } from "next/navigation";

const ROLES = [
  { value: "citizen", label: "Citizen", description: "Report scams, scan links, and track cases" },
  { value: "police", label: "Police / Cyber Cell Investigator", description: "Investigate cases, view radar map & manage evidence", requiresKYC: true },
  { value: "banker", label: "Bank Nodal Official", description: "Review fraud flags, frozen mule accounts & alerts", requiresKYC: true },
  { value: "admin", label: "Organization / System Administrator", description: "Manage platform, audit KYC & deploy tactical surveillance", requiresKYC: true },
];

const INDIAN_STATES = [
  "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Gujarat", "Haryana",
  "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
  "Odisha", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana", "Uttar Pradesh", "Uttarakhand", "West Bengal"
];

export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuthStore();

  // Basic Information
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("citizen");

  // Official Institutional & KYC Details
  const [designation, setDesignation] = useState("");
  const [stationName, setStationName] = useState("");
  const [stationPhone, setStationPhone] = useState("");
  const [stateName, setStateName] = useState("Karnataka");
  const [cityName, setCityName] = useState("");
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);
  const [locatingGPS, setLocatingGPS] = useState(false);

  // File Uploads
  const [orgIdFile, setOrgIdFile] = useState<File | null>(null);
  const [aadhaarFile, setAadhaarFile] = useState<File | null>(null);

  // OTP Verification Step
  const [step, setStep] = useState<"form" | "otp" | "success">("form");
  const [otpCode, setOtpCode] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);

  // Loading & Error States
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successPayload, setSuccessPayload] = useState<any>(null);

  // Cooldown countdown effect
  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown((prev) => prev - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const isOfficial = role !== "citizen";

  // GPS Acquisition
  const handleDetectGPS = () => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");
      return;
    }
    setLocatingGPS(true);
    setError("");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(Number(pos.coords.latitude.toFixed(6)));
        setLongitude(Number(pos.coords.longitude.toFixed(6)));
        setLocatingGPS(false);
      },
      (err) => {
        setLocatingGPS(false);
        setError("Could not acquire GPS position. Please enter station coordinates or city manually.");
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const validateFile = (file: File | null, label: string): string | null => {
    if (!file) return `${label} is required.`;
    const allowed = ["application/pdf", "image/jpeg", "image/png", "image/webp"];
    if (!allowed.includes(file.type)) {
      return `${label} must be a PDF, JPEG, PNG, or WebP document.`;
    }
    if (file.size > 5 * 1024 * 1024) {
      return `${label} exceeds the maximum permitted limit of 5MB.`;
    }
    return null;
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (isOfficial) {
      const orgErr = validateFile(orgIdFile, role === "admin" ? "Company/Org ID Card" : role === "banker" ? "Bank Employee ID" : "Police/Investigator Badge");
      if (orgErr) {
        setError(orgErr);
        return;
      }
      const aadhaarErr = validateFile(aadhaarFile, "Aadhaar Card Document");
      if (aadhaarErr) {
        setError(aadhaarErr);
        return;
      }
    }

    setIsLoading(true);

    try {
      if (isOfficial) {
        const formData = new FormData();
        formData.append("email", email);
        formData.append("full_name", fullName);
        formData.append("password", password);
        formData.append("role", role === "banker" ? "bank_employee" : role);
        if (designation) formData.append("designation", designation);
        if (stationName) formData.append("station_name", stationName);
        if (stationPhone) formData.append("station_phone_number", stationPhone);
        if (cityName) formData.append("city", cityName);
        if (stateName) formData.append("state", stateName);
        if (latitude !== null) formData.append("latitude", latitude.toString());
        if (longitude !== null) formData.append("longitude", longitude.toString());
        if (orgIdFile) formData.append("org_id_file", orgIdFile);
        if (aadhaarFile) formData.append("aadhaar_file", aadhaarFile);

        await axios.post(api("/auth/register-official"), formData, {
          headers: { "Content-Type": "multipart/form-data" }
        });
      } else {
        await axios.post(api("/auth/register"), {
          email,
          full_name: fullName,
          role: "citizen",
          password,
        });
      }

      setStep("otp");
      setResendCooldown(60);
    } catch (err: any) {
      setError(formatApiError(err, "Registration failed. Please check your information and try again."));
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otpCode.trim().length !== 6) {
      setError("Please enter the 6-digit verification code sent to your email.");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const res = await axios.post(api("/auth/verify-registration-otp"), {
        email,
        otp: otpCode.trim(),
      });

      setSuccessPayload(res.data);
      if (res.data.access_token && res.data.user) {
        login(res.data.access_token, res.data.user);
      }
      setStep("success");
    } catch (err: any) {
      setError(formatApiError(err, "Invalid or expired verification code. Please try again."));
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendOTP = async () => {
    if (resendCooldown > 0) return;
    setError("");
    try {
      await axios.post(api("/auth/resend-registration-otp"), { email });
      setResendCooldown(60);
    } catch (err: any) {
      setError(formatApiError(err, "Could not resend verification code. Please try again later."));
    }
  };

  // 1. Success Screen
  if (step === "success") {
    const isCitizen = role === "citizen";
    return (
      <div className="rise-in text-center p-6 bg-surface rounded-2xl border border-line shadow-2xl space-y-5">
        <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto">
          <CheckCircle2 className="w-7 h-7 text-emerald-400" />
        </div>
        <h2 className="font-display font-semibold text-2xl tracking-tight text-ink">
          {isCitizen ? "Email Verified & Account Activated" : "KYC Submitted for Review"}
        </h2>
        <p className="text-sm text-ink-2 max-w-md mx-auto leading-relaxed">
          {isCitizen ? (
            "Your email has been verified and your Digital Rakshak account is fully active. You can now access your citizen dashboard, report incidents, and run OSINT threat scans."
          ) : (
            <>
              Your email <strong className="text-accent-text font-mono">{email}</strong> has been verified.
              Your official credentials, duty station location, and KYC documents have been submitted to platform administrators for authoritative verification. You will receive an official approval email once activated.
            </>
          )}
        </p>

        <div className="pt-3">
          {isCitizen ? (
            <Link href="/citizen">
              <Button variant="primary" size="lg" className="w-full sm:w-auto inline-flex items-center gap-2">
                <span>Go to Citizen Dashboard</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          ) : (
            <Link href="/auth/login">
              <Button variant="primary" size="lg" className="w-full sm:w-auto">
                Return to Sign In
              </Button>
            </Link>
          )}
        </div>
      </div>
    );
  }

  // 2. Email OTP Verification Screen
  if (step === "otp") {
    return (
      <div className="rise-in p-6 bg-surface rounded-2xl border border-line shadow-2xl space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mx-auto">
            <KeyRound className="w-6 h-6 text-cyan-400" />
          </div>
          <h2 className="font-display font-semibold text-xl tracking-tight text-ink">
            Verify Email Address
          </h2>
          <p className="text-xs text-ink-2 max-w-sm mx-auto">
            We sent a 6-digit cryptographic verification code to{" "}
            <span className="font-mono font-bold text-ink">{email}</span>. Please enter it below.
          </p>
        </div>

        <form onSubmit={handleVerifyOTP} className="space-y-4 max-w-sm mx-auto">
          <FormError>{error}</FormError>

          <div>
            <Label htmlFor="otpInput" className="text-center block text-xs font-semibold mb-2">
              6-Digit Verification Code
            </Label>
            <Input
              id="otpInput"
              type="text"
              maxLength={6}
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
              placeholder="123456"
              className="text-center font-mono text-2xl tracking-[0.5em] font-bold h-14"
              autoFocus
              required
            />
          </div>

          <Button type="submit" variant="primary" size="lg" loading={isLoading} className="w-full">
            Verify & Activate Account
          </Button>

          <div className="text-center pt-2">
            <button
              type="button"
              onClick={handleResendOTP}
              disabled={resendCooldown > 0}
              className="text-xs text-ink-2 hover:text-accent-text disabled:opacity-50 transition-colors inline-flex items-center gap-1.5"
            >
              <RefreshCw className={cn("w-3.5 h-3.5", resendCooldown > 0 && "animate-spin")} />
              <span>
                {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : "Didn't receive code? Resend OTP"}
              </span>
            </button>
          </div>
        </form>
      </div>
    );
  }

  // 3. Primary Registration Form
  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display font-semibold text-xl tracking-tight text-ink">
          Create Digital Rakshak Account
        </h2>
        <p className="text-sm text-ink-2 mt-1">
          Already registered?{" "}
          <Link href="/auth/login" className="text-accent-text font-medium underline underline-offset-4 hover:text-accent-hover">
            Sign in
          </Link>
        </p>
      </div>

      <form onSubmit={handleRegisterSubmit} className="space-y-5">
        <FormError>{error}</FormError>

        {/* Role Selector */}
        <fieldset>
          <legend className="block text-xs font-bold uppercase tracking-wider text-ink-2 mb-2">
            Select Your Role
          </legend>
          <div className="grid grid-cols-1 gap-2">
            {ROLES.map((r) => (
              <label
                key={r.value}
                className={cn(
                  "flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all duration-150",
                  role === r.value
                    ? "border-accent bg-accent/5 ring-1 ring-accent"
                    : "border-line bg-surface hover:border-ink-3"
                )}
              >
                <input
                  type="radio"
                  name="role"
                  value={r.value}
                  checked={role === r.value}
                  onChange={(e) => setRole(e.target.value)}
                  className="mt-1 accent-accent"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-ink">{r.label}</span>
                    {r.requiresKYC && (
                      <Badge tone="warning" className="text-[10px] px-1.5 py-0.2">
                        Official KYC & Approval
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-ink-2 mt-0.5">{r.description}</p>
                </div>
              </label>
            ))}
          </div>
        </fieldset>

        {/* Basic Credentials */}
        <div className="space-y-4 pt-2 border-t border-line/40">
          <div>
            <Label htmlFor="fullName">Full Name</Label>
            <Input
              id="fullName"
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Vikramaditya Rao"
              autoComplete="name"
            />
          </div>

          <div>
            <Label htmlFor="registerEmail">Official / Personal Email</Label>
            <Input
              id="registerEmail"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@domain.gov.in or you@example.com"
              autoComplete="email"
            />
            <p className="text-[11px] text-ink-3 mt-1">
              A 6-digit Email OTP verification code will be sent to this address.
            </p>
          </div>

          <div>
            <Label htmlFor="registerPassword">Password</Label>
            <Input
              id="registerPassword"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="8+ characters with at least 1 digit and 1 symbol"
              autoComplete="new-password"
            />
          </div>
        </div>

        {/* Institutional & Duty Location Section (Officials Only) */}
        {isOfficial && (
          <div className="space-y-4 pt-4 border-t border-line/40 rounded-xl bg-surface-2/40 p-4 border border-line/30">
            <div className="flex items-center gap-2 text-ink font-semibold text-sm">
              <Building className="w-4 h-4 text-cyan-400" />
              <span>Official Duty Jurisdiction & Contact</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label htmlFor="designation">Designation / Rank</Label>
                <Input
                  id="designation"
                  type="text"
                  required
                  value={designation}
                  onChange={(e) => setDesignation(e.target.value)}
                  placeholder={role === "police" ? "e.g. Inspector, Cyber Cell" : role === "banker" ? "e.g. Fraud Vigilance Manager" : "e.g. Security Director"}
                />
              </div>

              <div>
                <Label htmlFor="stationName">Station / Unit / Company</Label>
                <Input
                  id="stationName"
                  type="text"
                  required
                  value={stationName}
                  onChange={(e) => setStationName(e.target.value)}
                  placeholder={role === "police" ? "e.g. CID Cyber Crime PS" : role === "banker" ? "e.g. Central Fraud Operations" : "e.g. Digital Rakshak Org"}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <Label htmlFor="stationPhone">Official Desk Phone</Label>
                <Input
                  id="stationPhone"
                  type="tel"
                  required
                  value={stationPhone}
                  onChange={(e) => setStationPhone(e.target.value)}
                  placeholder="e.g. 080-22094498 or 1930"
                />
              </div>

              <div>
                <Label htmlFor="stateSelect">Jurisdiction State</Label>
                <select
                  id="stateSelect"
                  value={stateName}
                  onChange={(e) => setStateName(e.target.value)}
                  className="w-full h-10 px-3 rounded-control bg-surface border border-line text-sm text-ink focus:outline-none focus:border-accent"
                >
                  {INDIAN_STATES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              <div>
                <Label htmlFor="cityName">City / District</Label>
                <Input
                  id="cityName"
                  type="text"
                  required
                  value={cityName}
                  onChange={(e) => setCityName(e.target.value)}
                  placeholder="e.g. Bengaluru Urban"
                />
              </div>
            </div>

            {/* GPS Capture */}
            <div className="p-3 rounded-lg bg-surface border border-line/40 space-y-2">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <span className="text-xs font-medium text-ink flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-rose-400" />
                  <span>Duty Station GPS Coordinates</span>
                </span>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={handleDetectGPS}
                  loading={locatingGPS}
                  className="text-xs inline-flex items-center gap-1.5"
                >
                  <Compass className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Detect Duty Station GPS</span>
                </Button>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <Input
                  type="number"
                  step="any"
                  value={latitude !== null ? latitude : ""}
                  onChange={(e) => setLatitude(e.target.value ? parseFloat(e.target.value) : null)}
                  placeholder="Latitude (e.g. 12.9818)"
                  className="h-8 text-xs font-mono"
                />
                <Input
                  type="number"
                  step="any"
                  value={longitude !== null ? longitude : ""}
                  onChange={(e) => setLongitude(e.target.value ? parseFloat(e.target.value) : null)}
                  placeholder="Longitude (e.g. 77.5898)"
                  className="h-8 text-xs font-mono"
                />
              </div>
              <p className="text-[10px] text-ink-3">
                Used to plot your official post on the Tactical Response Map upon administrator verification.
              </p>
            </div>

            {/* Strict KYC Document Uploads */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center gap-2 text-ink font-semibold text-sm">
                <FileCheck2 className="w-4 h-4 text-emerald-400" />
                <span>Strict KYC Document Verification</span>
              </div>
              <p className="text-[11px] text-ink-3">
                Enterprise Zero-Trust Policy: Documents must be authentic PDF or image files under 5MB. Executables and spoofed signatures are strictly blocked.
              </p>

              {/* Document 1: Official Card */}
              <div className="p-3 rounded-lg border border-line/40 bg-surface">
                <Label className="text-xs font-semibold block mb-1">
                  1. {role === "admin" ? "Company / Organization ID Card" : role === "banker" ? "Bank Employee ID Card" : "Police Badge / Investigator Identity Card"}
                </Label>
                <input
                  type="file"
                  accept=".pdf,image/jpeg,image/png,image/webp"
                  required
                  onChange={(e) => setOrgIdFile(e.target.files?.[0] || null)}
                  className="block w-full text-xs text-ink-2 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-accent/10 file:text-accent-text hover:file:bg-accent/20 cursor-pointer"
                />
                {orgIdFile && (
                  <span className="text-[10px] text-emerald-400 mt-1 block">
                    ✓ {orgIdFile.name} ({(orgIdFile.size / 1024).toFixed(1)} KB)
                  </span>
                )}
              </div>

              {/* Document 2: Aadhaar Card */}
              <div className="p-3 rounded-lg border border-line/40 bg-surface">
                <Label className="text-xs font-semibold block mb-1">
                  2. Government Identity Card (Aadhaar Card)
                </Label>
                <input
                  type="file"
                  accept=".pdf,image/jpeg,image/png,image/webp"
                  required
                  onChange={(e) => setAadhaarFile(e.target.files?.[0] || null)}
                  className="block w-full text-xs text-ink-2 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-accent/10 file:text-accent-text hover:file:bg-accent/20 cursor-pointer"
                />
                {aadhaarFile && (
                  <span className="text-[10px] text-emerald-400 mt-1 block">
                    ✓ {aadhaarFile.name} ({(aadhaarFile.size / 1024).toFixed(1)} KB)
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        <Button type="submit" variant="primary" size="lg" loading={isLoading} className="w-full">
          {isOfficial ? "Submit Application & Verify Email OTP" : "Continue to Email Verification"}
        </Button>
      </form>
    </div>
  );
}
