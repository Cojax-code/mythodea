// Navigation partagée : les menus <details> se ferment hors clic, à Escape
// et quand un autre menu est ouvert. Compatible clavier et tactile.
(() => {
  function initMenus() {
    const menus = [...document.querySelectorAll('nav details.help-menu')];
    if (!menus.length) return;

    document.addEventListener('pointerdown', (event) => {
      for (const menu of menus) {
        if (menu.open && !menu.contains(event.target)) menu.open = false;
      }
    });

    for (const menu of menus) {
      menu.addEventListener('toggle', () => {
        if (!menu.open) return;
        for (const other of menus) {
          if (other !== menu) other.open = false;
        }
      });
    }

    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape') return;
      const opened = menus.filter(menu => menu.open);
      if (!opened.length) return;
      opened.forEach(menu => { menu.open = false; });
      opened[0].querySelector('summary')?.focus();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMenus, { once: true });
  } else {
    initMenus();
  }
})();
