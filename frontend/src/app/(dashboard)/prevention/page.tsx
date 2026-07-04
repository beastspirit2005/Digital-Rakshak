"use client";

import { useState } from "react";
import { ShieldCheck, Search, AlertTriangle, Link as LinkIcon, QrCode, Smartphone, HandCoins } from "lucide-react";

export default function PreventionSuite() {
  const [activeTab, setActiveTab] = useState("url");
  const [inputValue, setInputValue] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleScan = () => {
    setLoading(true);
    // Mock simulation for hackathon
    setTimeout(() => {
      setResult({
        safe: Math.random() > 0.5,
        confidence: (Math.random() * 0.4 + 0.5).toFixed(2),
        reason: "Analyzed based on OSINT databases and recent CTI graph clusters.",
      });
      setLoading(false);
    }, 1500);
  };

  const tabs = [
    { id: "url", label: "URL/Link Scanner", icon: LinkIcon, placeholder: "https://example.com" },
    { id: "upi", label: "UPI ID Verifier", icon: HandCoins, placeholder: "merchant@bank" },
    { id: "apk", label: "APK/App Checker", icon: Smartphone, placeholder: "Upload or paste package name" },
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
        
        <div className="flex gap-4">
          {activeTab === 'qr' || activeTab === 'apk' ? (
            <input
              key={`file-${activeTab}`}
              type="file"
              accept={activeTab === 'qr' ? "image/*" : ".apk"}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setInputValue(e.target.files[0].name);
                } else {
                  setInputValue("");
                }
              }}
              className="flex-1 bg-background border border-border rounded-xl px-4 py-2 text-foreground focus:border-green-500 focus:ring-1 focus:ring-green-500 outline-none file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-green-500/20 file:text-green-400 hover:file:bg-green-500/30"
            />
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
            disabled={!inputValue || loading}
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
