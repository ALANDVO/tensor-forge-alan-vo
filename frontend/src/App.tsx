import { useState } from "react";
import type { ForgeRequest, ForgeResponse } from "./api";
import { forgeSource } from "./api";
import { ForgeForm } from "./components/ForgeForm";
import { ForgeResult } from "./components/ForgeResult";
import "./index.css";
export default function App() {
  const [result, setResult] = useState<ForgeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (req: ForgeRequest) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await forgeSource(req);
      setResult(res);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "request failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <header>
        <h1>tensor-forge</h1>
        <p className="tagline">Forge agent-native CLI commands from source code.</p>
      </header>
      <main>
        <section>
          <h2>Forge CLI</h2>
          <ForgeForm onSubmit={handleSubmit} loading={loading} />
          {error && <div className="error" role="alert">{error}</div>}
        </section>
        {result && <ForgeResult result={result} />}
      </main>
      <footer>
        <small>
          Deterministic offline analysis &middot; LLM advisory is a planned milestone
          &middot; Alan Vo | AI &amp; Machine Learning
        </small>
      </footer>
    </div>
  );
}