"use client";


import { api } from "@/lib/api";
import { useState, useRef, useEffect } from "react";
import { Mic, Square, Loader2, Bot, CheckCircle2, FileText, Send, User, MapPin } from "lucide-react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";

export default function CopilotPage() {
  const [isRecording, setIsRecording] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [draftReport, setDraftReport] = useState<any>(null);
  const [location, setLocation] = useState<{lat: number, lng: number} | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const { token } = useAuthStore();

  useEffect(() => {
    setIsLocating(true);
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude
          });
          setIsLocating(false);
        },
        (error) => {
          // Silently handle error and fallback to demo coordinates (Mumbai)
          // console.error triggers Next.js red overlay in dev mode
          setLocation({
            lat: 19.0760,
            lng: 72.8777
          });
          setIsLocating(false);
        },
        { enableHighAccuracy: true, timeout: 5000 }
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
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        await processAudio(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Error accessing microphone:", err);
      alert("Microphone access is required for the Co-Pilot.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
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
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      if (response.data.transcript) {
        setTranscript(response.data.transcript);
      } else {
        alert("Could not transcribe the audio.");
      }
    } catch (error) {
      console.error("Error transcribing audio:", error);
      alert("Error occurred during transcription.");
    } finally {
      setIsProcessing(false);
    }
  };

  const analyzeTranscript = async () => {
    if (!transcript.trim()) return;
    
    setIsAnalyzing(true);
    try {
      const response = await axios.post(api("/agents/analyze-transcript"), {
        transcript: transcript
      });
      
      if (response.data.draft) {
        setDraftReport(response.data.draft);
      } else {
        alert("Error generating draft.");
      }
    } catch (error) {
      console.error("Error analyzing transcript:", error);
      alert("Failed to analyze transcript.");
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
          'Content-Type': 'multipart/form-data',
          Authorization: `Bearer ${token}`
        }
      });
      alert("Case officially submitted to the National Database!");
      setTranscript("");
      setDraftReport(null);
    } catch (error) {
      console.error("Error submitting report:", error);
      alert("Failed to submit report.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-6">
      {/* Left Column: Voice Input */}
      <div className="w-1/3 flex flex-col gap-6">
        <div className="glass-panel p-6 flex-1 flex flex-col items-center justify-center text-center">
          <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center mb-6">
            <Bot className="w-10 h-10 text-primary" />
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-2">AI Investigator Co-Pilot</h2>
          <p className="text-muted-foreground mb-12">
            Speak naturally with the victim or dictate the case. I will transcribe, analyze, and draft the official report automatically.
          </p>

          <div className="relative">
            {isRecording && (
              <div className="absolute -inset-4 bg-red-500/20 rounded-full animate-ping" />
            )}
            <button
              onClick={isRecording ? stopRecording : startRecording}
              className={`relative z-10 w-24 h-24 rounded-full flex items-center justify-center shadow-lg transition-all ${
                isRecording 
                  ? "bg-red-500 hover:bg-red-600" 
                  : "bg-primary hover:bg-primary/90"
              }`}
            >
              {isRecording ? (
                <Square className="w-10 h-10 text-foreground" />
              ) : (
                <Mic className="w-10 h-10 text-foreground" />
              )}
            </button>
          </div>
          
          <p className={`mt-6 font-medium ${isRecording ? "text-red-400 animate-pulse" : "text-muted-foreground"}`}>
            {isRecording ? "Recording... (Click to stop)" : "Click mic to start listening"}
          </p>
          
          <div className="mt-8 flex items-center gap-2 bg-background/50 px-4 py-2 rounded-full border border-border">
            <MapPin className="w-4 h-4 text-primary" />
            {isLocating ? (
              <span className="text-muted-foreground text-sm animate-pulse">Acquiring live GPS location...</span>
            ) : location ? (
              <span className="text-green-500 text-sm font-medium">GPS Secured: {location.lat.toFixed(4)}, {location.lng.toFixed(4)}</span>
            ) : (
              <span className="text-amber-500 text-sm">Location unavailable</span>
            )}
          </div>
        </div>
      </div>

      {/* Right Column: AI Processing & Draft */}
      <div className="flex-1 flex flex-col gap-6">
        <div className="glass-panel p-6 h-1/3 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <FileText className="w-5 h-5 text-purple-500" />
              Live Transcription (Editable)
            </h3>
            {transcript && (
              <button 
                onClick={analyzeTranscript}
                disabled={isAnalyzing}
                className="bg-purple-500 hover:bg-purple-600 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
              >
                {isAnalyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bot className="w-4 h-4" />}
                Analyze Draft
              </button>
            )}
          </div>
          <div className="flex-1 bg-background/50 rounded-xl p-1 border border-border flex flex-col">
            {isProcessing ? (
              <div className="flex items-center gap-3 text-muted-foreground h-full justify-center">
                <Loader2 className="w-5 h-5 animate-spin text-primary" />
                Processing audio through Whisper Agent...
              </div>
            ) : (
              <textarea
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                placeholder="Waiting for audio input... You can also type or paste text here."
                className="w-full h-full bg-transparent p-3 text-foreground leading-relaxed resize-none focus:outline-none placeholder:text-muted-foreground placeholder:italic"
              />
            )}
          </div>
        </div>

        <div className="glass-panel p-6 flex-1 flex flex-col">
          <h3 className="font-semibold text-lg flex items-center gap-2 mb-4">
            <CheckCircle2 className="w-5 h-5 text-green-500" />
            Auto-Generated Case Draft
          </h3>
          
          {draftReport ? (
            <div className="flex-1 flex flex-col gap-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-background/50 p-4 rounded-xl border border-border">
                  <span className="text-muted-foreground text-sm">Classification</span>
                  <p className="text-foreground font-bold text-lg">{draftReport.scam_type}</p>
                </div>
                <div className="bg-background/50 p-4 rounded-xl border border-border">
                  <span className="text-muted-foreground text-sm">AI Confidence</span>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-green-500" 
                        style={{ width: `${(draftReport.confidence || 0) * 100}%` }}
                      />
                    </div>
                    <span className="text-foreground font-bold">{Math.round((draftReport.confidence || 0) * 100)}%</span>
                  </div>
                </div>
              </div>

              <div className="bg-background/50 p-4 rounded-xl border border-border">
                <span className="text-muted-foreground text-sm mb-2 block">Extracted Entities (Attack DNA)</span>
                <div className="flex flex-wrap gap-2">
                  {draftReport.entities?.phone_numbers?.map((p: string) => (
                    <span key={p} className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm font-medium border border-blue-500/30">📱 {p}</span>
                  ))}
                  {draftReport.entities?.bank_accounts?.map((b: string) => (
                    <span key={b} className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm font-medium border border-green-500/30">🏦 {b}</span>
                  ))}
                  {draftReport.entities?.impersonation && (
                    <span className="px-3 py-1 bg-red-500/20 text-red-400 rounded-full text-sm font-medium border border-red-500/30">🎭 {draftReport.entities.impersonation}</span>
                  )}
                </div>
              </div>

              <div className="flex-1"></div>

              <button 
                onClick={submitReport}
                disabled={isProcessing}
                className="w-full bg-primary hover:bg-primary/90 text-white py-4 rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-primary/25 disabled:opacity-50"
              >
                {isProcessing ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                {isProcessing ? "Submitting to National Database..." : "Submit Official Report to Database"}
              </button>
            </div>
          ) : (
             <div className="flex-1 border-2 border-dashed border-border rounded-xl flex items-center justify-center text-muted-foreground">
                {isAnalyzing ? "Analyzing transcript..." : "The draft will appear here after analysis."}
             </div>
          )}
        </div>
      </div>
    </div>
  );
}
