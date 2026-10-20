import type { Metadata } from "next";
import Link from "next/link";
import { CreditCard, Check, Shield, Receipt, RefreshCw, XCircle, FileText } from "lucide-react";

export const metadata: Metadata = {
  title: "Subscription, Cancellation & Refund Policy | Digital Rakshak",
  description: "Official pricing, recurring billing terms, GST invoice details (SAC 998313), and cancellation/refund policies for Digital Rakshak.",
};

export default function BillingPolicyPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      
      {/* Header */}
      <div className="mb-12 border-b border-[#253540] pb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-500/30 text-sky-400 font-mono text-xs mb-4">
          <CreditCard className="w-3.5 h-3.5" />
          <span>Billing & Subscriptions Policy</span>
        </div>
        <h1 className="font-display font-extrabold text-3xl sm:text-5xl tracking-tight text-white mb-4">
          Subscription, Cancellation & Refund Policy
        </h1>
        <p className="text-sm sm:text-base text-[#94A3B8] leading-relaxed">
          Clear, transparent pricing and fair consumer policies. No hidden lock-ins.
        </p>
      </div>

      {/* Main Content */}
      <div className="space-y-10 text-sm sm:text-base text-[#CBD5E1] leading-relaxed font-sans">
        
        {/* Section 1: Plan Comparison Matrix */}
        <section className="space-y-4">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            1. Current Subscription Plans & Pricing
          </h2>
          <p>
            All consumer subscription plans are billed in Indian Rupees (INR) through Razorpay. Prices are displayed with mandatory 18% Goods & Services Tax (GST) breakdown under SAC 998313:
          </p>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
            
            {/* Free Shield */}
            <div className="p-5 rounded-xl bg-[#121B22] border border-[#253540] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-white text-base">Free Shield</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/10 text-[#CBD5E1]">Citizen Free</span>
                </div>
                <div className="font-display text-2xl font-bold text-white mb-3">
                  ₹0 <span className="text-xs text-[#94A3B8] font-normal">/ forever</span>
                </div>
                <ul className="space-y-2 text-xs text-[#94A3B8]">
                  <li className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> Up to 5 scans/day limit</li>
                  <li className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> Standard heuristic classification</li>
                  <li className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> Community fraud bulletin</li>
                </ul>
              </div>
              <div className="mt-4 pt-3 border-t border-[#253540] text-[11px] font-mono text-[#64748B]">
                Plan Code: b2c_free
              </div>
            </div>

            {/* Personal Pro (149) */}
            <div className="p-5 rounded-xl bg-[#121B22] border-2 border-[#F59E0B]/50 flex flex-col justify-between relative shadow-lg">
              <div className="absolute -top-3 right-4 px-2 py-0.5 rounded-full bg-[#F59E0B] text-[#08131A] font-bold text-[10px] uppercase tracking-wider">
                Most Popular
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-white text-base">Personal Pro</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#F59E0B]/20 text-[#F59E0B]">Monthly</span>
                </div>
                <div className="font-display text-2xl font-bold text-white">
                  ₹175.82 <span className="text-xs text-[#94A3B8] font-normal">/ mo</span>
                </div>
                <p className="text-[11px] text-[#A7B4BD] mb-3">
                  (Base: ₹149.00 + 18% GST: ₹26.82)
                </p>
                <ul className="space-y-2 text-xs text-[#CBD5E1]">
                  <li className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-[#F59E0B] shrink-0" /> Unlimited threat scans</li>
                  <li className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-[#F59E0B] shrink-0" /> 11-engine AI deep inspection</li>
                  <li className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-[#F59E0B] shrink-0" /> Suspicious APK decompiler</li>
                  <li className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-[#F59E0B] shrink-0" /> Priority WhatsApp & SMS shield</li>
                </ul>
              </div>
              <div className="mt-4 pt-3 border-t border-[#253540] text-[11px] font-mono text-[#F59E0B]">
                Plan Code: b2c_pro_149
              </div>
            </div>

            {/* Family Shield (249) */}
            <div className="p-5 rounded-xl bg-[#121B22] border border-[#253540] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-white text-base">Family Shield</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400">5 Accounts</span>
                </div>
                <div className="font-display text-2xl font-bold text-white">
                  ₹293.82 <span className="text-xs text-[#94A3B8] font-normal">/ mo</span>
                </div>
                <p className="text-[11px] text-[#A7B4BD] mb-3">
                  (Base: ₹249.00 + 18% GST: ₹44.82)
                </p>
                <ul className="space-y-2 text-xs text-[#CBD5E1]">
                  <li className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> Up to 5 family members covered</li>
                  <li className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> Elder scam protection alerts</li>
                  <li className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> Central family security report</li>
                  <li className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> Priority telephone assist</li>
                </ul>
              </div>
              <div className="mt-4 pt-3 border-t border-[#253540] text-[11px] font-mono text-[#CBD5E1]">
                Plan Code: b2c_pro_249
              </div>
            </div>

          </div>

          {/* Annual Plan Spotlight */}
          <div className="mt-4 p-5 rounded-xl bg-gradient-to-r from-[#18232c] to-[#121B22] border border-[#F59E0B]/30 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="space-y-1 text-center sm:text-left">
              <div className="flex items-center justify-center sm:justify-start gap-2">
                <span className="font-bold text-white text-base">Personal Pro Annual (365 Days)</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400">Save ~27%</span>
              </div>
              <p className="text-xs text-[#94A3B8]">
                Base: ₹1,299.00 + 18% GST (₹233.82) = <strong className="text-white">₹1,532.82 gross payable</strong> annually.
              </p>
            </div>
            <div className="text-right shrink-0">
              <span className="text-xs font-mono text-[#F59E0B]">Plan Code: b2c_pro_annual</span>
            </div>
          </div>
        </section>

        {/* Section 2: Billing & Renewals */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            2. Payment Methods & Automatic Renewals
          </h2>
          <p>
            Payments are securely processed via Razorpay. We support UPI AutoPay (Google Pay, PhonePe, Paytm, BHIM), Indian Rupee Credit/Debit Cards, and Netbanking.
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>
              <strong>Auto-Renewal:</strong> By subscribing to a monthly or annual plan, you authorize an e-mandate for recurring subscription renewal at the end of each billing cycle until cancelled.
            </li>
            <li>
              <strong>Pre-Debit Notifications:</strong> In accordance with Reserve Bank of India (RBI) e-mandate guidelines, an SMS/email pre-debit notification is sent at least 24 hours prior to recurring debit.
            </li>
            <li>
              <strong>Failed Debits:</strong> If a recurring payment fails, a 3-day grace period is granted during which retries occur. If unresolved, the account reverts automatically to the Free Shield tier without penalty.
            </li>
          </ul>
        </section>

        {/* Section 3: Invoicing & Taxes */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            3. GST Invoices & Statutory Compliance (SAC 998313)
          </h2>
          <p>
            Digital Rakshak is registered under the Goods and Services Tax Act. All cybersecurity threat intelligence and SaaS security defense services fall under <strong>Services Accounting Code (SAC) 998313</strong>.
          </p>
          <p>
            An official GST-compliant tax invoice is automatically generated upon every successful transaction. Customers can view and download tamper-evident PDF invoices at any time directly from the <strong>Personal Shield &rarr; Billing</strong> tab.
          </p>
        </section>

        {/* Section 4: Cancellation */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            4. 1-Click Cancellation Policy
          </h2>
          <p>
            You may cancel your recurring subscription at any time with a single click in your account settings:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>
              <strong>No Early Cancellation Fees:</strong> There are zero termination penalties or hidden fees.
            </li>
            <li>
              <strong>Continuous Access Until Cycle End:</strong> Once cancelled, your premium Pro features remain fully active until the expiration date of your current paid billing period.
            </li>
            <li>
              <strong>Preservation of Data:</strong> Your account history and scan records will remain safe and accessible under the Free tier.
            </li>
          </ul>
        </section>

        {/* Section 5: Refunds */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            5. Refund & Dispute Resolution Policy
          </h2>
          <div className="p-4 rounded-xl bg-[#121B22] border border-[#253540] space-y-2">
            <h3 className="font-bold text-white">7-Day Money-Back Guarantee (First-Time Subscriptions):</h3>
            <p className="text-xs sm:text-sm text-[#94A3B8]">
              If you are not satisfied with Digital Rakshak Pro, you may request a 100% refund within seven (7) calendar days of your initial subscription purchase. Submit a refund request via the <Link href="/contact?category=Subscription+%26+Billing" className="text-[#F59E0B] underline font-semibold">Billing & Refund Helpdesk</Link> with your registered email and payment reference ID.
            </p>
          </div>
          <ul className="list-disc pl-6 space-y-2">
            <li>
              <strong>Processing Timeline:</strong> Approved refunds are credited directly back to the original payment source (UPI account or bank card) within 5 to 7 banking business days, subject to your issuing bank&apos;s settlement schedule.
            </li>
            <li>
              <strong>Subsequent Renewals:</strong> Monthly renewal charges are non-refundable once the billing cycle has begun unless caused by an unresolved platform outage.
            </li>
            <li>
              <strong>Annual Subscriptions:</strong> For annual plans cancelled after the initial 7-day period, a prorated refund may be granted for remaining full unused calendar months, deducting the standard single-month rate for months consumed.
            </li>
          </ul>
        </section>

        {/* Section 6: Contact Billing */}
        <section className="space-y-2 pt-4 border-t border-[#253540]">
          <h3 className="font-bold text-white">Billing Support Contact</h3>
          <p className="text-xs sm:text-sm text-[#94A3B8]">
            For billing inquiries, GST invoice corrections, or refund tracking, submit an inquiry through our{" "}
            <Link href="/contact?category=Subscription+%26+Billing" className="text-[#F59E0B] underline font-semibold">
              Dedicated Billing & Refund Portal &rarr;
            </Link>
          </p>
        </section>

      </div>

    </div>
  );
}
