/**
 * SACHA AI Gesture Processing Pipeline (Backend Driven)
 */

class GesturePipeline {
    constructor() {
        this.container = document.getElementById('gesture-container');
        this.canvas = document.getElementById('gesture-canvas');
        this.statusLabel = document.querySelector('.gesture-status-label');
        
        if (this.canvas) {
            this.ctx = this.canvas.getContext('2d');
            this.resizeCanvas();
            window.addEventListener('resize', () => this.resizeCanvas());
        }
        
        this.isActive = false;
        
        // Landmark connections for MediaPipe hands
        this.HAND_CONNECTIONS = [
            [0, 1], [1, 2], [2, 3], [3, 4], // Thumb
            [0, 5], [5, 6], [6, 7], [7, 8], // Index
            [5, 9], [9, 10], [10, 11], [11, 12], // Middle
            [9, 13], [13, 14], [14, 15], [15, 16], // Ring
            [13, 17], [0, 17], [17, 18], [18, 19], [19, 20] // Pinky
        ];
    }
    
    resizeCanvas() {
        if (!this.canvas) return;
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    toggle(forceState) {
        const newState = forceState !== undefined ? forceState : !this.isActive;
        if (newState) {
            this.start();
        } else {
            this.stop();
        }
    }
    
    start() {
        if (this.isActive) return;
        this.isActive = true;
        
        if (this.container) {
            this.container.style.display = 'block';
        }
        
        if (this.statusLabel) {
            this.statusLabel.textContent = 'GESTURE TRACKING ACTIVE';
        }
        
        // Call Python backend to start tracking
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.start_gesture_tracking().catch(err => {
                console.error("Failed to start gesture tracking in backend", err);
            });
        } else {
            console.warn("pywebview API not ready, unable to start backend tracking");
        }
    }
    
    stop() {
        if (!this.isActive) return;
        this.isActive = false;
        
        if (this.container) {
            this.container.style.display = 'none';
        }
        
        if (this.ctx && this.canvas) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
        
        // Call Python backend to stop tracking
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.stop_gesture_tracking().catch(err => {
                console.error("Failed to stop gesture tracking in backend", err);
            });
        }
    }
    
    onGestureData(data) {
        if (!this.isActive || !this.ctx || !this.canvas) return;
        
        // Clear previous frame
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw HUD Frame
        this.drawHudFrame();
        
        if (data.error) {
            if (this.statusLabel) this.statusLabel.textContent = 'ERROR: ' + data.error;
            return;
        }
        
        if (data.clear || data.isClear) {
            document.dispatchEvent(new CustomEvent('gesture:clear'));
            if (data.clear) return; // If it's explicitly a clear command
        }
        
        if (data.landmarks && data.landmarks.length > 0) {
            this.renderLandmarks(data.landmarks);
            
            // Dispatch gesture:point event for AirDraw to consume
            if (data.x !== undefined && data.y !== undefined) {
                document.dispatchEvent(new CustomEvent('gesture:point', {
                    detail: {
                        x: data.x,
                        y: data.y,
                        isPinching: data.isPinching || false,
                        gesture: data.gesture || 'none'
                    }
                }));
            }
            
            if (this.statusLabel) {
                let status = `TRACKING: ${data.hand ? data.hand.toUpperCase() : 'HAND'}`;
                if (data.gesture) status += ` | ${data.gesture.toUpperCase()}`;
                if (data.confidence) status += ` (${(data.confidence * 100).toFixed(0)}%)`;
                this.statusLabel.textContent = status;
            }
        } else {
            if (this.statusLabel) this.statusLabel.textContent = 'SEARCHING FOR HANDS...';
        }
    }
    
    renderLandmarks(landmarks) {
        const w = this.canvas.width;
        const h = this.canvas.height;
        
        this.ctx.save();
        
        // Cybernetic style settings
        this.ctx.lineWidth = 2;
        this.ctx.strokeStyle = '#00f0ff';
        this.ctx.fillStyle = '#00f0ff';
        this.ctx.shadowBlur = 10;
        this.ctx.shadowColor = '#00f0ff';
        
        // Draw connections
        this.ctx.beginPath();
        for (const [i, j] of this.HAND_CONNECTIONS) {
            if (landmarks[i] && landmarks[j]) {
                this.ctx.moveTo(landmarks[i].x * w, landmarks[i].y * h);
                this.ctx.lineTo(landmarks[j].x * w, landmarks[j].y * h);
            }
        }
        this.ctx.stroke();
        
        // Draw landmarks
        for (let i = 0; i < landmarks.length; i++) {
            const lm = landmarks[i];
            this.ctx.beginPath();
            
            // Highlight fingertips differently (4=thumb, 8=index, 12=middle, 16=ring, 20=pinky)
            if ([4, 8, 12, 16, 20].includes(i)) {
                this.ctx.arc(lm.x * w, lm.y * h, 5, 0, 2 * Math.PI);
                this.ctx.fillStyle = '#ff00ff';
                this.ctx.shadowColor = '#ff00ff';
            } else {
                this.ctx.arc(lm.x * w, lm.y * h, 3, 0, 2 * Math.PI);
                this.ctx.fillStyle = '#00f0ff';
                this.ctx.shadowColor = '#00f0ff';
            }
            
            this.ctx.fill();
        }
        
        this.ctx.restore();
    }
    
    drawHudFrame() {
        const w = this.canvas.width;
        const h = this.canvas.height;
        const padding = 20;
        const cornerLen = 30;
        
        this.ctx.save();
        this.ctx.strokeStyle = 'rgba(0, 240, 255, 0.5)';
        this.ctx.lineWidth = 2;
        this.ctx.shadowBlur = 5;
        this.ctx.shadowColor = '#00f0ff';
        
        // Top-left
        this.drawCorner(padding, padding, cornerLen, cornerLen);
        // Top-right
        this.drawCorner(w - padding, padding, -cornerLen, cornerLen);
        // Bottom-left
        this.drawCorner(padding, h - padding, cornerLen, -cornerLen);
        // Bottom-right
        this.drawCorner(w - padding, h - padding, -cornerLen, -cornerLen);
        
        this.ctx.restore();
    }
    
    drawCorner(x, y, dx, dy) {
        this.ctx.beginPath();
        this.ctx.moveTo(x, y + dy);
        this.ctx.lineTo(x, y);
        this.ctx.lineTo(x + dx, y);
        this.ctx.stroke();
    }
}

// Export class to window
window.GesturePipeline = GesturePipeline;

// Register global callback for Python backend
window.sachaOnGesture = function(data) {
    if (window.gestureSystem) {
        window.gestureSystem.onGestureData(data);
    } else {
        console.warn("Gesture data received but window.gestureSystem is not initialized.");
    }
};
