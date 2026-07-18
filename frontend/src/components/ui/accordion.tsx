"use client";

import React, { useState } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Plus } from "lucide-react";

interface AccordionItemProps {
  id: string;
  trigger: React.ReactNode;
  children: React.ReactNode;
  isOpen: boolean;
  onToggle: () => void;
}

export function AccordionItem({ id, trigger, children, isOpen, onToggle }: AccordionItemProps) {
  const reduced = useReducedMotion();

  return (
    <div className="border-b border-line/60 last:border-0">
      <h3>
        <button
          type="button"
          aria-expanded={isOpen}
          aria-controls={`accordion-content-${id}`}
          id={`accordion-trigger-${id}`}
          onClick={onToggle}
          className="w-full py-5 flex items-center justify-between text-left font-display font-semibold text-ink hover:text-accent focus-visible:text-accent focus-visible:outline-none transition-colors group cursor-pointer"
        >
          <span className="text-base sm:text-lg pr-4">{trigger}</span>
          <span className="shrink-0 w-6 h-6 rounded-full bg-surface-2 border border-line/50 flex items-center justify-center text-ink group-hover:border-accent/40 group-hover:bg-accent-text/10 group-hover:text-accent transition-all duration-300">
            <motion.span
              animate={isOpen ? { rotate: 45 } : { rotate: 0 }}
              transition={reduced ? { duration: 0 } : { duration: 0.25, ease: "easeInOut" }}
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
            id={`accordion-content-${id}`}
            role="region"
            aria-labelledby={`accordion-trigger-${id}`}
            initial={reduced ? { opacity: 1 } : { opacity: 0, height: 0 }}
            animate={reduced ? { opacity: 1 } : { opacity: 1, height: "auto" }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="pb-5 text-sm sm:text-base text-ink-2 leading-relaxed font-sans">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface AccordionProps {
  items: {
    id: string;
    trigger: React.ReactNode;
    content: React.ReactNode;
  }[];
}

export function Accordion({ items }: AccordionProps) {
  const [openId, setOpenId] = useState<string | null>(null);

  const handleToggle = (id: string) => {
    setOpenId(openId === id ? null : id);
  };

  return (
    <div className="space-y-1">
      {items.map((item) => (
        <AccordionItem
          key={item.id}
          id={item.id}
          trigger={item.trigger}
          isOpen={openId === item.id}
          onToggle={() => handleToggle(item.id)}
        >
          {item.content}
        </AccordionItem>
      ))}
    </div>
  );
}