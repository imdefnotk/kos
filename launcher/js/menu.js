/*
  K.OS Quick Menu (Xbox button tap, PS5 style).
  A row of cards above a bar of icons. The bar picks what the cards show:
    K.OS Home, the game or app in front, downloads, sound, microphone,
    controller, internet, screenshot, power.
  Controls (the controller layer turns the controller into these keys while the
  menu is open): arrows move, Enter selects, Escape closes, Q / E (LB / RB) jump
  between bar icons. Xbox button: close (tap) or K.OS Home (hold).
  Talks to the K.OS Home helper (/api/quick and friends) and to the K.OS Home
  shell (window.kos.menu) to close itself, go home or press keys in the game.
*/
(function () {
  'use strict';

  var stage = document.getElementById('stage');
  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }
  function esc(s) { return String(s === undefined || s === null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  var shell = window.kos || null;

  var I = {
    home: '<svg viewBox="0 0 24 24"><path d="M4 11l8-7 8 7"></path><path d="M6 10v10h12V10"></path></svg>',
    app: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="3"></rect><path d="M10 9.5v5l4.5-2.5z"></path></svg>',
    down: '<svg viewBox="0 0 24 24"><path d="M12 4v11"></path><path d="M7 10l5 5 5-5"></path><path d="M5 20h14"></path></svg>',
    sound: '<svg viewBox="0 0 24 24"><path d="M4 9h4l5-4v14l-5-4H4z"></path><path d="M16.5 8.5a5 5 0 0 1 0 7"></path><path d="M19 6a8.5 8.5 0 0 1 0 12"></path></svg>',
    mute: '<svg viewBox="0 0 24 24"><path d="M4 9h4l5-4v14l-5-4H4z"></path><path d="M17 9l5 6M22 9l-5 6"></path></svg>',
    mic: '<svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"></rect><path d="M5 11a7 7 0 0 0 14 0"></path><path d="M12 18v3"></path></svg>',
    micOff: '<svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"></rect><path d="M5 11a7 7 0 0 0 14 0"></path><path d="M12 18v3"></path><path d="M3 3l18 18"></path></svg>',
    pad: '<svg viewBox="0 0 24 24"><path d="M6 8h12a4 4 0 0 1 4 4v1a4 4 0 0 1-7 2.6L14 14h-4l-1 1.6A4 4 0 0 1 2 13v-1a4 4 0 0 1 4-4z"></path><path d="M7 11v3M5.5 12.5h3"></path></svg>',
    wifi: '<svg viewBox="0 0 24 24"><path d="M2 9a15 15 0 0 1 20 0"></path><path d="M5.5 12.5a10 10 0 0 1 13 0"></path><path d="M9 16a5 5 0 0 1 6 0"></path><circle cx="12" cy="19.5" r="0.8"></circle></svg>',
    cable: '<svg viewBox="0 0 24 24"><rect x="7" y="3" width="10" height="7" rx="1.5"></rect><path d="M10 10v3h4v-3"></path><path d="M12 13v8"></path></svg>',
    shot: '<svg viewBox="0 0 24 24"><path d="M4 8a2 2 0 0 1 2-2h2l1.5-2h5L16 6h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"></path><circle cx="12" cy="12.5" r="3.5"></circle></svg>',
    power: '<svg viewBox="0 0 24 24"><path d="M12 3v9"></path><path d="M6.3 6.3a8 8 0 1 0 11.4 0"></path></svg>',
    moon: '<svg viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"></path></svg>',
    restart: '<svg viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.3-5.7"></path><path d="M20 4v5h-5"></path></svg>',
    swap: '<svg viewBox="0 0 24 24"><path d="M4 8h14"></path><path d="M15 4l4 4-4 4"></path><path d="M20 16H6"></path><path d="M9 12l-4 4 4 4"></path></svg>',
    play: '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"></path></svg>',
    close: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12"></path><path d="M18 6L6 18"></path></svg>',
    back: '<svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"></path></svg>',
    reload: '<svg viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.3-5.7"></path><path d="M20 4v5h-5"></path></svg>',
    steam: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"></circle><circle cx="15.5" cy="9.5" r="2.5"></circle><path d="M3.5 14l5 2"></path><circle cx="9.5" cy="16.5" r="1.8"></circle></svg>',
    info: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"></circle><path d="M12 11v6"></path><circle cx="12" cy="7.5" r="0.8"></circle></svg>',
    battery: '<svg viewBox="0 0 24 24"><rect x="2" y="7" width="18" height="10" rx="2"></rect><path d="M22 10v4"></path></svg>'
  };

  var BAR = [
    { id: 'home', label: 'K.OS Home', icon: 'home' },
    { id: 'app', label: 'Açık olan', icon: 'app' },
    { id: 'downloads', label: 'İndirmeler', icon: 'down' },
    { id: 'sound', label: 'Ses', icon: 'sound' },
    { id: 'mic', label: 'Mikrofon', icon: 'mic' },
    { id: 'pad', label: 'Kumanda', icon: 'pad' },
    { id: 'net', label: 'İnternet', icon: 'wifi' },
    { id: 'shot', label: 'Ekran görüntüsü', icon: 'shot' },
    { id: 'power', label: 'Güç', icon: 'power' }
  ];
  var MODE_LABEL = { auto: 'Otomatik', standard: 'Standart', keyboard: 'Klavye', custom: 'Özel' };

  var st = {
    q: null,            // last /api/quick answer
    panel: 'app',
    row: 'cards',
    card: 0,
    bar: 1,
    adjusting: false,
    confirm: null,
    open: false,
    timer: null
  };

  /* ---------- Helpers ---------- */

  function fit() {
    var s = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    stage.style.transform = 'translate(' + ((window.innerWidth - 1920 * s) / 2) + 'px,' + ((window.innerHeight - 1080 * s) / 2) + 'px) scale(' + s + ')';
  }

  function applyTheme() {
    try {
      var hex = JSON.parse(localStorage.getItem('kos.accent') || '"#E5322D"');
      var n = parseInt(String(hex).replace('#', ''), 16);
      if (!isNaN(n)) {
        document.documentElement.style.setProperty('--accent', hex);
        document.documentElement.style.setProperty('--accent-rgb', [(n >> 16) & 255, (n >> 8) & 255, n & 255].join(', '));
      }
    } catch (e) { /* default red */ }
  }

  function api(path, body) {
    var opts = { cache: 'no-store', headers: {} };
    if (body !== undefined) {
      opts.method = 'POST';
      opts.headers['X-KOS'] = '1';
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    return fetch(path, opts).then(function (r) { return r.json(); });
  }

  var toastTimer = null;
  function toast(text) {
    var t = $('#toast');
    t.textContent = text;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove('show'); }, 2600);
  }

  function close() { if (shell) { shell.menu('close'); } else { toast('(Hızlı Menü kapanır)'); } }
  function goHome() { if (shell) { shell.menu('home'); } else { toast('(K.OS Home açılır)'); } }
  function keys(combo) { if (shell) { shell.menu('keys', combo); } else { toast('(' + combo + ')'); } }

  function chip(cls, text) { return '<span class="chip ' + cls + '">' + esc(text) + '</span>'; }
  function badges(g) {
    var h = '';
    if (g.deck === 3) { h += chip('good', 'Steam Deck Doğrulandı'); }
    else if (g.deck === 2) { h += chip('ok', 'Steam Deck: Oynanabilir'); }
    else if (g.deck === 1) { h += chip('bad', 'Steam Deck: Desteklenmiyor'); }
    if (g.controller === 'full') { h += chip('good', 'Kumandayla tam uyumlu'); }
    else if (g.controller === 'partial') { h += chip('ok', 'Kısmi kumanda desteği'); }
    else if (g.controller === 'none') { h += chip('bad', 'Klavye ve fare oyunu'); }
    return h ? '<div class="badges">' + h + '</div>' : '';
  }
  function played(min) {
    if (!min) { return 'Hiç oynanmadı'; }
    return min < 60 ? min + ' dakika oynandı' : Math.round(min / 60) + ' saat oynandı';
  }

  /* ---------- Cards per bar icon ---------- */
  // A card: { icon, art, k, t, s, big, line, html, run, slider, cls }

  function cardsFor(panel) {
    var q = st.q || {};
    var g = q.game;
    var list = [];
    if (panel === 'home') {
      list.push({ icon: 'home', k: 'K.OS', t: 'K.OS Home\'a git', s: g ? g.name + ' arkada açık kalır' : 'Ana ekran', run: goHome });
      list.push({ icon: 'info', k: 'İpucu', t: 'Xbox tuşunu basılı tut', s: 'Her yerden doğrudan K.OS Home\'a gider', run: goHome });
    } else if (panel === 'app') {
      if (g) {
        list.push({ art: '/api/art/' + g.appid + '/header', k: 'Oyun', t: g.name, s: 'Oyuna dön', run: close });
        list.push({ icon: 'close', k: 'Oyun', t: 'Oyunu kapat', s: 'Kaydedilmemiş ilerleme kaybolur', confirm: 'close-game',
          run: function () {
            api('/api/game/close', {}).then(function (r) { toast(r.ok ? 'Oyun kapatılıyor...' : 'Oyun kapatılamadı.'); })
              .catch(function () { toast('Oyun kapatılamadı.'); });
            setTimeout(close, 900);
          } });
        list.push({ icon: 'steam', k: 'Steam', t: 'Steam katmanı', s: 'Arkadaşlar, sohbet, başarımlar, rehberler', run: function () { keys('KEY_LEFTSHIFT+KEY_TAB'); } });
        list.push({ icon: 'pad', k: 'Bu oyunda kumanda', t: MODE_LABEL[g.layoutMode] || 'Otomatik', s: 'Değiştirmek için seç', run: function () { cycleMode(g); } });
        list.push({ icon: 'info', k: played(g.playtimeMin), t: 'Oyun bilgisi', html: badges(g) || '<span class="s">Kumanda bilgisi yok</span>', run: null });
      }
      (q.webapps || []).forEach(function (w) {
        list.push({ icon: 'app', k: 'Uygulama', t: w.name, s: 'Uygulamaya dön', run: close });
        list.push({ icon: 'back', k: w.name, t: 'Geri', s: 'Önceki sayfa', run: function () { keys('KEY_LEFTALT+KEY_LEFT'); } });
        list.push({ icon: 'reload', k: w.name, t: 'Yenile', s: 'Sayfayı yeniden yükle', run: function () { keys('KEY_F5'); } });
        list.push({ icon: 'close', k: w.name, t: w.name + ' kapat', s: 'Uygulama kapanır', confirm: 'close-' + w.id,
          run: function () { api('/api/webapp/close', { id: w.id }).then(function (r) { toast(r.ok ? w.name + ' kapatılıyor...' : 'Kapatılamadı.'); }); setTimeout(close, 700); } });
      });
      if (!list.length) {
        list.push({ icon: 'home', k: 'Açık olan', t: 'Açık oyun yok', s: 'K.OS Home\'dan bir oyun veya uygulama aç', run: close });
      }
    } else if (panel === 'downloads') {
      (q.downloads || []).forEach(function (d) {
        list.push({ art: '/api/art/' + d.appid + '/header', k: 'İndiriliyor', t: d.name, line: d.percent, s: '%' + d.percent, run: null });
      });
      var u = q.update;
      if (u && u.ready) {
        list.push({ icon: 'restart', k: 'K.OS güncellemesi', t: 'Güncelleme hazır', s: 'Yeniden başlatınca yüklenir. Şimdi yeniden başlatmak için seç.', confirm: 'update-restart',
          run: function () { api('/api/power/restart', {}); } });
      } else if (u) {
        list.push({ icon: 'info', k: 'K.OS güncellemesi', t: 'K.OS güncel', s: u.version ? 'Sürüm ' + u.version : '', run: null });
      }
      if (!list.length) { list.push({ icon: 'down', k: 'İndirmeler', t: 'İndirme yok', s: 'Steam indirmeleri burada görünür', run: null }); }
    } else if (panel === 'sound') {
      var snd = q.sound;
      if (!snd) {
        list.push({ icon: 'sound', k: 'Ses', t: 'Ses ayarları yok', s: 'Bu bilgisayarda bulunamadı', run: null });
      } else {
        var pct = snd.volume === null || snd.volume === undefined ? 0 : Math.round(snd.volume * 100);
        list.push({ icon: snd.muted ? 'mute' : 'sound', k: 'Ses düzeyi', big: pct + '', line: pct, s: st.adjusting ? 'Sol / sağ: değiştir. Bitince A.' : 'Ayarlamak için seç', slider: 'volume' });
        list.push({ icon: snd.muted ? 'mute' : 'sound', k: 'Ses', t: snd.muted ? 'Ses kapalı' : 'Ses açık', s: snd.muted ? 'Açmak için seç' : 'Kapatmak için seç', cls: snd.muted ? '' : 'on',
          run: function () { api('/api/sound', { mute: 'toggle' }).then(refreshSoon); } });
        (snd.outputs || []).forEach(function (o) {
          list.push({ icon: 'sound', k: o['default'] ? 'Şu an kullanılan' : 'Ses çıkışı', t: o.name, s: o['default'] ? 'Seçili' : 'Buna geçmek için seç', cls: o['default'] ? 'on' : '',
            run: function () { api('/api/sound', { output: o.id }).then(function (r) { toast(r.ok ? 'Ses çıkışı: ' + o.name : 'Değiştirilemedi.'); refreshSoon(); }); } });
        });
      }
    } else if (panel === 'mic') {
      var mic = q.sound && q.sound.mic;
      if (!mic) {
        list.push({ icon: 'micOff', k: 'Mikrofon', t: 'Mikrofon bulunamadı', s: 'Kulaklık veya mikrofon takın', run: null });
      } else {
        list.push({ icon: mic.muted ? 'micOff' : 'mic', k: 'Mikrofon', t: mic.muted ? 'Mikrofon kapalı' : 'Mikrofon açık', s: mic.muted ? 'Açmak için seç' : 'Kapatmak için seç', cls: mic.muted ? '' : 'on',
          run: function () { api('/api/sound', { micMute: 'toggle' }).then(refreshSoon); } });
      }
    } else if (panel === 'pad') {
      var bats = q.batteries || [];
      (q.pads || []).forEach(function (p, i) {
        var b = bats[i];
        var level = b ? (b.percent !== null && b.percent !== undefined ? '%' + b.percent : (b.level || '')) : '';
        list.push({ icon: 'pad', k: 'Kumanda ' + (i + 1), t: p.name, s: level ? 'Pil: ' + level + (b.status === 'Charging' ? ' (şarj oluyor)' : '') : 'Pil bilgisi yok',
          line: b && b.percent !== null && b.percent !== undefined ? b.percent : null, run: null });
      });
      if (!(q.pads || []).length) {
        bats.forEach(function (b) {
          list.push({ icon: 'battery', k: 'Pil', t: b.name, s: b.percent !== null && b.percent !== undefined ? '%' + b.percent : (b.level || ''), line: b.percent, run: null });
        });
      }
      if (q.game) {
        list.push({ icon: 'pad', k: q.game.name + ' için', t: 'Kumanda düzeni: ' + (MODE_LABEL[q.game.layoutMode] || 'Otomatik'), s: 'Değiştirmek için seç', run: function () { cycleMode(q.game); } });
      }
      list.push({ icon: 'info', k: 'Kısayollar', t: 'Xbox + View = Esc', s: 'Xbox tuşu: bu menü. Basılı tut: K.OS Home.', run: null });
      if (q.layer && !q.layer.running) {
        list.push({ icon: 'info', k: 'K.OS kumanda katmanı', t: 'Çalışmıyor', s: 'Ayarlar > Kumandalar', run: null });
      }
    } else if (panel === 'net') {
      var n = q.net;
      if (!n) {
        list.push({ icon: 'wifi', k: 'İnternet', t: 'Bilgi yok', s: '', run: null });
      } else if (!n.type) {
        list.push({ icon: 'wifi', k: 'İnternet', t: 'Bağlı değil', s: 'Ayarlar > İnternet', run: null });
      } else {
        list.push({ icon: n.type === 'ethernet' ? 'cable' : 'wifi', k: n.type === 'ethernet' ? 'Kablolu' : 'Wi-Fi', t: n.name || 'Bağlı',
          s: (n.signal !== null && n.signal !== undefined ? 'Sinyal %' + n.signal + ' / ' : '') + (n.online === 'full' ? 'İnternete bağlı' : (n.online === 'none' ? 'İnternet yok' : 'Sınırlı bağlantı')),
          line: n.signal, cls: n.online === 'full' ? 'on' : '', run: null });
      }
    } else if (panel === 'shot') {
      list.push({ icon: 'shot', k: 'Ekran görüntüsü', t: 'Şimdi çek', s: 'Menü kapanır, ekran Resimler > K.OS klasörüne kaydedilir',
        run: function () { close(); api('/api/screenshot', {}).catch(function () {}); } });
    } else if (panel === 'power') {
      list.push({ icon: 'moon', k: 'Güç', t: 'Uyku Modu', s: 'Kumandayla uyandır', confirm: 'sleep', run: function () { close(); api('/api/power/sleep', {}); } });
      list.push({ icon: 'restart', k: 'Güç', t: 'Yeniden Başlat', s: 'K.OS yeniden açılır', confirm: 'restart', run: function () { api('/api/power/restart', {}); } });
      list.push({ icon: 'swap', k: 'Güç', t: 'Windows\'a Geç', s: 'Valorant, LoL ve daha fazlası', run: function () { close(); api('/api/power/windows', {}); } });
      list.push({ icon: 'power', k: 'Güç', t: 'Kapat', s: 'Konsolu tamamen kapatır', confirm: 'off', run: function () { api('/api/power/off', {}); } });
    }
    return list;
  }

  function cycleMode(g) {
    var order = ['auto', 'standard', 'keyboard'];
    var i = order.indexOf(g.layoutMode);
    var next = order[(i + 1) % order.length];
    var change = { games: {} };
    change.games[g.appid] = { mode: next };
    api('/api/controller', change).then(function (r) {
      if (r && r.ok) { g.layoutMode = next; toast('Kumanda düzeni: ' + MODE_LABEL[next]); render(); }
    }).catch(function () { toast('Değiştirilemedi.'); });
  }

  /* ---------- Drawing ---------- */

  var current = [];

  function render() {
    var panel = BAR[st.bar] ? st.panel : 'app';
    current = cardsFor(panel);
    if (st.card >= current.length) { st.card = current.length - 1; }
    if (st.card < 0) { st.card = 0; }
    var info = BAR.filter(function (b) { return b.id === panel; })[0];
    var q = st.q || {};
    $('#kicker').textContent = panel === 'app' ? 'AÇIK OLAN' : 'HIZLI MENÜ';
    $('#title').textContent = panel === 'app' ? (q.game ? q.game.name : ((q.webapps || [])[0] || {}).name || 'K.OS') : info.label;

    $('#cards').innerHTML = current.map(function (c, i) {
      var cls = 'card' + (c.cls ? ' ' + c.cls : '') + (st.row === 'cards' && st.card === i ? ' focused' : '') +
        (st.adjusting && st.card === i ? ' adjusting' : '') + (st.confirm && st.confirm === c.confirm && st.card === i ? ' confirm' : '');
      var h = '<div class="' + cls + '" data-i="' + i + '">';
      if (c.art) { h += '<div class="art" style="background-image:url(\'' + esc(c.art) + '\')"></div>'; }
      else if (c.icon) { h += '<div class="card-icon">' + I[c.icon] + '</div>'; }
      if (c.k) { h += '<span class="k">' + esc(c.k) + '</span>'; }
      if (c.big) { h += '<span class="big">' + esc(c.big) + '</span>'; }
      if (c.t) { h += '<span class="t">' + esc(st.confirm && st.confirm === c.confirm && st.card === i ? 'Emin misin? Tekrar seç' : c.t) + '</span>'; }
      if (c.html) { h += c.html; }
      if (c.s) { h += '<span class="s">' + esc(c.s) + '</span>'; }
      if (c.line !== undefined && c.line !== null) { h += '<div class="bar-line"><div style="width:' + Math.max(0, Math.min(100, c.line)) + '%"></div></div>'; }
      return h + '</div>';
    }).join('');

    var gameIcon = q.game ? '<img alt="" src="/api/art/' + q.game.appid + '/portrait" onerror="this.outerHTML=\'' + I.app.replace(/"/g, '&quot;') + '\'">' : I.app;
    $('#bar').innerHTML = BAR.map(function (b, i) {
      var icon = b.id === 'app' ? gameIcon : (b.id === 'sound' && q.sound && q.sound.muted ? I.mute :
        (b.id === 'mic' && q.sound && q.sound.mic && q.sound.mic.muted ? I.micOff :
        (b.id === 'net' && q.net && q.net.type === 'ethernet' ? I.cable : I[b.icon])));
      var badge = (b.id === 'downloads' && ((q.downloads || []).length || (q.update && q.update.ready))) ? '<span class="badge"></span>' : '';
      return '<button type="button" class="bar-btn' + (st.row === 'bar' && st.bar === i ? ' focused' : '') +
        (b.id === panel ? ' current' : '') + '" data-b="' + i + '" aria-label="' + esc(b.label) + '">' + icon + badge + '</button>';
    }).join('');

    // Keep the focused card in view
    var cards = $('#cards');
    var shift = 0;
    var focused = $('.card[data-i="' + st.card + '"]', cards);
    if (focused) {
      var left = st.card * (400 + 22);
      shift = Math.max(0, left - 1920 + 192 + 460);
    }
    cards.style.transform = 'translateX(' + (-shift) + 'px)';

    var hints = st.adjusting ? [['◀ ▶', 'Değiştir'], ['A', 'Tamam']] :
      [['A', 'Seç'], ['B', 'Kapat'], ['LB RB', 'Bölüm'], ['Xbox', 'Kapat'], ['Xbox basılı', 'K.OS Home']];
    $('#hints').innerHTML = hints.map(function (h) {
      return '<span class="hint"><span class="glyph">' + esc(h[0]) + '</span>' + esc(h[1]) + '</span>';
    }).join('');
  }

  function updateClock() {
    var d = new Date();
    $('#clock').textContent = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  }

  /* ---------- Data ---------- */

  function refresh() {
    return api('/api/quick').then(function (q) {
      if (q && q.ok) { st.q = q; }
      if (!st.adjusting) { render(); }
    }).catch(function () { render(); });
  }

  var soonTimer = null;
  function refreshSoon() {
    clearTimeout(soonTimer);
    soonTimer = setTimeout(refresh, 250);
  }

  function setVolume(delta) {
    var snd = st.q && st.q.sound;
    if (!snd) { return; }
    var v = Math.max(0, Math.min(1, Math.round(((snd.volume || 0) + delta) * 100) / 100));
    snd.volume = v;
    render();
    api('/api/sound', { volume: v }).catch(function () {});
  }

  /* ---------- Input ---------- */

  function setPanel(i) {
    st.bar = (i + BAR.length) % BAR.length;
    st.panel = BAR[st.bar].id;
    st.card = 0;
    st.confirm = null;
  }

  function activate() {
    if (st.row === 'bar') {
      var id = BAR[st.bar].id;
      if (id === 'home') { goHome(); return; }
      st.row = 'cards';
      st.card = 0;
      render();
      return;
    }
    var c = current[st.card];
    if (!c) { return; }
    if (c.slider) { st.adjusting = !st.adjusting; render(); if (!st.adjusting) { refreshSoon(); } return; }
    if (!c.run) { return; }
    if (c.confirm && st.confirm !== c.confirm) { st.confirm = c.confirm; render(); return; }
    st.confirm = null;
    c.run();
    render();
  }

  function move(dir) {
    if (st.adjusting) {
      if (dir === 'left') { setVolume(-0.05); }
      if (dir === 'right') { setVolume(0.05); }
      return;
    }
    st.confirm = null;
    if (st.row === 'cards') {
      if (dir === 'left' && st.card > 0) { st.card--; }
      else if (dir === 'right' && st.card < current.length - 1) { st.card++; }
      else if (dir === 'down') { st.row = 'bar'; }
    } else {
      if (dir === 'left') { setPanel(st.bar - 1); }
      else if (dir === 'right') { setPanel(st.bar + 1); }
      else if (dir === 'up') { st.row = 'cards'; }
    }
    render();
  }

  document.addEventListener('keydown', function (e) {
    var k = e.key;
    if (k === 'ArrowLeft') { move('left'); }
    else if (k === 'ArrowRight') { move('right'); }
    else if (k === 'ArrowUp') { move('up'); }
    else if (k === 'ArrowDown') { move('down'); }
    else if (k === 'Enter' || k === ' ') { activate(); }
    else if (k === 'Escape' || k === 'Backspace') {
      if (st.adjusting) { st.adjusting = false; render(); refreshSoon(); }
      else if (st.confirm) { st.confirm = null; render(); }
      else { close(); }
    }
    else if (k === 'q' || k === 'Q') { setPanel(st.bar - 1); st.row = 'bar'; render(); }
    else if (k === 'e' || k === 'E') { setPanel(st.bar + 1); st.row = 'bar'; render(); }
    else { return; }
    e.preventDefault();
  });

  // Mouse, handy while building
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.bar-btn');
    var c = e.target.closest('.card');
    if (b) { setPanel(parseInt(b.dataset.b, 10)); st.row = 'bar'; activate(); }
    else if (c) { st.row = 'cards'; st.card = parseInt(c.dataset.i, 10); activate(); }
  });

  /* ---------- Show and hide (from the K.OS Home shell) ---------- */

  function onShow() {
    st.open = true;
    st.panel = 'app';
    st.bar = 1;
    st.row = 'cards';
    st.card = 0;
    st.adjusting = false;
    st.confirm = null;
    applyTheme();
    updateClock();
    render();
    refresh();
    stage.classList.add('shown');
    clearInterval(st.timer);
    st.timer = setInterval(function () { if (st.open) { refresh(); updateClock(); } }, 2000);
  }

  function onHide() {
    st.open = false;
    stage.classList.remove('shown');
    clearInterval(st.timer);
  }

  fit();
  window.addEventListener('resize', fit);
  if (shell && shell.onMenu) {
    shell.onMenu(function (what) { if (what === 'show') { onShow(); } else { onHide(); } });
    refresh();  // have the data ready before the first Xbox press
  } else {
    onShow();   // opened in a normal browser for testing
  }
})();
