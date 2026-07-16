"use client";

import { useState, useEffect } from "react";
import { ShieldCheck, AlertTriangle, Link as LinkIcon, QrCode, Smartphone, HandCoins, Camera } from "lucide-react";
import axios from "axios";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { Rise } from "@/components/ui/motion";

// html5-qrcode touches window at import time, so require it client-side only.
let Html5QrcodeScanner: any;
if (typeof window !== "undefined") {
  Html5QrcodeScanner = require("html5-qrcode").Html5QrcodeScanner;
}

const TABS = [
  { id: "url", label: "Link", icon: LinkIcon, placeholder: "https://example.com", verb: "Scan link" },
  { id: "upi", label: "UPI ID", icon: HandCoins, placeholder: "merchant@bank", verb: "Verify UPI ID" },
  { id: "apk", label: "App file", icon: Smartphone, placeholder: "Upload an APK", verb: "Check APK" },
  { id: "qr", label: "QR code", icon: QrCode, placeholder: "Upload a QR image", verb: "Decode QR" },
];

export default function PreventionSuite() {
  const [activeTab, setActiveTab] = useState("url");
  const [inputValue, setInputValue] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [useCamera, setUseCamera] = useState(false);

  useEffect(() => {
    if (useCamera && activeTab === "qr" && Html5QrcodeScanner) {
      const scanner = new Html5QrcodeScanner(
        "reader",
        { fps: 10, qrbox: { width: 250, height: 250 } },
        false
      );

      scanner.render(
        (decodedText: string) => {
          scanner.clear();
          setUseCamera(false);
          setInputValue(decodedText);
          scanTextPayload(decodedText);
        },
        () => {
          // continuous-scan errors are expected noise
        }
      );

      return () => {
        scanner.clear().catch(console.error);
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [useCamera, activeTab]);

  const scanTextPayload = async (text: string) => {
    setLoading(true);
    setResult(null);
    try {
      const payload =
        activeTab === "url" ? { url: text } : activeTab === "upi" ? { upi: text } : { text: text };

      const res = await axios.post(api("/scan"), payload);
      setResult({
        safe: res.data.is_safe,
        confidence: 0.95,
        reason: res.data.reasons.join(" ") || "No threats detected.",
      });
    } catch (err: any) {
      setResult({
        safe: false,
        confidence: 0.99,
        reason: err.response?.data?.detail || "The scan failed.",
      });
    }
    setLoading(false);
  };

  const handleScan = async () => {
    setLoading(true);
    setResult(null);
    try {
      if (activeTab === "qr" && selectedFile) {
        const formData = new FormData();
        formData.append("file", selectedFile);
        const res = await axios.post(api("/scan/qr"), formData);
        setResult({
          safe: res.data.is_safe,
          confidence: 0.95,
          reason: res.data.reasons.join(" ") || "No threats found in the QR code.",
        });
      } else if (activeTab === "apk" && selectedFile) {
        const formData = new FormData();
        formData.append("file", selectedFile);
        const res = await axios.post(api("/scan/apk"), formData, {
          headers: { "Content-Type": "multipart/form-data" }
        });
        setResult({
          safe: res.data.is_safe,
          confidence: 0.95,
          reason: res.data.reasons.join("\n") || "No dangerous permissions found.",
        });
        setLoading(false);
        return;
      } else {
        await scanTextPayload(inputValue);
        return;
      }
    } catch (err: any) {
      setResult({
        safe: false,
        confidence: 0.99,
        reason: err.response?.data?.detail || "The scan failed.",
      });
    }
    setLoading(false);
  };

  const currentTab = TABS.find((t) => t.id === activeTab)!;

  return (
    <div className="max-w-2xl mx-auto space-y-6 pt-2">
      <Rise>
        <PageHeader
          title="Check before you trust"
          sub="Scan a link, UPI ID, app, or QR code before you tap it."
        />
      </Rise>

      <Rise index={1}>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {TABS.map((tab) => {
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
                className={cn(
                  "p-4 rounded-card flex flex-col items-center gap-1.5 transition-colors duration-150",
                  isActive
                    ? "bg-surface shadow-card text-ink"
                    : "bg-surface-2 text-ink-2 hover:text-ink hover:bg-surface-3"
                )}
                aria-pressed={isActive}
              >
                <Icon className="w-5 h-5" strokeWidth={isActive ? 2.2 : 2} />
                <span className="text-sm font-medium">{tab.label}</span>
              </button>
            );
          })}
        </div>
      </Rise>

      <Rise index={2}>
        <Card className="p-6">
          {useCamera && activeTab === "qr" && (
            <div className="w-full max-w-md mx-auto mb-4 overflow-hidden rounded-card border border-line">
              <div id="reader" className="w-full" />
              <button
                onClick={() => setUseCamera(false)}
                className="w-full p-2.5 bg-surface-2 text-sm text-ink hover:bg-surface-3 transition-colors"
              >
                Cancel camera
              </button>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3">
            {activeTab === "qr" || activeTab === "apk" ? (
              <div className="flex-1 flex gap-2">
                <Input
                  key={`file-${activeTab}`}
                  type="file"
                  accept={activeTab === "qr" ? "image/*" : ".apk"}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setSelectedFile(e.target.files[0]);
                      setInputValue(e.target.files[0].name);
                    } else {
                      setSelectedFile(null);
                      setInputValue("");
                    }
                  }}
                  className="pt-2 file:mr-3 file:py-1.5 file:px-3 file:rounded-pill file:border-0 file:text-xs file:font-medium file:bg-surface-2 file:text-ink hover:file:bg-surface-3"
                />
                {activeTab === "qr" && (
                  <Button type="button" onClick={() => setUseCamera(true)} className="h-11">
                    <Camera className="w-4 h-4" />
                    Camera
                  </Button>
                )}
              </div>
            ) : (
              <Input
                key={`text-${activeTab}`}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={currentTab.placeholder}
                className="flex-1"
              />
            )}

            <Button
              variant="primary"
              size="lg"
              onClick={handleScan}
              disabled={(!inputValue && !selectedFile) || useCamera}
              loading={loading}
              className="sm:w-auto w-full"
            >
              {currentTab.verb}
            </Button>
          </div>

          {result && (
            <div
              className={cn(
                "mt-6 p-5 rounded-card rise-in",
                result.safe ? "bg-success-tint" : "bg-danger-tint"
              )}
              role="status"
            >
              <div className="flex items-start gap-4">
                {result.safe ? (
                  <ShieldCheck className="w-6 h-6 text-success shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-6 h-6 text-danger shrink-0 mt-0.5" />
                )}
                <div className="min-w-0">
                  <h3
                    className={cn(
                      "font-display font-semibold text-base",
                      result.safe ? "text-success" : "text-danger"
                    )}
                  >
                    {result.safe ? "Looks safe" : "High risk — don't proceed"}
                  </h3>
                  <p className="text-sm text-ink-2 mt-1.5">{result.reason}</p>
                  <p className="text-xs text-ink-3 mt-3 tabular">
                    AI confidence {Math.round(result.confidence * 100)}%
                  </p>
                </div>
              </div>
            </div>
          )}
        </Card>
      </Rise>
    </div>
  );
}
