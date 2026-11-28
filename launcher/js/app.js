/*
  K.OS launcher (phase 2: real Steam games through the K.OS Home helper).
  Controls:
    Controller: D-pad or left stick to move, A to select, B to go back,
                LB / RB to switch sections, Start or Menu button for the Power menu.
    Keyboard:   arrow keys to move, Enter to select, Escape or Backspace to go back,
                Q / E to switch sections, P for the Power menu.
*/
(function () {
  'use strict';

  var D = window.KOS_DATA;
  var stage = document.getElementById('stage');
  var root = document.documentElement;

  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  /* ---------- Saved settings (kept in the browser on this machine) ---------- */

  var saved = {
    get: function (k, d) {
      try { var v = localStorage.getItem('kos.' + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; }
    },
    set: function (k, v) {
      try { localStorage.setItem('kos.' + k, JSON.stringify(v)); } catch (e) { /* storage unavailable: setting lasts until reload */ }
    }
  };

  var state = {
    screen: 'home',
    focused: null,
    overlay: null,
    beforeOverlay: null,
    settingsCat: 'baglanti',
    storeFilter: 'hepsi',
    installed: saved.get('installed', {}),
    installing: {},
    memory: {},
    padConnected: false,
    online: navigator.onLine,
    running: null,
    picker: null,
    ctl: null
  };

  var prefs = {
    accent: saved.get('accent', '#E5322D'),
    motion: saved.get('motion', true),
    autoBest: saved.get('autoBest', true),
    hdr: saved.get('hdr', false),
    textSize: saved.get('textSize', 'buyuk'),
    music: saved.get('music', true),
    musicLevel: saved.get('musicLevel', 'orta'),
    uiSounds: saved.get('uiSounds', true),
    gameArt: saved.get('gameArt', true)
  };

  /* ---------- Fit the 1920x1080 design to any window ---------- */

  function fit() {
    var s = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    stage.style.transform = 'translate(-50%, -50%) scale(' + s + ')';
  }
  window.addEventListener('resize', fit);
  fit();

  /* ---------- Icons ---------- */

  var ICON = {
    play: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"></rect><path d="M10 9.5v5l4.5-2.5z" fill="currentColor"></path></svg>',
    cloud: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 18h10a4 4 0 0 0 .5-8 5.5 5.5 0 0 0-10.6-1A4.5 4.5 0 0 0 7 18z"></path></svg>',
    globe: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M3 12h18"></path><path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18z"></path></svg>',
    swap: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h14"></path><path d="M15 4l4 4-4 4"></path><path d="M20 16H6"></path><path d="M9 12l-4 4 4 4"></path></svg>',
    grid: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1.5"></rect><rect x="14" y="3" width="7" height="7" rx="1.5"></rect><rect x="3" y="14" width="7" height="7" rx="1.5"></rect><rect x="14" y="14" width="7" height="7" rx="1.5"></rect></svg>',
    more: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="12" r="2"></circle><circle cx="12" cy="12" r="2"></circle><circle cx="19" cy="12" r="2"></circle></svg>',
    check: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg>',
    wifi: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 9a15 15 0 0 1 20 0"></path><path d="M5.5 12.5a10 10 0 0 1 13 0"></path><path d="M9 16a5 5 0 0 1 6 0"></path><circle cx="12" cy="19.5" r="0.8" fill="currentColor"></circle></svg>',
    wifiOff: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3l18 18"></path><path d="M9 16a5 5 0 0 1 6 0"></path><path d="M5.5 12.5a10 10 0 0 1 4-2.2"></path><path d="M2 9a15 15 0 0 1 5.5-3.3"></path><circle cx="12" cy="19.5" r="0.8" fill="currentColor"></circle></svg>',
    pad: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 8h12a4 4 0 0 1 4 4v1a4 4 0 0 1-7 2.6L14 14h-4l-1 1.6A4 4 0 0 1 2 13v-1a4 4 0 0 1 4-4z"></path><path d="M7 11v3M5.5 12.5h3"></path></svg>'
  };

  /* ---------- Theme color ---------- */

  function hexToRgb(hex) {
    var h = String(hex).replace('#', '');
    if (h.length === 3) { h = h.split('').map(function (c) { return c + c; }).join(''); }
    return [parseInt(h.slice(0, 2), 16) || 0, parseInt(h.slice(2, 4), 16) || 0, parseInt(h.slice(4, 6), 16) || 0];
  }

  function applyTheme(hex) {
    prefs.accent = hex;
    root.style.setProperty('--accent', hex);
    root.style.setProperty('--accent-rgb', hexToRgb(hex).join(', '));
    saved.set('accent', hex);
    if (window.KOSAudio) { KOSAudio.setTheme(hex); }
    $$('.swatch').forEach(function (s) {
      s.setAttribute('aria-checked', s.dataset.hex.toUpperCase() === hex.toUpperCase() ? 'true' : 'false');
    });
  }

  function applyMotion() {
    stage.classList.toggle('no-motion', !prefs.motion);
  }

  /* ---------- Private demo art ----------
     If launcher/demo-art/<id>.png (or .jpg, .webp, .svg) exists, it replaces
     the built-in K.OS tile art. That folder is kept out of Git on purpose. */

  var demoArt = {};
  function findDemoArt(id, done) {
    var exts = ['png', 'jpg', 'webp', 'svg'];
    var i = 0;
    (function next() {
      if (i >= exts.length) { done(null); return; }
      var src = 'demo-art/' + id + '.' + exts[i++];
      var img = new Image();
      img.onload = function () { done(src); };
      img.onerror = next;
      img.src = src;
    })();
  }
  function loadDemoArt(after) {
    var sample = D.games.filter(function (g) { return !g.live; });
    var ids = D.apps.map(function (a) { return a.id; })
      .concat(sample.map(function (g) { return g.id; }))
      .concat(sample.filter(function (g) { return g.steamAppId; }).map(function (g) { return g.id + '-hero'; }));
    var left = ids.length;
    if (!left) { after(); return; }
    ids.forEach(function (id) {
      findDemoArt(id, function (src) {
        if (src) { demoArt[id] = src; }
        if (--left === 0) { after(); }
      });
    });
  }

  /* ---------- Real game library (phase 2) ----------
     Opened through the K.OS Home helper (http://127.0.0.1:47800/), the launcher
     gets the installed Steam games, play time and pictures from the drive, and
     can start games. Opened as a plain file, the sample games stay. */

  var live = { on: false, platform: null, games: false, sig: '' };
  var base = { home: D.home.slice(), soon: D.games.filter(function (g) { return g.soon; }) };
  var HOME_RECENT = 5;

  // Trace lines into the helper log (seen with kos-diag), to find launch problems
  function trace(msg) {
    if (!live.on) { return; }
    try {
      api('/api/log', { method: 'POST', body: JSON.stringify({ m: msg + ' [overlay=' + (state.overlay || '-') + ' focus=' + document.hasFocus() + ']' }) }).catch(function () {});
    } catch (e) { /* tracing must never break K.OS Home */ }
  }

  function api(path, opts) {
    opts = opts || {};
    var ctrl = window.AbortController ? new AbortController() : null;
    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, opts.timeout || 6000) : null;
    var headers = opts.method === 'POST' ? { 'X-KOS': '1' } : {};
    if (opts.body) { headers['Content-Type'] = 'application/json'; }
    return fetch(path, {
      method: opts.method || 'GET',
      headers: headers,
      body: opts.body,
      cache: 'no-store',
      signal: ctrl ? ctrl.signal : undefined
    }).then(function (r) {
      if (timer) { clearTimeout(timer); }
      return r.json();
    });
  }

  function playedText(min) {
    if (!min) { return 'Hiç oynanmadı'; }
    if (min < 60) { return min + ' dakika oynandı'; }
    return Math.round(min / 60) + ' saat oynandı';
  }

  function lastText(ts) {
    if (!ts) { return 'Yeni'; }
    var days = Math.floor((Date.now() - ts * 1000) / 86400000);
    if (days <= 0) { return 'Son oynama: bugün'; }
    if (days === 1) { return 'Son oynama: dün'; }
    if (days < 7) { return 'Son oynama: ' + days + ' gün önce'; }
    if (days < 30) { return 'Son oynama: ' + Math.floor(days / 7) + ' hafta önce'; }
    try { return 'Son oynama: ' + new Date(ts * 1000).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' }); }
    catch (e) { return ''; }
  }

  function sizeText(bytes) {
    var gb = (bytes || 0) / 1e9;
    if (gb < 0.1) { return ''; }
    return (gb < 10 ? gb.toFixed(1) : String(Math.round(gb))).replace('.', ',') + ' GB';
  }

  function applyLibrary(lib) {
    var real = lib.games.map(function (s) {
      return {
        id: 'steam-' + s.appid, steamAppId: s.appid, live: true,
        name: s.name, short: esc(s.name),
        played: playedText(s.playtimeMin),
        save: s.updating ? 'Güncelleniyor' : lastText(s.lastPlayed),
        progress: sizeText(s.sizeBytes),
        achievement: null, friend: null, bg: '#1F1F23', art: '',
        img: '/api/art/' + s.appid + '/portrait',
        controller: s.controller || null, deck: typeof s.deck === 'number' ? s.deck : null
      };
    });
    D.games = real.concat(base.soon);
    var keep = base.home.filter(function (k) {
      return k === 'library' || k.indexOf('app:') === 0 || base.soon.some(function (g) { return g.id === k; });
    });
    D.home = real.slice(0, HOME_RECENT).map(function (g) { return g.id; }).concat(keep);
    D.gamesNote = 'Steam\'deki yüklü oyunların: ' + real.length;
    live.games = true;
    live.sig = lib.games.map(function (g) { return g.appid + ':' + g.lastPlayed + ':' + g.updating; }).join(',');
  }

  function loadLibrary(done) {
    if (location.protocol !== 'http:') { done(); return; }
    api('/api/ping', { timeout: 2000 }).then(function (p) {
      if (!p || p.app !== 'kos-home') { throw new Error('not kos-home'); }
      live.on = true;
      live.platform = p.platform;
      setInterval(function () { api('/api/ping').catch(function () { /* helper gone */ }); }, 30000);
      return api('/api/library');
    }).then(function (lib) {
      if (lib && lib.games && lib.games.length) { applyLibrary(lib); }
      else if (lib) {
        D.gamesNote = lib.steamFound ? 'Steam\'de yüklü oyun yok. Örnek oyunlar gösteriliyor.' : 'Steam bulunamadı. Örnek oyunlar gösteriliyor.';
      }
      done();
    }).catch(function () { done(); });
  }

  /* After a game closes or Steam installs something, show the new order. */
  var refreshing = false;
  function refreshLibrary() {
    if (!live.games || refreshing) { return; }
    refreshing = true;
    api('/api/library').then(function (lib) {
      refreshing = false;
      if (!lib || !lib.games || !lib.games.length) { return; }
      var sig = lib.games.map(function (g) { return g.appid + ':' + g.lastPlayed + ':' + g.updating; }).join(',');
      if (sig === live.sig || state.overlay) { return; }
      var wasHome = state.screen === 'home';
      applyLibrary(lib);
      renderHome();
      renderGames();
      if (wasHome) { setFocus($('#homeRow .tile')); }
    }).catch(function () { refreshing = false; });
  }

  /* A picture that fails to load falls back to the K.OS tile design. */
  document.addEventListener('error', function (e) {
    var img = e.target;
    if (img && img.classList && img.classList.contains('tile-img')) {
      var tile = img.closest('.tile');
      if (tile) { tile.classList.remove('has-image'); }
      img.remove();
    }
  }, true);

  /* ---------- Game picture behind the Home screen (PS5 style) ---------- */

  var STEAM_CDN = 'https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/';
  var heroBg = { index: 0, src: null, timer: null };

  function heroArtFor(key) {
    if (!prefs.gameArt || !key || key === 'library' || key.indexOf('app:') === 0) { return null; }
    var g = game(key);
    if (!g || !g.steamAppId) { return null; }
    if (demoArt[g.id + '-hero']) { return demoArt[g.id + '-hero']; }
    if (g.live) { return '/api/art/' + g.steamAppId + '/hero'; }
    return state.online ? STEAM_CDN + g.steamAppId + '/library_hero.jpg' : null;
  }

  function updateHeroBg(key) {
    clearTimeout(heroBg.timer);
    heroBg.timer = setTimeout(function () { showHeroBg(heroArtFor(key)); }, 140);
  }

  function showHeroBg(src) {
    var imgs = $$('.hero-bg .hb');
    if (imgs.length < 2 || src === heroBg.src) { return; }
    heroBg.src = src;
    if (!src) { imgs.forEach(function (i) { i.classList.remove('show'); }); return; }
    var pic = new Image();
    pic.onload = function () {
      if (heroBg.src !== src) { return; }
      var next = imgs[heroBg.index ^ 1];
      var cur = imgs[heroBg.index];
      next.src = src;
      next.classList.remove('show');
      void next.offsetWidth;
      next.classList.add('show');
      cur.classList.remove('show');
      heroBg.index ^= 1;
    };
    pic.onerror = function () {
      if (heroBg.src === src) { imgs.forEach(function (i) { i.classList.remove('show'); }); }
    };
    pic.src = src;
  }

  /* ---------- Lookups ---------- */

  function game(id) { return D.games.filter(function (g) { return g.id === id; })[0]; }
  function app(id) { return D.apps.filter(function (a) { return a.id === id; })[0]; }

  /* ---------- Tile markup ---------- */

  function imgTag(id) {
    return demoArt[id] ? '<img class="tile-img" alt="" src="' + esc(demoArt[id]) + '">' : '';
  }

  function gameTile(g, extra) {
    var src = demoArt[g.id] || g.img || '';
    return '<button type="button" class="tile f has-dot' + (src ? ' has-image' : '') + '" ' + extra +
      ' data-action="launch:' + g.id + '" aria-label="' + esc(g.name) + '">' +
      '<span class="tile-face" style="background:' + g.bg + '">' + g.art +
      '<span class="tile-label">' + g.short + '</span>' +
      (src ? '<img class="tile-img" alt="" decoding="async" src="' + esc(src) + '">' : '') + '</span>' +
      (g.soon ? '<span class="soon-badge">Yakında</span>' : '') + '</button>';
  }

  function appTile(a, extra, withDesc) {
    return '<button type="button" class="tile f has-dot' + (a.net ? ' needs-net' : '') + (demoArt[a.id] ? ' has-image' : '') + '" ' + extra +
      ' data-action="app:' + a.id + '" aria-label="' + esc(a.name) + '">' +
      '<span class="tile-face app-face" style="background:' + a.color + '">' + ICON[a.icon] +
      '<span><span class="tile-name">' + esc(a.name) + '</span>' +
      (withDesc ? '<span class="tile-desc" style="display:block">' + esc(a.desc) + '</span>' : '') + '</span>' +
      imgTag(a.id) + '</span><span class="net-badge">Çevrimdışı</span></button>';
  }

  /* ---------- Home ---------- */

  function renderHome() {
    var html = D.home.map(function (key, i) {
      var extra = 'data-group="home-row" data-home="' + i + '"';
      if (key === 'library') {
        return '<button type="button" class="tile f has-dot" ' + extra + ' data-action="tab:games" aria-label="Kütüphane">' +
          '<span class="tile-face library-face">' + ICON.grid + '<span>Kütüphane</span></span></button>';
      }
      if (key.indexOf('app:') === 0) { return appTile(app(key.slice(4)), extra, false); }
      return gameTile(game(key), extra);
    }).join('');
    $('#homeRow').innerHTML = html;
    renderHero(0);
  }

  function renderHero(index) {
    var key = D.home[index];
    state.heroKey = key;
    updateHeroBg(key);
    var hero = $('#hero');
    var side = $('#sideCards');
    var html = '';
    var sideHtml = '';
    var heroBtn = 'data-group="hero"';

    if (key === 'library') {
      html = '<div class="hero-kicker">KÜTÜPHANE</div><h1 class="hero-title">Tüm oyunların</h1>' +
        '<div class="hero-meta"><span>' + D.games.length + ' oyun</span><span class="sep">/</span><span>Steam, Epic ve GOG tek yerde</span></div>' +
        '<div class="hero-actions"><button type="button" class="btn primary f" ' + heroBtn + ' data-action="tab:games"><span class="dot"></span>Kütüphaneyi aç</button></div>';
    } else if (key.indexOf('app:') === 0) {
      var a = app(key.slice(4));
      html = '<div class="hero-kicker">UYGULAMA</div><h1 class="hero-title' + (a.name.length > 15 ? ' long' : '') + '">' + esc(a.name) + '</h1>' +
        '<div class="hero-meta"><span>' + esc(a.desc) + '</span></div>' +
        '<div class="hero-actions"><button type="button" class="btn primary f" ' + heroBtn + ' data-action="app:' + a.id + '"><span class="dot"></span>Aç</button></div>';
    } else if (game(key).soon) {
      var sg = game(key);
      html = '<div class="hero-kicker">YAKINDA</div><h1 class="hero-title' + (sg.name.length > 15 ? ' long' : '') + '">' + esc(sg.name) + '</h1>' +
        '<div class="hero-meta">' + sg.soon.map(function (t, i) { return (i ? '<span class="sep">/</span>' : '') + '<span>' + esc(t) + '</span>'; }).join('') + '</div>' +
        '<div class="hero-actions"><button type="button" class="btn primary f" ' + heroBtn + ' data-action="demo:' + esc(sg.name) + ' PC\'ye gelince haber vereceğiz (demo).">' +
        '<span class="dot"></span>Çıkınca haber ver</button></div>';
    } else {
      var g = game(key);
      html = '<div class="hero-kicker">' + (index === 0 ? 'SON OYNANAN' : 'OYUN') + '</div><h1 class="hero-title' + (g.name.length > 15 ? ' long' : '') + '">' + esc(g.name) + '</h1>' +
        '<div class="hero-meta">' + [g.played, g.save, g.progress].filter(Boolean).map(function (t, i) {
          return (i ? '<span class="sep">/</span>' : '') + '<span>' + esc(t) + '</span>';
        }).join('') + '</div>' +
        badgesHtml(g) +
        '<div class="hero-actions">' +
        (state.running && state.running.appid === g.steamAppId ?
          '<button type="button" class="btn primary f" ' + heroBtn + ' data-action="game:resume"><span class="dot"></span>Oyuna dön</button>' :
          '<button type="button" class="btn primary f" ' + heroBtn + ' data-action="launch:' + g.id + '"><span class="dot"></span>Oyna</button>') +
        '<button type="button" class="btn f" ' + heroBtn + ' data-action="demo:Oyun sayfası bir sonraki adımda gelecek.">Oyun Sayfası</button>' +
        '<button type="button" class="btn round f" ' + heroBtn + ' data-action="demo:Diğer seçenekler bir sonraki adımda gelecek." aria-label="Diğer seçenekler">' + ICON.more + '</button>' +
        '</div>';
      var pct = g.achievement ? Math.round(g.achievement.done / g.achievement.total * 100) : 0;
      sideHtml = !g.achievement ? '' : '<div class="card" style="display:flex;flex-direction:column;gap:14px">' +
        '<div class="card-kicker">BAŞARIM</div><div style="font-size:22px;font-weight:600">' + esc(g.achievement.name) + '</div>' +
        '<div class="progress"><div style="width:' + pct + '%"></div></div>' +
        '<div class="muted" style="font-size:17px">' + g.achievement.done + ' / ' + g.achievement.total + ' başarım</div></div>';
      if (g.friend) {
        sideHtml += '<div class="card" style="display:flex;align-items:center;gap:18px">' +
          '<div aria-hidden="true" style="width:48px;height:48px;border-radius:50%;background:#3F3F46"></div>' +
          '<div style="display:flex;flex-direction:column;gap:4px"><span style="font-size:20px;font-weight:600">' + esc(g.friend) + '</span>' +
          '<span class="muted" style="font-size:17px">' + esc(g.name) + '</span></div></div>';
      }
    }
    hero.innerHTML = html;
    side.innerHTML = sideHtml;
  }

  /* ---------- Games and Apps ---------- */

  function renderGames() {
    $('#gamesNote').textContent = D.gamesNote || '';
    $('#gamesGrid').innerHTML = D.games.map(function (g) { return gameTile(g, 'data-group="games"'); }).join('');
  }

  function renderApps() {
    $('#appsGrid').innerHTML = D.apps.map(function (a) { return appTile(a, 'data-group="apps"', true); }).join('');
  }

  /* ---------- Store ---------- */

  function storeState(a) {
    if (state.installed[a.id] || a.installed) { return 'done'; }
    if (state.installing[a.id] !== undefined) { return 'busy'; }
    if (a.downloading && !state.installed[a.id]) { return 'busy'; }
    return 'install';
  }

  function storeButton(a) {
    var s = storeState(a);
    if (s === 'done') { return '<span class="app-state done">' + ICON.check + 'Yüklü</span>'; }
    if (s === 'busy') {
      var p = state.installing[a.id] !== undefined ? state.installing[a.id] : a.downloading;
      return '<span class="app-state busy">İndiriliyor %' + p + '</span>';
    }
    return '<span class="app-state install">Yükle</span>';
  }

  function renderStore() {
    var feat = D.storeApps.filter(function (a) { return a.featured; })[0];
    $('#storeFeature').outerHTML =
      '<button type="button" class="store-feature f has-dot" id="storeFeature" data-group="store-top" data-action="install:' + feat.id + '">' +
      '<span class="feat-text">' +
      '<span class="kicker">BU HAFTA ÖNE ÇIKAN</span><h2>' + esc(feat.name) + '</h2>' +
      '<p>Epic, GOG ve Amazon oyunlarını tek yerden yükle ve oyna. K.OS ile tam uyumlu.</p>' +
      '<span id="featState" class="feat-state">' + featLabel(feat) + '</span></span>' +
      '<span class="feature-icon" aria-hidden="true">' + feat.letter + '</span></button>';
    renderDownloads();
    $('#storeChips').innerHTML = D.storeCategories.map(function (c) {
      return '<button type="button" role="tab" class="chip f' + (c.id === state.storeFilter ? ' selected' : '') +
        '" aria-selected="' + (c.id === state.storeFilter) + '" data-group="chips" data-action="filter:' + c.id + '">' + esc(c.name) + '</button>';
    }).join('');
    renderStoreGrid();
  }

  function featLabel(a) {
    var s = storeState(a);
    if (s === 'done') { return 'Yüklü'; }
    if (s === 'busy') { return 'İndiriliyor %' + state.installing[a.id]; }
    return 'A ile yükle';
  }

  function renderDownloads() {
    var active = D.storeApps.filter(function (a) { return state.installing[a.id] !== undefined; })[0];
    var first = active || D.storeApps.filter(function (a) { return a.downloading && !state.installed[a.id]; })[0];
    var box = $('#storeDownloads');
    if (!first) {
      box.innerHTML = '<span class="card-kicker">İNDİRİLENLER</span><span style="font-size:24px;font-weight:600">Her şey güncel</span><span class="muted" style="font-size:18px">Sırada uygulama yok</span>';
      return;
    }
    var p = state.installing[first.id] !== undefined ? state.installing[first.id] : first.downloading;
    box.innerHTML = '<span class="card-kicker">İNDİRİLENLER</span>' +
      '<div style="display:flex;flex-direction:column;gap:12px"><span style="font-size:24px;font-weight:600">' + esc(first.name) + '</span>' +
      '<div class="bar"><div style="width:' + p + '%"></div></div>' +
      '<span class="muted" style="font-size:18px">%' + p + '</span></div>' +
      '<span class="muted" style="font-size:18px">Uygulamalar Flathub üzerinden yüklenir</span>';
  }

  function renderStoreGrid() {
    var list = D.storeApps.filter(function (a) { return !a.featured && (state.storeFilter === 'hepsi' || a.cat === state.storeFilter); });
    $('#storeGrid').innerHTML = list.map(function (a) {
      return '<button type="button" class="app-card f has-dot" data-group="store-grid" data-app="' + a.id + '" data-action="install:' + a.id + '">' +
        '<span class="app-card-head"><span class="app-icon" style="background:' + a.color + '" aria-hidden="true">' + a.letter + '</span>' +
        '<span><b>' + esc(a.name) + '</b><small>' + esc(a.sub) + '</small></span></span>' + storeButton(a) + '</button>';
    }).join('');
  }

  function startInstall(id) {
    var a = D.storeApps.filter(function (x) { return x.id === id; })[0];
    if (!a) { return; }
    var s = storeState(a);
    if (s === 'done') { toast(a.name + ' zaten yüklü.'); return; }
    if (state.installing[id] !== undefined) { toast(a.name + ' indiriliyor.'); return; }
    if (!state.online) { toast('İnternet bağlantısı yok. Yüklemek için internete bağlanın.'); return; }
    state.installing[id] = a.downloading || 0;
    toast(a.name + ' yükleniyor (demo).');
    var timer = setInterval(function () {
      state.installing[id] = Math.min(100, state.installing[id] + 7);
      if (state.installing[id] >= 100) {
        clearInterval(timer);
        delete state.installing[id];
        state.installed[id] = true;
        saved.set('installed', state.installed);
        toast(a.name + ' yüklendi.');
      }
      refreshStoreInPlace();
    }, 280);
    refreshStoreInPlace();
  }

  function refreshStoreInPlace() {
    $$('#storeGrid .app-card').forEach(function (card) {
      var a = D.storeApps.filter(function (x) { return x.id === card.dataset.app; })[0];
      var old = card.querySelector('.app-state');
      var tmp = document.createElement('span');
      tmp.innerHTML = storeButton(a);
      card.replaceChild(tmp.firstChild, old);
    });
    var feat = D.storeApps.filter(function (a) { return a.featured; })[0];
    var fs = $('#featState');
    if (fs) { fs.textContent = featLabel(feat); }
    renderDownloads();
  }

  /* ---------- Settings ---------- */

  function renderSettingsNav() {
    $('#settingsNav').innerHTML = D.settingsCategories.map(function (c) {
      return '<button type="button" class="set-cat f' + (c.id === state.settingsCat ? ' current' : '') + '" data-group="set-nav" data-cat="' + c.id + '"' +
        (c.id === state.settingsCat ? ' aria-current="page"' : '') + '>' + esc(c.name) +
        (c.badge ? '<span class="badge">' + c.badge + '</span>' : '') + '</button>';
    }).join('');
  }

  function switchRow(key, title, text) {
    return '<div class="panel row"><div class="row-text"><b>' + title + '</b><span>' + text + '</span></div>' +
      '<button type="button" role="switch" class="switch f" data-group="set-pane" data-action="toggle:' + key + '" aria-checked="' + (prefs[key] ? 'true' : 'false') + '" aria-label="' + title + '"><span></span></button></div>';
  }

  function renderSettingsPane() {
    var cat = D.settingsCategories.filter(function (c) { return c.id === state.settingsCat; })[0];
    var pane = $('#settingsPane');
    if (cat.id === 'kumanda') { renderControllerPane(pane); return; }
    if (cat.id === 'ekran') {
      var sizes = [['normal', 'Normal'], ['buyuk', 'Büyük'], ['cokbuyuk', 'Çok büyük']];
      pane.innerHTML = '<h1>Ekran</h1>' +
        '<div class="panel row"><div class="row-text"><b>Tema rengi</b><span>Hareketli arka plan ve vurgular bu rengi kullanır</span></div>' +
        '<div class="swatches" role="radiogroup" aria-label="Tema rengi">' +
        D.themes.map(function (t) {
          return '<button type="button" role="radio" class="swatch f" data-group="set-pane" data-hex="' + t.hex + '" data-action="theme:' + t.hex + '" aria-label="' + t.name + '" ' +
            'aria-checked="' + (t.hex.toUpperCase() === prefs.accent.toUpperCase()) + '" style="background:' + t.hex + '"></button>';
        }).join('') + '</div></div>' +
        switchRow('motion', 'Hareketli arka plan', 'Kapatırsan arka plan durur, renkler kalır') +
        switchRow('gameArt', 'Oyun görselleri', 'Seçili oyunun resmi ana ekranın arka planında görünür') +
        switchRow('autoBest', 'En iyi görüntüyü otomatik seç', 'Ekranının desteklediği en yüksek çözünürlüğü ve hızı kullanır') +
        switchRow('hdr', 'HDR', 'Destekleyen oyun ve videolarda daha parlak, canlı renkler') +
        '<div class="panel row"><div class="row-text"><b>Yazı boyutu</b><span>Uzaktan daha kolay okumak için büyüt</span></div><div class="seg" role="group" aria-label="Yazı boyutu">' +
        sizes.map(function (s) {
          return '<button type="button" class="f" data-group="set-pane" data-action="size:' + s[0] + '" aria-pressed="' + (prefs.textSize === s[0]) + '">' + s[1] + '</button>';
        }).join('') + '</div></div>' +
        '<div class="info-grid"><div class="panel"><span>Çözünürlük</span><b>' + screen.width * (window.devicePixelRatio || 1) + ' x ' + screen.height * (window.devicePixelRatio || 1) + '</b></div>' +
        '<div class="panel"><span>Ekran</span><b>Bu ekran</b></div></div>';
      return;
    }
    if (cat.id === 'ses') {
      var levels = [['dusuk', 'Düşük'], ['orta', 'Orta'], ['yuksek', 'Yüksek']];
      pane.innerHTML = '<h1>Ses</h1>' +
        switchRow('music', 'Arka plan müziği', 'Ana ekranda sakin bir müzik çalar. Oyun veya uygulama açılınca susar') +
        '<div class="panel row"><div class="row-text"><b>Müzik seviyesi</b><span>Arka plan müziğinin ses düzeyi</span></div><div class="seg" role="group" aria-label="Müzik seviyesi">' +
        levels.map(function (l) {
          return '<button type="button" class="f" data-group="set-pane" data-action="level:' + l[0] + '" aria-pressed="' + (prefs.musicLevel === l[0]) + '">' + l[1] + '</button>';
        }).join('') + '</div></div>' +
        switchRow('uiSounds', 'Arayüz sesleri', 'Menülerde gezinirken yumuşak sesler') +
        '<div class="panel plan"><span class="plan-kicker">4. AŞAMADA EKLENECEK</span><ul><li>Genel ses düzeyi</li><li>Çıkış seçimi: TV, kulaklık, hoparlör</li><li>Mikrofon</li></ul></div>';
      return;
    }
    var items = D.settingsPlans[cat.id] || [];
    var extra = '';
    if (cat.id === 'guc') {
      extra = '<button type="button" class="btn primary f" style="align-self:flex-start" data-group="set-pane" data-action="power:windows"><span class="dot"></span>Windows\'a Geç</button>';
    }
    if (cat.id === 'sistem' && live.platform === 'linux') {
      extra = '<div class="panel row"><div class="row-text"><b>Masaüstü modu (geliştirici)</b><span>K.OS Home kapanır, normal masaüstü ve tüm ekranlar açılır. Geri dönmek için menüden K.OS Home\'u açın.</span></div>' +
        '<button type="button" class="btn f" data-group="set-pane" data-action="desktop:">Masaüstüne geç</button></div>';
    }
    pane.innerHTML = '<h1>' + esc(cat.name) + '</h1>' +
      '<div class="panel plan"><span class="plan-kicker">BU SAYFADA OLACAKLAR</span><ul>' +
      items.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>' +
      '<p>Bu sayfa 4. aşamada sistem ayarlarına bağlanacak.</p></div>' + extra;
  }


  /* ---------- Controller friendly badges (from Steam's own game info) ---------- */

  function deckBadge(g) {
    if (g.deck === 3) { return '<span class="chip-badge good">Steam Deck Doğrulandı</span>'; }
    if (g.deck === 2) { return '<span class="chip-badge ok">Steam Deck: Oynanabilir</span>'; }
    if (g.deck === 1) { return '<span class="chip-badge bad">Steam Deck: Desteklenmiyor</span>'; }
    return '';
  }

  function ctlBadge(g) {
    if (g.controller === 'full') { return '<span class="chip-badge good">Kumandayla tam uyumlu</span>'; }
    if (g.controller === 'partial') { return '<span class="chip-badge ok">Kısmi kumanda desteği</span>'; }
    if (g.controller === 'none') { return '<span class="chip-badge bad">Klavye ve fare oyunu</span>'; }
    return '';
  }

  function badgesHtml(g) {
    var html = deckBadge(g) + ctlBadge(g);
    return html ? '<div class="hero-badges">' + html + '</div>' : '';
  }

  function launchInfo(g) {
    var lines = [];
    if (g.deck === 3) { lines.push('Steam Deck Doğrulandı: K.OS\'ta sorunsuz çalışması beklenir.'); }
    if (g.deck === 1) { lines.push('Steam Deck\'te desteklenmiyor: K.OS\'ta sorun çıkarabilir. Sorun olursa Windows\'ta oynayın.'); }
    if (g.controller === 'full') { lines.push('Kumandayla tam uyumlu.'); }
    if (g.controller === 'partial') { lines.push('Kısmi kumanda desteği: bazı menüler klavye isteyebilir. Xbox tuşu + View = Esc.'); }
    if (g.controller === 'none') { lines.push('Klavye ve fare için yapılmış bir oyun. K.OS, kumandayı klavye gibi kullanır (Ayarlar > Kumandalar).'); }
    return lines.map(function (t) { return '<span>' + esc(t) + '</span>'; }).join('');
  }

  /* ---------- Running game: Xbox button brings K.OS Home over it (PS5 style) ---------- */

  function checkRunning(showMenu) {
    if (!live.on || live.platform !== 'linux') { return; }
    api('/api/running', { timeout: 3000 }).then(function (r) {
      var before = state.running ? state.running.appid : null;
      // alive=false: the game's process is gone (a failed start); no "Oyuna dön" then
      state.running = r && r.appid && r.alive !== false ? { appid: r.appid, name: r.name || 'Oyun' } : null;
      var now = state.running ? state.running.appid : null;
      if (before !== now && state.screen === 'home' && !state.overlay) { renderHero(D.home.indexOf(state.heroKey) < 0 ? 0 : D.home.indexOf(state.heroKey)); }
      if (showMenu && state.running && (!state.overlay || state.overlay === 'launch')) {
        if (state.overlay === 'launch') { closeOverlay(); }
        openIngame();
      }
      if (!state.running && state.overlay === 'ingame') { closeOverlay(); }
    }).catch(function () { /* helper busy: try again later */ });
  }

  function openIngame(note) {
    if (!state.running) { return; }
    $('#ingameTitle').textContent = state.running.name;
    $('#ingameNote').textContent = note || 'Oyun arka planda açık';
    var close = $('#ingame [data-action="game:close"]');
    delete close.dataset.confirm;
    $('b', close).textContent = 'Oyunu kapat';
    $('small', close).textContent = 'Kaydedilmemiş ilerleme kaybolur';
    openOverlay('ingame');
  }

  function gameAction(kind, el) {
    if (kind === 'resume') {
      closeOverlay();
      api('/api/game/resume', { method: 'POST' }).then(function (r) {
        if (!r.ok) { toast('Oyuna dönülemedi. Alt+Tab ile deneyin.'); }
      }).catch(function () { toast('Oyuna dönülemedi.'); });
    } else if (kind === 'close') {
      if (!el.dataset.confirm) {
        el.dataset.confirm = '1';
        $('b', el).textContent = 'Kapatmak için tekrar bas';
        $('small', el).textContent = 'Önce oyunda kaydettiğinden emin ol';
        return;
      }
      closeOverlay();
      api('/api/game/close', { method: 'POST' }).then(function (r) {
        toast(r.ok ? 'Oyun kapatılıyor...' : 'Oyun kapatılamadı.');
        setTimeout(function () { checkRunning(false); refreshLibrary(); }, 3000);
      }).catch(function () { toast('Oyun kapatılamadı.'); });
    } else {
      closeOverlay();
    }
  }

  /* ---------- Picker (choose one option from a list) ---------- */

  function openPicker(title, note, options, current, done) {
    $('#pickerTitle').textContent = title;
    $('#pickerNote').textContent = note || '';
    $('#pickerList').innerHTML = options.map(function (o, i) {
      if (o.head) { return '<div class="picker-head">' + esc(o.head) + '</div>'; }
      return '<button type="button" class="pick f' + (o.value === current ? ' current' : '') + '" data-group="picker" data-pick="' + i + '">' + esc(o.label) + '</button>';
    }).join('');
    state.picker = { options: options, done: done };
    $('#pickerList').scrollTop = 0;
    openOverlay('picker');
    setFocus($('#pickerList .pick.current') || $('#pickerList .pick'));
  }

  function pick(el) {
    var p = state.picker;
    var o = p && p.options[parseInt(el.dataset.pick, 10)];
    closeOverlay();
    if (o && p.done) { p.done(o.value); }
  }

  /* ---------- Controller buttons (Ayarlar > Kumandalar) ---------- */

  var BTN_LABEL = {
    A: 'A', B: 'B', X: 'X', Y: 'Y', LB: 'LB', RB: 'RB', LT: 'LT', RT: 'RT', VIEW: 'View', MENU: 'Menü',
    LS: 'Sol çubuk basma', RS: 'Sağ çubuk basma', UP: 'Yön tuşu yukarı', DOWN: 'Yön tuşu aşağı', LEFT: 'Yön tuşu sol', RIGHT: 'Yön tuşu sağ'
  };
  var KEY_LABEL = {
    KEY_ESC: 'Esc', KEY_ENTER: 'Enter', KEY_SPACE: 'Boşluk', KEY_TAB: 'Tab', KEY_BACKSPACE: 'Geri silme',
    KEY_LEFTSHIFT: 'Shift', KEY_LEFTCTRL: 'Ctrl', KEY_LEFTALT: 'Alt', KEY_UP: 'Yukarı ok', KEY_DOWN: 'Aşağı ok',
    KEY_LEFT: 'Sol ok', KEY_RIGHT: 'Sağ ok', KEY_PAGEUP: 'Page Up', KEY_PAGEDOWN: 'Page Down'
  };
  var MOUSE_LABEL = { left: 'sol tık', right: 'sağ tık', middle: 'orta tık' };

  function keyLabel(k) { return KEY_LABEL[k] || k.replace('KEY_', ''); }

  function targetLabel(t, name) {
    if (!t) { return name ? 'Kendisi (' + BTN_LABEL[name] + ')' : 'Yok'; }
    if (t === 'none') { return 'Kapalı'; }
    var i = t.indexOf(':');
    var kind = t.slice(0, i);
    var val = t.slice(i + 1);
    if (kind === 'pad') { return 'Kumanda: ' + (BTN_LABEL[val] || val); }
    if (kind === 'key') { return 'Klavye: ' + keyLabel(val); }
    if (kind === 'mouse') { return 'Fare: ' + (MOUSE_LABEL[val] || val); }
    return t;
  }

  function targetOptions(name, forHold) {
    var o = state.ctl.options;
    var list = [];
    if (forHold) { list.push({ value: null, label: 'Yok (basılı tutmak farklı bir şey yapmaz)' }); }
    else { list.push({ value: '', label: 'Kendisi (' + BTN_LABEL[name] + ')' }); }
    list.push({ value: 'none', label: 'Kapalı' });
    list.push({ head: 'Klavye' });
    o.keys.forEach(function (k) { list.push({ value: 'key:' + k, label: keyLabel(k) }); });
    list.push({ head: 'Fare' });
    o.mouse.forEach(function (m) { list.push({ value: 'mouse:' + m, label: 'Fare ' + MOUSE_LABEL[m] }); });
    list.push({ head: 'Kumanda tuşu' });
    o.pad.forEach(function (p) { list.push({ value: 'pad:' + p, label: BTN_LABEL[p] }); });
    return list;
  }

  function loadController(done) {
    if (!live.on) { done(); return; }
    api('/api/controller', { timeout: 4000 }).then(function (r) {
      if (r && r.ok) {
        var edit = state.ctl ? state.ctl.editing : 'standard';
        state.ctl = { config: r.config, status: r.status, options: r.options, presets: r.presets, editing: edit };
      }
      done();
    }).catch(function () { done(); });
  }

  function saveController(change, keepAction) {
    api('/api/controller', { method: 'POST', body: JSON.stringify(change) }).then(function (r) {
      if (!r || !r.ok) { throw new Error('save'); }
      state.ctl.config = r.config;
      redrawControllerPane(keepAction);
    }).catch(function () { toast('Kumanda ayarı kaydedilemedi.'); });
  }

  function editingLayout() {
    var c = state.ctl.config;
    var ed = state.ctl.editing;
    if (ed.indexOf('game:') === 0) {
      var g = c.games[ed.slice(5)];
      if (g && g.layout) { return g.layout; }
      state.ctl.editing = ed = 'standard';
    }
    return c[ed];
  }

  function saveEditing(layout, keepAction) {
    var ed = state.ctl.editing;
    var change = {};
    if (ed.indexOf('game:') === 0) {
      change.games = {};
      change.games[ed.slice(5)] = { mode: 'custom', layout: layout };
    } else {
      change[ed] = layout;
    }
    saveController(change, keepAction);
  }

  function redrawControllerPane(keepAction) {
    if (state.settingsCat !== 'kumanda' || state.screen !== 'settings') { return; }
    var box = $('#settingsPane');
    var top = box.scrollTop;
    renderSettingsPane();
    box.scrollTop = top;
    var el = keepAction ? $$('#settingsPane .f').filter(function (x) { return x.dataset.action === keepAction; })[0] : null;
    if (el) { setFocus(el); } else if (state.focused && !document.body.contains(state.focused)) { setFocus($('#settingsNav .current')); }
  }

  function gameModeLabel(g) {
    var c = state.ctl.config.games[String(g.steamAppId)] || { mode: 'auto' };
    if (c.mode === 'standard') { return 'Standart düzen'; }
    if (c.mode === 'keyboard') { return 'Klavye düzeni'; }
    if (c.mode === 'custom') { return 'Özel düzen'; }
    return 'Otomatik: ' + (g.controller === 'none' ? 'Klavye düzeni' : 'Standart düzen');
  }

  function renderControllerPane(pane) {
    if (!live.on || live.platform !== 'linux') {
      pane.innerHTML = '<h1>Kumandalar</h1><div class="panel plan"><span class="plan-kicker">K.OS\'TA</span><p>Kumanda tuşları K.OS\'ta ayarlanır. Bu bilgisayarda K.OS Home yardımcısı çalışmıyor veya bu Windows.</p></div>';
      if (live.on && !state.ctl) { loadController(function () { if (state.settingsCat === 'kumanda') { renderSettingsPane(); } }); }
      if (!state.ctl) { return; }
    }
    if (!state.ctl) {
      pane.innerHTML = '<h1>Kumandalar</h1><div class="panel plan"><p>Yükleniyor...</p></div>';
      loadController(function () { if (state.settingsCat === 'kumanda' && state.ctl) { renderSettingsPane(); } });
      return;
    }
    var c = state.ctl.config;
    var st = state.ctl.status || {};
    var lay = editingLayout();
    var ed = state.ctl.editing;
    var statusText = !st.fresh ? 'K.OS kumanda katmanı çalışmıyor (kos-input servisi).' :
      (st.pads && st.pads.length ? 'Bağlı: ' + st.pads.map(function (p) { return p.name; }).join(', ') : 'Bağlı kumanda yok.');
    var g = ed.indexOf('game:') === 0 ? game('steam-' + ed.slice(5)) : null;
    var edits = [['standard', 'Standart'], ['keyboard', 'Klavye oyunları']];
    if (ed.indexOf('game:') === 0) { edits.push([ed, g ? g.name : 'Oyun']); }

    var html = '<h1>Kumandalar</h1>' +
      '<div class="panel row"><div class="row-text"><b>K.OS kumanda katmanı</b><span>' + esc(statusText) + '</span></div>' +
      '<button type="button" role="switch" class="switch f" data-group="set-pane" data-action="ctlenable:" aria-checked="' + (c.enabled ? 'true' : 'false') + '" aria-label="K.OS kumanda katmanı"><span></span></button></div>' +
      '<div class="panel plan"><span class="plan-kicker">HER ZAMAN</span><ul>' +
      '<li>Xbox tuşuna bas: Hızlı Menü açılır, oyun arkada devam eder. Tekrar bas: oyuna dönersin.</li>' +
      '<li>Xbox tuşunu basılı tut: K.OS Home.</li>' +
      '<li>Xbox tuşu basılıyken View: Esc (Undertale gibi oyunlardan çıkmak için).</li></ul></div>' +
      '<div class="panel row"><div class="row-text"><b>Düzenlenen düzen</b><span>Standart: kumandalı oyunlar. Klavye oyunları: kumanda desteği olmayan oyunlar.</span></div><div class="seg">' +
      edits.map(function (e) {
        return '<button type="button" class="f" data-group="set-pane" data-action="ctledit:' + e[0] + '" aria-pressed="' + (ed === e[0]) + '">' + esc(e[1]) + '</button>';
      }).join('') + '</div></div>';

    html += '<div class="ctl-grid">' + state.ctl.options.buttons.map(function (n) {
      var b = lay.buttons[n] || { tap: '', hold: null };
      return '<div class="panel ctl-row"><b>' + esc(BTN_LABEL[n]) + '</b>' +
        '<button type="button" class="btn ctl-btn f" data-group="set-pane" data-action="ctltap:' + n + '">' + esc(targetLabel(b.tap, n)) + '</button>' +
        '<button type="button" class="btn ctl-btn hold f" data-group="set-pane" data-action="ctlhold:' + n + '">' +
        (b.hold ? 'Basılı: ' + esc(targetLabel(b.hold).replace(/^(Klavye|Fare|Kumanda): /, '')) : 'Basılı: -') + '</button></div>';
    }).join('') + '</div>';

    var sticks = [['left', 'Sol çubuk', [['pad', 'Kumanda'], ['arrows', 'Ok tuşları'], ['wasd', 'W A S D']], lay.leftStick],
                  ['right', 'Sağ çubuk', [['pad', 'Kumanda'], ['mouse', 'Fare']], lay.rightStick]];
    html += sticks.map(function (s) {
      return '<div class="panel row"><div class="row-text"><b>' + s[1] + '</b></div><div class="seg">' +
        s[2].map(function (o) {
          return '<button type="button" class="f" data-group="set-pane" data-action="ctlstick:' + s[0] + ':' + o[0] + '" aria-pressed="' + (s[3] === o[0]) + '">' + o[1] + '</button>';
        }).join('') + '</div></div>';
    }).join('');
    html += '<div class="panel row"><div class="row-text"><b>Bu düzeni sıfırla</b><span>' +
      (ed.indexOf('game:') === 0 ? 'Bu oyunun özel düzeni silinir, Otomatik\'e döner' : 'K.OS\'un hazır ayarına döner') + '</span></div>' +
      '<button type="button" class="btn f" data-group="set-pane" data-action="ctlreset:">Sıfırla</button></div>';

    var games = D.games.filter(function (x) { return x.live; });
    if (games.length) {
      html += '<h2 class="pane-sub">Oyunlara özel</h2>' + games.map(function (x) {
        return '<div class="panel row ctl-game"><div class="row-text"><b>' + esc(x.name) + '</b><span class="badges">' + deckBadge(x) + ctlBadge(x) + '</span></div>' +
          '<button type="button" class="btn f" data-group="set-pane" data-action="ctlgame:' + x.steamAppId + '">' + esc(gameModeLabel(x)) + '</button></div>';
      }).join('');
    }
    pane.innerHTML = html;
  }

  function controllerAction(kind, arg) {
    if (!state.ctl) { return; }
    var lay = JSON.parse(JSON.stringify(editingLayout()));
    var action = kind + ':' + arg;
    if (kind === 'ctlenable') {
      saveController({ enabled: !state.ctl.config.enabled }, action);
      toast(state.ctl.config.enabled ? 'K.OS kumanda katmanı kapatılıyor...' : 'K.OS kumanda katmanı açılıyor...');
    } else if (kind === 'ctledit') {
      state.ctl.editing = arg;
      redrawControllerPane(action);
    } else if (kind === 'ctltap' || kind === 'ctlhold') {
      var hold = kind === 'ctlhold';
      var cur = lay.buttons[arg] || { tap: '', hold: null };
      openPicker(BTN_LABEL[arg] + (hold ? ': basılı tutunca' : ''), hold ? 'Yarım saniye basılı tutunca ne yapsın?' : 'Bu tuş ne yapsın?',
        targetOptions(arg, hold), hold ? cur.hold : cur.tap, function (value) {
          lay.buttons[arg] = lay.buttons[arg] || { tap: '', hold: null };
          if (hold) { lay.buttons[arg].hold = value; } else { lay.buttons[arg].tap = value; }
          saveEditing(lay, action);
        });
    } else if (kind === 'ctlstick') {
      var parts = arg.split(':');
      lay[parts[0] === 'left' ? 'leftStick' : 'rightStick'] = parts[1];
      saveEditing(lay, action);
    } else if (kind === 'ctlreset') {
      var ed = state.ctl.editing;
      if (ed.indexOf('game:') === 0) {
        var ch = { games: {} };
        ch.games[ed.slice(5)] = null;
        state.ctl.editing = 'standard';
        saveController(ch, null);
      } else {
        saveController({ reset: ed }, action);
      }
      toast('Düzen sıfırlandı.');
    } else if (kind === 'ctlgame') {
      var g = game('steam-' + arg);
      var entry = state.ctl.config.games[arg] || { mode: 'auto' };
      openPicker(g ? g.name : 'Oyun', 'Bu oyunda kumanda nasıl çalışsın?', [
        { value: 'auto', label: 'Otomatik (kumanda desteğine göre)' },
        { value: 'standard', label: 'Standart düzen' },
        { value: 'keyboard', label: 'Klavye düzeni' },
        { value: 'custom', label: 'Özel düzen (bu oyuna özel tuşlar)' }
      ], entry.mode, function (mode) {
        var change = { games: {} };
        if (mode === 'custom') {
          var base = entry.layout || (entry.mode === 'keyboard' || (entry.mode === 'auto' && g && g.controller === 'none') ?
            state.ctl.config.keyboard : state.ctl.config.standard);
          change.games[arg] = { mode: 'custom', layout: base };
          state.ctl.editing = 'game:' + arg;
          saveController(change, 'ctledit:game:' + arg);
          toast('Özel düzen hazır. Yukarıdan tuşları değiştirin.');
        } else {
          change.games[arg] = { mode: mode };
          saveController(change, action);
        }
      });
    }
  }

  /* ---------- Status bar ---------- */

  function updateClock() {
    var d = new Date();
    $('#clock').textContent = ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
  }

  function updateNet() {
    state.online = navigator.onLine;
    var el = $('#netStatus');
    el.innerHTML = state.online ? ICON.wifi : ICON.wifiOff;
    el.classList.toggle('off', !state.online);
    el.setAttribute('aria-label', state.online ? 'İnternet bağlı' : 'İnternet yok');
    stage.classList.toggle('offline', !state.online);
    $('#powerNet').textContent = state.online ? 'Bağlı' : 'Bağlı değil';
  }

  function updatePad(connected) {
    state.padConnected = connected;
    var el = $('#padStatus');
    el.innerHTML = ICON.pad;
    el.classList.toggle('off', !connected);
    el.setAttribute('aria-label', connected ? 'Kumanda bağlı' : 'Kumanda bağlı değil');
    $('#powerPad').textContent = connected ? 'Bağlı' : 'Bağlı değil';
  }

  /* ---------- Screens and tabs ---------- */

  // LB / RB move between these; Ayarlar is under the profile button (top right)
  var TABS = ['home', 'games', 'apps', 'store'];

  function showScreen(name) {
    if (state.screen === name && $('#screen-' + name).classList.contains('active')) { return; }
    state.screen = name;
    stage.dataset.screen = name;
    $$('.screen').forEach(function (s) { s.classList.toggle('active', s.id === 'screen-' + name); });
    $('.avatar').classList.toggle('active', name === 'settings');
    $$('.tab').forEach(function (t) {
      var on = t.dataset.tab === name;
      t.classList.toggle('active', on);
      if (on) { t.setAttribute('aria-current', 'page'); state.memory.tabs = t; } else { t.removeAttribute('aria-current'); }
    });
    if (name === 'store') { renderStore(); }
    if (name === 'settings') { renderSettingsNav(); renderSettingsPane(); }
    updateHints();
  }

  function switchTab(step) {
    var i = TABS.indexOf(state.screen);
    var next = TABS[(i + step + TABS.length) % TABS.length];
    showScreen(next);
    focusFirstIn(next);
    sfx('move');
  }

  function focusFirstIn(name) {
    var first = {
      home: '#homeRow .tile',
      games: '#gamesGrid .tile',
      apps: '#appsGrid .tile',
      store: '#storeFeature',
      settings: '#settingsNav .current'
    }[name];
    var el = $(first);
    if (name === 'home' && state.memory['home-row']) { el = state.memory['home-row']; }
    if (el) { setFocus(el); }
  }

  /* ---------- Focus and movement ---------- */

  function visible(el) {
    if (!el || !document.body.contains(el)) { return false; }
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && el.offsetParent !== null;
  }

  function layer() {
    if (state.overlay === 'power' || state.overlay === 'picker' || state.overlay === 'ingame') { return $$('.f', $('#' + state.overlay)); }
    if (state.overlay) { return []; }
    return $$('.topbar .f').concat($$('.f', $('#screen-' + state.screen)));
  }

  function setFocus(el) {
    if (!el) { return; }
    if (state.focused && state.focused !== el) { state.focused.classList.remove('focused'); }
    state.focused = el;
    el.classList.add('focused');
    try { el.focus({ preventScroll: true }); } catch (e) { el.focus(); }
    if (el.dataset.group) { state.memory[el.dataset.group] = el; }
    keepInView(el);
    onFocusChanged(el);
  }

  function keepInView(el) {
    var box = el.closest('.scroll');
    if (!box) { return; }
    var s = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    var r = el.getBoundingClientRect();
    var b = box.getBoundingClientRect();
    var pad = 24 * s;
    if (r.bottom + pad > b.bottom) { box.scrollTop += (r.bottom + pad - b.bottom) / s; }
    if (r.top - pad < b.top) { box.scrollTop -= (b.top - (r.top - pad)) / s; }
  }

  function onFocusChanged(el) {
    if (el.dataset.tab) { showScreen(el.dataset.tab); }
    if (el.dataset.home !== undefined) { renderHero(parseInt(el.dataset.home, 10)); }
    if (el.dataset.cat && el.dataset.cat !== state.settingsCat) {
      state.settingsCat = el.dataset.cat;
      $$('.set-cat').forEach(function (c) {
        var on = c.dataset.cat === state.settingsCat;
        c.classList.toggle('current', on);
        if (on) { c.setAttribute('aria-current', 'page'); } else { c.removeAttribute('aria-current'); }
      });
      $('#settingsPane').scrollTop = 0;
      if (state.settingsCat === 'kumanda') { state.ctl = null; }
      renderSettingsPane();
    }
    updateHints();
  }

  function overlap(a1, a2, b1, b2) {
    if (a2 < b1) { return b1 - a2; }
    if (b2 < a1) { return a1 - b2; }
    return 0;
  }

  function move(dir) {
    var cur = state.focused;
    var els = layer();
    if (!cur || !visible(cur) || els.indexOf(cur) === -1) {
      if (state.overlay) { if (els[0]) { setFocus(els[0]); } } else { focusFirstIn(state.screen); }
      return;
    }
    var a = cur.getBoundingClientRect();
    var acx = (a.left + a.right) / 2;
    var acy = (a.top + a.bottom) / 2;
    var best = null;
    var bestScore = Infinity;
    var bestInLine = false;
    function inDirection(b) {
      var bcx = (b.left + b.right) / 2;
      var bcy = (b.top + b.bottom) / 2;
      if (dir === 'right') { return bcx > acx + 2 && b.right > a.right; }
      if (dir === 'left') { return bcx < acx - 2 && b.left < a.left; }
      if (dir === 'down') { return bcy > acy + 2 && b.bottom > a.bottom; }
      return bcy < acy - 2 && b.top < a.top;
    }
    els.forEach(function (el) {
      if (el === cur || !visible(el)) { return; }
      var b = el.getBoundingClientRect();
      var bcx = (b.left + b.right) / 2;
      var bcy = (b.top + b.bottom) / 2;
      var primary, secondary;
      if (dir === 'right') {
        if (bcx <= acx + 2 || b.right <= a.right) { return; }
        primary = Math.max(0, b.left - a.right);
        secondary = overlap(a.top, a.bottom, b.top, b.bottom);
      } else if (dir === 'left') {
        if (bcx >= acx - 2 || b.left >= a.left) { return; }
        primary = Math.max(0, a.left - b.right);
        secondary = overlap(a.top, a.bottom, b.top, b.bottom);
      } else if (dir === 'down') {
        if (bcy <= acy + 2 || b.bottom <= a.bottom) { return; }
        primary = Math.max(0, b.top - a.bottom);
        secondary = overlap(a.left, a.right, b.left, b.right);
      } else {
        if (bcy >= acy - 2 || b.top >= a.top) { return; }
        primary = Math.max(0, a.top - b.bottom);
        secondary = overlap(a.left, a.right, b.left, b.right);
      }
      var score = primary + secondary * 4 + Math.abs(dir === 'up' || dir === 'down' ? bcx - acx : bcy - acy) * 0.05;
      // Down means down: something straight below (or above, or beside) always
      // wins over something off to the side, however close that one is
      var inLine = secondary === 0;
      if ((inLine && !bestInLine) || (inLine === bestInLine && score < bestScore)) {
        bestScore = score; best = el; bestInLine = inLine;
      }
    });
    if (!best) { return; }
    var g = best.dataset.group;
    var mem = g ? state.memory[g] : null;
    if (mem && g !== cur.dataset.group && visible(mem) && els.indexOf(mem) !== -1 && inDirection(mem.getBoundingClientRect())) {
      best = mem;
    }
    setFocus(best);
    sfx('move');
  }

  /* ---------- Actions ---------- */

  function activate(el) {
    if (!el) { return; }
    if (el.dataset.pick !== undefined) { sfx('select'); pick(el); return; }
    if (el.dataset.tab) { showScreen(el.dataset.tab); focusFirstIn(el.dataset.tab); return; }
    if (el.dataset.cat) {
      var firstOnPane = $('#settingsPane .f');
      if (firstOnPane) { setFocus(firstOnPane); }
      return;
    }
    var action = el.dataset.action || '';
    var i = action.indexOf(':');
    var kind = i === -1 ? action : action.slice(0, i);
    var arg = i === -1 ? '' : action.slice(i + 1);
    if (kind) { sfx(kind === 'launch' || kind === 'app' ? 'open' : 'select'); }

    if (kind === 'tab') { showScreen(arg); focusFirstIn(arg); }
    else if (kind === 'launch') { launchGame(game(arg)); }
    else if (kind === 'app') { openApp(app(arg)); }
    else if (kind === 'install') { startInstall(arg); }
    else if (kind === 'filter') { setFilter(arg); }
    else if (kind === 'theme') { applyTheme(arg); }
    else if (kind === 'toggle') { toggle(arg, el); }
    else if (kind === 'size') { setSize(arg); }
    else if (kind === 'level') { setLevel(arg); }
    else if (kind === 'power') { powerAction(arg); }
    else if (kind === 'demo') { toast(arg); }
    else if (kind === 'game') { gameAction(arg, el); }
    else if (kind.indexOf('ctl') === 0) { controllerAction(kind, arg); }
    else if (kind === 'desktop') {
      // First press asks (visibly), second press within 4 seconds switches
      if (el.dataset.confirm !== 'desktop') {
        el.dataset.confirm = 'desktop';
        toast('Masaüstüne geçilsin mi? Onaylamak için tekrar basın.');
        setTimeout(function () { delete el.dataset.confirm; }, 4000);
        return;
      }
      delete el.dataset.confirm;
      toast('Masaüstüne geçiliyor...');
      api('/api/desktop', { method: 'POST' }).catch(function () { toast('Masaüstüne geçilemedi.'); });
    }
  }

  function setFilter(id) {
    state.storeFilter = id;
    $$('.chip').forEach(function (c) {
      var on = c.dataset.action === 'filter:' + id;
      c.classList.toggle('selected', on);
      c.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    renderStoreGrid();
  }

  function toggle(key, el) {
    prefs[key] = !prefs[key];
    saved.set(key, prefs[key]);
    el.setAttribute('aria-checked', prefs[key] ? 'true' : 'false');
    if (key === 'motion') { applyMotion(); }
    if (key === 'gameArt') { updateHeroBg(state.heroKey); }
    if (key === 'music' && window.KOSAudio) { KOSAudio.setMusic(prefs.music); }
    if (key === 'uiSounds' && window.KOSAudio) { KOSAudio.setUi(prefs.uiSounds); }
    if (key === 'hdr' && prefs.hdr) { toast('HDR açıldı. Gerçek ekran ayarı 4. aşamada bağlanacak.'); }
  }

  function setLevel(l) {
    prefs.musicLevel = l;
    saved.set('musicLevel', l);
    if (window.KOSAudio) { KOSAudio.setLevel(l); }
    $$('.seg button').forEach(function (b) {
      if (b.dataset.action.indexOf('level:') === 0) { b.setAttribute('aria-pressed', b.dataset.action === 'level:' + l ? 'true' : 'false'); }
    });
  }

  function setSize(size) {
    prefs.textSize = size;
    saved.set('textSize', size);
    $$('.seg button').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.action === 'size:' + size ? 'true' : 'false'); });
  }

  function launchGame(g) {
    if (!g) { return; }
    trace('launch pressed: ' + (g.name || '?') + ' running=' + (state.running ? state.running.appid : '-'));
    if (g.soon) { toast(g.name + ' henüz PC\'de yok. Çıkınca haber vereceğiz (demo).'); return; }
    if (state.running && g.live) {
      if (state.running.appid === g.steamAppId) { gameAction('resume'); return; }
      openIngame('Yeni bir oyun açmadan önce bu oyunu kapatın');
      return;
    }
    if (window.KOSAudio) { KOSAudio.duck(true); }
    openOverlay('launch');
    state.leftForGame = false;
    state.launch = { game: g, at: Date.now(), seen: false, failed: false };
    $('#launch').classList.remove('playing');
    $('#launchTitle').textContent = g.name;
    $('#launchText').textContent = 'Başlatılıyor...';
    $('#launchInfo').innerHTML = g.live ? launchInfo(g) : '';
    if (!g.live) {
      setTimeout(function () {
        if (state.overlay === 'launch') {
          $('#launchText').textContent = 'Bu bir örnek oyun. Gerçek oyunların için K.OS Home yardımcısıyla açın. Geri dönmek için B tuşuna basın.';
        }
      }, 2200);
      return;
    }
    api('/api/launch/' + g.steamAppId, { method: 'POST' }).then(function (r) {
      if (!r.ok) { throw new Error(r.error || 'launch'); }
      watchLaunch();
      setTimeout(function () {
        if (state.overlay === 'launch' && !state.leftForGame) {
          $('#launchText').textContent = 'Oyun açılıyor. Steam ilk açılışta biraz zaman alabilir. Geri dönmek için B tuşuna basın.';
        }
      }, 4000);
    }).catch(function () {
      if (state.overlay === 'launch') {
        $('#launchText').textContent = 'Oyun başlatılamadı. Steam\'in yüklü olduğundan emin olun. Geri dönmek için B tuşuna basın.';
      }
    });
  }

  // While the launch screen is up: notice a game that closes again by itself
  // right after starting (it happens on a first start, while Steam is still
  // signing in), and offer to try again instead of leaving K.OS Home stuck.
  function watchLaunch() {
    var L = state.launch;
    if (!L || state.overlay !== 'launch') { return; }
    api('/api/running', { timeout: 3000 }).then(function (r) {
      if (state.launch !== L || state.overlay !== 'launch') { return; }
      var alive = r && r.alive && r.appid === L.game.steamAppId;
      var now = Date.now();
      if (alive) {
        L.seen = true;
        L.goneAt = 0;
        if (L.failed) {
          // Steam started the game again by itself (it does that on a first
          // start): back to "starting"
          L.failed = false;
          trace('game is running again');
          $('#launchText').textContent = 'Başlatılıyor...';
        }
      } else if (!L.goneAt) {
        L.goneAt = now;
      }
      // Only give up when nothing has run for 30 s (Steam sometimes closes the
      // game right after starting it and starts it again about 20 s later), or
      // when nothing has started at all after 60 s.
      var goneLong = L.seen && L.goneAt && now - L.goneAt > 30000;
      var neverStarted = !L.seen && now - L.at > 60000;
      if (!L.failed && (goneLong || neverStarted)) {
        L.failed = true;
        trace('launch failed: no game process for 30 s');
        $('#launch').classList.remove('playing');
        $('#launchText').textContent = 'Oyun açılamadı. Tekrar denemek için A, geri dönmek için B tuşuna basın.';
      }
      if (now - L.at < 180000) { setTimeout(watchLaunch, 2000); }
    }).catch(function () { setTimeout(watchLaunch, 3000); });
  }

  function openApp(a) {
    if (!a) { return; }
    var viaHelper = live.platform === 'linux';
    if (a.id === 'windows' && !viaHelper) { powerAction('windows'); return; }
    if (a.net && !state.online) { toast('İnternet bağlantısı yok. ' + a.name + ' için internete bağlanın.'); return; }
    if (viaHelper) {
      api('/api/open/' + a.id, { method: 'POST' }).then(function (r) {
        if (r.ok) { toast(a.id === 'windows' ? 'Windows\'a geçiş soruluyor...' : a.name + ' açılıyor...'); }
        else if (r.error === 'missing') { toast(a.name + ' bu bilgisayarda bulunamadı.'); }
        else { toast(a.name + ' açılamadı.'); }
      }).catch(function () { toast(a.name + ' açılamadı. K.OS Home yardımcısı çalışmıyor.'); });
      return;
    }
    var win = window.open(a.url, '_blank');
    if (win) {
      try { win.opener = null; } catch (e) { /* not needed */ }
      toast(a.name + ' açılıyor...');
    } else {
      toast('Tarayıcı yeni pencereyi engelledi. K.OS\'u "K.OS Launcher.cmd" dosyasıyla açın.');
    }
  }

  function powerAction(kind) {
    if (kind === 'windows' && live.platform === 'linux') { openApp(app('windows')); return; }
    if (live.platform === 'linux') {
      var el = state.focused;
      var names = { sleep: 'Uyku moduna geçiliyor...', restart: 'Yeniden başlatılıyor...', off: 'Kapatılıyor...' };
      // Press twice: the first press only asks
      if (!el || el.dataset.confirm !== kind) {
        if (el) { el.dataset.confirm = kind; }
        toast(kind === 'sleep' ? 'Uyku modu için tekrar basın.' : (kind === 'restart' ? 'Yeniden başlatmak için tekrar basın.' : 'Kapatmak için tekrar basın.'));
        setTimeout(function () { if (el) { delete el.dataset.confirm; } }, 4000);
        return;
      }
      delete el.dataset.confirm;
      toast(names[kind] || '');
      api('/api/power/' + kind, { method: 'POST' }).catch(function () { toast('Olmadı. Tekrar deneyin.'); });
      return;
    }
    var msg = {
      sleep: 'Demo: K.OS\'ta bu düğme konsolu uyku moduna alır.',
      restart: 'Demo: K.OS\'ta bu düğme konsolu yeniden başlatır.',
      windows: 'Demo: K.OS\'ta bu düğme bilgisayarı bir kereliğine Windows ile açar.',
      off: 'Demo: K.OS\'ta bu düğme konsolu kapatır.'
    }[kind];
    toast(msg);
  }

  /* ---------- Overlays ---------- */

  function openOverlay(name) {
    if (state.overlay === name) { return; }
    if (!state.overlay) { state.beforeOverlay = state.focused; }
    state.overlay = name;
    $('#' + name).hidden = false;
    if (name === 'power') {
      var g = state.screen === 'home' ? game(D.home[0]) : null;
      if (live.on) { g = state.running; }
      $('#powerNote').textContent = g ? g.name + ' açık. Kapatmadan önce kaydedin.' : 'Ne yapmak istersiniz?';
      setFocus($('#power .power-btn'));
    }
    if (name === 'ingame') { setFocus($('#ingame .power-btn')); }
    updateHints();
  }

  function closeOverlay() {
    if (!state.overlay) { return; }
    if (state.overlay === 'launch' && window.KOSAudio) { KOSAudio.duck(false); }
    $('#launch').classList.remove('playing');
    $('#' + state.overlay).hidden = true;
    state.overlay = null;
    if (state.beforeOverlay && visible(state.beforeOverlay)) { setFocus(state.beforeOverlay); } else { focusFirstIn(state.screen); }
    updateHints();
  }

  function togglePower() {
    if (state.overlay === 'power') { closeOverlay(); } else if (!state.overlay) { openOverlay('power'); }
  }

  function back() {
    sfx('back');
    if (state.overlay) { closeOverlay(); return; }
    var cur = state.focused;
    if (cur && cur.closest('#settingsPane')) {
      setFocus($('#settingsNav .current'));
      return;
    }
    if (cur && !cur.classList.contains('tab')) {
      setFocus(state.memory.tabs || $('.tab.active'));
      return;
    }
    if (state.screen !== 'home') { showScreen('home'); setFocus($('.tab.active')); }
  }

  /* ---------- Hints ---------- */

  function hint(glyph, text) { return '<span class="hint"><span class="glyph">' + glyph + '</span>' + text + '</span>'; }

  function updateHints() {
    var left = [hint('A', 'Seç'), hint('B', 'Geri')];
    var right = 'Menü tuşu: Güç';
    if (state.overlay === 'launch') { left = [hint('B', 'Geri dön')]; right = ''; }
    else if (state.overlay === 'power' || state.overlay === 'picker') { left = [hint('A', 'Seç'), hint('B', 'Kapat')]; right = ''; }
    else if (state.overlay === 'ingame') { left = [hint('A', 'Seç'), hint('B', 'K.OS Home')]; right = 'Xbox tuşu: oyuna dön'; }
    else {
      left.push(hint('LB', 'Önceki'));
      left.push(hint('RB', 'Sonraki'));
      if (state.screen === 'store') { right = 'Uygulamalar Flathub üzerinden güvenle yüklenir'; }
    }
    $('#hints').innerHTML = '<div class="hints-left">' + left.join('') + '</div><span>' + right + '</span>';
  }

  /* ---------- Toast ---------- */

  var toastTimer = null;
  function toast(text) {
    var t = $('#toast');
    t.textContent = text;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove('show'); }, 3200);
  }

  /* ---------- Input: one place for every button ---------- */

  function press(button, from) {
    if (window.KOSAudio) { KOSAudio.wake(); }
    if (button === 'a' || button === 'b') { trace('press ' + button + ' from ' + (from || 'pad')); }
    if (button === 'a') {
      if (state.overlay === 'launch') {
        if (state.launch && state.launch.failed) { var again = state.launch.game; closeOverlay(); launchGame(again); }
        return;
      }
      activate(state.focused);
    }
    else if (button === 'b') { back(); }
    else if (button === 'menu') { togglePower(); }
    else if (button === 'lb') { if (!state.overlay) { switchTab(-1); } }
    else if (button === 'rb') { if (!state.overlay) { switchTab(1); } }
    else if (button === 'y') { if (!state.overlay) { toast('Arama 2. aşamada gelecek.'); } }
    else if (button === 'up' || button === 'down' || button === 'left' || button === 'right') {
      if (state.overlay === 'launch') { return; }
      move(button);
    }
  }

  document.addEventListener('keydown', function (e) {
    var map = {
      ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right',
      Enter: 'a', NumpadEnter: 'a', Space: 'a',
      Escape: 'b', Backspace: 'b',
      KeyQ: 'lb', KeyE: 'rb', KeyP: 'menu', KeyY: 'y'
    };
    var b = map[e.code];
    if (!b) { return; }
    e.preventDefault();
    // Steam turns controller presses into keys too (arrows, Enter, Escape).
    // While the controller is in use, those copies are ignored, otherwise
    // one press moves two steps.
    if (padBusy()) { if (b === 'a') { trace('key Enter ignored (controller in use)'); } return; }
    press(b, 'keyboard');
  });

  /* Mouse support, handy on a PC while building. */
  stage.addEventListener('click', function (e) {
    if (e.target.closest('#padStatus')) { toggleDiag(); return; }
    var el = e.target.closest('.f');
    if (!el || layer().indexOf(el) === -1) { return; }
    setFocus(el);
    trace('mouse click');
    activate(el);
  });

  /* ---------- Controller ----------
     Reads every connected controller each frame and combines them, because some
     PC software (RGB tools, virtual audio, wheel drivers) adds invisible
     "controllers" that can take the first slot. Each controller's resting
     position is remembered, so a device whose axis rests at an edge, or a
     button that is held when the launcher starts, does not cause movement. */

  var KEYS = ['a', 'b', 'y', 'lb', 'rb', 'menu', 'up', 'down', 'left', 'right'];
  var rest = {};
  var prev = {};
  var hold = { dir: null, next: 0 };
  var diag = { on: false, el: null, lastEvent: 'yok', error: '' };

  var lastPadUse = -1e9;
  function padBusy() {
    if (performance.now() - lastPadUse < 400) { return true; }
    var pads = readPads();
    for (var i = 0; i < pads.length; i++) {
      var p = pads[i];
      for (var b = 0; b < p.buttons.length; b++) { if (p.buttons[b] && p.buttons[b].pressed) { return true; } }
      for (var a = 0; a < Math.min(p.axes.length, 2); a++) { if (Math.abs(p.axes[a]) > 0.5) { return true; } }
    }
    return false;
  }

  function readPads() {
    try {
      var list = navigator.getGamepads ? navigator.getGamepads() : [];
      return Array.prototype.filter.call(list, function (p) { return p && p.connected; });
    } catch (e) {
      diag.error = String(e && e.message || e);
      return [];
    }
  }

  /* D-pad reported as one "hat" axis (common on non-Xbox controllers). */
  function hatDirection(p) {
    if (p.mapping === 'standard' || p.axes.length < 10) { return null; }
    var v = p.axes[9];
    if (typeof v !== 'number' || v < -1.05 || v > 1.05) { return null; }
    var i = Math.round((v + 1) / (2 / 7));
    return { up: i === 0 || i === 1 || i === 7, right: i >= 1 && i <= 3, down: i >= 3 && i <= 5, left: i >= 5 && i <= 7 };
  }

  function padState(p) {
    var b = function (n) { return !!(p.buttons[n] && p.buttons[n].pressed); };
    var sony = /054c/i.test(p.id) || /dualsense|dualshock|wireless controller/i.test(p.id);
    var s;
    if (p.mapping === 'standard') {
      s = {
        a: b(0), b: b(1), y: b(3), lb: b(4), rb: b(5), menu: b(9) || b(8) || b(16),
        up: b(12), down: b(13), left: b(14), right: b(15)
      };
    } else if (sony) {
      s = { a: b(1), b: b(2), y: b(3), lb: b(4), rb: b(5), menu: b(9) || b(8) || b(12), up: false, down: false, left: false, right: false };
    } else {
      s = { a: b(0), b: b(1), y: b(3), lb: b(4), rb: b(5), menu: b(9) || b(7), up: false, down: false, left: false, right: false };
    }
    var hat = hatDirection(p);
    if (hat) { s.up = s.up || hat.up; s.down = s.down || hat.down; s.left = s.left || hat.left; s.right = s.right || hat.right; }
    var r = rest[p.index] || (rest[p.index] = { axes: p.axes.slice(0, 2), held: {} });
    var ax = p.axes[0] || 0;
    var ay = p.axes[1] || 0;
    var moved = function (v, base) { return Math.abs(v) > 0.6 && Math.abs(v - (base || 0)) > 0.6; };
    if (moved(ax, r.axes[0])) { if (ax < 0) { s.left = true; } else { s.right = true; } }
    if (moved(ay, r.axes[1])) { if (ay < 0) { s.up = true; } else { s.down = true; } }
    if (!r.init) {
      KEYS.forEach(function (k) { if (s[k]) { r.held[k] = true; } });
      r.init = true;
    }
    KEYS.forEach(function (k) {
      if (r.held[k]) { if (!s[k]) { delete r.held[k]; } s[k] = false; }
    });
    return s;
  }

  function poll(t) {
    try {
      var pads = readPads();
      if ((pads.length > 0) !== state.padConnected) { updatePad(pads.length > 0); }
      var now = {};
      pads.forEach(function (p) {
        var s = padState(p);
        KEYS.forEach(function (k) { now[k] = now[k] || s[k]; });
      });
      if (KEYS.some(function (k) { return now[k]; })) { lastPadUse = performance.now(); }
      // Another window (a game, Netflix) is in front: ignore the controller here,
      // otherwise K.OS Home would move behind it.
      if (!document.hasFocus()) {
        prev = now;
        hold.dir = null;
        if (diag.on) { drawDiag(pads, now); }
        requestAnimationFrame(poll);
        return;
      }
      ['a', 'b', 'y', 'lb', 'rb', 'menu'].forEach(function (k) { if (now[k] && !prev[k]) { press(k); } });
      var dir = now.up ? 'up' : now.down ? 'down' : now.left ? 'left' : now.right ? 'right' : null;
      if (dir) {
        if (dir !== hold.dir) { press(dir); hold.dir = dir; hold.next = t + 380; }
        else if (t >= hold.next) { press(dir); hold.next = t + 110; }
      } else { hold.dir = null; }
      prev = now;
      if (diag.on) { drawDiag(pads, now); }
    } catch (e) {
      diag.error = String(e && e.message || e);
    }
    requestAnimationFrame(poll);
  }

  /* ---------- Diagnostics (F2) ----------
     Shows exactly what Chrome receives from each controller. */

  function drawDiag(pads, now) {
    if (!diag.el) {
      diag.el = document.createElement('pre');
      diag.el.style.cssText = 'position:fixed;left:16px;top:16px;z-index:99;margin:0;max-width:calc(100vw - 32px);padding:16px 20px;' +
        'background:rgba(0,0,0,0.9);color:#F4F4F5;font:15px/1.5 Consolas,monospace;border:1px solid #3F3F46;border-radius:12px;white-space:pre-wrap;';
      document.body.appendChild(diag.el);
    }
    var lines = [];
    lines.push('K.OS KUMANDA TESTI (F2 ile kapat)');
    lines.push('Pencere odakta: ' + (document.hasFocus() ? 'evet' : 'HAYIR, pencereye bir kez tiklayin'));
    lines.push('Guvenli sayfa: ' + (window.isSecureContext ? 'evet' : 'hayir') + '   Gamepad destegi: ' + (navigator.getGamepads ? 'var' : 'YOK'));
    lines.push('Son olay: ' + diag.lastEvent + (diag.error ? '   HATA: ' + diag.error : ''));
    lines.push('Bulunan kumanda: ' + pads.length);
    pads.forEach(function (p) {
      var pressed = [];
      p.buttons.forEach(function (b, i) { if (b.pressed || b.value > 0.5) { pressed.push(i); } });
      lines.push('');
      lines.push('[' + p.index + '] ' + p.id);
      lines.push('    eslesme: ' + (p.mapping || 'standart degil') + '   tus sayisi: ' + p.buttons.length + '   eksen sayisi: ' + p.axes.length);
      lines.push('    basili tuslar: ' + (pressed.length ? pressed.join(', ') : '-'));
      lines.push('    eksenler: ' + p.axes.map(function (a) { return a.toFixed(2); }).join('  '));
    });
    var active = KEYS.filter(function (k) { return now[k]; });
    lines.push('');
    lines.push('Launcher bunu goruyor: ' + (active.length ? active.join(', ') : '-'));
    diag.el.textContent = lines.join('\n');
  }

  function toggleDiag() {
    diag.on = !diag.on;
    if (!diag.on && diag.el) { diag.el.remove(); diag.el = null; }
  }

  document.addEventListener('keydown', function (e) {
    if (e.code === 'F2') { e.preventDefault(); toggleDiag(); }
  });

  // Messages only when the number of controllers goes from none to some or back
  // to none. On K.OS the same controller can show up twice for a moment (the
  // real one and the K.OS copy), and one of the two going away is not news.
  var padToastTimer = null;
  var padShown = null;
  function padToastLater() {
    clearTimeout(padToastTimer);
    padToastTimer = setTimeout(function () {
      var has = readPads().length > 0;
      if (padShown === null) { padShown = has; return; }
      if (has !== padShown) {
        padShown = has;
        toast(has ? 'Kumanda bağlandı.' : 'Kumanda bağlantısı kesildi.');
      }
    }, 1500);
  }
  window.addEventListener('gamepadconnected', function (e) {
    diag.lastEvent = 'bağlandı: ' + (e.gamepad && e.gamepad.id);
    trace('controller connected (' + readPads().length + ' seen)');
    updatePad(true);
    if (padShown === null) { padShown = false; }
    padToastLater();
  });
  window.addEventListener('gamepaddisconnected', function (e) {
    diag.lastEvent = 'ayrıldı: ' + (e.gamepad && e.gamepad.id);
    trace('controller disconnected (' + readPads().length + ' seen)');
    delete rest[e.gamepad && e.gamepad.index];
    updatePad(readPads().length > 0);
    if (padShown === null) { padShown = true; }
    padToastLater();
  });
  window.addEventListener('online', function () { updateNet(); toast('İnternete bağlandı.'); });
  window.addEventListener('offline', function () { updateNet(); toast('İnternet bağlantısı kesildi.'); });

  /* ---------- Start ---------- */

  applyTheme(prefs.accent);
  applyMotion();

  function sfx(kind) { if (window.KOSAudio) { KOSAudio.ui(kind); } }

  /* Music fades out while another window (Netflix, a game) is in front. */
  function syncDuck() {
    if (!window.KOSAudio) { return; }
    KOSAudio.duck(document.hidden || !document.hasFocus() || state.overlay === 'launch');
  }
  window.addEventListener('blur', function () {
    trace('K.OS Home lost focus');
    state.blurAt = Date.now();
    if (state.overlay === 'ingame' || state.overlay === 'picker') { closeOverlay(); }
    if (state.overlay === 'launch') {
      state.leftForGame = true;
      $('#launch').classList.add('playing');
    }
    syncDuck();
  });
  window.addEventListener('focus', function () {
    trace('K.OS Home got focus (leftForGame=' + state.leftForGame + ')');
    if (state.overlay === 'launch' && state.leftForGame) {
      // Away for a long time = the game was played and is over (or the player
      // came back on purpose): normal K.OS Home. Away only briefly = a Steam
      // window or the game's launcher came and went while the game is still
      // starting: keep the launch screen up instead of dropping back to Home.
      var away = Date.now() - (state.blurAt || 0);
      var failed = state.launch && state.launch.failed;
      // Never leave the black "game in front" screen up while K.OS Home is in front
      $('#launch').classList.remove('playing');
      if (away > 8000) {
        closeOverlay();
      } else if (!failed) {
        $('#launchText').textContent = 'Başlatılıyor...';
        trace('still starting: launch screen kept (away ' + away + ' ms)');
      }
    }
    state.leftForGame = false;
    syncDuck();
    refreshLibrary();
    // Back on K.OS Home (Xbox button held): the running game shows "Oyuna dön".
    // The Quick Menu (Xbox button tap) is its own window.
    setTimeout(function () { checkRunning(false); }, 1500);
  });
  document.addEventListener('visibilitychange', syncDuck);

  if (window.KOSAudio) {
    KOSAudio.start({ music: prefs.music, level: prefs.musicLevel, ui: prefs.uiSounds, theme: prefs.accent });
  }
  updateClock();
  setInterval(updateClock, 10000);
  updateNet();
  updatePad(false);
  requestAnimationFrame(poll);

  loadLibrary(function () {
    loadDemoArt(function () {
      renderHome();
      renderGames();
      renderApps();
      showScreen('home');
      setFocus($('#homeRow .tile'));
      checkRunning(false);
      setInterval(function () { checkRunning(false); }, 5000);
    });
  });
})();

/* Mouse pointer: hidden while the controller (or keyboard) is used, back as
   soon as the mouse really moves. Like a console, no arrow floating on screen. */
(function () {
  var hidden = false;
  function setHidden(on) {
    if (on === hidden) { return; }
    hidden = on;
    document.documentElement.classList.toggle('kos-nocursor', on);
  }
  document.addEventListener('keydown', function () { setHidden(true); }, true);
  document.addEventListener('mousemove', function (e) {
    if (Math.abs(e.movementX || 0) + Math.abs(e.movementY || 0) > 2) { setHidden(false); }
  }, true);
  setInterval(function () {
    var list;
    try { list = navigator.getGamepads ? navigator.getGamepads() : []; } catch (err) { return; }
    for (var i = 0; i < list.length; i++) {
      var p = list[i];
      if (!p || !p.connected) { continue; }
      for (var b = 0; b < p.buttons.length; b++) { if (p.buttons[b] && p.buttons[b].pressed) { setHidden(true); return; } }
      for (var a = 0; a < Math.min(p.axes.length, 4); a++) { if (Math.abs(p.axes[a]) > 0.5) { setHidden(true); return; } }
    }
  }, 100);
  setHidden(true);
})();
