import { useState } from "react";
import type { ForgeRequest } from "../api";

interface Props {
  onSubmit: (req: ForgeRequest) => Promise<void>;
  loading: boolean;
}

const SAMPLE = `def greet(name: str, times: int = 1, verbose: bool = False) -> str:
    """Greet a person by name."""
    return f"hi {name}"
`;

export function ForgeForm({ onSubmit, loading }: Props) {
  const [source, setSource] = useState(SAMPLE);
  const [programName, setProgramName] = useState("myapp");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    void onSubmit({ source, program_name: programName, language: "python" });
  };

  return (
    <form className="forge-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="program-name">Program name</label>
        <input
          id="program-name"
          value={programName}
          onChange={(e) => setProgramName(e.target.value)}
          placeholder="myapp"
          disabled={loading}
          required
        />
      </div>
      <div className="field">
        <label htmlFor="source">Python source</label>
        <textarea
          id="source"
          value={source}
          onChange={(e) => setSource(e.target.value)}
          placeholder="Paste Python source code here"
          disabled={loading}
          required
          rows={10}
        />
      </div>
      <button type="submit" disabled={loading}>
        {loading ? "Forging…" : "Forge CLI"}
      </button>
    </form>
  );
}