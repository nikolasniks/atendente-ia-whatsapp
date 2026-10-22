"""Ferramentas que o Claude pode usar durante o atendimento.

Regra de segurança: o cliente é identificado pelo número do WhatsApp ANTES da
conversa, e toda ferramenta filtra pelos dados desse cliente aqui no código.
A IA nunca escolhe de qual cliente são os dados, então não há como pedir
(ou enganar o bot para mostrar) pedidos ou contas de outra pessoa.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from . import telefone
from .erp import Erp, ErroErp

log = logging.getLogger(__name__)

SITUACOES_EM_ABERTO = {"VENCIDA", "NAO_RECEBIDA"}
MAX_PRODUTOS = 10
MAX_PEDIDOS = 10


def identificar_cliente(erp: Erp, numero_whatsapp: str) -> dict | None:
    """Procura o cliente cujo fone1 ou fone2 bate com o número do WhatsApp."""
    alvo = telefone.normalizar(numero_whatsapp)
    if not alvo:
        return None
    for resumo in erp.listar("clientes"):
        if telefone.iguais(resumo.get("fone1"), alvo):
            return erp.consultar("clientes", resumo["id"])
    # A listagem não traz fone2; um cliente cadastrado só com fone2
    # precisa ser consultado um a um. Se a API do ERP tiver filtro por
    # telefone, use-o aqui para não varrer todos os clientes.
    for resumo in erp.listar("clientes"):
        completo = erp.consultar("clientes", resumo["id"])
        if telefone.iguais(completo.get("fone2"), alvo):
            return completo
    return None


def _ferramenta(nome: str, descricao: str, propriedades: dict, obrigatorias: list[str]) -> dict:
    return {
        "name": nome,
        "description": descricao,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": propriedades,
            "required": obrigatorias,
            "additionalProperties": False,
        },
    }


BUSCAR_PRODUTOS = _ferramenta(
    "buscar_produtos",
    "Procura produtos no catálogo da loja pelo nome ou código e devolve "
    "código, nome, unidade e preço de tabela. Use antes de informar qualquer preço.",
    {"termo": {"type": "string", "description": "Nome, parte do nome ou código do produto."}},
    ["termo"],
)
CONSULTAR_PEDIDOS = _ferramenta(
    "consultar_pedidos",
    "Lista os pedidos mais recentes do cliente desta conversa, com status, "
    "data de entrega e valor.",
    {
        "somente_em_andamento": {
            "type": "boolean",
            "description": "true para esconder pedidos já entregues ou cancelados.",
        }
    },
    ["somente_em_andamento"],
)
CRIAR_ORCAMENTO = _ferramenta(
    "criar_orcamento",
    "Registra no ERP um orçamento para o cliente desta conversa, com preços de "
    "tabela. Não é um pedido: um vendedor revisa e confirma depois. Só use quando o "
    "cliente pedir e depois de confirmar com ele os produtos e as quantidades.",
    {
        "itens": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "produto_id": {"type": "string", "description": "id devolvido por buscar_produtos."},
                    "quantidade": {"type": "number"},
                },
                "required": ["produto_id", "quantidade"],
                "additionalProperties": False,
            },
        },
        "observacoes": {
            "type": "string",
            "description": "Detalhes que o cliente pediu (medidas, cores, prazo). Vazio se não houver.",
        },
    },
    ["itens", "observacoes"],
)
CONTAS_EM_ABERTO = _ferramenta(
    "contas_em_aberto",
    "Lista as contas a pagar do cliente desta conversa que ainda não foram pagas "
    "(vencidas ou a vencer), com valor e vencimento.",
    {},
    [],
)
CHAMAR_ATENDENTE = _ferramenta(
    "chamar_atendente",
    "Passa a conversa para um atendente humano. Use quando o cliente pedir, quando "
    "não houver ferramenta para o pedido dele, ou em reclamações e negociações.",
    {"motivo": {"type": "string", "description": "Resumo curto do que o cliente precisa."}},
    ["motivo"],
)


@dataclass
class Atendimento:
    """Ferramentas de uma conversa, presas ao cliente identificado (ou a nenhum)."""

    erp: Erp
    cliente: dict | None
    atendente_solicitado: str | None = field(default=None, init=False)

    def definicoes(self) -> list[dict]:
        """Ferramentas oferecidas ao Claude. Sem cliente identificado, nada de dados pessoais."""
        if self.cliente is None:
            return [BUSCAR_PRODUTOS, CHAMAR_ATENDENTE]
        return [BUSCAR_PRODUTOS, CONSULTAR_PEDIDOS, CRIAR_ORCAMENTO, CONTAS_EM_ABERTO, CHAMAR_ATENDENTE]

    def executar(self, nome: str, entrada: dict[str, Any]) -> tuple[str, bool]:
        """Roda uma ferramenta. Devolve (conteúdo em JSON, houve_erro)."""
        permitidas = {d["name"] for d in self.definicoes()}
        if nome not in permitidas:
            return json.dumps({"erro": f"Ferramenta '{nome}' indisponível nesta conversa."}), True
        try:
            resultado = getattr(self, f"_{nome}")(**entrada)
        except ErroErp:
            log.exception("Falha no ERP ao executar %s", nome)
            return json.dumps({"erro": "Sistema indisponível no momento. Tente de novo mais tarde."}), True
        except (TypeError, ValueError) as erro:
            return json.dumps({"erro": str(erro)}, ensure_ascii=False), True
        return json.dumps(resultado, ensure_ascii=False, default=str), False

    # --- implementações ---

    def _buscar_produtos(self, termo: str) -> dict:
        encontrados = self.erp.listar("produtos", {"search": termo})[:MAX_PRODUTOS]
        return {
            "produtos": [
                {
                    "id": p.get("id"),
                    "codigo": p.get("codigo"),
                    "nome": p.get("nome"),
                    "unidade": p.get("unidade"),
                    "preco_tabela": p.get("preco"),
                }
                for p in encontrados
            ]
        }

    def _consultar_pedidos(self, somente_em_andamento: bool) -> dict:
        meus = [p for p in self.erp.listar("pedidos") if p.get("clienteId") == self.cliente["id"]]
        if somente_em_andamento:
            encerrados = ("entregue", "cancelad", "finalizad")
            meus = [
                p for p in meus
                if not any(s in (p.get("statusTitulo") or "").lower() for s in encerrados)
            ]
        meus.sort(key=lambda p: p.get("data") or "", reverse=True)
        return {
            "pedidos": [
                {
                    "numero": p.get("idInt"),
                    "data": p.get("data"),
                    "status": p.get("statusTitulo"),
                    "data_entrega": p.get("dataEntrega"),
                    "entrega_a_combinar": p.get("entregaACombinar"),
                    "valor_total": p.get("valorTotal"),
                    "itens": [
                        {"nome": i.get("nome"), "quantidade": i.get("quantidade"), "status": i.get("statusTitulo")}
                        for i in p.get("itens") or []
                    ],
                }
                for p in meus[:MAX_PEDIDOS]
            ]
        }

    def _criar_orcamento(self, itens: list[dict], observacoes: str) -> dict:
        if not itens:
            raise ValueError("O orçamento precisa de pelo menos um item.")
        linhas = []
        for item in itens:
            if item["quantidade"] <= 0:
                raise ValueError("Quantidade deve ser maior que zero.")
            produto = self.erp.consultar("produtos", item["produto_id"])
            linhas.append((produto, item["quantidade"]))

        orcamento = self.erp.cadastrar(
            "orcamentos",
            {
                "clienteId": self.cliente["id"],
                "data": date.today().isoformat(),
                "observacoes": ("[Bot WhatsApp] " + observacoes).strip(),
            },
        )
        total = 0.0
        for produto, quantidade in linhas:
            # Preço sempre o de tabela; acréscimos e descontos ficam com o vendedor.
            preco = produto.get("preco") or 0.0
            self.erp.cadastrar(
                "itens_orcamento",
                {"produtoId": produto["id"], "quantidade": quantidade, "valorUnit": preco},
                documento_id=orcamento["id"],
            )
            total += preco * quantidade
        return {
            "orcamento_numero": orcamento.get("idInt"),
            "total_estimado": round(total, 2),
            "aviso": "Valores de tabela. Um vendedor vai revisar e confirmar com o cliente.",
        }

    def _contas_em_aberto(self) -> dict:
        abertas = [
            c for c in self.erp.listar("contas_receber")
            if c.get("personId") == self.cliente["id"]
            and not c.get("liquidado")
            and c.get("situacao") in SITUACOES_EM_ABERTO
        ]
        abertas.sort(key=lambda c: c.get("dataVencimento") or "")
        return {
            "contas": [
                {
                    "descricao": c.get("descricao"),
                    "parcela": c.get("parcela"),
                    "valor": c.get("valorConta"),
                    "vencimento": c.get("dataVencimento"),
                    "situacao": c.get("situacao"),
                }
                for c in abertas
            ]
        }

    def _chamar_atendente(self, motivo: str) -> dict:
        self.atendente_solicitado = motivo
        return {"ok": True, "mensagem": "Atendente avisado. Diga ao cliente que alguém vai responder em breve."}
