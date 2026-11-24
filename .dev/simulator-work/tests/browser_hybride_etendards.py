"""Parcours desktop/mobile contre le vrai serveur Linux, sans calcul substitué."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def exercise(browser, mobile=False):
    page = browser.new_page(viewport={'width': 390 if mobile else 1440, 'height': 1000},
                            is_mobile=mobile, has_touch=mobile)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8080/simulateur.html')
    expect(page.locator('#simulation-form')).to_be_visible()
    choices = page.locator('#A-general-1-orientation option').evaluate_all('items => items.map(o => o.value)')
    assert choices == ['', 'stratege', 'instinctif', 'hybride', 'zombie'], choices
    for camp, nature in [('A', 'hybride'), ('B', 'instinctif')]:
        page.locator(f'#{camp}-general-1-orientation').select_option(nature)
        level = page.locator(f'#{camp}-general-1-level')
        level.fill('20'); level.press('Tab')
        with page.expect_response('**/api/simulator/generate') as response:
            page.locator(f'#{camp}-general-1-generate').click()
        assert response.value.status == 200, response.value.text()
        profile = response.value.json()['profile']
        expect(page.locator(f'#{camp}-general-1-pc')).to_have_value(str(profile['pc']))
        expect(page.locator(f'#{camp}-general-1-capabilities')).to_have_value('3,2' if camp == 'A' else '1,2')
        page.locator(f'#{camp}-general-1-banner-block').select_option('avant')
        page.locator(f'#{camp}-avant-unit').select_option('archer')
        page.locator(f'#{camp}-avant-count').fill('20')
    page.locator('#A-general-1-qg').check()
    page.locator('#A-general-1-qg-block').select_option('avant')
    for mode in ('OFF/OFF', 'OFF/DEF'):
        page.locator('#combat-mode').select_option(mode)
        with page.expect_response('**/api/simulator/run', timeout=20000) as response:
            page.locator('#run-button').click()
        assert response.value.status == 200, response.value.text()
        result = response.value.json()
        assert result['configuration']['armies']['A']['generals'][0]['qg']
        assert result['configuration']['armies']['A']['generals'][0]['banner_block'] == 'avant'
        assert 'Étendard' in result['journal']
        expect(page.locator('#result-summary')).to_contain_text('par étendard')
    # Revenir à un niveau bas propose uniquement les capacités accessibles.
    for camp in ('A', 'B'):
        panel = page.locator(f'#camp-{camp}')
        if panel.get_attribute('open') is None:
            panel.locator(':scope > summary').click()
    field = page.locator('#A-general-1-level')
    field.fill('5'); field.press('Tab')
    assert page.locator('#A-general-1-capabilities option').evaluate_all('es => es.map(e => e.value)') == ['1,1', '2,0']
    page.locator('#A-general-1-capabilities').select_option('2,0')
    expect(page.locator('#A-general-1-banner-block')).to_be_disabled()
    page.locator('#A-general-1-capabilities').select_option('1,1')
    expect(page.locator('#A-general-1-banner-block')).to_be_enabled()
    field.fill('25'); field.press('Tab')
    expect(page.get_by_label('Récompense niveau 25:supplementaire', exact=True).first).to_be_visible()
    assert not errors, errors
    artifacts = Path(__file__).resolve().parents[1] / 'test-results'
    artifacts.mkdir(exist_ok=True)
    page.screenshot(path=str(artifacts / ('hybride-mobile.png' if mobile else 'hybride-desktop.png')), full_page=True)
    page.close()


if __name__ == '__main__':
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        exercise(browser)
        exercise(browser, True)
        browser.close()
    print('Parcours Hybride/Étendards desktop et mobile : OK')
