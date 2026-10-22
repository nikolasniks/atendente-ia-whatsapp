"""Conversa de demonstração no terminal, com o ERP de exemplo.

Usa o Claude de verdade no Amazon Bedrock (precisa de credenciais AWS e
gera custo por mensagem). Os dados da loja são todos fictícios.

    uv run python -m atendente_ia.demo --telefone 11999991111
"""

import argparse

from . import agente
from .config import carregar
from .erp_exemplo import ErpExemplo
from .ferramentas import Atendimento, identificar_cliente


def main() -> None:
    parser = argparse.ArgumentParser(description="Converse com o atendente usando dados de exemplo.")
    parser.add_argument(
        "--telefone",
        default="11999991111",
        help="WhatsApp de quem fala. 11999991111 = Ana Souza; outro número = não cadastrado.",
    )
    args = parser.parse_args()

    cfg = carregar()
    erp = ErpExemplo()
    atendimento = Atendimento(erp, identificar_cliente(erp, args.telefone))
    claude = agente.criar_cliente(cfg)
    quem = atendimento.cliente["nome"] if atendimento.cliente else "número não cadastrado"
    print(f"Demonstração ({quem}). Linha vazia para sair.\n")

    historico: list[dict] = []
    while mensagem := input("Você: ").strip():
        resposta = agente.responder(claude, cfg, atendimento, historico, mensagem)
        historico = resposta.historico
        print(f"\nAtendente: {resposta.texto}\n")
        if resposta.atendente_solicitado:
            print(f"[atendente humano chamado: {resposta.atendente_solicitado}]\n")
            atendimento.atendente_solicitado = None


if __name__ == "__main__":
    main()
