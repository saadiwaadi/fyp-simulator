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

// --- LIVE PITCH (spatial tracking, canvas renderer) ---
// One <canvas> repainted per animation frame: players, kit numbers, ball,
// and a fading ball trail all land in a single paint, so there is no DOM
// layout work per frame and no CSS coordinate-space pitfalls. The chalk
// pitch markings stay as the styled div behind the (transparent) canvas.
const pitchState = {
    frames: null, roster: null, players: [], ball: null,
    ptr: 0, subT: 0, lastTs: 0,
    canvas: null, ctx: null, pw: 0, ph: 0, dpr: 1,
    trail: [], mouse: null, hover: -1,
};

const PALETTE = {
    homeFill: '#a51418', homeRing: '#fbf7ef', homeText: '#fbf7ef',
    awayFill: '#fbf7ef', awayRing: '#252525', awayText: '#252525',
    gkRing: '#c2a56b', gold: '#c2a56b', cream: '#fbf7ef', ink: '#252525',
};

function readJsonScript(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
}

function initPitch() {
    const frames = readJsonScript('movement-frames');
    const roster = readJsonScript('movement-roster');
    const pitchEl = document.getElementById('pitch');
    if (!pitchEl) return;

    if (!frames || !roster || !frames.length) {
        // The pitch is a confirmed fixture of the execute screen: with no
        // telemetry (a match simulated on an older engine build) it stays
        // visible and says why it is empty instead of vanishing.
        const fallback = document.createElement('div');
        fallback.className = 'pitch-fallback';
        fallback.innerHTML = '<strong>NO MOVEMENT TELEMETRY</strong>' +
            '<span>This match was simulated before spatial tracking.<br>' +
            'Run a new match from the Tactical Lab to see the live pitch.</span>';
        pitchEl.appendChild(fallback);
        return;
    }

    const size = readJsonScript('pitch-size') || [20, 13];
    const st = pitchState;
    st.frames = frames;
    st.roster = roster;
    st.fieldW = size[0];
    st.fieldH = size[1];
    pitchEl.style.aspectRatio = `${size[0]} / ${size[1]}`;

    const canvas = document.createElement('canvas');
    canvas.className = 'pitch-canvas';
    pitchEl.appendChild(canvas);
    st.canvas = canvas;
    st.ctx = canvas.getContext('2d');

    const measure = () => {
        st.dpr = window.devicePixelRatio || 1;
        st.pw = pitchEl.clientWidth;
        st.ph = pitchEl.clientHeight;
        canvas.width = Math.round(st.pw * st.dpr);
        canvas.height = Math.round(st.ph * st.dpr);
    };
    measure();
    window.addEventListener('resize', measure);

    canvas.addEventListener('mousemove', (e) => {
        const r = canvas.getBoundingClientRect();
        st.mouse = { x: e.clientX - r.left, y: e.clientY - r.top };
    });
    canvas.addEventListener('mouseleave', () => { st.mouse = null; st.hover = -1; });

    // Fallback numbering (older saved matches without roster numbers):
    // count up within each side in roster order, keeper first.
    const sideCounter = { home: 0, away: 0 };
    st.players = roster.map((p, idx) => {
        sideCounter[p.side] = (sideCounter[p.side] || 0) + 1;
        const [fx, fy] = frames[0].p[idx];
        return {
            x: fx, y: fy,
            num: p.num || sideCounter[p.side],
            name: p.name,
            side: p.side,
            gk: p.role === 'GK',
        };
    });
    st.ball = { x: frames[0].b[0], y: frames[0].b[1] };

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
        const framesPerMs = 8 / Math.max(speed * 2.2, 200); // 8 frames per sim-minute
        st.subT += dt * framesPerMs;
        while (st.subT >= 1 && st.ptr < st.frames.length - 1 && st.frames[st.ptr + 1].m <= currentMinute) {
            st.ptr++;
            st.subT -= 1;
        }
        st.subT = Math.min(st.subT, 1);
    }

    if (!st.pw || !st.ph) { // pitch wasn't laid out at init (e.g. hidden tab)
        st.pw = st.canvas.parentElement.clientWidth;
        st.ph = st.canvas.parentElement.clientHeight;
        if (!st.pw || !st.ph) { requestAnimationFrame(pitchTick); return; }
        st.canvas.width = Math.round(st.pw * st.dpr);
        st.canvas.height = Math.round(st.ph * st.dpr);
    }

    const frame = st.frames[st.ptr];
    const ease = 1 - Math.pow(0.0025, dt / 1000); // smooth chase toward frame
    const toPx = (fx, fy) => [fx / st.fieldW * st.pw, fy / st.fieldH * st.ph];

    st.players.forEach((d, idx) => {
        const [tx, ty] = frame.p[idx];
        d.x += (tx - d.x) * ease;
        d.y += (ty - d.y) * ease;
    });

    const b = st.ball;
    b.x += (frame.b[0] - b.x) * ease * 1.4;
    b.y += (frame.b[1] - b.y) * ease * 1.4;

    // Ball trail: recent positions fade out — completed passes read as
    // drawn lines across the turf.
    const [bpx, bpy] = toPx(b.x, b.y);
    if (!isPaused) {
        st.trail.push({ x: bpx, y: bpy });
        if (st.trail.length > 26) st.trail.shift();
    }

    drawPitch(st, frame, bpx, bpy);
    requestAnimationFrame(pitchTick);
}

function drawPitch(st, frame, bpx, bpy) {
    const ctx = st.ctx;
    ctx.setTransform(st.dpr, 0, 0, st.dpr, 0, 0);
    ctx.clearRect(0, 0, st.pw, st.ph);

    const r = Math.max(9, st.pw * 0.013);   // player token radius
    const toPx = (fx, fy) => [fx / st.fieldW * st.pw, fy / st.fieldH * st.ph];

    // trail under everything
    for (let i = 1; i < st.trail.length; i++) {
        const a = st.trail[i - 1], c = st.trail[i];
        ctx.strokeStyle = `rgba(194, 165, 107, ${0.35 * (i / st.trail.length)})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(c.x, c.y);
        ctx.stroke();
    }

    // hover hit-test (screen space)
    st.hover = -1;
    if (st.mouse) {
        let best = 1e9;
        st.players.forEach((d, i) => {
            const [px, py] = toPx(d.x, d.y);
            const dist = Math.hypot(st.mouse.x - px, st.mouse.y - py);
            if (dist < r + 5 && dist < best) { best = dist; st.hover = i; }
        });
    }
    st.canvas.style.cursor = st.hover >= 0 ? 'pointer' : 'default';

    // players
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    st.players.forEach((d, i) => {
        const [px, py] = toPx(d.x, d.y);
        const home = d.side === 'home';

        ctx.beginPath();
        ctx.arc(px, py + 1.5, r, 0, Math.PI * 2);   // soft ground shadow
        ctx.fillStyle = 'rgba(0, 0, 0, 0.30)';
        ctx.fill();

        ctx.beginPath();
        ctx.arc(px, py, r, 0, Math.PI * 2);
        ctx.fillStyle = home ? PALETTE.homeFill : PALETTE.awayFill;
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = d.gk ? PALETTE.gkRing : (home ? PALETTE.homeRing : PALETTE.awayRing);
        ctx.stroke();

        ctx.fillStyle = home ? PALETTE.homeText : PALETTE.awayText;
        ctx.font = `bold ${Math.round(r * 0.95)}px Consolas, monospace`;
        ctx.fillText(d.num, px, py + 0.5);
    });

    // ball above players
    ctx.beginPath();
    ctx.arc(bpx, bpy, Math.max(4, r * 0.42), 0, Math.PI * 2);
    ctx.fillStyle = PALETTE.cream;
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = PALETTE.ink;
    ctx.stroke();

    // hover label
    if (st.hover >= 0) {
        const d = st.players[st.hover];
        const [px, py] = toPx(d.x, d.y);
        const label = `${d.num} · ${d.name}`;
        ctx.font = '600 11px "Segoe UI", sans-serif';
        const w = ctx.measureText(label).width + 14;
        const lx = Math.min(Math.max(px, w / 2 + 4), st.pw - w / 2 - 4);
        const ly = Math.max(py - r - 20, 14);
        ctx.fillStyle = PALETTE.cream;
        ctx.strokeStyle = PALETTE.gold;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(lx - w / 2, ly - 10, w, 20, 3);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = PALETTE.ink;
        ctx.fillText(label, lx, ly + 0.5);
    }
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

    if (line.includes('[GOAL]')) p.classList.add('log-goal');
    else if (line.includes('[TACTIC]') || line.includes('[SWITCH]') || line.includes('[CROSS]')) p.classList.add('log-tactic');
    else if (line.includes('[TURNOVER]') || line.includes('[LOOSE]')) p.classList.add('log-turnover');
    else if (line.includes('[TACKLE]') || line.includes('[INTERCEPTED]') || line.includes('Integrity')) p.classList.add('log-danger');
    else if (line.includes('[SAVE]') || line.includes('[CLAIMED]') || line.includes('[CLEARED]')) p.classList.add('log-save');

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