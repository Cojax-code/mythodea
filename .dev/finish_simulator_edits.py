from pathlib import Path

root = Path(__file__).resolve().parent / 'simulator-work'
p = root / 'js/simulateur.js'
s = p.read_text(encoding='utf-8')
start, end = s.index('    function renderRewardFields('), s.index('    function buildProfile(')
f = s[start:end]
f = f.replace('Number(level) > p.level', 'parseInt(level) > p.level')
f = f.replace('        for (let level = 1; level <= p.level; level++) {', '''        const keys = [];
        for (let level = 1; level <= p.level; level++) {
            keys.push(String(level));
            if ((!p.zombie || level <= p.level - p.zombie_levels) && catalog.extra_roulette_levels[p.nature].includes(level))
                keys.push(`${level}:supplementaire`);
        }
        for (const key of Object.keys(general.rewards)) if (!keys.includes(key)) delete general.rewards[key];
        for (const key of keys) {
            const level = parseInt(key);
            const extra = key.includes(":");''')
f = f.replace('general.rewards[level]', 'general.rewards[key]')
f = f.replace('row.append(node("span", "N" + level));', 'row.append(node("span", "N" + level + (extra ? " · supplémentaire" : " · classique")));')
f = f.replace(' + level);', ' + key);')
f = f.replace('                    prior.level = level - 1;', '''                    prior.level = level - 1;
                    // Le parcours antérieur vient des états exportés par le moteur.
                    delete prior.active_slots; delete prior.banner_level;''')
f = f.replace('if (Number(n) < level)', 'if (parseInt(n) < level || extra && n === String(level))')
f = f.replace('Object.assign(reward, result.reward);', '''if (extra) {
                        const [kind, value] = Array.isArray(result.supplementary) ? result.supplementary : ["unite", result.supplementary];
                        Object.assign(reward, {kind: {maitrise_commandement: "commandement", force_caractere: "moral"}[kind] || kind, value: String(value)});
                    } else Object.assign(reward, result.reward);''')
s = s[:start] + f + s[end:]
s = s.replace('Number(level) > p.level || Number(level) === 0', 'parseInt(level) > p.level || parseInt(level) === 0')
p.write_text(s, encoding='utf-8', newline='\n')

# Les anciennes graphies restent couvertes par les tests de migration du moteur.
for p in (root / 'tests').glob('*.py'):
    s = p.read_text(encoding='utf-8')
    s = s.replace("'stratege_hybride'", "'hybride'").replace("'instinctif_hybride'", "'hybride'")
    s = s.replace('"stratege_hybride"', '"hybride"').replace('"instinctif_hybride"', '"hybride"')
    s = s.replace("'stratege', 'instinctif', 'hybride', 'hybride'", "'stratege', 'instinctif', 'hybride'")
    s = s.replace("('hybride', 'hybride')", "('hybride',)")
    p.write_text(s, encoding='utf-8', newline='\n')
