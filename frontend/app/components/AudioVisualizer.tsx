"use client";

import { useEffect, useRef } from "react";

interface AudioVisualizerProps {
    isListening: boolean;
    isSpeaking: boolean;
    audioData?: number[]; // Frequency data (0-255)
}

export default function AudioVisualizer({
    isListening,
    isSpeaking,
    audioData
}: AudioVisualizerProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        let animationId: number;
        let time = 0;

        const draw = () => {
            time += 0.05;
            const width = canvas.width;
            const height = canvas.height;
            const centerY = height / 2;

            ctx.clearRect(0, 0, width, height);
            ctx.lineCap = "round";

            // Color based on state
            let color = "rgba(75, 85, 99, 0.5)"; // Gray (Idle)
            if (isListening) color = "rgba(139, 92, 246, 0.8)"; // Purple (Listening)
            if (isSpeaking) color = "rgba(59, 130, 246, 0.8)"; // Blue (Speaking)

            ctx.fillStyle = color;

            const bars = 60;
            const barWidth = 4;
            const spacing = 6;
            const totalWidth = bars * (barWidth + spacing);
            const startX = (width - totalWidth) / 2;

            for (let i = 0; i < bars; i++) {
                let barHeight = 4; // Min height

                if ((isListening || isSpeaking) && audioData && audioData.length > 0) {
                    // Map data to bars
                    // Simple simulation if no real data yet
                    // If we have real data, we map audioData[i] to height
                    // For now, let's use a simulated wave if data is missing or just noise

                    // Real data usage:
                    // const index = Math.floor((i / bars) * audioData.length);
                    // barHeight = (audioData[index] / 255) * (height / 2);

                    // Simulated "Alive" effect for demo if data is sparse
                    const noise = Math.sin(time + i * 0.2) * 20;
                    barHeight = 10 + Math.abs(noise) + Math.random() * 10;
                    if (isSpeaking) barHeight *= 2.5;
                } else {
                    // Idle breathing
                    barHeight = 4 + Math.sin(time + i * 0.5) * 2;
                }

                const x = startX + i * (barWidth + spacing);

                // Draw symmetric bars
                ctx.fillRect(x, centerY - barHeight / 2, barWidth, barHeight);
            }

            animationId = requestAnimationFrame(draw);
        };

        draw();

        return () => cancelAnimationFrame(animationId);
    }, [isListening, isSpeaking, audioData]);

    return (
        <
}
