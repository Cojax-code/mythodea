"use strict";

(() => {
    const $ = (id) => document.getElementById(id);
    const unitNames = {archer: "Archers", piquier: "Piquiers", cavalier: "Cavaliers", cavalerie_lourde: "Cavalerie lourde"};
    const blockNames = {avant: "Avant", droite: "Droite", gauche: "Gauche", arriere: "Arrière"};
    const camps = ["A", "B"];
    const orientations = {stratege: "Stratège", instinctif: "Instinctif", hybride: "Hybride", zombie: "Général zombie"};
    const maxActivePositions = 4;
    const armies = {A: [], B: []};
    const mobile = matchMedia("(max-width: 800px)");
    let nextGeneralId = 1;
    let verticalLayout = false;
    let catalog;
    let busy = false;
    let lastResult = null;
    let submittedConfiguration = null;
    let showErrors = false;
    let configurationErrors = [];

    function node(tag, text, className) {
        const element = document.createElement(tag);
        if (text !== undefined) element.textContent = text;
        if (className) element.className = className;
        return element;
    }

    function newGeneral(camp, initial = false) {
        const position = [1, 2, 3, 4].find(value => !armies[camp].some(g => g.position === value));
        return {id: nextGeneralId++, position, open: true, orientation: "stratege", qg: false, qgBlock: "arriere", banner_block: null,
            uiStep: 1, typeChosen: false, questHeavyCavalry: false, rewards: {}, naturalStats: {pc: 0, morale: 0}, appliedRewardStats: {pc: 0, morale: 0}, profile: {level: 0, nature: "stratege", trait: "leader", pc: 0, morale: 0, labels: {}, permanent: [], active: [], zombie: false, zombie_levels: 0, unlocked_evolutions: [], corpse_available: false},
            blocks: Object.fromEntries(catalog.blocks.map(block => [block, {
                unit: camp === "A" ? "archer" : "piquier", count: initial && block === "avant" ? "20" : "0"
            }]))};
    }

    function rememberGenerals() {
        for (const camp of camps) for (const general of armies[camp]) {
            if (!general.element) continue;
            general.open = general.element.open;
            // Seul le gestionnaire change valide une nouvelle orientation et
            // réinitialise les acquisitions. L'événement input le précède.
            const p = general.profile;
            p.zombie = general.orientation === "zombie";
            // La nature d'origine reste interne au profil zombie officiel.
            if (!p.zombie) p.nature = general.orientation;
            for (const key of ["level", "pc", "morale", "zombie_levels"]) p[key] = Number(general.profileControls[key].value);
            general.labelsOpen = general.labelsPanel.open;
            general.qg = !p.zombie && ["stratege", "hybride"].includes(p.nature) && general.profileControls.qg.checked;
            general.qgBlock = general.qgBlockInput.value;
            const selected = general.profileControls.capabilities.value.split(",").map(Number);
            [p.active_slots, p.banner_level] = selected;
            general.banner_block = general.profileControls.banner_block.value || null;
            p.unlocked_evolutions = [...new Set(Object.values(general.rewards || {})
                .filter(reward => reward.kind === "unite" && reward.value).map(reward => Number(reward.value)))];
            p.corpse_available = p.zombie;
            p.quest_heavy_cavalry = general.questHeavyCavalry;
            p.labels = {}; p.permanent = []; p.active = [];
            const earned = new Set(earnedRewardLabels(general));
            for (const [name, inputs] of Object.entries(general.labelControls)) {
                if (!earned.has(name)) continue;
                p.labels[name] = Number(inputs.rank.value) || 1;
                if (inputs.active.checked) p.active.push(name);
            }
            for (const block of catalog.blocks) {
                const controls = general.controls[block];
                general.blocks[block] = {unit: controls.unit.value, count: controls.count.value, messengers: Number(controls.messengers.value), shield: controls.shield.checked};
            }
        }
    }

    function combatBlocks(general) {
        return Object.fromEntries(catalog.blocks.map(block => [block, {
            ...general.blocks[block], count: Number(general.blocks[block].count)
        }]));
    }

    function randomBlocks(total, general) {
        // Préparation locale uniquement : aucun lien avec la graine du moteur.
        const pick = length => Math.floor(Math.random() * length);
        if (total === null) total = 1 + pick(catalog.max_units);
        const units = catalog.units.filter(unit => !["messager_du_QG", "Trop_gros_zombie"].includes(unit) && availableUnits(general).includes(unit));
        const blocks = [...catalog.blocks];
        for (let index = blocks.length - 1; index > 0; index--) {
            const other = pick(index + 1);
            [blocks[index], blocks[other]] = [blocks[other], blocks[index]];
        }
        const active = blocks.slice(0, 1 + pick(Math.min(blocks.length, total)));
        const result = Object.fromEntries(catalog.blocks.map(block => [block, {
            unit: units[pick(units.length)], count: 0, messengers: 0, shield: false
        }]));
        for (const block of active) result[block].count = 1;
        for (let remaining = total - active.length; remaining > 0; remaining--) result[active[pick(active.length)]].count++;
        for (const block of catalog.blocks) result[block].count = String(result[block].count);
        return result;
    }

    function randomize(camp, targets, focusId) {
        rememberGenerals();
        const choice = $(`random-count-${camp}`).value;
        const total = choice === "auto" ? null : Number(choice);
        const scope = targets.length === 1
            ? `du général ${armies[camp].indexOf(targets[0]) + 1} du camp ${camp}`
            : `des ${targets.length} généraux du camp ${camp}`;
        for (const general of targets) general.blocks = randomBlocks(total, general);
        renderGenerals();
        $(`random-status-${camp}`).textContent = `Composition ${scope} générée. Vous pouvez modifier chaque bloc ; la graine de combat est inchangée.`;
        $(focusId).focus();
    }

    function seedValue() {
        return $("seed-mode").value === "auto" ? null : Number($("seed").value);
    }

    function battleSignature() {
        return JSON.stringify(configuration());
    }

    function configuration() {
        return {
            armies: Object.fromEntries(camps.map(camp => [camp, {generals: armies[camp].map(general => ({
                position: general.position, qg: general.qg, qg_block: general.qgBlock, banner_block: general.banner_block, profile: general.profile, blocks: combatBlocks(general)
            }))}])),
            seed: seedValue(),
            mode: $("combat-mode").value,
            defender: $("combat-mode").value === "OFF/DEF" ? $("defender").value : null
        };
    }

    function update() {
        if (!catalog) return;
        rememberGenerals();
        configurationErrors = [];
        for (const camp of camps) for (const general of armies[camp]) refreshChoices(general);
        const defensive = $("combat-mode").value === "OFF/DEF";
        $("defender-field").hidden = !defensive;
        $("defender").disabled = !defensive;
        for (const camp of camps) {
            let campTotal = 0;
            if (armies[camp].filter(g => g.qg).length > 1) configurationErrors.push(`Camp ${camp} : plusieurs quartiers généraux sélectionnés.`);
            for (const [index, general] of armies[camp].entries()) {
                const where = `Camp ${camp} — Général ${index + 1}`;
                const errors = [];
                const p = general.profile;
                if (!general.typeChosen) errors.push(`${where} : choisissez le type de général.`);
                for (const [level, reward] of Object.entries(general.rewards)) {
                    const input = general.rewardsContainer.querySelector(`[aria-label="Valeur de récompense niveau ${level}"]`);
                    if (["commandement", "moral"].includes(reward.kind) && (!input.value || !input.checkValidity()))
                        errors.push(`${where} : valeur de récompense invalide au niveau ${level}.`);
                    if (["etiquette", "unite"].includes(reward.kind) && !reward.value)
                        errors.push(`${where} : choisissez la récompense du niveau ${level}.`);
                }
                const capacity = capacityOf(p);
                const units = availableUnits(general);
                let total = 0, shields = 0, zombies = 0;
                for (const block of catalog.blocks) {
                    const c = general.controls[block], b = general.blocks[block];
                    const count = Number(c.count.value), messengers = Number(c.messengers.value);
                    const blockWhere = `${where} — Bloc ${blockNames[block]}`;
                    if (!c.count.value || !c.count.checkValidity() || !Number.isInteger(count)) errors.push(`${blockWhere} : effectif entier entre 0 et ${c.count.max} requis.`);
                    if (!c.messengers.value || !c.messengers.checkValidity() || !Number.isInteger(messengers)) errors.push(`${blockWhere} : nombre de Messagers invalide.`);
                    const occupied = count * catalog.unit_details[b.unit].places + 5 * messengers + 10 * c.shield.checked;
                    total += Number.isFinite(occupied) ? occupied : 0;
                    if (occupied > capacity) errors.push(`${blockWhere} : capacité maximale dépassée (${occupied} / ${capacity} places).`);
                    if (count > 0 && !units.includes(b.unit)) errors.push(`${blockWhere} : unité incompatible avec ce type de général.`);
                    if (messengers > 0 && !units.includes("messager_du_QG")) errors.push(`${blockWhere} : Messager incompatible avec ce type de général.`);
                    if (c.shield.checked && !units.includes("Trop_gros_zombie")) errors.push(`${blockWhere} : Gros zombie réservé aux généraux zombies.`);
                    shields += Number(c.shield.checked);
                    if (b.unit === "zombie") zombies += count;
                    c.hint.textContent = b.unit === "cavalerie_lourde" && count > 0
                        ? (block === "avant" && count >= 15 ? "Formation lourde : seuil de 15 atteint." : "Cavalerie lourde : sans bonus de formation.")
                        : (count === 0 ? "Bloc vide" : "");
                }
                if (total < 1) errors.push(`${where} : la composition doit contenir au moins une unité.`);
                if (total > capacity) errors.push(`${where} : capacité maximale dépassée (${total} / ${capacity} places).`);
                if (shields > 1) errors.push(`${where} : un seul Gros zombie est autorisé.`);
                if (shields && zombies < 1) errors.push(`${where} : le Gros zombie doit accompagner des Zombies ordinaires.`);
                const maximum = activeLimit(p);
                const ordinary = p.active.filter(name => !(p.zombie && name === "mort_vivant")).length;
                if (ordinary > maximum) errors.push(`${where} : nombre d’étiquettes supérieur à la limite autorisée (${ordinary} / ${maximum}).`);
                for (const [name, inputs] of Object.entries(general.labelControls)) {
                    const reserved = p.zombie && name === "mort_vivant";
                    inputs.active.disabled = !(name in p.labels) || (!inputs.active.checked && !reserved && ordinary >= maximum);
                    if (inputs.active.checked && (!inputs.rank.value || !inputs.rank.checkValidity())) errors.push(`${where} : rang invalide pour l’étiquette ${name.replaceAll("_", " ")}.`);
                }
                for (const [key, input] of Object.entries(general.profileControls)) {
                    if (!input.disabled && (!input.checkValidity() || (input.type === "number" && !Number.isSafeInteger(Number(input.value))))) errors.push(`${where} : ${input.labels?.[0]?.textContent || key} invalide.`);
                }
                if (general.qg && !catalog.blocks.includes(general.qgBlock)) errors.push(`${where} : bloc du QG invalide.`);
                general.labelsSummary.textContent = `${ordinary} / ${maximum} étiquette(s) sélectionnée(s)${p.zombie ? " · mort_vivant dispose d’un emplacement réservé supplémentaire" : ""}${p.pc === 0 ? " · PC nuls : aucun bonus d’étiquette" : ""}`;
                general.steps?.forEach((section, i) => { section.hidden = i + 2 > general.uiStep; });
                general.qgStep.hidden = p.zombie || (!["stratege", "hybride"].includes(p.nature) && !p.banner_level) || general.uiStep < 4;
                general.labelStep.hidden = earnedRewardLabels(general).length === 0 || general.uiStep < 5;
                general.nextQG.textContent = earnedRewardLabels(general).length ? "Continuer vers les étiquettes" : "Continuer vers la composition";
                if (general.extras) general.extras.hidden = general.uiStep < 6;
                general.summary.textContent = `Position ${general.position} · ${total} / ${capacity} places · N${p.level} · ${p.pc} PC · ${orientations[general.orientation]}${general.qg ? ` · QG (${blockNames[general.qgBlock]})` : ""}${errors.length ? " · saisie à vérifier" : ""}`;
                general.summary.classList.toggle("sim-error", errors.length > 0);
                general.removeButton.disabled = armies[camp].length === 1;
                configurationErrors.push(...errors);
                campTotal += total;
            }
            const count = armies[camp].length;
            $(`total-${camp}`).textContent = `${count} ${count === 1 ? "général" : "généraux"} · ${campTotal} places · ${count} / ${maxActivePositions} positions`;
            $(`add-${camp}`).disabled = count >= maxActivePositions;
        }
        const fixedSeed = $("seed-mode").value === "fixed";
        $("fixed-seed").hidden = !fixedSeed;
        $("seed").disabled = !fixedSeed;
        if (fixedSeed && (!$("seed").value || !$("seed").checkValidity())) configurationErrors.push("Graine de combat : entier entre 0 et 4294967295 requis.");
        $("validation").replaceChildren(...(showErrors ? configurationErrors.map(error => node("p", error)) : []));
        $("validation").hidden = !showErrors || !configurationErrors.length;
        $("run-button").disabled = busy;
        $("advanced-summary").textContent = fixedSeed ? `Graine fixe : ${$("seed").value || "à renseigner"}` : "Réglages automatiques";
        if (lastResult) {
            const stale = battleSignature() !== submittedConfiguration;
            $("result-stale").hidden = !stale;
            $("results-caption").textContent = `${$("results-caption").dataset.outcome}${stale ? " · configuration modifiée" : ""}`;
        }
    }

    function capacityOf(profile) {
        return profile.zombie ? catalog.options.zombie_capacities[profile.zombie_levels] : catalog.options.normal_capacity;
    }

    function availableUnits(general) {
        const p = general.profile;
        if (p.zombie) return ["zombie", "Trop_gros_zombie"];
        return catalog.options.natures[p.nature].compatible_units.filter(name => {
            const detail = catalog.unit_details[name];
            if (detail.etiquettes.includes("mort_vivant")) return false;
            if (name === "cavalerie_lourde") return p.unlocked_evolutions.includes(104) || general.questHeavyCavalry === true;
            if (!detail.progression) return true;
            return Object.entries(catalog.options.natures[p.nature].evolutions || {}).some(
                ([id, unit]) => unit === name && p.unlocked_evolutions.includes(Number(id)));
        });
    }

    function refreshChoices(general) {
        const p = general.profile, controls = general.profileControls;
        const levelValid = controls.level.checkValidity() && controls.level.value !== "";
        if (levelValid) {
            p.zombie_levels = p.zombie ? Math.min(p.level, p.zombie_levels) : 0;
            controls.zombie_levels.value = p.zombie_levels;
            controls.zombie_levels.max = p.level;
        }
        controls.zombie_levels.parentElement.hidden = !p.zombie;
        controls.zombie_levels.disabled = !p.zombie;
        controls.morale.parentElement.hidden = p.zombie;
        controls.morale.disabled = p.zombie;
        const qgAllowed = !p.zombie && ["stratege", "hybride"].includes(p.nature);
        controls.banner_block.disabled = p.zombie || !p.banner_level;
        if (controls.banner_block.disabled) { controls.banner_block.value = ""; general.banner_block = null; }
        general.qgStep.hidden = !qgAllowed && controls.banner_block.disabled;
        general.qgField.hidden = !qgAllowed;
        general.continueStats.textContent = (qgAllowed || !controls.banner_block.disabled) ? "Continuer vers le QG et l’étendard" : (earnedRewardLabels(general).length ? "Continuer vers les étiquettes" : "Continuer vers la composition");
        controls.qg.disabled = !qgAllowed;
        if (!qgAllowed) {
            controls.qg.checked = false;
            general.qg = false;
        }
        general.qgPlacement.hidden = !general.qg;
        general.qgBlockInput.disabled = !general.qg;
        for (const [name, inputs] of Object.entries(general.labelControls)) {
            const max = catalog.label_rank_max[p.level] || 1;
            inputs.rank.max = max;
            if (levelValid && Number(inputs.rank.value) > max) inputs.rank.value = max;
            inputs.rank.disabled = !inputs.active.checked;
            if (name in p.labels) p.labels[name] = Number(inputs.rank.value);
            inputs.rank.closest(".sim-label-row").classList.toggle("sim-known", inputs.active.checked);
        }
        
        const units = availableUnits(general);
        const fighters = units.filter(name => !["messager_du_QG", "Trop_gros_zombie"].includes(name));
        for (const block of catalog.blocks) {
            const b = general.blocks[block], c = general.controls[block];
            if (!fighters.includes(b.unit) && Number(b.count) === 0) b.unit = fighters[0];
            // Conserver une saisie devenue incompatible pour permettre sa correction.
            const choices = fighters.includes(b.unit) ? fighters : [b.unit, ...fighters];
            c.unit.replaceChildren(...choices.map(name => {
                const compatible = fighters.includes(name);
                const option = node("option", `${unitNames[name] || name.replaceAll("_", " ")}${compatible ? "" : " — incompatible"}`);
                option.value = name; option.disabled = !compatible; return option;
            }));
            c.unit.value = b.unit;
            c.count.max = Math.floor(capacityOf(p) / catalog.unit_details[b.unit].places);
            c.messengerField.hidden = !units.includes("messager_du_QG") && !b.messengers;
            c.shieldField.hidden = !p.zombie && !b.shield;
            c.shield.disabled = !b.shield && (!units.includes("Trop_gros_zombie") ||
                !Object.values(general.blocks).some(v => v.unit === "zombie" && Number(v.count) > 0) ||
                Object.values(general.blocks).some(v => v.shield));
        }
        general.unitHelp.textContent = p.zombie
            ? "Unités zombies uniquement. Gros zombie : 10 places, un seul, accompagné de Zombies ordinaires. Aucun moral ni soin."
            : "Les unités évoluées exigent leur déblocage. La Forge transforme les unités déjà débloquées. Messager : 5 places.";
    }

    function activeLimit(profile) {
        return profile.active_slots ?? 1;
    }

    function earnedRewardLabels(general) {
        return [...new Set(Object.values(general.rewards)
            .filter(item => item.kind === "etiquette" && item.value)
            .map(item => item.value))];
    }

    function syncRewardSelections(general) {
        const p = general.profile;
        const known = earnedRewardLabels(general);
        const previous = new Set(Object.keys(p.labels));
        const retained = {};
        for (const name of known) retained[name] = p.labels[name] || 1;
        p.labels = retained;
        p.active = p.active.filter(name => known.includes(name));
        for (const name of known) if (!previous.has(name) &&
            (p.active.filter(n => !(p.zombie && n === "mort_vivant")).length < activeLimit(p) || p.zombie && name === "mort_vivant"))
            p.active.push(name);
        p.unlocked_evolutions = [...new Set(Object.values(general.rewards)
            .filter(item => item.kind === "unite" && item.value)
            .map(item => Number(item.value)))];
        if (general.labelControls) for (const [name, c] of Object.entries(general.labelControls)) {
            c.row.hidden = !known.includes(name);
            if (!known.includes(name)) {
                c.active.checked = false;
            } else {
                c.rank.value = p.labels[name];
                c.active.checked = p.active.includes(name);
            }
        }
        if (general.profileControls?.pc && general.profileControls?.morale) {
            const totals = {pc: 0, morale: 0};
            for (const reward of Object.values(general.rewards)) {
                const amount = Number(reward.value);
                if (reward.kind === "commandement" && Number.isInteger(amount) && amount >= 5 && amount <= 10)
                    totals.pc += amount;
                if (reward.kind === "moral" && Number.isInteger(amount) && amount >= 2 && amount <= 4)
                    totals.morale += amount;
            }
            for (const key of ["pc", "morale"]) {
                const limit = key === "morale" ? 100 : Infinity;
                p[key] = Math.max(0, Math.min(limit, general.naturalStats[key] + totals[key]));
                general.profileControls[key].value = String(p[key]);
            }
            general.appliedRewardStats = totals;
        }
        if (general.uiStep === 5 && !known.length) general.uiStep = 6;
    }

    async function engineRequest(operation, payload) {
        const response = await fetch(`/api/simulator/${operation}`, {
            method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Calcul indisponible.");
        return result;
    }

    function generationRequest(general, level = general.profile.level) {
        const p = general.profile;
        return {level, nature: p.nature, zombie: p.zombie,
            zombie_levels: Math.max(0, level - (p.level - p.zombie_levels)), seed: null};
    }

    function renderRewardFields(general) {
        if (!general.rewardsContainer) return;
        const p = general.profile;
        const options = catalog.options.natures[p.nature]?.roulette_evolutions || {};
        const knownLabels = new Set(), knownUnits = new Set();
        const rows = node("div", undefined, "sim-rewards-list");
        const keys = [];
        for (let level = 1; level <= p.level; level++) {
            keys.push(String(level));
            if ((!p.zombie || level <= p.level - p.zombie_levels) && catalog.extra_roulette_levels[p.nature].includes(level))
                keys.push(`${level}:supplementaire`);
        }
        for (const key of Object.keys(general.rewards)) if (!keys.includes(key)) delete general.rewards[key];
        for (const key of keys) {
            const level = parseInt(key);
            const extra = key.includes(":");
            const zombieLevel = p.zombie && level > p.level - p.zombie_levels;
            const reward = general.rewards[key] || {kind: "", value: ""};
            const row = node("div", undefined, "sim-reward-row");
            row.append(node("span", "N" + level + (extra ? " · supplémentaire" : " · classique")));
            const kind = node("select");
            const categories = zombieLevel ? [["", "Aucune"], ...(!knownLabels.has("mort_vivant") ? [["etiquette", "Mort-vivant"]] : [])]
                : [["", "Non renseignée"], ["commandement", "PC (+5 à +10)"],
                   ["moral", "Moral (+2 à +4)"], ["etiquette", "Étiquette"], ["unite", "Unité débloquée"]];
            for (const [id, label] of categories) {
                const option = node("option", label); option.value = id; kind.append(option);
            }
            if (!categories.some(([id]) => id === reward.kind)) { reward.kind = ""; reward.value = ""; }
            const labelChoices = (zombieLevel ? ["mort_vivant"] : Object.keys(catalog.labels)).filter(name => !knownLabels.has(name));
            const unitChoices = Object.entries(options).filter(([id]) => !knownUnits.has(id));
            if (reward.kind === "etiquette" && !labelChoices.includes(reward.value) ||
                reward.kind === "unite" && !unitChoices.some(([id]) => id === reward.value)) reward.value = "";
            general.rewards[key] = reward;
            if (reward.kind === "etiquette" && reward.value) knownLabels.add(reward.value);
            if (reward.kind === "unite" && reward.value) knownUnits.add(reward.value);
            kind.value = reward.kind;
            kind.setAttribute("aria-label", "Récompense niveau " + key);
            const choice = node("select");
            choice.setAttribute("aria-label", "Choix de récompense niveau " + key);
            const amount = node("input");
            Object.assign(amount, {type: "number", step: "1"});
            amount.setAttribute("aria-label", "Valeur de récompense niveau " + key);
            const renderChoice = () => {
                const selections = reward.kind === "etiquette"
                    ? labelChoices
                        .map(name => [name, name.replaceAll("_", " ")])
                    : reward.kind === "unite"
                        ? unitChoices.map(([id, name]) => [id, unitNames[name] || name.replaceAll("_", " ")])
                        : [];
                const placeholder = node("option", "Choisir…"); placeholder.value = "";
                choice.replaceChildren(placeholder, ...selections.map(([id, text]) => {
                    const opt = node("option", text); opt.value = id; return opt;
                }));
                choice.value = selections.some(([id]) => id === reward.value) ? reward.value : "";
                choice.hidden = selections.length === 0;
                amount.hidden = !["commandement", "moral"].includes(reward.kind);
                amount.min = reward.kind === "commandement" ? "5" : "2";
                amount.max = reward.kind === "commandement" ? "10" : "4";
                amount.value = reward.kind === "commandement" || reward.kind === "moral" ? reward.value : "";
            };
            const randomValue = node("button", "Aléatoire", "sim-secondary");
            randomValue.type = "button";
            randomValue.setAttribute("aria-label", "Tirer une valeur pour la récompense du niveau " + key);
            const apply = () => {
                general.rewards[key] = {...reward};
                renderRewardFields(general);
                syncRewardSelections(general);
                if (general.rewardInfo) general.rewardInfo.textContent = "Étiquettes acquises : " + (earnedRewardLabels(general).join(", ").replaceAll("_", " ") || "aucune");
                update();
            };
            kind.addEventListener("change", () => { reward.kind = kind.value; reward.value = ""; renderChoice(); apply(); });
            choice.addEventListener("change", () => { reward.value = choice.value; apply(); });
            amount.addEventListener("change", () => { reward.value = amount.value; apply(); });
            randomValue.addEventListener("click", async () => {
                rememberGenerals();
                const signature = JSON.stringify([p, general.rewards]);
                randomValue.disabled = true;
                try {
                    const prior = structuredClone(p);
                    prior.level = level - 1;
                    // Le parcours antérieur vient des états exportés par le moteur.
                    delete prior.active_slots; delete prior.banner_level;
                    prior.zombie = zombieLevel;
                    prior.zombie_levels = Math.max(0, level - 1 - (p.level - p.zombie_levels));
                    prior.labels = {}; prior.active = []; prior.permanent = []; prior.unlocked_evolutions = [];
                    const natural = await engineRequest("natural", generationRequest(general, level - 1));
                    prior.pc = natural.pc; prior.morale = natural.morale;
                    for (const [n, item] of Object.entries(general.rewards)) if (parseInt(n) < level || extra && n === String(level)) {
                        if (item.kind === "etiquette" && item.value) prior.labels[item.value] = 1;
                        if (item.kind === "unite" && item.value) prior.unlocked_evolutions.push(Number(item.value));
                        if (item.kind === "commandement") prior.pc += Number(item.value);
                        if (item.kind === "moral") prior.morale = Math.min(100, prior.morale + Number(item.value));
                    }
                    const result = await engineRequest("reward", {profile: prior, seed: null, slot: extra ? "supplementaire" : "classique"});
                    if (!randomValue.isConnected || signature !== JSON.stringify([p, general.rewards])) return;
                    Object.assign(reward, result.reward);
                    apply();
                } catch (error) { general.rewardInfo.textContent = error.message; }
                finally { randomValue.disabled = false; }
            });
            renderChoice();
            row.append(kind, choice, amount, randomValue);
            rows.append(row);
        }
        general.rewardsContainer.replaceChildren(rows);
        const acquired = earnedRewardLabels(general);
        if (general.rewardInfo) general.rewardInfo.textContent = acquired.length
            ? "Étiquettes acquises : " + acquired.join(", ").replaceAll("_", " ")
            : "Aucune étiquette acquise à ce niveau.";
    }

    function buildProfile(body, camp, general, index) {
        const prefix = `${camp}-general-${index + 1}`;
        const p = general.profile;
        const controls = general.profileControls = {};
        function numberField(key, title, max) {
            const input = node("input");
            Object.assign(input, {id: `${prefix}-${key}`, type: "number", min: "0", step: "1", required: true, value: p[key]});
            if (max !== null) input.max = String(max);
            const label = node("label", title); label.htmlFor = input.id;
            const field = node("div"); field.append(label, input); controls[key] = input;
            return field;
        }
        const levelStep = node("section", undefined, "sim-step");
        levelStep.append(numberField("level", "2. Niveau", catalog.limits.level));
        levelStep.append(numberField("zombie_levels", "Niveaux après zombification", catalog.limits.level));
        const capabilities = node("select"); capabilities.id = `${prefix}-capabilities`;
        controls.capabilities = capabilities;
        const capabilitiesLabel = node("label", "Capacités spécifiques débloquées"); capabilitiesLabel.htmlFor = capabilities.id;
        levelStep.append(capabilitiesLabel, capabilities);
        general.refreshCapabilities = () => {
            const states = catalog.specific_states[p.nature]?.[p.level - p.zombie_levels] || [];
            capabilities.replaceChildren(...states.map(([slots, banner]) => {
                const option = node("option", `${slots} emplacement(s) actif(s) · étendard ${["absent", "normal", "royal"][banner]}`);
                option.value = `${slots},${banner}`; return option;
            }));
            const current = `${p.active_slots ?? 1},${p.banner_level ?? 0}`;
            if (states.some(pair => pair.join(",") === current)) capabilities.value = current;
            const pair = capabilities.value.split(",").map(Number);
            [p.active_slots, p.banner_level] = pair;
            capabilities.disabled = states.length <= 1;
        };
        general.refreshCapabilities();
        capabilities.addEventListener("change", () => { rememberGenerals(); update(); });
        const banner = node("select"); banner.id = `${prefix}-banner-block`; controls.banner_block = banner;
        for (const [value, title] of [["", "Aucun étendard placé"], ...Object.entries(blockNames)]) {
            const option = node("option", title); option.value = value; banner.append(option);
        }
        banner.value = general.banner_block || "";
        const bannerLabel = node("label", "Bloc portant l’étendard"); bannerLabel.htmlFor = banner.id;

        const trait = node("select"); trait.id = `${prefix}-trait`;
        for (const name of catalog.traits) {
            const option = node("option", name); option.value = name; trait.append(option);
        }
        trait.value = p.trait;
        const traitLabel = node("label", "Trait inné"); traitLabel.htmlFor = trait.id;
        trait.addEventListener("change", () => { p.trait = trait.value; });
        levelStep.append(traitLabel, trait);
        const rewardsPanel = node("details", undefined, "sim-level-rewards");
        rewardsPanel.open = true;
        rewardsPanel.append(node("summary", "Récompenses reçues par niveau"));
        general.rewardsContainer = node("div");
        general.rewardInfo = node("p", "", "sim-muted");
        rewardsPanel.append(general.rewardInfo, general.rewardsContainer);
        levelStep.append(rewardsPanel);
        renderRewardFields(general);
        const generate = node("button", "Générer un général à ce niveau", "sim-secondary");
        generate.type = "button"; generate.id = `${prefix}-generate`;
        const generationStatus = node("p", "", "sim-muted"); generationStatus.setAttribute("role", "status");
        generationStatus.id = `${prefix}-generation-status`;
        generate.addEventListener("click", async () => {
            if (busy || !controls.level.checkValidity() || !controls.zombie_levels.checkValidity()) return;
            rememberGenerals(); busy = true; generate.disabled = true;
            generationStatus.textContent = "Progression officielle en cours…";
            try {
                const request = general.typeChosen ? generationRequest(general) : {level: p.level, seed: null};
                const result = await engineRequest("generate", request);
                general.profile = {...result.profile, unlocked_evolutions: result.unlocked_evolutions, corpse_available: result.profile.zombie};
                general.orientation = result.profile.zombie ? "zombie" : result.profile.nature;
                general.typeChosen = true;
                general.rewards = Object.fromEntries(result.rewards.map(reward => [
                    reward.slot === "supplementaire" ? `${reward.level}:supplementaire` : reward.level,
                    {kind: reward.kind, value: reward.value}]));
                const totals = {pc: 0, morale: 0};
                for (const reward of result.rewards) {
                    if (reward.kind === "commandement") totals.pc += Number(reward.value);
                    if (reward.kind === "moral") totals.morale += Number(reward.value);
                }
                general.naturalStats = {pc: result.profile.pc - totals.pc, morale: result.profile.morale - totals.morale};
                general.appliedRewardStats = totals;
                general.uiStep = 6;
                renderGenerals();
                $(`${prefix}-generation-status`).textContent = `Profil généré · graine ${result.seed}.`;
            } catch (error) { generationStatus.textContent = error.message; }
            finally { busy = false; generate.disabled = false; update(); }
        });
        levelStep.append(generate, generationStatus);
        body.append(levelStep);
        const continueLevel = node("button", "Valider le niveau et les récompenses", "sim-secondary");
        continueLevel.type = "button";
        continueLevel.addEventListener("click", () => {
            if (!controls.level.checkValidity() || !controls.zombie_levels.checkValidity()) return;
            for (const reward of Object.values(general.rewards)) {
                if (reward.kind && !reward.value) {
                    general.rewardInfo.textContent = "Complétez les récompenses sélectionnées avant de continuer.";
                    return;
                }
            }
            general.uiStep = Math.max(3, general.uiStep);
            update();
        });
        levelStep.append(continueLevel);
        controls.level.addEventListener("change", () => {
            if (controls.level.checkValidity()) {
                p.level = Number(controls.level.value);
                p.zombie_levels = p.zombie ? Math.min(p.level, p.zombie_levels) : 0;
                controls.zombie_levels.value = p.zombie_levels;
                general.refreshCapabilities();
                for (const level of Object.keys(general.rewards))
                    if (parseInt(level) > p.level || parseInt(level) === 0) delete general.rewards[level];
                renderRewardFields(general);
                syncRewardSelections(general);
                general.uiStep = Math.max(3, general.uiStep);
                update();
            }
        });
        controls.zombie_levels.addEventListener("change", () => {
            if (!controls.zombie_levels.checkValidity()) return;
            p.zombie_levels = Number(controls.zombie_levels.value);
            general.refreshCapabilities();
            renderRewardFields(general);
            syncRewardSelections(general);
            update();
        });
        const statsStep = node("section", undefined, "sim-step");
        statsStep.append(node("h3", "3. Statistiques du général"));
        body.append(statsStep);
        const randomStats = node("button", "Tirer les gains naturels", "sim-secondary");
        randomStats.type = "button";
        const statsStatus = node("p", "", "sim-muted"); statsStatus.setAttribute("role", "status");
        randomStats.id = `${prefix}-natural`;
        randomStats.addEventListener("click", async () => {
            if (!controls.level.checkValidity() || !controls.zombie_levels.checkValidity()) return;
            rememberGenerals();
            const request = generationRequest(general);
            randomStats.disabled = true;
            statsStatus.textContent = "Calcul des gains naturels…";
            try {
                const result = await engineRequest("natural", request);
                if (!randomStats.isConnected || JSON.stringify(request) !== JSON.stringify(generationRequest(general))) return;
                general.naturalStats = {pc: result.pc, morale: result.morale};
                syncRewardSelections(general);
                update();
                statsStatus.textContent = "Gains naturels tirés ; récompenses conservées.";
            } catch (error) { statsStatus.textContent = error.message; }
            finally { randomStats.disabled = false; }
        });
        statsStep.append(randomStats, statsStatus);
        const grid = node("div", undefined, "sim-options-grid");
        grid.append(numberField("pc", "Points de commandement (PC)", catalog.limits.pc),
            numberField("morale", "Moral", catalog.limits.morale));
        for (const key of ["pc", "morale"]) controls[key].addEventListener("change", () => {
            general.naturalStats[key] = Number(controls[key].value) - general.appliedRewardStats[key];
        });
        statsStep.append(grid);
        statsStep.append(node("p", "Le tirage calcule uniquement les gains naturels selon le type et le niveau, puis ajoute les récompenses déjà choisies au point 2. Il ne change aucune récompense.", "sim-muted"));
        const continueStats = node("button", "Continuer", "sim-secondary");
        continueStats.type = "button";
        continueStats.addEventListener("click", () => {
            const canHaveQG = !p.zombie && ["stratege", "hybride"].includes(p.nature);
            general.uiStep = Math.max((canHaveQG || !p.zombie && p.banner_level) ? 4 : (earnedRewardLabels(general).length ? 5 : 6), general.uiStep);
            update();
        });
        statsStep.append(continueStats);
        general.continueStats = continueStats;
        const qgStep = node("section", undefined, "sim-step");
        general.qgStep = qgStep;
        qgStep.append(node("h3", "4. QG et étendard"));
        const qg = node("input"); Object.assign(qg, {type: "checkbox", id: `${prefix}-qg`, checked: general.qg});
        controls.qg = qg;
        const qgLabel = node("label", "Quartier général du camp"); qgLabel.htmlFor = qg.id;
        const qgField = node("div", undefined, "sim-check"); qgField.append(qg, qgLabel); general.qgField = qgField;
        qg.addEventListener("change", () => {
            if (qg.checked) for (const other of armies[camp]) if (other !== general) other.profileControls.qg.checked = false;
        });
        const placement = node("div"); general.qgPlacement = placement;
        const block = node("select"); block.id = `${prefix}-qg-block`; general.qgBlockInput = block;
        for (const name of ["avant", "arriere", "gauche", "droite"]) {
            const option = node("option", blockNames[name]); option.value = name; block.append(option);
        }
        block.value = general.qgBlock;
        const blockLabel = node("label", "Bloc du QG"); blockLabel.htmlFor = block.id;
        placement.append(blockLabel, block, node("p", "Le QG reste un rôle du général. Ce placement ne crée aucun bonus propre au bloc ; les effets globaux suivent le moteur officiel.", "sim-muted"));
        qgStep.append(qgField, placement, bannerLabel, banner);
        const rules = node("a", "Règles des généraux et des étendards");
        rules.href = "bestiaire.html#generaux";
        qgStep.append(rules);
        const nextQG = node("button", "Continuer vers les étiquettes", "sim-secondary");
        general.nextQG = nextQG;
        nextQG.type = "button";
        nextQG.addEventListener("click", () => {
            general.uiStep = Math.max(earnedRewardLabels(general).length ? 5 : 6, general.uiStep);
            update();
        });
        qgStep.append(nextQG); body.append(qgStep);
        const details = node("details", undefined, "sim-labels");
        details.open = general.labelsOpen ?? true; general.labelsPanel = details;
        general.labelsSummary = node("p", "", "sim-muted");
        details.append(node("summary", "5. Étiquettes et rangs"), general.labelsSummary,
            node("p", "Sélectionnez une étiquette et choisissez son rang pour appliquer son effet au combat. Décochez-la pour retirer son effet."));
        general.labelControls = {};
        for (const name of Object.keys(catalog.labels)) {
            const row = node("div", undefined, "sim-label-row");
            const active = node("input"); Object.assign(active, {type: "checkbox", id: `${prefix}-label-${name}-active`, checked: p.active.includes(name)});
            const label = node("label", name.replaceAll("_", " ")); label.htmlFor = active.id;
            const rank = node("input"); Object.assign(rank, {type: "number", min: "1", max: catalog.label_rank_max[p.level], step: "1", required: true, value: p.labels[name] || 1, id: `${prefix}-label-${name}`});
            const rankLabel = node("label", "Rang"); rankLabel.htmlFor = rank.id;
            rank.setAttribute("aria-label", "Rang de " + name.replaceAll("_", " "));
            const effect = catalog.labels[name];
            const relatedUnits = catalog.units.filter(unit => catalog.unit_details[unit]?.etiquettes?.includes(name));
            const unitNamesText = relatedUnits.map(unit => unitNames[unit] || unit.replaceAll("_", " ")).join(", ");
            const hint = node("small", unitNamesText ? "Unités : " + unitNamesText : (typeof effect === "string" ? effect : ""), "sim-muted");
            row.append(active, label, rankLabel, rank, hint);
            general.labelControls[name] = {rank, active, row}; details.append(row);
        }
        syncRewardSelections(general);
        

        const labelStep = node("section", undefined, "sim-step");
        general.labelStep = labelStep;
        labelStep.append(details);
        const nextLabels = node("button", "Continuer vers la composition", "sim-secondary");
        nextLabels.type = "button";
        nextLabels.addEventListener("click", () => { general.uiStep = Math.max(6, general.uiStep); update(); });
        labelStep.append(nextLabels); body.append(labelStep);

    }

    function buildGeneral(camp, general, index) {
        const details = node("details", undefined, "sim-general");
        details.open = general.open;
        details.dataset.generalId = general.id;
        details.dataset.position = general.position;
        const summary = node("summary");
        const summaryText = node("small");
        summary.append(node("span", `Général ${index + 1}`), summaryText);
        const body = node("div", undefined, "sim-general-body");
        const position = node("select");
        position.id = `${camp}-general-${index + 1}-position`;
        for (let value = 1; value <= maxActivePositions; value++) {
            const occupied = armies[camp].find(g => g !== general && g.position === value);
            const option = node("option", `Position ${value}${occupied ? " — permuter" : ""}`);
            option.value = value;
            position.append(option);
        }
        position.value = general.position;
        const positionLabel = node("label", "Position active");
        positionLabel.htmlFor = position.id;
        position.addEventListener("change", () => {
            rememberGenerals();
            const value = Number(position.value);
            const occupied = armies[camp].find(g => g !== general && g.position === value);
            if (occupied) occupied.position = general.position;
            general.position = value;
            renderGenerals();
            $(position.id).focus();
        });
        const placement = node("div"); placement.append(positionLabel, position);
        const orientation = node("select");
        orientation.id = `${camp}-general-${index + 1}-orientation`;
        for (const [value, name] of Object.entries(orientations)) {
            const option = node("option", name);
            option.value = value;
            orientation.append(option);
        }
        const placeholder = node("option", "Choisir un type…");
        placeholder.value = "";
        placeholder.disabled = true;
        orientation.prepend(placeholder);
        orientation.value = general.typeChosen ? general.orientation : "";
        const label = node("label", "1. Type de général");
        label.htmlFor = orientation.id;
        const help = node("p", "Profil synthétique modifiable. Les PC ne sont pas recalculés lorsque vous changez le niveau ; utilisez la génération pour obtenir une progression officielle.", "sim-muted");
        help.id = `${orientation.id}-help`;
        orientation.setAttribute("aria-describedby", help.id);
        body.append(label, orientation, help);
        orientation.addEventListener("change", () => {
            if (general.orientation !== orientation.value) {
                general.rewards = {};
                general.appliedRewardStats = {pc: 0, morale: 0};
                general.naturalStats = {pc: 0, morale: 0};
                general.qg = false;
                general.profile.labels = {};
                general.profile.active = [];
                general.profile.permanent = [];
                general.profile.unlocked_evolutions = [];
                general.profile.pc = 0;
                general.profile.morale = 0;
                general.profile.zombie_levels = 0;
                general.profile.trait = "leader";
                general.questHeavyCavalry = false;
                for (const block of catalog.blocks) {
                    general.blocks[block] = {unit: "archer", count: "0", messengers: 0, shield: false};
                }
                general.orientation = orientation.value;
                general.profile.zombie = orientation.value === "zombie";
                if (!general.profile.zombie) general.profile.nature = orientation.value;
                else general.profile.nature = "stratege";
                general.typeChosen = true;
                general.uiStep = 2;
                renderGenerals();
                return;
            }
            general.typeChosen = true;
            general.orientation = orientation.value;
            general.uiStep = Math.max(2, general.uiStep);
            update();
        });
        buildProfile(body, camp, general, index);
        const compositionStep = node("section", undefined, "sim-step");
        compositionStep.append(placement, node("h3", "6. Composition des unités"));
        general.unitHelp = node("p", "", "sim-muted"); compositionStep.append(general.unitHelp);
        const quest = node("label", "Cavalerie lourde débloquée par quête", "sim-check");
        const questCheck = node("input");
        questCheck.type = "checkbox";
        questCheck.checked = general.questHeavyCavalry;
        questCheck.addEventListener("change", () => {
            general.questHeavyCavalry = questCheck.checked;
            update();
        });
        quest.prepend(questCheck);
        compositionStep.append(quest);
        const random = node("button", "Composition aléatoire", "sim-secondary sim-random-general");
        random.id = `${camp}-general-${index + 1}-random`;
        random.type = "button";
        random.setAttribute("aria-label", `Composition aléatoire pour le général ${index + 1} du camp ${camp}`);
        random.setAttribute("aria-describedby", `random-help-${camp}`);
        random.addEventListener("click", () => randomize(camp, [general], random.id));
        compositionStep.append(random);
        const grid = node("div", undefined, "sim-formation");
        general.controls = {};
        for (const block of catalog.blocks) {
            // Conserver les identifiants historiques pour le premier général.
            const prefix = index === 0 ? `${camp}-${block}` : `${camp}-${index + 1}-${block}`;
            const fieldset = node("fieldset", undefined, `sim-block sim-block-${block}`);
            fieldset.append(node("legend", blockNames[block]));
            const select = node("select");
            select.id = `${prefix}-unit`;
            const unitLabel = node("label", "Unité");
            unitLabel.htmlFor = select.id;
            for (const unit of catalog.units.filter(u => !["messager_du_QG", "Trop_gros_zombie"].includes(u))) {
                const option = node("option", unitNames[unit] || unit);
                option.value = unit;
                select.append(option);
            }
            select.value = general.blocks[block].unit;
            const input = node("input");
            input.id = `${prefix}-count`;
            input.type = "number";
            input.min = "0";
            input.max = "120";
            input.step = "1";
            input.required = true;
            input.value = general.blocks[block].count;
            const countLabel = node("label", "Effectif");
            countLabel.htmlFor = input.id;
            const hint = node("small", "", "sim-muted");
            hint.id = `${prefix}-hint`;
            input.setAttribute("aria-describedby", hint.id);
            const messengers = node("input");
            Object.assign(messengers, {type: "number", min: "0", max: "4", step: "1", value: general.blocks[block].messengers || 0, id: `${prefix}-messengers`});
            const messengerLabel = node("label", "Messagers (5 places chacun)");
            messengerLabel.htmlFor = messengers.id;
            const shield = node("input");
            Object.assign(shield, {type: "checkbox", checked: general.blocks[block].shield || false, id: `${prefix}-shield`});
            const shieldLabel = node("label", "Gros zombie (10 places)");
            shieldLabel.htmlFor = shield.id;
            const messengerField = node("div"); messengerField.append(messengerLabel, messengers);
            const shieldField = node("div", undefined, "sim-check"); shieldField.append(shield, shieldLabel);
            fieldset.append(unitLabel, select, countLabel, input, hint, messengerField, shieldField);
            grid.append(fieldset);
            general.controls[block] = {unit: select, count: input, hint, messengers, shield, messengerField, shieldField};
        }
        compositionStep.append(grid);
        const extras = node("details", undefined, "sim-optional");
        extras.append(node("summary", "7. Paramètres facultatifs : blessures, vétéran, fatigue…"),
            node("p", "Ces paramètres seront disponibles lorsque leur transmission au moteur sera prise en charge.", "sim-muted"));
        body.append(compositionStep, extras);
        const remove = node("button", "Retirer ce général", "sim-secondary sim-remove");
        remove.type = "button";
        remove.setAttribute("aria-label", `Retirer le général ${index + 1} du camp ${camp}`);
        remove.addEventListener("click", () => {
            if (armies[camp].length <= 1) return;
            rememberGenerals();
            armies[camp] = armies[camp].filter(item => item.id !== general.id);
            renderGenerals();
            $(`add-${camp}`).focus();
        });
        body.append(remove);
        details.append(summary, body);
        Object.assign(general, {element: details, orientationInput: orientation, summary: summaryText, removeButton: remove,
            steps: Array.from(body.querySelectorAll(":scope > .sim-step")), extras});
        return details;
    }

    function renderGenerals() {
        for (const camp of camps) {
            $(`generals-${camp}`).replaceChildren(...armies[camp].map((general, index) => buildGeneral(camp, general, index)));
        }
        update();
    }

    function buildArmies() {
        for (const camp of camps) {
            armies[camp] = [newGeneral(camp, true)];
            const army = node("details", undefined, `sim-panel sim-config-panel sim-army sim-camp-${camp.toLowerCase()}`);
            army.id = `camp-${camp}`;
            army.open = true;
            const summary = node("summary");
            const total = node("small", "", "sim-total");
            total.id = `total-${camp}`;
            total.setAttribute("aria-live", "polite");
            summary.append(node("span", `Camp ${camp}`), total);
            const body = node("div", undefined, "sim-panel-body");
            body.append(node("p", camp === "A" ? "Généraux alliés" : "Généraux adverses", "sim-muted"));
            const list = node("div");
            list.id = `generals-${camp}`;
            const add = node("button", "Ajouter un général", "sim-secondary");
            add.id = `add-${camp}`;
            add.type = "button";
            add.addEventListener("click", () => {
                if (armies[camp].length >= maxActivePositions) return;
                rememberGenerals();
                const general = newGeneral(camp);
                armies[camp].push(general);
                renderGenerals();
                general.element.querySelector("summary").focus();
            });
            const randomLabel = node("label", "Soldats par général (tirage aléatoire)");
            randomLabel.htmlFor = `random-count-${camp}`;
            const randomCount = node("select");
            randomCount.id = randomLabel.htmlFor;
            const automatic = node("option", "Aléatoire : 1 à 20 soldats");
            automatic.value = "auto";
            randomCount.append(automatic);
            for (let count = 1; count <= catalog.max_units; count++) {
                const option = node("option", `${count} ${count === 1 ? "soldat" : "soldats"}`);
                option.value = String(count);
                randomCount.append(option);
            }
            
            const random = node("button", "Remplir le camp aléatoirement", "sim-secondary");
            random.type = "button";
            random.id = `random-${camp}`;
            random.setAttribute("aria-label", `Remplir le camp ${camp} aléatoirement`);
            random.setAttribute("aria-describedby", `random-help-${camp}`);
            random.addEventListener("click", () => randomize(camp, armies[camp], random.id));
            const actions = node("div", undefined, "sim-actions");
            actions.append(add, random);
            const help = node("p", "Le nombre choisi s'applique à chaque général généré, individuellement ou pour tout le camp. Les blocs existants sont remplacés directement, sans confirmation. La graine de combat ne change pas.", "sim-muted");
            help.id = `random-help-${camp}`;
            const status = node("p", "", "sim-muted");
            status.id = `random-status-${camp}`;
            status.setAttribute("role", "status");
            const randomControls = node("div", undefined, "sim-random-settings");
            randomControls.append(randomLabel, randomCount);
            body.append(list, actions, randomControls, help, status);
            army.append(summary, body);
            $("armies").append(army);
        }
        renderGenerals();
    }

    function updateLayout() {
        const vertical = mobile.matches || verticalLayout;
        document.querySelector(".simulator").dataset.layout = vertical ? "vertical" : "horizontal";
        const label = mobile.matches ? "Disposition verticale sur petit écran" : `Afficher les camps ${vertical ? "horizontalement" : "verticalement"}`;
        $("layout-button").disabled = mobile.matches;
        $("layout-button").setAttribute("aria-label", label);
        $("layout-button").setAttribute("aria-pressed", String(vertical));
        $("layout-button").title = label;
        $("layout-icon").textContent = vertical ? "▤" : "▥";
    }

    function describe(counts) {
        return Object.entries(counts).map(([type, count]) => `${count} ${unitNames[type] || type}`).join(", ") || "Vide";
    }

    function combatText(tag, text, className) {
        const element = node(tag, undefined, className);
        // Texte uniquement : préserver exactement le rapport, sans interpréter du HTML.
        const tokens = /\b(?:j1|bot|allies)(?: general\d+)?\b|\bcamp [AB]\b|\b(?:avant|droite|gauche|arriere|arrière)\b/gi;
        let cursor = 0;
        for (const match of text.matchAll(tokens)) {
            element.append(document.createTextNode(text.slice(cursor, match.index)));
            const token = match[0].toLowerCase();
            if (/^(j1|camp a)\b/.test(token)) element.append(node("span", match[0], "sim-log-camp-a"));
            else if (/^(j2|camp b)\b/.test(token)) element.append(node("span", match[0], "sim-log-camp-b"));
            else element.append(node("strong", match[0], "sim-log-block"));
            cursor = match.index + match[0].length;
        }
        element.append(document.createTextNode(text.slice(cursor)));
        return element;
    }

    function phaseDetail(detail, isShock, engagement) {
        const row = node("li");
        const one = isShock ? "1" : "attaquant";
        const two = isShock ? "2" : "defenseur";
        const actor = isShock ? engagement.joueur_1 : detail.joueur_attaquant;
        const firstCamp = actor === "j1" ? "A" : "B";
        const secondCamp = firstCamp === "A" ? "B" : "A";
        row.append(combatText("p", `${isShock ? "Choc" : `Tour ${detail.tour}, action ${detail.numero}`} : camp ${firstCamp}, ${blockNames[detail[`bloc_${one}`]]} ↔ camp ${secondCamp}, ${blockNames[detail[`bloc_${two}`]]}`));
        for (const [key, camp] of [[one, firstCamp], [two, secondCamp]]) {
            const initial = detail[`initial_${key}`];
            const final = detail[`final_${key}`];
            const values = detail.values[key];
            row.append(node("p", `${camp} · ${unitNames[detail[`type_${key}`]] || detail[`type_${key}`]} : ${initial} → ${final} (variation ${final - initial}). Valeur de base ${values.base}, avantage de type ×${values.advantage}.`, "sim-muted"));
        }
        return row;
    }

    function render(result) {
        $("results-panel").open = true;
        $("results").hidden = false;
        $("result-summary").replaceChildren();
        const outcomes = {A: "Victoire du camp A", B: "Victoire du camp B", mutual_destruction: "Destruction mutuelle — aucun vainqueur", contested: "Issue indécise — les deux camps restent présents"};
        $("results-caption").dataset.outcome = `Dernier combat ${result.before.A.generals.length} contre ${result.before.B.generals.length} : ${outcomes[result.outcome]} · ${result.after.A.total + result.after.B.total} unités survivantes`;
        $("results-caption").textContent = $("results-caption").dataset.outcome;
        $("result-summary").append(node("p", outcomes[result.outcome], "sim-outcome"));
        if (result.battle_resolution?.impasse) {
            const retreating = result.battle_resolution.camps_retraite.map(camp => camp === "j1" ? "A" : "B").join(" et ");
            $("result-summary").append(node("p", `Impasse à valeurs nulles, sans pertes artificielles. Retraite requise : camp(s) ${retreating}. La carte et les destinations ne sont pas simulées : retraite physique non résolue, survivants conservés et territoire encore contesté.`, "sim-note"));
        }
        for (const camp of camps) $("result-summary").append(node("p", `Camp ${camp} : variation nette ${-result.losses[camp]} unités, ${result.after[camp].total} restantes (créations comprises). Généraux : ${result.after[camp].surviving_generals} survivants, ${result.after[camp].destroyed_generals} détruits sur ${result.before[camp].generals.length}.`));
        for (const qg of result.qg_initial) if (qg) $("result-summary").append(node("p", `QG initial ${qg.qg.join(" / ")} : ${qg.pc_initial} PC personnels + ${qg.bonus_messager} via Messager = ${qg.pc_global} PC globaux. Soutien figé, interrompu à sa destruction ; aucun remplacement.`));
        const saves = result.saves || [];
        $("result-summary").append(node("p", `Sauvetages par le moral : ${saves.filter(s => s.kind === "morale").length} · par étendard : ${saves.filter(s => s.kind === "banner").length}. Charges restantes détaillées dans le journal.`));
        $("result-summary").append(node("p", `Soins de victoire du Chaman : ${result.healed_by_shaman} soldats traités. Les bonus exacts figurent dans le journal.`));
        const mode = result.conditions.mode + (result.conditions.defender ? ` · camp ${result.conditions.defender} défenseur` : "");
        $("result-meta").textContent = `Graine ${result.seed} · Moteur V2.0 ${result.engine_revision || result.engine_commit.slice(0, 12)} · Python ${result.python_version} · ${mode}, sans fatigue · ${result.conditions.orders.length ? "ordre actif" : "sans ordre"}`;
        $("block-results").replaceChildren();
        for (const camp of camps) {
            const container = node("div", undefined, `sim-camp-${camp.toLowerCase()}`);
            container.append(node("h4", `Camp ${camp}`));
            for (const [index, general] of result.before[camp].generals.entries()) {
                const finalGeneral = result.after[camp].generals[index];
                const generalDetails = node("details", undefined, "sim-general sim-general-result");
                const engaged = result.engagements.filter(e => e.participants.some(p => p.owner === (camp === "A" ? "j1" : "j2") && p.name === general.name)).length;
                generalDetails.append(node("summary", `Général ${index + 1} · position ${general.position} · ${finalGeneral.alive ? "survivant" : "détruit"} · variation nette ${finalGeneral.total - general.total} · ${finalGeneral.total} unités restantes · ${engaged} engagements`));
                const grid = node("div", undefined, "sim-formation sim-general-body");
                for (const block of catalog.blocks) {
                    const card = node("div", undefined, `sim-block sim-block-${block}`);
                    const before = general.blocks[block];
                    const after = finalGeneral.blocks[block];
                    const initial = Object.values(before).reduce((a, b) => a + b, 0);
                    const final = Object.values(after).reduce((a, b) => a + b, 0);
                    card.append(node("strong", blockNames[block]), node("p", `Avant : ${describe(before)}`), node("p", `Après : ${describe(after)}`));
                    const health = result.health[camp][index].blocks[block];
                    const preHealing = result.health_before_healing[camp][index].blocks[block];
                    card.append(node("p", `${health.destroyed} soldats détruits · ${health.created} créés · ${health.converted} conversions reçues · ${preHealing.wounded} blessés avant soins, ${health.wounded} après soins (${health.wounds} blessures).`));
                    const bar = node("meter");
                    bar.min = 0;
                    bar.max = Math.max(1, initial);
                    bar.value = final;
                    bar.setAttribute("aria-label", `${camp}, général ${index + 1}, ${blockNames[block]} : ${final} survivants sur ${initial}`);
                    card.append(bar);
                    grid.append(card);
                }
                generalDetails.append(grid);
                container.append(generalDetails);
            }
            $("block-results").append(container);
        }
        $("phases").replaceChildren();
        result.engagements.forEach((engagement, index) => {
            const container = node("details", undefined, "sim-phase");
            container.open = index === 0;
            const labels = engagement.participants.map(p => `Camp ${p.owner === "j1" ? "A" : "B"}, ${p.name.replace("general", "général ")} (position ${p.position})`);
            container.append(node("summary", `Engagement ${index + 1} · ${engagement.phase === "frontal" ? "frontal" : "rangé"} · ${labels.join(" contre ")}`));
            container.append(node("p", `A : ${engagement.initial_1} → ${engagement.final_1} unités · B : ${engagement.initial_2} → ${engagement.final_2} unités.`));
            for (const [title, entries, shock] of [["Choc initial", engagement.chocs, true], ["Manœuvres", engagement.manoeuvres, false]]) {
                container.append(node("h4", title));
                if (!entries.length) container.append(node("p", "Aucune confrontation dans cette phase."));
                const list = node("ol");
                entries.forEach(detail => list.append(phaseDetail(detail, shock, engagement)));
                container.append(list);
            }
            $("phases").append(container);
        });
        renderJournal(result);
        $("results-title").focus({preventScroll: true});
        $("results").scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "start"});
    }

    function renderJournal(result) {
        const journal = $("journal");
        journal.replaceChildren();
        const lines = result.journal.match(/[^\n]*\n|[^\n]+$/g) || [];
        let cursor = 0;
        for (const explanation of result.explanations) {
            if (explanation.line > cursor) journal.append(combatText("pre", lines.slice(cursor, explanation.line).join("")));
            const detail = node("details", undefined, "sim-explanation");
            detail.append(node("summary", `ⓘ ${explanation.title}`), node("p", explanation.text));
            journal.append(detail);
            cursor = explanation.line;
        }
        if (cursor < lines.length) journal.append(combatText("pre", lines.slice(cursor).join("")));
    }

    function edited() {
        $("run-error").hidden = true;
        update();
    }
    $("simulation-form").addEventListener("input", edited);
    $("simulation-form").addEventListener("change", edited);
    $("swap-button").addEventListener("click", () => {
        rememberGenerals();
        [armies.A, armies.B] = [armies.B, armies.A];
        if ($("combat-mode").value === "OFF/DEF") $("defender").value = $("defender").value === "A" ? "B" : "A";
        for (const camp of camps) $(`random-status-${camp}`).textContent = "";
        renderGenerals();
    });
    $("layout-button").addEventListener("click", () => { verticalLayout = !verticalLayout; updateLayout(); });
    mobile.addEventListener("change", updateLayout);
    $("reuse-seed").addEventListener("click", () => {
        $("seed").value = lastResult.seed;
        $("seed-mode").value = "fixed";
        $("advanced-panel").open = true;
        update();
        $("seed").focus();
    });
    $("simulation-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        if (busy) return;
        showErrors = true;
        update();
        if (configurationErrors.length) return;
        busy = true;
        const payload = configuration();
        const signature = battleSignature();
        $("run-error").hidden = true;
        $("run-button").textContent = "Combat en cours…";
        $("service-status").textContent = "Le moteur résout le combat…";
        $("results").setAttribute("aria-busy", "true");
        update();
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 15000);
        try {
            const response = await fetch("/api/simulator/run", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload), signal: controller.signal});
            if (!(response.headers.get("content-type") || "").includes("application/json")) throw new Error("Le serveur de simulation ne répond pas. Ouvrez cette page depuis le serveur Python du projet.");
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || "La simulation a échoué.");
            lastResult = result;
            submittedConfiguration = signature;
            if (battleSignature() === signature) {
                document.querySelectorAll(".sim-config-panel").forEach(panel => { panel.open = false; });
            }
            render(result);
            $("service-status").textContent = "Combat terminé. Vous pouvez modifier les formations et relancer.";
        } catch (error) {
            $("run-error").textContent = error.name === "AbortError" ? "Le serveur n’a pas répondu à temps. Vos compositions sont conservées." : error.message;
            $("run-error").hidden = false;
            $("service-status").textContent = "La simulation n’a pas abouti.";
        } finally {
            clearTimeout(timeout);
            busy = false;
            $("run-button").textContent = "Lancer le combat";
            $("results").setAttribute("aria-busy", "false");
            update();
        }
    });

    async function start() {
        try {
            const response = await fetch("/api/simulator/catalog", {signal: AbortSignal.timeout(10000)});
            if (!response.ok || !(response.headers.get("content-type") || "").includes("application/json")) throw new Error(`Catalogue indisponible (HTTP ${response.status}).`);
            catalog = await response.json();
            const options = await fetch("/api/simulator/options", {method: "POST", headers: {"Content-Type": "application/json"}, body: "{}", signal: AbortSignal.timeout(15000)});
            if (!options.ok) {
                const reason = await options.json().catch(() => ({}));
                throw new Error(`Options du moteur indisponibles (HTTP ${options.status}) : ${reason.error || "Réponse inattendue"}`);
            }
            catalog.options = await options.json();
            for (const unit of catalog.units) unitNames[unit] ||= unit.replaceAll("_", " ");
            buildArmies();
            $("simulation-form").hidden = false;
            $("service-status").textContent = "Configurez votre duel. Vous pouvez replier et rouvrir chaque panneau.";
            $("engine-version").textContent = `Moteur officiel V2.0 · ${catalog.engine_commit.slice(0, 12)} · OFF/OFF et OFF/DEF, sans fatigue · jusqu’à ${catalog.max_generals_per_camp} généraux actifs par camp.`;
            $("layout-button").hidden = false;
            updateLayout();
            update();
        } catch (error) {
            console.error("Initialisation du simulateur Mythodea :", error);
            $("service-status").className = "sim-error";
            $("service-status").textContent = `Échec de l’initialisation du simulateur : ${error.message || String(error)}. Vérifiez le terminal du serveur et rechargez la page.`;
        }
    }
    start();
})();
