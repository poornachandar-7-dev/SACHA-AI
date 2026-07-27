/* SACHA — Dynamic Gesture Visualizer */
const videoEl = document.getElementById("webcam");
const canvasEl = document.getElementById("gesture-canvas");
const ctx = canvasEl.getContext("2d");

let hands = null, camera = null, animationFrame = null;
let targetX = 0.5, targetY = 0.5, targetSpread = 0.3;
let curX = 0.5, curY = 0.5, curSpread = 0.3;

let currentScene = "orb";
let sceneState = {};

function resetSceneState() {
    sceneState = { stars: null, planets: null, electrons: null, fireParticles: [] };
}
resetSceneState();

function resizeCanvas() {
    canvasEl.width = canvasEl.clientWidth;
    canvasEl.height = canvasEl.clientHeight;
    resetSceneState();
}

function onResults(results) {
    if (!results.multiHandLandmarks || results.multiHandLandmarks.length === 0) return;
    const lm = results.multiHandLandmarks[0];
    let sx = 0, sy = 0;
    for (const p of lm) { sx += p.x; sy += p.y; }
    targetX = sx / lm.length;
    targetY = sy / lm.length;
    const dx = lm[4].x - lm[20].x, dy = lm[4].y - lm[20].y;
    targetSpread = Math.min(Math.max(Math.sqrt(dx*dx + dy*dy) * 1.8, 0.15), 0.6);
}

function getStars(w, h) {
    if (sceneState.stars && sceneState.stars.w === w) return sceneState.stars.list;
    const list = [];
    for (let i = 0; i < 100; i++) list.push({ x: Math.random()*w, y: Math.random()*h, r: Math.random()*1.5, t: Math.random()*Math.PI*2 });
    sceneState.stars = { w, h, list };
    return list;
}

// ---------- SCENE RENDERERS ----------
const scenes = {
    orb: (w, h, cx, cy, spread, time) => {
        const r0 = spread * Math.min(w,h) * 0.6;
        for (let i = 3; i >= 1; i--) {
            ctx.beginPath(); ctx.arc(cx, cy, r0*(1+i*0.35), 0, Math.PI*2);
            ctx.strokeStyle = `rgba(94,124,255,${0.12/i})`; ctx.lineWidth = 1.5; ctx.stroke();
        }
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r0);
        g.addColorStop(0, "rgba(124,156,255,0.9)"); g.addColorStop(1, "rgba(94,124,255,0.05)");
        ctx.beginPath(); ctx.arc(cx, cy, r0, 0, Math.PI*2); ctx.fillStyle = g; ctx.fill();
    },

    solar: (w, h, cx, cy, spread, time) => {
        // Draw stars
        for (const s of getStars(w, h)) {
            ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI*2);
            ctx.fillStyle = `rgba(255,255,255,${0.4 + 0.6*Math.abs(Math.sin(time+s.t))})`; ctx.fill();
        }
        if (!sceneState.planets) {
            sceneState.planets = [
                { d: 0.25, s: 2.0, r: 4, c: "#b8a89a", a: 0 },
                { d: 0.35, s: 1.5, r: 5, c: "#e8c080", a: 1.2 },
                { d: 0.48, s: 1.0, r: 6, c: "#4a90e2", a: 2.5 },
                { d: 0.62, s: 0.8, r: 5, c: "#d5603a", a: 3.8 },
                { d: 0.78, s: 0.5, r: 10, c: "#d4a574", a: 5.1 },
                { d: 0.92, s: 0.3, r: 9, c: "#e8d4a0", a: 0.7, rings: true },
            ];
        }
        const scale = spread * Math.min(w,h) * 1.5;
        // Sun
        const sg = ctx.createRadialGradient(cx, cy, 0, cx, cy, scale*0.15);
        sg.addColorStop(0, "#fff4c2"); sg.addColorStop(0.4, "rgba(255,180,60,0.8)"); sg.addColorStop(1, "rgba(255,120,40,0)");
        ctx.beginPath(); ctx.arc(cx, cy, scale*0.15, 0, Math.PI*2); ctx.fillStyle = sg; ctx.fill();
        
        // Planets
        for (const p of sceneState.planets) {
            const oR = scale * p.d;
            ctx.beginPath(); ctx.arc(cx, cy, oR, 0, Math.PI*2);
            ctx.strokeStyle = "rgba(255,255,255,0.1)"; ctx.lineWidth = 1; ctx.stroke();
            p.a += p.s * 0.01;
            const px = cx + Math.cos(p.a)*oR, py = cy + Math.sin(p.a)*oR*0.85;
            if (p.rings) {
                ctx.beginPath(); ctx.ellipse(px, py, p.r*2.5, p.r*0.7, 0.3, 0, Math.PI*2);
                ctx.strokeStyle = "rgba(232,212,160,0.7)"; ctx.lineWidth = 2; ctx.stroke();
            }
            ctx.beginPath(); ctx.arc(px, py, p.r, 0, Math.PI*2); ctx.fillStyle = p.c; ctx.fill();
        }
    },

    atom: (w, h, cx, cy, spread, time) => {
        const scale = spread * Math.min(w,h) * 1.0;
        if (!sceneState.electrons) sceneState.electrons = [{t:0,p:0,s:2},{t:1,p:1.5,s:1.8},{t:-1,p:3,s:2.5}];
        // Nucleus
        const ng = ctx.createRadialGradient(cx, cy, 0, cx, cy, scale*0.15);
        ng.addColorStop(0, "rgba(255,120,180,1)"); ng.addColorStop(1, "rgba(150,50,130,0)");
        ctx.beginPath(); ctx.arc(cx, cy, scale*0.15, 0, Math.PI*2); ctx.fillStyle = ng; ctx.fill();
        // Orbits & Electrons
        for (const e of sceneState.electrons) {
            ctx.save(); ctx.translate(cx, cy); ctx.rotate(e.t);
            ctx.beginPath(); ctx.ellipse(0, 0, scale*0.6, scale*0.25, 0, 0, Math.PI*2);
            ctx.strokeStyle = "rgba(140,180,255,0.3)"; ctx.lineWidth = 1; ctx.stroke();
            e.p += e.s * 0.02;
            const ex = Math.cos(e.p)*scale*0.6, ey = Math.sin(e.p)*scale*0.25;
            ctx.beginPath(); ctx.arc(ex, ey, 5, 0, Math.PI*2);
            ctx.fillStyle = "#8cc8ff"; ctx.shadowColor = "#8cc8ff"; ctx.shadowBlur = 15; ctx.fill();
            ctx.shadowBlur = 0; ctx.restore();
        }
    },

    fire: (w, h, cx, cy, spread, time) => {
        const scale = spread * Math.min(w,h) * 0.8;
        if (sceneState.fireParticles.length < 80) {
            sceneState.fireParticles.push({
                x: cx + (Math.random()-0.5)*scale*0.4, y: cy + scale*0.3,
                vx: (Math.random()-0.5)*1, vy: -Math.random()*4 - 2,
                life: 1, size: Math.random()*8 + 4
            });
        }
        for (let i = sceneState.fireParticles.length-1; i >= 0; i--) {
            const p = sceneState.fireParticles[i];
            p.x += p.vx; p.y += p.vy; p.life -= 0.02;
            if (p.life <= 0) { sceneState.fireParticles.splice(i,1); continue; }
            const r = p.size * p.life;
            const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r);
            g.addColorStop(0, `rgba(255,255,200,${p.life})`); g.addColorStop(1, `rgba(255,80,0,0)`);
            ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI*2); ctx.fillStyle = g; ctx.fill();
        }
    }
};

// ---------- MAIN LOOP ----------
function drawFrame() {
    const w = canvasEl.width, h = canvasEl.height;
    ctx.clearRect(0, 0, w, h);
    curX += (targetX - curX) * 0.15; curY += (targetY - curY) * 0.15;
    curSpread += (targetSpread - curSpread) * 0.15;
    const cx = curX * w, cy = curY * h;
    const time = Date.now() / 1000;
    
    // Render current scene
    const renderer = scenes[currentScene] || scenes.orb;
    renderer(w, h, cx, cy, curSpread, time);
    
    animationFrame = requestAnimationFrame(drawFrame);
}

// ---------- SCENE SWITCHING ----------
window.setScene = function(name) {
    if (scenes[name]) {
        currentScene = name;
        resetSceneState();
        console.log(`[SACHA] Visualizer changed to: ${name}`);
    } else {
        currentScene = "orb";
        resetSceneState();
    }
};

// ---------- CAMERA SETUP ----------
async function startGestureTracking() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        videoEl.srcObject = stream;
        resizeCanvas();
        window.addEventListener("resize", resizeCanvas);
        hands = new Hands({ locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}` });
        hands.setOptions({ maxNumHands: 1, modelComplexity: 1, minDetectionConfidence: 0.6, minTrackingConfidence: 0.5 });
        hands.onResults(onResults);
        camera = new Camera(videoEl, { onFrame: async () => { await hands.send({ image: videoEl }); }, width: 640, height: 360 });
        camera.start();
        drawFrame();
    } catch (err) { console.error("Camera error:", err); alert("Camera access denied."); }
}

window.startGestureTracking = startGestureTracking;
window.stopGestureTracking = function() {
    if (camera) { camera.stop(); camera = null; }
    if (videoEl.srcObject) { videoEl.srcObject.getTracks().forEach(t => t.stop()); videoEl.srcObject = null; }
    if (animationFrame) { cancelAnimationFrame(animationFrame); animationFrame = null; }
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
};