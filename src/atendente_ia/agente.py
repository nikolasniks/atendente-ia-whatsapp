"""Laço de atendimento: envia a conversa ao Claude e executa as ferramentas pedidas."""

import logging
from dataclasses import dataclass

import anthropic

from . import prompt
from .config import Config
from .ferramentas import Atendimento

log = logging.getLogger(__name__)

RESPOSTA_FALHA = (
    "Desculpe, não consegui concluir seu atendimento agora. "
    "Já avisei nossa equipe e um atendente vai falar com você em breve."
)


@dataclass
class Resposta:
    texto: str
    historico: list[dict]
    atendente_solicitado: str | None


def criar_cliente(cfg: Config) -> anthropic.AnthropicBedrockMantle:
    # Usa as credenciais da AWS do ambiente (papel IAM da Lambda).
    return anthropic.AnthropicBedrockMantle(aws_region=cfg.aws_region)


def _blocos(conteudo) -> list[dict]:
    # Guarda os blocos exatamente como vieram (inclusive os de raciocínio),
    # para reenviar sem alteração na próxima mensagem.
    return [b.model_dump(mode="json", exclude_none=True) for b in conteudo]


def _texto(conteudo) -> str:
    return "\n".join(b.text for b in conteudo if b.type == "text").strip()


def responder(
    claude: anthropic.AnthropicBedrockMantle,
    cfg: Config,
    atendimento: Atendimento,
    historico: list[dict],
    mensagem: str,
) -> Resposta:
    mensagens = [*historico, {"role": "user", "content": mensagem}]
    sistema = prompt.montar(atendimento.cliente, cfg.empresa)

    for _ in range(cfg.max_voltas_ferramentas):
        resposta = claude.messages.create(
            model=cfg.modelo,
            max_tokens=cfg.max_tokens,
            system=sistema,
            tools=atendimento.definicoes(),
            thinking={"type": "adaptive"},
            output_config={"effort": cfg.esforco},
            messages=mensagens,
        )

        if resposta.stop_reason == "refusal":
            log.warning("Claude recusou a mensagem: %s", resposta.stop_details)
            atendimento.atendente_solicitado = "Mensagem recusada pelo filtro de segurança"
            return Resposta(RESPOSTA_FALHA, historico, atendimento.atendente_solicitado)

        mensagens.append({"role": "assistant", "content": _blocos(resposta.content)})

        if resposta.stop_reason == "tool_use":
            resultados = []
            for bloco in resposta.content:
                if bloco.type != "tool_use":
                    continue
                conteudo, erro = atendimento.executar(bloco.name, bloco.input)
                resultados.append(
                    {"type": "tool_result", "tool_use_id": bloco.id, "content": conteudo, "is_error": erro}
                )
            # Todos os resultados juntos numa única mensagem.
            mensagens.append({"role": "user", "content": resultados})
            continue

        texto = _texto(resposta.content)
        if resposta.stop_reason == "max_tokens" or not texto:
            log.warning("Resposta incompleta (stop_reason=%s)", resposta.stop_reason)
            atendimento.atendente_solicitado = atendimento.atendente_solicitado or "Resposta incompleta do bot"
            # Descarta a troca incompleta para não deixar o histórico quebrado.
            return Resposta(RESPOSTA_FALHA, historico, atendimento.atendente_solicitado)
        return Resposta(texto, mensagens, atendimento.atendente_solicitado)

    log.warning("Limite de %d voltas de ferramentas atingido", cfg.max_voltas_ferramentas)
    atendimento.atendente_solicitado = atendimento.atendente_solicitado or "Bot não concluiu o atendimento"
    return Resposta(RESPOSTA_FALHA, historico, atendimento.atendente_solicitado)
