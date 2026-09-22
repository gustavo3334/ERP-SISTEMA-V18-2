from pathlib import Path


def test_rh_category_filter_and_distinct_badges_are_present():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert 'id="rhEmployeeCategory"' in html
    assert "Todos os vínculos" in html
    assert "Registrado" in html
    assert "Sem registro" in html
    assert "MEI" in html
    assert ".rh-reg-alert.unregistered" in html
    assert ".rh-reg-alert.mei" in html
    assert "e.employmentCategory===category" in html


def test_client_price_table_and_payment_options_are_integrated():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert "Tabela de preços do cliente" in html
    assert 'name="paymentMethods"' in html
    assert "Cartão de crédito" in html
    assert "Cartão de débito" in html
    assert "fpCollectClientPriceTable" in html
    assert "fpResolveClientProductPrice" in html
    assert "Preço da tabela do cliente quando cadastrado" in html
    assert "/api/v1/client-management/sync/front" in html
    assert "/api/v1/client-management/front/state" in html
    assert "R$ 3.011,00" not in html
