from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_hotfix_is_loaded_last_and_calls_authoritative_endpoint():
    html=(ROOT/'frontend'/'index.html').read_text(encoding='utf-8')
    assert html.count('stock-locations-hotfix.js?v=18.2.0') == 1
    assert html.rfind('stock-locations-hotfix.js?v=18.2.0') > html.rfind('fpSeniorRelationalDeleteGuard')
    js=(ROOT/'frontend'/'stock-locations-hotfix.js').read_text(encoding='utf-8')
    assert "fetch('/api/v1/stock-locations'" not in js  # helper wraps fetch centrally
    assert "request('/api/v1/stock-locations')" in js
    assert 'MutationObserver' in js
    assert 'Carregando locais...' in js
    assert 'Estoque Principal' in js

def test_hotfix_is_mirrored_to_public():
    assert (ROOT/'frontend'/'stock-locations-hotfix.js').read_text(encoding='utf-8') == (ROOT/'public'/'stock-locations-hotfix.js').read_text(encoding='utf-8')
