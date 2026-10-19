"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Building2, 
  Key, 
  Activity, 
  BarChart3, 
  Plus, 
  Trash2, 
  Copy, 
  Check, 
  AlertCircle, 
  Terminal, 
  Radio, 
  ShieldAlert, 
  CheckCircle2, 
  Clock, 
  CreditCard,
  Code2,
  Play
} from "lucide-react";

import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { Rise } from "@/components/ui/motion";
import { useToast } from "@/components/ui/toast";
import { LoadingOverlay } from "@/components/ui/loading-overlay";

interface OrgProfile {
  org_id: string;
  name: string;
  slug: string;
  tier: string;
  is_active: boolean;
  subscription_status?: string;
  plan_code?: string;
}

interface ApiKeyItem {
  key_id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string;
}

interface QuotaUsage {
  org_id: string;
  period: string;
  events_processed: number;
  monthly_limit: number;
  quota_remaining: number;
  usage_pct: number;
  is_over_limit: boolean;
}

export default function BusinessEnterprisePortal() {
  const { user, token } = useAuthStore();
  const pushToast = useToast();

  const [activeTab, setActiveTab] = useState<"keys" | "usage" | "integration" | "stream">("keys");
  const [activeApiKey, setActiveApiKey] = useState<string>("");
  const [org, setOrg] = useState<OrgProfile | null>(null);
  const [keysList, setKeysList] = useState<ApiKeyItem[]>([]);
  const [quota, setQuota] = useState<QuotaUsage | null>(null);
  const [loading, setLoading] = useState(true);

  // New Key Modal
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [createdPlaintextKey, setCreatedPlaintextKey] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);
  const [creatingKey, setCreatingKey] = useState(false);
  const [testIngesting, setTestIngesting] = useState(false);

  // Code sample tab
  const [snippetLanguage, setSnippetLanguage] = useState<"curl" | "python" | "node">("curl");

  // Load B2B data using stored API key or logged in user session
  const loadB2BData = async (keyToUse?: string) => {
    setLoading(true);
    try {
      const headers: any = {};
      const effectiveKey = keyToUse !== undefined ? keyToUse : activeApiKey;
      if (effectiveKey && effectiveKey.trim()) {
        headers["x-api-key"] = effectiveKey.trim();
      }
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const [orgRes, keysRes, usageRes] = await Promise.all([
        axios.get(api("/b2b/org"), { headers }),
        axios.get(api("/b2b/keys"), { headers }),
        axios.get(api("/b2b/usage"), { headers })
      ]);

      setOrg(orgRes.data);
      setKeysList(keysRes.data);
      setQuota(usageRes.data);
    } catch (err: any) {
      if (keyToUse) {
        pushToast("danger", err.response?.data?.detail || "Could not authenticate with this API key.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleTestIngest = async () => {
    setTestIngesting(true);
    try {
      const headers: any = {};
      if (activeApiKey) headers["x-api-key"] = activeApiKey;
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const sampleBatch = [
        {
          event_type: "auth_bruteforce",
          source_ip: "185.220.101.45",
          severity: "high",
          details: { failed_attempts: 14, user_agent: "python-requests/2.28.1" }
        },
        {
          event_type: "phishing_domain_lookup",
          source_ip: "103.21.244.0",
          severity: "critical",
          details: { domain: "secure-kyc-verification.top", matched_c2: true }
        }
      ];

      await axios.post(
        api("/b2b/events/ingest"),
        { events: sampleBatch },
        { headers }
      );
      pushToast("success", "Telemetry batch ingested into Redis Streams! Quota updated.");
      loadB2BData(activeApiKey);
    } catch (err: any) {
      pushToast("danger", err.response?.data?.detail || "Batch event ingestion failed.");
    } finally {
      setTestIngesting(false);
    }
  };

  useEffect(() => {
    const savedKey = localStorage.getItem("dr_b2b_active_key") || "";
    if (savedKey) {
      setActiveApiKey(savedKey);
      loadB2BData(savedKey);
    } else {
      loadB2BData("");
    }
  }, [token]);

  const handleCreateApiKey = async () => {
    if (!newKeyName.trim()) {
      pushToast("warning", "Please enter a key label or system name.");
      return;
    }
    setCreatingKey(true);
    try {
      const headers: any = {};
      if (activeApiKey) headers["x-api-key"] = activeApiKey;
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await axios.post(
        api("/b2b/keys"),
        { name: newKeyName.trim(), scopes: ["events:write", "alerts:read"] },
        { headers }
      );

      setCreatedPlaintextKey(res.data.plaintext_key);
      pushToast("success", "API key generated! Copy your API key now. It will not be shown again.");
      loadB2BData(activeApiKey);
    } catch (err: any) {
      pushToast("danger", err.response?.data?.detail || "Failed to create API key.");
    } finally {
      setCreatingKey(false);
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    try {
      const headers: any = {};
      if (activeApiKey) headers["x-api-key"] = activeApiKey;
      if (token) headers["Authorization"] = `Bearer ${token}`;

      await axios.delete(api(`/b2b/keys/${keyId}`), { headers });
      pushToast("info", "The API key has been deactivated.");
      loadB2BData(activeApiKey);
    } catch (err: any) {
      pushToast("danger", err.response?.data?.detail || "Could not revoke key.");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
    pushToast("info", "Copied to Clipboard");
  };


  return (
    <div className="max-w-6xl mx-auto space-y-8 p-4 md:p-6 pb-20">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/40 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
              <Building2 className="w-7 h-7 text-primary" /> Digital Rakshak Business
            </h1>
            {org && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20 uppercase tracking-wider">
                {org.tier} TIER
              </span>
            )}
          </div>
          <p className="text-muted-foreground mt-1 text-sm md:text-base">
            Enterprise threat intelligence, batch event ingestion, and real-time security alerts.
          </p>
        </div>

        {/* API Key Connection Pill */}
        <div className="flex items-center gap-2">
          <Input 
            placeholder="Enter B2B API Key (dr_live_...)"
            value={activeApiKey}
            onChange={(e) => setActiveApiKey(e.target.value)}
            className="w-64 h-9 text-xs font-mono"
          />
          <Button 
            onClick={() => {
              localStorage.setItem("dr_b2b_active_key", activeApiKey);
              loadB2BData(activeApiKey);
            }}
            className="h-9 text-xs"
          >
            Connect
          </Button>
        </div>
      </div>

      {/* Quota & Org Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Quota Card */}
        <Card className="p-5 border-border/60 bg-card/60 backdrop-blur-sm space-y-3">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-semibold uppercase tracking-wider">
            <span>Monthly Event Quota</span>
            <Activity className="w-4 h-4 text-primary" />
          </div>
          <div className="space-y-1">
            <div className="text-2xl font-bold text-foreground">
              {quota ? `${quota.events_processed.toLocaleString()} / ${quota.monthly_limit.toLocaleString()}` : "0 / 100,000"}
            </div>
            <div className="text-xs text-muted-foreground">
              {quota ? `${quota.quota_remaining.toLocaleString()} events remaining this month` : "Connect key to view quota"}
            </div>
          </div>
          {/* Progress bar */}
          <div className="w-full bg-muted/60 rounded-full h-2 overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all ${
                (quota?.usage_pct || 0) > 90 ? "bg-rose-500" : (quota?.usage_pct || 0) > 75 ? "bg-amber-500" : "bg-primary"
              }`}
              style={{ width: `${Math.min(quota?.usage_pct || 0, 100)}%` }}
            />
          </div>
        </Card>

        {/* Organization Info */}
        <Card className="p-5 border-border/60 bg-card/60 backdrop-blur-sm space-y-3">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-semibold uppercase tracking-wider">
            <span>Organization Context</span>
            <Building2 className="w-4 h-4 text-primary" />
          </div>
          <div className="space-y-1">
            <div className="text-2xl font-bold text-foreground">
              {org?.name || "Enterprise Workspace"}
            </div>
            <div className="text-xs font-mono text-muted-foreground">
              slug: {org?.slug || "pending-connection"}
            </div>
          </div>
          <div className="text-xs text-emerald-500 font-medium flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" /> High-throughput Redis Streams Enabled
          </div>
        </Card>

        {/* Active Keys Count */}
        <Card className="p-5 border-border/60 bg-card/60 backdrop-blur-sm space-y-3">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-semibold uppercase tracking-wider">
            <span>Machine API Keys</span>
            <Key className="w-4 h-4 text-primary" />
          </div>
          <div className="space-y-1">
            <div className="text-2xl font-bold text-foreground">
              {keysList.filter(k => k.is_active).length} Active Keys
            </div>
            <div className="text-xs text-muted-foreground">
              SHA-256 hashed credentials
            </div>
          </div>
          <Button 
            onClick={() => setShowKeyModal(true)}
            variant="secondary" 
            className="w-full h-8 text-xs font-medium"
          >
            <Plus className="w-3.5 h-3.5 mr-1.5" /> Generate New Key
          </Button>

        </Card>
      </div>

      {/* Main Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-border/60 pb-2 text-sm font-medium">
        {[
          { id: "keys", label: "API Keys", icon: Key },
          { id: "integration", label: "Ingestion Guide", icon: Code2 },
          { id: "stream", label: "Live Alert Feed", icon: Radio }
        ].map(tab => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
                active 
                  ? "bg-primary text-white shadow-sm" 
                  : "text-muted-foreground hover:bg-muted/40"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab: API Keys */}
      {activeTab === "keys" && (
        <Card className="p-6 border-border/60 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-base">Organization API Keys</h3>
              <p className="text-xs text-muted-foreground">Authenticate your SIEM, microservices, or transaction switches.</p>
            </div>
            <Button onClick={() => setShowKeyModal(true)} className="h-9 text-xs">
              <Plus className="w-3.5 h-3.5 mr-1.5" /> New Key
            </Button>
          </div>

          {keysList.length === 0 ? (
            <div className="text-center py-10 border border-dashed border-border/60 rounded-xl space-y-2">
              <Key className="w-8 h-8 text-muted-foreground mx-auto" />
              <div className="text-sm font-medium">No API keys loaded</div>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Connect an existing B2B key above, or generate your first key to start piping threat telemetry.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border/60 text-muted-foreground">
                    <th className="pb-3 font-semibold">NAME</th>
                    <th className="pb-3 font-semibold">KEY PREFIX</th>
                    <th className="pb-3 font-semibold">SCOPES</th>
                    <th className="pb-3 font-semibold">CREATED</th>
                    <th className="pb-3 font-semibold">LAST USED</th>
                    <th className="pb-3 font-semibold text-right">ACTION</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {keysList.map(key => (
                    <tr key={key.key_id} className="hover:bg-muted/20">
                      <td className="py-3 font-medium text-foreground">{key.name}</td>
                      <td className="py-3 font-mono text-muted-foreground">{key.key_prefix}...</td>
                      <td className="py-3">
                        <div className="flex gap-1 flex-wrap">
                          {key.scopes.map(s => (
                            <span key={s} className="px-1.5 py-0.5 rounded bg-muted text-[10px] text-muted-foreground">
                              {s}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 text-muted-foreground">
                        {new Date(key.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 text-muted-foreground">
                        {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : "Never"}
                      </td>
                      <td className="py-3 text-right">
                        {key.is_active && (
                          <Button 
                            onClick={() => handleRevokeKey(key.key_id)}
                            variant="ghost" 
                            className="h-7 text-xs text-rose-500 hover:text-rose-600 hover:bg-rose-500/10 px-2"
                          >
                            <Trash2 className="w-3.5 h-3.5 mr-1" /> Revoke
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Tab: Ingestion Guide */}
      {activeTab === "integration" && (
        <Card className="p-6 border-border/60 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="font-bold text-base flex items-center gap-2">
                <Terminal className="w-4 h-4 text-primary" /> Threat Event Ingestion API
              </h3>
              <p className="text-xs text-muted-foreground mt-1">
                Send batches of up to 100 security events per call to <code className="bg-muted px-1.5 py-0.5 rounded font-mono text-foreground">POST /v1/b2b/events/ingest</code>.
              </p>
            </div>
            <Button
              onClick={handleTestIngest}
              disabled={testIngesting}
              variant="secondary"
              className="h-8 text-xs font-semibold gap-1.5 shrink-0"
            >
              <Play className="w-3.5 h-3.5" /> Test Ingest Live Event Batch
            </Button>
          </div>

          <div className="space-y-3">
            <div className="flex gap-2">
              {(["curl", "python", "node"] as const).map(lang => (
                <button
                  key={lang}
                  onClick={() => setSnippetLanguage(lang)}
                  className={`px-3 py-1 rounded-md text-xs font-semibold uppercase ${
                    snippetLanguage === lang 
                      ? "bg-primary text-white" 
                      : "bg-muted text-muted-foreground hover:bg-muted/80"
                  }`}
                >
                  {lang}
                </button>
              ))}
            </div>

            <div className="relative bg-zinc-950 text-zinc-100 p-4 rounded-xl font-mono text-xs overflow-x-auto border border-zinc-800">
              <button
                onClick={() => {
                  const text = snippetLanguage === "curl" ? curlSnippet : snippetLanguage === "python" ? pythonSnippet : nodeSnippet;
                  copyToClipboard(text);
                }}
                className="absolute top-3 right-3 p-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
              >
                {copiedKey ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>

              <pre>
                {snippetLanguage === "curl" && curlSnippet}
                {snippetLanguage === "python" && pythonSnippet}
                {snippetLanguage === "node" && nodeSnippet}
              </pre>
            </div>
          </div>
        </Card>
      )}

      {/* Tab: Live Alert Stream */}
      {activeTab === "stream" && (
        <Card className="p-6 border-border/60 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-base flex items-center gap-2">
                <Radio className="w-4 h-4 text-rose-500 animate-pulse" /> Live Organization Security Stream
              </h3>
              <p className="text-xs text-muted-foreground">Server-Sent Events (SSE) feed scoped exclusively to your tenant.</p>
            </div>
            <span className="text-xs text-emerald-500 font-semibold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" /> Connected
            </span>
          </div>

          <div className="border border-border/60 rounded-xl p-4 bg-muted/20 space-y-3 font-mono text-xs">
            <div className="p-3 rounded-lg border border-border/60 bg-card/80 flex items-start justify-between">
              <div>
                <div className="text-rose-500 font-bold flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5" /> CRITICAL: Phishing Campaign Correlation
                </div>
                <div className="text-muted-foreground mt-1">
                  Target: Brand Impersonation • Domain: secure-kyc-update.online
                </div>
              </div>
              <span className="text-[10px] text-muted-foreground">Just now</span>
            </div>

            <div className="p-3 rounded-lg border border-border/60 bg-card/80 flex items-start justify-between">
              <div>
                <div className="text-amber-500 font-bold flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5" /> HIGH: Credential Stuffing Anomaly
                </div>
                <div className="text-muted-foreground mt-1">
                  Source: 185.220.101.5 • 42 failed attempts within 60s
                </div>
              </div>
              <span className="text-[10px] text-muted-foreground">2 min ago</span>
            </div>
          </div>
        </Card>
      )}

      {/* Modal: Create API Key */}
      {showKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-card border border-border/80 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold">Create Machine API Key</h3>
              <button onClick={() => { setShowKeyModal(false); setCreatedPlaintextKey(null); }} className="text-muted-foreground hover:text-foreground">✕</button>
            </div>

            {!createdPlaintextKey ? (
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">KEY LABEL / SYSTEM NAME</label>
                  <Input 
                    placeholder="e.g., Cloudflare WAF Ingestion, Splunk Forwarder"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                  />
                </div>
                <Button 
                  onClick={handleCreateApiKey}
                  disabled={creatingKey || !newKeyName}
                  className="w-full text-xs font-semibold"
                >
                  {creatingKey ? "Generating SHA-256 Key..." : "Generate Key"}
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-600 dark:text-amber-400">
                  ⚠️ <strong>Save this key now.</strong> For security reasons, this key will never be shown again.
                </div>
                <div className="flex items-center gap-2">
                  <Input value={createdPlaintextKey} readOnly className="font-mono text-xs" />
                  <Button onClick={() => copyToClipboard(createdPlaintextKey)} className="shrink-0">
                    {copiedKey ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </div>
                <Button 
                  onClick={() => { setShowKeyModal(false); setCreatedPlaintextKey(null); setNewKeyName(""); }}
                  className="w-full text-xs"
                >
                  Done
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Loading Overlays for Machine API Key Provisioning & Batch Ingestion */}
      <LoadingOverlay
        open={creatingKey}
        variant="cyber"
        fullscreen={true}
        title="Provisioning Machine API Key"
        subtitle="Generating SHA-256 key hash and assigning telemetry write scopes..."
        badge="B2B Key Service"
        steps={[
          "Generating cryptographically secure token entropy...",
          "Calculating SHA-256 key hash for secure storage...",
          "Configuring rate limits & telemetry scopes in Redis...",
          "Registering audit trail..."
        ]}
      />

      <LoadingOverlay
        open={testIngesting}
        variant="cyber"
        fullscreen={true}
        title="Ingesting Security Telemetry Batch"
        subtitle="Piping STIX 2.1 threat events into enterprise Redis Streams..."
        badge="Event Ingestion Core"
        steps={[
          "Validating JSON event schemas & severity metrics...",
          "Ingesting batch into high-throughput Redis Streams...",
          "Cross-checking IoCs against National Threat Pattern Registry...",
          "Updating organization quota and audit logs..."
        ]}
      />
    </div>
  );
}

const curlSnippet = `curl -X POST "https://api.digitalrakshak.org/v1/b2b/events/ingest" \\
  -H "Content-Type: application/json" \\
  -H "x-api-key: YOUR_DR_API_KEY" \\
  -d '{
    "events": [
      {
        "event_type": "phishing_url",
        "severity": "critical",
        "source_ip": "103.21.244.0",
        "metadata": {
          "url": "https://secure-hdfc-otp.xyz/update",
          "target_entity": "UPI_SWITCH"
        }
      }
    ]
  }'`;

const pythonSnippet = `import requests

url = "https://api.digitalrakshak.org/v1/b2b/events/ingest"
headers = {
    "x-api-key": "YOUR_DR_API_KEY",
    "Content-Type": "application/json"
}

payload = {
    "events": [
        {
            "event_type": "fraud_transaction",
            "severity": "high",
            "metadata": {"account_id": "ACC9912", "amount": 85000}
        }
    ]
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())`;

const nodeSnippet = `const axios = require('axios');

async function ingestEvents() {
  const res = await axios.post(
    'https://api.digitalrakshak.org/v1/b2b/events/ingest',
    {
      events: [
        {
          event_type: 'suspicious_qr',
          severity: 'medium',
          metadata: { decoded_payload: 'upi://pay?pa=fake@okhdfc' }
        }
      ]
    },
    {
      headers: { 'x-api-key': 'YOUR_DR_API_KEY' }
    }
  );
  console.log(res.data);
}

ingestEvents();`;
