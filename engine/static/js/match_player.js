// CONFIG
let playbackSpeed = 800;
let currentIndex = 0;
let intervalId = null;
let isPaused = false;

// STATE
let homeScore = 0, awayScore = 0;
let homeShots = 0, awayShots = 0;
let homeStruct = 100, awayStruct = 100;
let breaks = 0;

// MOCK FATIGUE DATA (To be replaced by real engine data later)
let fatigueRoster = [
    { name: "DM - Anchor", val: 95 },
    { name: "FWD - Presser", val: 92 },
    { name: "WB - Runner", val: 90 }
];

function init() {
    // 1. Get Safely Passed Logs from HTML
    const logData = document.getElementById('match-logs-data');
    if (logData) {
        window.matchLogs = JSON.parse(logData.textContent);
    } else {
        window.matchLogs = []; // Safety fallback
    }

    // 2. Set System Loads from Context
    const ctx = window.matchContext || { tempo:3, press:3, risk:3 };
    document.getElementById('load-tempo').style.width = (ctx.tempo * 20) + "%";
    document.getElementById('load-press').style.width = (ctx.press * 20) + "%";
    document.getElementById('load-risk').style.width  = (ctx.risk * 20) + "%";
    
    // 3. Start
    startSimulation();
}

function startSimulation() {
    if (intervalId) clearInterval(intervalId);
    intervalId = setInterval(processNextLog, playbackSpeed);
    document.getElementById('status-msg').innerText = "SIMULATION RUNNING...";
    document.getElementById('status-msg').classList.add('blink');
}

function togglePause() {
    const btn = document.getElementById('btn-pause');
    if (isPaused) {
        isPaused = false;
        startSimulation();
        btn.innerText = "⏸ PAUSE";
        btn.style.color = "#ccc";
    } else {
        isPaused = true;
        clearInterval(intervalId);
        document.getElementById('status-msg').innerText = "SIMULATION PAUSED";
        document.getElementById('status-msg').classList.remove('blink');
        btn.innerText = "▶ RESUME";
        btn.style.color = "var(--accent)";
    }
}

function processNextLog() {
    if (currentIndex >= window.matchLogs.length) {
        finishSimulation();
        return;
    }

    const log = window.matchLogs[currentIndex];
    const terminal = document.getElementById('terminal-feed');
    
    // 1. Create Row
    const row = document.createElement('div');
    row.className = 'log-entry';
    
    // Parse Time
    let minute = "00'";
    let content = log;
    const timeMatch = log.match(/^(\d+)'/);
    if (timeMatch) {
        minute = timeMatch[0];
        content = log.replace(timeMatch[0], "").trim();
        document.getElementById('sim-minute').innerText = minute;
        
        // Every 5 minutes, degrade fatigue
        if (parseInt(timeMatch[1]) % 5 === 0) simulateFatigue();
    }

    // 2. Identify Context
    const homeName = document.querySelector('.team-box.home .team-name').innerText;
    const isHomeEvent = content.includes(homeName);

    // 3. Logic & Style
    if (content.includes("GOAL")) {
        row.classList.add('log-goal');
        updateScore(content, homeName);
        triggerMomentum(isHomeEvent);
    } 
    else if (content.includes("SAVE")) {
        row.classList.add('log-save');
        updateShots(content, homeName);
    }
    else if (content.includes("MISS")) {
        row.style.color = "#888"; 
        updateShots(content, homeName); 
    }
    else if (content.includes("TACTIC") || content.includes("PHASE")) {
        row.classList.add('log-tactic');
        updateStructure(isHomeEvent);
        triggerMomentum(isHomeEvent);
        breaks++;
        document.getElementById('live-breaks').innerText = breaks;
    }
    else if (content.includes("TURNOVER")) {
        row.classList.add('log-turnover');
    }
    else if (content.includes("FOUL")) {
        row.classList.add('log-foul');
    }

    // 4. Inject into UI
    row.innerHTML = `<span class="log-time" style="color:#555; display:inline-block; width:30px;">${minute}</span><span class="log-text">${content}</span>`;
    terminal.appendChild(row);
    terminal.scrollTop = terminal.scrollHeight;

    currentIndex++;
}

// --- UPDATERS ---
function updateScore(log, homeName) {
    if (log.includes(homeName)) {
        homeScore++; document.getElementById('score-home').innerText = homeScore; homeShots++;
    } else {
        awayScore++; document.getElementById('score-away').innerText = awayScore; awayShots++;
    }
    updateShotsUI();
}

function updateShots(log, homeName) {
    if (log.includes(homeName)) homeShots++; else awayShots++;
    updateShotsUI();
}

function updateShotsUI() {
    document.getElementById('live-sh-h').innerText = homeShots;
    document.getElementById('live-sh-a').innerText = awayShots;
}

function updateStructure(isHomeAttacking) {
    if (isHomeAttacking) {
        awayStruct = Math.max(awayStruct - (Math.random() * 3), 10);
        document.getElementById('val-away-struct').innerText = Math.round(awayStruct) + "%";
        document.getElementById('bar-away-struct').style.width = awayStruct + "%";
    } else {
        homeStruct = Math.max(homeStruct - (Math.random() * 3), 10);
        document.getElementById('val-home-struct').innerText = Math.round(homeStruct) + "%";
        document.getElementById('bar-home-struct').style.width = homeStruct + "%";
    }
}

function simulateFatigue() {
    const list = document.getElementById('fatigue-list');
    if (!list) return; // Guard clause
    list.innerHTML = "";
    
    fatigueRoster.forEach(p => {
        p.val -= (Math.random() * 2); 
        let colorClass = p.val < 50 ? "color:#ff3333" : "color:#aaa";
        
        let item = document.createElement('div');
        item.className = 'fatigue-item';
        item.innerHTML = `<span class="f-name">${p.name}</span><span class="f-val" style="${colorClass}">${Math.round(p.val)}%</span>`;
        list.appendChild(item);
    });
}

function triggerMomentum(isHome) {
    const bar = document.getElementById('momentum-indicator');
    if (!bar) return;
    bar.style.left = isHome ? '30%' : '70%';
    setTimeout(() => { bar.style.left = '50%'; }, 600);
}

// --- CONTROLS ---
function setSpeed(ms) {
    playbackSpeed = ms;
    if (!isPaused) startSimulation();
}

function skipSim() {
    playbackSpeed = 5;
    if (!isPaused) startSimulation();
}

function finishSimulation() {
    clearInterval(intervalId);
    document.getElementById('status-msg').innerText = "SIMULATION COMPLETE";
    document.getElementById('status-msg').classList.remove('blink');
    document.getElementById('status-msg').style.color = "#fff";
    
    const btnReturn = document.getElementById('btn-return');
    if(btnReturn) btnReturn.style.display = 'inline-block';
    
    const btnPause = document.getElementById('btn-pause');
    if(btnPause) btnPause.style.display = 'none';

    // Completing the chopped-off block!
    if (window.finalStats) {
        document.getElementById('score-home').innerText = window.finalStats.h_score;
        document.getElementById('score-away').innerText = window.finalStats.a_score;
        document.getElementById('live-poss').innerText = window.finalStats.h_poss + "%";
        
        document.getElementById('val-home-struct').innerText = window.finalStats.h_struct + "%";
        document.getElementById('bar-home-struct').style.width = window.finalStats.h_struct + "%";
        
        document.getElementById('val-away-struct').innerText = window.finalStats.a_struct + "%";
        document.getElementById('bar-away-struct').style.width = window.finalStats.a_struct + "%";
    }
}

// 🔥 IGNITION SWITCH: Start the engine when the file loads!
window.onload = init;