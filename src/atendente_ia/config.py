"""Configurações do bot, lidas de variáveis de ambiente (definidas na Lambda)."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # Região AWS onde tudo roda.
    aws_region: str = "us-east-2"
    # Claude Sonnet 5 no Amazon Bedrock (IDs do Bedrock levam o prefixo "anthropic.").
    modelo: str = "anthropic.claude-sonnet-5"
    # Esforço de raciocínio: low | medium | high | xhigh | max
    esforco: str = "high"
    max_tokens: int = 16000
    # Limite de voltas IA -> ferramenta -> IA numa mesma mensagem do cliente.
    max_voltas_ferramentas: int = 8
    # Nome da empresa usado nas instruções do atendente.
    empresa: str = "Marcenaria Exemplo"
    # Endereço base da API do ERP e nome do segredo (Secrets Manager) com o token.
    erp_base_url: str = ""
    erp_segredo: str = "atendente-ia/erp-token"


def carregar() -> Config:
    padrao = Config()
    return Config(
        aws_region=os.environ.get("AWS_REGION", padrao.aws_region),
        modelo=os.environ.get("BOT_MODELO", padrao.modelo),
        esforco=os.environ.get("BOT_ESFORCO", padrao.esforco),
        max_tokens=int(os.environ.get("BOT_MAX_TOKENS", padrao.max_tokens)),
        max_voltas_ferramentas=int(
            os.environ.get("BOT_MAX_VOLTAS", padrao.max_voltas_ferramentas)
        ),
        empresa=os.environ.get("BOT_EMPRESA", padrao.empresa),
        erp_base_url=os.environ.get("ERP_BASE_URL", padrao.erp_base_url),
        erp_segredo=os.environ.get("ERP_SEGREDO", padrao.erp_segredo),
    )
