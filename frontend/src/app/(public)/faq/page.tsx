"use client";

import { useState, useMemo } from "react";
import { Search, ChevronDown, HelpCircle, Shield, CreditCard, Lock, Building, Sparkles } from "lucide-react";
import Link from "next/link";

interface FAQItem {
  id: string;
  category: "General" | "Scanners" | "Billing" | "Privacy" | "Enterprise";
  question: string;
  answer: string | React.ReactNode;
}

const FAQS: FAQItem[] = [
  {
    id: "what-is-digital-rakshak",
    category: "General",
    question: "What is Digital Rakshak?",
    answer: "Digital Rakshak is an Indian cyber threat intelligence platform engineered to protect citizens and enterprises against digital fraud, phishing, fake arrest notices, loan APK traps, and mule bank account networks using 11 specialized AI engines.",
  },
  {
    id: "how-does-detection-work",
    category: "Scanners",
    question: "How does scam detection work?",
    answer: "When you enter a suspect indicator (such as a URL, suspicious message, phone number, or APK file), our platform coordinates 11 detection engines: heuristic regex matching, neural NLP reasoning, visual OCR for forged logos/warrants, APK decompilation for predatory permissions, and Neo4j graph cross-referencing.",
  },
  {
    id: "what-can-i-scan",
    category: "Scanners",
    question: "What types of indicators can I scan?",
    answer: "You can scan URLs and domains, SMS & WhatsApp messages, phone numbers, UPI VPAs (e.g., scammer@okhdfcbank), screenshot images of fake warrants/bills, and Android APK installation packages.",
  },
  {
    id: "low-risk-guarantee",
    category: "Scanners",
    question: "Does a low-risk score guarantee 100% safety?",
    answer: "No. Automated AI risk scoring is probabilistic. A 'Low Risk' score means no known malicious indicators or heuristic anomalies were triggered at that moment. Because fraudsters constantly deploy brand-new domains and accounts, you must always independently verify high-value fund requests.",
  },
  {
    id: "free-plan-features",
    category: "Billing",
    question: "What is included in the Free Shield plan?",
    answer: "The Free Shield plan gives all citizens access to core heuristic threat scanning with up to 5 scans per day, community scam advisories, and basic guidance on reporting fraud to National Helpline 1930 at zero cost.",
  },
  {
    id: "pro-features-pricing",
    category: "Billing",
    question: "What does Pro Protection include and what are the exact prices?",
    answer: (
      <span>
        Digital Rakshak offers three consumer Pro tiers:
        <br /><br />
        1. <strong>Personal Pro:</strong> ₹149/mo base + 18% GST (₹26.82) = <strong>₹175.82 gross / month</strong>. Includes unlimited scans, 11-engine AI deep scan, APK decompilation, priority alerts, and downloadable PDF forensic dossiers.
        <br />
        2. <strong>Family Shield:</strong> ₹249/mo base + 18% GST (₹44.82) = <strong>₹293.82 gross / month</strong>. Protects up to 5 family member accounts with elder protection mode.
        <br />
        3. <strong>Personal Pro Annual:</strong> ₹1,299/yr base + 18% GST (₹233.82) = <strong>₹1,532.82 gross / year</strong> (save ~27% over monthly billing) for 365 days of comprehensive protection.
      </span>
    ),
  },
  {
    id: "how-to-cancel",
    category: "Billing",
    question: "How do I cancel my subscription?",
    answer: "You can cancel your subscription with a single click at any time from your Personal Shield dashboard under Settings &rarr; Billing. Your Pro access remains active until the end of your prepaid billing period, with zero penalty.",
  },
  {
    id: "where-is-invoice",
    category: "Billing",
    question: "Where can I download my GST tax invoice?",
    answer: "All transactions are billed under SAC Code 998313 with official GST compliance. You can instantly download your official GST PDF invoices under Personal Shield &rarr; Billing history.",
  },
  {
    id: "delete-scan-history",
    category: "Privacy",
    question: "How can I delete my scan history?",
    answer: "You have complete control over your scan history. You can click 'Clear History' in your Personal Shield dashboard at any time, which triggers our DELETE /v1/scan/history API to permanently wipe your historical scans.",
  },
  {
    id: "monitor-phone",
    category: "Privacy",
    question: "Does Digital Rakshak monitor every application on my phone?",
    answer: "No. Digital Rakshak strictly operates on user-submitted artifacts and explicit permission grants. We do NOT run intrusive spyware, background keyloggers, or record private phone conversations.",
  },
  {
    id: "enterprise-integration",
    category: "Enterprise",
    question: "How can a company integrate Digital Rakshak APIs?",
    answer: "Enterprises and fintech platforms can generate REST API keys through our Business Console to perform high-speed transaction risk scoring, webhook threat event streaming, and bulk domain telemetry. Visit our Business Console or contact sales to get started.",
  },
  {
    id: "report-vulnerability",
    category: "Enterprise",
    question: "How do I report a security vulnerability (VDP)?",
    answer: "We run a Responsible Vulnerability Disclosure Program. Ethical researchers can review our safe-harbor terms on our Security Disclaimer page and submit proofs-of-concept securely through our Vulnerability Disclosure Helpdesk Portal under the Security category.",
  },
];

const CATEGORIES = ["All", "General", "Scanners", "Billing", "Privacy", "Enterprise"] as const;

export default function FAQPage() {
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<string>("All");
  const [openItems, setOpenItems] = useState<Record<string, boolean>>({
    "what-is-digital-rakshak": true,
    "pro-features-pricing": true,
  });

  const toggleItem = (id: string) => {
    setOpenItems((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredFaqs = useMemo(() => {
    return FAQS.filter((faq) => {
      const matchesCategory = activeCategory === "All" || faq.category === activeCategory;
      const q = search.toLowerCase();
      const matchesSearch =
        search === "" ||
        faq.question.toLowerCase().includes(q) ||
        (typeof faq.answer === "string" && faq.answer.toLowerCase().includes(q));
      return matchesCategory && matchesSearch;
    });
  }, [search, activeCategory]);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16 space-y-12">
      
      {/* Header */}
      <div className="text-center space-y-4 max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-500/30 text-sky-400 font-mono text-xs">
          <HelpCircle className="w-3.5 h-3.5" />
          <span>Knowledge Base & Support</span>
        </div>
        <h1 className="font-display font-extrabold text-3xl sm:text-5xl text-white tracking-tight">
          Frequently Asked Questions
        </h1>
        <p className="text-sm sm:text-base text-[#94A3B8]">
          Find answers about threat scanning, pricing, privacy, GST invoicing, and enterprise integrations.
        </p>
      </div>

      {/* Search & Category Filter Controls */}
      <div className="space-y-4">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94A3B8]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search questions (e.g. pricing, invoice, cancel, APK, DPDP)..."
            className="w-full pl-11 pr-4 py-3 rounded-2xl bg-[#121B22] border border-[#253540] focus:border-[#F59E0B] text-white text-sm focus:outline-none shadow-sm"
          />
        </div>

        {/* Category Tabs */}
        <div className="flex flex-wrap items-center gap-2">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setActiveCategory(cat)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                activeCategory === cat
                  ? "bg-[#F59E0B] text-[#08131A] shadow-sm font-bold"
                  : "bg-[#121B22] border border-[#253540] text-[#94A3B8] hover:text-white hover:border-[#354856]"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* FAQ Accordion List */}
      <div className="space-y-3">
        {filteredFaqs.length === 0 ? (
          <div className="p-8 text-center rounded-2xl bg-[#121B22] border border-[#253540] space-y-2">
            <p className="text-white font-bold text-base">No matching questions found</p>
            <p className="text-xs text-[#94A3B8]">
              Try searching with a different term, or submit your question directly to our support team.
            </p>
            <div className="pt-2">
              <Link
                href="/contact"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#F59E0B] text-[#08131A] font-bold text-xs"
              >
                <span>Ask Support</span>
              </Link>
            </div>
          </div>
        ) : (
          filteredFaqs.map((faq) => {
            const isOpen = !!openItems[faq.id];
            return (
              <div
                key={faq.id}
                className="rounded-2xl bg-[#121B22] border border-[#253540] overflow-hidden transition-colors"
              >
                <button
                  type="button"
                  onClick={() => toggleItem(faq.id)}
                  className="w-full p-5 text-left flex items-center justify-between gap-4 hover:bg-[#18232c] transition-colors"
                  aria-expanded={isOpen}
                >
                  <span className="font-bold text-white text-sm sm:text-base leading-snug">
                    {faq.question}
                  </span>
                  <ChevronDown
                    className={`w-4 h-4 text-[#94A3B8] shrink-0 transition-transform duration-200 ${
                      isOpen ? "rotate-180 text-[#F59E0B]" : ""
                    }`}
                  />
                </button>

                {isOpen && (
                  <div className="px-5 pb-5 pt-1 text-xs sm:text-sm text-[#CBD5E1] leading-relaxed border-t border-[#253540]/50">
                    {faq.answer}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Still Have Questions Banner */}
      <div className="p-6 rounded-2xl bg-[#121B22] border border-[#253540] flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <h3 className="font-bold text-white text-base">Still have questions?</h3>
          <p className="text-xs text-[#94A3B8] mt-0.5">
            Our engineering, billing, and privacy desks are available to assist you.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Link
            href="/contact"
            className="px-4 py-2 rounded-xl bg-[#F59E0B] hover:bg-[#D97706] text-[#08131A] font-bold text-xs transition-colors shadow-sm"
          >
            Contact Helpdesk
          </Link>
          <Link
            href="/billing-policy"
            className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-semibold transition-colors"
          >
            Review Billing Policy
          </Link>
        </div>
      </div>

    </div>
  );
}
