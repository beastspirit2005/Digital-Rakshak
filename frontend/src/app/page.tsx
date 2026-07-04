import Link from "next/link";
import { Shield, Lock, Activity, Server, Globe2 } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Background Gradients */}
      <div className="absolute top-0 -left-1/4 w-[150%] h-[150%] bg-gradient-to-br from-indigo-500/20 via-transparent to-purple-600/10 -z-10 animate-pulse" style={{ animationDuration: '8s' }} />
      <div className="absolute top-1/4 -right-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[128px] -z-10" />
      <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-purple-600/20 rounded-full blur-[128px] -z-10" />

      {/* Navbar */}
      <nav className="border-b border-border/50 bg-background/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-8 h-8 text-primary" />
            <span className="text-xl font-bold tracking-tight">Digital Rakshak</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <Link href="/" className="text-sm font-medium text-primary hover:text-primary/80 transition-colors">Home</Link>
            <Link href="#how-it-works" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">How it Works</Link>
            <Link href="/report" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Report Scam</Link>
            <Link href="/prevention" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Prevention</Link>
            <Link href="/resources" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Resources</Link>
            <Link href="/about" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">About</Link>
          </div>
          <div className="flex items-center gap-4">
            <ThemeToggle />
            <Link 
              href="/auth/login" 
              className="text-sm font-medium bg-primary text-primary-foreground px-6 py-2 rounded-lg hover:bg-primary/90 transition-all shadow-[0_0_15px_rgba(79,70,229,0.5)]"
            >
              Login
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-6 pt-24 pb-32">
        <div className="flex flex-col md:flex-row items-center justify-between gap-12 animate-in fade-in slide-in-from-bottom-8 duration-1000">
          
          <div className="flex-1 space-y-8 text-left">
            <h1 className="text-5xl md:text-6xl font-bold tracking-tight leading-tight">
              AI-Powered Protection<br/>
              for a Safer <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-purple-400">Digital India</span>
            </h1>
            
            <p className="text-lg text-muted-foreground max-w-xl leading-relaxed">
              Detect scams. Prevent fraud. Empower investigators.<br/><br/>
              Digital Rakshak uses advanced AI to detect digital frauds, empower citizens and investigators, and build a secure digital ecosystem.
            </p>

            <div className="flex flex-col sm:flex-row items-center gap-4 pt-4">
              <Link 
                href="/auth/login"
                className="w-full sm:w-auto text-center bg-primary text-primary-foreground px-8 py-3.5 rounded-lg font-medium hover:bg-primary/90 transition-all shadow-[0_0_20px_rgba(79,70,229,0.4)]"
              >
                SHOULD I TRUST THIS?
              </Link>
              <Link 
                href="/report"
                className="w-full sm:w-auto text-center bg-transparent border border-border text-foreground px-8 py-3.5 rounded-lg font-medium hover:bg-accent transition-all"
              >
                REPORT A SCAM
              </Link>
            </div>
          </div>

          <div className="flex-1 relative flex items-center justify-center">
            {/* Shield Graphic with orbiting nodes */}
            <div className="relative w-80 h-80 flex items-center justify-center">
              {/* Central Shield */}
              <div className="z-10 relative">
                <div className="absolute inset-0 bg-primary/20 blur-2xl rounded-full animate-pulse" />
                <Shield className="w-40 h-40 text-primary drop-shadow-[0_0_15px_rgba(79,70,229,0.8)]" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-4xl font-bold text-primary-foreground">R</span>
                </div>
              </div>
              
              {/* Orbit Rings */}
              <div className="absolute inset-0 border border-primary/20 rounded-full" />
              <div className="absolute -inset-10 border border-primary/10 rounded-full" />
            </div>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="glass-panel mt-24 p-6 rounded-2xl grid grid-cols-2 md:grid-cols-4 gap-8 text-center divide-x divide-border">
          <div>
            <h3 className="text-3xl font-bold text-foreground">1.2M+</h3>
            <p className="text-sm text-muted-foreground mt-1">Threats Detected</p>
          </div>
          <div>
            <h3 className="text-3xl font-bold text-foreground">98.7%</h3>
            <p className="text-sm text-muted-foreground mt-1">Detection Accuracy</p>
          </div>
          <div>
            <h3 className="text-3xl font-bold text-foreground">50K+</h3>
            <p className="text-sm text-muted-foreground mt-1">Cases Investigated</p>
          </div>
          <div className="border-r-0">
            <h3 className="text-3xl font-bold text-foreground">28</h3>
            <p className="text-sm text-muted-foreground mt-1">States Covered</p>
          </div>
        </div>

        {/* Feature Grid */}
        <div id="features" className="grid md:grid-cols-3 gap-8 mt-32 relative z-10">
          <div className="glass-panel p-8 rounded-2xl flex flex-col gap-4 hover:-translate-y-2 transition-transform duration-300">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
              <Globe2 className="w-6 h-6 text-blue-500" />
            </div>
            <h3 className="text-xl font-semibold">Global Threat Feed</h3>
            <p className="text-muted-foreground leading-relaxed">
              Real-time ingestion of malicious IPs, domains, and hashes from global telemetry databases.
            </p>
          </div>

          <div className="glass-panel p-8 rounded-2xl flex flex-col gap-4 hover:-translate-y-2 transition-transform duration-300">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20">
              <Server className="w-6 h-6 text-purple-500" />
            </div>
            <h3 className="text-xl font-semibold">Spatial Analysis</h3>
            <p className="text-muted-foreground leading-relaxed">
              Powered by PostGIS and pgvector for advanced geographical and similarity-based threat hunting.
            </p>
          </div>

          <div className="glass-panel p-8 rounded-2xl flex flex-col gap-4 hover:-translate-y-2 transition-transform duration-300">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
              <Lock className="w-6 h-6 text-emerald-500" />
            </div>
            <h3 className="text-xl font-semibold">Zero-Trust Access</h3>
            <p className="text-muted-foreground leading-relaxed">
              Passwordless, OTP-driven access control with strict RBAC for analysts, admins, and partners.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
