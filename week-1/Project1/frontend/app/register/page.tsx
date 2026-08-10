"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";

export default function RegisterPage() {

  const router = useRouter();

  const [fullName, setFullName] = useState("");

  const [email, setEmail] = useState("");

  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");

  const [success, setSuccess] = useState("");

  const handleRegister = async (
    e: React.FormEvent
  ) => {

    e.preventDefault();

    setError("");

    setSuccess("");

    setLoading(true);

    try {

      const response = await fetch(
        "http://127.0.0.1:8000/api/v1/users/register",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            full_name: fullName,
            email: email,
            password: password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {

        throw new Error(
          data.message ||
          "Only Mccain employees are allowed to register"
        );

      }

      setSuccess(
        "Registration successful! Redirecting to login..."
      );

      setTimeout(() => {

        router.push("/login");

      }, 1500);

    } catch (err: any) {

      setError(
        err.message ||
        "Registration failed."
      );

    }

    setLoading(false);

  };

  return (

    <div className="min-h-screen bg-gray-100 flex justify-center items-center p-6">

      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl p-8">

        <div className="flex flex-col items-center">

          <Image
            src="/mccain-logo.jpg"
            alt="McCain"
            width={90}
            height={90}
            className="mb-4"
          />

          <h1 className="text-3xl font-bold text-gray-800">

            Create Account

          </h1>

          <p className="text-gray-500 mt-2">

            Register to access the AI Assistant

          </p>

        </div>

        <form
          onSubmit={handleRegister}
          className="mt-8 space-y-5"
        >

          <div>

            <label className="block text-sm font-medium text-gray-700 mb-2">

              Full Name

            </label>

            <input
              type="text"
              required
              value={fullName}
              onChange={(e)=>
                setFullName(
                  e.target.value
                )
              }
              placeholder="John Doe"
              className="w-full border rounded-lg px-4 py-3 text-black focus:outline-none focus:ring-2 focus:ring-yellow-500"
            />

          </div>

          <div>

            <label className="block text-sm font-medium text-gray-700 mb-2">

              Email

            </label>

            <input
              type="email"
              required
              value={email}
              onChange={(e)=>
                setEmail(
                  e.target.value
                )
              }
              placeholder="john@mccain.com"
              className="w-full border rounded-lg px-4 py-3 text-black focus:outline-none focus:ring-2 focus:ring-yellow-500"
            />

          </div>

          <div>

            <label className="block text-sm font-medium text-gray-700 mb-2">

              Password

            </label>

            <input
              type="password"
              required
              value={password}
              onChange={(e)=>
                setPassword(
                  e.target.value
                )
              }
              placeholder="********"
              className="w-full border rounded-lg px-4 py-3 text-black focus:outline-none focus:ring-2 focus:ring-yellow-500"
            />

          </div>

          {error && (

            <div className="bg-red-100 border border-red-300 rounded-lg text-red-600 p-3 text-sm">

              {error}

            </div>

          )}

          {success && (

            <div className="bg-green-100 border border-green-300 rounded-lg text-green-700 p-3 text-sm">

              {success}

            </div>

          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-yellow-500 hover:bg-yellow-600 text-white font-semibold py-3 rounded-lg transition disabled:bg-gray-400"
          >

            {

              loading

              ?

              "Creating Account..."

              :

              "Register"

            }

          </button>

        </form>

        <div className="mt-6 text-center">

          <p className="text-gray-600">

            Already have an account?{" "}

            <button
              onClick={()=>
                router.push(
                  "/login"
                )
              }
              className="text-yellow-600 font-semibold hover:underline"
            >

              Login

            </button>

          </p>

        </div>

      </div>

    </div>

  );

}