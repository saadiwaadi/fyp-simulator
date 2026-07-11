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
let currentMinute = 0;

document.addEventListener("DOMContentLoaded", () => {
    // 1. Load the data passed from Django
    const rawData = document.getElementById('match-logs-data');
    if (rawData) {
        logsData = JSON.parse(rawData.textContent);
        playLoop();
    }
    initPitch();
});

// --- LIVE PITCH (spatial tracking) ---
// Renders movement frames exported by the engine. Dots ease toward each
// frame's positions, and the frame pointer follows the commentary minute,
// so motion stays smooth and in sync with the feed.
const pitchState = { frames: null, roster: null, dots: [], ballDot: null, ptr: 0, subT: 0, lastTs: 0 };

function readJsonScript(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
}

function initPitch() {
    const frames = readJsonScript('movement-frames');
    const roster = readJsonScript('movement-roster');
    const pitchEl = document.getElementById('pitch');
    if (!frames || !roster || !frames.length || !pitchEl) {
        // Older match without movement telemetry: hide the pitch panel.
        const wrap = document.getElementById('pitch-wrap');
        if (wrap) wrap.style.display = 'none';
        return;
    }

    const size = readJsonScript('pitch-size') || [20, 13];
    pitchState.frames = frames;
    pitchState.roster = roster;
    pitchState.fieldW = size[0];
    pitchState.fieldH = size[1];
    pitchEl.style.aspectRatio = `${size[0]} / ${size[1]}`;

    roster.forEach((p, idx) => {
        const dot = document.createElement('div');
        dot.className = `player-dot ${p.side}` + (p.role === 'GK' ? ' gk' : '');
        const label = document.createElement('span');
        label.className = 'dot-label';
        label.textContent = p.name;
        dot.appendChild(label);
        pitchEl.appendChild(dot);
        const [fx, fy] = frames[0].p[idx];
        pitchState.dots.push({ el: dot, x: fx, y: fy });
    });

    const ball = document.createElement('div');
    ball.className = 'ball-dot';
    pitchEl.appendChild(ball);
    pitchState.ballDot = { el: ball, x: frames[0].b[0], y: frames[0].b[1] };

    requestAnimationFrame(pitchTick);
}

function pitchTick(ts) {
    const st = pitchState;
    if (!st.frames) return;
    const dt = st.lastTs ? Math.min(ts - st.lastTs, 100) : 16;
    st.lastTs = ts;

    // Follow the commentary: advance toward the last frame of currentMinute,
    // pacing sub-frames so a minute of motion spreads across the ticker time.
    if (!isPaused) {
        const framesPerMs = 4 / Math.max(speed * 2.2, 200); // ~4 frames per sim-minute
        st.subT += dt * framesPerMs;
        while (st.subT >= 1 && st.ptr < st.frames.length - 1 && st.frames[st.ptr + 1].m <= currentMinute) {
            st.ptr++;
            st.subT -= 1;
        }
        st.subT = Math.min(st.subT, 1);
    }

    const frame = st.frames[st.ptr];
    const ease = 1 - Math.pow(0.0025, dt / 1000); // smooth chase toward frame

    st.dots.forEach((d, idx) => {
        const [tx, ty] = frame.p[idx];
        d.x += (tx - d.x) * ease;
        d.y += (ty - d.y) * ease;
        d.el.style.left = (d.x / st.fieldW * 100) + '%';
        d.el.style.top = (d.y / st.fieldH * 100) + '%';
    });

    const b = st.ballDot;
    b.x += (frame.b[0] - b.x) * ease * 1.4;
    b.y += (frame.b[1] - b.y) * ease * 1.4;
    b.el.style.left = (b.x / st.fieldW * 100) + '%';
    b.el.style.top = (b.y / st.fieldH * 100) + '%';

    requestAnimationFrame(pitchTick);
}

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
        currentMinute = parseInt(timeMatch[1]);
        document.getElementById('sim-minute').innerText = timeMatch[1] + "'";
    }
    if (line.includes('FULL TIME')) {
        currentMinute = 9999; // let the pitch play out to the last frame
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
    if (pitchState.frames) {
        pitchState.ptr = pitchState.frames.length - 1; // settle dots at full-time positions
    }
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