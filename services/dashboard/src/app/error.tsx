"use client";

export default function PageError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 space-y-4">
      <p className="text-red-600 font-medium">Failed to load data</p>
      <p className="text-sm text-gray-500">{error.message}</p>
      <button
        onClick={reset}
        className="px-4 py-2 bg-green-700 text-white rounded text-sm hover:bg-green-800"
      >
        Retry
      </button>
    </div>
  );
}
