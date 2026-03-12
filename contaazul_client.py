"""Conta Azul API Client.

Handles OAuth 2.0 authentication and provides typed access to API endpoints.
Base URL: https://api-v2.contaazul.com
Auth URL: https://auth.contaazul.com/oauth2/token
"""

import base64
import json
import os
from datetime import datetime, timedelta, timezone

import requests


class ContaAzulAuth:
    """Manages OAuth 2.0 token lifecycle for Conta Azul API.

    Proactively refreshes the access token before it expires (with a 5-minute
    buffer), and also handles reactive refresh on 401 responses.
    """

    TOKEN_URL = "https://auth.contaazul.com/oauth2/token"
    REFRESH_BUFFER = timedelta(minutes=5)

    def __init__(self, client_id: str, client_secret: str,
                 access_token: str = "", refresh_token: str = ""):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._basic_auth = base64.b64encode(
            f"{client_id}:{client_secret}".encode()
        ).decode()
        self._token_expiry = self._parse_expiry(access_token)

    @staticmethod
    def _parse_expiry(token: str) -> datetime | None:
        """Extract expiry time from a JWT access token."""
        if not token:
            return None
        try:
            payload_b64 = token.split(".")[1]
            # Add padding for base64
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.b64decode(payload_b64))
            return datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        except (IndexError, KeyError, ValueError):
            return None

    def is_token_expired(self) -> bool:
        """Check if the access token is expired or about to expire."""
        if not self._token_expiry:
            return True
        return datetime.now(timezone.utc) >= (self._token_expiry - self.REFRESH_BUFFER)

    def ensure_valid_token(self) -> None:
        """Refresh the token proactively if it's expired or about to expire."""
        if self.is_token_expired() and self.refresh_token:
            self.refresh()

    def refresh(self) -> str:
        """Exchange refresh_token for a new access_token."""
        if not self.refresh_token:
            raise ValueError(
                "No refresh_token available. Run the OAuth authorization flow first."
            )
        resp = requests.post(
            self.TOKEN_URL,
            headers={
                "Authorization": f"Basic {self._basic_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self._token_expiry = self._parse_expiry(self.access_token)
        if "refresh_token" in data:
            self.refresh_token = data["refresh_token"]
        return self.access_token

    def get_auth_header(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}


class ContaAzulClient:
    """HTTP client for Conta Azul API v2."""

    BASE_URL = "https://api-v2.contaazul.com"

    def __init__(self, auth: ContaAzulAuth):
        self.auth = auth
        self.session = requests.Session()
        self.session.headers.update(auth.get_auth_header())

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make an authenticated request with proactive + reactive token refresh."""
        # Proactive: refresh before expiry (avoids wasting a round-trip)
        self.auth.ensure_valid_token()
        self.session.headers.update(self.auth.get_auth_header())

        url = f"{self.BASE_URL}{path}"
        resp = self.session.request(method, url, **kwargs)

        # Reactive: handle unexpected 401 (e.g. token revoked server-side)
        if resp.status_code == 401 and self.auth.refresh_token:
            self.auth.refresh()
            self.session.headers.update(self.auth.get_auth_header())
            resp = self.session.request(method, url, **kwargs)

        resp.raise_for_status()
        return resp

    def get(self, path: str, params: dict = None) -> requests.Response:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict = None) -> requests.Response:
        return self._request("POST", path, json=json)

    def put(self, path: str, json: dict = None) -> requests.Response:
        return self._request("PUT", path, json=json)

    def delete(self, path: str, params: dict = None) -> requests.Response:
        return self._request("DELETE", path, params=params)

    # --- Invoice endpoints (Notas Fiscais) ---

    def list_invoices(self, data_inicial: str, data_final: str,
                      pagina: int = 1, tamanho_pagina: int = 10,
                      **filters) -> dict:
        """List product invoices (NFe) by date range.

        Args:
            data_inicial: Start date YYYY-MM-DD
            data_final: End date YYYY-MM-DD
            pagina: Page number (default 1)
            tamanho_pagina: Page size (10, 20, 50, or 100)
            **filters: Optional - documento_tomador, numero_nota, id_venda
        """
        params = {
            "data_inicial": data_inicial,
            "data_final": data_final,
            "pagina": pagina,
            "tamanho_pagina": tamanho_pagina,
            **filters,
        }
        return self.get("/v1/notas-fiscais", params=params).json()

    def list_service_invoices(self, data_competencia_de: str,
                              data_competencia_ate: str,
                              pagina: int = 1, tamanho_pagina: int = 10,
                              **filters) -> dict:
        """List service invoices (NFS-e) by date range (max 15 days).

        Args:
            data_competencia_de: Start date YYYY-MM-DD
            data_competencia_ate: End date YYYY-MM-DD (max 15 days from start)
            pagina: Page number (default 1)
            tamanho_pagina: Page size (10, 20, 50, or 100)
            **filters: Optional - ids, id_cliente, numero_venda, status, etc.
        """
        params = {
            "data_competencia_de": data_competencia_de,
            "data_competencia_ate": data_competencia_ate,
            "pagina": pagina,
            "tamanho_pagina": tamanho_pagina,
            **filters,
        }
        return self.get("/v1/notas-fiscais-servico", params=params).json()

    def get_invoice_by_key(self, chave: str) -> str:
        """Get a specific invoice XML by its access key."""
        resp = self.get(f"/v1/notas-fiscais/{chave}")
        return resp.text

    def link_invoices_to_mdfe(self, identificador: str,
                               chaves_acesso: list[str],
                               status: str = None) -> None:
        """Associate invoices to an MDF-e manifest.

        Args:
            identificador: MDF-e identifier
            chaves_acesso: List of invoice access keys
            status: Optional - AUTORIZADO, ENCERRADO, or CANCELADO
        """
        body = {
            "identificador": identificador,
            "chaves_acesso": chaves_acesso,
        }
        if status:
            body["status"] = status
        self.post("/v1/notas-fiscais/vinculo-mdfe", json=body)

    # --- Financial endpoints (quick access) ---

    def list_categories(self) -> list:
        """List financial categories."""
        return self.get("/v1/categorias").json()

    def list_cost_centers(self) -> list:
        """List cost centers (centros de custo)."""
        return self.get("/v1/centro-de-custo").json()


def create_client_from_env() -> ContaAzulClient:
    """Create a ContaAzulClient from .env environment variables."""
    auth = ContaAzulAuth(
        client_id=os.environ["CONTAAZUL_CLIENT_ID"],
        client_secret=os.environ["CONTAAZUL_CLIENT_SECRET"],
        access_token=os.environ.get("CONTAAZUL_ACCESS_TOKEN", ""),
        refresh_token=os.environ.get("CONTAAZUL_REFRESH_TOKEN", ""),
    )
    return ContaAzulClient(auth)
