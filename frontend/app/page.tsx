import AgentFeed from "./components/AgentFeed";
import MemoryViewer from "./components/MemoryViewer";
import PerfChart from "./components/PerfChart";
import Portfolio from "./components/Portfolio";
import SignalBoard from "./components/SignalBoard";
import TradeHistory from "./components/TradeHistory";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0d0d0f] p-4 md:p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-[#a78bfa] to-[#60a5fa] bg-clip-text text-transparent">
          Phantom
        </h1>
        <p className="text-[#555] text-sm italic mt-1">&quot;A portfolio that thinks for itself.&quot;</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 flex flex-col gap-4">
          <AgentFeed />
          <PerfChart />
          <TradeHistory />
        </div>

        <div className="flex flex-col gap-4">
          <Portfolio />
          <MemoryViewer />
          <SignalBoard />
        </div>
      </div>
    </main>
  );
}
