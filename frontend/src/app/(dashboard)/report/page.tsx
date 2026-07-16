"use client";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";
import { 
  Loader2, 
  CheckCircle2, 
  UploadCloud, 
  MapPin, 
  Lock, 
  ChevronRight, 
  ChevronLeft, 
  Clock 
} from "lucide-react";
import { TerminalOverlay } from "@/components/ui/terminal-overlay";
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
import { Card } from "@/components/ui/card";
import { Segmented } from "@/components/ui/tabs";
import { ConfidenceDial } from "@/components/ui/stat";
import { ZtivfMeters } from "@/components/ztivf-meters";
import { axisTick } from "@/components/ui/chart";

export default function ReportPage() {
  // Wizard Navigation Step
  const [activeStep, setActiveStep] = useState<number>(1);

  // Core Form Fields
  const [scamText, setScamText] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [victimPhone, setVictimPhone] = useState("");
  const [victimAddress, setVictimAddress] = useState("");
  const [reportType, setReportType] = useState("scam");
  const [file, setFile] = useState<File | null>(null);

  // Operational State Handlers
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successData, setSuccessData] = useState<any>(null);
  const [aiMode, setAiMode] = useState("auto");

  // Geolocation States
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [locationSuccess, setLocationSuccess] = useState(false);

  // Terminal Simulation Overlay
  const [showBrain, setShowBrain] = useState(false);
  const [brainLogs, setBrainLogs] = useState<string[]>([]);
  const [models, setModels] = useState<any[]>([]);

  const { token } = useAuthStore();
  const reduced = useReducedMotion();

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await axios.get(api("/agents/models"), { 
          headers: { Authorization: `Bearer ${token}` } 
        });
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
  }, [token]);

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
          setError("We captured your coordinates but couldn't resolve the city name.");
        } finally {
          setIsLocating(false);
        }
      },
      (err) => {
        console.error(err);
        setError("Location detection failed. Ensure location permissions are active.");
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

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
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
      if (victimPhone) formData.append("victim_phone", victimPhone);
      if (victimAddress) formData.append("victim_address", victimAddress);
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
      setError(err.response?.data?.detail || "The report couldn't be submitted. Please try again.");
    } finally {
      setIsLoading(false);
      setShowBrain(false);
    }
  };

  const progressPercentage = activeStep * 25;
  const sixDim = successData?.ai_analysis?.six_dim_score;

  return (
    <div className="max-w-2xl mx-auto pt-4 pb-12 px-4 sm:px-6">
      <AnimatePresence mode="wait">
        {!successData ? (
          <div key="reporting-wizard" className="space-y-6">
            {/* Header progress tracking */}
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider">
                <span className="text-accent font-display">Step {activeStep} of 4</span>
                <span className="text-ink-3 flex items-center gap-1.5 font-sans normal-case">
                  <Clock className="w-3.5 h-3.5" />
                  About 1 minute
                </span>
              </div>
              <div className="h-1.5 w-full bg-surface-3 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-accent"
                  initial={{ width: 0 }}
                  animate={{ width: `${progressPercentage}%` }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                />
              </div>
            </div>

            {/* Steps Container */}
            <form onSubmit={(e) => e.preventDefault()} className="space-y-6">
              <FormError>{error}</FormError>

              <>
                {activeStep === 1 && (
                  <motion.div
                    key="step-1"
                    initial={reduced ? { opacity: 0 } : { opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={reduced ? { opacity: 0 } : { opacity: 0, x: -20 }}
                    transition={{ duration: 0.25, ease: "easeOut" }}
                    className="space-y-6"
                  >
                    <div className="space-y-1">
                      <p className="text-xs font-bold uppercase tracking-widest text-accent font-mono">
                        REPORT A SCAM
                      </p>
                      <h2 className="font-display font-bold text-2xl tracking-tight text-ink">
                        What happened?
                      </h2>
                      <p className="text-sm text-ink-2">
                        Tell us what happened in your own words. You don't need to use formal language.
                      </p>
                    </div>

                    <div className="space-y-4">
                      <Segmented
                        className="w-full"
                        items={[
                          { id: "scam", label: "Cyber scam" },
                          { id: "counterfeit", label: "Fake currency" },
                        ]}
                        value={reportType}
                        onChange={setReportType}
                      />

                      <Card className="p-6 bg-surface-2 border-line/10">
                        <Label htmlFor="scamText" className="sr-only">Incident Details</Label>
                        <Textarea
                          id="scamText"
                          required
                          rows={7}
                          value={scamText}
                          onChange={(e) => setScamText(e.target.value)}
                          placeholder="Example: I got an SMS saying my electricity bill is unpaid and power will be cut tonight. The sender asked me to call +919876543210 and install an APK link http://fake-bescom-update.com"
                          className="bg-surface focus:ring-1 focus:ring-accent/30 focus:border-accent"
                        />
                        <p className="text-xs text-ink-3 mt-3 leading-normal">
                          Paste the message if you have it. Names, numbers, links and timelines all help the analysis.
                        </p>
                      </Card>
                    </div>

                    <div className="flex justify-end pt-2">
                      <Button
                        type="button"
                        variant="primary"
                        size="lg"
                        disabled={!scamText.trim()}
                        onClick={() => setActiveStep(2)}
                        className="w-full sm:w-auto shadow-md"
                      >
                        Continue
                        <ChevronRight className="w-4 h-4 ml-1.5" />
                      </Button>
                    </div>
                  </motion.div>
                )}

                {activeStep === 2 && (
                  <motion.div
                    key="step-2"
                    initial={reduced ? { opacity: 0 } : { opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={reduced ? { opacity: 0 } : { opacity: 0, x: -20 }}
                    transition={{ duration: 0.25, ease: "easeOut" }}
                    className="space-y-6"
                  >
                    <div className="space-y-1">
                      <p className="text-xs font-bold uppercase tracking-widest text-accent font-mono">
                        REPORT A SCAM
                      </p>
                      <h2 className="font-display font-bold text-2xl tracking-tight text-ink">
                        Where did this happen?
                      </h2>
                      <p className="text-sm text-ink-2">
                        This helps us route your report to the right authority.
                      </p>
                    </div>

                    <Card className="p-6 bg-surface-2 border-line/10 space-y-6">
                      <button
                        type="button"
                        onClick={handleDetectLocation}
                        disabled={isLocating}
                        className={cn(
                          "w-full p-5 rounded-card border text-center transition-all duration-200 cursor-pointer",
                          locationSuccess
                            ? "border-success/30 bg-success-tint/20 text-success"
                            : "border-line bg-surface hover:border-accent"
                        )}
                      >
                        {isLocating ? (
                          <div className="flex items-center justify-center gap-2">
                            <Loader2 className="w-5 h-5 animate-spin text-accent" />
                            <span className="text-sm font-semibold text-ink">Accessing GPS...</span>
                          </div>
                        ) : (
                          <div className="space-y-1.5 flex flex-col items-center">
                            <MapPin className={cn("w-6 h-6", locationSuccess ? "text-success" : "text-accent")} />
                            <span className="text-sm font-semibold text-ink">
                              {locationSuccess ? "Location captured" : "Use my current location"}
                            </span>
                            <span className="text-xs text-ink-3">Detect location automatically</span>
                          </div>
                        )}
                      </button>

                      {locationSuccess && (
                        <p className="text-xs text-success font-medium flex items-center gap-1.5 justify-center">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          GPS coordinates captured: {latitude?.toFixed(4)}, {longitude?.toFixed(4)}
                        </p>
                      )}

                      <div className="relative flex items-center justify-center">
                        <div className="absolute inset-0 flex items-center">
                          <span className="w-full border-t border-line/10" />
                        </div>
                        <span className="relative px-3 bg-surface-2 text-xs font-semibold text-ink-3 uppercase">
                          OR
                        </span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="city">City</Label>
                          <Input
                            id="city"
                            type="text"
                            value={city}
                            onChange={(e) => setCity(e.target.value)}
                            placeholder="e.g. Bengaluru"
                            className="bg-surface focus:ring-1 focus:ring-accent/30 focus:border-accent"
                          />
                        </div>
                        <div>
                          <Label htmlFor="state">State</Label>
                          <Input
                            id="state"
                            type="text"
                            value={state}
                            onChange={(e) => setState(e.target.value)}
                            placeholder="e.g. Karnataka"
                            className="bg-surface focus:ring-1 focus:ring-accent/30 focus:border-accent"
                          />
                        </div>
                      </div>
                    </Card>

                    <div className="flex items-center justify-between gap-4 pt-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="lg"
                        onClick={() => setActiveStep(1)}
                        className="text-ink-2 hover:text-ink"
                      >
                        <ChevronLeft className="w-4 h-4 mr-1.5" />
                        Back
                      </Button>
                      <Button
                        type="button"
                        variant="primary"
                        size="lg"
                        onClick={() => setActiveStep(3)}
                        className="shadow-md"
                      >
                        Continue
                        <ChevronRight className="w-4 h-4 ml-1.5" />
                      </Button>
                    </div>
                  </motion.div>
                )}

                {activeStep === 3 && (
                  <motion.div
                    key="step-3"
                    initial={reduced ? { opacity: 0 } : { opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={reduced ? { opacity: 0 } : { opacity: 0, x: -20 }}
                    transition={{ duration: 0.25, ease: "easeOut" }}
                    className="space-y-6"
                  >
                    <div className="space-y-1">
                      <p className="text-xs font-bold uppercase tracking-widest text-accent font-mono">
                        REPORT A SCAM
                      </p>
                      <h2 className="font-display font-bold text-2xl tracking-tight text-ink">
                        How can we contact you?
                      </h2>
                      <p className="text-sm text-ink-2">
                        Optional, but recommended. Your details are used only for updates about your report.
                      </p>
                    </div>

                    <Card className="p-6 bg-surface-2 border-line/10 space-y-4">
                      <div>
                        <Label htmlFor="victimPhone">Phone Number</Label>
                        <Input
                          id="victimPhone"
                          type="tel"
                          value={victimPhone}
                          onChange={(e) => setVictimPhone(e.target.value)}
                          placeholder="e.g. +91 98765 43210"
                          className="bg-surface focus:ring-1 focus:ring-accent/30 focus:border-accent"
                        />
                      </div>
                      <div>
                        <Label htmlFor="victimAddress">Full Address</Label>
                        <Textarea
                          id="victimAddress"
                          rows={3}
                          value={victimAddress}
                          onChange={(e) => setVictimAddress(e.target.value)}
                          placeholder="e.g. Door No, Street, Ward, District, Pin Code"
                          className="bg-surface focus:ring-1 focus:ring-accent/30 focus:border-accent"
                        />
                      </div>

                      <div className="pt-2 flex items-center gap-2 text-xs text-ink-3 bg-surface p-3 rounded-control border border-line/5">
                        <Lock className="w-3.5 h-3.5 text-accent shrink-0" />
                        <span>Your contact details are encrypted before being saved.</span>
                      </div>
                    </Card>

                    <div className="flex items-center justify-between gap-4 pt-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="lg"
                        onClick={() => setActiveStep(2)}
                        className="text-ink-2 hover:text-ink"
                      >
                        <ChevronLeft className="w-4 h-4 mr-1.5" />
                        Back
                      </Button>
                      <Button
                        type="button"
                        variant="primary"
                        size="lg"
                        onClick={() => setActiveStep(4)}
                        className="shadow-md"
                      >
                        Continue
                        <ChevronRight className="w-4 h-4 ml-1.5" />
                      </Button>
                    </div>
                  </motion.div>
                )}

                {activeStep === 4 && (
                  <motion.div
                    key="step-4"
                    initial={reduced ? { opacity: 0 } : { opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={reduced ? { opacity: 0 } : { opacity: 0, x: -20 }}
                    transition={{ duration: 0.25, ease: "easeOut" }}
                    className="space-y-6"
                  >
                    <div className="space-y-1">
                      <p className="text-xs font-bold uppercase tracking-widest text-accent font-mono">
                        REPORT A SCAM
                      </p>
                      <h2 className="font-display font-bold text-2xl tracking-tight text-ink">
                        Do you have a screenshot or recording?
                      </h2>
                      <p className="text-sm text-ink-2">
                        Optional — you can submit your report without one.
                      </p>
                    </div>

                    <label className="relative block rounded-card border border-dashed border-line bg-surface p-10 text-center cursor-pointer transition-colors duration-150 hover:border-accent">
                      <input
                        type="file"
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                        accept="image/png, image/jpeg, image/gif, application/pdf, audio/mpeg, audio/wav"
                      />
                      {file ? (
                        <div className="flex flex-col items-center gap-2">
                          <CheckCircle2 className="w-8 h-8 text-success mb-1" />
                          <p className="text-sm font-semibold text-ink truncate max-w-md">{file.name}</p>
                          <p className="text-xs text-ink-3">
                            {(file.size / 1024 / 1024).toFixed(2)} MB • Click to change
                          </p>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center gap-2">
                          <UploadCloud className="w-8 h-8 text-accent mb-1" />
                          <p className="text-sm font-semibold text-ink">Add a screenshot or recording</p>
                          <p className="text-xs text-ink-3">
                            JPEG · PNG · PDF · MP3 · Up to 10 MB
                          </p>
                        </div>
                      )}
                    </label>

                    <div className="flex flex-col gap-3 pt-2">
                      <div className="flex items-center justify-between gap-4">
                        <Button
                          type="button"
                          variant="ghost"
                          size="lg"
                          onClick={() => setActiveStep(3)}
                          className="text-ink-2 hover:text-ink"
                        >
                          <ChevronLeft className="w-4 h-4 mr-1.5" />
                          Back
                        </Button>
                        <Button
                          type="button"
                          variant="primary"
                          size="lg"
                          loading={isLoading}
                          onClick={() => handleSubmit()}
                          className="shadow-md"
                        >
                          Submit for analysis
                        </Button>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleSubmit()}
                        disabled={isLoading}
                        className="text-xs text-center text-ink-3 hover:text-accent transition-colors py-2"
                      >
                        Skip for now
                      </button>
                    </div>
                  </motion.div>
                )}
              </>
            </form>
          </div>
        ) : (
          <motion.div
            key="success"
            initial={{ opacity: 0, y: reduced ? 0 : 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="space-y-6"
          >
            <Card className="p-6 sm:p-8 bg-surface-2 border-line/10">
              <div className="flex flex-col sm:flex-row sm:items-center gap-6">
                <ConfidenceDial
                  value={successData.ai_analysis?.confidence || 0}
                  size={112}
                  label="AI confidence"
                />
                <div>
                  <p className="text-xs text-ink-3 mb-1">
                    Case <span className="text-ink font-semibold tabular">{successData.case_number}</span>
                  </p>
                  <h2 className="font-display font-semibold text-lg tracking-tight text-ink">
                    Report filed
                  </h2>
                  <p className="text-sm text-ink-2 mt-1">
                    Classified as{" "}
                    <span className="font-semibold text-ink capitalize">
                      {(successData.ai_analysis?.threat_class || "unknown").replace(/_/g, " ")}
                    </span>
                    . Investigators can see this case now.
                  </p>
                </div>
              </div>
            </Card>

            {successData.ai_analysis?.raw_explanation && (
              <Card className="p-6 bg-surface-2 border-line/10">
                <p className="text-xs text-ink-3 mb-2 font-mono uppercase tracking-wider">Why the AI thinks so</p>
                <p className="text-sm text-ink leading-relaxed">
                  {successData.ai_analysis.raw_explanation}
                </p>
              </Card>
            )}

            {successData.ai_analysis?.ztivf_metrics && (
              <Card className="p-6 bg-surface-2 border-line/10">
                <p className="text-xs text-ink-3 mb-4 font-mono uppercase tracking-wider">Zero-trust validation</p>
                <ZtivfMeters metrics={successData.ai_analysis.ztivf_metrics} />
              </Card>
            )}

            {sixDim && (
              <Card className="p-6 bg-surface-2 border-line/10">
                <p className="text-xs text-ink-3 mb-2 font-mono uppercase tracking-wider">Threat profile</p>
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
                  setActiveStep(1);
                  setLocationSuccess(false);
                  setLatitude(null);
                  setLongitude(null);
                  setCity("");
                  setState("");
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

      <TerminalOverlay open={showBrain} logs={brainLogs} />
    </div>
  );
}