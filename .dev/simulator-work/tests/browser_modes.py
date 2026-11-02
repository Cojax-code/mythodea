"""Modes, capacité des soutiens et sélections d'étiquettes dans un vrai navigateur."""
import argparse
from playwright.sync_api import sync_playwright, expect
from browser_smoke import open_panel, run


def main(url, channel):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=channel, headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(url)
        expect(page.locator('#simulation-form')).to_be_visible()
        open_panel(page, 'advanced-panel')
        page.locator('#seed-mode').select_option('fixed')
        page.locator('#seed').fill('901')
        ordinary = run(page)
        page.locator('#combat-mode').select_option('OFF/DEF')
        for defender in ('A', 'B'):
            page.locator('#defender').select_option(defender)
            defensive = run(page)
            assert defensive['after'] == ordinary['after']
            assert defensive['conditions']['defender'] == defender
        page.locator('#swap-button').click()
        expect(page.locator('#defender')).to_have_value('A')
        open_panel(page, 'camp-A')
        open_panel(page, 'camp-B')
        page.locator('#A-avant-count').fill('15')
        page.locator('#A-avant-messengers').fill('1')
        expect(page.locator('#run-button')).to_be_enabled()
        page.locator('#A-avant-count').fill('16')
        expect(page.locator('#run-button')).to_be_disabled()
        page.locator('#A-avant-count').fill('15')
        page.locator('#A-general-1-qg').check()
        supported = run(page)
        assert supported['before']['A']['generals'][0]['blocks']['avant']['messager_du_QG'] == 1
        open_panel(page, 'camp-A')
        page.locator('#A-avant-messengers').fill('0')
        page.locator('#A-general-1-orientation').select_option('instinctif')
        page.locator('#A-general-1-level').fill('5')
        page.locator('#generals-A .sim-labels > summary').click()
        page.locator('#A-general-1-label-orc').fill('2')
        page.locator('#A-general-1-label-orc-active').check()
        page.locator('#A-general-1-label-infanterie').fill('1')
        expect(page.locator('#A-general-1-label-infanterie-active')).to_be_disabled()
        # Le serveur refuse aussi les connaissances incompatibles, sans résultat trompeur.
        with page.expect_response('**/api/simulator/run') as response:
            page.locator('#run-button').click()
        assert response.value.status == 400
        expect(page.locator('#run-error')).to_be_visible()
        page.locator('#A-general-1-label-infanterie').fill('0')
        page.locator('#A-avant-unit').select_option('orc_archer')
        result = run(page)
        assert result['configuration']['armies']['A']['generals'][0]['profile']['active'] == ['orc']
        open_panel(page, 'camp-A')
        page.locator('#random-count-A').select_option('20')
        for _ in range(3):
            page.locator('#A-general-1-random').click()
            expect(page.locator('#run-button')).to_be_enabled()
        random_result = run(page)
        assert random_result['before']['A']['total'] == 20
        # Un échec du serveur conserve tous les champs.
        page.route('**/api/simulator/run', lambda route: route.fulfill(status=503, content_type='application/json', body='{"error":"Moteur indisponible"}'))
        page.locator('#run-button').click()
        expect(page.locator('#run-error')).to_have_text('Moteur indisponible')
        expect(page.locator('#run-button')).to_be_enabled()
        assert not errors, errors
        browser.close()
    print('Navigateur : OFF/OFF, OFF/DEF, échange, Messagers, limites, erreurs API et compositions aléatoires OK.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8080/simulateur.html')
    parser.add_argument('--channel', default='chrome')
    args = parser.parse_args()
    main(args.url, args.channel)
