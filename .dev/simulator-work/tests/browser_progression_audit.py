"""Parcours réel progression, avec Chrome et le backend Bubblewrap."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from browser_smoke import open_panel, run

URL = 'http://127.0.0.1:8080/simulateur.html'


def panel(page, camp='A'):
    return page.locator(f'#generals-{camp} .sim-general').first


def choose(page, nature, camp='A'):
    open_panel(page, f'camp-{camp}')
    page.locator(f'#{camp}-general-1-orientation').select_option(nature)


def level(page, value, camp='A'):
    field = page.locator(f'#{camp}-general-1-level')
    field.fill(str(value))
    field.press('Tab')


def reward(page, n, kind, value, camp='A'):
    root = panel(page, camp)
    selector = root.get_by_label(f'Récompense niveau {n}', exact=True)
    if selector.input_value() != kind:
        selector.select_option(kind)
    if kind in ('commandement', 'moral'):
        field = root.get_by_label(f'Valeur de récompense niveau {n}', exact=True)
        field.fill(str(value)); field.press('Tab')
    else:
        root.get_by_label(f'Choix de récompense niveau {n}', exact=True).select_option(str(value))


def advance(page, camp='A'):
    root = panel(page, camp)
    root.get_by_role('button', name='Valider le niveau et les récompenses', exact=True).click()
    for _ in range(3):
        buttons = root.get_by_role('button', name='Continuer', exact=False)
        for button in buttons.all():
            if button.is_visible():
                button.click()
    expect(page.locator(f'#{camp}-avant-count')).to_be_visible()


def natural(page):
    with page.expect_response('**/api/simulator/natural') as response:
        page.locator('#A-general-1-natural').click()
    assert response.value.status == 200, response.value.text()
    expect(page.locator('#A-general-1-natural')).to_be_enabled()
    return response.value.json()


def exercise(browser, mobile=False):
    page = browser.new_page(viewport={'width': 390 if mobile else 1440, 'height': 844 if mobile else 1000},
                            is_mobile=mobile, has_touch=mobile)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(URL)
    expect(page.locator('#simulation-form')).to_be_visible()
    choose(page, 'stratege', 'B'); advance(page, 'B')
    choose(page, 'stratege'); advance(page)
    expect(page.locator('#A-general-1-pc')).to_have_value('0')
    expect(page.locator('#A-general-1-morale')).to_have_value('0')
    expect(page.locator('#generals-A .sim-labels')).to_be_hidden()
    assert page.get_by_role('button', name='Tirer les récompenses et les gains naturels', exact=True).count() == 0
    assert page.locator('#A-avant-unit option[value="cavalerie_lourde"]').count() == 0
    assert page.locator('#A-avant-unit option[value="chevalier_clinquant"]').count() == 0
    # Les gains naturels sont remplacés, les récompenses et désactivations conservées.
    for nature in ('stratege', 'instinctif', 'hybride'):
        choose(page, nature)
        for n in (1, 5, 10, 15):
            level(page, n)
            for i in range(1, n + 1):
                if i == 5 or i == 10 and nature.startswith('stratege'):
                    reward(page, i, 'etiquette', 'infanterie' if i == 5 else 'distance')
                else:
                    reward(page, i, 'commandement', 5)
            advance(page)
            if n >= 5:
                page.locator('#A-general-1-label-infanterie-active').uncheck()
            before = panel(page).locator('.sim-rewards-list').evaluate('e => e.innerText + [...e.querySelectorAll("select,input")].map(e => e.value).join()')
            totals = 5 * (n - (1 if n >= 5 else 0) - (1 if n >= 10 and nature.startswith('stratege') else 0))
            for _ in range(2):
                gains = natural(page)
                expect(page.locator('#A-general-1-pc')).to_have_value(str(gains['pc'] + totals))
                expect(page.locator('#A-general-1-morale')).to_have_value(str(gains['morale']))
                assert panel(page).locator('.sim-rewards-list').evaluate('e => e.innerText + [...e.querySelectorAll("select,input")].map(e => e.value).join()') == before
                if n >= 5:
                    expect(page.locator('#A-general-1-label-infanterie-active')).not_to_be_checked()
            if nature.startswith('instinctif'):
                expect(page.locator('#A-general-1-qg')).to_be_disabled()
    # L'Hybride accède aux deux familles, mais chaque unité exige son acquisition.
    choose(page, 'hybride'); level(page, 1)
    reward(page, 1, 'unite', 106)
    choices = panel(page).get_by_label('Choix de récompense niveau 1', exact=True)
    assert choices.locator('option[value="108"]').count() == 1
    advance(page)
    assert page.locator('#A-avant-unit option[value="orc_archer"]').count() == 0
    choose(page, 'stratege'); level(page, 5)
    reward(page, 1, 'unite', 106)
    reward(page, 2, 'moral', 4)
    reward(page, 3, 'unite', 110)
    reward(page, 4, 'commandement', 10)
    reward(page, 5, 'etiquette', 'infanterie')
    advance(page)
    natural(page)
    expect(page.locator('#A-general-1-morale')).to_have_value('4')
    page.locator('#A-general-1-label-infanterie').fill('2')
    page.locator('#A-general-1-label-infanterie').press('Tab')
    page.locator('#A-general-1-label-infanterie-active').uncheck()
    page.locator('#A-avant-unit').select_option('chevalier_clinquant')
    page.locator('#A-avant-count').fill('10')
    page.locator('#A-avant-messengers').fill('1')
    page.locator('#A-general-1-qg').check()
    result = run(page)
    p = result['configuration']['armies']['A']['generals'][0]['profile']
    assert p['labels'] == {'infanterie': 2} and p['active'] == []
    assert p['unlocked_evolutions'] == [106, 110]
    open_panel(page, 'camp-A')
    panel(page).get_by_label('Cavalerie lourde débloquée par quête', exact=True).check()
    page.locator('#A-avant-unit').select_option('cavalerie_lourde')
    result = run(page)
    assert result['configuration']['armies']['A']['generals'][0]['profile']['quest_heavy_cavalry']
    # Réorientation réinitialise QG, acquis et unités sans erreur JavaScript.
    choose(page, 'instinctif'); level(page, 1); reward(page, 1, 'unite', 104); advance(page)
    expect(page.locator('#A-general-1-qg')).not_to_be_checked()
    page.locator('#A-avant-unit').select_option('cavalerie_lourde')
    page.locator('#A-avant-count').fill('10')
    run(page)
    # Le palier donne une récompense classique et une capacité spécifique.
    open_panel(page, 'camp-A'); level(page, 5)
    with page.expect_response('**/api/simulator/reward') as response:
        panel(page).get_by_role('button', name='Tirer une valeur pour la récompense du niveau 5', exact=True).click()
    assert response.value.status == 200, response.value.text()
    expected = response.value.json()['reward']
    expect(panel(page).get_by_label('Récompense niveau 5', exact=True)).to_have_value(expected['kind'])
    field = 'Valeur' if expected['kind'] in ('commandement', 'moral') else 'Choix'
    expect(panel(page).get_by_label(f'{field} de récompense niveau 5', exact=True)).to_have_value(expected['value'])
    # Zombie : historique vivant conservé, seuls les niveaux suivants sont zombies.
    choose(page, 'zombie'); level(page, 5)
    page.locator('#A-general-1-zombie_levels').fill('3')
    page.locator('#A-general-1-zombie_levels').press('Tab')
    reward(page, 1, 'commandement', 10)
    reward(page, 2, 'moral', 4)
    reward(page, 3, 'etiquette', 'mort_vivant')
    advance(page)
    gains = natural(page)
    assert 4 <= gains['pc'] <= 8
    expect(page.locator('#A-general-1-pc')).to_have_value(str(gains['pc'] + 10))
    page.locator('#A-avant-count').fill('10')
    page.locator('#A-avant-shield').check()
    run(page)
    # Les deux modes de combat restent exécutables avec le moteur isolé.
    open_panel(page, 'advanced-panel')
    page.locator('#combat-mode').select_option('OFF/DEF')
    page.locator('#defender').select_option('B')
    assert run(page)['configuration']['mode'] == 'OFF/DEF'
    assert not errors, errors
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    Path('test-results').mkdir(exist_ok=True)
    page.screenshot(path=f'test-results/progression-{"mobile" if mobile else "desktop"}.png', full_page=True)
    page.close()


if __name__ == '__main__':
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        exercise(browser)
        exercise(browser, True)
        browser.close()
    print('Progression desktop/mobile, trois orientations, zombies, QG, déblocages, OFF/OFF et OFF/DEF : OK')
