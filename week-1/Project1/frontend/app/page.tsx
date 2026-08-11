"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type Message = {
  role: "user" | "assistant";
  text: string;
};

export default function Home() {
  const router = useRouter();

  const [authorized, setAuthorized] = useState(false);

  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "👋 Hello! I am McCain Employee Assistant. How can I help you today?",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {

    const token = localStorage.getItem(
      "access_token"
    );

    if (!token) {

      router.replace("/login");

      return;

    }

    setAuthorized(true);

  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages]);

  const logout = () => {

    localStorage.removeItem(
      "access_token"
    );

    localStorage.removeItem(
      "refresh_token"
    );

    router.push("/login");

  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const question = input.trim();

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        text: question,
      },
      {
        role: "assistant",
        text: "",
      },
    ]);

    setInput("");
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/chat/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify({
          message: question,
        }),
      });

      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }

      if (!response.body) {
        throw new Error("The server returned an empty response");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let answer = "";

      while (true) {
        const { value, done } = await reader.read();

        if (done) {
          break;
        }

        const chunk = decoder.decode(value, {
          stream: true,
        });

        if (!chunk) {
          continue;
        }

        for (const character of chunk) {
          answer += character;

          setMessages((prev) => {
            const updated = [...prev];
            const lastIndex = updated.length - 1;

            if (updated[lastIndex]?.role === "assistant") {
              updated[lastIndex] = {
                role: "assistant",
                text: answer,
              };
            }

            return updated;
          });

          await new Promise((resolve) => setTimeout(resolve, 10));
        }
      }

      const remaining = decoder.decode();

      if (remaining) {
        answer += remaining;

        setMessages((prev) => {
          const updated = [...prev];
          const lastIndex = updated.length - 1;

          if (updated[lastIndex]?.role === "assistant") {
            updated[lastIndex] = {
              role: "assistant",
              text: answer,
            };
          }

          return updated;
        });
      }

      if (!answer.trim()) {
        throw new Error("The server returned an empty response");
      }
    } catch (error) {
      console.error("Streaming error:", error);

      setMessages((prev) => {
        const updated = [...prev];
        const lastIndex = updated.length - 1;

        if (updated[lastIndex]?.role === "assistant") {
          updated[lastIndex] = {
            role: "assistant",
            text: "❌ Unable to connect to server.",
          };
        }

        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  if (!authorized) {

    return null;

  }

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-6">
      <div className="w-full max-w-3xl h-[85vh] bg-white rounded-2xl shadow-xl flex flex-col">
        <div className="bg-red-500 text-white p-5 rounded-t-2xl">

  <div className="flex items-center justify-between">

    <div className="flex items-center gap-4">

      <img
        src="/mccain-logo.jpg"
        alt="McCain Logo"
        className="h-36 w-auto bg-red-500 rounded-lg p-1"
      />

      <div>

        <h1 className="text-2xl font-bold">
          McCain Employee Assistant
        </h1>

        <p className="text-sm opacity-90">
          Ask anything about McCain 
        </p>

      </div>

    </div>

    <button
      onClick={logout}
      className="bg-white text-red-600 px-5 py-2 rounded-lg font-semibold hover:bg-gray-100 transition"
    >
      Logout
    </button>

  </div>

</div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[75%] px-5 py-3 rounded-2xl shadow ${
                  message.role === "user"
                    ? "bg-yellow-500 text-white rounded-br-sm"
                    : "bg-gray-200 text-black rounded-bl-sm"
                }`}
              >
                <p className="text-sm font-semibold mb-1">
                  {message.role === "user" ? "You" : "McCain AI"}
                </p>
                <p className="whitespace-pre-wrap">{message.text}</p>
              </div>
            </div>
          ))}

          <div ref={bottomRef} />
        </div>

        <div className="border-t p-4">
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Ask a question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !loading) {
                  void sendMessage();
                }
              }}
className="flex-1 border rounded-xl px-4 py-3 text-black placeholder:text-gray-500 outline-none focus:ring-2 focus:ring-yellow-500"            />

            <button
              onClick={() => void sendMessage()}
              disabled={loading}
              className="bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-400 text-white px-6 rounded-xl font-semibold transition"
            >
              Send
            </button>
          </div>

          <p className="text-xs text-gray-500 mt-2">
            Powered by FastAPI • Gemini • Qdrant
          </p>
        </div>
      </div>
    </div>
  );
}
