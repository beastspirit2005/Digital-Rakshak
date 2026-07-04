"use client";


import { api } from "@/lib/api";
import React, { useState, useEffect } from "react";
import { Settings, Cpu, Mail, Server, ShieldCheck, Zap, Loader2, CheckCircle2, Wifi, WifiOff } from "lucide-react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";

export default function AdminSettingsPage() {
  const [forceLocal, setForceLocal] = useState(false);
  const [aiMode, setAiMode] = useState<"auto" | "gemini" | "ollama" | "both">("auto");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState(0);
  const [smtpUser, setSmtpUser] = useState("");
  const [ollamaHost, setOllamaHost] = useState("");
  const [geminiConfigured, setGeminiConfigured] = useState(false);
  const { token } = useAuthStore();

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await axios.get(api("/admin/settings"), {
          headers: { Authorization: `Bearer ${token}` }
        });
        setForceLocal(res.data.force_local_inference);
        setAiMode(res.data.default_ai_mode);
        setSmtpHost(res.data.smtp_host);
        setSmtpPort(res.data.smtp_port);
        setSmtpUser(res.data.smtp_user);
        setOllamaHost(res.data.ollama_host);
        setGeminiConfigured(res.data.gemini_configured);
      } catch (err) {
        console.error("Failed to load settings", err);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchSettings();
  }, [token]);

  const saveSettings = async (updates: { force_local_inference?: boolean; default_ai_mode?: string }) => {
    setSaving(true);
    setSaved(false);
    try {
      await axios.put(api("/admin/settings"), updates, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error("Failed to save settings", err);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleLocal = () => {
    const newVal = !forceLocal;
    setForceLocal(newVal);
    saveSettings({ force_local_inference: newVal });
  };

  const handleModeChange = (mode: "auto" | "gemini" | "ollama" | "both") => {
    setAiMode(mode);
    saveSettings({ default_ai_mode: mode });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary/10 text-primary rounded-xl">
            <Settings className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">System Settings</h1>
            <p className="text-muted-foreground">Configure global system preferences and AI behavior.</p>
          </div>
        </div>
        {(saving || saved) && (
          <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${saved ? 'bg-green-500/10 text-green-500' : 'bg-primary/10 text-primary'}`}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            {saving ? "Saving..." : "Saved!"}
          </div>
        )}
      </div>

      <div className="space-y-6">
        {/* AI Configuration Section */}
        <div className="glass-panel rounded-2xl overflow-hidden">
          <div className="p-6 border-b border-border bg-muted/30">
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <Cpu className="w-5 h-5 text-primary" />
              AI &amp; Inference Settings
            </h2>
            <p className="text-sm text-muted-foreground mt-1">Manage how the AI assistant processes requests.</p>
          </div>
          
          <div className="p-6 space-y-8">
            {/* Status indicators */}
            <div className="grid grid-cols-2 gap-4">
              <div className={`flex items-center gap-3 p-4 rounded-xl border ${geminiConfigured ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
                {geminiConfigured ? <Wifi className="w-5 h-5 text-green-500" /> : <WifiOff className="w-5 h-5 text-red-500" />}
                <div>
                  <p className="text-sm font-medium text-foreground">Google Gemini</p>
                  <p className="text-xs text-muted-foreground">{geminiConfigured ? 'API key configured' : 'Not configured'}</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-4 rounded-xl border border-blue-500/30 bg-blue-500/5">
                <Server className="w-5 h-5 text-blue-500" />
                <div>
                  <p className="text-sm font-medium text-foreground">Ollama (Local)</p>
                  <p className="text-xs text-muted-foreground">{ollamaHost}</p>
                </div>
              </div>
            </div>

            {/* Toggle: Force Local */}
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-medium text-foreground flex items-center gap-2">
                  Force Local Inference (Ollama)
                  <ShieldCheck className="w-4 h-4 text-green-500" />
                </h3>
                <p className="text-sm text-muted-foreground mt-1 max-w-lg">
                  When enabled, all AI processing will be forced to use local models. 
                  Data will not be sent to external APIs like Google Gemini.
                </p>
              </div>
              <button 
                onClick={handleToggleLocal}
                className={`relative inline-flex h-7 w-12 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${forceLocal ? 'bg-green-500' : 'bg-muted'}`}
              >
                <span className={`pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${forceLocal ? 'translate-x-5' : 'translate-x-0'}`} />
              </button>
            </div>

            <hr className="border-border" />

            {/* Select: Default AI Mode */}
            <div>
              <h3 className="text-base font-medium text-foreground flex items-center gap-2 mb-3">
                Default AI Mode
                <Zap className="w-4 h-4 text-amber-500" />
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                {([
                  { id: "auto" as const, label: "Auto", desc: "Gemini first, Ollama fallback", emoji: "🔄" },
                  { id: "gemini" as const, label: "Gemini", desc: "Cloud-based, high performance", emoji: "☁️" },
                  { id: "ollama" as const, label: "Ollama", desc: "Local, privacy focused", emoji: "🔒" },
                  { id: "both" as const, label: "Hybrid", desc: "Run both in parallel", emoji: "⚡" },
                ]).map(mode => (
                  <button
                    key={mode.id}
                    onClick={() => handleModeChange(mode.id)}
                    disabled={forceLocal}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      forceLocal ? 'opacity-50 cursor-not-allowed border-border bg-muted/20' :
                      aiMode === mode.id 
                        ? 'border-primary bg-primary/10 ring-1 ring-primary' 
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <div className="text-lg mb-1">{mode.emoji}</div>
                    <div className="font-semibold text-foreground">{mode.label}</div>
                    <div className="text-xs text-muted-foreground mt-1">{mode.desc}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Email/SMTP Settings */}
        <div className="glass-panel rounded-2xl overflow-hidden">
          <div className="p-6 border-b border-border bg-muted/30">
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <Mail className="w-5 h-5 text-muted-foreground" />
              SMTP Configuration
              <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-full">Read-only</span>
            </h2>
            <p className="text-sm text-muted-foreground mt-1">Email server settings are configured via environment variables.</p>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-2 flex items-center gap-2">
                  <Server className="w-4 h-4" />
                  SMTP Host
                </label>
                <input
                  type="text"
                  readOnly
                  value={smtpHost}
                  className="block w-full rounded-lg border border-border bg-muted/50 text-muted-foreground sm:text-sm px-4 py-2.5 cursor-not-allowed"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-2">
                  SMTP Port
                </label>
                <input
                  type="text"
                  readOnly
                  value={smtpPort}
                  className="block w-full rounded-lg border border-border bg-muted/50 text-muted-foreground sm:text-sm px-4 py-2.5 cursor-not-allowed"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-muted-foreground mb-2">
                  SMTP Username
                </label>
                <input
                  type="text"
                  readOnly
                  value={smtpUser}
                  className="block w-full rounded-lg border border-border bg-muted/50 text-muted-foreground sm:text-sm px-4 py-2.5 cursor-not-allowed"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
