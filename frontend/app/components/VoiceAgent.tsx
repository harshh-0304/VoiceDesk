"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Mic, MicOff, Activity, Zap, Terminal, Volume2, Send, Copy, Check, RotateCcw } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import AudioVisualizer from "./AudioVisualizer";
import { cn } from "@/lib/utils";

// Types
type AgentState = "idle" | "listening" | "thinking" | "speaking";

const SILENCE_ENERGY_THRESHOLD = 12; // Energy level threshold to detect silence
const SILENCE_DURATION_MS = 4000; // ms of silence before auto-commit
const MIN_RECORDING_DURATION_MS = 3000; // Must record at least 3s before silence detector activates

interface SpeechRecognitionEventLike {
    resultIndex: number;
    results: {
        length: number;
        [index: number]: {
            isFinal: boolean;
            [index: number]: { transcript: string };
        };
    };
}

interface SpeechRecognitionErrorLike {
    error: string;
}

interface SpeechRecognitionLike {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    start: () => void;
    stop: () => void;
    onstart: (() => void) | null;
    onresult: ((event: SpeechRecognitionEventLike) => void) | null;
    onend: (() => void) | null;
    onerror: ((event: SpeechRecognitionErrorLike) => void) | null;
}

export default function VoiceAgent() {
    const [isConnected, setIsConnected] = useState(false);
    const [state, setState] = useState<AgentState>("idle");
    const [transcription, setTranscription] = useState("");
    const [assistantResponse, setAssistantResponse] = useState("");
    const [textInput, setTextInput] = useState("");
    const [logs, setLogs] = useState<string[]>([]);
    const [freqData, setFreqData] = useState<number[]>(() => new Array(60).fill(0));
    const [audioDevices, setAudioDevices] = useState<{ deviceId: string; label: string }[]>([]);
    const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
    const [micVolume, setMicVolume] = useState<number>(0);
    const [copied, setCopied] = useState(false);

    // Core Refs
    const wsRef = useRef<WebSocket | null>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const audioQueueRef = useRef<string[]>([]); // Base64 audio chunks
    const isPlayingRef = useRef(false);
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const silenceStartRef = useRef<number | null>(null);
    const recordingStartTimeRef = useRef<number>(0);
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

    const refreshAudioDevices = useCallback(async () => {
        try {
            if (!navigator.mediaDevices?.enumerateDevices) return;
            const devices = await navigator.mediaDevices.enumerateDevices();
            const audioInputs = devices
                .filter((d) => d.kind === "audioinput")
                .map((d, i) => ({
                    deviceId: d.deviceId,
                    label: d.label || `Microphone ${i + 1}`,
                }));
            setAudioDevices(audioInputs);
            if (audioInputs.length > 0) {
                setSelectedDeviceId((prev) => prev || audioInputs[0].deviceId);
            }
        } catch (err) {
            console.error("Failed to enumerate audio devices:", err);
        }
    }, []);

    useEffect(() => {
        let isMounted = true;
        const init = async () => {
            try {
                if (!navigator.mediaDevices?.enumerateDevices) return;
                const devices = await navigator.mediaDevices.enumerateDevices();
                if (!isMounted) return;
                const audioInputs = devices
                    .filter((d) => d.kind === "audioinput")
                    .map((d, i) => ({
                        deviceId: d.deviceId,
                        label: d.label || `Microphone ${i + 1}`,
                    }));
                setAudioDevices(audioInputs);
                if (audioInputs.length > 0) {
                    setSelectedDeviceId((prev) => prev || audioInputs[0].deviceId);
                }
            } catch (err) {
                console.error("Failed to initialize audio devices:", err);
            }
        };

        void init();
        navigator.mediaDevices?.addEventListener("devicechange", refreshAudioDevices);
        return () => {
            isMounted = false;
            navigator.mediaDevices?.removeEventListener("devicechange", refreshAudioDevices);
        };
    }, [refreshAudioDevices]);

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

        if (recognitionRef.current) {
            try {
                recognitionRef.current.stop();
            } catch {
                // Ignore errors when stopping already inactive recognition
            }
        }

        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
            processingRef.current = true;
            mediaRecorderRef.current.stop();
        }
    }, []);

    useEffect(() => {
        stopListeningRef.current = stopListening;
    }, [stopListening]);

    // Send query to VoiceDesk backend (via text or transcribed voice)
    const sendTextQuery = useCallback((queryText: string) => {
        const prompt = queryText.trim();
        if (!prompt) return;

        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            addLog("Error: Backend is offline. Connecting...");
            connectWebSocketRef.current();
            return;
        }

        wsRef.current.send(JSON.stringify({ type: "text_query", text: prompt }));
        setTranscription(prompt);
        setAssistantResponse("");
        setState("thinking");
        addLog(`User: "${prompt}"`);
    }, [addLog]);

    const handleCopyResponse = useCallback(() => {
        if (!assistantResponse) return;
        void navigator.clipboard.writeText(assistantResponse).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }).catch(() => {});
    }, [assistantResponse]);

    const handleClearConversation = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "clear_memory" }));
        }
        setTranscription("");
        setAssistantResponse("");
        addLog("Conversation context cleared.");
    }, [addLog]);

    // VAD & silence polling
    const monitorSilence = useCallback(() => {
        if (stateRef.current !== "listening") return;
        if (!analyserRef.current) return;

        const bufferLength = analyserRef.current.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        analyserRef.current.getByteFrequencyData(dataArray);

        // Measure energy in human vocal range (bins 2 to 35, ~80Hz to ~3500Hz)
        let vocalEnergy = 0;
        const maxBin = Math.min(bufferLength, 35);
        for (let i = 2; i < maxBin; i++) {
            vocalEnergy += dataArray[i];
        }
        const vocalAverage = vocalEnergy / (maxBin - 2);

        // Update live VU volume meter (0-100)
        setMicVolume(Math.min(100, Math.round((vocalAverage / 128) * 100 * 2.5)));

        // Visualizer snapshot
        setFreqData(Array.from(dataArray.slice(0, 60)));

        const now = performance.now();
        // Give user minimum recording duration before silence detector activates
        if (now - recordingStartTimeRef.current < MIN_RECORDING_DURATION_MS) {
            silenceStartRef.current = null;
        } else if (vocalAverage > SILENCE_ENERGY_THRESHOLD) {
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

    // Start microphone capture with Native Chrome Speech Recognition + Visualizer
    const startListening = useCallback(async () => {
        try {
            if (!audioContextRef.current) {
                audioContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
            }
            if (audioContextRef.current.state === "suspended") {
                await audioContextRef.current.resume();
            }

            const audioConstraints: MediaTrackConstraints = {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                ...(selectedDeviceId ? { deviceId: { exact: selectedDeviceId } } : {}),
            };

            const stream = await navigator.mediaDevices.getUserMedia({
                audio: audioConstraints,
            });

            refreshAudioDevices();

            const source = audioContextRef.current.createMediaStreamSource(stream);
            analyserRef.current = audioContextRef.current.createAnalyser();
            analyserRef.current.fftSize = 512;
            analyserRef.current.smoothingTimeConstant = 0.5;
            source.connect(analyserRef.current);

            // Animate visualizer frequency bars
            const monitorVisualizer = () => {
                if (!analyserRef.current) return;
                const bufferLength = analyserRef.current.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);
                analyserRef.current.getByteFrequencyData(dataArray);

                setFreqData(Array.from(dataArray.slice(0, 60)));

                let energy = 0;
                for (let i = 2; i < 35; i++) energy += dataArray[i];
                setMicVolume(Math.min(100, Math.round((energy / 33 / 128) * 100 * 2.5)));

                animFrameRef.current = requestAnimationFrame(monitorVisualizer);
            };

            // Check if Native Chrome Speech Recognition is available
            const SpeechRec = typeof window !== "undefined"
                ? ((window as unknown as { SpeechRecognition?: new () => SpeechRecognitionLike; webkitSpeechRecognition?: new () => SpeechRecognitionLike }).SpeechRecognition ||
                   (window as unknown as { SpeechRecognition?: new () => SpeechRecognitionLike; webkitSpeechRecognition?: new () => SpeechRecognitionLike }).webkitSpeechRecognition)
                : undefined;
            if (SpeechRec) {
                const rec = new SpeechRec();
                rec.continuous = false;
                rec.interimResults = true;
                rec.lang = "en-US";

                rec.onstart = () => {
                    setState("listening");
                    addLog("Listening to speech... Speak clearly now.");
                    animFrameRef.current = requestAnimationFrame(monitorVisualizer);
                };

                let finalSpeech = "";
                rec.onresult = (evt: SpeechRecognitionEventLike) => {
                    let interim = "";
                    for (let i = evt.resultIndex; i < evt.results.length; i++) {
                        const res = evt.results[i];
                        if (res.isFinal) {
                            finalSpeech += res[0].transcript;
                        } else {
                            interim += res[0].transcript;
                        }
                    }
                    const live = finalSpeech || interim;
                    if (live) setTranscription(live);
                };

                rec.onend = () => {
                    if (animFrameRef.current) {
                        cancelAnimationFrame(animFrameRef.current);
                        animFrameRef.current = null;
                    }
                    stream.getTracks().forEach((t) => t.stop());

                    if (finalSpeech.trim()) {
                        addLog(`Captured: "${finalSpeech.trim()}"`);
                        sendTextQuery(finalSpeech.trim());
                    } else {
                        addLog("No speech recognized. Click orb to try again or type below.");
                        setState("idle");
                    }
                };

                rec.onerror = (err: SpeechRecognitionErrorLike) => {
                    console.warn("Speech recognition notice:", err.error);
                    if (err.error === "no-speech") {
                        addLog("No speech detected. Please speak closer to your mic or type below.");
                    } else if (err.error === "not-allowed") {
                        addLog("Error: Microphone permission was denied in Chrome.");
                    }
                    setState("idle");
                };

                recognitionRef.current = rec;
                rec.start();
                return;
            }

            // Fallback: MediaRecorder if SpeechRecognition is not supported
            const mimeType = typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                ? "audio/webm;codecs=opus"
                : typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported("audio/webm")
                ? "audio/webm"
                : "";

            const recorderOptions: MediaRecorderOptions = mimeType ? { mimeType } : {};
            mediaRecorderRef.current = new MediaRecorder(stream, recorderOptions);
            audioChunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (event: BlobEvent) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorderRef.current.onstop = () => {
                if (mediaRecorderRef.current?.stream) {
                    mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
                }

                if (processingRef.current) {
                    const actualType = mediaRecorderRef.current?.mimeType || "audio/webm";
                    const blob = new Blob(audioChunksRef.current, { type: actualType });
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        const result = reader.result as string;
                        const base64data = result.split(",")[1];
                        if (base64data && wsRef.current?.readyState === WebSocket.OPEN) {
                            addLog(`Sending ${Math.round(blob.size / 1024)} KB audio to server...`);
                            wsRef.current.send(
                                JSON.stringify({ type: "commit", audio_data: base64data })
                            );
                            setState("thinking");
                            setAssistantResponse("");
                        } else {
                            addLog("Error: Backend is offline (ws://127.0.0.1:8000). Please check server.");
                            setState("idle");
                        }
                        audioChunksRef.current = [];
                    };
                    reader.readAsDataURL(blob);
                }
            };

            mediaRecorderRef.current.start(100);
            setState("listening");
            processingRef.current = false;
            silenceStartRef.current = null;
            recordingStartTimeRef.current = performance.now();
            addLog("Microphone active. Speak now, then click orb when done.");

            animFrameRef.current = requestAnimationFrame(() => {
                monitorSilenceRef.current();
            });
        } catch (err) {
            console.error("Microphone Access Error:", err);
            addLog("Error: Microphone access denied or unavailable.");
            setState("idle");
        }
    }, [addLog, selectedDeviceId, refreshAudioDevices, sendTextQuery]);

    useEffect(() => {
        startListeningRef.current = startListening;
    }, [startListening]);

    // WebSocket link
    const connectWebSocket = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }

        const socketUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000/ws/audio";
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

    const handleSendText = (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (textInput.trim()) {
            sendTextQuery(textInput);
            setTextInput("");
        }
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
                    className="absolute bottom-[-32px] text-[10px] text-gray-500 hover:text-rose-400 font-mono tracking-widest uppercase transition-colors cursor-pointer"
                >
                    [ RESET_SESSION ]
                </button>
            </div>

            {/* Live Status Hint */}
            <div className="text-xs font-mono text-center tracking-wide h-6">
                {state === "listening" ? (
                    <span className="text-purple-300 animate-pulse font-semibold">
                        ● Listening... Speak now (click orb again when done)
                    </span>
                ) : state === "thinking" ? (
                    <span className="text-amber-300 animate-pulse">
                        ⟳ Transcribing speech &amp; generating response...
                    </span>
                ) : state === "speaking" ? (
                    <span className="text-emerald-300 font-semibold">
                        ▶ VoiceDesk is speaking out loud...
                    </span>
                ) : (
                    <span className="text-gray-400">
                        Click the mic orb to speak, or type a question below
                    </span>
                )}
            </div>

            {/* Quick Interactive Prompt Bar */}
            <form
                onSubmit={handleSendText}
                className="w-full max-w-xl flex items-center gap-2 glass rounded-full px-4 py-2 border border-purple-500/30 focus-within:border-purple-400 transition-colors shadow-[0_0_15px_rgba(168,85,247,0.1)]"
            >
                <input
                    type="text"
                    value={textInput}
                    onChange={(e) => setTextInput(e.target.value)}
                    placeholder="Type a question or click the mic orb above to speak..."
                    className="flex-1 bg-transparent text-sm text-purple-100 placeholder-purple-300/40 outline-none px-2 py-1 font-sans"
                />
                <button
                    type="submit"
                    disabled={!textInput.trim() || !isConnected}
                    className="px-4 py-1.5 rounded-full bg-purple-600/70 hover:bg-purple-600 text-purple-100 text-xs font-mono flex items-center gap-1.5 transition-all disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                >
                    <Send size={13} />
                    <span>SEND</span>
                </button>
            </form>

            {/* Live Conversation Display */}
            {(transcription || assistantResponse) && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="w-full max-w-2xl glass rounded-xl p-5 border border-purple-500/20 text-sm space-y-3"
                >
                    <div className="flex items-center justify-between pb-2 border-b border-purple-500/10 text-xs font-mono text-gray-400">
                        <span>LIVE TRANSCRIPT</span>
                        <div className="flex items-center gap-2">
                            {assistantResponse && (
                                <button
                                    type="button"
                                    onClick={handleCopyResponse}
                                    title="Copy response to clipboard"
                                    className="px-2 py-0.5 rounded hover:bg-purple-500/20 text-purple-300 hover:text-white transition-colors cursor-pointer flex items-center gap-1 text-[11px]"
                                >
                                    {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                                    <span>{copied ? "COPIED" : "COPY"}</span>
                                </button>
                            )}
                            <button
                                type="button"
                                onClick={handleClearConversation}
                                title="Clear conversation memory"
                                className="px-2 py-0.5 rounded hover:bg-purple-500/20 text-gray-400 hover:text-purple-300 transition-colors cursor-pointer flex items-center gap-1 text-[11px]"
                            >
                                <RotateCcw size={12} />
                                <span>CLEAR</span>
                            </button>
                        </div>
                    </div>
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

            {/* Input Device Selector & Audio Level */}
            <div className="flex flex-wrap items-center justify-between w-full max-w-4xl px-4 py-2 glass rounded-lg text-xs font-mono border border-purple-500/20 gap-3">
                <div className="flex items-center gap-2 flex-1 min-w-[260px]">
                    <Mic size={14} className="text-purple-400 shrink-0" />
                    <span className="text-gray-400 shrink-0 text-[11px]">ACTIVE MIC:</span>
                    <select
                        value={selectedDeviceId}
                        onChange={(e) => setSelectedDeviceId(e.target.value)}
                        className="bg-black/60 border border-purple-500/30 rounded px-2 py-1 text-purple-200 outline-none text-xs flex-1 cursor-pointer truncate hover:border-purple-400 transition-colors"
                    >
                        {audioDevices.length === 0 ? (
                            <option value="">Default System Microphone</option>
                        ) : (
                            audioDevices.map((d) => (
                                <option key={d.deviceId} value={d.deviceId} className="bg-neutral-900 text-purple-100">
                                    {d.label}
                                </option>
                            ))
                        )}
                    </select>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-gray-400 text-[10px]">MIC LEVEL:</span>
                    <div className="w-24 h-2.5 bg-black/60 rounded-full overflow-hidden border border-purple-500/30 p-0.5">
                        <div
                            className={cn(
                                "h-full rounded-full transition-all duration-75",
                                micVolume > 30 ? "bg-emerald-400 shadow-[0_0_8px_#34d399]" : micVolume > 10 ? "bg-purple-400" : "bg-purple-900/40"
                            )}
                            style={{ width: `${Math.max(4, micVolume)}%` }}
                        />
                    </div>
                    <span className="text-[10px] font-mono text-purple-300 w-8 text-right">{micVolume}%</span>
                </div>
            </div>

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
