"""Actions utilisateur communes aux parcours de configuration progressifs."""
from playwright.sync_api import expect


def open_panel(page, identifier):
    panel = page.locator('#' + identifier)
    if panel.get_attribute('open') is None:
        panel.locator(':scope > summary').click()


def panel(page, camp='A', index=1):
    return page.locator(f'#generals-{camp} .sim-general').nth(index - 1)


def choose(page, nature, camp='A', index=1):
    open_panel(page, f'camp-{camp}')
    page.locator(f'#{camp}-general-{index}-orientation').select_option(nature)


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
        field.fill(str(value))
        field.press('Tab')
    else:
        root.get_by_label(f'Choix de récompense niveau {n}', exact=True).select_option(str(value))


def advance(page, camp='A', index=1):
    root = panel(page, camp, index)
    root.get_by_role('button', name='Valider le niveau et les récompenses', exact=True).click()
    for _ in range(3):
        for button in root.get_by_role('button', name='Continuer', exact=False).all():
            if button.is_visible():
                button.click()
    prefix = camp if index == 1 else f'{camp}-{index}'
    expect(page.locator(f'#{prefix}-avant-count')).to_be_visible()


def initialize(page):
    for camp in ('A', 'B'):
        choose(page, 'stratege', camp)
        advance(page, camp)
