"use client";

import React, { useState } from "react";
import { motion, AnimatePresence, useReducedMotion, type Variants } from "framer-motion";
import { HelpCircle, Plus } from "lucide-react";

const FAQ_ITEMS = [
  {
    id: "faq-1",
    trigger: "What is Digital Rakshak?",
    content:
      "Digital Rakshak is an AI-powered cyber threat intelligence platform that connects citizen reports, financial fraud signals, law enforcement agencies and banking systems to detect, verify and respond to cybercrime in real time.",
  },
  {
    id: "faq-2",
    trigger: "Who can use Digital Rakshak?",
    content:
      "Digital Rakshak is designed for citizens, cyber cells, police departments, banks, financial institutions and authorized government agencies to collaborate securely against cybercrime.",
  },
  {
    id: "faq-3",
    trigger: "How does AI help investigators?",
    content:
      "Artificial Intelligence analyzes reports, detects hidden relationships between cases, prioritizes threats, identifies fraud patterns and assists investigators with actionable intelligence while keeping human officers in control.",
  },
  {
    id: "faq-4",
    trigger: "Is my personal information secure?",
    content:
      "Yes. All sensitive information is encrypted and processed through secure access controls. Personal data is only available to authorized personnel in accordance with cybersecurity and privacy policies.",
  },
  {
    id: "faq-5",
    trigger: "Which cyber crimes can I report?",
    content:
      "Digital Rakshak supports reporting phishing attacks, UPI fraud, investment scams, counterfeit currency, deepfakes, identity theft, fake websites, digital arrest scams, social media fraud and other cyber-enabled crimes.",
  },
  {
    id: "faq-6",
    trigger: "Can I track my complaint?",
    content:
      "Yes. Registered users can securely monitor complaint progress, receive investigation updates and view important notifications.",
  },
];

export function FAQSection() {
  const reduced = useReducedMotion();
  const [openId, setOpenId] = useState<string | null>(null);

  const handleToggle = (id: string) => {
    setOpenId(openId === id ? null : id);
  };

  const containerVariants: Variants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: 0.05,
      },
    },
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 10 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.4,
        ease: [0.16, 1, 0.3, 1],
      },
    },
  };

  return (
    <section 
      id="faq" 
      className="relative overflow-hidden pt-20 pb-32 bg-[#020617] text-[#E7EEF3]"
    >
      {/* Cinematic 5-stop gradient overlay matching the Hero section */}
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
        }}
      />

      {/* Ambient glows on opposite sides */}
      <div className="absolute left-0 bottom-1/4 w-[500px] h-[500px] rounded-full bg-[radial-gradient(circle_at_center,rgba(14,165,233,0.06)_0%,transparent_70%)] pointer-events-none" />
      <div className="absolute right-0 top-1/4 w-[600px] h-[600px] rounded-full bg-[radial-gradient(circle_at_center,rgba(245,158,11,0.16)_0%,transparent_70%)] pointer-events-none mix-blend-screen" />

      {/* Cyber vector grid overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(37,53,64,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(37,53,64,0.05)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />

      <div className="relative z-10 max-w-4xl mx-auto px-6">
        
        {/* Section Header */}
        <motion.div
          initial={reduced ? {} : { opacity: 0, y: 15 }}
          whileInView={reduced ? {} : { opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="text-center max-w-2xl mx-auto mb-14 space-y-4"
        >
          <div className="inline-flex items-center gap-2 bg-[#17232A] border border-[#253540] px-3.5 py-1.5 rounded-full text-xs font-semibold text-[#F59E0B] tracking-wide uppercase">
            <HelpCircle className="w-3.5 h-3.5 text-[#F59E0B]" />
            Citizens & Officers Support
          </div>
          
          <h2 className="font-display font-bold text-2xl sm:text-3xl tracking-tight text-[#E7EEF3] leading-tight">
            Frequently Asked Questions
          </h2>
          
          <p className="text-sm sm:text-base text-[#A7B4BD] leading-relaxed font-sans">
            Everything you need to know about Digital Rakshak, reporting cybercrime and how our AI-powered intelligence platform protects citizens.
          </p>
        </motion.div>

        {/* transparent Accordion Rows */}
        <motion.div
          initial={reduced ? {} : "hidden"}
          whileInView={reduced ? undefined : "visible"}
          viewport={{ once: true, amount: 0.15 }}
          variants={containerVariants}
          className="space-y-1"
        >
          {FAQ_ITEMS.map((item) => {
            const isOpen = openId === item.id;
            return (
              <motion.div 
                key={item.id} 
                variants={itemVariants}
                className="border-b border-[rgba(37,53,64,0.4)] last:border-0"
              >
                <h3>
                  <button
                    type="button"
                    aria-expanded={isOpen}
                    aria-controls={`accordion-content-${item.id}`}
                    id={`accordion-trigger-${item.id}`}
                    onClick={() => handleToggle(item.id)}
                    className="w-full py-5 flex items-center justify-between text-left font-display font-semibold text-[#E7EEF3] hover:text-[#F59E0B] focus-visible:text-[#F59E0B] focus-visible:outline-none transition-colors group cursor-pointer"
                  >
                    <span className="text-base sm:text-lg pr-4">{item.trigger}</span>
                    <span className="shrink-0 w-6 h-6 rounded-full bg-[#17232A]/80 border border-[#253540]/60 flex items-center justify-center text-[#E7EEF3] group-hover:border-[#F59E0B]/40 group-hover:bg-[#F59E0B]/10 group-hover:text-[#F59E0B] transition-all duration-300">
                      <motion.span
                        animate={isOpen ? { rotate: 45 } : { rotate: 0 }}
                        transition={reduced ? { duration: 0 } : { duration: 0.2, ease: "easeInOut" }}
                        className="flex items-center justify-center"
                      >
                        <Plus className="w-4 h-4" />
                      </motion.span>
                    </span>
                  </button>
                </h3>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      id={`accordion-content-${item.id}`}
                      role="region"
                      aria-labelledby={`accordion-trigger-${item.id}`}
                      initial={reduced ? { opacity: 1 } : { opacity: 0, height: 0 }}
                      animate={reduced ? { opacity: 1 } : { opacity: 1, height: "auto" }}
                      exit={reduced ? { opacity: 0 } : { opacity: 0, height: 0 }}
                      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                      className="overflow-hidden"
                    >
                      <div className="pb-5 text-sm sm:text-base text-[#A7B4BD] leading-relaxed font-sans">
                        {item.content}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </motion.div>

      </div>
    </section>
  );
}