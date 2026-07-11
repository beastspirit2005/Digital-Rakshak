"use client";

import { api } from "@/lib/api";
import React, { useState, useEffect } from "react";
import { Activity, Fingerprint, Network, MapPin, CheckCircle2, Loader2, Wifi, WifiOff, Server } from "lucide-react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { cn } from "@/lib/utils";
import { Card, CardHeader, Inset } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";
import { Input, Label } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { Rise } from "@/components/ui/motion";

const AI_MODES = [
  { id: "auto" as const, label: "Platform default", desc: "Specialized native models with local reasoning" },
  { id: "groq" as const, label: "Cloud fast", desc: "Groq LPU running Llama 3 models" },
  { id: "ollama" as const, label: "Strict offline", desc: "Local models only, nothing leaves the server" },
  { id: "both" as const, label: "Hybrid", desc: "Run both pipelines for A/B comparison" },
];

const AGENTS = [
  {
    name: "ThreatAnalysisAgent",
    model: "Rakshak-Text v1.0",
    icon: Activity,
    tags: ["Scam classification", "Threat score", "Confidence", "Ontology mapping"],
  },
  {
    name: "BehaviourAgent",
    model: "Rakshak-Behaviour v1.0",
    icon: Fingerprint,
    tags: ["Attack DNA", "Behaviour fingerprint", "Social engineering", "Psychological analysis"],
  },
  {
    name: "CampaignAgent",
    model: "Rakshak-Link & Rakshak-Embedding",
    icon: Network,
    tags: ["Similarity", "Duplicate detection", "Campaign clustering"],
  },
  {
    name: "GeoAgent",
    model: "Geo Resolver & PostGIS",
    icon: MapPin,
    tags: ["NER extraction", "Geo resolution", "Threat density", "Spread tracking"],
  },
];

export default function AdminSettingsPage() {
  const [forceLocal, setForceLocal] = useState(false);
  const [aiMode, setAiMode] = useState<"auto" | "groq" | "ollama" | "both">("auto");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState(0);
  const [smtpUser, setSmtpUser] = useState("");
  const [ollamaHost, setOllamaHost] = useState("");
  const [groqConfigured, setGroqConfigured] = useState(false);
  const { token } = useAuthStore();

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await axios.get(api("/admin/settings"), {
          headers: { Authorization: `Bearer ${token}` },
        });
        setForceLocal(res.data.force_local_inference);
        setAiMode(res.data.default_ai_mode);
        setSmtpHost(res.data.smtp_host);
        setSmtpPort(res.data.smtp_port);
        setSmtpUser(res.data.smtp_user);
        setOllamaHost(res.data.ollama_host);
        setGroqConfigured(res.data.groq_configured);
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
        headers: { Authorization: `Bearer ${token}` },
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

  const handleModeChange = (mode: "auto" | "groq" | "ollama" | "both") => {
    setAiMode(mode);
    saveSettings({ default_ai_mode: mode });
  };

  if (loading) {
    return (
      <div className="space-y-6 pt-2">
        <PageHeader title="Platform settings" sub="Global preferences and AI behavior." />
        <Skeleton className="h-72 rounded-card" />
        <Skeleton className="h-56 rounded-card" />
      </div>
    );
  }

  return (
    <div className="space-y-6 pt-2 max-w-4xl">
      <Rise>
        <PageHeader
          title="Platform settings"
          sub="Global preferences and AI behavior."
          actions={
            (saving || saved) && (
              <Badge tone={saved ? "success" : "neutral"}>
                {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                {saving ? "Saving…" : "Saved"}
              </Badge>
            )
          }
        />
      </Rise>

      <Rise index={1}>
        <Card>
          <CardHeader title="Inference" sub="How the AI core processes requests." />
          <div className="px-6 pb-6 space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Inset className="flex items-center gap-3 p-4">
                {groqConfigured ? (
                  <Wifi className="w-4 h-4 text-success shrink-0" />
                ) : (
                  <WifiOff className="w-4 h-4 text-danger shrink-0" />
                )}
                <div>
                  <p className="text-sm font-medium text-ink">Groq LPU (cloud)</p>
                  <p className="text-xs text-ink-2">
                    {groqConfigured ? "API key configured" : "Not configured"}
                  </p>
                </div>
              </Inset>
              <Inset className="flex items-center gap-3 p-4">
                <Server className="w-4 h-4 text-ink-2 shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-ink">Ollama (local)</p>
                  <p className="text-xs text-ink-2 truncate">{ollamaHost}</p>
                </div>
              </Inset>
            </div>

            <div className="flex items-center justify-between gap-6">
              <div>
                <h3 className="text-sm font-medium text-ink">Force local inference</h3>
                <p className="text-sm text-ink-2 mt-0.5 max-w-lg">
                  Keep every AI request on this server. Nothing is sent to external APIs.
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={forceLocal}
                onClick={handleToggleLocal}
                className={cn(
                  "relative inline-flex h-6 w-11 shrink-0 rounded-pill transition-colors duration-150",
                  forceLocal ? "bg-accent" : "bg-surface-3"
                )}
              >
                <span
                  className={cn(
                    "pointer-events-none inline-block h-5 w-5 mt-0.5 ml-0.5 rounded-pill bg-surface shadow-card transition-transform duration-150",
                    forceLocal && "translate-x-5"
                  )}
                />
              </button>
            </div>

            <div>
              <h3 className="text-sm font-medium text-ink mb-3">Default AI mode</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {AI_MODES.map((mode) => (
                  <button
                    key={mode.id}
                    onClick={() => handleModeChange(mode.id)}
                    disabled={forceLocal}
                    className={cn(
                      "p-4 rounded-control border text-left transition-colors duration-150",
                      forceLocal
                        ? "opacity-50 cursor-not-allowed border-line"
                        : aiMode === mode.id
                          ? "border-accent-text bg-surface-2"
                          : "border-line hover:border-ink-3"
                    )}
                  >
                    <p className="text-sm font-medium text-ink">{mode.label}</p>
                    <p className="text-xs text-ink-2 mt-1">{mode.desc}</p>
                  </button>
                ))}
              </div>
              {forceLocal && (
                <p className="text-xs text-ink-3 mt-2">
                  Mode selection is disabled while local inference is forced.
                </p>
              )}
            </div>
          </div>
        </Card>
      </Rise>

      <Rise index={2}>
        <Card>
          <CardHeader
            title="Specialist agents"
            sub="Every case runs through these engines before fusion."
            action={<Badge tone="lilac">MAIF v10.0</Badge>}
          />
          <div className="px-6 pb-6 grid grid-cols-1 md:grid-cols-2 gap-3">
            {AGENTS.map((agent) => {
              const Icon = agent.icon;
              return (
                <Inset key={agent.name} className="p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="text-sm font-medium text-ink">{agent.name}</h3>
                      <p className="text-xs text-ink-2 mt-0.5">{agent.model}</p>
                    </div>
                    <Icon className="w-4 h-4 text-ink-3 shrink-0" />
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {agent.tags.map((tag) => (
                      <Badge key={tag}>{tag}</Badge>
                    ))}
                  </div>
                </Inset>
              );
            })}
          </div>
        </Card>
      </Rise>

      <Rise index={3}>
        <Card>
          <CardHeader
            title="Email delivery"
            sub="SMTP is configured through environment variables."
            action={<Badge>Read-only</Badge>}
          />
          <div className="px-6 pb-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="smtpHost">SMTP host</Label>
              <Input id="smtpHost" readOnly value={smtpHost} className="text-ink-2" />
            </div>
            <div>
              <Label htmlFor="smtpPort">SMTP port</Label>
              <Input id="smtpPort" readOnly value={smtpPort} className="text-ink-2" />
            </div>
            <div className="sm:col-span-2">
              <Label htmlFor="smtpUser">SMTP username</Label>
              <Input id="smtpUser" readOnly value={smtpUser} className="text-ink-2" />
            </div>
          </div>
        </Card>
      </Rise>
    </div>
  );
}
