// --- 0. DATA: TACTICAL INSTRUCTIONS ---
const TACTICAL_MENUS = {
    'GK': [ { val: 'Standard', name: 'Traditional' }, { val: 'Sweeper Keeper', name: 'Sweeper Keeper (Risk)' }, { val: 'Cross Claimer', name: 'Cross Claimer' } ],
    'DEF_C': [ { val: 'Stay Back', name: 'Stay Back' }, { val: 'Ball Playing', name: 'Ball Playing Def' }, { val: 'Aggressive', name: 'Step Up' }, { val: 'Play as Striker', name: 'Join Attack (Late)' } ],
    'DEF_W': [ { val: 'Balanced', name: 'Balanced' }, { val: 'Join Attack', name: 'Overlap' }, { val: 'Stay Back', name: 'Stay Back' }, { val: 'Invert', name: 'Invert' } ],
    'MID_C': [ { val: 'Balanced', name: 'Balanced' }, { val: 'Cover Center', name: 'Cover Center' }, { val: 'Cover Wing', name: 'Cover Wing' }, { val: 'Get Forward', name: 'Get Forward' }, { val: 'Deep Playmaker', name: 'Deep Playmaker' } ],
    'MID_W': [ { val: 'Balanced', name: 'Balanced' }, { val: 'Cut Inside', name: 'Cut Inside' }, { val: 'Stay Wide', name: 'Hug Sideline' }, { val: 'Free Roam', name: 'Free Roam' } ],
    'FWD_C': [ { val: 'Balanced', name: 'Balanced' }, { val: 'Get In Behind', name: 'Get In Behind' }, { val: 'False 9', name: 'False 9' }, { val: 'Target Man', name: 'Target Man' }, { val: 'Press Line', name: 'Press Line' } ],
    'FWD_W': [ { val: 'Balanced', name: 'Balanced' }, { val: 'Cut Inside', name: 'Cut Inside' }, { val: 'Stay Wide', name: 'Stay Wide' }, { val: 'Come Back', name: 'Track Back' } ]
};

const ROLE_WEIGHTS = {
    'Standard': { 'sta':1, 'spd':1, 'sho':1, 'def':1, 'pas':1 },
    'Sweeper Keeper': { 'spd':4, 'pas':3, 'def':1 },
    'Cross Claimer': { 'def':4, 'sta':2 },
    'Stay Back': { 'def':4, 'sta':2 },
    'Ball Playing': { 'pas':4, 'def':2 },
    'Aggressive': { 'def':3, 'spd':3 },
    'Play as Striker': { 'sho':3, 'def':2 },
    'Join Attack': { 'sta':4, 'spd':3, 'pas':2 },
    'Invert': { 'pas':4, 'def':2, 'sta':2 },
    'Cover Center': { 'def':4, 'sta':3 },
    'Cover Wing': { 'spd':3, 'sta':3 },
    'Get Forward': { 'sho':3, 'pas':2, 'sta':2 },
    'Deep Playmaker': { 'pas':5, 'def':1 },
    'Cut Inside': { 'spd':3, 'sho':4, 'pas':1 },
    'Stay Wide': { 'spd':4, 'pas':3 },
    'Free Roam': { 'pas':3, 'spd':2, 'sho':2 },
    'Get In Behind': { 'spd':5, 'sho':2 },
    'False 9': { 'pas':4, 'sho':2, 'spd':1 },
    'Target Man': { 'sta':5, 'sho':2, 'def':2 },
    'Press Line': { 'sta':5, 'spd':3 },
    'Come Back': { 'sta':4, 'def':3 }
};

let tacticalMemory = { '5v5': {}, '11v11': {} };

// --- LOGIC FUNCTIONS (Copy Paste your previous Logic here) ---
function changeMode(newMode) {
    const pitch = document.getElementById('pitch');
    const currentMode = pitch.classList.contains('mode-5v5') ? '5v5' : '11v11';

    const currentSlots = document.querySelectorAll(`.mode-${currentMode} .slot`);
    tacticalMemory[currentMode] = {}; 
    currentSlots.forEach(slot => {
        const card = slot.querySelector('.card');
        if(card) tacticalMemory[currentMode][card.id] = slot.id;
    });

    const bench = document.getElementById('bench');
    document.querySelectorAll('.card').forEach(c => { c.classList.remove('deployed'); bench.appendChild(c); });

    pitch.className = `pitch-container mode-${newMode}`;
    document.getElementById('form-mode').value = newMode;

    const saved = tacticalMemory[newMode];
    for (const [cid, sid] of Object.entries(saved)) {
        const c = document.getElementById(cid); const s = document.getElementById(sid);
        if (c && s) { s.appendChild(c); c.classList.add('deployed'); }
    }
}

function allowDrop(ev) { ev.preventDefault(); ev.currentTarget.classList.add('drag-over'); }
function drag(ev) { ev.dataTransfer.setData("text", ev.target.id); }
function drop(ev) {
    ev.preventDefault(); ev.currentTarget.classList.remove('drag-over');
    let card = document.getElementById(ev.dataTransfer.getData("text"));
    let slot = ev.target.closest('.slot');
    
    if(slot) {
        if (slot.getAttribute('data-zone') === 'GK' && card.getAttribute('data-role') !== 'GK') {
            alert("TACTICAL ERROR: ONLY SPECIALIST GOALKEEPERS CAN BE DEPLOYED IN THIS SLOT."); return; 
        }
        let existing = slot.querySelector('.card');
        if (existing && existing.id !== card.id) {
            document.getElementById('bench').appendChild(existing); existing.classList.remove('deployed');
        }
        slot.appendChild(card); card.classList.add('deployed');
        let mode = document.getElementById('form-mode').value;
        tacticalMemory[mode][card.id] = slot.id;
        inspectPlayer(card.getAttribute('data-id'));
    }
}

function inspectPlayer(pid) {
    let card = document.getElementById('p-' + pid);
    let role = card.getAttribute('data-role');
    let slot = card.parentElement;
    let zone = slot.getAttribute('data-zone');

    document.getElementById('con-name').innerText = card.getAttribute('data-name');
    document.getElementById('con-role').innerText = role;
    document.getElementById('active-player-id').value = pid;
    document.getElementById('console-tabs').style.display = 'flex';

    updateStat('sta', card.getAttribute('data-sta'));
    updateStat('spd', card.getAttribute('data-spd'));
    updateStat('sho', card.getAttribute('data-sho'));
    updateStat('def', card.getAttribute('data-def'));

    populateDropdown(role, zone, card.getAttribute('data-instr'));
    document.getElementById('input-sp').value = card.getAttribute('data-sp') || "";

    generateTraits(card);
    recalcFit();
}

function populateDropdown(role, zone, currentSelection) {
    const select = document.getElementById('input-instr');
    select.innerHTML = "";
    
    let contextKey = role;
    if (role !== 'GK') {
        let width = (zone === 'C') ? 'C' : 'W';
        contextKey = `${role}_${width}`;
    }

    const options = TACTICAL_MENUS[contextKey] || [{val:'Standard', name:'Standard'}];
    options.forEach(opt => {
        let el = document.createElement('option');
        el.value = opt.val;
        el.innerText = opt.name;
        select.appendChild(el);
    });

    if(currentSelection && options.some(o => o.val === currentSelection)) {
        select.value = currentSelection;
    } else {
        select.value = options[0].val;
    }
}

function generateTraits(card) {
    const box = document.getElementById('trait-box'); if(!box) return;
    box.innerHTML = ''; 

    const s = {
        sta: parseInt(card.getAttribute('data-sta')),
        spd: parseInt(card.getAttribute('data-spd')),
        sho: parseInt(card.getAttribute('data-sho')),
        def: parseInt(card.getAttribute('data-def'))
    };

    const traits = [
        { name: 'High Motor', icon: '🔥', check: s.sta > 80 },
        { name: 'Speedster',  icon: '⚡', check: s.spd > 85 },
        { name: 'Clinical',   icon: '🎯', check: s.sho > 80 },
        { name: 'Wall',       icon: '🧱', check: s.def > 80 },
        { name: 'Playmaker',  icon: '🧠', check: (s.sho + s.spd + s.def) < 150 && s.sta > 70 }
    ];

    traits.forEach(t => {
        let d = document.createElement('div');
        d.className = `trait-badge ${t.check ? 'active' : ''}`;
        if(t.check && s.sho > 90) d.classList.add('gold');
        d.innerHTML = `${t.icon} ${t.name}`;
        box.appendChild(d);
    });
}

function recalcFit() {
    const pid = document.getElementById('active-player-id').value; if(!pid) return;
    const card = document.getElementById('p-' + pid);
    const instr = document.getElementById('input-instr').value;
    
    card.setAttribute('data-instr', instr);

    const weights = ROLE_WEIGHTS[instr] || ROLE_WEIGHTS['Standard'];
    
    const s = {
        'sta': parseInt(card.getAttribute('data-sta')),
        'spd': parseInt(card.getAttribute('data-spd')),
        'sho': parseInt(card.getAttribute('data-sho')),
        'def': parseInt(card.getAttribute('data-def'))
    };
    s['pas'] = Math.round((s.sho + s.def + s.spd)/3); // Proxy for passing

    let score = 0, max = 0;
    for (const [k, w] of Object.entries(weights)) {
        score += (s[k] || 50) * w;
        max += 100 * w;
    }

    const pct = Math.round((score / max) * 100);
    const el = document.getElementById('live-fit-score');
    if(el) {
        el.innerText = pct + "%";
        el.className = 'fit-score ' + (pct > 85 ? 'fit-high' : pct > 70 ? 'fit-med' : 'fit-low');
    }
}

function saveTacticLocal(type) {
    let pid = document.getElementById('active-player-id').value; if(!pid) return;
    let card = document.getElementById('p-' + pid);
    let val = document.getElementById('input-' + type).value;

    if (type === 'sp' && val !== "") {
        ['CAP', 'PEN', 'CR', 'FK'].forEach(role => {
            if (val === role) {
                document.querySelectorAll('.card').forEach(c => {
                    if (c.id !== card.id && c.getAttribute('data-sp') === role) c.setAttribute('data-sp', "");
                });
            }
        });
    }
    card.setAttribute('data-' + type, val);
}

function updateStat(k, v) { 
    document.getElementById('val-'+k).innerText = v; 
    document.getElementById('bar-'+k).style.width = v+'%'; 
}

function switchTab(n) {
    document.querySelectorAll('.tab, .view-section').forEach(e => e.classList.remove('active'));
    event.currentTarget.classList.add('active'); document.getElementById('view-'+n).classList.add('active');
}

// --- UPDATED EXECUTION (Uses Window Data) ---
function executeMission() {
    // ... (Your existing validation checks) ...

    // SHOW LOADER
    document.getElementById('loader').style.display = 'flex';

    // Submit after a tiny delay to allow the UI to repaint
    setTimeout(() => {
        document.getElementById('exe-form').submit();
    }, 50);
}    
    let container = document.getElementById('form-data'); container.innerHTML = "";
    let cards = document.querySelectorAll('.card.deployed');
    let mode = document.getElementById('form-mode').value;
    let req = (mode === '5v5') ? 5 : 11;

    if(cards.length < req) { alert(`SQUAD UNDERSTRENGTH. ${mode} REQUIRES ${req}.`); return; }

    cards.forEach(c => {
        let pid = c.getAttribute('data-id');
        let slot = c.parentElement;
        addHidden(container, 'starting_players', pid);
        addHidden(container, `zone_${pid}`, slot.getAttribute('data-zone'));
        addHidden(container, `instruction_${pid}`, c.getAttribute('data-instr')||"");
        addHidden(container, `set_piece_${pid}`, c.getAttribute('data-sp')||"");
    });
    document.getElementById('exe-form').submit();
}

function addHidden(p, n, v) { let i = document.createElement('input'); i.type='hidden'; i.name=n; i.value=v; p.appendChild(i); }

window.onload = function() {
    let cards = document.querySelectorAll('.card');
    cards.forEach(c => {
        if(c.getAttribute('data-start') === "True") {
            let z = c.getAttribute('data-saved-zone');
            let s = document.querySelector(`.mode-5v5 .slot[data-zone='${z}']:not(:has(.card))`);
            if(s) { s.appendChild(c); c.classList.add('deployed'); tacticalMemory['5v5'][c.id] = s.id; }
        }
    });
};