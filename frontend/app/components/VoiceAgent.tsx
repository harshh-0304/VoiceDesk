"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Mic, MicOff, Activity, Zap, Terminal } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import AudioVisualizer from "./AudioVisualizer";
import { cn } from "@/lib/utils";

// Types
type AgentState = "idle" | "listening" | "thinking" | "speaking";

export default function VoiceAgent() {
    const [isConnected, setIsConnected] = useState(false);
    const [state, setState] = useState<AgentState>("idle");
    const [transcription, setTranscription] = useState("");
    const [logs, setLogs] = useState<string[]>([]);

    // Refs
    const ws = useRef<WebSocket | null>(null);
    const mediaRecorder = useRef<MediaRecorder | null>(null);
    const audioChunks = useRef<Blob[]>([]);
    const audioQueue = useRef<string[]>([]); // Base64 strings
    const isPlaying = useRef(false);
    const audioContext = useRef<AudioContext | null>(null);
    const analyser = useRef<AnalyserNode | null>(null);
    const silenceStart = useRef<number | null>(null);
    const processingRef = useRef(false);

    // Constants
    const SILENCE_THRESHOLD = 20; // 0-255 energy level
    const SILENCE_DURATION = 1500; // ms

    // Visualizer Data
    const [freqData, setFreqData] = useState<number[]>(new Array(60).fill(0));

    const addLog = (msg: string) => {
        setLogs((prev) => [...prev.slice(-5), `[${new Date().toLocaleTimeString()}] ${msg}`]);
    };

    const connectWebSocket = useCallback(() => {
        ws.current = new WebSocket("ws://localhost:8000/ws/audio");

        ws.current.onopen = () => {
            setIsConnected(true);
            addLog("System Online. Shadow Link Established.");
        };

        ws.current.onclose = () => {
            setIsConnected(false);
            addLog("System Offline. Link Severed.");
            setTimeout(connectWebSocket, 3000); // Reconnect
        };

        ws.current.onmessage = async (event) => {
            const msg = JSON.parse(event.data);

            if (msg.type === "transcription") {
                setTranscription(msg.text);
                addLog(`User: ${msg.text}`);
                setState("thinking");
            } else if (msg.type === "text_delta") {
                // Show streaming text if needed
            } else if (msg.type === "status") {
                if (msg.state === "speaking") setState("speaking");
                if (msg.state === "listening") {
                    setState("idle");
                    startListening();
                }
            } else if (msg.type === "audio_stream") {
                audioQueue.current.push(msg.data);
                processAudioQueue();
            }
        };
    }, []);

    useEffect(() => {
        connectWebSocket();
        return () => ws.current?.close();
    }, [connectWebSocket]);

    // Audio Playback Queue
    const processAudioQueue = async () => {
        if (isPlaying.current || audioQueue.current.length === 0) return;

        isPlaying.current = true;
        const chunk = audioQueue.current.shift();
        if (!chunk) {
            isPlaying.current = false;
            return;
        }

        try {
            const audioBytes = atob(chunk);
            const arrayBuffer = new ArrayBuffer(audioBytes.length);
            const view = new Uint8Array(arrayBuffer);
            for (let i = 0; i < audioBytes.length; i++) {
                view[i] = audioBytes.charCodeAt(i);
            }

            if (!audioContext.current) audioContext.current = new AudioContext();

            // Decode can fail if chunk is partial or corrupt
            audioContext.current.decodeAudioData(arrayBuffer, (audioBuffer) => {
                const source = audioContext.current!.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContext.current!.destination);
                source.onended = () => {
                    isPlaying.current = false;
                    processAudioQueue();
                };
                source.start();
            }, (err) => {
                console.error("Audio decode error:", err);
                addLog("Error: Audio Stream Corrupt");
                isPlaying.current = false;
                processAudioQueue(); // Skip and try next
            });

        } catch (e) {
            console.error("Audio playback error", e);
            isPlaying.current = false;
            processAudioQueue();
        }
    };

    // Microphone & VAD
    const startListening = async () => {
        try {
            if (!audioContext.current) audioContext.current = new AudioContext();
            await audioContext.current.resume();

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            const source = audioContext.current.createMediaStreamSource(stream);
            analyser.current = audioContext.current.createAnalyser();
            analyser.current.fftSize = 256;
            source.connect(analyser.current);

            mediaRecorder.current = new MediaRecorder(stream);
            audioChunks.current = [];

            mediaRecorder.current.ondataavailable = (e) => {
                if (e.data.size > 0) audioChunks.current.push(e.data);
            };

            mediaRecorder.current.onstop = () => {
                if (processingRef.current) {
                    const blob = new Blob(audioChunks.current, { type: "audio/wav" });
                    const reader = new FileReader();
                    reader.readAsDataURL(blob);
                    reader.onloadend = () => {
                        const base64data = (reader.result as string).split(",")[1];
                        ws.current?.send(JSON.stringify({ type: "commit", audio_data: base64data }));
                        setState("thinking");
                        audioChunks.current = [];
                    };
                }
            };

            mediaRecorder.current.start();
            setState("listening");
            processingRef.current = false;

            checkSilence();

        } catch (err) {
            console.error("Mic Error:", err);
            addLog("Error: Microphone Access Denied");
        }
    };

    const stopListening = () => {
        if (mediaRecorder.current && mediaRecorder.current.state !== "inactive") {
            processingRef.current = true;
            mediaRecorder.current.stop();
            mediaRecorder.current.stream.getTracks().forEach(track => track.stop());
        }
    };

    const checkSilence = () => {
        if (state === "thinking" || state === "speaking") return;
        if (!analyser.current) return;

        const bufferLength = analyser.current.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        analyser.current.getByteFrequencyData(dataArray);

        const average = dataArray.reduce((a, b) => a + b) / bufferLength;
        setFreqData(Array.from(dataArray).slice(0, 60));

        if (average > SILENCE_THRESHOLD) {
            silenceStart.current = null;
        } else {
            if (!silenceStart.current) silenceStart.current = Date.now();
            else if (Date.now() - silenceStart.current > SILENCE_DURATION) {
                if (state === "listening") {
                    addLog("Silence detected. Committing...");
                    stopListening();
                    return;
                }
            }
        }

        if (state === "listening") requestAnimationFrame(checkSilence);
    };

    return (
        <div className="flex flex-col items-center justify-center w-full min-h-[80vh] space-y-12">

            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between w-full px-8 py-4 glass rounded-full border border-purple-500/20 shadow-[0_0_15px_rgba(168,85,247,0.1)]"
            >
                <div className="flex items-center space-x-4">
                    <div className={cn("w-3 h-3 rounded-full shadow-[0_0_10px]", isConnected ? "bg-purple-500 shadow-purple-500" : "bg-red-500 shadow-red-500")} />
                    <span className="text-sm font-bold tracking-[0.2em] text-purple-100 font-orbitron">VOICEDESK // SHADOW_MONARCH</span>
                </div>
                <div className="flex items-center space-x-2 text-xs font-mono text-purple-300">
                    <Activity size={14} />
                    <span>{state.toUpperCase()}</span>
                </div>
            </motion.div>

            {/* Core Interaction */}
            <div className="relative w-80 h-80 flex items-center justify-center">
                {/* Background Glows */}
                <motion.div
                    animate={{
                        scale: state === "listening" ? [1, 1.2, 1] : 1,
                        opacity: state === "listening" ? 0.4 : 0.1
                    }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="absolute inset-0 bg-purple-600 rounded-full blur-3xl"
                />

                {/* Main Button */}
                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={state === "idle" ? startListening : stopListening}
                    className={cn(
                        "relative z-10 w-40 h-40 rounded-full glass flex items-center justify-center border-4 transition-all duration-300",
                        state === "listening"
                            ? "border-purple-500 shadow-[0_0_50px_rgba(168,85,247,0.8)] bg-purple-900/20"
                            : "border-gray-500 shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:border-white hover:bg-white/5"
                    )}
                >
                    <AnimatePresence mode="wait">
                        {state === "listening" ? (
                            <motion.div
                                key="mic"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                            >
                                <Mic className="w-16 h-16 text-purple-300 drop-shadow-[0_0_10px_rgba(168,85,247,0.8)]" />
                            </motion.div>
                        ) : (
                            <motion.div
                                key="micoff"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                            >
                                <MicOff className="w-16 h-16 text-gray-400" />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.button>

                {/* Reset Button */}
                <button
                    onClick={() => { setState("idle"); isPlaying.current = false; audioQueue.current = []; setLogs([]); }}
                    className="absolute bottom-[-60px] text-[10px] text-gray-600 hover:text-red-500 font-mono tracking-widest uppercase transition-colors"
                >
                    [ SYSTEM_RESET ]
                </button>
            </div>

            {/* Visualizer & Logs */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="w-full grid grid-cols-1 md:grid-cols-2 gap-6"
            >
                {/* Visualizer */}
                <div className="glass rounded-xl p-6 relative overflow-hidden flex items-center justify-center border border-purple-500/10">
                    <div className="absolute top-3 left-4 text-[10px] font-mono text-purple-400/50 flex items-center gap-2">
                        <Zap size={10} /> FREQUENCY_DOMAIN
                    </div>
                    <AudioVisualizer isListening={state === "listening"} isSpeaking={state === "speaking"} audioData={freqData} />
                </div>

                {/* Terminal */}
                <div className="glass rounded-xl p-4 font-mono text-xs h-48 overflow-y-auto border border-purple-500/10 bg-black/20">
                    <div className="sticky top-0 bg-transparent text-purple-400/50 mb-2 text-[10px] flex items-center gap-2">
                        <Terminal size={10} /> SYSTEM_LOGS
                    </div>
                    <div className="space-y-1">
                        {logs.map((log, i) => (
                            <div key={i} className="text-gray-400">
                                <span className="text-purple-500/50 mr-2">{">"}</span>{log}
                            </div>
                        ))}
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
