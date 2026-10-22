from atendente_ia.agente import RESPOSTA_FALHA, responder
from atendente_ia.config import Config
from atendente_ia.erp_exemplo import ErpExemplo
from atendente_ia.ferramentas import Atendimento, identificar_cliente
from falsos import ClaudeFalso, mensagem, texto, uso_ferramenta

CFG = Config()


def _atendimento():
    erp = ErpExemplo()
    return Atendimento(erp, identificar_cliente(erp, "5511999991111"))


def test_usa_sonnet_5_com_esforco_alto():
    claude = ClaudeFalso([mensagem("end_turn", texto("Olá!"))])
    responder(claude, CFG, _atendimento(), [], "oi")
    chamada = claude.chamadas[0]
    assert chamada["model"] == "anthropic.claude-sonnet-5"
    assert chamada["output_config"] == {"effort": "high"}
    assert "Marcenaria Exemplo" in chamada["system"]


def test_executa_ferramenta_e_devolve_resposta_final():
    claude = ClaudeFalso([
        mensagem("tool_use", uso_ferramenta("t1", "consultar_pedidos", {"somente_em_andamento": True})),
        mensagem("end_turn", texto("Seu pedido 501 está em produção.")),
    ])
    resposta = responder(claude, CFG, _atendimento(), [], "cadê meu pedido?")

    assert resposta.texto == "Seu pedido 501 está em produção."
    resultado = claude.chamadas[1]["messages"][-1]["content"][0]
    assert resultado["tool_use_id"] == "t1" and "501" in resultado["content"]
    # Histórico: usuário, assistente (tool_use), resultados, assistente (texto)
    assert [m["role"] for m in resposta.historico] == ["user", "assistant", "user", "assistant"]


def test_recusa_vira_atendimento_humano_sem_sujar_historico():
    claude = ClaudeFalso([mensagem("refusal")])
    resposta = responder(claude, CFG, _atendimento(), [], "xyz")
    assert resposta.texto == RESPOSTA_FALHA
    assert resposta.atendente_solicitado
    assert resposta.historico == []


def test_limite_de_voltas_chama_atendente():
    voltas = [
        mensagem("tool_use", uso_ferramenta(f"t{i}", "buscar_produtos", {"termo": "caixa"}))
        for i in range(CFG.max_voltas_ferramentas)
    ]
    resposta = responder(ClaudeFalso(voltas), CFG, _atendimento(), [], "caixa")
    assert resposta.texto == RESPOSTA_FALHA
    assert resposta.atendente_solicitado
