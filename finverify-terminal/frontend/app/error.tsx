"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex-1 flex items-center justify-center min-h-[60vh]">
      <div className="panel p-8 max-w-md w-full text-center space-y-4 border-l-4 border-t-red">
        <div className="text-t-red font-mono text-sm font-bold tracking-widest">
          SYSTEM ERROR
        </div>
        <div className="text-t-secondary font-mono text-xs leading-relaxed">
          {error.message || "BACKEND UNREACHABLE — The DVL engine is not responding."}
        </div>
        <div className="text-t-muted font-mono text-[10px]">
          Check that the backend is running on port 8000
        </div>
        <button
          onClick={reset}
          className="px-5 py-2 bg-t-red/10 border border-t-red/30 text-t-red font-mono text-xs font-bold uppercase tracking-wider hover:bg-t-red/20 transition-colors"
        >
          ▶ RETRY CONNECTION
        </button>
      </div>
    </div>
  );
}
