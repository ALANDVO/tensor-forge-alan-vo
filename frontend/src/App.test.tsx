import { render, screen, cleanup, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, afterEach } from "vitest";
import App from "./App";

const mockForgeResponse = {
  program_name: "myapp",
  language: "python",
  error: null,
  commands: [
    {
      name: "greet",
      kind: "function",
      docstring: "Greet a person by name.",
      location: "line 1",
      rendered: "myapp greet <NAME> [--times <VALUE>] [--verbose]",
      arguments: [
        { name: "name", py_type: "str", cli_type: "string", required: true, default: null, help: "Greet a person." },
        { name: "times", py_type: "int", cli_type: "integer", required: false, default: "1", help: "" },
        { name: "verbose", py_type: "bool", cli_type: "boolean", required: false, default: "False", help: "" },
      ],
    },
  ],
};

function stubFetch(response: unknown) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => response }));
}

afterEach(() => { vi.restoreAllMocks(); cleanup(); });

describe("tensor-forge dashboard", () => {
  it("renders the forge form", () => {
    render(<App />);
    expect(screen.getByLabelText(/program name/i)).toBeTruthy();
    expect(screen.getByText(/python source/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /forge cli/i })).toBeTruthy();
  });

  it("forges commands from pasted source and displays them", async () => {
    const user = userEvent.setup();
    stubFetch(mockForgeResponse);
    render(<App />);
    await user.clear(screen.getByLabelText(/program name/i));
    await user.type(screen.getByLabelText(/program name/i), "myapp");
    await user.click(screen.getByRole("button", { name: /forge cli/i }));
    expect(await screen.findByText(/myapp greet/i)).toBeTruthy();
    const article = screen.getByRole("article");
    expect(within(article).getByText(/greet a person by name/i)).toBeTruthy();
  });

  it("offers JSON export of the forge result", async () => {
    const user = userEvent.setup();
    stubFetch(mockForgeResponse);
    render(<App />);
    await user.click(screen.getByRole("button", { name: /forge cli/i }));
    await screen.findByText(/myapp greet/i);
    expect(screen.getByRole("button", { name: /export json/i })).toBeTruthy();
  });
});