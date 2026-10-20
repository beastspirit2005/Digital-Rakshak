import type { Metadata } from "next";
import Link from "next/link";
import { Eye, CheckCircle2, ShieldCheck, Mail, Sparkles, Sliders } from "lucide-react";

export const metadata: Metadata = {
  title: "Accessibility Statement | Digital Rakshak",
  description: "Digital Rakshak's commitment to digital accessibility, WCAG 2.1 AA conformance, and inclusive cyber defense for all citizens.",
};

export default function AccessibilityPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      
      {/* Header */}
      <div className="mb-12 border-b border-[#253540] pb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-mono text-xs mb-4">
          <Eye className="w-3.5 h-3.5" />
          <span>Universal Digital Inclusivity</span>
        </div>
        <h1 className="font-display font-extrabold text-3xl sm:text-5xl tracking-tight text-white mb-4">
          Accessibility Statement
        </h1>
        <p className="text-sm sm:text-base text-[#94A3B8] leading-relaxed">
          Digital defense must be accessible to every citizen, regardless of physical ability, device type, or assistive technology.
        </p>
      </div>

      {/* Main Content */}
      <div className="space-y-10 text-sm sm:text-base text-[#CBD5E1] leading-relaxed font-sans">
        
        {/* Section 1: Commitment */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            1. Our Commitment to Accessibility
          </h2>
          <p>
            At Digital Rakshak, we believe that cybersecurity is a fundamental civil safeguard. Victims of predatory digital arrest calls or loan harassment span diverse age groups and varying physical capabilities. We are actively committed to ensuring our platform conforms to the <strong>Web Content Accessibility Guidelines (WCAG) 2.1 Level AA</strong> specifications.
          </p>
        </section>

        {/* Section 2: Concrete Measures */}
        <section className="space-y-4">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            2. Measures Taken Across Our Platform
          </h2>
          
          <div className="grid sm:grid-cols-2 gap-4">
            
            <div className="p-5 rounded-xl bg-[#121B22] border border-[#253540] space-y-2">
              <span className="font-bold text-white text-sm flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>High-Contrast Color Palette</span>
              </span>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                Our interface is engineered with deep obsidian dark backgrounds and radiant saffron/emerald accents, rigorously calibrated to exceed the 4.5:1 contrast ratio required for comfortable readability by low-vision users.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-[#121B22] border border-[#253540] space-y-2">
              <span className="font-bold text-white text-sm flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Full Keyboard Operability</span>
              </span>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                Every navigation link, threat scanner input, button, and modal popup is completely operable using standard keyboard controls (<kbd className="px-1.5 py-0.5 rounded bg-white/10 text-xs font-mono">Tab</kbd>, <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-xs font-mono">Enter</kbd>, <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-xs font-mono">Esc</kbd>) with visible focus rings.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-[#121B22] border border-[#253540] space-y-2">
              <span className="font-bold text-white text-sm flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Screen Reader Semantics</span>
              </span>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                We utilize semantic HTML5 elements (<code className="text-[#F59E0B]">&lt;nav&gt;</code>, <code className="text-[#F59E0B]">&lt;main&gt;</code>, <code className="text-[#F59E0B]">&lt;header&gt;</code>, <code className="text-[#F59E0B]">&lt;footer&gt;</code>) along with descriptive ARIA attributes and icon labels to provide assistive readers with lucid contextual cues.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-[#121B22] border border-[#253540] space-y-2">
              <span className="font-bold text-white text-sm flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Reduced Motion Support</span>
              </span>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                For visitors who experience vestibular disorders or motion sickness, our application respects your operating system&apos;s <code className="text-[#F59E0B]">prefers-reduced-motion</code> setting, immediately disabling rapid animations and transitions.
              </p>
            </div>

          </div>
        </section>

        {/* Section 3: Ongoing Improvements */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            3. Continuous Auditing & Known Limitations
          </h2>
          <p>
            While we continually audit our code with automated scanners (such as Axe-core and Lighthouse) and manual review, some complex interactive visual components (such as multi-node Neo4j threat graph visualizers) may contain technical complexities for non-visual navigation. We provide tabular data alternatives and text-based incident summaries for all visual graph representations.
          </p>
        </section>

        {/* Section 4: Feedback Channel */}
        <section className="space-y-3 pt-4 border-t border-[#253540]">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            4. Accessibility Feedback & Assistance
          </h2>
          <p>
            If you encounter any accessibility barriers while using Digital Rakshak, or if you need information provided in an alternative format, our engineering team is here to assist:
          </p>
          <div className="p-5 rounded-xl bg-[#121B22] border border-[#253540] space-y-2 text-xs sm:text-sm">
            <p><strong className="text-white">Accessibility Desk:</strong> Submit an inquiry via our <Link href="/contact?category=Technical+Support" className="text-[#F59E0B] underline font-semibold">Technical Support & Accessibility Desk &rarr;</Link></p>
            <p><strong className="text-white">Response Turnaround:</strong> We acknowledge accessibility reports within 48 hours and prioritize remediation in sprint deployments.</p>
          </div>
        </section>

      </div>

    </div>
  );
}
