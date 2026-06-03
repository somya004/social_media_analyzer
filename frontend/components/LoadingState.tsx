export default function LoadingState({ message = "Extracting and indexing content..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center gap-4 py-10">
      <div className="flex gap-2 items-end h-8">
        {[0, 1, 2, 3].map(i => (
          <span
            key={i}
            className="w-2 rounded-full bg-indigo-400"
            style={{
              height: "8px",
              animation: `bounce-dot 1.2s ease-in-out ${i * 0.15}s infinite`,
            }}
          />
        ))}
      </div>
      <p className="text-xs font-mono text-zinc-500 text-center">{message}</p>
      <style>{`
        @keyframes bounce-dot {
          0%,100%{transform:translateY(0);opacity:.3;height:8px}
          50%{transform:translateY(-10px);opacity:1;height:16px}
        }
      `}</style>
    </div>
  );
}
