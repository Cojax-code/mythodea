"""Interface réelle : profils, sélections, génération, quatre généraux, mobile."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def open_panel(page, identifier):
    panel = page.locator('#' + identifier)
    if panel.get_attribute('open') is None:
        panel.locator(':scope > summary').click()


def run(page):
    with page.expect_response('**/api/simulator/run') as response:
        page.locator('#run-button').click()
    assert response.value.status == 200, response.value.text()
    expect(page.locator('#run-button')).to_have_text('Lancer la simulation')
    expect(page.locator('#results')).to_be_visible()
    return response.value.json()


def main(url, channel):
    artifacts = Path(__file__).resolve().parents[1] / 'test-results'
    artifacts.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=channel, headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(url)
        expect(page.locator('#simulation-form')).to_be_visible()
        expect(page.locator('#classic-order')).to_have_count(0)
        expect(page.locator('#terrain')).to_have_count(0)
        expect(page.locator('.simulator')).to_have_attribute('data-layout', 'horizontal')
        page.locator('#A-avant-count').fill('19')
        page.locator('#layout-button').focus()
        page.keyboard.press('Space')
        expect(page.locator('.simulator')).to_have_attribute('data-layout', 'vertical')
        expect(page.locator('#A-avant-count')).to_have_value('19')
        page.locator('#layout-button').click()
        page.locator('#A-avant-count').fill('20')
        page.locator('#A-general-1-level').fill('10')
        page.locator('#A-general-1-pc').fill('40')
        page.locator('#A-general-1-pc').fill('20')
        page.locator('#generals-A .sim-labels > summary').click()
        page.locator('#A-general-1-label-infanterie').fill('2')
        page.locator('#A-general-1-label-infanterie-active').check()
        page.locator('#A-general-1-qg').check()
        open_panel(page, 'advanced-panel')
        page.locator('#seed-mode').select_option('fixed')
        page.locator('#seed').fill('12')
        first = run(page)
        assert first['calculations'][0][0]['bonus_percent'] == 20
        assert first['qg_initial'][0]['pc_global'] == 20
        assert first['configuration']['armies']['A']['generals'][0]['profile']['labels'] == {'infanterie': 2}
        expect(page.locator('#result-summary')).to_contain_text('Victoire du camp A')
        page.locator('#reuse-seed').click()
        assert run(page)['journal'] == first['journal']
        open_panel(page, 'camp-A')
        page.locator('#A-droite-count').fill('1')
        expect(page.locator('#run-button')).to_be_disabled()
        expect(page.locator('#result-stale')).to_be_visible()
        page.locator('#A-droite-count').fill('0')
        # Quatre emplacements, permutation et conservation des profils.
        for _ in range(3): page.locator('#add-A').click()
        expect(page.locator('#add-A')).to_be_disabled()
        expect(page.locator('#run-button')).to_be_disabled()
        for i in (2, 3, 4): page.locator(f'#A-{i}-avant-count').fill('10')
        page.locator('#A-general-1-position').select_option('4')
        expect(page.locator('#A-general-4-position')).to_have_value('1')
        expect(page.locator('#A-general-1-pc')).to_have_value('20')
        page.locator('#A-general-2-qg').check()
        expect(page.locator('#A-general-1-qg')).not_to_be_checked()
        many = run(page)
        assert len(many['before']['A']['generals']) == 4
        expect(page.locator('.sim-general-result')).to_have_count(5)
        open_panel(page, 'camp-A')
        page.locator('#generals-A .sim-remove').nth(2).click()
        expect(page.locator('#generals-A .sim-general')).to_have_count(3)
        # Génération réutilisable à deux niveaux, réponse du vrai moteur.
        for level in (5, 10):
            page.locator('#A-general-1-level').fill(str(level))
            with page.expect_response('**/api/simulator/generate') as response:
                page.locator('#A-general-1-generate').click()
            assert response.value.status == 200, response.value.text()
            generated = response.value.json()['profile']
            expect(page.locator('#A-general-1-level')).to_have_value(str(level))
            expect(page.locator('#A-general-1-pc')).to_have_value(str(generated['pc']))
            expect(page.locator('#A-general-1-orientation')).to_have_value(generated['nature'])
            expect(page.locator('#A-general-1-generate')).to_be_enabled()
        page.locator('#random-A').click()
        page.screenshot(path=str(artifacts / 'simulateur-v20-profils.png'), full_page=True)
        # Aucun script injecté par le journal ; texte du moteur conservé.
        page.locator('.sim-journal > summary').click()
        assert page.locator('#journal pre').evaluate_all("els => els.map(e => e.textContent).join('')") == many['journal']
        page.locator('.sim-explanation > summary').first.focus()
        page.keyboard.press('Enter')
        expect(page.locator('.sim-explanation p').first).to_be_visible()
        assert not errors, errors
        mobile = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        mobile.on('pageerror', lambda error: errors.append(str(error)))
        mobile.goto(url)
        expect(mobile.locator('#simulation-form')).to_be_visible()
        expect(mobile.locator('.simulator')).to_have_attribute('data-layout', 'vertical')
        mobile.locator('#generals-A .sim-labels > summary').tap()
        assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
        result = run(mobile)
        mobile.locator('.sim-journal > summary').tap()
        mobile.locator('.sim-explanation > summary').first.tap()
        expect(mobile.locator('.sim-explanation p').first).to_be_visible()
        assert mobile.locator('#journal pre').evaluate_all("els => els.map(e => e.textContent).join('')") == result['journal']
        mobile.screenshot(path=str(artifacts / 'simulateur-v20-mobile.png'), full_page=True)
        assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
        unavailable = browser.new_page()
        unavailable.route('**/api/simulator/catalog', lambda route: route.fulfill(status=503))
        unavailable.goto(url)
        expect(unavailable.locator('#simulation-form')).to_be_hidden()
        expect(unavailable.locator('#service-status')).to_contain_text('indisponible')
        assert not errors, errors
        browser.close()
    print('Navigateur : profils, PC, étiquettes, QG, génération réutilisable, positions, multi-généraux, journal, clavier et mobile OK.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8080/simulateur.html')
    parser.add_argument('--channel', default='chrome')
    args = parser.parse_args()
    main(args.url, args.channel)
