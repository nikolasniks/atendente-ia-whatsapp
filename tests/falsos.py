"""Claude falso para testar o agente sem rede e sem custo."""

import copy

from anthropic.types import Message


def mensagem(stop_reason, *blocos):
    return Message.model_validate(
        {
            "id": "msg_teste",
            "type": "message",
            "role": "assistant",
            "model": "anthropic.claude-sonnet-5",
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "content": list(blocos),
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
    )


def texto(t):
    return {"type": "text", "text": t}


def uso_ferramenta(id_, nome, entrada):
    return {"type": "tool_use", "id": id_, "name": nome, "input": entrada}


class ClaudeFalso:
    """Devolve respostas roteirizadas e guarda o que recebeu."""

    def __init__(self, respostas):
        self._respostas = list(respostas)
        self.chamadas: list[dict] = []
        self.messages = self

    def create(self, **kwargs):
        # Cópia: o agente continua alterando a lista de mensagens depois.
        self.chamadas.append(copy.deepcopy(kwargs))
        return self._respostas.pop(0)
