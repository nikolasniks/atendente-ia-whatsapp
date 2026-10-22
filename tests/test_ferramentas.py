import json

from atendente_ia.erp_exemplo import ErpExemplo
from atendente_ia.ferramentas import Atendimento, identificar_cliente


def _atendimento(numero="5511999991111"):
    erp = ErpExemplo()
    return Atendimento(erp, identificar_cliente(erp, numero)), erp


def _rodar(atendimento, nome, entrada):
    conteudo, erro = atendimento.executar(nome, entrada)
    return json.loads(conteudo), erro


def test_identifica_por_fone1_e_fone2():
    erp = ErpExemplo()
    assert identificar_cliente(erp, "+55 11 99999-1111")["id"] == "c1"
    assert identificar_cliente(erp, "1133334444")["id"] == "c2"
    assert identificar_cliente(erp, "21 91234-5678") is None


def test_pedidos_so_do_proprio_cliente():
    atendimento, _ = _atendimento()
    resultado, erro = _rodar(atendimento, "consultar_pedidos", {"somente_em_andamento": False})
    assert not erro
    assert [p["numero"] for p in resultado["pedidos"]] == [501, 502]


def test_pedidos_em_andamento_escondem_entregues():
    atendimento, _ = _atendimento()
    resultado, _ = _rodar(atendimento, "consultar_pedidos", {"somente_em_andamento": True})
    assert [p["numero"] for p in resultado["pedidos"]] == [501]


def test_contas_so_em_aberto_e_do_proprio_cliente():
    atendimento, _ = _atendimento()
    resultado, _ = _rodar(atendimento, "contas_em_aberto", {})
    assert [c["valor"] for c in resultado["contas"]] == [50.0]


def test_desconhecido_nao_tem_ferramentas_de_dados_pessoais():
    atendimento, _ = _atendimento("21 91234-5678")
    nomes = {d["name"] for d in atendimento.definicoes()}
    assert nomes == {"buscar_produtos", "chamar_atendente"}
    resultado, erro = _rodar(atendimento, "consultar_pedidos", {"somente_em_andamento": False})
    assert erro and "indisponível" in resultado["erro"]


def test_orcamento_usa_preco_de_tabela_e_cliente_da_conversa():
    atendimento, erp = _atendimento()
    resultado, erro = _rodar(
        atendimento,
        "criar_orcamento",
        {"itens": [{"produto_id": "p1", "quantidade": 4}, {"produto_id": "p2", "quantidade": 1}], "observacoes": "cor natural"},
    )
    assert not erro
    assert resultado["total_estimado"] == 75.0
    cabecalho, *itens = erp.cadastros
    assert cabecalho[0] == "orcamentos" and cabecalho[1]["clienteId"] == "c1"
    assert [i[1]["valorUnit"] for i in itens] == [12.5, 25.0]


def test_orcamento_rejeita_quantidade_invalida():
    atendimento, erp = _atendimento()
    resultado, erro = _rodar(atendimento, "criar_orcamento", {"itens": [{"produto_id": "p1", "quantidade": 0}], "observacoes": ""})
    assert erro
    assert erp.cadastros == []


def test_chamar_atendente_marca_conversa():
    atendimento, _ = _atendimento()
    _rodar(atendimento, "chamar_atendente", {"motivo": "quer negociar prazo"})
    assert atendimento.atendente_solicitado == "quer negociar prazo"
