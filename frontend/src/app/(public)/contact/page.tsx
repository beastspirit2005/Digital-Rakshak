"use client";

import { useState, useEffect, Suspense, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { 
  Send, 
  CheckCircle2, 
  AlertCircle, 
  PhoneCall, 
  ShieldAlert, 
  ExternalLink, 
  Clock, 
  Copy, 
  Check,
  Building,
  HelpCircle,
  CreditCard,
  Lock,
  Bug,
  ArrowRight
} from "lucide-react";
import { API_BASE_URL } from "@/lib/api";

const CATEGORIES = [
  { id: "General Inquiry", label: "General Inquiry", icon: HelpCircle },
  { id: "Technical Support", label: "Technical Support", icon: AlertCircle },
  { id: "Subscription & Billing", label: "Subscription & Billing", icon: CreditCard },
  { id: "Privacy & DPDP Request", label: "Privacy & DPDP Request", icon: Lock },
  { id: "Security Vulnerability (VDP)", label: "Security Vulnerability (VDP)", icon: Bug },
  { id: "Enterprise Partnership", label: "Enterprise Partnership", icon: Building },
];

function ContactFormContent() {
  const searchParams = useSearchParams();
  const formRef = useRef<HTMLDivElement>(null);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [category, setCategory] = useState("General Inquiry");
  const [subject, setSubject] = useState("");
  const [referenceNumber, setReferenceNumber] = useState("");
  const [message, setMessage] = useState("");
  
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [ticketResult, setTicketResult] = useState<{ ticket_number: string; message: string } | null>(null);
  const [copied, setCopied] = useState(false);

  // Sync category from URL search params if provided (e.g. /contact?category=Subscription+%26+Billing)
  useEffect(() => {
    const requestedCategory = searchParams.get("category");
    if (requestedCategory) {
      const match = CATEGORIES.find(
        (c) => c.id.toLowerCase() === requestedCategory.toLowerCase() || c.label.toLowerCase() === requestedCategory.toLowerCase()
      );
      if (match) {
        setCategory(match.id);
        if (formRef.current) {
          formRef.current.scrollIntoView({ behavior: "smooth" });
        }
      }
    }
  }, [searchParams]);

  const selectDesk = (catId: string) => {
    setCategory(catId);
    if (formRef.current) {
      formRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!name.trim() || !email.trim() || !subject.trim() || !message.trim()) {
      setErrorMsg("Please fill out all required fields.");
      return;
    }

    if (message.trim().length < 10) {
      setErrorMsg("Please provide a more descriptive message (at least 10 characters).");
      return;
    }

    setSubmitting(true);

    try {
      const res = await fetch(`${API_BASE_URL}/support/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          category,
          subject: subject.trim(),
          message: message.trim(),
          reference_number: referenceNumber.trim() || undefined,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || data.message || "Failed to submit inquiry. Please try again.");
      }

      setTicketResult({
        ticket_number: data.ticket_number || "TKT-INQ-SUCCESS",
        message: data.message || "Your inquiry has been successfully received by our specialized dispatch desk.",
      });

      // Clear form inputs
      setName("");
      setEmail("");
      setSubject("");
      setReferenceNumber("");
      setMessage("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Network error. Please try again later.";
      setErrorMsg(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const copyTicket = () => {
    if (ticketResult?.ticket_number) {
      navigator.clipboard.writeText(ticketResult.ticket_number);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      
      {/* Emergency Fraud Alert Banner */}
      <div className="mb-10 p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-amber-500/15 via-rose-500/15 to-amber-500/15 border border-amber-500/30 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-[#F59E0B] shrink-0 mt-0.5" />
          <div>
            <p className="font-bold text-white text-sm">
              Are you an active victim of ongoing cyber fraud or digital arrest?
            </p>
            <p className="text-xs text-[#CBD5E1] mt-0.5 leading-relaxed">
              Do not wait for contact ticket replies. Immediately contact the Government of India&apos;s 24/7 National Cybercrime Helpline to freeze funds.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <a
            href="tel:1930"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#F59E0B] text-[#08131A] font-bold text-xs hover:bg-[#D97706] transition-colors shadow-sm"
          >
            <PhoneCall className="w-4 h-4" />
            <span>Call 1930 Now</span>
          </a>
          <a
            href="https://cybercrime.gov.in"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-white text-xs hover:bg-white/10 transition-colors"
          >
            <span>cybercrime.gov.in</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* Page Header */}
      <div className="text-center max-w-2xl mx-auto mb-12">
        <h1 className="font-display font-extrabold text-3xl sm:text-5xl text-white tracking-tight mb-3">
          Digital Rakshak Secure Helpdesk
        </h1>
        <p className="text-sm sm:text-base text-[#94A3B8] leading-relaxed">
          Submit inquiries directly to our specialized response teams. All messages are encrypted in transit and routed privately to the designated duty officer.
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8 items-start">
        
        {/* Left Column: Direct Department Routing Desks */}
        <div className="lg:col-span-1 space-y-4">
          
          <div className="p-5 rounded-2xl bg-[#121B22] border border-[#253540] space-y-3">
            <h2 className="font-bold text-white text-base">Specialized Response Desks</h2>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              Select a specialized desk below to automatically configure your inquiry routing:
            </p>
            
            <div className="space-y-2 pt-1">
              <button
                type="button"
                onClick={() => selectDesk("Technical Support")}
                className={`w-full p-3 rounded-xl text-left border transition-all flex items-center justify-between ${
                  category === "Technical Support"
                    ? "bg-[#18232c] border-[#F59E0B] text-white"
                    : "bg-[#050D12] border-[#253540] text-[#CBD5E1] hover:border-[#354856]"
                }`}
              >
                <div>
                  <span className="text-xs font-bold block text-white">General & Technical Desk</span>
                  <span className="text-[11px] text-[#94A3B8]">App features, scan issues, bug reports</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-[#F59E0B] shrink-0" />
              </button>

              <button
                type="button"
                onClick={() => selectDesk("Subscription & Billing")}
                className={`w-full p-3 rounded-xl text-left border transition-all flex items-center justify-between ${
                  category === "Subscription & Billing"
                    ? "bg-[#18232c] border-[#F59E0B] text-white"
                    : "bg-[#050D12] border-[#253540] text-[#CBD5E1] hover:border-[#354856]"
                }`}
              >
                <div>
                  <span className="text-xs font-bold block text-white">Billing & Refund Desk</span>
                  <span className="text-[11px] text-[#94A3B8]">GST invoices, Pro plans, refund requests</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-[#F59E0B] shrink-0" />
              </button>

              <button
                type="button"
                onClick={() => selectDesk("Privacy & DPDP Request")}
                className={`w-full p-3 rounded-xl text-left border transition-all flex items-center justify-between ${
                  category === "Privacy & DPDP Request"
                    ? "bg-[#18232c] border-[#F59E0B] text-white"
                    : "bg-[#050D12] border-[#253540] text-[#CBD5E1] hover:border-[#354856]"
                }`}
              >
                <div>
                  <span className="text-xs font-bold block text-white">DPDP Grievance Officer</span>
                  <span className="text-[11px] text-[#94A3B8]">Data principal rights, erasure requests</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-[#F59E0B] shrink-0" />
              </button>

              <button
                type="button"
                onClick={() => selectDesk("Security Vulnerability (VDP)")}
                className={`w-full p-3 rounded-xl text-left border transition-all flex items-center justify-between ${
                  category === "Security Vulnerability (VDP)"
                    ? "bg-[#18232c] border-[#F59E0B] text-white"
                    : "bg-[#050D12] border-[#253540] text-[#CBD5E1] hover:border-[#354856]"
                }`}
              >
                <div>
                  <span className="text-xs font-bold block text-white">Security & VDP Desk</span>
                  <span className="text-[11px] text-[#94A3B8]">Ethical disclosures, security reports</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-[#F59E0B] shrink-0" />
              </button>
            </div>

            <div className="pt-3 border-t border-[#253540] flex items-center gap-2 text-[11px] text-[#94A3B8]">
              <Clock className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>Response Turnaround: Typically within 24 hours</span>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-[#121B22] border border-[#253540] space-y-2 text-xs">
            <span className="font-bold text-white block">Security & Privacy Guardrail:</span>
            <p className="text-[#94A3B8] leading-relaxed">
              Never share OTPs, UPI PINs, banking passwords, or payment credentials. Digital Rakshak personnel will never request your secret authentication keys.
            </p>
          </div>

        </div>

        {/* Right Column: Inbound Helpdesk Submission Form */}
        <div className="lg:col-span-2" ref={formRef}>
          <div className="p-6 sm:p-8 rounded-2xl bg-[#121B22] border border-[#253540]">
            
            {ticketResult ? (
              <div className="text-center py-8 space-y-4">
                <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto">
                  <CheckCircle2 className="w-8 h-8" />
                </div>
                <h3 className="font-display font-bold text-2xl text-white">
                  Inquiry Dispatched Successfully
                </h3>
                <p className="text-sm text-[#94A3B8] max-w-md mx-auto leading-relaxed">
                  {ticketResult.message}
                </p>

                {/* Ticket Tracking Number Card */}
                <div className="inline-flex items-center gap-3 px-4 py-2.5 rounded-xl bg-[#050D12] border border-[#253540] font-mono text-sm mt-2">
                  <span className="text-[#94A3B8]">Reference ID:</span>
                  <span className="font-bold text-[#F59E0B]">{ticketResult.ticket_number}</span>
                  <button
                    onClick={copyTicket}
                    className="p-1 rounded hover:bg-white/10 text-[#CBD5E1] transition-colors"
                    title="Copy Reference ID"
                  >
                    {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>

                <div className="pt-6">
                  <button
                    onClick={() => setTicketResult(null)}
                    className="px-5 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-semibold transition-colors"
                  >
                    Submit Another Inquiry
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-6">
                
                {errorMsg && (
                  <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{errorMsg}</span>
                  </div>
                )}

                {/* Category Selector Buttons */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-white block uppercase tracking-wider font-mono">
                    Target Department <span className="text-[#F59E0B]">*</span>
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {CATEGORIES.map((cat) => {
                      const Icon = cat.icon;
                      const selected = category === cat.id;
                      return (
                        <button
                          key={cat.id}
                          type="button"
                          onClick={() => setCategory(cat.id)}
                          className={`p-3 rounded-xl text-left border text-xs flex items-start gap-2 transition-all ${
                            selected
                              ? "bg-[#18232c] border-[#F59E0B] text-white shadow-sm"
                              : "bg-[#050D12] border-[#253540] text-[#94A3B8] hover:text-white hover:border-[#354856]"
                          }`}
                        >
                          <Icon className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${selected ? "text-[#F59E0B]" : "text-[#64748B]"}`} />
                          <span className="font-semibold">{cat.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Name & Email Row */}
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-[#CBD5E1] block">
                      Your Full Name <span className="text-[#F59E0B]">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Rahul Sharma"
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#050D12] border border-[#253540] focus:border-[#F59E0B] text-white text-sm focus:outline-none"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-[#CBD5E1] block">
                      Your Contact Email <span className="text-[#F59E0B]">*</span>
                    </label>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="e.g. rahul@example.com"
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#050D12] border border-[#253540] focus:border-[#F59E0B] text-white text-sm focus:outline-none"
                    />
                  </div>
                </div>

                {/* Subject & Reference ID */}
                <div className="grid sm:grid-cols-3 gap-4">
                  <div className="sm:col-span-2 space-y-1.5">
                    <label className="text-xs font-semibold text-[#CBD5E1] block">
                      Subject Line <span className="text-[#F59E0B]">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      placeholder="Brief summary of your request"
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#050D12] border border-[#253540] focus:border-[#F59E0B] text-white text-sm focus:outline-none"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-[#CBD5E1] block">
                      Reference / Invoice ID <span className="text-[#64748B] text-[11px]">(Optional)</span>
                    </label>
                    <input
                      type="text"
                      value={referenceNumber}
                      onChange={(e) => setReferenceNumber(e.target.value)}
                      placeholder="e.g. INV-10029"
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#050D12] border border-[#253540] focus:border-[#F59E0B] text-white text-sm focus:outline-none font-mono"
                    />
                  </div>
                </div>

                {/* Message */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-semibold text-[#CBD5E1] block">
                      Message & Description <span className="text-[#F59E0B]">*</span>
                    </label>
                    <span className="text-[11px] text-[#64748B] font-mono">
                      {message.length} / 4000
                    </span>
                  </div>
                  <textarea
                    required
                    rows={5}
                    value={message}
                    maxLength={4000}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Provide details of your request. Our specialized response desk will receive this inquiry privately and follow up with you directly."
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#050D12] border border-[#253540] focus:border-[#F59E0B] text-white text-sm focus:outline-none resize-y"
                  />
                </div>

                {/* Submit Action */}
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full py-3 rounded-xl bg-[#F59E0B] hover:bg-[#D97706] text-[#08131A] font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-md disabled:opacity-50"
                >
                  {submitting ? (
                    <span>Routing inquiry securely...</span>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      <span>Submit Inbound Inquiry</span>
                    </>
                  )}
                </button>

              </form>
            )}

          </div>
        </div>

      </div>

    </div>
  );
}

export default function ContactPage() {
  return (
    <Suspense fallback={
      <div className="max-w-6xl mx-auto px-4 py-16 text-center text-[#94A3B8]">
        Loading Secure Helpdesk...
      </div>
    }>
      <ContactFormContent />
    </Suspense>
  );
}
