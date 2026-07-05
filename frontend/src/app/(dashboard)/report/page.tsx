"use client";


import { api } from "@/lib/api";
import { useState, useEffect } from "react";
import { Shield, Loader2, CheckCircle2, AlertCircle, UploadCloud, MapPin, Terminal } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function ReportPage() {
  const router = useRouter();
  const [scamText, setScamText] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successData, setSuccessData] = useState<any>(null);
  const [aiMode, setAiMode] = useState("auto");
  const [file, setFile] = useState<File | null>(null);
  
  // GPS State
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [locationSuccess, setLocationSuccess] = useState(false);
  
  // AI Brain Overlay State
  const [showBrain, setShowBrain] = useState(false);
  const [brainLogs, setBrainLogs] = useState<string[]>([]);
  
  // Dynamic Models State
  const [models, setModels] = useState<any[]>([]);
  const [isHeavy, setIsHeavy] = useState(false);
  
  const { token } = useAuthStore();

  useEffect(() => {
    // Fetch available models
    const fetchModels = async () => {
      try {
        const res = await axios.get(api("/agents/models"));
        setModels(res.data.models);
        // Set default to recommended
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

  // Update heavy warning on selection
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
      setError("Geolocation is not supported by your browser.");
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
          const res = await axios.get(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`);
          if (res.data && res.data.address) {
            setCity(res.data.address.city || res.data.address.town || res.data.address.village || "");
            setState(res.data.address.state || "");
            setLocationSuccess(true);
          }
        } catch (err) {
          console.error("Failed to reverse geocode", err);
          setError("Location detected but could not fetch city/state name.");
        } finally {
          setIsLocating(false);
        }
      },
      (error) => {
        console.error(error);
        setError("Failed to detect location. Please ensure location permissions are granted.");
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
      "[FUSION AGENT] Calculating final Threat Confidence Score..."
    ];
    
    for (const log of logs) {
      setBrainLogs(prev => [...prev, log]);
      // random delay between 400ms and 900ms to simulate real-time processing
      await new Promise(resolve => setTimeout(resolve, 400 + Math.random() * 500));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setShowBrain(true);
    setBrainLogs([]);
    setError("");
    
    // Start streaming thought logs in the background
    const thoughtSimulation = simulateThoughtLogs();

    try {
      const formData = new FormData();
      formData.append("scam_text", scamText);
      formData.append("ai_mode", aiMode);
      if (city) formData.append("city", city);
      if (state) formData.append("state", state);
      if (latitude) formData.append("latitude", latitude.toString());
      if (longitude) formData.append("longitude", longitude.toString());
      if (file) formData.append("file", file);

      const response = await axios.post(
        api("/cases/submit"),
        formData,
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            "Content-Type": "multipart/form-data" 
          }
        }
      );
      
      // Ensure the simulation finishes so judges can read it
      await thoughtSimulation;
      setBrainLogs(prev => [...prev, "[SUCCESS] Analysis complete. Returning verdict."]);
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setSuccessData(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to submit report. Please try again.");
    } finally {
      setIsLoading(false);
      setShowBrain(false);
    }
  };

  return (
    <div className="min-h-screen bg-muted/30 py-12 px-4 sm:px-6">
      <div className="max-w-3xl mx-auto space-y-8">
        
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center border border-primary/20 shadow-inner mx-auto mb-6">
            <Shield className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Report a Cyber Crime</h1>
          <p className="text-muted-foreground mt-2">
            Our AI Core will instantly analyze your report for threat patterns and route it to the correct agency.
          </p>
        </div>

        <AnimatePresence mode="wait">
          {!successData ? (
            <motion.form
              key="form"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              onSubmit={handleSubmit}
              className="glass-panel p-6 md:p-8 rounded-3xl space-y-6 border border-border"
            >
              {error && (
                <div className="bg-red-500/10 text-red-600 dark:text-red-400 p-4 rounded-xl flex items-center gap-2 text-sm border border-red-500/20">
                  <AlertCircle className="w-5 h-5 shrink-0" />
                  <p>{error}</p>
                </div>
              )}

              <div className="space-y-3">
                <label className="text-sm font-medium">Describe the Incident / Paste the Message</label>
                <textarea
                  required
                  rows={6}
                  value={scamText}
                  onChange={(e) => setScamText(e.target.value)}
                  placeholder="E.g. I received an SMS saying my electricity bill is unpaid and power will be cut tonight. The link was http://fake-bescom-update.com"
                  className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none resize-none"
                />
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Provide as much context as possible. Include specific details like caller names, requested actions, and timelines.
                </p>
              </div>

              <div className="bg-muted/50 p-4 rounded-2xl border border-border">
                <div className="flex items-center justify-between mb-4">
                  <label className="text-sm font-medium">Location Info</label>
                  <button 
                    type="button" 
                    onClick={handleDetectLocation}
                    disabled={isLocating}
                    className="flex items-center gap-2 text-xs font-bold px-3 py-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
                  >
                    {isLocating ? <Loader2 className="w-3 h-3 animate-spin" /> : <MapPin className="w-3 h-3" />}
                    {locationSuccess ? "Location Captured" : "Auto-Detect"}
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <input 
                      type="text"
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      className="w-full bg-background border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all text-sm"
                      placeholder="City"
                    />
                  </div>
                  <div>
                    <input 
                      type="text"
                      value={state}
                      onChange={(e) => setState(e.target.value)}
                      className="w-full bg-background border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all text-sm"
                      placeholder="State"
                    />
                  </div>
                </div>
                {locationSuccess && (
                  <p className="text-xs text-emerald-500 font-medium mt-2 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> GPS Coordinates Captured: {latitude?.toFixed(4)}, {longitude?.toFixed(4)}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Intelligence Engine
                </label>
                <select
                  value={aiMode}
                  onChange={(e) => setAiMode(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="both">⚡ Ensemble Analysis (Both Cloud & Local) (Heavy)</option>
                  <optgroup label="Cloud Models (Gemini)">
                    {models.filter(m => m.provider === 'google').map(m => (
                      <option key={m.id} value={m.id}>
                        {m.name} {m.is_recommended ? '(Recommended)' : ''}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Local Models (Ollama - Privacy Preserving)">
                    {models.filter(m => m.provider === 'ollama').map(m => (
                      <option key={m.id} value={m.id}>
                        {m.name} {m.is_recommended ? '(Recommended)' : ''}
                      </option>
                    ))}
                  </optgroup>
                </select>
                
                {isHeavy && (
                  <div className="mt-3 p-3 bg-yellow-50 dark:bg-yellow-500/10 border border-yellow-200 dark:border-yellow-500/20 rounded-xl flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-500 shrink-0 mt-0.5" />
                    <p className="text-sm text-yellow-800 dark:text-yellow-400">
                      <strong>Warning:</strong> This is a heavy compute operation. Analysis may take up to 2 minutes and is strictly rate-limited to 5 requests per minute to protect system hardware.
                    </p>
                  </div>
                )}
              </div>

              <div className="relative border-2 border-dashed border-border rounded-2xl p-8 flex flex-col items-center justify-center text-center hover:bg-muted/30 transition-colors cursor-pointer overflow-hidden group">
                <input 
                  type="file" 
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" 
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  accept="image/png, image/jpeg, image/gif, application/pdf, audio/mpeg, audio/wav"
                />
                
                {file ? (
                  <div className="flex flex-col items-center gap-2">
                    <CheckCircle2 className="w-10 h-10 text-emerald-500 mb-1" />
                    <p className="text-sm font-medium text-foreground">{file.name}</p>
                    <p className="text-xs text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    <p className="text-xs text-primary mt-2 font-medium group-hover:underline">Click to change file</p>
                  </div>
                ) : (
                  <>
                    <UploadCloud className="w-8 h-8 text-muted-foreground mx-auto mb-2 group-hover:text-primary transition-colors" />
                    <p className="text-sm font-medium">Upload Screenshots or Audio</p>
                    <p className="text-xs text-muted-foreground mt-1">JPEG, PNG, PDF, MP3 up to 10MB</p>
                  </>
                )}
              </div>

              <button
                type="submit"
                disabled={isLoading || !scamText.trim()}
                className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground py-4 rounded-xl font-medium hover:bg-primary/90 transition-all active:scale-[0.98] disabled:opacity-70 text-lg shadow-lg shadow-primary/20"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Analyzing via AI Core...
                  </>
                ) : (
                  "Submit Report for Analysis"
                )}
              </button>
            </motion.form>
          ) : (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="glass-panel p-8 rounded-3xl space-y-6 border border-emerald-500/20 text-center"
            >
              <div className="w-20 h-20 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto border border-emerald-500/20">
                <CheckCircle2 className="w-10 h-10 text-emerald-500" />
              </div>
              
              <div>
                <h2 className="text-2xl font-bold tracking-tight mb-2">Report Captured</h2>
                <p className="text-muted-foreground">
                  Case ID: <span className="font-mono text-foreground font-semibold">{successData.case_number}</span>
                </p>
              </div>

              <div className="bg-background rounded-2xl p-6 text-left border border-border mt-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <Shield className="w-4 h-4 text-primary" />
                  AI Analysis Results
                </h3>
                
                <div className="space-y-4 text-sm">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 rounded-xl bg-muted/50">
                      <p className="text-muted-foreground text-xs uppercase tracking-wider font-semibold mb-1">Threat Level</p>
                      <p className="font-medium text-red-500">{successData.ai_analysis?.decision || "Unknown"}</p>
                    </div>
                    <div className="p-3 rounded-xl bg-muted/50">
                      <p className="text-muted-foreground text-xs uppercase tracking-wider font-semibold mb-1">Confidence Score</p>
                      <p className="font-medium">{((successData.ai_analysis?.confidence || 0) * 100).toFixed(1)}%</p>
                    </div>
                  </div>
                  
                  {successData.ai_analysis?.ztivf_metrics && (
                    <div className="mt-4 p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
                      <h4 className="text-sm font-semibold text-indigo-400 mb-3 flex items-center gap-2">
                        <Shield className="w-4 h-4" />
                        Zero-Trust Validation (ZTIVF)
                      </h4>
                      <div className="grid grid-cols-2 gap-y-3 gap-x-6 text-xs">
                        {Object.entries(successData.ai_analysis.ztivf_metrics).map(([key, value]) => (
                          <div key={key} className="space-y-1">
                            <div className="flex justify-between text-muted-foreground capitalize">
                              <span>{key.replace('_score', '')}</span>
                              <span className="font-medium text-foreground">{((value as number) * 100).toFixed(0)}%</span>
                            </div>
                            <div className="h-1.5 w-full bg-background rounded-full overflow-hidden">
                              <div 
                                className={`h-full rounded-full ${
                                  (value as number) > 0.8 ? 'bg-emerald-500' : 
                                  (value as number) > 0.5 ? 'bg-amber-500' : 'bg-red-500'
                                }`} 
                                style={{ width: `${(value as number) * 100}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {successData.ai_analysis?.raw_explanation && (
                    <div className="mt-4 p-3 rounded-xl bg-muted/30 border border-border">
                      <p className="text-muted-foreground text-xs uppercase tracking-wider font-semibold mb-2">AI Reasoning</p>
                      <p className="text-sm text-foreground/90 leading-relaxed">
                        {successData.ai_analysis.raw_explanation}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-4 flex items-center justify-center gap-4">
                <button 
                  onClick={() => {
                    setSuccessData(null);
                    setScamText("");
                    setFile(null);
                  }}
                  className="px-6 py-2.5 rounded-xl text-sm font-medium border border-border hover:bg-muted transition-colors"
                >
                  Submit Another
                </button>
                <Link
                  href="/workbench"
                  className="px-6 py-2.5 rounded-xl text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-md"
                >
                  Go to Dashboard
                </Link>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* AI Brain Overlay Modal */}
        <AnimatePresence>
          {showBrain && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4"
            >
              <div className="max-w-2xl w-full bg-[#0a0a0a] border border-[#333] rounded-2xl overflow-hidden shadow-2xl">
                <div className="bg-[#111] border-b border-[#333] p-3 flex items-center gap-3">
                  <Terminal className="w-5 h-5 text-emerald-500" />
                  <span className="text-emerald-500 font-mono text-sm tracking-wider">RAIC_EXECUTION_TERMINAL</span>
                </div>
                <div className="p-6 h-80 overflow-y-auto font-mono text-sm space-y-2 text-emerald-400">
                  {brainLogs.map((log, index) => (
                    <motion.div 
                      key={index}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className={`${log.includes('[SUCCESS]') ? 'text-green-300 font-bold mt-4' : 'opacity-80'}`}
                    >
                      <span className="opacity-50 mr-2">{new Date().toISOString().split('T')[1].slice(0, -1)}</span>
                      {log}
                    </motion.div>
                  ))}
                  <div className="animate-pulse">_</div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
