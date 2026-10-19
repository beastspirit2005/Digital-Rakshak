"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";
import { axisTick } from "@/components/ui/chart";

interface ThreatProfileRadarProps {
  sixDim: {
    threat: number;
    behavior: number;
    network: number;
    integrity: number;
    impersonation: number;
    extraction: number;
  };
  reduced?: boolean | null;
}

export function ThreatProfileRadar({ sixDim, reduced }: ThreatProfileRadarProps) {
  const chartData = [
    { subject: "Threat", A: (sixDim.threat ?? 0) * 100 },
    { subject: "Behavior", A: (sixDim.behavior ?? 0) * 100 },
    { subject: "Network", A: (sixDim.network ?? 0) * 100 },
    { subject: "Integrity", A: (sixDim.integrity ?? 0) * 100 },
    { subject: "Impersonation", A: (sixDim.impersonation ?? 0) * 100 },
    { subject: "Extraction", A: (sixDim.extraction ?? 0) * 100 },
  ];

  return (
    <div className="h-60 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={chartData}>
          <PolarGrid stroke="var(--line)" />
          <PolarAngleAxis dataKey="subject" tick={axisTick} />
          <Radar
            name="Threat profile"
            dataKey="A"
            stroke="var(--chart-1)"
            fill="var(--chart-1)"
            fillOpacity={0.25}
            isAnimationActive={!reduced}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default ThreatProfileRadar;
