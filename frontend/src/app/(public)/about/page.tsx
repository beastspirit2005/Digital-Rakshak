import type { Metadata } from "next";
import Link from "next/link";
import { 
  ShieldCheck, 
  Cpu, 
  Network, 
  Lock, 
  Users, 
  Building2, 
  CheckCircle2, 
  ArrowRight,
  Flame,
  Globe2,
  FileCheck
} from "lucide-react";

export const metadata: Metadata = {
  title: "About Digital Rakshak | Sovereign Cyber Defense for India",
  description: "Learn about Digital Rakshak's mission, sovereign cybersecurity technology, and 11 specialized AI engines protecting 1.4 billion citizens.",
};

const ENGINES = [
  {
    num: "01",
    name: "Attack DNA Fingerprinting",
    desc: "Extracts cryptographic and behavioural signatures from incoming fraud payloads to detect repeat criminal syndicates across regions.",
  },
  {
    num: "02",
    name: "Heuristic Threat Matcher",
    desc: "Lightweight, ultra-low latency regex and pattern rules that intercept obvious phishing lures, lottery scams, and urgent fear cues in milliseconds.",
  },
  {
    num: "03",
    name: "Neo4j Fraud Graph Correlator",
    desc: "Connects phone numbers, UPI VPAs, IP subnets, and beneficiary mule accounts across state borders into organized crime cluster topologies.",
  },
  {
    num: "04",
    name: "Visual OCR & Forgery Detector",
    desc: "Decodes forged police arrest warrants, fake Supreme Court notices, and counterfeit bank letterheads using deep convolutional vision networks.",
  },
  {
    num: "05",
    name: "APK Decompilation Engine",
    desc: "Static and dynamic dissection of sideloaded Android APKs, inspecting background SMS-reading permissions and remote-access trojans.",
  },
  {
    num: "06",
    name: "Multi-Dialect Indic NLP",
    desc: "Understands high-pressure social engineering scripts across Hindi, Hinglish, Tamil, Telugu, Bengali, Marathi, and English.",
  },
  {
    num: "07",
    name: "Digital Arrest Classifier",
    desc: "Specialized defense pipeline analyzing video/audio intimidation tactics used by extortion rackets impersonating CBI, ED, and Cyber Police.",
  },
  {
    num: "08",
    name: "UPI VPA & Mule Correlator",
    desc: "Cross-checks receiver payment identifiers against known fraudulent bank account rings before money leaves the citizen's wallet.",
  },
  {
    num: "09",
    name: "Domain Typosquatting Sensor",
    desc: "Detects look-alike and homograph phishing URLs spoofing Indian banking portals, electricity boards, and government schemes.",
  },
  {
    num: "10",
    name: "Friction & Redirection Interceptor",
    desc: "Delays rash impulsive payments with high-risk friction modals and educational intervention checks to break criminal hypnotic pressure.",
  },
  {
    num: "11",
    name: "Incident Dossier Generator",
    desc: "Compiles verified technical forensic telemetry into structured, timestamped PDF dossiers formatted specifically for National Helpline 1930 reports.",
  },
];

export default function AboutPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-20 space-y-16">
      
      {/* Hero Section */}
      <div className="text-center max-w-3xl mx-auto space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F59E0B]/10 border border-[#F59E0B]/30 text-[#F59E0B] font-mono text-xs">
          <span>Sovereign Cyber Threat Intelligence</span>
        </div>
        <h1 className="font-display font-extrabold text-3xl sm:text-5xl text-white tracking-tight leading-tight">
          Defending 1.4 Billion Citizens Against Organized Cybercrime.
        </h1>
        <p className="text-base sm:text-lg text-[#94A3B8] leading-relaxed">
          Digital Rakshak is India&apos;s sovereign AI cybersecurity shield. We construct real-time defensive intelligence to stop digital arrest cartels, mule banking rings, and predatory loan APKs before innocent families lose their life savings.
        </p>
      </div>

      {/* Mission & Sovereignty Grid */}
      <div className="grid md:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl bg-[#121B22] border border-[#253540] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <h3 className="font-display font-bold text-lg text-white">Citizen Protection First</h3>
          <p className="text-xs sm:text-sm text-[#94A3B8] leading-relaxed">
            Every citizen deserves institutional-grade cybersecurity. We make deep forensic threat intelligence accessible to anyone with a smartphone, in simple everyday language.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-[#121B22] border border-[#253540] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400 flex items-center justify-center">
            <Lock className="w-5 h-5" />
          </div>
          <h3 className="font-display font-bold text-lg text-white">National Data Sovereignty</h3>
          <p className="text-xs sm:text-sm text-[#94A3B8] leading-relaxed">
            Indian citizen data remains protected within our borders. Governed strictly under India&apos;s DPDP Act 2023 with on-premise AI models and zero third-party commercial profiling.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-[#121B22] border border-[#253540] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 text-[#F59E0B] flex items-center justify-center">
            <Network className="w-5 h-5" />
          </div>
          <h3 className="font-display font-bold text-lg text-white">Ecosystem Collaboration</h3>
          <p className="text-xs sm:text-sm text-[#94A3B8] leading-relaxed">
            Bridging the gap between citizens, law enforcement agencies, and scheduled commercial banks to rapidly identify mule clusters and preserve hard-earned capital.
          </p>
        </div>
      </div>

      {/* The 11 AI Engines Section */}
      <div className="space-y-8">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <p className="font-mono text-xs uppercase tracking-wider text-[#F59E0B] font-bold">
            Proprietary Architecture
          </p>
          <h2 className="font-display font-bold text-2xl sm:text-4xl text-white">
            The 11-Engine Threat Intelligence Core
          </h2>
          <p className="text-sm text-[#94A3B8]">
            Traditional antivirus looks only at known file signatures. Digital Rakshak coordinates 11 concurrent detection disciplines in real-time.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-4">
          {ENGINES.map((engine) => (
            <div 
              key={engine.num}
              className="p-5 rounded-2xl bg-[#121B22] border border-[#253540] hover:border-[#F59E0B]/50 transition-colors space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-[#F59E0B]">
                  ENGINE {engine.num}
                </span>
                <Cpu className="w-4 h-4 text-[#64748B]" />
              </div>
              <h3 className="font-bold text-white text-base leading-snug">
                {engine.name}
              </h3>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                {engine.desc}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Who We Serve Section */}
      <div className="p-8 rounded-3xl bg-[#121B22] border border-[#253540] space-y-6">
        <h2 className="font-display font-bold text-2xl text-white text-center sm:text-left">
          Serving India&apos;s Entire Digital Defense Spectrum
        </h2>
        
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 pt-2">
          <div className="space-y-2">
            <span className="font-bold text-white block text-sm">Citizens & Elders</span>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              Instant verification of scary WhatsApp calls, parcel delivery SMS scams, and spurious lottery notifications before panic strikes.
            </p>
          </div>

          <div className="space-y-2">
            <span className="font-bold text-white block text-sm">Startups & SMBs</span>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              Protection against domain spoofing, executive impersonation (CEO fraud), and fake vendor payment details.
            </p>
          </div>

          <div className="space-y-2">
            <span className="font-bold text-white block text-sm">Financial Institutions</span>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              High-throughput B2B API integrations to score outbound UPI transactions and detect dormant mule account activations.
            </p>
          </div>

          <div className="space-y-2">
            <span className="font-bold text-white block text-sm">Law Enforcement</span>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              Dedicated officer dashboards to visualize multi-state syndicate linkages, money laundering trails, and automated evidence packets.
            </p>
          </div>
        </div>

        <div className="pt-6 border-t border-[#253540] flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-[#CBD5E1]">
            Ready to secure your personal digital identity or deploy enterprise threat feeds?
          </p>
          <div className="flex items-center gap-3">
            <Link
              href="/personal"
              className="px-4 py-2 rounded-xl bg-[#F59E0B] hover:bg-[#D97706] text-[#08131A] font-bold text-xs transition-colors shadow-sm"
            >
              Start Free Shield
            </Link>
            <Link
              href="/contact"
              className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-semibold transition-colors"
            >
              Enterprise Contact
            </Link>
          </div>
        </div>
      </div>

    </div>
  );
}
