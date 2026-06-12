const template = document.createElement("template");
template.innerHTML = `
    <style>
      :host { display: block; font-family: var(--paper-font-body1_); }
      ha-card { padding: 12px; }
      .header { display:flex; align-items:center; justify-content:space-between; gap:12px; }
      .title { font-weight: 500; font-size: 16px; }
      .content { display:flex; align-items:center; gap:8px; margin-top:12px; }

      .image { flex: 1 1 auto; display:flex; align-items:center; justify-content:center; }
      .feeder {
        width: 160px;
        height: 256px;
        border-radius: 8px;
        object-fit: cover;
      }

      .info-label {
        font-weight: 600;
        font-size: 18px;
        display: flex; align-items:center;
        justify-content:center;
        color: var(--primary-text-color);
        padding-bottom: 15px;
      }

      .error-label {
        height: 20px;
        text-align: center;
        font-size: 0.85em;
        font-weight: 500;
        line-height: 20px;
      }

      .controls { width: 160px; display:flex; flex-direction:column; gap:12px; align-items:stretch; }
      mwc-button { --mdc-theme-primary: var(--primary-color); width:100%; }
      .small { font-size: 12px; color: var(--secondary-text-color); }

      ha-button {
        width: 100%;
      }
      .snack {
        --mdc-theme-primary: var(--secondary-text-color);
      }

      .status-warning {
        color: #ff9800;
      }

      .status-error {
        color: #f44336;
      }

      /* Timer sectie */
      .timer-section {
        margin-top: 16px;
        border-top: 1px solid var(--divider-color);
        padding-top: 12px;
      }

      .timer-section-title {
        font-weight: 500;
        font-size: 14px;
        color: var(--secondary-text-color);
        margin-bottom: 8px;
      }

      .timer-list {
        display: flex;
        flex-direction: column;
        gap: 6px;
        margin-bottom: 10px;
      }

      .timer-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: var(--secondary-background-color);
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
      }

      .timer-row .timer-time {
        font-weight: 600;
        color: var(--primary-text-color);
      }

      .timer-row .timer-mode {
        color: var(--secondary-text-color);
        font-size: 12px;
        margin-left: 8px;
      }

      .timer-delete {
        background: none;
        border: none;
        color: var(--error-color, #f44336);
        cursor: pointer;
        font-size: 16px;
        padding: 2px 6px;
        border-radius: 4px;
        line-height: 1;
      }

      .timer-delete:hover {
        background: var(--error-color, #f44336);
        color: white;
      }

      .timer-add {
        display: flex;
        gap: 6px;
        align-items: center;
        margin-top: 4px;
      }

      .timer-add input[type="time"] {
        flex: 1;
        padding: 6px 8px;
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 13px;
      }

      .timer-add select {
        padding: 6px 8px;
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 13px;
      }

      .timer-add-btn {
        background: var(--primary-color);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 6px 12px;
        cursor: pointer;
        font-size: 13px;
        font-weight: 500;
      }

      .timer-add-btn:hover {
        opacity: 0.85;
      }

      .timer-add-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }

      .timer-empty {
        font-size: 12px;
        color: var(--secondary-text-color);
        text-align: center;
        padding: 8px 0;
      }

      .timer-max {
        font-size: 11px;
        color: var(--secondary-text-color);
        text-align: right;
        margin-top: 4px;
      }
    </style>
    <ha-card>
      <div class="header">
        <div class="title" id="title">Alfeedo</div>
        <div class="small" id="last_updated"></div>
      </div>
      <div class="content">
        <div class="image">
          <img id="feeder_img" class="feeder" alt="Feeder image" src="">
        </div>

        <div class="controls">
          <div class="info-label" id="state_label">--</div>
          <div class="info-label" id="fill_label">--%</div>
          <div id="status_message" class="error-label"></div>
          <ha-button class="meal" unelevated>Dispense Meal</ha-button>
          <ha-button class="snack" outlined>Dispense Snack</ha-button>
        </div>
      </div>

      <div class="timer-section">
        <div class="timer-section-title">⏰ Timers</div>
        <div class="timer-list" id="timer_list"></div>
        <div class="timer-add">
          <input type="time" id="timer_time" value="08:00">
          <select id="timer_mode">
            <option value="meal">Meal</option>
            <option value="snack">Snack</option>
          </select>
          <button class="timer-add-btn" id="timer_add_btn">+</button>
        </div>
        <div class="timer-max" id="timer_max"></div>
      </div>
    </ha-card>
  `;

// Register the card in Home Assistant's custom card registry early to
// improve discoverability in the UI and reduce race conditions.
window.customCards = window.customCards || [];
window.customCards.push({
  type: "alfeedo-card",
  name: "Alfeedo Card",
  preview: true,
  description: "A custom card to monitor and trigger your Alfeedo cat feeder.",
});
console.debug("alfeedo: customCards pushed");

class AlfeedoCard extends HTMLElement {
  constructor() {
    super();
    this._root = null;
    this._hass = null;
    this._config = null;
    this._entitiesResolved = false;
  }

  connectedCallback() {
    this._ensureRoot();
    if (this._config && this._hass) {
      this.hass = this._hass;
    }
  }

  _ensureRoot() {
    if (this._root) return;
    this._root = this.attachShadow({ mode: "open" });
    this._root.appendChild(template.content.cloneNode(true));

    // Timer add knop
    const addBtn = this._root.getElementById("timer_add_btn");
    if (addBtn) addBtn.onclick = () => this._addTimer();
  }

  _el(id) {
    if (!this._root) this._ensureRoot();
    return this._root ? this._root.getElementById(id) : null;
  }

  setConfig(config) {
    console.debug("alfeedo-card: setConfig called", config);
    if (!config) {
      throw new Error("Invalid configuration");
    }
    this._config = config;

    this._ensureRoot();

    const titleEl = this._el("title");
    if (titleEl) titleEl.textContent = this._config.title || "Alfeedo";

    const imgEl = this._el("feeder_img");
    if (imgEl) {
      imgEl.src = this._config.image || "/alfeedo/ui/img/feeder.png";
    }

    const btnMeal = this._root.querySelector(".meal");
    const btnSnack = this._root.querySelector(".snack");

    if (btnMeal) btnMeal.onclick = () => this._pressButton("meal");
    if (btnSnack) btnSnack.onclick = () => this._pressButton("snack");
  }

  static getConfigElement() {
    return document.createElement("alfeedo-card-editor");
  }

  static getStubConfig() {
    return { entity: "sensor.alfeedo_feeder_state", title: "Alfeedo" };
  }

  _pressButton(feedingType) {
    if (!this._hass || !this._config.entity) return;

    let buttonId;
    if (feedingType === 'meal' && this._config.meal_button) {
      buttonId = this._config.meal_button;
    } else if (feedingType === 'snack' && this._config.snack_button) {
      buttonId = this._config.snack_button;
    } else {
      buttonId = this._config.entity.replace('sensor.', 'button.').replace('_feeder_state', '_feed_' + feedingType);
    }

    this._hass.callService("button", "press", { entity_id: buttonId });
  }

  _addTimer() {
    if (!this._hass) return;
    const timeInput = this._el("timer_time");
    const modeInput = this._el("timer_mode");
    if (!timeInput || !modeInput) return;

    const time = timeInput.value;
    const mode = modeInput.value;
    if (!time) return;

    const addBtn = this._el("timer_add_btn");
    if (addBtn) addBtn.disabled = true;

    this._hass.callService("alfeedo", "add_timer", { time, mode }).then(() => {
      if (addBtn) addBtn.disabled = false;
    }).catch(() => {
      if (addBtn) addBtn.disabled = false;
    });
  }

  _deleteTimer(timerId) {
    if (!this._hass) return;
    this._hass.callService("alfeedo", "delete_timer", { timer_id: timerId });
  }

  _renderTimers(timers, maxTimers) {
    const list = this._el("timer_list");
    const maxEl = this._el("timer_max");
    if (!list) return;

    list.innerHTML = "";

    if (!timers || timers.length === 0) {
      list.innerHTML = `<div class="timer-empty">Geen timers ingesteld</div>`;
    } else {
      timers.forEach(timer => {
        const row = document.createElement("div");
        row.className = "timer-row";
        row.innerHTML = `
          <span class="timer-time">${timer.time}</span>
          <span class="timer-mode">${timer.mode}</span>
          <button class="timer-delete" title="Verwijder timer">✕</button>
        `;
        row.querySelector(".timer-delete").onclick = () => this._deleteTimer(timer.id);
        list.appendChild(row);
      });
    }

    // Verberg add knop als max bereikt
    const addBtn = this._el("timer_add_btn");
    if (addBtn) addBtn.disabled = timers && timers.length >= maxTimers;

    if (maxEl) maxEl.textContent = `${timers ? timers.length : 0} / ${maxTimers} timers`;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;

    this._ensureRoot();

    const stateLabel = this._el("state_label");
    const statusMsg = this._el('status_message');
    const fillLabel = this._el('fill_label');
    const lastUpdated = this._el("last_updated");
    const img = this._el("feeder_img");

    const entity = this._config.entity;
    if (!entity || !hass.states[entity]) {
      if (stateLabel) stateLabel.textContent = "No Entity";
      return;
    }

    const stateObj = hass.states[entity];
    const value = stateObj.state;

    if (stateLabel) stateLabel.textContent = value;

    const fill_level = stateObj.attributes.fill_level;
    const num = Number(fill_level);
    const pct = Number.isFinite(num) ? Math.max(0, Math.min(100, Math.round(num))) : null;
    const errorState = stateObj.attributes.error_state;
    const nextTimer = stateObj.attributes.next_timer;
    const nextTimerMode = stateObj.attributes.next_timer_mode;

    if (pct !== null && fillLabel) {
      fillLabel.textContent = `${pct}%`;
      if (img) {
        let fixedValue = pct;
        if (Math.round(pct) > 0) {
          fixedValue = Math.max(1, Math.round(pct / 10) * 10);
        }
        const fillImg = `/alfeedo/ui/img/feeder transparent ${fixedValue} ${errorState}.png`;
        img.src = fillImg;
      }
    } else if (fillLabel) {
      fillLabel.textContent = `${value}`;
      if (img) img.src = this._config.image || "/alfeedo/ui/img/feeder.png";
    }

    if (statusMsg) {
      switch (errorState) {
        case "ok":
          statusMsg.className = "error-label";
          statusMsg.innerHTML = (nextTimerMode !== "off") ? "Next timer: " + this.formatTime(nextTimer) : "";
          break;
        case "struggling":
          statusMsg.innerText = "The feeder is struggling";
          statusMsg.className = "error-label status-warning";
          break;
        case "jammed":
          statusMsg.innerText = "The feeder may be jammed";
          statusMsg.className = "error-label status-error";
          break;
      }
    }

    if (lastUpdated) {
      lastUpdated.textContent = stateObj.last_updated ? new Date(stateObj.last_updated).toLocaleString() : "";
    }

    // Timers ophalen uit de timers sensor
    const timerEntity = this._config.timers_entity ||
      entity.replace("_feeder_state", "_timers");
    if (timerEntity && hass.states[timerEntity]) {
      const timerState = hass.states[timerEntity];
      const timers = timerState.attributes.timers || [];
      const maxTimers = timerState.attributes.max_timers || 10;
      this._renderTimers(timers, maxTimers);
    }
  }

  getCardSize() {
    return 4;
  }

  formatTime(totalMinutes) {
    const date = new Date();
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    date.setHours(hours, minutes, 0, 0);
    return new Intl.DateTimeFormat(navigator.language, {
      hour: 'numeric',
      minute: '2-digit',
    }).format(date);
  }
}

class AlfeedoCardEditor extends HTMLElement {
  constructor() {
    super();
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;

    if (!this.shadowRoot) this.attachShadow({ mode: "open" });

    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => this._valueChanged(ev));
      this.shadowRoot.appendChild(this._form);

      this._form.computeLabel = (schema) => {
        return schema.label || schema.name;
      };
    }

    const schema = [
      { name: "title", selector: { text: {} } },
      {
        name: "entity",
        label: "Feeder Status Sensor",
        selector: { entity: { domain: "sensor", integration: "alfeedo" } }
      },
      {
        name: "meal_button",
        label: "Meal Button (Optional)",
        selector: { entity: { domain: "button", integration: "alfeedo" } }
      },
      {
        name: "snack_button",
        label: "Snack Button (Optional)",
        selector: { entity: { domain: "button", integration: "alfeedo" } }
      },
      {
        name: "timers_entity",
        label: "Timers Sensor (Optional)",
        selector: { entity: { domain: "sensor", integration: "alfeedo" } }
      },
      { name: "image", label: "Custom Image URL", selector: { text: {} } }
    ];

    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = schema;
  }

  _valueChanged(ev) {
    const event = new CustomEvent("config-changed", {
      detail: { config: ev.detail.value },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

if (!customElements.get("alfeedo-card")) {
  customElements.define("alfeedo-card", AlfeedoCard);
  console.debug("alfeedo-card: defined");
} else {
  console.debug("alfeedo-card: already defined");
}

customElements.define("alfeedo-card-editor", AlfeedoCardEditor);

window.AlfeedoCard = AlfeedoCard;
window.AlfeedoCardEditor = AlfeedoCardEditor;
customElements.whenDefined('alfeedo-card').then(() => console.debug('alfeedo-card: whenDefined'));
console.debug("alfeedo: registered");
