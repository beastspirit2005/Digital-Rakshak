"use client";

import { api } from "@/lib/api";
import { useState, useEffect } from "react";
import { Loader2, CheckCircle2, UploadCloud, MapPin, Terminal } from "lucide-react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import Link from "next/link";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Input, Textarea, Label, FormError } from "@/components/ui/field";
import { Card, Inset } from "@/components/ui/card";
import { Segmented } from "@/components/ui/tabs";
import { ConfidenceDial } from "@/components/ui/stat";
import { ZtivfMeters } from "@/components/ztivf-meters";
import { axisTick } from "@/components/ui/chart";

export default function ReportPage() {
  const [scamText, setScamText] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successData, setSuccessData] = useState<any>(null);
  const [aiMode, setAiMode] = useState("auto");
  const [reportType, setReportType] = useState("scam");
  const [file, setFile] = useState<File | null>(null);

  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [locationSuccess, setLocationSuccess] = useState(false);

  const [showBrain, setShowBrain] = useState(false);
  const [brainLogs, setBrainLogs] = useState<string[]>([]);

  const [models, setModels] = useState<any[]>([]);
  const [isHeavy, setIsHeavy] = useState(false);

  const { token } = useAuthStore();
  const reduced = useReducedMotion();

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await axios.get(api("/agents/models"));
        setModels(res.data.models);
        const recommended = res.data.models.find((m: any) => m.is_recommended);
        if (recommended) {
          setAiMode(recommended.id);
        }
      } catch (err) {
        console.error("Failed to fetch models", err);
      }
    };
    fetchModels();
  }, []);

  useEffect(() => {
    if (aiMode === "both") {
      setIsHeavy(true);
    } else {
      const selected = models.find((m) => m.id === aiMode);
      setIsHeavy(selected?.is_heavy || false);
    }
  }, [aiMode, models]);

  const handleDetectLocation = () => {
    setIsLocating(true);
    setError("");

    if (!navigator.geolocation) {
      setError("Your browser doesn't support location detection.");
      setIsLocating(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        setLatitude(lat);
        setLongitude(lon);

        try {
          const res = await axios.get(api(`/cases/location?lat=${lat}&lon=${lon}`));
          if (res.data) {
            setCity(res.data.city || "");
            setState(res.data.state || "");
            setLocationSuccess(true);
          }
        } catch (err) {
          console.error("Failed to reverse geocode", err);
          setError("We got your coordinates but couldn't look up the city name.");
        } finally {
          setIsLocating(false);
        }
      },
      (error) => {
        console.error(error);
        setError("Location detection failed. Check that location permission is allowed.");
        setIsLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const simulateThoughtLogs = async () => {
    const logs = [
      "[SYSTEM] Initializing Rakshak Artificial Intelligence Core (RAIC)...",
      "[ROUTER] Determining optimal inference engine based on payload...",
      "[VISION AGENT] Pre-processing evidence and scanning for OCR data...",
      "[THREAT AGENT] Running heuristic NLP models on text...",
      "[THREAT AGENT] Correlating entities against National TPR database...",
      "[FUSION AGENT] Synthesizing multi-modal data...",
      "[FUSION AGENT] Calculating final Threat Confidence Score...",
    ];

    for (const log of logs) {
      setBrainLogs((prev) => [...prev, log]);
      await new Promise((resolve) => setTimeout(resolve, 400 + Math.random() * 500));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setShowBrain(true);
    setBrainLogs([]);
    setError("");

    const thoughtSimulation = simulateThoughtLogs();

    try {
      const formData = new FormData();
      formData.append("scam_text", scamText);
      if (city) formData.append("city", city);
      if (state) formData.append("state", state);
      if (latitude) formData.append("latitude", latitude.toString());
      if (longitude) formData.append("longitude", longitude.toString());
      formData.append("ai_mode", aiMode);
      formData.append("report_type", reportType);
      if (file) formData.append("file", file);

      const response = await axios.post(api("/cases/submit"), formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "multipart/form-data",
        },
      });

      await thoughtSimulation;
      setBrainLogs((prev) => [...prev, "[SUCCESS] Analysis complete. Returning verdict."]);
      await new Promise((resolve) => setTimeout(resolve, 1000));

      setSuccessData(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "The report couldn't be submitted. Try again.");
    } finally {
      setIsLoading(false);
      setShowBrain(false);
    }
  };

  const sixDim = successData?.ai_analysis?.six_dim_score;

  return (
    <div className="max-w-2xl mx-auto pt-2 pb-8">
      <div className="mb-8">
        <p className="font-serif italic text-sm text-ink-2 mb-2">Two minutes, eleven AI engines</p>
        <h1 className="font-display font-semibold text-xl sm:text-2xl tracking-tight text-ink">
          Report a cyber crime
        </h1>
        <p className="text-sm text-ink-2 mt-2 max-w-lg">
          Describe what happened in your own words. The report is analyzed instantly and routed
          to the right agency.
        </p>
      </div>

      <AnimatePresence mode="wait" initial={false}>
        {!successData ? (
          <motion.form
            key="form"
            initial={{ opacity: 0, y: reduced ? 0 : 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            onSubmit={handleSubmit}
            className="space-y-6"
          >
            <FormError>{error}</FormError>

            <Segmented
              className="w-full"
              items={[
                { id: "scam", label: "Cyber scam" },
                { id: "counterfeit", label: "Fake currency" },
              ]}
              value={reportType}
              onChange={setReportType}
            />

            <Card className="p-6 space-y-2">
              <Label htmlFor="scamText">What happened?</Label>
              <Textarea
                id="scamText"
                required
                rows={6}
                value={scamText}
                onChange={(e) => setScamText(e.target.value)}
                placeholder="Example: I got an SMS saying my electricity bill is unpaid and power will be cut tonight. The link was http://fake-bescom-update.com"
              />
              <p className="text-xs text-ink-3">
                Paste the message if you have it. Names, numbers, and timelines all help the analysis.
              </p>
            </Card>

            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <Label className="mb-0">Where did this happen?</Label>
                <Button
                  type="button"
                  size="sm"
                  onClick={handleDetectLocation}
                  loading={isLocating}
                >
                  <MapPin className="w-3.5 h-3.5" />
                  {locationSuccess ? "Location captured" : "Detect my location"}
                </Button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="City"
                  aria-label="City"
                />
                <Input
                  type="text"
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  placeholder="State"
                  aria-label="State"
                />
              </div>
              {locationSuccess && (
                <p className="text-xs text-success font-medium mt-3 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  GPS captured: {latitude?.toFixed(4)}, {longitude?.toFixed(4)}
                </p>
              )}
            </Card>

            <label className="relative block rounded-card border border-dashed border-line bg-surface p-8 text-center cursor-pointer transition-colors duration-150 hover:border-ink-3">
              <input
                type="file"
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                accept="image/png, image/jpeg, image/gif, application/pdf, audio/mpeg, audio/wav"
              />
              {file ? (
                <div className="flex flex-col items-center gap-1">
                  <CheckCircle2 className="w-6 h-6 text-success mb-1" />
                  <p className="text-sm font-medium text-ink">{file.name}</p>
                  <p className="text-xs text-ink-3">{(file.size / 1024 / 1024).toFixed(2)} MB · click to change</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-1">
                  <UploadCloud className="w-6 h-6 text-ink-3 mb-1" />
                  <p className="text-sm font-medium text-ink">Add a screenshot or recording</p>
                  <p className="text-xs text-ink-3">JPEG, PNG, PDF, or MP3 up to 10 MB — optional</p>
                </div>
              )}
            </label>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              disabled={!scamText.trim()}
              loading={isLoading}
              className="w-full sticky bottom-20 md:bottom-auto md:static shadow-card"
            >
              {isLoading ? "Analyzing your report…" : "Submit for analysis"}
            </Button>
          </motion.form>
        ) : (
          <motion.div
            key="success"
            initial={{ opacity: 0, y: reduced ? 0 : 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="space-y-6"
          >
            <Card className="p-6 sm:p-8">
              <div className="flex flex-col sm:flex-row sm:items-center gap-6">
                <ConfidenceDial
                  value={successData.ai_analysis?.confidence || 0}
                  size={112}
                  label="AI confidence"
                />
                <div>
                  <p className="text-xs text-ink-3 mb-1">
                    Case <span className="text-ink font-medium tabular">{successData.case_number}</span>
                  </p>
                  <h2 className="font-display font-semibold text-lg tracking-tight text-ink">
                    Report filed
                  </h2>
                  <p className="text-sm text-ink-2 mt-1">
                    Classified as{" "}
                    <span className="font-medium text-ink capitalize">
                      {(successData.ai_analysis?.threat_class || "unknown").replace(/_/g, " ")}
                    </span>
                    . Investigators can see this case now.
                  </p>
                </div>
              </div>
            </Card>

            {successData.ai_analysis?.raw_explanation && (
              <Card className="p-6">
                <p className="text-xs text-ink-3 mb-2">Why the AI thinks so</p>
                <p className="text-sm text-ink leading-relaxed">
                  {successData.ai_analysis.raw_explanation}
                </p>
              </Card>
            )}

            {successData.ai_analysis?.ztivf_metrics && (
              <Card className="p-6">
                <p className="text-xs text-ink-3 mb-4">Zero-trust validation</p>
                <ZtivfMeters metrics={successData.ai_analysis.ztivf_metrics} />
              </Card>
            )}

            {sixDim && (
              <Card className="p-6">
                <p className="text-xs text-ink-3 mb-2">Threat profile</p>
                <div className="h-60 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart
                      cx="50%"
                      cy="50%"
                      outerRadius="70%"
                      data={[
                        { subject: "Threat", A: sixDim.threat * 100 },
                        { subject: "Behavior", A: sixDim.behavior * 100 },
                        { subject: "Network", A: sixDim.network * 100 },
                        { subject: "Integrity", A: sixDim.integrity * 100 },
                        { subject: "Impersonation", A: sixDim.impersonation * 100 },
                        { subject: "Extraction", A: sixDim.extraction * 100 },
                      ]}
                    >
                      <PolarGrid stroke="var(--line)" />
                      <PolarAngleAxis dataKey="subject" tick={axisTick} />
                      <Radar
                        name="Threat profile"
                        dataKey="A"
                        stroke="var(--chart-1)"
                        fill="var(--chart-1)"
                        fillOpacity={0.25}
                        isAnimationActive={!reduced}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            )}

            <div className="flex items-center justify-center gap-3">
              <Button
                onClick={() => {
                  setSuccessData(null);
                  setScamText("");
                  setFile(null);
                }}
              >
                Report another
              </Button>
              <Link href="/citizen">
                <Button variant="primary">See my reports</Button>
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* RAIC execution log — shown while the swarm analyzes */}
      <AnimatePresence>
        {showBrain && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-ink/50 flex items-center justify-center p-4"
          >
            <Card className="max-w-xl w-full overflow-hidden">
              <div className="bg-surface-2 px-5 py-3 flex items-center gap-2.5">
                <Terminal className="w-4 h-4 text-accent-text" />
                <span className="text-sm font-medium text-ink">Rakshak AI core</span>
                <Loader2 className="w-3.5 h-3.5 animate-spin text-ink-3 ml-auto" />
              </div>
              <div className="p-5 h-72 overflow-y-auto font-mono text-xs space-y-2">
                {brainLogs.map((log, index) => (
                  <motion.p
                    key={index}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className={
                      log.includes("[SUCCESS]")
                        ? "text-success font-semibold"
                        : "text-ink-2"
                    }
                  >
                    {log}
                  </motion.p>
                ))}
                <p className="text-ink-3 animate-pulse">▋</p>
              </div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
