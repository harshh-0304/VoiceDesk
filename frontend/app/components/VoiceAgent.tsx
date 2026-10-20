"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Mic, MicOff, Activity, Zap, Terminal, Volume2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import AudioVisualizer from "./AudioVisualizer";
import { cn } from "@/lib/utils";

// Types
type AgentState = "idle" | "listening" | "thinking" | "speaking";

const SILENCE_THRESHOLD = 20; // 0-255 energy level
const SILENCE_DURATION_MS = 1500; // ms of silence before auto-commit

export default function VoiceAgent() {
    const [isConnected, setIsConnected] = useState(false);
    const [state, setState] = useState<AgentState>("idle");
    const [transcription, setTranscription] = useState("");
    const [assistantResponse, setAssistantResponse] = useState("");
    const [logs, setLogs] = useState<string[]>([]);
    const [freqData, setFreqData] = useState<number[]>(() => new Array(60).fill(0));

    // Core Refs
    const wsRef = useRef<WebSocket | null>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const audioQueueRef = useRef<string[]>([]); // Base64 audio chunks
    const isPlayingRef = useRef(false);
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const silenceStartRef = useRef<number | null>(null);
    const processingRef = useRef(false);
    const animFrameRef = useRef<number | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const stateRef = useRef<AgentState>(state);

    // Stable Callback Function Refs for React 19 Lifecycle
    const processAudioQueueRef = useRef<() => void>(() => {});
    const monitorSilenceRef = useRef<() => void>(() => {});
    const connectWebSocketRef = useRef<() => void>(() => {});
    const startListeningRef = useRef<() => void>(() => {});
    const stopListeningRef = useRef<() => void>(() => {});

    useEffect(() => {
        stateRef.current = state;
    }, [state]);

    const addLog = useCallback((msg: string) => {
        const timeStr = new Date().toLocaleTimeString();
        setLogs((prev) => [...prev.slice(-6), `[${timeStr}] ${msg}`]);
    }, []);

    // Audio Playback Processing
    const processAudioQueue = useCallback(async () => {
        if (isPlayingRef.current || audioQueueRef.current.length === 0) return;

        isPlayingRef.current = true;
        const chunk = audioQueueRef.current.shift();
        if (!chunk) {
            isPlayingRef.current = false;
            return;
        }

        try {
            const binaryString = atob(chunk);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            if (!audioContextRef.current) {
                audioContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
            }

            if (audioContextRef.current.state === "suspended") {
                await audioContextRef.current.resume();
            }

            audioContextRef.current.decodeAudioData(
                bytes.buffer,
                (audioBuffer) => {
                    if (!audioContextRef.current) return;
                    const source = audioContextRef.current.createBufferSource();
                    source.buffer = audioBuffer;
                    source.connect(audioContextRef.current.destination);
                    source.onended = () => {
                        isPlayingRef.current = false;
                        processAudioQueueRef.current();
                    };
                    source.start(0);
                },
                (err) => {
                    console.error("Audio decode error:", err);
                    isPlayingRef.current = false;
                    processAudioQueueRef.current();
                }
            );
        } catch (e) {
            console.error("Audio playback queue error:", e);
            isPlayingRef.current = false;
            processAudioQueueRef.current();
        }
    }, []);

    useEffect(() => {
        processAudioQueueRef.current = processAudioQueue;
    }, [processAudioQueue]);

    // Stop recording and send audio
    const stopListening = useCallback(() => {
        if (animFrameRef.current) {
            cancelAnimationFrame(animFrameRef.current);
            animFrameRef.current = null;
        }

        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
            processingRef.current = true;
            mediaRecorderRef.current.stop();
            mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
        }
    }, []);

    useEffect(() => {
        stopListeningRef.current = stopListening;
    }, [stopListening]);

    // VAD & silence polling
    const monitorSilence = useCallback(() => {
        if (stateRef.current !== "listening") return;
        if (!analyserRef.current) return;

        const bufferLength = analyserRef.current.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        analyserRef.current.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
        }
        const average = sum / bufferLength;

        // Visualizer snapshot
        setFreqData(Array.from(dataArray.slice(0, 60)));

        const now = performance.now();
        if (average > SILENCE_THRESHOLD) {
            silenceStartRef.current = null;
        } else {
            if (silenceStartRef.current === null) {
                silenceStartRef.current = now;
            } else if (now - silenceStartRef.current > SILENCE_DURATION_MS) {
                addLog("Silence detected. Committing audio...");
                stopListeningRef.current();
                return;
            }
        }

        animFrameRef.current = requestAnimationFrame(() => {
            monitorSilenceRef.current();
        });
    }, [addLog]);

    useEffect(() => {
        monitorSilenceRef.current = monitorSilence;
    }, [monitorSilence]);

    // Start microphone capture
    const startListening = useCallback(async () => {
        try {
            if (!audioContextRef.current) {
                audioContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
            }
            if (audioContextRef.current.state === "suspended") {
                await audioContextRef.current.resume();
            }

            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 16000,
                },
            });

            const source = audioContextRef.current.createMediaStreamSource(stream);
            analyserRef.current = audioContextRef.current.createAnalyser();
            analyserRef.current.fftSize = 256;
            source.connect(analyserRef.current);

            mediaRecorderRef.current = new MediaRecorder(stream);
            audioChunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (event: BlobEvent) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorderRef.current.onstop = () => {
                if (processingRef.current) {
                    const blob = new Blob(audioChunksRef.current, { type: "audio/wav" });
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        const result = reader.result as string;
                        const base64data = result.split(",")[1];
                        if (base64data && wsRef.current?.readyState === WebSocket.OPEN) {
                            wsRef.current.send(
                                JSON.stringify({ type: "commit", audio_data: base64data })
                            );
                            setState("thinking");
                            setAssistantResponse("");
                        }
                        audioChunksRef.current = [];
                    };
                    reader.readAsDataURL(blob);
                }
            };

            mediaRecorderRef.current.start(250);
            setState("listening");
            processingRef.current = false;
            silenceStartRef.current = null;

            animFrameRef.current = requestAnimationFrame(() => {
                monitorSilenceRef.current();
            });
        } catch (err) {
            console.error("Microphone Access Error:", err);
            addLog("Error: Microphone access denied or unavailable.");
            setState("idle");
        }
    }, [addLog]);

    useEffect(() => {
        startListeningRef.current = startListening;
    }, [startListening]);

    // WebSocket link
    const connectWebSocket = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }

        const socketUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/audio";
        const ws = new WebSocket(socketUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            setIsConnected(true);
            addLog("Connected to VoiceDesk Neural Core.");
        };

        ws.onclose = () => {
            setIsConnected(false);
            addLog("Connection severed. Retrying in 3 seconds...");
            reconnectTimeoutRef.current = setTimeout(() => {
                connectWebSocketRef.current();
            }, 3000);
        };

        ws.onerror = (err) => {
            console.error("WebSocket Error:", err);
            ws.close();
        };

        ws.onmessage = async (event: MessageEvent) => {
            try {
                const msg = JSON.parse(event.data);

                if (msg.type === "transcription") {
                    setTranscription(msg.text);
                    addLog(`User: "${msg.text}"`);
                    setState("thinking");
                } else if (msg.type === "text_delta") {
                    setAssistantResponse((prev) => prev + (msg.delta || ""));
                } else if (msg.type === "response_complete") {
                    if (msg.text) setAssistantResponse(msg.text);
                } else if (msg.type === "status") {
                    if (msg.state === "speaking") {
                        setState("speaking");
                    } else if (msg.state === "listening") {
                        setState("idle");
                    }
                } else if (msg.type === "audio_stream") {
                    audioQueueRef.current.push(msg.data);
                    processAudioQueueRef.current();
                } else if (msg.type === "error") {
                    addLog(`Server: ${msg.message}`);
                }
            } catch (err) {
                console.error("Failed to parse websocket message:", err);
            }
        };
    }, [addLog]);

    useEffect(() => {
        connectWebSocketRef.current = connectWebSocket;
    }, [connectWebSocket]);

    useEffect(() => {
        connectWebSocket();
        return () => {
            if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
            if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
            if (wsRef.current) wsRef.current.close();
        };
    }, [connectWebSocket]);

    const handleReset = () => {
        setState("idle");
        isPlayingRef.current = false;
        audioQueueRef.current = [];
        setAssistantResponse("");
        setTranscription("");
        setLogs([]);
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "clear_memory" }));
        }
        addLog("System reset. Session memory cleared.");
    };

    return (
        <div className="flex flex-col items-center justify-center w-full min-h-[80vh] space-y-10">
            {/* Header Badge */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between w-full max-w-2xl px-6 py-3 glass rounded-full border border-purple-500/20 shadow-[0_0_15px_rgba(168,85,247,0.1)]"
            >
                <div className="flex items-center space-x-3">
                    <div
                        className={cn(
                            "w-3 h-3 rounded-full transition-all duration-300",
                            isConnected
                                ? "bg-emerald-400 shadow-[0_0_10px_#34d399]"
                                : "bg-rose-500 shadow-[0_0_10px_#f43f5e]"
                        )}
                    />
                    <span className="text-xs font-bold tracking-[0.2em] text-purple-100 font-orbitron">
                        VOICEDESK // SHADOW_MONARCH
                    </span>
                </div>
                <div className="flex items-center space-x-2 text-xs font-mono text-purple-300">
                    <Activity size={14} className={state === "listening" ? "animate-pulse text-purple-400" : ""} />
                    <span>{state.toUpperCase()}</span>
                </div>
            </motion.div>

            {/* Core Interaction Sphere */}
            <div className="relative w-80 h-80 flex items-center justify-center">
                {/* Dynamic Ambient Aura */}
                <motion.div
                    animate={{
                        scale: state === "listening" ? [1, 1.25, 1] : state === "speaking" ? [1, 1.15, 1] : 1,
                        opacity: state === "listening" ? 0.45 : state === "speaking" ? 0.35 : 0.1,
                    }}
                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                    className="absolute inset-0 bg-purple-600 rounded-full blur-3xl pointer-events-none"
                />

                {/* Primary Interaction Button */}
                <motion.button
                    type="button"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={state === "idle" ? startListening : stopListening}
                    aria-label={state === "listening" ? "Stop recording speech" : "Start recording speech"}
                    className={cn(
                        "relative z-10 w-40 h-40 rounded-full glass flex items-center justify-center border-4 transition-all duration-300 cursor-pointer",
                        state === "listening"
                            ? "border-purple-400 shadow-[0_0_50px_rgba(168,85,247,0.85)] bg-purple-900/30"
                            : state === "speaking"
                            ? "border-emerald-400 shadow-[0_0_35px_rgba(52,211,153,0.6)] bg-emerald-950/20"
                            : "border-gray-600 shadow-[0_0_20px_rgba(255,255,255,0.08)] hover:border-purple-400 hover:bg-white/5"
                    )}
                >
                    <AnimatePresence mode="wait">
                        {state === "listening" ? (
                            <motion.div
                                key="mic-on"
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.8 }}
                            >
                                <Mic className="w-16 h-16 text-purple-300 drop-shadow-[0_0_12px_rgba(168,85,247,0.9)] animate-pulse" />
                            </motion.div>
                        ) : state === "speaking" ? (
                            <motion.div
                                key="speaking-icon"
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.8 }}
                            >
                                <Volume2 className="w-16 h-16 text-emerald-400 drop-shadow-[0_0_12px_rgba(52,211,153,0.8)]" />
                            </motion.div>
                        ) : (
                            <motion.div
                                key="mic-off"
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.8 }}
                            >
                                <MicOff className="w-16 h-16 text-gray-400" />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.button>

                {/* Reset Trigger */}
                <button
                    type="button"
                    onClick={handleReset}
                    className="absolute bottom-[-45px] text-[10px] text-gray-500 hover:text-rose-400 font-mono tracking-widest uppercase transition-colors cursor-pointer"
                >
                    [ RESET_SESSION ]
                </button>
            </div>

            {/* Live Conversation Display */}
            {(transcription || assistantResponse) && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="w-full max-w-2xl glass rounded-xl p-5 border border-purple-500/20 text-sm space-y-3"
                >
                    {transcription && (
                        <div className="flex items-start space-x-2 text-purple-200">
                            <span className="font-mono text-xs uppercase text-purple-400 font-semibold min-w-16">User:</span>
                            <span className="italic">{transcription}</span>
                        </div>
                    )}
                    {assistantResponse && (
                        <div className="flex items-start space-x-2 text-gray-100">
                            <span className="font-mono text-xs uppercase text-emerald-400 font-semibold min-w-16">VoiceDesk:</span>
                            <span>{assistantResponse}</span>
                        </div>
                    )}
                </motion.div>
            )}

            {/* Visualizer & System Logs */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
                className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-6"
            >
                {/* Audio Spectrum Visualizer */}
                <div className="glass rounded-xl p-6 relative overflow-hidden flex items-center justify-center border border-purple-500/10 min-h-[180px]">
                    <div className="absolute top-3 left-4 text-[10px] font-mono text-purple-400/60 flex items-center gap-2">
                        <Zap size={10} /> FREQUENCY_DOMAIN
                    </div>
                    <AudioVisualizer
                        isListening={state === "listening"}
                        isSpeaking={state === "speaking"}
                        audioData={freqData}
                    />
                </div>

                {/* System Logs Stream */}
                <div className="glass rounded-xl p-4 font-mono text-xs h-48 overflow-y-auto border border-purple-500/10 bg-black/20">
                    <div className="sticky top-0 bg-transparent text-purple-400/60 mb-2 text-[10px] flex items-center gap-2">
                        <Terminal size={10} /> SYSTEM_TELEMETRY
                    </div>
                    <div className="space-y-1">
                        {logs.map((log, i) => (
                            <div key={i} className="text-gray-400 text-[11px] leading-relaxed">
                                <span className="text-purple-400/70 mr-1.5">&gt;</span>
                                {log}
                            </div>
                        ))}
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
