"use client";

import { api } from "@/lib/api";
import { useState, useRef, useEffect } from "react";
import { Mic, Square, Bot, Send, MapPin, Loader2 } from "lucide-react";

import axios from "axios";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/lib/auth-store";
import { Card, CardHeader, Inset } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { Rise } from "@/components/ui/motion";
import { useToast } from "@/components/ui/toast";

export default function CopilotPage() {
  const [isRecording, setIsRecording] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [draftReport, setDraftReport] = useState<any>(null);
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [isLocating, setIsLocating] = useState(false);


  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const { token } = useAuthStore();
  const toast = useToast();

  useEffect(() => {
    setIsLocating(true);
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          });
          setIsLocating(false);
        },
        () => {
          setLocation(null);
          setIsLocating(false);
          toast(
            "danger",
            "Location access is unavailable. The report will be submitted without GPS coordinates."
          );
        },
        { enableHighAccuracy: true, timeout: 30000, maximumAge: 10000 }
      );
    } else {
      setIsLocating(false);
    }
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: "audio/webm" });
        await processAudio(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Error accessing microphone:", err);
      toast("danger", "The co-pilot needs microphone access to listen.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
    }
  };

  const processAudio = async (audioBlob: Blob) => {
    setIsProcessing(true);
    setTranscript("");
    setDraftReport(null);

    try {
      const formData = new FormData();
      formData.append("file", audioBlob, "audio.webm");

      const response = await axios.post(api("/agents/transcribe"), formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      if (response.data.transcript) {
        setTranscript(response.data.transcript);
      } else {
        toast("danger", "The audio couldn't be transcribed.");
      }
    } catch (error) {
      console.error("Error transcribing audio:", error);
      toast("danger", "Something went wrong during transcription.");
    } finally {
      setIsProcessing(false);
    }
  };

  const analyzeTranscript = async () => {
    if (!transcript.trim()) return;

    setIsAnalyzing(true);
    try {
      const response = await axios.post(api("/agents/analyze-transcript"), {
        transcript: transcript,
      });

      if (response.data.draft) {
        setDraftReport(response.data.draft);
      } else {
        toast("danger", "The draft couldn't be generated.");
      }
    } catch (error) {
      console.error("Error analyzing transcript:", error);
      toast("danger", "The transcript couldn't be analyzed.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  

  const submitReport = async () => {
    if (!transcript.trim()) return;
    setIsProcessing(true);


    try {
      const formData = new FormData();
      formData.append("scam_text", transcript);
      formData.append("ai_mode", "auto");

      if (location) {
        formData.append("latitude", location.lat.toString());
        formData.append("longitude", location.lng.toString());
      }

      await axios.post(api("/cases/submit"), formData, {
        headers: {
          "Content-Type": "multipart/form-data",
          Authorization: `Bearer ${token}`,
        },
      });
toast("success", "Case submitted to the national database.");
     
      setTranscript("");
      setDraftReport(null);
    } catch (error) {
      console.error("Error submitting report:", error);
      toast("danger", "The report couldn't be submitted.");
    } finally {
      setIsProcessing(false);
      
    }
  };

  return (
    <div className="space-y-6 pt-2">
      <Rise>
        <PageHeader
          title="AI co-pilot"
          sub="Dictate a case or interview the victim — the co-pilot transcribes, analyzes, and drafts the report."
        />
      </Rise>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
        {/* recorder */}
        <Rise index={1}>
          <Card className="p-8 flex flex-col items-center text-center">
            <div className="relative my-6">
              {isRecording && (
                <span className="absolute -inset-3 rounded-pill bg-danger/15 animate-ping" />
              )}
              <button
                onClick={isRecording ? stopRecording : startRecording}
                aria-label={isRecording ? "Stop recording" : "Start recording"}
                className={cn(
                  "relative z-10 w-20 h-20 rounded-pill flex items-center justify-center shadow-card transition-colors duration-150 active:scale-95",
                  isRecording
                    ? "bg-danger text-surface"
                    : "bg-accent text-accent-ink hover:bg-accent-hover"
                )}
              >
                {isRecording ? <Square className="w-7 h-7" /> : <Mic className="w-7 h-7" />}
              </button>
            </div>

            <p className={cn("text-sm font-medium", isRecording ? "text-danger" : "text-ink")}>
              {isRecording ? "Recording — tap to stop" : "Tap to start listening"}
            </p>
            <p className="text-xs text-ink-2 mt-1.5 max-w-[16rem]">
              Speak naturally in any language. The transcript stays editable before anything is
              filed.
            </p>

            <div className="mt-8 flex items-center gap-2 text-xs">
              <MapPin className="w-3.5 h-3.5 text-ink-3" />
              {isLocating ? (
                <span className="text-ink-3">Getting your location…</span>
              ) : location ? (
                <span className="text-ink-2 tabular">
                  GPS {location.lat.toFixed(4)}, {location.lng.toFixed(4)}
                </span>
              ) : (
                <span className="text-warning">Location unavailable</span>
              )}
            </div>
          </Card>
        </Rise>

        {/* transcript + draft */}
        <div className="lg:col-span-2 space-y-4">
          <Rise index={2}>
            <Card>
              <CardHeader
                title="Transcript"
                sub="Editable before analysis"
                action={
                  transcript ? (
                    <Button size="sm" loading={isAnalyzing} onClick={analyzeTranscript}>
                      <Bot className="w-3.5 h-3.5" />
                      Analyze
                    </Button>
                  ) : undefined
                }
              />
              <div className="px-6 pb-6">
                {isProcessing && !transcript ? (
                  <div className="space-y-2.5 py-2">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-5/6" />
                    <Skeleton className="h-4 w-3/4" />
                    <p className="text-xs text-ink-3 pt-1">Transcribing through the Whisper agent…</p>
                  </div>
                ) : (
                  <Textarea
                    rows={5}
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                    placeholder="Waiting for audio — or type and paste text here."
                  />
                )}
              </div>
            </Card>
          </Rise>

          <Rise index={3}>
            <Card>
              <CardHeader title="Case draft" sub="Generated from the transcript" />
              <div className="px-6 pb-6">
                {draftReport ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <Inset className="p-4">
                        <p className="text-xs text-ink-3 mb-1">Classification</p>
                        <p className="text-sm font-medium text-ink capitalize">
                          {String(draftReport.scam_type || "—").replace(/_/g, " ")}
                        </p>
                      </Inset>
                      <Inset className="p-4">
                        <p className="text-xs text-ink-3 mb-1.5">AI confidence</p>
                        <div className="flex items-center gap-3">
                          <div className="flex-1 h-1.5 bg-surface-3 rounded-pill overflow-hidden">
                            <div
                              className="h-full bg-accent rounded-pill"
                              style={{ width: `${(draftReport.confidence || 0) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium text-ink tabular">
                            {Math.round((draftReport.confidence || 0) * 100)}%
                          </span>
                        </div>
                      </Inset>
                    </div>

                    <div>
                      <p className="text-xs text-ink-3 mb-2">Extracted entities</p>
                      <div className="flex flex-wrap gap-1.5">
                        {draftReport.entities?.phone_numbers?.map((p: string) => (
                          <Badge key={p} tone="lilac" className="tabular">{p}</Badge>
                        ))}
                        {draftReport.entities?.bank_accounts?.map((b: string) => (
                          <Badge key={b} tone="peach" className="tabular">{b}</Badge>
                        ))}
                        {draftReport.entities?.impersonation && (
                          <Badge tone="danger">
                            Impersonating {draftReport.entities.impersonation}
                          </Badge>
                        )}
                      </div>
                    </div>

                    <Button
                      variant="primary"
                      size="lg"
                      className="w-full"
                      loading={isProcessing}
                      onClick={submitReport}
                    >
                      <Send className="w-4 h-4" />
                      File the report
                    </Button>
                  </div>
                ) : (
                  <div className="rounded-control border border-dashed border-line py-10 text-center text-sm text-ink-3">
                    {isAnalyzing ? (
                      <span className="inline-flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Analyzing the transcript…
                      </span>
                    ) : (
                      "The draft appears here after analysis."
                    )}
                  </div>
                )}
              </div>
            </Card>
          </Rise>
        </div>
      </div>

      
    </div>
  );
}
