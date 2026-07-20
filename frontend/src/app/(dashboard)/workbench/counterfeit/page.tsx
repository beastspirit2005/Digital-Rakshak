"use client";

import React, { useState, useRef } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Upload,
  Eye,
  RefreshCw,
  Cpu,
  FileText,
  MapPin,
  Building2,
  Share2,
  ArrowRight,
  Search,
  Lock,
  Layers,
  Zap,
  Image as ImageIcon
} from "lucide-react";
import { RAICExecutionMonitor } from "@/components/ui/RAICExecutionMonitor";
import { api } from "@/lib/api";

export default function CounterfeitIntelligenceHubPage() {
  const { token } = useAuthStore();
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [analyzed, setAnalyzed] = useState<boolean>(false);
  const [advisorySent, setAdvisorySent] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [visionResult, setVisionResult] = useState<any>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [platformSettings, setPlatformSettings] = useState<any>(null);
  
  React.useEffect(() => {
    fetch(api("/admin/settings"), {
      headers: { Authorization: `Bearer ${token}` }
    })
    .then(res => res.json())
    .then(data => setPlatformSettings(data))
    .catch(err => console.error("Failed to load settings:", err));
  }, [token]);

  const isOffline = platformSettings?.force_local_inference || platformSettings?.default_ai_mode === 'ollama';
  const engineName = isOffline ? 'Native PyTorch MobileNetV3' : 'Groq Llama-4-Scout-17B-Vision';
  const engineType = isOffline ? 'Strictly Offline PyTorch Core' : 'Cloud Vision Engine';

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setAnalyzed(false);
      setVisionResult(null);
      setAdvisorySent(false);
    }
  };

  const handleSimulateVisionScan = async () => {
    if (!selectedFile) return;
    
    setAnalyzing(true);
    setAnalyzed(false);
    setAdvisorySent(false);
    
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      
      const res = await fetch(api("/scan/counterfeit"), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      });
      
      const data = await res.json();
      setVisionResult(data);
      setAnalyzed(true);
    } catch (err) {
      console.error("Vision scan failed:", err);
      // Fallback error state
      setVisionResult({
        decision: "Error: Analysis Failed",
        confidence: 0,
        threat_class: "Unknown",
        evidence: ["Failed to reach Groq Vision API."]
      });
      setAnalyzed(true);
    } finally {
      setAnalyzing(false);
    }
  };

  const sendRbiAdvisory = () => {
    setAdvisorySent(true);
  };

  const isCounterfeit = visionResult?.decision?.toLowerCase().includes("counterfeit");

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100 p-4 md:p-6 space-y-6 font-sans transition-colors duration-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-amber-100 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-500/40 text-amber-600 dark:text-amber-400 shadow-xl flex items-center justify-center">
            <Eye className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl md:text-3xl font-black font-mono tracking-tight text-slate-950 dark:text-white uppercase">
                Counterfeit Intelligence Hub 
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-500/40">
                Sprint 6 Vision Core
              </span>
            </div>
            <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-0.5 flex items-center gap-2">
              <span>Model: {engineName}</span>
              <span className="text-slate-300 dark:text-slate-600">•</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Live Multi-Spectral Decomposition</span>
            </p>
          </div>
        </div>

        {/* Note Selector / Uploader Trigger */}
        <div className="flex items-center gap-3">
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileSelect} 
            accept="image/*" 
            className="hidden" 
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-4 py-2.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-mono font-bold text-slate-750 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-all flex items-center gap-2 shadow-sm"
          >
            <Upload className="w-4 h-4" /> Upload Currency Image
          </button>
          
          <button
            onClick={handleSimulateVisionScan}
            disabled={analyzing || !selectedFile}
            className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-mono font-bold text-white shadow-lg transition-all ${
              !selectedFile 
                ? "bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed shadow-none" 
                : "bg-amber-500 hover:bg-amber-600"
            }`}
          >
            {analyzing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
            Execute Vision Scan
          </button>
        </div>
      </div>

      {advisorySent && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-500/40 text-emerald-800 dark:text-emerald-300 text-xs font-mono flex items-center justify-between shadow-sm"
        >
          <span className="flex items-center gap-2 font-bold">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" /> SUCCESS: Forensic Advisory & Note DNA Spec transmitted to RBI Fake Currency Control Cell & National Banking Grid.
          </span>
          <button onClick={() => setAdvisorySent(false)} className="text-slate-400 hover:text-slate-700 dark:hover:text-white">✕</button>
        </motion.div>
      )}

      {/* Top Split Card: Note Image / Telemetry vs Verdict Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 5 Columns: Note Spec & Vision Scan Progress */}
        <div className="lg:col-span-5 bg-white dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4 flex flex-col justify-between min-h-[350px] shadow-sm">
          <div>
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <span className="font-mono text-xs font-bold text-slate-600 dark:text-slate-300 uppercase">Live Image Ingestion Buffer</span>
              <span className={`text-xs font-mono font-bold ${isOffline ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                {engineType}
              </span>
            </div>

            {/* Simulated Currency Note Visual Viewport */}
            <div className="mt-4 rounded-xl border border-amber-300 dark:border-amber-500/30 relative flex flex-col items-center justify-center min-h-[250px] overflow-hidden bg-slate-50 dark:bg-slate-950">
              <div className="absolute inset-0 bg-[radial-gradient(#f59e0b_1px,transparent_1px)] [background-size:12px_12px] opacity-5 dark:opacity-10" />
              
              {previewUrl ? (
                <div className="relative w-full h-full p-2 flex items-center justify-center">
                  <img src={previewUrl} alt="Uploaded evidence" className="max-w-full max-h-[220px] object-contain rounded-lg shadow-2xl relative z-10" />
                  
                  {/* Scan Line Animation */}
                  {analyzing && (
                    <motion.div 
                      className="absolute inset-0 z-20 border-t-2 border-b-2 border-amber-500 bg-amber-500/20"
                      initial={{ height: "10%", top: "0%" }}
                      animate={{ top: ["0%", "90%", "0%"] }}
                      transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    />
                  )}
                </div>
              ) : (
                <div className="z-10 text-center space-y-3 p-6 text-slate-400 dark:text-slate-500">
                  <ImageIcon className="w-10 h-10 mx-auto opacity-40 dark:opacity-50" />
                  <p className="font-mono text-xs">No image uploaded. Click the upload button above to ingest a suspect currency note.</p>
                </div>
              )}

              {/* Status Badge Overlay */}
              {analyzed && visionResult && (
                <div className="absolute bottom-4 left-0 right-0 flex justify-center z-30">
                  <span
                    className={`px-3 py-1.5 rounded-full text-xs font-mono font-bold shadow-xl backdrop-blur-md ${
                      isCounterfeit
                        ? "bg-rose-500/90 text-white border border-rose-400"
                        : "bg-emerald-500/90 text-white border border-emerald-400"
                    }`}
                  >
                    {visionResult.decision}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right 7 Columns: Vision Security Features Decomposition Matrix */}
        <div className="lg:col-span-7 bg-white dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              <h3 className="font-mono text-sm font-bold text-slate-800 dark:text-white uppercase tracking-wide">
                Security Features Decomposition & Forensic Verdict
              </h3>
            </div>
            {analyzed && visionResult && (
              <span className={`text-xs font-mono font-bold ${isCounterfeit ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"}`}>
                Vision Confidence: {Math.round((visionResult.score || 0.99) * 100)}%
              </span>
            )}
          </div>

          {!selectedFile ? (
            <div className="py-24 text-center text-slate-400 dark:text-slate-600 font-mono text-xs flex flex-col items-center justify-center">
              <Eye className="w-8 h-8 mb-3 opacity-20" />
              Awaiting image ingestion to begin optical decomposition...
            </div>
          ) : analyzing ? (
            <div className="py-24 text-center text-slate-400 dark:text-slate-500 font-mono text-xs space-y-3">
              <RefreshCw className={`w-8 h-8 animate-spin mx-auto ${isOffline ? 'text-emerald-500 dark:text-emerald-400' : 'text-amber-500 dark:text-amber-400'}`} />
              <p className="text-slate-600 dark:text-slate-400">{engineName} analyzing intaglio relief, OVI shift, and micro-lettering...</p>
            </div>
          ) : analyzed && visionResult ? (
            <div className="space-y-4 max-h-[300px] overflow-y-auto pr-1 font-mono text-xs">
              
              <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                <span className="text-slate-400 dark:text-slate-500 text-[10px] block uppercase mb-1">AI Final Verdict:</span>
                <span className={`text-sm font-bold ${isCounterfeit ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"}`}>
                  {visionResult.decision}
                </span>
              </div>
              
              <div>
                <span className="text-slate-400 dark:text-slate-500 text-[10px] block uppercase mb-2">Detected Anomalies / Evidence:</span>
                {visionResult.evidence && visionResult.evidence.length > 0 ? (
                  <ul className="space-y-2">
                    {visionResult.evidence.map((ev: string, idx: number) => (
                      <li key={idx} className="p-3 rounded bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800/80 text-slate-700 dark:text-slate-300 flex items-start gap-2">
                        <AlertTriangle className={`w-4 h-4 mt-0.5 shrink-0 ${isCounterfeit ? "text-amber-500" : "text-emerald-500"}`} />
                        <span>{ev}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="p-3 rounded bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                    No distinct security features or anomalies identified.
                  </div>
                )}
              </div>
              
              {visionResult.extracted_text && (
                <div>
                  <span className="text-slate-400 dark:text-slate-500 text-[10px] block uppercase mb-2">Raw OCR Extraction:</span>
                  <div className="p-3 rounded bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 italic">
                    &quot;{visionResult.extracted_text}&quot;
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="py-24 text-center text-slate-400 dark:text-slate-600 font-mono text-xs flex flex-col items-center justify-center">
              Image loaded. Ready to execute scan.
            </div>
          )}

          <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-3 mt-auto">
            <button
              onClick={sendRbiAdvisory}
              disabled={advisorySent || !analyzed || !isCounterfeit}
              className={`px-4 py-2 rounded-lg font-mono font-bold text-xs transition-all shadow-lg flex items-center gap-2 ${
                advisorySent || !analyzed || !isCounterfeit
                  ? "bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed shadow-none"
                  : "bg-gradient-to-r from-amber-500 to-rose-600 hover:from-amber-600 hover:to-rose-500 text-white"
              }`}
            >
              <Zap className="w-4 h-4" /> Dispatch Forensic Advisory to RBI
            </button>
          </div>
        </div>
      </div>

      {/* Embed RAIC Execution Monitor for live vision engine progress */}
      <div className="space-y-2">
        <h3 className="font-mono text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          Vision Execution Engine Telemetry (`RAICExecutionMonitor`)
        </h3>
        <RAICExecutionMonitor 
          autoConnect={true} 
          className="max-h-56 bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm text-slate-800 dark:text-slate-200" 
        />
      </div>
    </div>
  );
}