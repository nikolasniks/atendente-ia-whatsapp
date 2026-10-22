"""ERP de exemplo, em memória, com dados fictícios.

Usado nos testes e na demonstração (`demo.py`). Nenhum dado aqui é real.
"""

import copy
import itertools

DADOS_EXEMPLO = {
    "clientes": [
        {"id": "c1", "idInt": 1, "nome": "Ana Souza", "fone1": "(11) 99999-1111", "fone2": ""},
        {"id": "c2", "idInt": 2, "nome": "Loja Ateliê Criativo", "fone1": "11 98888-2222", "fone2": "11 3333-4444"},
    ],
    # Preço em tabela por faixa de quantidade (o campo "preco" fica zerado, como em alguns ERPs).
    "produtos": [
        {"id": "p1", "idInt": 10, "codigo": "CX20", "nome": "Caixa MDF 20x14x8", "unidade": "un", "preco": 0,
         "gruposPrecosVenda": [{"idPriceGroup": None, "titulo": "Padrão",
                                "precosVenda": [{"de": 1, "valor": 12.5}, {"de": 50, "valor": 10.0}]}]},
        {"id": "p2", "idInt": 11, "codigo": None, "nome": "Bandeja MDF 30cm", "unidade": "un", "preco": 0,
         "gruposPrecosVenda": [{"idPriceGroup": None, "titulo": "Padrão", "precosVenda": [{"de": 1, "valor": 25.0}]}]},
        {"id": "p3", "idInt": 12, "codigo": "PL40", "nome": "Placa decorativa MDF 40x30", "unidade": "un", "preco": 0,
         "gruposPrecosVenda": [{"idPriceGroup": None, "titulo": "Padrão", "precosVenda": [{"de": 1, "valor": 18.9}]}]},
        {"id": "p4", "idInt": 13, "codigo": "SP", "nome": "Peça sem preço", "unidade": "un", "preco": 0,
         "gruposPrecosVenda": []},
    ],
    "pedidos": [
        {
            "id": "o1", "idInt": 501, "clienteId": "c1", "data": "2026-10-01",
            "statusTitulo": "Em produção", "dataEntrega": "2026-10-28", "valorTotal": 100.0,
            "itens": [{"nome": "Caixa MDF 20x14x8", "quantidade": 8, "statusTitulo": "Em produção"}],
        },
        {"id": "o2", "idInt": 502, "clienteId": "c1", "data": "2026-09-01", "statusTitulo": "Entregue", "valorTotal": 50.0, "itens": []},
        {"id": "o3", "idInt": 503, "clienteId": "c2", "data": "2026-10-05", "statusTitulo": "Em produção", "valorTotal": 999.0, "itens": []},
    ],
    "contas_receber": [
        {"id": "r1", "personId": "c1", "descricao": "Pedido 501", "parcela": "1/2", "valorConta": 50.0, "dataVencimento": "2026-10-30", "liquidado": False, "situacao": "NAO_RECEBIDA"},
        {"id": "r2", "personId": "c1", "descricao": "Pedido 400", "parcela": "1/1", "valorConta": 80.0, "dataVencimento": "2026-08-30", "liquidado": True, "situacao": "RECEBIDA"},
        {"id": "r3", "personId": "c2", "descricao": "Pedido 503", "parcela": "1/1", "valorConta": 700.0, "dataVencimento": "2026-10-10", "liquidado": False, "situacao": "VENCIDA"},
    ],
}


class ErpExemplo:
    def __init__(self, dados: dict | None = None):
        self.dados = copy.deepcopy(dados or DADOS_EXEMPLO)
        self.cadastros: list[tuple[str, dict, str | None]] = []
        self._ids = itertools.count(900)

    def listar(self, recurso, params=None):
        itens = self.dados.get(recurso, [])
        termo = (params or {}).get("search")
        if termo:
            itens = [i for i in itens if termo.lower() in ((i.get("nome") or "") + (i.get("codigo") or "")).lower()]
        if recurso == "clientes":
            # Como em muitos ERPs, a listagem não traz todos os campos (aqui, fone2).
            return [{k: v for k, v in i.items() if k != "fone2"} for i in itens]
        return list(itens)

    def consultar(self, recurso, id_):
        registro = next(i for i in self.dados[recurso] if i["id"] == id_)
        # Como em alguns ERPs, a consulta por id não traz a tabela de preços.
        return {k: v for k, v in registro.items() if k != "gruposPrecosVenda"}

    def cadastrar(self, recurso, dados, documento_id=None):
        self.cadastros.append((recurso, dados, documento_id))
        n = next(self._ids)
        return {"id": f"novo{n}", "idInt": n, **dados}
