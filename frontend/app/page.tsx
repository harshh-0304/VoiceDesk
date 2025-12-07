import VoiceAgent from "./components/VoiceAgent";
import Particles from "./components/Particles";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-transparent relative overflow-hidden">
      <Particles />
      <div className="z-10 w-full max-w-4xl">
        <VoiceAgent />
      </div>
    </main>
  );
}
