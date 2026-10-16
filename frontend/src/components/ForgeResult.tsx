import { useState } from "react";
import type { ForgeResponse } from "../api";

interface Props {
  result: ForgeResponse;
}

function copyToClipboard(text: string) {
  void navigator.clipboard.writeText(text);
}

export function ForgeResult({ result }: Props) {
  const [copied, setCopied] = useState(false);

  const downloadJson = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.program_name}-commands.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!result.commands.length) {
    return (
      <section className="result">
        <h2>Result</h2>
        <p>No CLI entry points were found in the source.</p>
      </section>
    );
  }

  return (
    <section className="result">
      <h2>Result — {result.program_name}</h2>
      <div className="export-bar">
        <button onClick={downloadJson} type="button">Export JSON</button>
      </div>
      <div className="commands">
        {result.commands.map((cmd) => (
          <article key={cmd.name} className="command">
            <div className="command-header">
              <code className="rendered">{cmd.rendered}</code>
              <button
                type="button"
                onClick={() => { copyToClipboard(cmd.rendered); setCopied(true); }}
                title="Copy command"
              >{copied ? "Copied" : "Copy"}</button>
            </div>
            <p className="docstring">{cmd.docstring || <em>(no description)</em>}</p>
            {cmd.arguments.length > 0 && (
              <table className="args">
                <thead>
                  <tr><th>Argument</th><th>Type</th><th>Required</th><th>Default</th><th>Help</th></tr>
                </thead>
                <tbody>
                  {cmd.arguments.map((a) => (
                    <tr key={a.name}>
                      <td><code>{a.name}</code></td>
                      <td>{a.cli_type}</td>
                      <td>{a.required ? "yes" : "no"}</td>
                      <td>{a.default ?? "—"}</td>
                      <td>{a.help || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}