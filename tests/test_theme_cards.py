from pathlib import Path

from styles import _css_para_tema


def test_mobility_cards_use_semantic_classes_instead_of_dark_inline_colors():
    app_source = Path("app.py").read_text(encoding="utf-8")
    mobility_block = app_source[
        app_source.index('<div class="mobility-heading">') :
        app_source.index('mostrar_seccion("Estadísticas vehiculares consolidadas")')
    ]

    assert "#141E29" not in mobility_block
    assert "#E8EEF3" not in mobility_block
    assert 'class="mobility-card mobility-card--blue"' in mobility_block
    assert 'class="mobility-card mobility-card--orange"' in mobility_block
    assert 'class="mobility-card mobility-card--green"' in mobility_block


def test_card_variables_change_between_light_and_dark_themes():
    light = _css_para_tema("Claro")
    dark = _css_para_tema("Oscuro")

    assert "--card-bg: #FFFFFF" in light
    assert "--text-primary: #17212B" in light
    assert "--accent-orange: #B45309" in light
    assert "--accent-green: #0F766E" in light
    assert "--card-bg: #182431" in dark
    assert "--text-primary: #E8EEF3" in dark
    assert "--accent-orange: #F5B041" in dark
    assert "--accent-green: #32C7AE" in dark
    assert ".mobility-heading__value" in light
    assert ".peak-card" in dark
