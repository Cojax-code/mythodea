"use strict";

(() => {
    const $ = (id) => document.getElementById(id);
    const unitNames = {archer: "Archers", piquier: "Piquiers", cavalier: "Cavaliers", cavalerie_lourde: "Cavalerie lourde"};
    const blockNames = {avant: "Avant", droite: "Droite", gauche: "Gauche", arriere: "Arrière"};
    const camps = ["A", "B"];
    const orientations = {stratege: "Stratège", instinctif: "Instinctif", stratege_hybride: "Stratège hybride", instinctif_hybride: "Instinctif hybride"};
    const maxActivePositions = 4;
    const armies = {A: [], B: []};
    const mobile = matchMedia("(max-width: 800px)");
    let nextGeneralId = 1;
    let verticalLayout = false;
    let catalog;
    let busy = false;
    let lastResult = null;
    let submittedConfiguration = null;

    function node(tag, text, className) {
        const element = document.createElement(tag);
        if (text !== undefined) element.textContent = text;
        if (className) element.className = className;
        return element;
    }

    function newGeneral(camp, initial = false) {
        const position = [1, 2, 3, 4].find(value => !armies[camp].some(g => g.position === value));
        return {id: nextGeneralId++, position, open: true, orientation: "stratege", qg: false,
            profile: {level: 0, nature: "stratege", trait: "leader", pc: 0, morale: 0, labels: {}, permanent: [], active: [], zombie: false, zombie_levels: 0},
            blocks: Object.fromEntries(catalog.blocks.map(block => [block, {
                unit: camp === "A" ? "archer" : "piquier", count: initial && block === "avant" ? "20" : "0"
            }]))};
    }

    function rememberGenerals() {
        for (const camp of camps) for (const general of armies[camp]) {
            if (!general.element) continue;
            general.open = general.element.open;
            general.orientation = general.orientationInput.value;
            const p = general.profile;
            p.nature = general.orientation;
            for (const key of ["level", "pc", "morale", "zombie_levels"]) p[key] = Number(general.profileControls[key].value);
            p.trait = general.profileControls.trait.value;
            p.zombie = general.profileControls.zombie.checked;
            general.qg = general.profileControls.qg.checked;
            p.labels = {}; p.permanent = []; p.active = [];
            for (const [name, inputs] of Object.entries(general.labelControls)) {
                const rank = Number(inputs.rank.value);
                if (rank > 0) {
                    p.labels[name] = rank;
                    if (inputs.active.checked) p.active.push(name);
                    if (inputs.permanent.checked) p.permanent.push(name);
                }
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
        const units = catalog.units.filter(unit => !["messager_du_QG", "Trop_gros_zombie"].includes(unit) && compatible(unit, general.profile));
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
                position: general.position, qg: general.qg, profile: general.profile, blocks: combatBlocks(general)
            }))}])),
            seed: seedValue(),
            mode: $("combat-mode").value,
            defender: $("combat-mode").value === "OFF/DEF" ? $("defender").value : null
        };
    }

    function update() {
        if (!catalog) return;
        rememberGenerals();
        const defensive = $("combat-mode").value === "OFF/DEF";
        $("defender-field").hidden = !defensive;
        $("defender").disabled = !defensive;
        let valid = true;
        for (const camp of camps) {
            let campTotal = 0;
            for (const general of armies[camp]) {
                let total = 0;
                let generalValid = true;
                for (const block of catalog.blocks) {
                    const {count: input, hint} = general.controls[block];
                    const count = Number(input.value);
                    generalValid = generalValid && input.value !== "" && input.checkValidity() && Number.isInteger(count);
                    total += (Number.isFinite(count) ? count : 0) * catalog.unit_details[general.blocks[block].unit].places + 5 * Number(general.controls[block].messengers.value) + 10 * general.controls[block].shield.checked;
                    generalValid = generalValid && (count === 0 || compatible(general.blocks[block].unit, general.profile));
                    generalValid = generalValid && (Number(general.controls[block].messengers.value) === 0 || compatible("messager_du_QG", general.profile));
                    generalValid = generalValid && general.controls[block].messengers.value !== "" && general.controls[block].messengers.checkValidity();
                    const heavy = general.blocks[block].unit === "cavalerie_lourde" && count > 0;
                    hint.textContent = heavy
                        ? (block === "avant" && count >= 15 ? "Formation lourde : seuil de 15 atteint." : "Cavalerie lourde : sans bonus de formation.")
                        : (count === 0 ? "Bloc vide" : "");
                }
                const capacity = general.profile.zombie ? 20 + 2 * general.profile.zombie_levels : 20;
                const maxActive = activeLimit(general.profile);
                generalValid = generalValid && total >= 1 && total <= capacity && general.profile.active.length <= maxActive;
                generalValid = generalValid && Object.values(general.profileControls).every(input => input.checkValidity());
                for (const [name, inputs] of Object.entries(general.labelControls)) {
                    inputs.rank.max = catalog.label_rank_max[general.profile.level] || 1;
                    inputs.active.disabled = Number(inputs.rank.value) === 0 || (!inputs.active.checked && general.profile.active.length >= maxActive);
                    generalValid = generalValid && inputs.rank.checkValidity() && (!inputs.permanent.checked || Number(inputs.rank.value) === 1);
                }
                general.labelsSummary.textContent = `${general.profile.active.length} / ${maxActive} actives · permanentes : rang 1 · validation des connaissances par le moteur`;
                valid = valid && generalValid;
                campTotal += total;
                general.summary.textContent = `Position ${general.position} · ${total} / ${capacity} places · N${general.profile.level} · ${general.profile.pc} PC · ${orientations[general.orientation]}${general.qg ? " · QG" : ""}${generalValid ? "" : " · saisie à vérifier"}`;
                general.summary.classList.toggle("sim-error", !generalValid);
                general.removeButton.disabled = armies[camp].length === 1;
            }
            const count = armies[camp].length;
            $(`total-${camp}`).textContent = `${count} ${count === 1 ? "général" : "généraux"} · ${campTotal} unités · ${count} / ${maxActivePositions} positions`;
            $(`add-${camp}`).disabled = count >= maxActivePositions;
        }
        const fixedSeed = $("seed-mode").value === "fixed";
        $("fixed-seed").hidden = !fixedSeed;
        $("seed").disabled = !fixedSeed;
        valid = valid && (!fixedSeed || ($("seed").value !== "" && $("seed").checkValidity()));
        $("validation").textContent = valid ? "" : "Vérifiez les capacités, la compatibilité des unités, les étiquettes et les valeurs saisies.";
        $("run-button").disabled = busy || !valid;
        $("advanced-summary").textContent = fixedSeed ? `Graine fixe : ${$("seed").value || "à renseigner"}` : "Réglages automatiques";
        if (lastResult) {
            const stale = battleSignature() !== submittedConfiguration;
            $("result-stale").hidden = !stale;
            $("results-caption").textContent = `${$("results-caption").dataset.outcome}${stale ? " · configuration modifiée" : ""}`;
        }
    }

    function compatible(unit, profile) {
        const natures = catalog.unit_details[unit].natures;
        return !natures || profile.nature.endsWith("_hybride") || natures.includes(profile.nature);
    }

    function activeLimit(profile) {
        return catalog.active_limits[profile.nature] + Number(profile.zombie && "mort_vivant" in profile.labels);
    }

    function buildProfile(body, camp, general, index) {
        const prefix = `${camp}-general-${index + 1}`;
        const p = general.profile;
        const controls = general.profileControls = {};
        const grid = node("div", undefined, "sim-options-grid");
        for (const [key, title, max] of [["level", "Niveau", catalog.limits.level], ["pc", "Points de commandement (PC)", catalog.limits.pc], ["morale", "Moral", catalog.limits.morale], ["zombie_levels", "Niveaux gagnés après zombification", catalog.limits.level]]) {
            const input = node("input");
            Object.assign(input, {id: `${prefix}-${key}`, type: "number", min: "0", max: String(max), step: "1", required: true, value: p[key]});
            const label = node("label", title); label.htmlFor = input.id;
            const field = node("div"); field.append(label, input); grid.append(field); controls[key] = input;
        }
        const trait = node("select"); trait.id = `${prefix}-trait`;
        for (const name of catalog.traits) { const option = node("option", name); option.value = name; trait.append(option); }
        trait.value = p.trait; controls.trait = trait;
        const traitLabel = node("label", "Trait inné"); traitLabel.htmlFor = trait.id;
        grid.append(traitLabel, trait);
        for (const [key, title, checked] of [["qg", "Quartier général du camp", general.qg], ["zombie", "Général zombie", p.zombie]]) {
            const input = node("input"); Object.assign(input, {type: "checkbox", id: `${prefix}-${key}`, checked});
            const label = node("label", title); label.htmlFor = input.id;
            grid.append(label, input); controls[key] = input;
        }
        controls.qg.addEventListener("change", () => {
            if (controls.qg.checked) for (const other of armies[camp]) if (other !== general) other.profileControls.qg.checked = false;
            update();
        });
        body.append(grid);
        const generate = node("button", "Générer un général à ce niveau", "sim-secondary");
        generate.type = "button"; generate.id = `${prefix}-generate`;
        const status = node("p", "Le tirage remplace les caractéristiques et les étiquettes ; les troupes restent modifiables.", "sim-muted");
        status.setAttribute("role", "status"); status.id = `${prefix}-generation-status`;
        generate.addEventListener("click", async () => {
            if (busy || !controls.level.checkValidity()) return;
            rememberGenerals(); busy = true; generate.disabled = true; update();
            status.textContent = "Progression officielle en cours…";
            try {
                const response = await fetch("/api/simulator/generate", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({level: p.level, seed: null}), signal: AbortSignal.timeout(15000)});
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || "Génération indisponible.");
                rememberGenerals();
                general.profile = result.profile; general.orientation = result.profile.nature;
                renderGenerals();
                $(`${prefix}-generation-status`).textContent = `Général généré par le moteur · graine ${result.seed}. Vérifiez la compatibilité des troupes conservées.`;
            } catch (error) { status.textContent = error.message; }
            finally { busy = false; generate.disabled = false; update(); }
        });
        body.append(generate, status);
        const details = node("details", undefined, "sim-labels");
        const summary = node("summary", "Étiquettes connues et actives");
        const labelsSummary = node("p", "", "sim-muted"); general.labelsSummary = labelsSummary;
        details.append(summary, labelsSummary, node("p", "Rang 0 : inconnue. Les étiquettes permanentes restent au rang 1. Le moteur contrôle les limites d’apprentissage et d’activation."));
        general.labelControls = {};
        for (const name of Object.keys(catalog.labels)) {
            const row = node("div", undefined, "sim-label-row");
            const rank = node("input"); Object.assign(rank, {type: "number", min: "0", max: catalog.label_rank_max[p.level], step: "1", value: p.labels[name] || 0, id: `${prefix}-label-${name}`});
            const label = node("label", name.replaceAll("_", " ")); label.htmlFor = rank.id;
            row.append(label, rank);
            const inputs = {rank};
            for (const [key, text] of [["active", "Active"], ["permanent", "Permanente"]]) {
                const input = node("input"); Object.assign(input, {type: "checkbox", id: `${rank.id}-${key}`, checked: p[key].includes(name)});
                const caption = node("label", text); caption.htmlFor = input.id;
                row.append(caption, input); inputs[key] = input;
            }
            general.labelControls[name] = inputs; details.append(row);
        }
        body.append(details);
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
        body.append(positionLabel, position);
        const orientation = node("select");
        orientation.id = `${camp}-general-${index + 1}-orientation`;
        for (const [value, name] of Object.entries(orientations)) {
            const option = node("option", name);
            option.value = value;
            orientation.append(option);
        }
        orientation.value = general.orientation;
        const label = node("label", "Nature du général");
        label.htmlFor = orientation.id;
        const help = node("p", "Profil synthétique modifiable. Les PC ne sont pas recalculés lorsque vous changez le niveau ; utilisez la génération pour obtenir une progression officielle.", "sim-muted");
        help.id = `${orientation.id}-help`;
        orientation.setAttribute("aria-describedby", help.id);
        body.append(label, orientation, help);
        buildProfile(body, camp, general, index);
        const random = node("button", "Composition aléatoire", "sim-secondary sim-random-general");
        random.id = `${camp}-general-${index + 1}-random`;
        random.type = "button";
        random.setAttribute("aria-label", `Composition aléatoire pour le général ${index + 1} du camp ${camp}`);
        random.setAttribute("aria-describedby", `random-help-${camp}`);
        random.addEventListener("click", () => randomize(camp, [general], random.id));
        body.append(random);
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
            const shieldLabel = node("label", "Gros zombie (10 places, un seul par général)");
            shieldLabel.htmlFor = shield.id;
            fieldset.append(unitLabel, select, countLabel, input, hint, messengerLabel, messengers, shieldLabel, shield);
            grid.append(fieldset);
            general.controls[block] = {unit: select, count: input, hint, messengers, shield};
        }
        body.append(grid);
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
        Object.assign(general, {element: details, orientationInput: orientation, summary: summaryText, removeButton: remove});
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
            body.append(randomLabel, randomCount);
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
            body.append(list, actions, help, status);
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
        for (const camp of camps) $("result-summary").append(node("p", `Camp ${camp} : variation nette ${-result.losses[camp]} unités, ${result.after[camp].total} restantes (créations comprises). Généraux : ${result.after[camp].surviving_generals} survivants, ${result.after[camp].destroyed_generals} détruits sur ${result.before[camp].generals.length}.`));
        for (const qg of result.qg_initial) if (qg) $("result-summary").append(node("p", `QG initial ${qg.qg.join(" / ")} : ${qg.pc_initial} PC personnels + ${qg.bonus_messager} via Messager = ${qg.pc_global} PC globaux. Soutien figé, interrompu à sa destruction ; aucun remplacement.`));
        $("result-summary").append(node("p", `Soins de victoire du Chaman : ${result.healed_by_shaman} soldats traités. Les bonus exacts figurent dans le journal.`));
        const mode = result.conditions.mode + (result.conditions.defender ? ` · camp ${result.conditions.defender} défenseur` : "");
        $("result-meta").textContent = `Graine ${result.seed} · Moteur V2.0 ${result.engine_commit.slice(0, 12)} · Python ${result.python_version} · ${mode}, sans fatigue · ${result.conditions.orders.length ? "ordre actif" : "sans ordre"}`;
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

    $("simulation-form").addEventListener("input", update);
    $("simulation-form").addEventListener("change", update);
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
        update();
        if ($("run-button").disabled) return;
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
            $("run-button").textContent = "Lancer la simulation";
            $("results").setAttribute("aria-busy", "false");
            update();
        }
    });

    async function start() {
        try {
            const response = await fetch("/api/simulator/catalog", {signal: AbortSignal.timeout(10000)});
            if (!response.ok || !(response.headers.get("content-type") || "").includes("application/json")) throw new Error();
            catalog = await response.json();
            for (const unit of catalog.units) unitNames[unit] ||= unit.replaceAll("_", " ");
            buildArmies();
            $("simulation-form").hidden = false;
            $("service-status").textContent = "Configurez votre duel. Vous pouvez replier et rouvrir chaque panneau.";
            $("engine-version").textContent = `Moteur officiel V2.0 · ${catalog.engine_commit.slice(0, 12)} · OFF/OFF et OFF/DEF, sans fatigue · jusqu’à ${catalog.max_generals_per_camp} généraux actifs par camp.`;
            $("layout-button").hidden = false;
            updateLayout();
            update();
        } catch (_error) {
            $("service-status").className = "sim-error";
            $("service-status").textContent = "Le service de simulation est indisponible. Cette page nécessite le serveur Python du projet ; son lancement est décrit dans le README. Une page HTML ouverte seule ne peut pas exécuter le moteur.";
        }
    }
    start();
})();
