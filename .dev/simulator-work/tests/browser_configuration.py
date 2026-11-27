"""Configuration expérimentale et calcul officiel, sur ordinateur et mobile."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from browser_smoke import open_panel, run
from browser_helpers import initialize, choose, level, reward, advance

URL = 'http://127.0.0.1:8080/simulateur.html'


def exercise(browser, mobile):
    page = browser.new_page(viewport={'width': 390 if mobile else 1440, 'height': 844 if mobile else 1000},
                            is_mobile=mobile, has_touch=mobile)
    errors, requests = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: requests.append(request.url) if request.url.endswith('/run') else None)
    page.goto(URL)
    expect(page.locator('#simulation-form')).to_be_visible()
    assert page.locator('#A-general-1-orientation option').count() == 5
    assert page.locator('[id$="-known"], [id$="-permanent"], #A-general-1-zombie, .sim-unlocks').count() == 0
    initialize(page)
    expect(page.locator('#A-avant-messengers')).to_be_hidden()
    for nature in ('instinctif', 'hybride', 'stratege'):
        choose(page, nature)
        advance(page)
        choices = page.locator('#A-avant-unit option:not(:disabled)').evaluate_all('items => items.map(o => o.value)')
        assert 'orc_archer' not in choices and 'cavalerie_lourde' not in choices
        page.locator('#A-general-1-pc').fill('40')
        expect(page.locator('#A-general-1-pc')).to_have_value('40')
        expect(page.locator('#A-general-1-morale')).to_be_visible()
    level(page, 3)
    reward(page, 1, 'etiquette', 'infanterie')
    reward(page, 2, 'etiquette', 'distance')
    reward(page, 3, 'etiquette', 'humain')
    advance(page)
    page.locator('#A-general-1-label-infanterie-active').check()
    expect(page.locator('#A-general-1-label-distance-active')).to_be_disabled()
    level(page, 5)
    page.locator('#A-general-1-label-distance-active').check()
    expect(page.locator('#A-general-1-label-humain-active')).to_be_disabled()
    for rank in ('2', '1', '2'):
        page.locator('#A-general-1-label-infanterie').fill(rank)
        expect(page.locator('#A-general-1-label-infanterie')).to_have_value(rank)
    level(page, 10)
    page.locator('#A-general-1-label-humain-active').check()
    level(page, 3)
    expect(page.locator('#A-general-1-label-infanterie')).to_have_value('1')
    page.locator('#A-avant-count').fill('21')
    page.locator('#B-avant-count').fill('0')
    page.locator('#run-button').click()
    expect(page.locator('#validation')).to_contain_text('nombre d’étiquettes supérieur')
    expect(page.locator('#validation')).to_contain_text('Camp A — Général 1 — Bloc Avant')
    expect(page.locator('#validation')).to_contain_text('Camp B — Général 1')
    assert requests == []
    assert page.locator('#validation').evaluate('e => getComputedStyle(e).color') == 'rgb(155, 39, 28)'
    assert page.locator('#validation').evaluate('e => e.previousElementSibling.contains(document.getElementById("run-button"))')
    expect(page.locator('#A-avant-count')).to_have_value('21')
    page.locator('#A-avant-count').fill('15')
    page.locator('#B-avant-count').fill('20')
    for label in ('distance', 'humain'):
        page.locator(f'#A-general-1-label-{label}-active').uncheck()
    expect(page.locator('#validation')).to_be_hidden()
    level(page, 4)
    reward(page, 4, 'unite', 110)
    page.locator('#A-avant-messengers').fill('1')
    page.locator('#A-general-1-qg').check()
    page.locator('#A-general-1-qg-block').select_option('gauche')
    page.locator('#add-A').click()
    choose(page, 'stratege', index=2)
    advance(page, index=2)
    page.locator('#A-2-avant-count').fill('7')
    page.locator('#A-general-2-qg').check()
    expect(page.locator('#A-general-1-qg')).not_to_be_checked()
    page.locator('#A-general-1-qg').check()
    expect(page.locator('#A-general-2-qg')).not_to_be_checked()
    result = run(page)
    g = result['configuration']['armies']['A']['generals'][0]
    assert g['qg_block'] == 'gauche' and g['qg']
    assert g['profile']['labels'] == {'infanterie': 1, 'distance': 1, 'humain': 1}
    assert g['profile']['active'] == ['infanterie'] and g['profile']['permanent'] == []
    assert result['before']['A']['generals'][0]['blocks']['avant']['messager_du_QG'] == 1
    open_panel(page, 'camp-A')
    choose(page, 'zombie')
    level(page, 1)
    page.locator('#A-general-1-zombie_levels').fill('1')
    page.locator('#A-general-1-zombie_levels').press('Tab')
    reward(page, 1, 'etiquette', 'mort_vivant')
    advance(page)
    expect(page.locator('#A-general-1-morale')).to_be_hidden()
    expect(page.locator('#A-avant-count')).to_have_value('0')
    page.locator('#A-avant-unit').select_option('zombie')
    page.locator('#A-avant-count').fill('10')
    page.locator('#A-avant-shield').check()
    expect(page.locator('#A-droite-shield')).to_be_disabled()
    page.locator('#A-general-1-label-mort_vivant-active').check()
    result = run(page)
    assert result['before']['A']['generals'][0]['blocks']['avant']['Trop_gros_zombie'] == 1
    open_panel(page, 'camp-A')
    page.locator('#A-general-1-level').fill('5')
    page.locator('#A-general-1-zombie_levels').fill('3')
    page.locator('#A-avant-count').fill('16')
    for _ in range(2):
        with page.expect_response('**/api/simulator/generate') as response:
            page.locator('#A-general-1-generate').click()
        assert response.value.status == 200, response.value.text()
        expect(page.locator('#A-general-1-generation-status')).to_contain_text('Profil généré')
        expect(page.locator('#A-general-1-generate')).to_be_enabled()
        expect(page.locator('#A-general-1-orientation')).to_have_value('zombie')
        expect(page.locator('#A-general-1-level')).to_have_value('5')
        expect(page.locator('#A-general-1-zombie_levels')).to_have_value('3')
    level(page, 1)
    expect(page.locator('#A-general-1-zombie_levels')).to_have_value('1')
    expect(page.locator('#A-general-1-capabilities')).to_have_value('1,0')
    page.locator('#A-avant-count').fill('10')
    run(page)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    Path('test-results').mkdir(exist_ok=True)
    page.screenshot(path=f'test-results/configuration-{"mobile" if mobile else "desktop"}.png', full_page=True)
    assert not errors, errors
    page.close()


def impact(browser):
    page = browser.new_page()
    page.goto(URL)
    expect(page.locator('#simulation-form')).to_be_visible()
    initialize(page)
    page.locator('#B-avant-unit').select_option('archer')
    level(page, 5)
    reward(page, 1, 'etiquette', 'infanterie')
    advance(page)
    page.locator('#A-general-1-label-infanterie-active').uncheck()
    page.locator('#A-general-1-pc').fill('40')
    open_panel(page, 'advanced-panel')
    page.locator('#seed-mode').select_option('fixed')
    page.locator('#seed').fill('42')
    inactive = run(page)
    open_panel(page, 'camp-A')
    page.locator('#A-general-1-label-infanterie-active').check()
    page.locator('#A-general-1-label-infanterie').fill('2')
    active = run(page)
    assert inactive['calculations'][0][0]['bonus_percent'] == 0
    assert active['calculations'][0][0]['bonus_percent'] == 40
    assert active['after'] != inactive['after']
    open_panel(page, 'camp-A')
    page.locator('#A-general-1-label-infanterie-active').uncheck()
    assert run(page)['after'] == inactive['after']
    page.close()


if __name__ == '__main__':
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        exercise(browser, False)
        exercise(browser, True)
        impact(browser)
        browser.close()
    print('Configuration ordinateur/mobile, orientations, rangs, unités, QG, erreurs et calcul réel : OK')
