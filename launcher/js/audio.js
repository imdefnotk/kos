/*
  K.OS launcher sound: generated ambient music and soft navigation sounds.

  The music is made live with the Web Audio API (slow chords plus occasional
  chimes), so it is original and needs no music files. Each theme color plays
  in its own key.

  To use your own music instead, put a file named ambient.mp3 (or ambient.ogg)
  in the launcher's audio folder. It then loops in place of the generated music.
*/
(function () {
  'use strict';

  var LEVELS = { dusuk: 0.22, orta: 0.4, yuksek: 0.65 };
  var KEYS = { '#E5322D': 50, '#F97316': 52, '#3B82F6': 48, '#22D3EE': 45, '#8B5CF6': 53, '#22C55E': 55 };
  var CHORDS = [[0, 4, 7, 11], [-3, 0, 4, 7], [-7, -3, 0, 4], [-5, 2, 7, 9]];
  var PENTA = [0, 2, 4, 7, 9];

  var ctx = null;
  var master, musicBus, uiBus, reverb, filter;
  var musicOn = true;
  var uiOn = true;
  var level = 'orta';
  var ducked = false;
  var root = 50;
  var chordIndex = 0;
  var nextChord = 0;
  var nextChime = 0;
  var timer = null;
  var track = null;
  var trackChecked = false;

  function freq(midi) { return 440 * Math.pow(2, (midi - 69) / 12); }

  function makeReverb() {
    var len = Math.floor(ctx.sampleRate * 3.5);
    var buf = ctx.createBuffer(2, len, ctx.sampleRate);
    for (var c = 0; c < 2; c++) {
      var d = buf.getChannelData(c);
      for (var i = 0; i < len; i++) { d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 3); }
    }
    var conv = ctx.createConvolver();
    conv.buffer = buf;
    return conv;
  }

  function setup() {
    if (ctx) { return true; }
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) { return false; }
    ctx = new AC();
    var comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -18;
    comp.ratio.value = 3;
    comp.connect(ctx.destination);

    master = ctx.createGain();
    master.gain.value = 0;
    master.connect(comp);

    reverb = makeReverb();
    var wet = ctx.createGain();
    wet.gain.value = 0.55;
    reverb.connect(wet);
    wet.connect(master);

    filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 1100;
    filter.Q.value = 0.4;
    var lfo = ctx.createOscillator();
    var lfoAmt = ctx.createGain();
    lfo.frequency.value = 0.035;
    lfoAmt.gain.value = 450;
    lfo.connect(lfoAmt);
    lfoAmt.connect(filter.frequency);
    lfo.start();

    var lowCut = ctx.createBiquadFilter();
    lowCut.type = 'highpass';
    lowCut.frequency.value = 70;
    lowCut.Q.value = 0.7;
    lowCut.connect(filter);

    musicBus = ctx.createGain();
    musicBus.gain.value = 1;
    musicBus.connect(lowCut);
    filter.connect(master);
    filter.connect(reverb);

    uiBus = ctx.createGain();
    uiBus.gain.value = 1.4;
    uiBus.connect(comp);
    return true;
  }

  function chord(t0) {
    var notes = CHORDS[chordIndex % CHORDS.length].map(function (n) { return root + n; });
    notes.push(root + CHORDS[chordIndex % CHORDS.length][0] - 12);
    chordIndex++;
    var dur = 15;
    notes.forEach(function (m, i) {
      [-6, 6].forEach(function (cents) {
        var o = ctx.createOscillator();
        var g = ctx.createGain();
        o.type = i === notes.length - 1 ? 'sine' : 'triangle';
        o.frequency.value = freq(m);
        o.detune.value = cents;
        var peak = i === notes.length - 1 ? 0.12 : 0.07;
        g.gain.setValueAtTime(0, t0);
        g.gain.linearRampToValueAtTime(peak, t0 + 4.5);
        g.gain.setValueAtTime(peak, t0 + dur - 6);
        g.gain.linearRampToValueAtTime(0, t0 + dur);
        o.connect(g);
        g.connect(musicBus);
        o.start(t0);
        o.stop(t0 + dur + 0.1);
      });
    });
  }

  function chime(t0) {
    var m = root + 24 + PENTA[Math.floor(Math.random() * PENTA.length)] + (Math.random() < 0.3 ? 12 : 0);
    var o = ctx.createOscillator();
    var g = ctx.createGain();
    o.type = 'sine';
    o.frequency.value = freq(m);
    g.gain.setValueAtTime(0, t0);
    g.gain.linearRampToValueAtTime(0.08, t0 + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + 4);
    o.connect(g);
    g.connect(reverb);
    g.connect(master);
    o.start(t0);
    o.stop(t0 + 4.1);
  }

  function schedule() {
    if (!ctx || track) { return; }
    var now = ctx.currentTime;
    if (now + 1.5 >= nextChord) { chord(Math.max(now, nextChord)); nextChord = Math.max(now, nextChord) + 11; }
    if (now + 1.5 >= nextChime) { chime(Math.max(now, nextChime)); nextChime = Math.max(now, nextChime) + 4 + Math.random() * 6; }
  }

  function target() { return musicOn && !ducked ? LEVELS[level] : 0; }

  function applyLevel(seconds) {
    var v = target();
    if (track) {
      fadeTrack(v, seconds);
      if (ctx) { master.gain.setTargetAtTime(0, ctx.currentTime, 0.2); }
      return;
    }
    if (!ctx) { return; }
    var t = ctx.currentTime;
    master.gain.cancelScheduledValues(t);
    master.gain.setValueAtTime(master.gain.value, t);
    master.gain.linearRampToValueAtTime(v, t + (seconds || 1.2));
  }

  var trackFade = null;
  function fadeTrack(v, seconds) {
    clearInterval(trackFade);
    var start = track.volume;
    var steps = Math.max(1, Math.round((seconds || 1.2) * 20));
    var i = 0;
    if (v > 0 && track.paused) { track.play().catch(function () {}); }
    trackFade = setInterval(function () {
      i++;
      track.volume = Math.max(0, Math.min(1, start + (v - start) * (i / steps)));
      if (i >= steps) {
        clearInterval(trackFade);
        if (v === 0) { track.pause(); }
      }
    }, 50);
  }

  function findTrack(done) {
    if (trackChecked) { done(); return; }
    trackChecked = true;
    var names = ['audio/ambient.mp3', 'audio/ambient.ogg', 'audio/kos-idle-ambient.ogg'];
    var i = 0;
    (function next() {
      if (i >= names.length) { done(); return; }
      var a = new Audio();
      var src = names[i++];
      a.preload = 'auto';
      a.oncanplaythrough = function () { a.oncanplaythrough = null; a.onerror = null; a.loop = true; a.volume = 0; track = a; done(); };
      a.onerror = function () { a.oncanplaythrough = null; a.onerror = null; next(); };
      a.src = src;
    })();
  }

  /* Browsers only allow sound after the first button press, key press or click,
     unless the launcher was opened with the K.OS starter file. */
  function wake() {
    if (!setup()) { return; }
    if (ctx.state === 'suspended') { ctx.resume().catch(function () {}); }
    if (track && target() > 0 && track.paused) { track.play().catch(function () {}); }
  }

  window.KOSAudio = {
    start: function (opts) {
      musicOn = opts.music !== false;
      uiOn = opts.ui !== false;
      level = LEVELS[opts.level] ? opts.level : 'orta';
      this.setTheme(opts.theme || '#E5322D');
      if (!setup()) { return; }
      findTrack(function () {
        nextChord = ctx.currentTime + 0.3;
        nextChime = ctx.currentTime + 6;
        timer = setInterval(schedule, 500);
        schedule();
        wake();
        applyLevel(4);
      });
      ['keydown', 'pointerdown'].forEach(function (ev) { window.addEventListener(ev, wake, true); });
    },
    wake: wake,
    setMusic: function (on) { musicOn = on; wake(); applyLevel(1.5); },
    setLevel: function (l) { if (LEVELS[l]) { level = l; applyLevel(0.6); } },
    setUi: function (on) { uiOn = on; },
    setTheme: function (hex) {
      var r = KEYS[String(hex).toUpperCase()];
      root = typeof r === 'number' ? r : 50;
    },
    duck: function (on) {
      if (ducked === on) { return; }
      ducked = on;
      applyLevel(on ? 0.8 : 2.5);
    },
    ui: function (kind) {
      if (!uiOn || !ctx || ctx.state !== 'running') { return; }
      var t = ctx.currentTime;
      var spec = {
        move: [[root + 36, 0, 0.05, 0.06]],
        select: [[root + 31, 0, 0.09, 0.07], [root + 36, 0.06, 0.12, 0.07]],
        back: [[root + 36, 0, 0.08, 0.06], [root + 31, 0.05, 0.12, 0.06]],
        open: [[root + 24, 0, 0.3, 0.06], [root + 31, 0.07, 0.3, 0.05], [root + 36, 0.14, 0.4, 0.05]]
      }[kind];
      if (!spec) { return; }
      spec.forEach(function (n) {
        var o = ctx.createOscillator();
        var g = ctx.createGain();
        o.type = 'sine';
        o.frequency.value = freq(n[0]);
        g.gain.setValueAtTime(0, t + n[1]);
        g.gain.linearRampToValueAtTime(n[3], t + n[1] + 0.008);
        g.gain.exponentialRampToValueAtTime(0.0001, t + n[1] + n[2]);
        o.connect(g);
        g.connect(uiBus);
        if (kind === 'open') { g.connect(reverb); }
        o.start(t + n[1]);
        o.stop(t + n[1] + n[2] + 0.05);
      });
    }
  };
})();
