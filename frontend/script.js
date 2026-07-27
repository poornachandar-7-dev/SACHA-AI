const BACKEND_URL = "http://localhost:8000";

// Fixed element IDs (removed trailing spaces)
const input = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const chatLog = document.getElementById("chat-log");
const micBtn = document.getElementById("mic-btn");
const voiceToggle = document.getElementById("voice-toggle");
const voiceIcon = document.getElementById("voice-icon");
const voiceLabel = document.getElementById("voice-label");
const gestureToggle = document.getElementById("gesture-toggle");
const gestureLabel = document.getElementById("gesture-label");
const gesturePanel = document.getElementById("gesture-panel");

let voiceOutputEnabled = true;
let isRecording = false;
let gestureActive = false;

// --- 🎨 SCENE DETECTION ---
const SCENE_KEYWORDS = {
    solar:  ["solar system", "solar", "planet", "planets", "sun", "space"],
    atom:   ["atom", "atomic", "electron", "molecule", "nucleus", "science"],
    fire:   ["fire", "flame", "burn", "hot", "blaze"],
    orb:    ["orb", "ball", "circle", "default"]
};

function detectScene(message) {
    const lower = message.toLowerCase();
    for (const [scene, keywords] of Object.entries(SCENE_KEYWORDS)) {
        for (const kw of keywords) {
            if (lower.includes(kw)) return scene;
        }
    }
    return null;
}

// --- UI HELPERS ---
function clearEmptyState() {
    const empty = chatLog.querySelector(".empty-state");
    if (empty) empty.remove();
}

function addMessage(sender, text) {
    clearEmptyState();
    const div = document.createElement("div");
    div.className = `msg ${sender === "You" ? "user" : "sacha"}`;
    div.textContent = text;
    chatLog.appendChild(div);
    chatLog.scrollTop = chatLog.scrollHeight;
}

function showTyping() {
    clearEmptyState();
    const div = document.createElement("div");
    div.className = "typing";
    div.id = "typing-indicator";
    div.innerHTML = "<span></span><span></span><span></span>";
    chatLog.appendChild(div);
    chatLog.scrollTop = chatLog.scrollHeight;
}

function hideTyping() {
    const el = document.getElementById("typing-indicator");
    if (el) el.remove();
}

function speak(text) {
    if (!voiceOutputEnabled || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(u);
}

// ---  SEND MESSAGE ---
async function sendMessage(message) {
    if (!message) return;

    // 1. Detect and change the visualizer scene
    const scene = detectScene(message);
    if (scene) {
        if (window.setScene) window.setScene(scene);
        addMessage("SACHA", `✨ Switching visualizer to: ${scene.toUpperCase()}`);
        
        // Auto-open gesture panel if it's closed
        if (!gestureActive) {
            gestureActive = true;
            gestureToggle.classList.add("active");
            gestureLabel.textContent = "Gesture on";
            gesturePanel.classList.remove("hidden");
            if (window.startGestureTracking) await window.startGestureTracking();
        }
    }

    // 2. Send to backend
    addMessage("You", message);
    input.value = "";
    showTyping();

    try {
        const res = await fetch(`${BACKEND_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message }),
        });
        const data = await res.json();
        hideTyping();
        addMessage("SACHA", data.reply);
        speak(data.reply);
    } catch (err) {
        hideTyping();
        addMessage("SACHA", "Error: couldn't reach the backend.");
    }
}

// --- EVENT LISTENERS ---
sendBtn.addEventListener("click", () => sendMessage(input.value.trim()));
input.addEventListener("keydown", (e) => { if (e.key === "Enter") sendMessage(input.value.trim()); });

voiceToggle.addEventListener("click", () => {
    voiceOutputEnabled = !voiceOutputEnabled;
    voiceIcon.textContent = voiceOutputEnabled ? "🔊" : "🔇";
    voiceLabel.textContent = voiceOutputEnabled ? "Voice on" : "Voice off";
    voiceToggle.classList.toggle("off", !voiceOutputEnabled);
});

gestureToggle.addEventListener("click", async () => {
    gestureActive = !gestureActive;
    gestureToggle.classList.toggle("active", gestureActive);
    gestureLabel.textContent = gestureActive ? "Gesture on" : "Gesture off";
    gesturePanel.classList.toggle("hidden", !gestureActive);
    if (gestureActive) {
        if (window.startGestureTracking) await window.startGestureTracking();
    } else {
        if (window.stopGestureTracking) window.stopGestureTracking();
    }
});

// Voice Input
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onstart = () => { isRecording = true; micBtn.classList.add("recording"); };
    recognition.onresult = (e) => sendMessage(e.results[0][0].transcript);
    recognition.onend = () => { isRecording = false; micBtn.classList.remove("recording"); };
    micBtn.addEventListener("click", () => { isRecording ? recognition.stop() : recognition.start(); });
} else {
    micBtn.style.opacity = "0.4";
}

window.addEventListener("beforeunload", () => {
  navigator.sendBeacon("http://localhost:8000/shutdown");
});