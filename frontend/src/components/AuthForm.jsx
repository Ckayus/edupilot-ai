
import { useState } from "react";
import { loginStudent, registerStudent } from "../services/api";

export default function AuthForm({ onLogin }) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isRegistering) {
        await registerStudent(email, password);
      }

      await loginStudent(email, password);
      onLogin();
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-container">
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>EduPilot AI</h1>

        <p>
          {isRegistering
            ? "Create your student account"
            : "Log in to continue learning"}
        </p>

        <label htmlFor="email">Email address</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@example.com"
          required
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="At least 8 characters"
          minLength={isRegistering ? 8 : 1}
          required
        />

        {error && <p className="auth-error">{error}</p>}

        <button type="submit" disabled={loading}>
          {loading
            ? "Please wait..."
            : isRegistering
              ? "Create account"
              : "Log in"}
        </button>

        <p>
          {isRegistering
            ? "Already have an account?"
            : "New to EduPilot AI?"}{" "}
          <button
            type="button"
            className="auth-toggle"
            onClick={() => {
              setIsRegistering(!isRegistering);
              setError("");
            }}
          >
            {isRegistering ? "Log in" : "Create account"}
          </button>
        </p>
      </form>
    </div>
  );
}
