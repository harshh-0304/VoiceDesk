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
    audioData,
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

            // Dynamic color state
            let color = "rgba(107, 114, 128, 0.4)"; // Gray (Idle)
            if (isListening) color = "rgba(168, 85, 247, 0.85)"; // Purple (Listening)
            if (isSpeaking) color = "rgba(52, 211, 153, 0.85)"; // Emerald (Speaking)

            ctx.fillStyle = color;

            const bars = 48;
            const barWidth = 4;
            const spacing = 4;
            const totalWidth = bars * (barWidth + spacing);
            const startX = (width - totalWidth) / 2;

            for (let i = 0; i < bars; i++) {
                let barHeight = 4;

                if ((isListening || isSpeaking) && audioData && audioData.length > 0) {
                    const dataIndex = Math.floor((i / bars) * audioData.length);
                    const rawVal = audioData[dataIndex] || 0;
                    barHeight = 6 + (rawVal / 255) * (height * 0.7);
                    if (isSpeaking) barHeight = Math.max(barHeight, 10 + Math.sin(time + i * 0.4) * 20);
                } else if (isListening) {
                    const noise = Math.sin(time + i * 0.3) * 12;
                    barHeight = 8 + Math.abs(noise);
                } else {
                    barHeight = 4 + Math.sin(time + i * 0.4) * 2.5;
                }

                const x = startX + i * (barWidth + spacing);
                ctx.fillRect(x, centerY - barHeight / 2, barWidth, barHeight);
            }

            animationId = requestAnimationFrame(draw);
        };

        draw();

        return () => cancelAnimationFrame(animationId);
    }, [isListening, isSpeaking, audioData]);

    return (
        <canvas
            ref={canvasRef}
            width={480}
            height={90}
            className="w-full max-w-md h-24 block"
        />
    );
}
