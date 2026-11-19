"use client";

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-center space-y-4">
          <h2 className="text-xl font-semibold text-red-600">Something went wrong</h2>
          <p className="text-sm text-gray-500">{error.message}</p>
          <button
            onClick={reset}
            className="px-4 py-2 bg-green-700 text-white rounded text-sm hover:bg-green-800"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
