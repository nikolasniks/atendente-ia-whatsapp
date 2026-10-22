from atendente_ia import telefone


def test_formatos_do_whatsapp_e_do_cadastro_batem():
    assert telefone.normalizar("+55 (11) 99999-1111") == "11999991111"
    assert telefone.normalizar("5511999991111") == "11999991111"
    assert telefone.iguais("whatsapp:+5511999991111", "(11) 99999-1111")


def test_celular_antigo_sem_nono_digito():
    assert telefone.iguais("1199991111", "11999991111")


def test_fixo_nao_ganha_nove():
    assert telefone.normalizar("(11) 3333-4444") == "1133334444"


def test_vazio_nunca_e_igual():
    assert not telefone.iguais("", "")
    assert not telefone.iguais(None, "11999991111")
