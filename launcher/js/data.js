/*
  K.OS launcher sample data.
  Games here are made-up examples so the screens have something to show.
  When the launcher runs through the K.OS Home helper, the real installed
  Steam games replace them (see js/app.js, "Real game library").
*/
window.KOS_DATA = {
  themes: [
    { hex: '#E5322D', name: 'Kırmızı' },
    { hex: '#F97316', name: 'Turuncu' },
    { hex: '#3B82F6', name: 'Mavi' },
    { hex: '#22D3EE', name: 'Turkuaz' },
    { hex: '#8B5CF6', name: 'Mor' },
    { hex: '#22C55E', name: 'Yeşil' }
  ],

  games: [
    {
      id: 'kuzey-isigi', name: 'Kuzey Işığı', short: 'Kuzey<br>Işığı',
      played: '12 saat oynandı', save: 'Bulut kaydı güncel', progress: 'Bölüm 4: Buzul Geçidi',
      achievement: { name: 'Kuzey Feneri', done: 24, total: 35 },
      friend: 'Arda şimdi oynuyor',
      bg: '#12262E',
      art: '<div class="art" style="background:#1C3A44;clip-path:polygon(0 100%,30% 45%,50% 62%,75% 30%,100% 70%,100% 100%)"></div>' +
           '<div class="art" style="inset:auto;right:19%;top:17%;width:15%;height:15%;border-radius:50%;background:#E8D8B0"></div>'
    },
    {
      id: 'demir-hat', name: 'Demir Hat', short: 'Demir<br>Hat',
      played: '31 saat oynandı', save: 'Bulut kaydı güncel', progress: 'Hat 7: Kömür Ocağı',
      achievement: { name: 'Son Sefer', done: 41, total: 50 },
      friend: null,
      bg: '#2A1A12',
      art: '<div class="art" style="top:auto;height:60%;background:#6B2E14;clip-path:polygon(0 40%,100% 0,100% 100%,0 100%)"></div>'
    },
    {
      id: 'gece-surusu', name: 'Gece Sürüşü', short: 'Gece<br>Sürüşü',
      played: '4 saat oynandı', save: 'Bulut kaydı güncel', progress: 'Sezon 1, Yarış 6',
      achievement: { name: 'Boş Yollar', done: 9, total: 40 },
      friend: 'Elif çevrimiçi',
      bg: '#151530',
      art: '<div class="art" style="inset:16% 19% 22% 19%;border-radius:50%;border:clamp(6px,4%,10px) solid #4B4BC8"></div>'
    },
    {
      id: 'tuz-yolu', name: 'Tuz Yolu', short: 'Tuz<br>Yolu',
      played: '2 saat oynandı', save: 'Yerel kayıt', progress: 'Kervan 2',
      achievement: { name: 'İlk Han', done: 3, total: 28 },
      friend: null,
      bg: '#3A2A14',
      art: '<div class="art" style="top:auto;height:55%;background:#C9A25E;clip-path:polygon(0 50%,25% 25%,55% 55%,80% 20%,100% 40%,100% 100%,0 100%)"></div>' +
           '<div class="art" style="top:auto;height:30%;background:#8A6A32;clip-path:polygon(0 40%,40% 0,70% 45%,100% 15%,100% 100%,0 100%)"></div>'
    },
    {
      id: 'kizil-vadi', name: 'Kızıl Vadi', short: 'Kızıl<br>Vadi',
      played: '18 saat oynandı', save: 'Bulut kaydı güncel', progress: 'Perde 3',
      achievement: { name: 'Vadi Bekçisi', done: 30, total: 46 },
      friend: null,
      bg: '#2B0E10',
      art: '<div class="art" style="background:#7A1F1F;clip-path:polygon(0 30%,35% 30%,42% 100%,0 100%)"></div>' +
           '<div class="art" style="background:#5A1616;clip-path:polygon(100% 20%,62% 20%,55% 100%,100% 100%)"></div>'
    },
    {
      id: 'son-liman', name: 'Son Liman', short: 'Son<br>Liman',
      played: '7 saat oynandı', save: 'Bulut kaydı güncel', progress: 'Ada 5',
      achievement: { name: 'Fener Ustası', done: 12, total: 30 },
      friend: null,
      bg: '#0E1E33',
      art: '<div class="art" style="top:auto;height:35%;background:#173A5E"></div>' +
           '<div class="art" style="inset:auto;left:58%;bottom:35%;width:8%;height:38%;background:#E4E4E7"></div>' +
           '<div class="art" style="inset:auto;left:56%;bottom:73%;width:12%;height:6%;background:#E5322D"></div>'
    },
    {
      id: 'yildiz-tozu', name: 'Yıldız Tozu', short: 'Yıldız<br>Tozu',
      played: 'Hiç oynanmadı', save: 'Yeni', progress: 'Başlamaya hazır',
      achievement: { name: 'İlk Işık', done: 0, total: 22 },
      friend: null,
      bg: '#1A1030',
      art: '<div class="art" style="background:radial-gradient(circle at 20% 30%,#C4B5FD 0 2px,transparent 3px),radial-gradient(circle at 70% 20%,#E9D5FF 0 3px,transparent 4px),radial-gradient(circle at 55% 60%,#C4B5FD 0 2px,transparent 3px),radial-gradient(circle at 85% 70%,#DDD6FE 0 2px,transparent 3px),radial-gradient(circle at 35% 75%,#E9D5FF 0 3px,transparent 4px)"></div>'
    },
    {
      id: 'tas-kule', name: 'Taş Kule', short: 'Taş<br>Kule',
      played: '1 saat oynandı', save: 'Yerel kayıt', progress: 'Kat 2',
      achievement: { name: 'Temel', done: 2, total: 33 },
      friend: null,
      bg: '#1C1C20',
      art: '<div class="art" style="inset:auto;left:38%;bottom:0;width:24%;height:70%;background:#52525B"></div>' +
           '<div class="art" style="inset:auto;left:34%;bottom:68%;width:32%;height:8%;background:#71717A"></div>'
    }
  ],

  apps: [
    {
      id: 'netflix', name: 'Netflix', url: 'https://www.netflix.com', net: true,
      color: '#8F1D22', icon: 'play',
      desc: 'Dizi ve filmler. Tam ekran açılır, kumandayla kullanılır.'
    },
    {
      id: 'hbomax', name: 'HBO Max', url: 'https://www.hbomax.com', net: true,
      color: '#4A2A8C', icon: 'play',
      desc: 'Dizi ve filmler. Tam ekran açılır, kumandayla kullanılır.'
    },
    {
      id: 'xcloud', name: 'Xbox Bulut Oyun', url: 'https://www.xbox.com/play', net: true,
      color: '#17663F', icon: 'cloud',
      desc: 'Game Pass oyunlarını indirmeden, buluttan oyna.'
    },
    {
      id: 'browser', name: 'İnternet', url: 'https://www.google.com', net: true,
      color: '#1F3A8A', icon: 'globe',
      desc: 'Tam ekran internet tarayıcısı.'
    },
    {
      id: 'steam', name: 'Steam', url: 'steam://open/games', net: false,
      color: '#1B2838', icon: 'pad',
      desc: 'Steam mağazası ve kütüphanen. Oyunların K.OS kütüphanesinde de görünür.'
    },
    {
      id: 'windows', name: "Windows'a Geç", url: null, net: false,
      color: '#27272A', icon: 'swap',
      desc: 'Valorant, LoL ve Game Pass PC oyunları için Windows ile yeniden başlat.'
    }
  ],

  gamesNote: 'Örnek kütüphane. Gerçek oyunların için K.OS Home\'u yardımcı programla aç.',

  home: ['kuzey-isigi', 'demir-hat', 'gece-surusu', 'app:netflix', 'app:hbomax', 'app:xcloud', 'library'],

  storeCategories: [
    { id: 'hepsi', name: 'Hepsi' },
    { id: 'sohbet', name: 'Sohbet' },
    { id: 'medya', name: 'Müzik ve Video' },
    { id: 'magaza', name: 'Oyun Mağazaları' },
    { id: 'yayin', name: 'Yayın ve Kayıt' },
    { id: 'emu', name: 'Emülatörler' },
    { id: 'arac', name: 'Araçlar' }
  ],

  storeApps: [
    { id: 'discord', name: 'Discord', sub: 'Sohbet', cat: 'sohbet', color: '#3B3F8F', letter: 'D' },
    { id: 'spotify', name: 'Spotify', sub: 'Müzik', cat: 'medya', color: '#155C3A', letter: 'S', downloading: 62 },
    { id: 'obs', name: 'OBS Studio', sub: 'Yayın ve kayıt', cat: 'yayin', color: '#6B2E14', letter: 'O' },
    { id: 'moonlight', name: 'Moonlight', sub: 'Oyun aktarımı', cat: 'yayin', color: '#1C3A44', letter: 'M', installed: true },
    { id: 'prism', name: 'Prism Launcher', sub: 'Minecraft', cat: 'magaza', color: '#4A2A8C', letter: 'P' },
    { id: 'retroarch', name: 'RetroArch', sub: 'Emülatör', cat: 'emu', color: '#8F1D22', letter: 'R' },
    { id: 'vlc', name: 'VLC', sub: 'Video oynatıcı', cat: 'medya', color: '#7A4A10', letter: 'V' },
    { id: 'lutris', name: 'Lutris', sub: 'Oyun mağazaları', cat: 'magaza', color: '#12262E', letter: 'L' },
    { id: 'heroic', name: 'Heroic Games Launcher', sub: 'Epic, GOG, Amazon', cat: 'magaza', color: '#1F1F23', letter: 'H', featured: true },
    { id: 'firefox', name: 'Firefox', sub: 'İnternet tarayıcısı', cat: 'arac', color: '#7C2D12', letter: 'F' },
    { id: 'dolphin', name: 'Dolphin', sub: 'Emülatör', cat: 'emu', color: '#0C4A6E', letter: 'D' },
    { id: 'telegram', name: 'Telegram', sub: 'Sohbet', cat: 'sohbet', color: '#0E5A8A', letter: 'T' }
  ],

  settingsCategories: [
    { id: 'internet', name: 'İnternet' },
    { id: 'bluetooth', name: 'Bluetooth ve Kumandalar' },
    { id: 'ekran', name: 'Ekran' },
    { id: 'ses', name: 'Ses' },
    { id: 'guc', name: 'Güç ve Uyku' },
    { id: 'windows', name: 'Windows' },
    { id: 'hesaplar', name: 'Hesaplar' },
    { id: 'dil', name: 'Dil ve Bölge' },
    { id: 'guncelleme', name: 'Güncellemeler', badge: '1' },
    { id: 'sistem', name: 'Sistem Bilgisi' }
  ],

  /* What each settings page will hold once it is connected to the system (phase 4). */
  settingsPlans: {
    internet: ['Wi-Fi ağları ve şifre girişi', 'Kablolu bağlantı', 'Bağlantı testi'],
    bluetooth: ['Kumanda eşleştirme', 'Kulaklık ve hoparlör', 'Kumanda titreşimi ve pil'],
    ses: ['Ses düzeyi', 'Çıkış seçimi: TV, kulaklık, hoparlör', 'Mikrofon'],
    guc: ['Uyku zamanlayıcısı', 'Kumandayla uyandırma', 'Ekran koruyucu'],
    windows: ["Windows'a Geç", 'Windows ile saat uyumu', 'Varsayılan açılış sistemi'],
    hesaplar: ['Steam, Epic ve GOG girişleri', 'Profil adı ve resmi', 'Ebeveyn denetimi'],
    dil: ['Dil: Türkçe', 'Klavye: Türkçe Q', 'Saat dilimi: İstanbul'],
    guncelleme: ['K.OS güncellemesi hazır', 'Otomatik güncelleme', 'Önceki sürüme dön'],
    sistem: ['İşlemci, ekran kartı, bellek', 'Depolama alanı', 'K.OS sürümü']
  }
};
