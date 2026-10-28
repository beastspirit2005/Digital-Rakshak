"use client";

import { useState, useEffect } from "react";
import { api, formatApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useToast } from "@/components/ui/toast";
import {
  UserCircle,
  ShieldCheck,
  Building,
  KeyRound,
  MapPin,
  Compass,
  Phone,
  Mail,
  Lock,
  Save,
  CheckCircle2,
  Sparkles,
  FileText,
  BadgeAlert,
  ShieldAlert
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Label, FormError } from "@/components/ui/field";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const INDIAN_STATES = [
  "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Gujarat", "Haryana",
  "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
  "Odisha", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana", "Uttar Pradesh", "Uttarakhand", "West Bengal"
];

export default function AccountSettingsPage() {
  const { token, user: authUser, updateUser } = useAuthStore();
  const toast = useToast();

  const [activeTab, setActiveTab] = useState<"profile" | "security" | "privacy">("profile");
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [locatingGPS, setLocatingGPS] = useState(false);

  // Form Fields
  const [profile, setProfile] = useState({
    id: "",
    email: "",
    full_name: "",
    role: "citizen",
    station_phone_number: "",
    city: "",
    state: "Karnataka",
    station_name: "",
    badge_number: "",
    designation: "",
    latitude: null as number | null,
    longitude: null as number | null,
    is_verified: false,
    is_approved: false,
    is_pro: false,
  });

  // Password Fields
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");

  // DPDP Consents
  const [consents, setConsents] = useState({
    ai_threat_analysis: true,
    telemetry_monitoring: true,
    syndicate_intel_sharing: true,
    communication_alerts: true,
  });
  const [savingConsent, setSavingConsent] = useState(false);

  // Load User Profile & Consents
  useEffect(() => {
    if (!token) return;

    const fetchProfile = async () => {
      try {
        const res = await fetch(api("/users/me"), {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setProfile({
            id: data.id,
            email: data.email,
            full_name: data.full_name || "",
            role: data.role || "citizen",
            station_phone_number: data.station_phone_number || "",
            city: data.city || "",
            state: data.state || "Karnataka",
            station_name: data.station_name || "",
            badge_number: data.badge_number || "",
            designation: data.designation || "",
            latitude: data.latitude,
            longitude: data.longitude,
            is_verified: data.is_verified,
            is_approved: data.is_approved,
            is_pro: data.is_pro,
          });
        }

        // Fetch DPDP Consents
        const consentRes = await fetch(api("/users/me/consent"), {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (consentRes.ok) {
          const cData = await consentRes.json();
          if (cData.consents) {
            setConsents({
              ai_threat_analysis: cData.consents.ai_threat_analysis ?? true,
              telemetry_monitoring: cData.consents.telemetry_monitoring ?? true,
              syndicate_intel_sharing: cData.consents.syndicate_intel_sharing ?? true,
              communication_alerts: cData.consents.communication_alerts ?? true,
            });
          }
        }
      } catch (err) {
        console.error("Failed to load profile", err);
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [token]);

  // GPS Acquisition
  const handleDetectGPS = () => {
    if (!navigator.geolocation) {
      toast("warning", "Geolocation is not supported by your browser.");
      return;
    }
    setLocatingGPS(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setProfile((prev) => ({
          ...prev,
          latitude: Number(pos.coords.latitude.toFixed(6)),
          longitude: Number(pos.coords.longitude.toFixed(6)),
        }));
        setLocatingGPS(false);
        toast("success", "Current GPS coordinates detected.");
      },
      (err) => {
        setLocatingGPS(false);
        toast("danger", "Could not detect GPS location.");
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  // Save Profile Changes
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);

    try {
      const res = await fetch(api("/users/me"), {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          full_name: profile.full_name,
          station_phone_number: profile.station_phone_number,
          city: profile.city,
          state: profile.state,
          station_name: profile.station_name,
          badge_number: profile.badge_number,
          designation: profile.designation,
          latitude: profile.latitude,
          longitude: profile.longitude,
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to update profile");
      }

      const data = await res.json();
      if (data.user) {
        updateUser({
          full_name: data.user.full_name,
          station_phone_number: data.user.station_phone_number
        });
      }

      toast("success", "Profile updated successfully. Map coordinates updated in real time.");
    } catch (err: any) {
      toast("danger", err.message || "Failed to update profile");
    } finally {
      setSavingProfile(false);
    }
  };

  // Change Password
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError("");

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters long.");
      return;
    }

    setChangingPassword(true);

    try {
      const res = await fetch(api("/users/me/change-password"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to change password");
      }

      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast("success", "Password updated successfully.");
    } catch (err: any) {
      setPasswordError(err.message || "Failed to update password");
    } finally {
      setChangingPassword(false);
    }
  };

  // Toggle DPDP Consents
  const handleToggleConsent = async (key: keyof typeof consents) => {
    const updated = { ...consents, [key]: !consents[key] };
    setConsents(updated);
    setSavingConsent(true);

    try {
      await fetch(api("/users/me/consent"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(updated)
      });
      toast("success", "DPDP consent preferences updated.");
    } catch (err) {
      toast("danger", "Could not save consent preference.");
    } finally {
      setSavingConsent(false);
    }
  };

  const isOfficial = ["police", "cyber_cell", "bank_employee", "admin"].includes(profile.role);

  return (
    <div className="space-y-6 pb-12">
      {/* Header Profile Summary */}
      <div className="rounded-2xl bg-surface border border-line p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center font-mono text-2xl font-bold text-accent-text">
            {profile.full_name ? profile.full_name.slice(0, 2).toUpperCase() : profile.email.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="font-display font-semibold text-xl text-ink">
                {profile.full_name || profile.email}
              </h1>
              <Badge
                tone={
                  profile.role === "admin"
                    ? "danger"
                    : profile.role === "police" || profile.role === "cyber_cell"
                    ? "accent"
                    : "neutral"
                }
                className="capitalize text-xs font-semibold"
              >
                {profile.role.replace("_", " ")}
              </Badge>
              {profile.is_verified && (
                <Badge tone="success" className="text-[10px] inline-flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Email Verified</span>
                </Badge>
              )}
              {profile.is_pro && (
                <Badge tone="accent" className="text-[10px] inline-flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  <span>Pro Shield</span>
                </Badge>
              )}
            </div>
            <p className="text-xs text-ink-2 mt-1 font-mono">
              {profile.email} {profile.station_name ? `• ${profile.station_name}` : ""}
            </p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1 bg-surface-2 p-1 rounded-xl border border-line self-stretch md:self-auto">
          <button
            onClick={() => setActiveTab("profile")}
            className={cn(
              "flex-1 md:flex-none px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all",
              activeTab === "profile" ? "bg-surface text-ink shadow-sm" : "text-ink-2 hover:text-ink"
            )}
          >
            Profile & Duty
          </button>
          <button
            onClick={() => setActiveTab("security")}
            className={cn(
              "flex-1 md:flex-none px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all",
              activeTab === "security" ? "bg-surface text-ink shadow-sm" : "text-ink-2 hover:text-ink"
            )}
          >
            Security
          </button>
          <button
            onClick={() => setActiveTab("privacy")}
            className={cn(
              "flex-1 md:flex-none px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all",
              activeTab === "privacy" ? "bg-surface text-ink shadow-sm" : "text-ink-2 hover:text-ink"
            )}
          >
            DPDP Consents
          </button>
        </div>
      </div>

      {/* TAB 1: Profile & Duty Station */}
      {activeTab === "profile" && (
        <form onSubmit={handleSaveProfile} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Personal / Account Info */}
            <div className="rounded-2xl bg-surface border border-line p-5 space-y-4 shadow-sm">
              <div className="flex items-center gap-2 text-ink font-semibold text-sm border-b border-line/40 pb-3">
                <UserCircle className="w-4 h-4 text-accent-text" />
                <span>Personal Information</span>
              </div>

              <div>
                <Label htmlFor="accountName">Full Name</Label>
                <Input
                  id="accountName"
                  value={profile.full_name}
                  onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                  placeholder="Your Full Name"
                  required
                />
              </div>

              <div>
                <Label htmlFor="accountEmail">Email Address</Label>
                <Input
                  id="accountEmail"
                  value={profile.email}
                  disabled
                  className="bg-surface-2 text-ink-2 font-mono text-xs cursor-not-allowed"
                />
                <span className="text-[10px] text-ink-3 mt-1 block">
                  Email address is cryptographically verified and cannot be changed directly.
                </span>
              </div>

              <div>
                <Label htmlFor="accountPhone">
                  {isOfficial ? "Official Desk / Station Phone" : "Primary / Emergency Phone"}
                </Label>
                <Input
                  id="accountPhone"
                  type="tel"
                  value={profile.station_phone_number}
                  onChange={(e) => setProfile({ ...profile, station_phone_number: e.target.value })}
                  placeholder="e.g. 080-22094498 or +91 98765 43210"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="stateSelect">State / Territory</Label>
                  <select
                    id="stateSelect"
                    value={profile.state}
                    onChange={(e) => setProfile({ ...profile, state: e.target.value })}
                    className="w-full h-10 px-3 rounded-control bg-surface border border-line text-sm text-ink focus:outline-none focus:border-accent"
                  >
                    {INDIAN_STATES.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <Label htmlFor="accountCity">City / District</Label>
                  <Input
                    id="accountCity"
                    value={profile.city}
                    onChange={(e) => setProfile({ ...profile, city: e.target.value })}
                    placeholder="e.g. Bengaluru"
                  />
                </div>
              </div>
            </div>

            {/* Official Duty Station & Tactical Geospatial Position */}
            {isOfficial ? (
              <div className="rounded-2xl bg-surface border border-line p-5 space-y-4 shadow-sm">
                <div className="flex items-center gap-2 text-ink font-semibold text-sm border-b border-line/40 pb-3">
                  <Building className="w-4 h-4 text-cyan-400" />
                  <span>Duty Station & Tactical Radar Coordinates</span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label htmlFor="stationName">Station / Branch Name</Label>
                    <Input
                      id="stationName"
                      value={profile.station_name}
                      onChange={(e) => setProfile({ ...profile, station_name: e.target.value })}
                      placeholder="e.g. CID Cyber Crime Police Station"
                    />
                  </div>

                  <div>
                    <Label htmlFor="designation">Designation / Title</Label>
                    <Input
                      id="designation"
                      value={profile.designation}
                      onChange={(e) => setProfile({ ...profile, designation: e.target.value })}
                      placeholder="e.g. Inspector, Cyber Cell"
                    />
                  </div>
                </div>

                {/* GPS Coordinates */}
                <div className="p-3.5 rounded-xl bg-surface-2/60 border border-line space-y-3">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <span className="text-xs font-semibold text-ink flex items-center gap-1.5">
                      <MapPin className="w-4 h-4 text-rose-400" />
                      <span>Tactical Map Anchor Coordinates</span>
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
                      <span>Detect Current GPS</span>
                    </Button>
                  </div>

                  <div className="grid grid-cols-2 gap-2 font-mono">
                    <div>
                      <span className="text-[10px] text-ink-3 block mb-1">Latitude</span>
                      <Input
                        type="number"
                        step="any"
                        value={profile.latitude !== null ? profile.latitude : ""}
                        onChange={(e) => setProfile({ ...profile, latitude: e.target.value ? parseFloat(e.target.value) : null })}
                        placeholder="e.g. 12.9818"
                        className="h-9 text-xs font-mono"
                      />
                    </div>
                    <div>
                      <span className="text-[10px] text-ink-3 block mb-1">Longitude</span>
                      <Input
                        type="number"
                        step="any"
                        value={profile.longitude !== null ? profile.longitude : ""}
                        onChange={(e) => setProfile({ ...profile, longitude: e.target.value ? parseFloat(e.target.value) : null })}
                        placeholder="e.g. 77.5898"
                        className="h-9 text-xs font-mono"
                      />
                    </div>
                  </div>
                  <p className="text-[11px] text-ink-3 leading-relaxed">
                    Updating coordinates immediately repositions your official duty marker on the Administrator Tactical Map and calibrates proximity sorting.
                  </p>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl bg-surface border border-line p-5 space-y-4 shadow-sm flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 text-ink font-semibold text-sm border-b border-line/40 pb-3">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>Citizen Cyber Protection Status</span>
                  </div>
                  <div className="space-y-3 pt-3">
                    <p className="text-xs text-ink-2 leading-relaxed">
                      Your citizen account is registered with Digital Rakshak Sovereign Defense.
                      Setting your accurate city and state ensures you receive real-time, localized threat advisories whenever a phishing syndicate or digital arrest racket operates in your jurisdiction.
                    </p>
                    <div className="p-3 rounded-xl bg-surface-2 border border-line/50 text-xs space-y-1">
                      <span className="font-semibold text-ink block">National Cyber Helpline</span>
                      <p className="text-ink-2 font-mono">
                        Call <strong className="text-accent-text">1930</strong> for immediate Golden Hour transaction containment.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300">
                  Account Verified & Sovereign Shield Active.
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-end pt-2">
            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={savingProfile}
              className="inline-flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              <span>Save Profile Changes</span>
            </Button>
          </div>
        </form>
      )}

      {/* TAB 2: Security & Password */}
      {activeTab === "security" && (
        <form onSubmit={handleChangePassword} className="max-w-md mx-auto space-y-4 rounded-2xl bg-surface border border-line p-6 shadow-sm">
          <div className="flex items-center gap-2 text-ink font-semibold text-sm border-b border-line/40 pb-3">
            <KeyRound className="w-4 h-4 text-cyan-400" />
            <span>Change Account Password</span>
          </div>

          <FormError>{passwordError}</FormError>

          <div>
            <Label htmlFor="currentPwd">Current Password</Label>
            <Input
              id="currentPwd"
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="••••••••••••"
              autoComplete="current-password"
            />
          </div>

          <div>
            <Label htmlFor="newPwd">New Password</Label>
            <Input
              id="newPwd"
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="8+ characters with digit & symbol"
              autoComplete="new-password"
            />
          </div>

          <div>
            <Label htmlFor="confirmPwd">Confirm New Password</Label>
            <Input
              id="confirmPwd"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••••••"
              autoComplete="new-password"
            />
          </div>

          <Button type="submit" variant="primary" size="lg" loading={changingPassword} className="w-full">
            Update Password
          </Button>
        </form>
      )}

      {/* TAB 3: DPDP Act 2023 Consents */}
      {activeTab === "privacy" && (
        <div className="max-w-2xl mx-auto rounded-2xl bg-surface border border-line p-6 space-y-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-line/40 pb-3">
            <div className="flex items-center gap-2 text-ink font-semibold text-sm">
              <Lock className="w-4 h-4 text-amber-400" />
              <span>DPDP Act 2023 Consent & Data Processing Control</span>
            </div>
            <Badge tone="success" className="text-[10px]">
              DPDP Compliant
            </Badge>
          </div>

          <p className="text-xs text-ink-2 leading-relaxed">
            In accordance with India&apos;s Digital Personal Data Protection Act (DPDP Act, 2023), you hold sovereign rights over non-essential telemetry and syndicate intel telemetry. All changes are immutably signed to audit logs.
          </p>

          <div className="space-y-3">
            {[
              {
                key: "ai_threat_analysis" as const,
                title: "AI Threat & Scam Pattern Analysis",
                desc: "Allows automated heuristic and Qwen model analysis on submitted scam statements to identify predatory techniques."
              },
              {
                key: "syndicate_intel_sharing" as const,
                title: "De-identified Syndicate Intelligence Sharing",
                desc: "Shares anonymized mule accounts, suspicious domains, and phone hashes with Law Enforcement and Banking nodal desks."
              },
              {
                key: "telemetry_monitoring" as const,
                title: "Fraud Velocity & Telemetry Monitoring",
                desc: "Permits telemetry correlation to detect coordinated distributed attacks across Indian financial institutions."
              },
              {
                key: "communication_alerts" as const,
                title: "Operational SMS & Email Advisory Alerts",
                desc: "Permits urgent security notices and case status dispatches."
              }
            ].map((item) => (
              <div
                key={item.key}
                className="flex items-start justify-between p-3.5 rounded-xl border border-line bg-surface-2/40 gap-4"
              >
                <div>
                  <h4 className="text-xs font-semibold text-ink">{item.title}</h4>
                  <p className="text-[11px] text-ink-2 mt-0.5">{item.desc}</p>
                </div>
                <input
                  type="checkbox"
                  checked={consents[item.key]}
                  onChange={() => handleToggleConsent(item.key)}
                  disabled={savingConsent}
                  className="mt-1 w-4 h-4 accent-accent rounded cursor-pointer"
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
