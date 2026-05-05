export default function Loading() {
  return (
    <div className="flex-1 flex items-center justify-center min-h-[60vh]">
      <div className="text-center space-y-4">
        <div className="text-t-green font-mono text-sm tracking-widest animate-pulse">
          INITIALIZING FINVERIFY TERMINAL...
        </div>
        <div className="flex items-center justify-center gap-1 font-mono text-t-muted text-xs">
          <span>LOADING DVL ENGINE</span>
          <span className="inline-block w-2 h-4 bg-t-green/80 animate-blink" />
        </div>
        <div className="mx-auto w-48 h-[2px] bg-t-border overflow-hidden rounded-full">
          <div className="h-full bg-t-green/60 rounded-full animate-slide-up" style={{ width: "60%" }} />
        </div>
      </div>
    </div>
  );
}
