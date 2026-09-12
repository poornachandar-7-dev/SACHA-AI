/**
 * app/static/js/airdraw.js — JARVIS-style fingertip AirDraw overlay.
 * 
 * Provides interactive glowing gesture/canvas drawing with fingertip tracking,
 * smoothing interpolation, stroke memory, color switching, and clear gestures.
 */

class AirDraw {
  constructor(canvasId = 'airdraw-canvas') {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.active = false;
    this.isDrawing = false;
    this.strokes = [];
    this.currentStroke = [];
    this.currentColor = '#00f0ff';
    this.lineWidth = 4;
    this.glow = true;

    this.initCanvas();
    this.bindEvents();
  }

  initCanvas() {
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
    this.redrawAll();
  }

  toggle(forceState = null) {
    this.active = forceState !== null ? forceState : !this.active;
    if (this.active) {
      this.canvas.classList.add('active');
      document.querySelector('.airdraw-toolbar')?.classList.add('visible');
    } else {
      this.canvas.classList.remove('active');
      document.querySelector('.airdraw-toolbar')?.classList.remove('visible');
    }
    return this.active;
  }

  setColor(color) {
    this.currentColor = color;
  }

  setLineWidth(width) {
    this.lineWidth = width;
  }

  startStroke(x, y) {
    if (!this.active) return;
    this.isDrawing = true;
    this.currentStroke = [{ x, y, color: this.currentColor, width: this.lineWidth }];
  }

  addPoint(x, y) {
    if (!this.active || !this.isDrawing) return;
    const pt = { x, y, color: this.currentColor, width: this.lineWidth };
    this.currentStroke.push(pt);
    this.renderSegment(this.currentStroke);
  }

  endStroke() {
    if (!this.active || !this.isDrawing) return;
    this.isDrawing = false;
    if (this.currentStroke.length > 1) {
      this.strokes.push([...this.currentStroke]);
    }
    this.currentStroke = [];
  }

  clear() {
    this.strokes = [];
    this.currentStroke = [];
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  renderSegment(stroke) {
    if (stroke.length < 2) return;
    const p1 = stroke[stroke.length - 2];
    const p2 = stroke[stroke.length - 1];

    this.ctx.save();
    this.ctx.beginPath();
    this.ctx.moveTo(p1.x, p1.y);
    this.ctx.lineTo(p2.x, p2.y);
    this.ctx.strokeStyle = p2.color;
    this.ctx.lineWidth = p2.width;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';

    if (this.glow) {
      this.ctx.shadowColor = p2.color;
      this.ctx.shadowBlur = 12;
    }
    this.ctx.stroke();
    this.ctx.restore();
  }

  redrawAll() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    for (const stroke of this.strokes) {
      if (stroke.length < 2) continue;
      this.ctx.save();
      this.ctx.beginPath();
      this.ctx.moveTo(stroke[0].x, stroke[0].y);
      for (let i = 1; i < stroke.length; i++) {
        this.ctx.lineTo(stroke[i].x, stroke[i].y);
      }
      this.ctx.strokeStyle = stroke[0].color;
      this.ctx.lineWidth = stroke[0].width;
      this.ctx.lineCap = 'round';
      this.ctx.lineJoin = 'round';
      if (this.glow) {
        this.ctx.shadowColor = stroke[0].color;
        this.ctx.shadowBlur = 12;
      }
      this.ctx.stroke();
      this.ctx.restore();
    }
  }

  bindEvents() {
    // Listen to custom Gesture events from gesture.js
    window.addEventListener('gesture:point', (e) => {
      if (!this.active) return;
      const { x, y, isPinching } = e.detail;
      const canvasX = x * this.canvas.width;
      const canvasY = y * this.canvas.height;

      if (isPinching) {
        if (!this.isDrawing) {
          this.startStroke(canvasX, canvasY);
        } else {
          this.addPoint(canvasX, canvasY);
        }
      } else if (this.isDrawing) {
        this.endStroke();
      }
    });

    window.addEventListener('gesture:clear', () => {
      if (this.active) {
        this.clear();
      }
    });
  }
}

// Global initialization
window.AirDraw = AirDraw;

