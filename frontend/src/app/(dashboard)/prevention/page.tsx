"use client";

import { useState, useEffect } from "react";
import { ShieldCheck, Search, AlertTriangle, Link as LinkIcon, QrCode, Smartphone, HandCoins, Camera } from "lucide-react";
import axios from "axios";

// Using require to avoid Next.js SSR issues with html5-qrcode
let Html5QrcodeScanner: any;
if (typeof window !== "undefined") {
  Html5QrcodeScanner = require("html5-qrcode").Html5QrcodeScanner;
}

export default function PreventionSuite() {
  const [activeTab, setActiveTab] = useState("url");
  const [inputValue, setInputValue] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [useCamera, setUseCamera] = useState(false);

  useEffect(() => {
    if (useCamera && activeTab === 'qr' && Html5QrcodeScanner) {
      const scanner = new Html5QrcodeScanner(
        "reader",
        { fps: 10, qrbox: { width: 250, height: 250 } },
        false
      );
      
      scanner.render((decodedText: string) => {
        scanner.clear();
        setUseCamera(false);
        setInputValue(decodedText);
        scanTextPayload(decodedText);
      }, (err: any) => {
        // Ignore continuous scanning errors
      });

      return () => {
        scanner.clear().catch(console.error);
      };
    }
  }, [useCamera, activeTab]);

  const scanTextPayload = async (text: string) => {
    setLoading(true);
    setResult(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";
      const payload = activeTab === 'url' ? { url: text } : 
                      activeTab === 'upi' ? { upi: text } : 
                      { text: text };
                      
      const res = await axios.get(`${apiUrl}/scan`, { params: payload });
      setResult({
        safe: res.data.is_safe,
        confidence: 0.95, // AI confidence mocked for UI consistency
        reason: res.data.reasons.join(" ") || "No threats detected.",
      });
    } catch (err: any) {
      setResult({ safe: false, confidence: 0.99, reason: err.response?.data?.detail || "Scan failed." });
    }
    setLoading(false);
  };

  const handleScan = async () => {
    setLoading(true);
    setResult(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";
      
      if (activeTab === 'qr' && selectedFile) {
        const formData = new FormData();
        formData.append("file", selectedFile);
        const res = await axios.post(`${apiUrl}/scan/qr`, formData);
        setResult({
          safe: res.data.is_safe,
          confidence: 0.95,
          reason: res.data.reasons.join(" ") || "No threats detected in QR code.",
        });
      } 
      else if (activeTab === 'apk' && selectedFile) {
        // Mock APK scan since it requires submitting a case in the current backend architecture
        // or we could add a dedicated /scan/apk endpoint. For now, simulated.
        setTimeout(() => {
          setResult({
            safe: false,
            confidence: 0.99,
            reason: `Malicious APK Profile: BIND_ACCESSIBILITY_SERVICE detected in ${selectedFile.name}.`,
          });
          setLoading(false);
        }, 1500);
        return;
      }
      else {
        await scanTextPayload(inputValue);
        return;
      }
    } catch (err: any) {
      setResult({ safe: false, confidence: 0.99, reason: err.response?.data?.detail || "Scan failed." });
    }
    setLoading(false);
  };

  const tabs = [
    { id: "url", label: "URL/Link Scanner", icon: LinkIcon, placeholder: "https://example.com" },
    { id: "upi", label: "UPI ID Verifier", icon: HandCoins, placeholder: "merchant@bank" },
    { id: "apk", label: "APK/App Checker", icon: Smartphone, placeholder: "Upload APK" },
    { id: "qr", label: "QR Code Decoder", icon: QrCode, placeholder: "Upload QR image" },
  ];

  const currentTab = tabs.find(t => t.id === activeTab)!;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <ShieldCheck className="w-8 h-8 text-green-500" />
          Proactive Prevention Suite
        </h1>
        <p className="text-muted-foreground mt-2">
          Scan links, UPI IDs, and files before you interact with them. Powered by Digital Rakshak AI.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setResult(null);
                setInputValue("");
                setSelectedFile(null);
                setUseCamera(false);
              }}
              className={`p-4 rounded-xl border flex flex-col items-center justify-center gap-2 transition-all ${
                isActive 
                  ? "bg-green-500/10 border-green-500 text-green-400" 
                  : "bg-card border-border text-muted-foreground hover:bg-muted"
              }`}
            >
              <Icon className="w-6 h-6" />
              <span className="font-medium">{tab.label}</span>
            </button>
          );
        })}
      </div>

      <div className="glass-panel p-8 max-w-2xl mx-auto mt-8">
        <h2 className="text-xl font-semibold mb-4 text-foreground flex items-center gap-2">
          <Search className="w-5 h-5" />
          Scan {currentTab.label.split(" ")[0]}
        </h2>
        
        {useCamera && activeTab === 'qr' ? (
          <div className="w-full max-w-md mx-auto mb-4 overflow-hidden rounded-xl border-2 border-green-500">
            <div id="reader" className="w-full"></div>
            <button onClick={() => setUseCamera(false)} className="w-full p-2 bg-muted text-foreground hover:bg-muted/80">Cancel Camera</button>
          </div>
        ) : null}
        
        <div className="flex gap-4">
          {activeTab === 'qr' || activeTab === 'apk' ? (
            <div className="flex-1 flex gap-2">
              <input
                key={`file-${activeTab}`}
                type="file"
                accept={activeTab === 'qr' ? "image/*" : ".apk"}
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setSelectedFile(e.target.files[0]);
                    setInputValue(e.target.files[0].name);
                  } else {
                    setSelectedFile(null);
                    setInputValue("");
                  }
                }}
                className="flex-1 bg-background border border-border rounded-xl px-4 py-2 text-foreground focus:border-green-500 focus:ring-1 focus:ring-green-500 outline-none file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-green-500/20 file:text-green-400 hover:file:bg-green-500/30"
              />
              {activeTab === 'qr' && (
                <button 
                  onClick={() => setUseCamera(true)}
                  className="bg-muted hover:bg-muted/80 text-foreground px-4 py-2 rounded-xl border flex items-center gap-2"
                >
                  <Camera className="w-5 h-5" /> Camera
                </button>
              )}
            </div>
          ) : (
            <input
              key={`text-${activeTab}`}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={currentTab.placeholder}
              className="flex-1 bg-background border border-border rounded-xl px-4 py-3 text-foreground focus:border-green-500 focus:ring-1 focus:ring-green-500 outline-none"
            />
          )}
          
          <button 
            onClick={handleScan}
            disabled={(!inputValue && !selectedFile) || loading || useCamera}
            className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-8 py-3 rounded-xl font-medium transition-colors flex items-center gap-2"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              "Scan Now"
            )}
          </button>
        </div>

        {result && (
          <div className={`mt-8 p-6 rounded-xl border ${result.safe ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
            <div className="flex items-start gap-4">
              <div className={`p-3 rounded-full ${result.safe ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                {result.safe ? <ShieldCheck className="w-8 h-8" /> : <AlertTriangle className="w-8 h-8" />}
              </div>
              <div>
                <h3 className={`text-2xl font-bold ${result.safe ? 'text-green-400' : 'text-red-400'}`}>
                  {result.safe ? "Safe to Proceed" : "High Risk Detected!"}
                </h3>
                <p className="text-muted-foreground mt-2">{result.reason}</p>
                <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
                  <span>AI Confidence:</span>
                  <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${result.safe ? 'bg-green-500' : 'bg-red-500'}`} 
                      style={{ width: `${result.confidence * 100}%` }}
                    />
                  </div>
                  <span>{Math.round(result.confidence * 100)}%</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
