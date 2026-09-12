/**
 * app/static/js/hud.js — Main HUD Controller for SACHA AI V3 Desktop.
 * 
 * Manages streaming responses, pywebview IPC communication, UI state,
 * markdown parsing, personality presets, voice pipeline, settings modal,
 * and gesture/airdraw subsystems.
 */

(function () {
  'use strict';

  // State
  let pywebviewReady = false;
  let isStreaming = false;
  let currentAssistantBubble = null;
  let currentTokenAccumulator = '';
  let airdrawInstance = null;
  let gestureInstance = null;
  let voiceActive = false;

  // DOM Elements
  const messagesContainer = document.getElementById('messages-container');
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const providerPill = document.getElementById('provider-pill');
  const factsPill = document.getElementById('facts-pill');
  const statusDot = document.getElementById('status-dot');
  const presetSelect = document.getElementById('preset-select');
  const voiceBtn = document.getElementById('voice-btn');
  const gestureBtn = document.getElementById('gesture-btn');
  const airdrawBtn = document.getElementById('airdraw-btn');
  const toolsContainer = document.getElementById('tools-container');
  const settingsBtn = document.getElementById('settings-btn');
  const settingsModal = document.getElementById('settings-modal');
  const voiceStatusEl = document.getElementById('voice-status');
  const voiceStatusText = document.getElementById('voice-status-text');

  // Initialize
  function init() {
    setupEventListeners();
    setupInputAutoresize();
    setupSettingsModal();

    if (window.AirDraw) {
      airdrawInstance = new window.AirDraw('airdraw-canvas');
    }
    if (window.GesturePipeline) {
      gestureInstance = new window.GesturePipeline();
    }
  }

  // Pywebview readiness
  window.addEventListener('pywebviewready', () => {
    pywebviewReady = true;
    console.log('[HUD] pywebview bridge ready');
    refreshStatus();
    loadPresets();
    loadHistory();
  });

  // =========================================================================
  // Event Listeners
  // =========================================================================

  function setupEventListeners() {
    sendBtn?.addEventListener('click', handleSend);

    chatInput?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    });

    // Quick prompt chips
    document.querySelectorAll('.prompt-btn, .chip-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const text = btn.getAttribute('data-prompt') || btn.textContent.trim();
        if (chatInput) {
          chatInput.value = text;
          chatInput.focus();
        }
      });
    });

    // Preset selector
    presetSelect?.addEventListener('change', async (e) => {
      if (pywebviewReady && window.pywebview?.api?.set_preset) {
        const res = await window.pywebview.api.set_preset(e.target.value);
        console.log('[HUD] Preset changed:', res);
      }
    });

    // Voice button — start/stop real mic recording
    voiceBtn?.addEventListener('click', async () => {
      if (!pywebviewReady || !window.pywebview?.api) {
        voiceBtn.classList.toggle('active');
        return;
      }

      if (!voiceActive) {
        try {
          const res = await window.pywebview.api.start_voice_listen();
          if (res.status === 'ok') {
            voiceActive = true;
            voiceBtn.classList.add('active', 'voice-recording');
          }
        } catch (err) {
          console.warn('[HUD] Voice start error:', err);
        }
      } else {
        try {
          await window.pywebview.api.stop_voice_listen();
        } catch (err) {
          console.warn('[HUD] Voice stop error:', err);
        }
        voiceActive = false;
        voiceBtn.classList.remove('active', 'voice-recording');
        if (voiceStatusEl) voiceStatusEl.classList.remove('visible');
      }
    });

    // Gesture button — start/stop Python-side hand tracking
    gestureBtn?.addEventListener('click', async () => {
      if (gestureInstance) {
        const active = await gestureInstance.toggle();
        gestureBtn.classList.toggle('active', active);
      }
    });

    // AirDraw button toggle (drawing only works via hand gestures)
    airdrawBtn?.addEventListener('click', () => {
      if (airdrawInstance) {
        const active = airdrawInstance.toggle();
        airdrawBtn.classList.toggle('active', active);
      }
    });

    // AirDraw toolbar color picking
    document.querySelectorAll('.color-dot').forEach((dot) => {
      dot.addEventListener('click', () => {
        document.querySelectorAll('.color-dot').forEach((d) => d.classList.remove('selected'));
        dot.classList.add('selected');
        const color = dot.getAttribute('data-color');
        if (airdrawInstance) {
          airdrawInstance.setColor(color);
        }
      });
    });

    // Window controls
    document.getElementById('btn-minimize')?.addEventListener('click', () => {
      if (pywebviewReady && window.pywebview?.api?.minimize_window) {
        window.pywebview.api.minimize_window();
      }
    });
    document.getElementById('btn-maximize')?.addEventListener('click', () => {
      if (pywebviewReady && window.pywebview?.api?.maximize_window) {
        window.pywebview.api.maximize_window();
      }
    });
    document.getElementById('btn-close')?.addEventListener('click', () => {
      if (pywebviewReady && window.pywebview?.api?.close_window) {
        window.pywebview.api.close_window();
      }
    });
  }

  function setupInputAutoresize() {
    if (!chatInput) return;
    chatInput.addEventListener('input', () => {
      chatInput.style.height = 'auto';
      chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
    });
  }

  // =========================================================================
  // Chat Streaming
  // =========================================================================

  async function handleSend() {
    if (isStreaming) return;
    const text = chatInput?.value?.trim();
    if (!text) return;

    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Remove welcome hero if present
    document.querySelector('.welcome-hero')?.remove();

    appendMessage('user', text);

    currentAssistantBubble = appendMessage('assistant', '', true);
    currentTokenAccumulator = '';
    isStreaming = true;
    updateSendButtonState(true);

    if (pywebviewReady && window.pywebview?.api?.send_message) {
      try {
        const res = await window.pywebview.api.send_message(text);
        if (res.mode === 'sync' && res.text) {
          window.sachaOnToken({ text: res.text, provider: res.provider || 'local' });
          window.sachaOnDone({ provider: res.provider || 'local' });
        }
      } catch (err) {
        window.sachaOnError({ message: String(err) });
      }
    } else {
      setTimeout(() => {
        window.sachaOnToken({ text: `SACHA online. Received: "${text}"`, provider: 'simulation' });
        window.sachaOnDone({ provider: 'simulation', duration_ms: 120 });
      }, 300);
    }
  }

  // Streaming Token Receiver (Called from Python IPC)
  window.sachaOnToken = function (data) {
    if (!currentAssistantBubble) return;
    const token = data.text || '';
    currentTokenAccumulator += token;

    if (data.provider && currentAssistantBubble.parentNode) {
      const badge = currentAssistantBubble.parentNode.querySelector('.provider-badge');
      if (badge) {
        badge.textContent = data.provider;
      }
    }

    renderBubbleContent(currentAssistantBubble, currentTokenAccumulator, true);
    scrollToBottom();
  };

  // Streaming Done Receiver
  window.sachaOnDone = function (data) {
    isStreaming = false;
    updateSendButtonState(false);

    if (currentAssistantBubble) {
      renderBubbleContent(currentAssistantBubble, currentTokenAccumulator, false);
      currentAssistantBubble = null;
    }
    currentTokenAccumulator = '';
    refreshStatus();
  };

  // Streaming Error Receiver
  window.sachaOnError = function (data) {
    isStreaming = false;
    updateSendButtonState(false);

    if (currentAssistantBubble) {
      currentAssistantBubble.innerHTML = `<div style="color: var(--accent-rose);">⚠️ Error: ${escapeHtml(data.message || 'Unknown error')}</div>`;
      currentAssistantBubble = null;
    }
    currentTokenAccumulator = '';
  };

  // =========================================================================
  // Voice Pipeline Callbacks (Called from Python IPC)
  // =========================================================================

  window.sachaOnVoiceStatus = function (data) {
    if (!voiceStatusEl || !voiceStatusText) return;

    const state = data.state || 'idle';
    const text = data.text || '';

    if (state === 'idle') {
      voiceStatusEl.classList.remove('visible');
      voiceActive = false;
      voiceBtn?.classList.remove('active', 'voice-recording');
    } else {
      voiceStatusEl.classList.add('visible');
      voiceStatusEl.className = `voice-status visible voice-${state}`;
      voiceStatusText.textContent = text;
    }

    if (state === 'recording') {
      voiceBtn?.classList.add('voice-recording');
    } else if (state === 'transcribing') {
      voiceBtn?.classList.remove('voice-recording');
      voiceBtn?.classList.add('voice-transcribing');
    } else if (state === 'speaking') {
      voiceBtn?.classList.remove('voice-recording', 'voice-transcribing');
      voiceBtn?.classList.add('voice-speaking');
    } else {
      voiceBtn?.classList.remove('voice-recording', 'voice-transcribing', 'voice-speaking');
    }
  };

  window.sachaOnVoiceMessage = function (data) {
    // Display the user's voice message in the chat
    document.querySelector('.welcome-hero')?.remove();

    if (data.role === 'user') {
      appendMessage('user', `🎤 ${data.text}`);
      // Create assistant bubble for the upcoming streamed reply
      currentAssistantBubble = appendMessage('assistant', '', true);
      currentTokenAccumulator = '';
      isStreaming = true;
      updateSendButtonState(true);
    }
  };

  // =========================================================================
  // Settings Modal
  // =========================================================================

  function setupSettingsModal() {
    settingsBtn?.addEventListener('click', openSettings);
    document.getElementById('settings-close')?.addEventListener('click', closeSettings);
    document.getElementById('settings-cancel')?.addEventListener('click', closeSettings);
    document.getElementById('settings-save')?.addEventListener('click', saveSettings);

    // Close on backdrop click
    settingsModal?.addEventListener('click', (e) => {
      if (e.target === settingsModal) closeSettings();
    });

    // Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && settingsModal?.classList.contains('visible')) {
        closeSettings();
      }
    });
  }

  async function openSettings() {
    if (!settingsModal) return;
    settingsModal.classList.add('visible');

    if (pywebviewReady && window.pywebview?.api?.get_settings) {
      try {
        const settings = await window.pywebview.api.get_settings();
        populateSettingsForm(settings);
      } catch (err) {
        console.warn('[HUD] Settings fetch error:', err);
      }
    }

    // Load available local models
    if (pywebviewReady && window.pywebview?.api?.get_available_models) {
      try {
        const models = await window.pywebview.api.get_available_models();
        populateModelDropdowns(models);
      } catch (err) {
        console.warn('[HUD] Models fetch error:', err);
      }
    }
  }

  function closeSettings() {
    settingsModal?.classList.remove('visible');
  }

  function populateSettingsForm(settings) {
    const providerSelect = document.getElementById('setting-default-provider');
    const localModelSelect = document.getElementById('setting-local-model');
    const localUrlInput = document.getElementById('setting-local-url');
    const sttSelect = document.getElementById('setting-stt-engine');
    const ttsSelect = document.getElementById('setting-tts-engine');

    if (providerSelect) providerSelect.value = settings.default_provider || 'local';
    if (localUrlInput) localUrlInput.value = settings.local_base_url || 'http://localhost:11434';
    if (sttSelect) sttSelect.value = settings.stt_engine || 'faster_whisper';
    if (ttsSelect) ttsSelect.value = settings.tts_engine || 'piper';

    // Show key status indicators
    updateKeyStatus('gemini', settings.gemini_key_set);
    updateKeyStatus('openai', settings.openai_key_set);
    updateKeyStatus('nvidia', settings.nvidia_key_set);

    // Clear key inputs (only show if user wants to change)
    document.getElementById('setting-gemini-key').value = '';
    document.getElementById('setting-openai-key').value = '';
    document.getElementById('setting-nvidia-key').value = '';
    document.getElementById('setting-gemini-key').placeholder = settings.gemini_key_set ? '●●●●●●●● (saved)' : 'Enter Gemini API key...';
    document.getElementById('setting-openai-key').placeholder = settings.openai_key_set ? '●●●●●●●● (saved)' : 'Enter OpenAI API key...';
    document.getElementById('setting-nvidia-key').placeholder = settings.nvidia_key_set ? '●●●●●●●● (saved)' : 'Enter NVIDIA API key...';
  }

  function updateKeyStatus(provider, isSet) {
    const el = document.getElementById(`${provider}-key-status`);
    if (!el) return;
    if (isSet) {
      el.textContent = '✓';
      el.className = 'key-status key-set';
    } else {
      el.textContent = '✗';
      el.className = 'key-status key-unset';
    }
  }

  function populateModelDropdowns(models) {
    const localModelSelect = document.getElementById('setting-local-model');
    if (!localModelSelect) return;

    const currentVal = localModelSelect.value;
    localModelSelect.innerHTML = '';

    const localModels = models.local || [];
    if (localModels.length === 0) {
      localModels.push('llama3');
    }
    localModels.forEach((m) => {
      const opt = document.createElement('option');
      opt.value = m;
      opt.textContent = m;
      localModelSelect.appendChild(opt);
    });

    // Restore previous selection
    if (currentVal && localModels.includes(currentVal)) {
      localModelSelect.value = currentVal;
    }
  }

  async function saveSettings() {
    if (!pywebviewReady || !window.pywebview?.api?.save_settings) {
      closeSettings();
      return;
    }

    const data = {};
    const providerSelect = document.getElementById('setting-default-provider');
    const localModelSelect = document.getElementById('setting-local-model');
    const localUrlInput = document.getElementById('setting-local-url');
    const sttSelect = document.getElementById('setting-stt-engine');
    const ttsSelect = document.getElementById('setting-tts-engine');
    const geminiKey = document.getElementById('setting-gemini-key')?.value?.trim();
    const openaiKey = document.getElementById('setting-openai-key')?.value?.trim();
    const nvidiaKey = document.getElementById('setting-nvidia-key')?.value?.trim();

    if (providerSelect) data.default_provider = providerSelect.value;
    if (localModelSelect) data.local_model = localModelSelect.value;
    if (localUrlInput) data.local_base_url = localUrlInput.value;
    if (sttSelect) data.stt_engine = sttSelect.value;
    if (ttsSelect) data.tts_engine = ttsSelect.value;

    // Only send keys if the user actually typed something
    if (geminiKey) data.gemini_api_key = geminiKey;
    if (openaiKey) data.openai_api_key = openaiKey;
    if (nvidiaKey) data.nvidia_api_key = nvidiaKey;

    try {
      const settingsJson = JSON.stringify(data);
      const res = await window.pywebview.api.save_settings(settingsJson);
      if (res.status === 'ok') {
        console.log('[HUD] Settings saved successfully');
        closeSettings();
        // Refresh status to show updated providers
        setTimeout(refreshStatus, 500);
      } else {
        console.warn('[HUD] Settings save error:', res.message);
        alert('Failed to save settings: ' + (res.message || 'Unknown error'));
      }
    } catch (err) {
      console.warn('[HUD] Settings save error:', err);
    }
  }

  // =========================================================================
  // UI Helpers
  // =========================================================================

  function appendMessage(role, content, isStreamingBubble = false) {
    const row = document.createElement('div');
    row.className = `msg-row ${role}`;

    const meta = document.createElement('div');
    meta.className = 'msg-meta';
    meta.innerHTML = `
      <span>${role === 'user' ? 'You' : 'SACHA AI'}</span>
      ${role === 'assistant' ? '<span class="provider-badge">neural</span>' : ''}
    `;

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';

    if (content) {
      renderBubbleContent(bubble, content, isStreamingBubble);
    } else if (isStreamingBubble) {
      bubble.innerHTML = '<span class="streaming-cursor"></span>';
    }

    row.appendChild(meta);
    row.appendChild(bubble);
    messagesContainer?.appendChild(row);
    scrollToBottom();

    return bubble;
  }

  function renderBubbleContent(element, rawText, showCursor = false) {
    let formatted = formatMarkdown(rawText);
    if (showCursor) {
      formatted += '<span class="streaming-cursor"></span>';
    }
    element.innerHTML = formatted;
  }

  function formatMarkdown(text) {
    if (!text) return '';
    let escaped = escapeHtml(text);

    // Code blocks ```code```
    escaped = escaped.replace(/```([\s\S]*?)```/g, (match, code) => {
      return `<pre><code>${code.trim()}</code></pre>`;
    });

    // Inline code `code`
    escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold **text**
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic *text*
    escaped = escaped.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Paragraphs & Line Breaks
    escaped = escaped.replace(/\n\n+/g, '</p><p>');
    escaped = escaped.replace(/\n/g, '<br>');

    return `<p>${escaped}</p>`;
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function scrollToBottom() {
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  function updateSendButtonState(streaming) {
    if (sendBtn) {
      sendBtn.disabled = streaming;
      sendBtn.style.opacity = streaming ? '0.5' : '1';
    }
  }

  // =========================================================================
  // Status & Data Refresh
  // =========================================================================

  async function refreshStatus() {
    if (!pywebviewReady || !window.pywebview?.api?.get_status) return;
    try {
      const status = await window.pywebview.api.get_status();
      if (providerPill && status.settings?.default_provider) {
        providerPill.textContent = status.settings.default_provider.toUpperCase();
      }
      if (factsPill && status.memory?.facts !== undefined) {
        factsPill.textContent = `${status.memory.facts} Facts`;
      }
      if (statusDot) {
        statusDot.classList.remove('offline');
      }

      // Show configured providers count
      if (status.router?.configured_providers) {
        const count = status.router.configured_providers.length;
        if (providerPill) {
          providerPill.title = `${count} provider(s): ${status.router.configured_providers.join(', ')}`;
        }
      }

      // Populate tools
      if (toolsContainer && status.tools && Array.isArray(status.tools)) {
        toolsContainer.innerHTML = status.tools
          .map((t) => `<div class="tool-chip"><span>!${escapeHtml(t)}</span></div>`)
          .join('');
      }
    } catch (err) {
      console.warn('[HUD] Status fetch error:', err);
    }
  }

  async function loadPresets() {
    if (!pywebviewReady || !window.pywebview?.api?.get_presets || !presetSelect) return;
    try {
      const presets = await window.pywebview.api.get_presets();
      presetSelect.innerHTML = presets
        .map((p) => `<option value="${p}">${p.charAt(0).toUpperCase() + p.slice(1)}</option>`)
        .join('');
    } catch (err) {
      console.warn('[HUD] Presets fetch error:', err);
    }
  }

  async function loadHistory() {
    if (!pywebviewReady || !window.pywebview?.api?.get_history) return;
    try {
      const history = await window.pywebview.api.get_history();
      if (history && history.length > 0) {
        document.querySelector('.welcome-hero')?.remove();
        history.forEach((msg) => {
          appendMessage(msg.role, msg.content, false);
        });
      }
    } catch (err) {
      console.warn('[HUD] History fetch error:', err);
    }
  }

  // Boot UI
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
