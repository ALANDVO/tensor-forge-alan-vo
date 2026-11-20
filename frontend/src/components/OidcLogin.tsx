import { useState, useEffect } from "react";
import { ForgeError } from "./api";

interface Props {
  onLoginSuccess: (token: string) => void;
  onError: (msg: string) => void;
}

const KEYCLOAK_URL = "https://auth.example.com/realms/tensor-forge";
const CLIENT_ID = "tensor-forge-client";
const REDIRECT_URI = "http://127.0.0.1:8000/api/oidc/callback";

function b64encode(str: string): string {
  // Standard base64url encode without padding
  return btoa(str).replace(/+/g, "-").replace(/=/g, "").replace(/_/g, ".");
}

export function OidcLogin({ onLoginSuccess, onError }: Props) {
  const [loading, setLoading] = useState(false);
  const [state, setState] = useState<string | null>(null);

  useEffect(() => {
    // Check if we're returning from Keycloak callback with a token
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (token) {
      onLoginSuccess(token);
      // Clear token from URL
      const newUrl = window.location.origin + window.location.pathname;
      history.pushState(null, "", newUrl);
      return;
    }
  }, [onLoginSuccess]);

  const handleLogin = async () => {
    setLoading(true);
    try {
      // Generate PKCE pair
      const verifier = crypto.randomUUID() + crypto.randomUUID() + crypto.randomUUID();
      const encoder = new TextEncoder();
      const data = encoder.encode(verifier);
      const hash = await crypto.subtle.digest("SHA-256", data);
      const challenge = b64encode(
        String.fromCharCode(...new Uint8Array(hash))
      );

      // Generate random state
      const state = b64encode(crypto.getRandomValues(new Uint16Array(8))
        .reduce((acc, val) => acc + String.fromCharCode(val % 65 + 65), ""));

      setState(state);

      const params = new URLSearchParams({
        response_type: "code",
        client_id: CLIENT_ID,
        redirect_uri: REDIRECT_URI,
        scope: "openid profile email",
        state,
        code_challenge: challenge,
        code_challenge_method: "S256",
        prompt: "login",
      });

      const authUrl = `${KEYCLOAK_URL}/protocol/openid/authorize?${params}`;
      window.location.href = authUrl;
    } catch (e: any) {
      onError(e?.message ?? "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="oidc-login">
      {loading ? (
        <span>Logging in…</span>
      ) : (
        <button
          onClick={handleLogin}
          className="oidc-button"
          aria-label="Login with Keycloak OIDC"
        >
          🔑 Login with Keycloak
        </button>
      )}
    </div>
  );
}
