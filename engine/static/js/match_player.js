// --- STATE TRACKERS ---
let logsData = [];
let currentIndex = 0;
let speed = 800;
let isPaused = false;
let simInterval;

let currentHomeScore = 0;
let currentAwayScore = 0;
let homeIntegrity = 100;
let awayIntegrity = 100;
let totalBreaks = 0;

document.addEventListener("DOMContentLoaded", () => {
    // 1. Load the data passed from Django
    const rawData = document.getElementById('match-logs-data');
    if (rawData) {
        logsData = JSON.parse(rawData.textContent);
        playLoop();
    }
});

// --- MAIN PLAYBACK LOOP ---
function playLoop() {
    clearInterval(simInterval);
    simInterval = setInterval(() => {
        if (isPaused) return;
        
        if (currentIndex >= logsData.length) {
            finalizeSim();
            return;
        }
        
        processLogLine(logsData[currentIndex]);
        currentIndex++;
    }, speed);
}

// --- THE PARSER (Reads the text and updates the UI) ---
function processLogLine(line) {
    const terminalFeed = document.getElementById('terminal-feed');

    // 1. Parse Minute
    let timeMatch = line.match(/^(\d+)'/);
    if (timeMatch) {
        document.getElementById('sim-minute').innerText = timeMatch[1] + "'";
    }

    // 2. Parse Goals & Score
    if (line.includes('[GOAL]')) {
        let scoreMatch = line.match(/\((\d+)\s*-\s*(\d+)\)/);
        if (scoreMatch) {
            currentHomeScore = parseInt(scoreMatch[1]);
            currentAwayScore = parseInt(scoreMatch[2]);
            
            document.getElementById('score-home').innerText = currentHomeScore;
            document.getElementById('score-away').innerText = currentAwayScore;
            
            // Flash effect
            document.getElementById('score-home').classList.add('goal-flash');
            setTimeout(() => document.getElementById('score-home').classList.remove('goal-flash'), 500);
            
            // Update Shots (Approximate based on goals for live feed)
            document.getElementById('live-sh-h').innerText = currentHomeScore;
            document.getElementById('live-sh-a').innerText = currentAwayScore;
        }
    }

    // 3. Parse Structural Integrity Damage
    let homeDmgMatch = line.match(/Home Integrity\s*(-?\d+\.?\d*)%/);
    if (homeDmgMatch) {
        homeIntegrity += parseFloat(homeDmgMatch[1]); // It's negative, so we add it to subtract
        updateIntegrityBar('home', homeIntegrity);
    }

    let awayDmgMatch = line.match(/Away Integrity\s*(-?\d+\.?\d*)%/);
    if (awayDmgMatch) {
        awayIntegrity += parseFloat(awayDmgMatch[1]);
        updateIntegrityBar('away', awayIntegrity);
    }

    // 4. Parse Tactical Breaks
    if (line.includes('[TACTIC]')) {
        totalBreaks++;
        document.getElementById('live-breaks').innerText = totalBreaks;
    }

    // 5. Print to Terminal with Colors
    let p = document.createElement('div');
    p.className = 'log-line';
    p.innerText = line;
    
    if (line.includes('[GOAL]')) p.style.color = 'var(--neon-green)';
    else if (line.includes('[TACTIC]')) p.style.color = 'var(--neon-blue)';
    else if (line.includes('[TURNOVER]')) p.style.color = 'orange';
    else if (line.includes('Integrity')) p.style.color = 'var(--neon-red)';
    else p.style.color = 'var(--text)';
    
    terminalFeed.appendChild(p);
    terminalFeed.scrollTop = terminalFeed.scrollHeight; // Auto-scroll
}

// --- HELPER FUNCTIONS ---
function updateIntegrityBar(side, value) {
    // Clamp value between 0 and 100
    let pct = Math.max(0, Math.min(100, value));
    let bar = document.getElementById(`bar-${side}-struct`);
    let valText = document.getElementById(`val-${side}-struct`);
    
    if (bar && valText) {
        bar.style.width = pct + '%';
        valText.innerText = Math.round(pct) + '%';
        
        // Change color to red if critical
        if (pct < 30) bar.style.background = 'var(--neon-red)';
        else if (pct < 60) bar.style.background = 'orange';
    }
}

// --- CONTROLS ---
window.togglePause = function() {
    isPaused = !isPaused;
    document.getElementById('btn-pause').innerText = isPaused ? "▶ RESUME" : "⏸ PAUSE";
    document.getElementById('status-msg').innerText = isPaused ? "SIMULATION PAUSED" : "SIMULATION RUNNING...";
};

window.setSpeed = function(newSpeed) {
    speed = newSpeed;
    if (!isPaused) playLoop(); // Restart interval with new speed
};

window.skipSim = function() {
    isPaused = true;
    clearInterval(simInterval);
    
    // Instantly process all remaining logs silently to get final math
    while (currentIndex < logsData.length) {
        processLogLine(logsData[currentIndex]);
        currentIndex++;
    }
    finalizeSim();
};

function finalizeSim() {
    clearInterval(simInterval);
    document.getElementById('status-msg').innerText = "SIMULATION COMPLETE";
    document.getElementById('status-msg').style.color = "var(--neon-green)";
    document.getElementById('btn-return').style.display = "inline-block";
    
    // Force final exact stats from the backend just to be safe
    if (window.finalStats) {
        document.getElementById('score-home').innerText = window.finalStats.h_score;
        document.getElementById('score-away').innerText = window.finalStats.a_score;
        updateIntegrityBar('home', window.finalStats.h_struct);
        updateIntegrityBar('away', window.finalStats.a_struct);
        document.getElementById('live-poss').innerText = window.finalStats.h_poss + "%";
    }
}