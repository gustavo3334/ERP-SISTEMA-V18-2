from pathlib import Path


def front_html() -> str:
    return (Path(__file__).resolve().parents[1] / "frontend" / "index.html").read_text(encoding="utf-8")


def test_target_panels_do_not_contain_demo_business_values():
    html = front_html()
    forbidden = [
        "R$ 612,40", "R$ 138,00", "R$ 92,30", "R$ 842,70", "R$ 1.490,00", "43,4%",
        "<td>Gustavo</td><td>42", "<td>Ahmad</td><td>38",
        "<strong>ADLA CAMPOS</strong>", "R$ 4.980</strong>", "R$ 1.500</strong>",
        "R$ 3.480</strong>", "22/06/2026</strong>",
        "<span>(-) Impostos</span><strong>R$ 34.800</strong>",
        "<span>(-) Custos variáveis</span><strong>R$ 141.630</strong>",
        "<span>(-) Despesas fixas</span><strong>R$ 98.200</strong>",
        "<span>Resultado operacional</span><strong style=\"color:var(--success)\">R$ 138.270</strong>",
    ]
    for value in forbidden:
        assert value not in html


def test_target_panels_have_backend_integration_ids():
    html = front_html()
    required_ids = [
        'id="salesCommissionsTable"', 'id="salesSummaryClient"', 'id="salesSummaryTotal"',
        'id="bomMaterialCost"', 'id="bomTotalCost"', 'id="bomSalePrice"',
        'id="dreGrossRevenue"', 'id="dreTaxes"', 'id="dreOperatingResult"',
    ]
    for value in required_ids:
        assert value in html
