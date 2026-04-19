'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { KanbanBoard } from "@/components/KanbanBoard";

export default function Home() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await fetch('/auth/check', {
        credentials: 'include',
      });
      const data = await response.json();
      setIsAuthenticated(data.authenticated);
    } catch (err) {
      setIsAuthenticated(false);
      console.error('Auth check error:', err);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
        credentials: 'include',
      });

      if (response.ok) {
        setIsAuthenticated(true);
        setUsername('');
        setPassword('');
      } else {
        setError('Invalid username or password');
      }
    } catch (err) {
      setError('Login failed. Please try again.');
      console.error('Login error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
      setIsAuthenticated(false);
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  if (isAuthenticated === null) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-[#888888]">Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#032147] to-[#209dd7] px-4">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-2xl shadow-2xl p-8">
            <h1 className="text-3xl font-bold text-[#032147] mb-2 text-center">
              Project Management
            </h1>
            <p className="text-[#888888] text-center mb-8">Sign in to your account</p>

            <form onSubmit={handleLogin} className="space-y-6">
              <div>
                <label htmlFor="username" className="block text-sm font-semibold text-[#032147] mb-2">
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="user"
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-[#209dd7] transition"
                  disabled={loading}
                  autoComplete="username"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-semibold text-[#032147] mb-2">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="password"
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-[#209dd7] transition"
                  disabled={loading}
                  autoComplete="current-password"
                />
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-700 text-sm">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-[#753991] hover:bg-[#5f2d79] disabled:bg-gray-400 text-white font-semibold rounded-lg transition duration-200"
              >
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
            </form>

            <div className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-100">
              <p className="text-xs text-[#888888] mb-2">
                <strong>Demo Credentials:</strong>
              </p>
              <p className="text-xs text-[#888888]">Username: <code className="bg-white px-2 py-1 rounded">user</code></p>
              <p className="text-xs text-[#888888]">Password: <code className="bg-white px-2 py-1 rounded">password</code></p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      <header className="bg-[#032147] text-white p-4 shadow-lg">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <h1 className="text-2xl font-bold">Project Management</h1>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-[#753991] hover:bg-[#5f2d79] rounded-lg text-white font-semibold transition"
          >
            Logout
          </button>
        </div>
      </header>
      <main className="flex-1">
        <KanbanBoard />
      </main>
    </div>
  );
}
