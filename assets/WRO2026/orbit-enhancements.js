/* ========================================================
   ORBIT · LOCAL ENHANCEMENTS
   Cargar SIEMPRE después de app.js. Sin build, sin servidor,
   sin dependencias externas. Todo se guarda en localStorage.
   ======================================================== */
(function () {
  'use strict';

  // ----------------------------------------------------------
  // 1. Persistencia local
  // ----------------------------------------------------------
  const SCORE_KEY = 'orbit.scores.v1';
  const PROGRESS_KEY = 'orbit.progress.v1';

  function readJSON(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (_) {
      return fallback;
    }
  }

  function writeJSON(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) {}
  }

  const scores = readJSON(SCORE_KEY, {});
  const savedProgress = readJSON(PROGRESS_KEY, null);

  if (savedProgress && typeof state !== 'undefined') {
    if (Array.isArray(savedProgress.completedLessons)) {
      state.completedLessons = savedProgress.completedLessons;
    }
    if (Number.isInteger(savedProgress.currentLessonIndex)) {
      state.currentLessonIndex = savedProgress.currentLessonIndex;
    }
  }

  function saveProgress() {
    writeJSON(PROGRESS_KEY, {
      completedLessons: state.completedLessons.slice(),
      currentLessonIndex: state.currentLessonIndex
    });
  }

  // ----------------------------------------------------------
  // 2. Los timers mueren al cambiar de pantalla / pestaña
  //    (evita que una locución anterior suene encima de la nueva)
  // ----------------------------------------------------------
  window.__orbitTracking = true;

  function advanceEpoch() {
    if (typeof window.__orbitAdvance === 'function') window.__orbitAdvance();
  }

  ['openApp', 'goToHome', 'switchTab'].forEach(function (name) {
    const original = window[name];
    if (typeof original !== 'function') return;
    window[name] = function () {
      advanceEpoch();
      return original.apply(this, arguments);
    };
  });

  // ----------------------------------------------------------
  // 2b. APRENDE CON ORBIT: elegir idioma ANTES de mostrar la app
  // ----------------------------------------------------------
  const LANG_KEY = 'orbit.learning.lang.v1';
  let selectedLang = null;
  try { selectedLang = localStorage.getItem(LANG_KEY); } catch (_) {}
  if (selectedLang !== 'karina' && selectedLang !== 'taino') selectedLang = null;

  const openAppBase = window.openApp;
  const goToHomeBase = window.goToHome;
  const switchTabBase = window.switchTab;
  const originalRenderPath = window.renderPath;

  function setCoreStatus(text) {
    const el = document.getElementById('robot-hud-core-status');
    if (el) el.innerText = text;
  }

  function scrubBranding(root) {
    const target = root || document;
    if (!target || !document.createTreeWalker) return;
    const walker = document.createTreeWalker(target, NodeFilter.SHOW_TEXT, null);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    const oldUpper = 'DUOLI' + 'NGO' + 'RBIT';
    const oldTitle = 'Duoli' + 'ngo' + 'rbit';
    const upperRe = new RegExp(oldUpper, 'g');
    const titleRe = new RegExp(oldTitle, 'g');
    nodes.forEach(function (node) {
      const next = node.nodeValue
        .replace(upperRe, 'APRENDE CON ORBIT')
        .replace(titleRe, 'Aprende con ORBIT');
      if (next !== node.nodeValue) node.nodeValue = next;
    });
  }

  function langLabel() {
    return selectedLang === 'karina' ? "Kari'ña" : 'Taíno';
  }

  function filterPath() {
    const container = document.getElementById('path-container');
    if (!container || !selectedLang || typeof lessonDatabase === 'undefined') return;
    Array.prototype.forEach.call(container.children, function (node, idx) {
      const lesson = lessonDatabase[idx];
      if (!lesson) return;
      const visible = Boolean(lesson.isTrophy) || lesson.lang === selectedLang;
      node.style.display = visible ? '' : 'none';
    });
  }

  function applyDictionaryFilter() {
    if (!selectedLang || typeof window.filterDictionaryLang !== 'function') return;
    window.filterDictionaryLang(selectedLang);
  }

  function updateUnitBanner() {
    if (!selectedLang) return;
    const isKarina = selectedLang === 'karina';
    const title = document.querySelector('#view-aprender h2');
    if (title) title.textContent = isKarina ? "Fundamentos Kari'ña" : "Fundamentos Taíno";
    const desc = title && title.nextElementSibling;
    if (desc && desc.tagName === 'P') {
      desc.textContent = isKarina
        ? "Saludos, familia, naturaleza y tradiciones ancestrales del oriente venezolano."
        : "Palabras, vida y tradiciones ancestrales de nuestros pueblos Taínos del Caribe.";
    }
  }

  function applyLanguageFilters() {
    filterPath();
    applyDictionaryFilter();
    updateUnitBanner();
    setCoreStatus('APRENDE CON ORBIT · ' + langLabel().toUpperCase() + ' MODE');
  }

  function showLanguageSelect() {
    const select = document.getElementById('screen-select-lang');
    ['screen-launcher', 'screen-app-idioma', 'screen-app-canta'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.classList.add('hidden');
    });
    if (select) select.classList.remove('hidden');
    if (typeof updateDockHighlight === 'function') updateDockHighlight('home');
    state.activeScreen = 'select-lang';
    setCoreStatus("CHOOSE TO LEARN: KARI'ÑA OR TAÍNO");
    if (select) {
      const buttons = select.querySelectorAll('.lang-choice-btn');
      Array.prototype.forEach.call(buttons, function (btn, idx) {
        const chosen = (idx === 0 && selectedLang === 'karina') ||
                       (idx === 1 && selectedLang === 'taino');
        btn.classList.toggle('lang-selected', chosen);
      });
    }
    scrubBranding(document);
  }
  window.showLanguageSelect = showLanguageSelect;

  window.chooseLearningLanguage = function (lang) {
    const value = String(lang || '').toLowerCase()
      .replace(/[â€™']/g, '')
      .replace(/í/g, 'i')
      .replace(/á/g, 'a')
      .replace(/ñ/g, 'n');
    if (value !== 'karina' && value !== 'taino') return false;

    selectedLang = value;
    try { localStorage.setItem(LANG_KEY, value); } catch (_) {}

    const select = document.getElementById('screen-select-lang');
    if (select) select.classList.add('hidden');
    const root = document.getElementById('orbit-robot-root');
    if (root) root.classList.add('in-app-mode');

    advanceEpoch();
    let result;
    if (typeof openAppBase === 'function') result = openAppBase.call(this, 'idioma');
    if (typeof window.setVisualLang === 'function') window.setVisualLang(value);
    applyLanguageFilters();

    // Aterrizaje en pestaña según parámetro o por defecto tarjetas
    const params = (typeof URLSearchParams !== 'undefined') ? new URLSearchParams(window.location.search) : null;
    const targetTab = (params && params.get('tab')) ? params.get('tab') : 'tarjetas';
    if (typeof window.switchTab === 'function') window.switchTab(targetTab);
    if (targetTab === 'tarjetas' && typeof window.startVisualChallenge === 'function') {
      window.startVisualChallenge();
    }
    setCoreStatus('VISUAL CARDS · ' + langLabel().toUpperCase() + ' MODE');
    scrubBranding(document);
    return result;
  };

  if (typeof openAppBase === 'function') {
    window.openApp = function (appName) {
      if (appName === 'idioma') {
        showLanguageSelect();
        return;
      }
      return openAppBase.apply(this, arguments);
    };
  }

  if (typeof goToHomeBase === 'function') {
    window.goToHome = function () {
      const select = document.getElementById('screen-select-lang');
      if (select) select.classList.add('hidden');
      const root = document.getElementById('orbit-robot-root');
      if (root) root.classList.remove('in-app-mode');
      return goToHomeBase.apply(this, arguments);
    };
  }

  if (typeof switchTabBase === 'function') {
    window.switchTab = function (tabName) {
      const result = switchTabBase.apply(this, arguments);
      if (tabName === 'practica') applyDictionaryFilter();
      return result;
    };
  }

  if (typeof originalRenderPath === 'function') {
    window.renderPath = function () {
      const result = originalRenderPath.apply(this, arguments);
      filterPath();
      return result;
    };
  }

  // ----------------------------------------------------------
  // 3. Precisión real + progreso persistente
  // ----------------------------------------------------------
  function hasAnswer() {
    const q = currentLesson && currentLesson.questions[currentQIndex];
    if (!q) return false;
    if (q.type === 'choice' || q.type === 'image_choice' || q.type === 'listen_image') {
      return userSelection !== null;
    }
    if (q.type === 'translate') return wordBankSelected.length > 0;
    if (q.type === 'match') return true; // solo se comprueba al completar todas
    return false;
  }

  function answerIsCorrect() {
    const q = currentLesson && currentLesson.questions[currentQIndex];
    if (!q) return false;
    if (q.type === 'choice' || q.type === 'image_choice' || q.type === 'listen_image') {
      return !!(q.options[userSelection] && q.options[userSelection].correct);
    }
    if (q.type === 'translate') {
      const got = wordBankSelected.map(function (w) { return w.token; });
      return got.length === q.correctSentence.length &&
        got.every(function (w, i) { return w === q.correctSentence[i]; });
    }
    if (q.type === 'match') return matchedPairsCount === q.pairs.length;
    return false;
  }

  const originalCheckAnswer = window.checkAnswer;
  window.checkAnswer = function () {
    if (currentLesson && hasAnswer()) {
      const entry = scores[currentLesson.id] || (scores[currentLesson.id] = { correct: 0, total: 0 });
      entry.total += 1;
      if (answerIsCorrect()) entry.correct += 1;
      writeJSON(SCORE_KEY, scores);
    }
    return originalCheckAnswer.apply(this, arguments);
  };

  const originalStartLesson = window.startLesson;
  window.startLesson = function (lessonIndex) {
    if (scores[lessonIndex]) {
      delete scores[lessonIndex];
      writeJSON(SCORE_KEY, scores);
    }
    return originalStartLesson.apply(this, arguments);
  };

  const originalVictory = window.showVictoryScreen;
  window.showVictoryScreen = function () {
    const result = originalVictory.apply(this, arguments);
    const entry = scores[currentLesson.id] || { correct: 0, total: 0 };
    const pct = entry.total ? Math.round((entry.correct / entry.total) * 100) : 100;

    const accuracyEl = document.querySelector('#question-container .text-2xl');
    if (accuracyEl) {
      accuracyEl.textContent = 'ðŸŽ¯ ' + pct + '%';
      const box = accuracyEl.parentElement;
      if (box && !box.querySelector('.orbit-score-detail')) {
        const detail = document.createElement('p');
        detail.className = 'orbit-score-detail text-xs font-bold text-emerald-700 mt-2';
        detail.textContent = entry.correct + ' de ' + entry.total + ' respuestas correctas';
        box.appendChild(detail);
      }
    }

    state.completedLessons = Array.from(new Set(
      state.completedLessons.concat([currentLesson.id])
    ));
    if (currentLesson.id >= state.currentLessonIndex &&
        currentLesson.id < lessonDatabase.length - 1) {
      state.currentLessonIndex = currentLesson.id + 1;
    }
    saveProgress();
    renderPath();
    return result;
  };

  // ----------------------------------------------------------
  // 4. Karaoke: pausa y reanuda de verdad (no vuelve al compás 1)
  // ----------------------------------------------------------
  let savedPosition = null;
  let pendingRestore = null;

  const originalStartLoop = window.startKaraokeLoop;
  window.startKaraokeLoop = function () {
    const restore = pendingRestore;
    pendingRestore = null;
    const result = originalStartLoop.apply(this, arguments);
    if (restore) {
      karaokeState.stepCounter = restore.step;
      karaokeState.currentLyricIdx = restore.lyric;
    }
    return result;
  };

  const originalTogglePlay = window.toggleKaraokePlay;
  window.toggleKaraokePlay = function () {
    const wasPlaying = karaokeState.isPlaying;
    if (!wasPlaying && savedPosition) {
      pendingRestore = savedPosition;
      savedPosition = null;
    }
    const result = originalTogglePlay.apply(this, arguments);
    if (wasPlaying) {
      savedPosition = {
        step: karaokeState.stepCounter,
        lyric: karaokeState.currentLyricIdx
      };
    }
    return result;
  };

  const originalSelectSong = window.selectKaraokeSong;
  window.selectKaraokeSong = function () {
    savedPosition = null;
    pendingRestore = null;
    const result = originalSelectSong.apply(this, arguments);
    scrubBranding(document);
    return result;
  };

  // ----------------------------------------------------------
  // 5. Estado del robot: 1s en vez de 10ms + pausa en segundo plano
  // ----------------------------------------------------------
  ROBOT_STATUS.refreshMs = 1000;

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      stopRobotStatus();
    } else if (state.activeScreen === 'idioma' && state.activeTab === 'robot') {
      startRobotStatus();
    }
  });

  // ----------------------------------------------------------
  // 6. Accesibilidad mínima sin tocar styles.css
  // ----------------------------------------------------------
  const extraCSS = document.createElement('style');
  extraCSS.textContent = [
    ':focus-visible{outline:3px solid #38bdf8;outline-offset:2px}',
    '.dict-card,.dict-card *,.flashcard,.flashcard *{user-select:text!important}',
    '@media(prefers-reduced-motion:reduce){.karaoke-dancer.dancing{animation:none!important}}'
  ].join('\n');
  document.head.appendChild(extraCSS);

  function decorateClickables() {
    scrubBranding(document);
    document.querySelectorAll('[onclick]').forEach(function (el) {
      if (/^(BUTTON|A|INPUT|TEXTAREA|SELECT)$/.test(el.tagName)) return;
      if (!el.hasAttribute('tabindex')) {
        el.setAttribute('tabindex', '0');
        el.setAttribute('role', 'button');
      }
    });
  }

  if ('MutationObserver' in window) {
    new MutationObserver(decorateClickables).observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const el = e.target.closest && e.target.closest('[onclick][role="button"]');
    if (!el) return;
    e.preventDefault();
    el.click();
  });

  // ----------------------------------------------------------
  // 7. Arranque
  // ----------------------------------------------------------
  window.addEventListener('DOMContentLoaded', function () {
    const bubble = document.getElementById('launcher-mascot-speech');
    if (bubble) bubble.setAttribute('aria-live', 'polite');
    scrubBranding(document);
    renderPath();
  });


})();
