"use client";

import React, { useState, useRef } from "react";
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
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [analyzed, setAnalyzed] = useState<boolean>(false);
  const [advisorySent, setAdvisorySent] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [visionResult, setVisionResult] = useState<any>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      
      const token = localStorage.getItem("token") || "";
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

  setVisionResult(null);
  setAnalyzed(false);

  alert("Vision scan failed.");
} finally {
      setAnalyzing(false);
    }
  };

  const sendRbiAdvisory = () => {
    setAdvisorySent(true);
  };

  const isCounterfeit = visionResult?.decision?.toLowerCase().includes("counterfeit");

  return (
    <div className="min-h-screen bg-bg text-ink p-4 md:p-6 space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-line/10">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-accent-text/10 border border-accent/20 text-accent-text shadow-xl flex items-center justify-center">
            <Eye className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl md:text-3xl font-black font-mono tracking-tight text-ink uppercase">
                Counterfeit Intelligence Hub 
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-accent-text/10 text-accent-text border border-accent/20">
                Sprint 6 Vision Core
              </span>
            </div>
            <p className="text-xs font-mono text-ink-2 mt-0.5 flex items-center gap-2">
              <span>Model: Groq Llama-3.2-90B-Vision</span>
              <span className="text-ink-3">•</span>
              <span className="text-success font-semibold">Live Multi-Spectral Decomposition</span>
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
            className="px-4 py-2.5 rounded-lg bg-surface border border-line/10 text-xs font-mono font-bold text-ink hover:bg-surface-2 transition-all flex items-center gap-2"
          >
            <Upload className="w-4 h-4" /> Upload Currency Image
          </button>
          
          <button
            onClick={handleSimulateVisionScan}
            disabled={analyzing || !selectedFile}
            className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-mono font-bold text-ink shadow-lg transition-all ${
              !selectedFile ? "bg-surface-2 text-ink-3 cursor-not-allowed" : "bg-accent hover:bg-accent-hover"
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
          className="p-3 rounded-lg bg-success-tint/60 border border-success/20 text-success text-xs font-mono flex items-center justify-between"
        >
          <span className="flex items-center gap-2 font-bold">
            <CheckCircle2 className="w-4 h-4 text-success" /> SUCCESS: Forensic Advisory & Note DNA Spec transmitted to RBI Fake Currency Control Cell & National Banking Grid.
          </span>
          <button onClick={() => setAdvisorySent(false)} className="text-ink-2 hover:text-ink">✕</button>
        </motion.div>
      )}

      {/* Top Split Card: Note Image / Telemetry vs Verdict Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 5 Columns: Note Spec & Vision Scan Progress */}
        <div className="lg:col-span-5 bg-surface border border-line/10 rounded-xl p-5 space-y-4 flex flex-col justify-between min-h-[350px]">
          <div>
            <div className="flex items-center justify-between border-b border-line/10 pb-3">
              <span className="font-mono text-xs font-bold text-ink-2 uppercase">Live Image Ingestion Buffer</span>
              <span className="text-xs font-mono text-accent-text font-bold">Cloud Vision Engine</span>
            </div>

            {/* Simulated Currency Note Visual Viewport */}
            <div className="mt-4 rounded-xl border border-accent/20 relative flex flex-col items-center justify-center min-h-[250px] overflow-hidden bg-bg">
              <div className="absolute inset-0 bg-[radial-gradient(currentColor_1px,transparent_1px)] [background-size:12px_12px] text-accent-text/10 opacity-10" />
              
              {previewUrl ? (
                <div className="relative w-full h-full p-2 flex items-center justify-center">
                  <img src={previewUrl} alt="Uploaded evidence" className="max-w-full max-h-[220px] object-contain rounded-lg shadow-2xl relative z-10" />
                  
                  {/* Scan Line Animation */}
                  {analyzing && (
                    <motion.div 
                      className="absolute inset-0 z-20 border-t-2 border-b-2 border-accent bg-accent/20"
                      initial={{ height: "10%", top: "0%" }}
                      animate={{ top: ["0%", "90%", "0%"] }}
                      transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    />
                  )}
                </div>
              ) : (
                <div className="z-10 text-center space-y-3 p-6 text-ink-3">
                  <ImageIcon className="w-10 h-10 mx-auto opacity-50" />
                  <p className="font-mono text-xs">No image uploaded. Click the upload button above to ingest a suspect currency note.</p>
                </div>
              )}

              {/* Status Badge Overlay */}
              {analyzed && visionResult && (
                <div className="absolute bottom-4 left-0 right-0 flex justify-center z-30">
                  <span
                    className={`px-3 py-1.5 rounded-full text-xs font-mono font-bold shadow-xl backdrop-blur-md ${
                      isCounterfeit
                        ? "bg-danger/90 text-ink border border-danger/20"
                        : "bg-success/90 text-ink border border-success/20"
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
        <div className="lg:col-span-7 bg-surface border border-line/10 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-line/10 pb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-accent-text" />
              <h3 className="font-mono text-sm font-bold text-ink uppercase tracking-wide">
                Security Features Decomposition & Forensic Verdict
              </h3>
            </div>
            {analyzed && visionResult && (
              <span className={`text-xs font-mono font-bold ${isCounterfeit ? "text-danger" : "text-success"}`}>
                Vision Confidence: {Math.round((visionResult.score || 0.99) * 100)}%
              </span>
            )}
          </div>

          {!selectedFile ? (
            <div className="py-24 text-center text-ink-3 font-mono text-xs flex flex-col items-center justify-center">
              <Eye className="w-8 h-8 mb-3 opacity-20" />
              Awaiting image ingestion to begin optical decomposition...
            </div>
          ) : analyzing ? (
            <div className="py-24 text-center text-ink-3 font-mono text-xs space-y-3">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto text-accent-text" />
              <p>Groq Vision AI analyzing intaglio relief, OVI shift, and micro-lettering...</p>
            </div>
          ) : analyzed && visionResult ? (
            <div className="space-y-4 max-h-[300px] overflow-y-auto pr-1 font-mono text-xs">
              
              <div className="p-4 rounded-lg bg-bg border border-line/10">
                <span className="text-ink-3 text-[10px] block uppercase mb-1">AI Final Verdict:</span>
                <span className={`text-sm font-bold ${isCounterfeit ? "text-danger" : "text-success"}`}>
                  {visionResult.decision}
                </span>
              </div>
              
              <div>
                <span className="text-ink-3 text-[10px] block uppercase mb-2">Detected Anomalies / Evidence:</span>
                {visionResult.evidence && visionResult.evidence.length > 0 ? (
                  <ul className="space-y-2">
                    {visionResult.evidence.map((ev: string, idx: number) => (
                      <li key={idx} className="p-3 rounded bg-bg border border-line/10 text-ink flex items-start gap-2">
                        <AlertTriangle className={`w-4 h-4 mt-0.5 shrink-0 ${isCounterfeit ? "text-warning" : "text-success"}`} />
                        <span>{ev}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="p-3 rounded bg-bg border border-line/10 text-ink-2">
                    No distinct security features or anomalies identified.
                  </div>
                )}
              </div>
              
              {visionResult.extracted_text && (
                <div>
                  <span className="text-ink-3 text-[10px] block uppercase mb-2">Raw OCR Extraction:</span>
                  <div className="p-3 rounded bg-bg border border-line/10 text-ink-2 italic">
                    "{visionResult.extracted_text}"
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="py-24 text-center text-ink-3 font-mono text-xs flex flex-col items-center justify-center">
              Image loaded. Ready to execute scan.
            </div>
          )}

          <div className="pt-3 border-t border-line/10 flex justify-end gap-3 mt-auto">
            <button
              onClick={sendRbiAdvisory}
              disabled={advisorySent || !analyzed || !isCounterfeit}
              className={`px-4 py-2 rounded-lg font-mono font-bold text-xs transition-all shadow-lg flex items-center gap-2 ${
                advisorySent || !analyzed || !isCounterfeit
                  ? "bg-surface-2 text-ink-3 cursor-not-allowed"
                  : "bg-gradient-to-r from-accent to-danger hover:from-accent-hover hover:to-danger/90 text-ink"
              }`}
            >
              <Zap className="w-4 h-4" /> Dispatch Forensic Advisory to RBI
            </button>
          </div>
        </div>
      </div>

      {/* Embed RAIC Execution Monitor for live vision engine progress */}
      <div className="space-y-2">
        <h3 className="font-mono text-xs font-bold text-ink-2 uppercase tracking-wider">
          Vision Execution Engine Telemetry (`RAICExecutionMonitor`)
        </h3>
        <RAICExecutionMonitor autoConnect={true} className="max-h-56" />
      </div>
    </div>
  );
}