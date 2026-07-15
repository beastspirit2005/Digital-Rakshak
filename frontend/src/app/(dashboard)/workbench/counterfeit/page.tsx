"use client";

import React, { useState } from "react";
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
  Zap
} from "lucide-react";
import { RAICExecutionMonitor } from "@/components/ui/RAICExecutionMonitor";

interface SecurityFeatureCheck {
  feature_name: string;
  expected_spec: string;
  observed_spec: string;
  status: "PASS" | "FAIL" | "SUSPICIOUS";
  confidence: number;
}

export default function CounterfeitIntelligenceHubPage() {
  const [selectedNote, setSelectedNote] = useState<string>("₹500 Series #2026-84A (Kolkata Seizure)");
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [analyzed, setAnalyzed] = useState<boolean>(true);
  const [advisorySent, setAdvisorySent] = useState<boolean>(false);

  const sampleNotes = [
    {
      id: "note-1",
      title: "₹500 Series #2026-84A (Kolkata Seizure)",
      serial: "8MD 492810",
      verdict: "COUNTERFEIT (Grade B+ Super-Note)",
      confidence: 0.96,
      origin: "Kolkata - Indo-Bangladesh Transit Vector",
      syndicate: "SYND-2026-IND-55"
    },
    {
      id: "note-2",
      title: "₹500 Series #2025-12B (Delhi ATM Deposit)",
      serial: "3AC 918241",
      verdict: "COUNTERFEIT (Grade C Photostat/Offset)",
      confidence: 0.99,
      origin: "Delhi NCR Local Printing Node",
      syndicate: "SYND-2026-IND-12"
    },
    {
      id: "note-3",
      title: "₹200 Series #2026-04C (Mumbai Retail Sweep)",
      serial: "5LP 001924",
      verdict: "AUTHENTIC (Genuine RBI Issue)",
      confidence: 0.98,
      origin: "Mumbai Federal Reserve Checkpoint",
      syndicate: "None (Clean)"
    }
  ];

  const currentSample = sampleNotes.find((n) => n.title === selectedNote) || sampleNotes[0];

  const securityFeatures: SecurityFeatureCheck[] = currentSample.verdict.includes("COUNTERFEIT")
    ? [
        {
          feature_name: "Optically Variable Ink (OVI) Colour Shift",
          expected_spec: "Green to Blue shift on tilting at 45 degree angle",
          observed_spec: "Static green pigment printed with glossy lacquer",
          status: "FAIL",
          confidence: 0.98
        },
        {
          feature_name: "Watermark & Mahatma Gandhi Portrait",
          expected_spec: "Multi-tonal watermarked portrait with light and dark contrast",
          observed_spec: "Single-tone oil printed silhouette (Back-printed)",
          status: "FAIL",
          confidence: 0.94
        },
        {
          feature_name: "Micro-lettering ('RBI' & 'Bharat' in Hindi)",
          expected_spec: "Crisp 0.2mm intaglio lettering readable under 10x magnification",
          observed_spec: "Blurred pixelated characters (300 DPI lithograph)",
          status: "FAIL",
          confidence: 0.97
        },
        {
          feature_name: "Windowed Security Thread with Color Shift",
          expected_spec: "3mm colour-shifting metallic thread embedded inside paper matrix",
          observed_spec: "Surface-stamped silver foil strip glued between paper layers",
          status: "FAIL",
          confidence: 0.99
        },
        {
          feature_name: "Intaglio Printing (Raised Tactile Marks)",
          expected_spec: "Raised tactile bleeding marks (5 lines for ₹500) for visually impaired",
          observed_spec: "Flat thermal embossing simulating tactile feel",
          status: "SUSPICIOUS",
          confidence: 0.88
        }
      ]
    : [
        {
          feature_name: "Optically Variable Ink (OVI) Colour Shift",
          expected_spec: "Green to Blue shift on tilting at 45 degree angle",
          observed_spec: "Authentic multi-layer optical shift verified",
          status: "PASS",
          confidence: 0.99
        },
        {
          feature_name: "Watermark & Mahatma Gandhi Portrait",
          expected_spec: "Multi-tonal watermarked portrait with light and dark contrast",
          observed_spec: "Genuine pulp fiber density differential verified",
          status: "PASS",
          confidence: 0.98
        },
        {
          feature_name: "Micro-lettering ('RBI' & 'Bharat' in Hindi)",
          expected_spec: "Crisp 0.2mm intaglio lettering readable under 10x magnification",
          observed_spec: "Sharp intaglio impression verified",
          status: "PASS",
          confidence: 0.99
        },
        {
          feature_name: "Windowed Security Thread with Color Shift",
          expected_spec: "3mm colour-shifting metallic thread embedded inside paper matrix",
          observed_spec: "Fully integrated security thread verified",
          status: "PASS",
          confidence: 0.99
        },
        {
          feature_name: "Intaglio Printing (Raised Tactile Marks)",
          expected_spec: "Raised tactile bleeding marks (5 lines for ₹500) for visually impaired",
          observed_spec: "Authentic high-pressure intaglio relief verified",
          status: "PASS",
          confidence: 0.99
        }
      ];

  const handleSimulateVisionScan = () => {
    setAnalyzing(true);
    setAnalyzed(false);
    setAdvisorySent(false);
    setTimeout(() => {
      setAnalyzing(false);
      setAnalyzed(true);
    }, 2000);
  };

  const sendRbiAdvisory = () => {
    setAdvisorySent(true);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6 space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-purple-900/40 border border-purple-500/40 text-purple-400 shadow-xl flex items-center justify-center">
            <Eye className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl md:text-3xl font-black font-mono tracking-tight text-white uppercase">
                Counterfeit Intelligence Hub (`/workbench/counterfeit`)
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-purple-500/20 text-purple-300 border border-purple-500/40">
                Sprint 6 Vision Core
              </span>
            </div>
            <p className="text-xs font-mono text-slate-400 mt-0.5 flex items-center gap-2">
              <span>Model: Qwen 2.5-VL-7B-Instruct Vision Engine</span>
              <span className="text-slate-600">•</span>
              <span className="text-emerald-400 font-semibold">10-Layer Security Feature Decomposition</span>
            </p>
          </div>
        </div>

        {/* Note Selector */}
        <div className="flex items-center gap-3">
          <select
            value={selectedNote}
            onChange={(e) => {
              setSelectedNote(e.target.value);
              setAdvisorySent(false);
            }}
            className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-purple-500"
          >
            {sampleNotes.map((note) => (
              <option key={note.id} value={note.title}>
                {note.title}
              </option>
            ))}
          </select>
          <button
            onClick={handleSimulateVisionScan}
            disabled={analyzing}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-mono font-bold bg-purple-600 hover:bg-purple-500 text-white shadow-lg transition-all"
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
          className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs font-mono flex items-center justify-between"
        >
          <span className="flex items-center gap-2 font-bold">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" /> SUCCESS: Forensic Advisory & Note DNA Spec transmitted to RBI Fake Currency Control Cell & National Banking Grid.
          </span>
          <button onClick={() => setAdvisorySent(false)} className="text-slate-400 hover:text-white">✕</button>
        </motion.div>
      )}

      {/* Top Split Card: Note Image / Telemetry vs Verdict Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 5 Columns: Note Spec & Vision Scan Progress */}
        <div className="lg:col-span-5 bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="font-mono text-xs font-bold text-slate-300 uppercase">Serial # {currentSample.serial}</span>
              <span className="text-xs font-mono text-purple-400 font-bold">{currentSample.origin}</span>
            </div>

            {/* Simulated Currency Note Visual Viewport */}
            <div className="mt-4 p-6 rounded-xl bg-gradient-to-br from-amber-950/40 via-slate-950 to-purple-950/40 border border-purple-500/30 relative flex flex-col items-center justify-center min-h-[220px]">
              <div className="absolute inset-0 bg-[radial-gradient(#a855f7_1px,transparent_1px)] [background-size:12px_12px] opacity-20" />
              <div className="z-10 text-center space-y-2">
                <div className="px-4 py-2 rounded bg-slate-900/90 border border-purple-500/60 font-mono text-sm font-black tracking-widest text-white shadow-xl">
                  RESERVE BANK OF INDIA • ₹500
                </div>
                <div className="text-xs font-mono text-purple-300">
                  Optical Scan Resolution: 1200 DPI Multispectral
                </div>
                {analyzing ? (
                  <div className="pt-2 flex flex-col items-center gap-2 text-purple-400 font-mono text-xs">
                    <RefreshCw className="w-6 h-6 animate-spin" />
                    <span>Deconstructing 5 Security Layers...</span>
                  </div>
                ) : (
                  <div className="pt-2">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-mono font-bold ${
                        currentSample.verdict.includes("COUNTERFEIT")
                          ? "bg-rose-500/20 text-rose-400 border border-rose-500/40"
                          : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                      }`}
                    >
                      {currentSample.verdict}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 font-mono text-xs text-slate-400 flex items-center justify-between">
            <span>Linked Syndicate Grid:</span>
            <span className="font-bold text-white bg-slate-800 px-2 py-0.5 rounded">{currentSample.syndicate}</span>
          </div>
        </div>

        {/* Right 7 Columns: Vision Security Features Decomposition Matrix */}
        <div className="lg:col-span-7 bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-purple-400" />
              <h3 className="font-mono text-sm font-bold text-white uppercase tracking-wide">
                Security Features Decomposition & Forensic Verdict
              </h3>
            </div>
            <span className="text-xs font-mono text-emerald-400 font-bold">
              Vision Confidence: {(currentSample.confidence * 100).toFixed(1)}%
            </span>
          </div>

          {analyzing ? (
            <div className="py-16 text-center text-slate-500 font-mono text-xs space-y-3">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto text-purple-400" />
              <p>Analyzing intaglio relief, OVI shift, and micro-lettering...</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-80 overflow-y-auto pr-1 font-mono text-xs">
              {securityFeatures.map((check, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 hover:border-slate-700 transition-all space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200">{check.feature_name}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        check.status === "PASS"
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                          : check.status === "FAIL"
                          ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                          : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                      }`}
                    >
                      {check.status} ({Math.round(check.confidence * 100)}%)
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-400">
                    <div>
                      <span className="text-slate-500 text-[10px] block uppercase">RBI Official Spec:</span>
                      <span className="text-slate-300">{check.expected_spec}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] block uppercase">Observed Vision Output:</span>
                      <span
                        className={
                          check.status === "PASS"
                            ? "text-emerald-300 font-medium"
                            : "text-rose-300 font-medium"
                        }
                      >
                        {check.observed_spec}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="pt-3 border-t border-slate-800 flex justify-end gap-3">
            <button
              onClick={sendRbiAdvisory}
              disabled={advisorySent}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-rose-600 hover:from-purple-500 hover:to-rose-500 text-white font-mono font-bold text-xs transition-all shadow-lg flex items-center gap-2"
            >
              <Zap className="w-4 h-4" /> Dispatch Forensic Advisory to RBI / Banking Grid
            </button>
          </div>
        </div>
      </div>

      {/* Embed RAIC Execution Monitor for live vision engine progress */}
      <div className="space-y-2">
        <h3 className="font-mono text-xs font-bold text-slate-400 uppercase tracking-wider">
          Vision Execution Engine Telemetry (`RAICExecutionMonitor`)
        </h3>
        <RAICExecutionMonitor autoConnect={true} className="max-h-56" />
      </div>
    </div>
  );
}
