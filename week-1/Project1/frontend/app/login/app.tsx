"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (
    e: React.FormEvent
  ) => {
    e.preventDefault();

    setError("");
    setLoading(true);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/v1/auth/login",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            email,
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.message ||
            "Login failed."
        );
      }

      localStorage.setItem(
        "access_token",
        data.data.access_token
      );

      localStorage.setItem(
        "refresh_token",
        data.data.refresh_token
      );

      router.push("/");
    } catch (err: any) {
      setError(
        err.message ||
          "Unable to login."
      );
    }

    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-100 flex justify-center items-center p-6">

      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl p-8">

        <div className="flex flex-col items-center">

          <Image
            src="/mccain-logo.png"
            alt="McCain"
            width={90}
            height={90}
            className="mb-4"
          />

          <h1 className="text-3xl font-bold text-gray-800">
            Welcome Back
          </h1>

          <p className="text-gray-500 mt-2">
            Login to continue
          </p>

        </div>

        <form
          onSubmit={handleLogin}
          className="mt-8 space-y-5"
        >

          <div>

            <label className="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>

            <input
              type="email"
              value={email}
              onChange={(e) =>
                setEmail(
                  e.target.value
                )
              }
              required
              placeholder="test@mccain.com"
              className="w-full border rounded-lg px-4 py-3 text-black focus:outline-none focus:ring-2 focus:ring-yellow-500"
            />

          </div>

          <div>

            <label className="block text-sm font-medium text-gray-700 mb-2">
              Password
            </label>

            <input
              type="password"
              value={password}
              onChange={(e) =>
                setPassword(
                  e.target.value
                )
              }
              required
              placeholder="********"
              className="w-full border rounded-lg px-4 py-3 text-black focus:outline-none focus:ring-2 focus:ring-yellow-500"
            />

          </div>

          {error && (

            <div className="bg-red-100 text-red-600 border border-red-300 rounded-lg p-3 text-sm">

              {error}

            </div>

          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-yellow-500 hover:bg-yellow-600 text-white font-semibold py-3 rounded-lg transition disabled:bg-gray-400"
          >

            {loading
              ? "Logging in..."
              : "Login"}

          </button>

        </form>

        <div className="mt-6 text-center">

          <p className="text-gray-600">

            Don't have an account?{" "}

            <button
              onClick={() =>
                router.push(
                  "/register"
                )
              }
              className="text-yellow-600 font-semibold hover:underline"
            >

              Register

            </button>

          </p>

        </div>

      </div>

    </div>
  );
}