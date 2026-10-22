"""Acesso ao ERP.

O bot só depende da interface `Erp` (listar, consultar, cadastrar). Para ligar
a outro sistema, basta escrever um adaptador com esses três métodos.
`ErpHttp` é um adaptador REST genérico: ajuste caminhos e autenticação
conforme a documentação da API do seu ERP.
"""

from typing import Any, Protocol

import httpx


class Erp(Protocol):
    def listar(self, recurso: str, params: dict[str, Any] | None = None) -> list[dict]: ...

    def consultar(self, recurso: str, id_: str) -> dict: ...

    def cadastrar(
        self, recurso: str, dados: dict[str, Any], documento_id: str | None = None
    ) -> dict: ...


class ErroErp(Exception):
    """Falha ao falar com o ERP (rede, autenticação ou resposta inesperada)."""


class ErpHttp:
    """Adaptador REST genérico."""

    def __init__(self, base_url: str, token: str, timeout: float = 15.0):
        if not base_url:
            raise ValueError("ERP_BASE_URL não configurado")
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )

    def _caminho(self, recurso: str, documento_id: str | None = None) -> str:
        if recurso == "itens_orcamento":
            return f"/orcamentos/{documento_id}/itens"
        return f"/{recurso}"

    def _req(self, metodo: str, caminho: str, **kwargs: Any) -> Any:
        try:
            resposta = self._http.request(metodo, caminho, **kwargs)
            resposta.raise_for_status()
        except httpx.HTTPError as erro:
            raise ErroErp(f"{metodo} {caminho}: {erro}") from erro
        return resposta.json() if resposta.content else {}

    def listar(self, recurso: str, params: dict[str, Any] | None = None) -> list[dict]:
        corpo = self._req("GET", self._caminho(recurso), params=params or {})
        if isinstance(corpo, dict):
            return corpo.get("items") or corpo.get("data") or []
        return corpo

    def consultar(self, recurso: str, id_: str) -> dict:
        return self._req("GET", f"{self._caminho(recurso)}/{id_}")

    def cadastrar(
        self, recurso: str, dados: dict[str, Any], documento_id: str | None = None
    ) -> dict:
        return self._req("POST", self._caminho(recurso, documento_id), json=dados)
