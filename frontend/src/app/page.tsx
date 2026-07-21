"use client";

import Link from "next/link";
import { 
  ArrowRight, 
  CheckCircle2, 
  Activity, 
  MoreHorizontal, 
  Link2, 
  PhoneOff, 
  TrendingUp, 
  CheckCheck, 
  Lock 
} from "lucide-react";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { Card } from "@/components/ui/card";
import { useAuthStore } from "@/lib/auth-store";
import { useState, useEffect, useRef } from "react";
import { BrandIdentity } from "@/components/brand-identity";
import { BrandLogo } from "@/components/brand-logo";
import { AnimatedCounter } from "@/components/animated-counter";
import { FAQSection } from "@/components/landing/FAQsection";
import { NationalAlertTicker } from "@/components/landing/NationalAlertTicker";
const STEPS = [
  {
    stepNumber: "01",
    title: "Tell us what happened",
    body: "Paste the message, upload a screenshot, or just speak. Reporting takes about two minutes and works in your language.",
  },
  {
    stepNumber: "02",
    title: "Eleven AI engines take it apart",
    body: "The report is classified, fingerprinted, and cross-referenced against national intelligence — phone numbers, accounts, and domains included.",
  },
  {
    stepNumber: "03",
    title: "The right people act",
    body: "Linked cases surface organized networks. Investigators get the full analysis; banks get freeze requests; you get updates.",
  },
];

const STATS = [
  {
    value: 1.2,
    decimals: 1,
    suffix: "M+",
    label: "threats detected",
  },
  {
    value: 98.7,
    decimals: 1,
    suffix: "%",
    label: "detection accuracy",
  },
  {
    value: 50,
    decimals: 0,
    suffix: "K+",
    label: "cases investigated",
  },
  {
    value: 28,
    decimals: 0,
    suffix: "",
    label: "states covered",
  },
];

export default function LandingPage() {
  const { isAuthenticated } = useAuthStore();
  const [mounted, setMounted] = useState(false);
  const reduced = useReducedMotion();

  const howItWorksRef = useRef<HTMLElement>(null);
  const { scrollYProgress: howItWorksProgress } = useScroll({
    target: howItWorksRef,
    offset: ["start end", "start 0.35"],
  });
  const howItWorksBg = useTransform(
    howItWorksProgress,
    [0, 1],
    ["#020617", "#ffffff"]
  );

  useEffect(() => {
    setMounted(true);
  }, []);

  const getHref = (path: string) => {
    if (!mounted) return path;
    return isAuthenticated ? path : `/auth/login?next=${encodeURIComponent(path)}`;
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] selection:bg-[#F59E0B] selection:text-[#08131A] overflow-x-hidden">
      {/* Premium Navy Header */}
      <nav className="sticky top-0 z-50 bg-[#0a0a0c]/95 border-b border-white/8 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 min-w-0">
            <span className="flex items-center justify-center shrink-0 w-9 h-9 rounded-lg bg-[#18181c] border border-white/10">
              <BrandLogo size={22} />
            </span>
            <span className="min-w-0">
              <span className="block font-display text-[17px] font-bold tracking-tight leading-none text-[#E7EEF3]">
                Digital Rakshak
              </span>
              <span className="hidden sm:block mt-1 text-[9px] font-medium tracking-[0.22em] uppercase text-[#8293AA]">
                Cyber Threat Intelligence for India
              </span>
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-8">
            <a href="#about" className="text-sm font-medium text-[#A7B4BD] hover:text-[#E7EEF3] transition-colors">
              About
            </a>
            <a href="#how-it-works" className="text-sm font-medium text-[#A7B4BD] hover:text-[#E7EEF3] transition-colors">
              How it works
            </a>
            <a href="#features" className="text-sm font-medium text-[#A7B4BD] hover:text-[#E7EEF3] transition-colors">
              Features
            </a>
            <a
  href="#faq"
  className="text-sm font-medium text-[#A7B4BD] hover:text-[#E7EEF3] transition-colors"
>
    FAQ
</a>
          </div>

          <div className="flex items-center gap-4">
            <Link
              href="/auth/login"
              className="inline-flex items-center h-9 px-4 rounded-control text-sm font-semibold bg-[#18181c] border border-white/10 text-[#E7EEF3] hover:bg-[#232328] transition-all duration-150"
            >
              Sign in
            </Link>
          </div>
        </div>
      </nav>

      <main>
        {/* Dark Navy Cybersecurity Hero */}
        <section 
          id="about" 
          className="bg-[#020617] text-[#E7EEF3] relative overflow-hidden border-b border-[#253540]/20 pt-16 pb-24 sm:pt-28 sm:pb-32"
        >
          {/* Cyber security command center background layout */}
          <div 
            className="absolute inset-0 bg-[position:right_center] bg-cover bg-no-repeat pointer-events-none"
            style={{ 
              backgroundImage: "url('/hackerimg.png')",
              opacity: 1.2
            }} 
          />

          {/* Premium customized 5-stop cinematic gradient overlay */}
          <div 
            className="absolute inset-0 pointer-events-none" 
            style={{
  background: `
    linear-gradient(
      90deg,
      rgba(2,6,23,0.98) 0%,
      rgba(4,14,32,0.92) 20%,
      rgba(8,20,40,0.65) 45%,
      rgba(255,153,51,0.18) 70%,
      rgba(255,153,51,0.08) 100%
    )
  `,
}}/>

          {/* Soft ambient lighting and glows */}
          <div className="absolute right-0 top-1/4 w-[600px] h-[600px] rounded-full bg-[radial-gradient(circle_at_center,rgba(245,158,11,0.22)_0%,transparent_70%)] pointer-events-none mix-blend-screen" />
          <div className="absolute left-1/4 bottom-1/4 w-[500px] h-[500px] rounded-full bg-[radial-gradient(circle_at_center,rgba(14,165,233,0.08)_0%,transparent_70%)] pointer-events-none" />
          
          {/* Subtle vector grid effect */}
          <div className="absolute inset-0 bg-[linear-gradient(rgba(37,53,64,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(37,53,64,0.05)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />
          
          <div className="max-w-[1550px] mx-auto px-8 relative z-10 grid lg:grid-cols-12 gap-8 items-center">
            
            {/* LEFT (35% on Desktop) - Device Mockups */}
                          <div className="lg:col-span-5 w-full flex items-center justify-start ml-6 relative">
                          <div className="absolute w-[320px] h-[320px] bg-[#F59E0B]/5 blur-[80px] rounded-full pointer-events-none animate-pulse" />
              
              <motion.div 
                initial={reduced ? {} : { opacity: 0, y: 30 }}
                animate={reduced ? {} : { opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                className="relative w-full max-w-[600px] sm:max-w-[650px]"
              >
                {/* LAPTOP HARDWARE */}
                <div className="relative w-full bg-[#121F26] rounded-t-2xl border-t border-x border-[#33414A] p-1 shadow-2xl">
                  {/* Laptop Screen Bezel */}
                  <div className="relative w-full bg-black rounded-t-[10px] p-1.5 sm:p-2.5 overflow-hidden">
                    {/* Centered Camera */}
                    <div className="absolute top-1.5 left-1/2 -translate-x-1/2 w-1.5 h-1.5 bg-[#17232A] rounded-full z-20" />
                    
                    {/* Laptop Screen Display */}
                    <div className="w-full aspect-[16/10] bg-[#F8FAFC] rounded-md p-2.5 sm:p-3 relative overflow-hidden flex flex-col justify-between border border-[#E2E8F0]">
                      {/* Grid Telemetry Map overlay */}
                      <div className="absolute inset-0 bg-[linear-gradient(rgba(226,232,240,0.5)_1px,transparent_1px),linear-gradient(90deg,rgba(226,232,240,0.5)_1px,transparent_1px)] bg-[size:16px_16px] pointer-events-none" />
                      
                      {/* Dashboard Header */}
                      <div className="relative z-10 flex items-center justify-between border-b border-[#E2E8F0] pb-1.5">
                        <div className="flex items-center gap-1.5">
                          <BrandLogo size={20} />
                          <div>
                            <p className="font-display font-black text-[8.5px] sm:text-[9.5px] text-[#0F172A] leading-none tracking-tight">
                              DIGITAL RAKSHAK 
                            </p>
                            <p className="text-[5px] sm:text-[6px] tracking-widest text-[#64748B] uppercase font-mono font-bold mt-0.5">
                              Threat Command Panel
                            </p>
                          </div>
                        </div>
                        <span className="font-mono text-[6px] sm:text-[7px] text-[#F59E0B] font-bold border border-[#F59E0B]/30 px-1 py-0.5 bg-[#F59E0B]/5 rounded">
                          TELEMETRY FEED
                        </span>
                      </div>

                      {/* Command Statistics Row */}
                      <div className="relative z-10 grid grid-cols-4 gap-1.5 mt-2">
                        <div className="bg-white border border-[#E2E8F0] rounded p-1 shadow-sm">
                          <span className="block font-mono text-[5px] sm:text-[5.5px] font-bold text-[#64748B] tracking-wider uppercase">THREATS</span>
                          <span className="block font-display font-extrabold text-[10px] sm:text-[11px] text-[#0F172A] mt-0.5">
                            <AnimatedCounter
                              value={1.2}
                              decimals={1}
                              suffix="M+"
                              duration={700}
                            />
                          </span>
                        </div>
                        <div className="bg-white border border-[#E2E8F0] rounded p-1 shadow-sm">
                          <span className="block font-mono text-[5px] sm:text-[5.5px] font-bold text-[#64748B] tracking-wider uppercase">ACCURACY</span>
                          <span className="block font-display font-extrabold text-[10px] sm:text-[11px] text-[#00D9A3] mt-0.5">
                            <AnimatedCounter
                              value={98.7}
                              decimals={1}
                              suffix="%"
                              duration={800}
                            />
                          </span>
                        </div>
                        <div className="bg-white border border-[#E2E8F0] rounded p-1 shadow-sm">
                          <span className="block font-mono text-[5px] sm:text-[5.5px] font-bold text-[#64748B] tracking-wider uppercase">INVESTIGATED</span>
                          <span className="block font-display font-extrabold text-[10px] sm:text-[11px] text-[#0F172A] mt-0.5">
                            <AnimatedCounter
                              value={50}
                              suffix="K+"
                              duration={750}
                            />
                          </span>
                        </div>
                        <div className="bg-white border border-[#E2E8F0] rounded p-1 shadow-sm">
                          <span className="block font-mono text-[5px] sm:text-[5.5px] font-bold text-[#64748B] tracking-wider uppercase">COVERAGE</span>
                          <span className="block font-display font-extrabold text-[10px] sm:text-[11px] text-[#F59E0B] mt-0.5">
                            <AnimatedCounter
                              value={28}
                              suffix=" STATES"
                              duration={650}
                            />
                          </span>
                        </div>
                      </div>

                      {/* Chart & Telemetry Row */}
                      <div className="relative z-10 flex-1 grid grid-cols-5 gap-2 mt-2 min-h-0">
                        {/* Threat Trend Vector Chart */}
                        <div className="col-span-3 bg-white border border-[#E2E8F0] rounded p-1.5 flex flex-col justify-between shadow-sm">
                          <span className="font-mono text-[5px] sm:text-[6px] tracking-wider text-[#64748B] uppercase font-bold flex items-center gap-1">
                            <TrendingUp className="w-2.5 h-2.5 text-[#F59E0B]" />
                            Threat Activity
                          </span>
                          <div className="flex-1 w-full flex items-center justify-center pt-1.5">
                            <svg className="w-full h-full min-h-[30px]" viewBox="0 0 100 30" preserveAspectRatio="none">
                              <defs>
                                <linearGradient id="chartGlow" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.1" />
                                  <stop offset="100%" stopColor="#F59E0B" stopOpacity="0.0" />
                                </linearGradient>
                              </defs>
                              <line x1="0" y1="10" x2="100" y2="10" stroke="#F1F5F9" strokeWidth="0.5" />
                              <line x1="0" y1="20" x2="100" y2="20" stroke="#F1F5F9" strokeWidth="0.5" />
                              <motion.path
                                d="M 0,25 C 20,20 30,10 50,15 C 70,20 80,5 100,8"
                                fill="none"
                                stroke="#F59E0B"
                                strokeWidth="1.5"
                                strokeLinecap="round"
                                initial={reduced ? {} : { pathLength: 0, opacity: 0 }}
                                animate={reduced ? {} : { pathLength: 1, opacity: 1 }}
                                transition={{
                                  delay: 0.45,
                                  duration: 0.9,
                                  ease: [0.16, 1, 0.3, 1],
                                }}
                              />
                              <path 
                                d="M 0,25 C 20,20 30,10 50,15 C 70,20 80,5 100,8 L 100,30 L 0,30 Z" 
                                fill="url(#chartGlow)"
                              />
                              <circle cx="50" cy="15" r="1.2" fill="#F59E0B" />
                              <circle cx="100" cy="8" r="1.2" fill="#F59E0B" />
                            </svg>
                          </div>
                        </div>

                        {/* Live telemetry alert cluster */}
                        <div className="col-span-2 bg-white border border-[#E2E8F0] rounded p-1.5 flex flex-col justify-between shadow-sm">
                          <span className="font-mono text-[5px] sm:text-[6px] tracking-wider text-[#64748B] uppercase font-bold">Live Streams</span>
                          <div className="space-y-1 mt-1 text-[5px] sm:text-[6px] leading-tight">
                            <div className="flex items-start gap-1">
                              <span className="w-1 h-1 rounded-full bg-[#EF4444] mt-0.5 shrink-0 animate-pulse" />
                              <p className="text-[#0F172A] truncate max-w-[54px] font-semibold">UPI Fraud NCR</p>
                            </div>
                            <div className="flex items-start gap-1">
                              <span className="w-1 h-1 rounded-full bg-[#F59E0B] mt-0.5 shrink-0" />
                              <p className="text-[#64748B] truncate max-w-[54px] font-medium">Phish MH</p>
                            </div>
                            <div className="flex items-start gap-1">
                              <span className="w-1 h-1 rounded-full bg-[#00D9A3] mt-0.5 shrink-0 animate-pulse" />
                              <p className="text-[#64748B] truncate max-w-[54px] font-medium">APK Malware KA</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Laptop Key Base chassis */}
                  <div className="w-[106%] h-2.5 bg-[#33414A] rounded-b-lg border-b border-x border-[#253540] absolute bottom-[-10px] left-1/2 -translate-x-1/2 flex items-center justify-center">
                    <div className="w-14 h-0.5 bg-black/60 rounded-b" />
                  </div>
                </div>

                {/* PHONE COMPONENT */}
                <motion.div 
                  initial={reduced ? {} : { opacity: 0, x: 20 }}
                  animate={reduced ? {} : { opacity: 1, x: 0 }}
                  transition={{ delay: 0.35, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                  className="absolute bottom-[-16px] right-[-10px] sm:right-[-16px] z-20 w-[140px] sm:w-[155px] aspect-[9/16] bg-[#0C151B] border-[6px] border-[#33414A] rounded-[24px] shadow-2xl overflow-hidden flex flex-col shrink-0"
                >
                  {/* Smartphone dynamic island speaker detail */}
                  <div className="absolute top-1 left-1/2 -translate-x-1/2 w-10 h-2 bg-[#33414A] rounded-full z-30 flex items-center justify-center">
                    <div className="w-4 h-0.5 bg-[#17232A] rounded-full" />
                  </div>

                  {/* Smartphone screen contents */}
                  <div className="flex-1 bg-[#F8FAFC] pt-4.5 px-2 pb-2 flex flex-col gap-1.5 select-none text-[8px] relative border border-[#E2E8F0] rounded-[18px]">
                    <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-1">
                      <div className="flex items-center gap-1">
                        <BrandLogo size={13} />
                        <span className="font-display font-extrabold text-[7.5px] text-[#0F172A]">Rakshak</span>
                      </div>
                      <span className="text-[7.5px] font-bold text-[#00D9A3] flex items-center gap-0.5 font-mono">
                        <span className="w-1 h-1 rounded-full bg-[#00D9A3] animate-pulse" />
                        Protected
                      </span>
                    </div>

                    {/* App protected details card */}
                    <div className="bg-white border border-[#E2E8F0] rounded p-1.5 flex flex-col gap-0.5 shadow-sm">
                      <p className="text-[6.5px] tracking-wider text-[#64748B] font-mono font-bold uppercase">Recent Analysis</p>
                      <p className="text-[11px] font-black text-[#00D9A3] tracking-tight font-display leading-none">99% Secure</p>
                      <p className="text-[6px] text-[#64748B] leading-snug mt-0.5">
                        Last 14 calls analyzed. 3 blocked.
                      </p>
                    </div>

                    {/* App history logs feed */}
                    <div className="bg-white border border-[#E2E8F0] rounded p-1.5 flex-1 overflow-hidden flex flex-col justify-between shadow-sm">
                      <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-0.5">
                        <span className="font-bold text-[#0F172A] text-[7px] tracking-wide">Action History</span>
                        <MoreHorizontal className="w-2.5 h-2.5 text-[#64748B]" />
                      </div>

                      <div className="space-y-1 mt-1 flex-1 flex flex-col justify-center">
                        <div className="flex items-center gap-1.5">
                          <span className="w-4 h-4 rounded bg-[#00D9A3]/10 border border-[#00D9A3]/20 flex items-center justify-center shrink-0">
                            <CheckCheck className="w-2 h-2 text-[#00D9A3]" />
                          </span>
                          <div className="min-w-0 flex-1 leading-none">
                            <p className="text-[7px] font-semibold text-[#0F172A] truncate">UPI Verified</p>
                            <p className="text-[5.5px] text-[#00D9A3] font-mono font-medium">Safe</p>
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5">
                          <span className="w-4 h-4 rounded bg-[#EF4444]/10 border border-[#EF4444]/20 flex items-center justify-center shrink-0">
                            <PhoneOff className="w-2 h-2 text-[#EF4444]" />
                          </span>
                          <div className="min-w-0 flex-1 leading-none">
                            <p className="text-[7px] font-semibold text-[#0F172A] truncate">AI Blocked</p>
                            <p className="text-[5.5px] text-[#EF4444] font-mono font-medium">Scam Pattern</p>
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5">
                          <span className="w-4 h-4 rounded bg-[#F59E0B]/10 border border-[#F59E0B]/20 flex items-center justify-center shrink-0">
                            <Lock className="w-2 h-2 text-[#F59E0B]" />
                          </span>
                          <div className="min-w-0 flex-1 leading-none">
                            <p className="text-[7px] font-semibold text-[#0F172A] truncate">QR Scan</p>
                            <p className="text-[5.5px] text-[#F59E0B] font-mono font-medium">Under Review</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              </motion.div>
            </div>

            {/* CENTER (30% on Desktop) - Text Content Block */}
            <motion.div
              initial={reduced ? {} : "hidden"}
              animate={reduced ? undefined : "visible"}
              variants={{
                hidden: {},
                visible: {
                  transition: {
                    staggerChildren: 0.09,
                  },
                },
              }}
              className="lg:col-span-6 lg:col-start-7 flex flex-col justify-center order-1 lg:order-2 pl-6"
              >
              <motion.div
                variants={{
                  hidden: { opacity: 0, y: 10 },
                  visible: {
                    opacity: 1.3,
                    y: 0,
                    transition: {
                      duration: 0.4,
                      ease: [0.16, 1, 0.3, 1],
                    },
                  },
                }}
                className="inline-flex items-center gap-2 bg-[#17232A] border border-[#253540] px-3.5 py-1.5 rounded-pill text-xs font-semibold text-[#F59E0B] tracking-wide mb-6 uppercase w-fit"
              >
                <span className="flex h-1.5 w-1.5 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00D9A3] opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[#00D9A3]"></span>
                </span>
                Cyber threat intelligence for India
              </motion.div>
              
              <motion.h1
                variants={{
                  hidden: { opacity: 0, y: 16 },
                  visible: {
                    opacity: 1,
                    y: 0,
                    transition: {
                      duration: 0.5,
                      ease: [0.16, 1, 0.3, 1],
                    },
                  },
                }}
                className="font-display font-bold text-2xl sm:text-[2.75rem] leading-[1] tracking-tight text-[#E7EEF3]"
              >
                One report can <br className="hidden sm:inline" />
                take down an entire <br className="hidden sm:inline" />
                <span className="text-[#F59E0B] drop-shadow-[0_4px_12px_rgba(245,158,11,0.15)]">scam network.</span>
              </motion.h1>
              
              <motion.p
                variants={{
                  hidden: { opacity: 0, y: 14 },
                  visible: {
                    opacity: 1,
                    y: 0,
                    transition: {
                      duration: 0.45,
                      ease: [0.16, 1, 0.3, 1],
                    },
                  },
                }}
                className="text-base sm:text-lg text-[#A7B4BD] mt-6 max-w-[700px] leading-relaxed font-sans"
              >
                Digital Rakshak analyzes cyber threat signals with AI, connects related cases across India, and turns scattered reports into actionable intelligence.
              </motion.p>
              
              <motion.div
                variants={{
                  hidden: { opacity: 0, y: 14 },
                  visible: {
                    opacity: 1,
                    y: 0,
                    transition: {
                      duration: 0.45,
                      ease: [0.16, 1, 0.3, 1],
                    },
                  },
                }}
                className="flex flex-row gap-4 mt-8 flex-wrap"
              >
                <Link
                  href={getHref("/report")}
                  className="inline-flex items-center justify-center h-12 px-6 rounded-control bg-[#F59E0B] text-[#08131A] font-bold text-sm hover:bg-[#F97316] hover:shadow-[0_4px_20px_rgba(245,158,11,0.25)] transition-all duration-150 active:scale-[0.98] group shrink-0"
                >
                  Report a scam
                  <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-0.5 transition-transform" />
                </Link>
                <Link
                  href={getHref("/prevention")}
                  className="inline-flex items-center justify-center h-12 px-6 rounded-control bg-[#17232A] text-[#E7EEF3] border border-[#253540] font-semibold text-sm hover:bg-[#1b282f] hover:border-[#33414a] transition-colors duration-150 shrink-0"
                >
                  Check a suspicious link
                </Link>
              </motion.div>
            </motion.div>

           

          </div>
        </section>
    <NationalAlertTicker />
        {/* Animated Enterprise Trust Statistics */}
        <section
          id="features"
          className="bg-[#020617] border-y border-[#253540]/20 py-14"
        >
          <div className="max-w-[1500px] mx-auto px-6">
            <motion.div
              initial={reduced ? {} : "hidden"}
              whileInView={reduced ? undefined : "visible"}
              viewport={{ once: true, amount: 0.35 }}
              variants={{
                hidden: {},
                visible: {
                  transition: {
                    staggerChildren: 0.08,
                  },
                },
              }}
              className="grid grid-cols-2 md:grid-cols-4 gap-8"
            >
              {STATS.map((stat) => (
                <motion.div
                  key={stat.label}
                  variants={{
                    hidden: {
                      opacity: 0,
                      y: 14,
                    },
                    visible: {
                      opacity: 1,
                      y: 0,
                      transition: {
                        duration: 0.4,
                        ease: [0.16, 1, 0.3, 1],
                      },
                    },
                  }}
                  className="border-l-2 border-[#253540]/40 pl-5 py-1"
                >
                  <p className="font-display font-extrabold text-2xl sm:text-3xl tracking-tight text-[#E7EEF3] tabular">
                    <AnimatedCounter
                      value={stat.value}
                      decimals={stat.decimals}
                      suffix={stat.suffix}
                      duration={850}
                    />
                  </p>

                  <p className="text-xs font-semibold text-[#A7B4BD] uppercase tracking-wider mt-1">
                    {stat.label}
                  </p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* How it Works Section — background turns black→white as it scrolls into view */}
        <motion.section
          id="how-it-works"
          ref={howItWorksRef}
          style={reduced ? { backgroundColor: "#ffffff" } : { backgroundColor: howItWorksBg }}
          className="py-20 sm:py-28"
        >
          <div className="max-w-6xl mx-auto px-6">
            <div className="text-center max-w-2xl mx-auto mb-16">
              <p className="font-serif italic text-lg text-[#64748B] mb-2">How it works</p>
              <h2 className="font-display font-bold text-2xl sm:text-3xl tracking-tight text-[#08131A]">
                From a two-minute report to organized-crime intelligence.
              </h2>
            </div>
            
            <div className="grid md:grid-cols-3 gap-6 lg:gap-8 mt-12">
              {STEPS.map((step) => (
                <Card 
                  key={step.title} 
                  className="p-8 bg-[#F8FAFC] border border-[#E2E8F0] shadow-sm rounded-card relative hover:shadow-md hover:border-[#CBD5E1] transition-all duration-200"
                >
                  <div className="font-mono font-extrabold text-xs tracking-widest text-[#F59E0B] mb-5 flex items-center justify-between">
                    <span>STAGE {step.stepNumber}</span>
                    <CheckCircle2 className="w-4 h-4 text-[#CBD5E1]" />
                  </div>
                  <h3 className="font-display font-bold text-lg text-[#08131A] leading-snug">
                    {step.title}
                  </h3>
                  <p className="text-sm text-[#475569] mt-3 leading-relaxed">
                    {step.body}
                  </p>
                </Card>
              ))}
            </div>
          </div>
        </motion.section>
<FAQSection />
       
      </main>

      {/* Cyber Premium Footer */}
      <footer className="bg-[#050D12] text-[#A7B4BD] border-t border-[#253540]/30">
        <div className="max-w-6xl mx-auto px-6 py-10 flex flex-col sm:flex-row items-center justify-between gap-6">
          <BrandIdentity compact fixedDark />
          <p className="text-xs text-[#64748B] text-center sm:text-right max-w-md leading-relaxed">
            AI-assisted analysis supports, but does not replace, official investigation.
          </p>
        </div>
      </footer>
    </div>
  );
}