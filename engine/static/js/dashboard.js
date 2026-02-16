/* --- TACTICAL TERMINAL // ENGINE UI --- */

let speed = 400; 
let index = 0;
let timer = null;

function openTab(tabId) {
    const contents = document.getElementsByClassName("tab-content");
    for (let content of contents) {
        content.style.display = "none";
        content.classList.remove("active");
    }
    const btns = document.getElementsByClassName("tab-btn");
    for (let btn of btns) {
        btn.classList.remove("active");
    }
    document.getElementById(tabId).style.display = "block";
    document.getElementById(tabId).classList.add("active");
    event.currentTarget.classList.add("active");
}

function playTicker() {
    const lines = document.getElementsByClassName("line");
    const feed = document.getElementById("feed");
    const scoreBoard = document.getElementById("scoreboard");

    if (index < lines.length) {
        lines[index].style.display = "block";
        
        // Smart Auto-Scroll
        if(feed.scrollTop + feed.clientHeight >= feed.scrollHeight - 100) {
            feed.scrollTop = feed.scrollHeight;
        }
        
        index++;
        timer = setTimeout(playTicker, speed);
    } else {
        if(scoreBoard) {
            scoreBoard.classList.remove("blur");
            scoreBoard.classList.add("reveal");
        }
    }
}

function setSpeed(newSpeed) { speed = newSpeed; }
function skipAll() { speed = 0; }

// Auto-start on load if lines exist
document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementsByClassName("line").length > 0) {
        playTicker();
    }
});