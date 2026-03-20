import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center h-screen gap-4">
      <h1 className="text-4xl font-black tracking-tight uppercase">Titan Cold Caller</h1>
      <Link 
        href="/command-center" 
        className="px-6 py-2 bg-neon-emerald text-background rounded font-bold hover:opacity-90 transition-opacity uppercase tracking-widest text-sm"
      >
        Enter Command Center
      </Link>
    </div>
  );
}
