/* World Mappy 実データ版 destinations.js（プレビュー用）
   index.html の COUNTRIES 配列（全29ヶ国）を、Claude Design案が要求するスキーマに変換して格納。
   budget は元の5段階（budget1〜5）配列から、並び替えた中央寄りの1つを採用し 格安/中級/高級 の3段階に圧縮。
   season(s,e) は bestLabel の主要レンジを1つの連続区間として近似（複数レンジがある国は幅を広めに取っている）。 */
(function () {
  const TIER_LABEL = { 1: '格安', 2: '格安', 3: '中級', 4: '高級', 5: '高級' };
  function budgetLabel(arr) {
    const nums = arr.map((b) => +b.replace('budget', '')).sort((a, b) => a - b);
    const idx = Math.ceil((nums.length - 1) / 2);
    return TIER_LABEL[nums[idx]];
  }

  const RAW = [
    { id: 'malaysia', city: 'マレーシア', country: 'マレーシア', area: '東南アジア', s: 3, e: 10, season: '3〜10月', hours: 7, budgetArr: ['budget1', 'budget2'], tags: ['ビーチ', '世界遺産', 'グルメ', '自然', '都市', '歴史'], lat: 3.14, lon: 101.69, rec: true, blurb: '右にマレー系、左にインド系、後ろを向けば中華系。異なる民族が共生する光景が新鮮。', cardImg: '../malaysia/素材/ヒーロー.webp', href: '../malaysia/index.html', available: true },
    { id: 'thailand', city: 'タイ', country: 'タイ', area: '東南アジア', s: 11, e: 4, season: '11〜4月', hours: 6.5, budgetArr: ['budget1', 'budget2'], tags: ['ビーチ', '世界遺産', 'グルメ', '都市', 'リゾート', '歴史'], lat: 13.75, lon: 100.5, rec: true, blurb: '朝は寺院で線香の煙、昼は屋台でガパオ、夜は街が別の顔を見せる。', cardImg: '../thailand/素材/ヒーロー.webp', href: '../thailand/index.html', available: true },
    { id: 'uzbekistan', city: 'ウズベキスタン', country: 'ウズベキスタン', area: '中央アジア', s: 4, e: 10, season: '4〜6月・9〜10月', hours: 12, budgetArr: ['budget1', 'budget2'], tags: ['世界遺産', '歴史', 'グルメ', '自然', '都市'], lat: 41.3, lon: 69.24, rec: true, blurb: 'シルクロードの古都が残る中央アジアの秘境。青タイルの霊廟と圧倒的なホスピタリティ', cardImg: '../uzbekistan/素材/ヒーロー.webp', href: '../uzbekistan/index.html', available: true },
    { id: 'south_africa', city: '南アフリカ共和国', country: '南アフリカ共和国', area: 'アフリカ', s: 9, e: 11, season: '9〜11月', hours: 22, budgetArr: ['budget2', 'budget3'], tags: ['サファリ', '絶景', '世界遺産', 'グルメ'], lat: -33.92, lon: 18.42, rec: true, blurb: '日本のほぼ反対。あれ？聞いてた話と違う、、自然と都市の融合が気持ちいい。', cardImg: '../south_africa/素材/ヒーロー.webp', href: '../south_africa/index.html', available: true },
    { id: 'taiwan', city: '台湾', country: '台湾', area: '東アジア', s: 10, e: 4, season: '10〜11月・3〜4月', hours: 3.5, budgetArr: ['budget1', 'budget2'], tags: ['グルメ', '夜市', '歴史', '絶景'], lat: 25.03, lon: 121.56, rec: true, blurb: '九份の石段に赤提灯が連なる夕暮れ、湯けむりと夜市の喧騒。', cardImg: '../taiwan/素材/ヒーロー.webp', href: '../taiwan/index.html', available: true },
    { id: 'singapore', city: 'シンガポール', country: 'シンガポール', area: '東南アジア', s: 2, e: 4, season: '2〜4月（通年OK）', hours: 7.5, budgetArr: ['budget2', 'budget3'], tags: ['グルメ', '都市', '夜景', '家族旅行'], lat: 1.35, lon: 103.82, rec: true, blurb: 'マリーナベイの摩天楼にスーパーツリーの光が灯り、屋台街のラクサが夜風に流れる。', cardImg: '../singapore/素材/ヒーロー.webp', href: '../singapore/index.html', available: true },
    { id: 'srilanka', city: 'スリランカ民主社会主義共和国', country: 'スリランカ民主社会主義共和国', area: '南アジア', s: 12, e: 3, season: '12〜3月', hours: 9.5, budgetArr: ['budget2', 'budget3'], tags: ['世界遺産', '紅茶', '自然', 'グルメ'], lat: 6.93, lon: 79.85, rec: true, blurb: '霧に沈む中央高地を走る紅茶列車の車窓いっぱいに、摘みたての茶葉の香り。', cardImg: '../srilanka/素材/ヒーロー.webp', href: '../srilanka/index.html', available: true },
    { id: 'korea', city: '韓国', country: '韓国', area: '東アジア', s: 4, e: 11, season: '4〜5月・9〜11月', hours: 2.25, budgetArr: ['budget1', 'budget2'], tags: ['グルメ', '都市', '歴史'], lat: 37.57, lon: 126.98, rec: true, blurb: '飛行機2時間・時差なしなのに、近すぎて逆に新鮮。', cardImg: '../korea/素材/ヒーロー.webp', href: '../korea/index.html', available: true },
    { id: 'laos', city: 'ラオス人民民主共和国', country: 'ラオス人民民主共和国', area: '東南アジア', s: 11, e: 2, season: '11〜2月', hours: 11, budgetArr: ['budget1'], tags: ['世界遺産', '自然', '歴史'], lat: 17.97, lon: 102.6, rec: false, blurb: '托鉢僧の静かな列と川面にたつ朝もやが、メコン河畔にたたずむ古都を包み込む。', cardImg: '../laos/素材/ヒーロー.webp', href: '../laos/index.html', available: true },
    { id: 'vietnam', city: 'ベトナム', country: 'ベトナム', area: '東南アジア', s: 12, e: 5, season: '12〜5月', hours: 6.25, budgetArr: ['budget1'], tags: ['ビーチ', '世界遺産', 'グルメ', '自然', '歴史'], lat: 21.03, lon: 105.85, rec: true, blurb: '赤い提灯が石畳の運河に揺れるホイアンの夕暮れ、バイクの喧騒とフォーの湯気。', cardImg: '../vietnam/素材/ヒーロー.webp', href: '../vietnam/index.html', available: true },
    { id: 'philippines', city: 'フィリピン', country: 'フィリピン', area: '東南アジア', s: 12, e: 5, season: '12〜5月', hours: 4.75, budgetArr: ['budget1'], tags: ['ビーチ', 'リゾート', 'グルメ', '自然', 'ダイビング'], lat: 14.6, lon: 120.98, rec: false, blurb: '切り立つ石灰岩の断崖が抱くエメラルドのラグーンで、バンカーボートの航跡。', cardImg: '../philippines/素材/ヒーロー.webp', href: '../philippines/index.html', available: true },
    { id: 'spain', city: 'スペイン', country: 'スペイン', area: 'ヨーロッパ', s: 4, e: 10, season: '4〜6月・9〜10月', hours: 15.5, budgetArr: ['budget2', 'budget3'], tags: ['世界遺産', 'グルメ', '建築', '歴史'], lat: 40.42, lon: -3.7, rec: false, blurb: '灼熱の太陽の下、真っ赤な衣装のフラメンコの足音とギターの旋律。', cardImg: '../spain/素材/ヒーロー.webp', href: '../spain/index.html', available: true },
    { id: 'italy', city: 'イタリア', country: 'イタリア', area: 'ヨーロッパ', s: 4, e: 10, season: '4〜6月・9〜10月', hours: 13, budgetArr: ['budget2', 'budget3'], tags: ['世界遺産', 'グルメ', '建築', '歴史'], lat: 41.9, lon: 12.5, rec: false, blurb: '石畳に響くヴェスパの音とジェラート片手の観光客が、古代遺跡に溶け込んでいく。', cardImg: '../italy/素材/ヒーロー.webp', href: '../italy/index.html', available: true },
    { id: 'north_korea', city: '北朝鮮', country: '北朝鮮', area: '東アジア', s: 4, e: 10, season: '現在は渡航不可（参考情報）', hours: 99, budgetArr: ['budget3'], tags: ['史跡', '特殊事情', 'ツアー限定', '現在渡航不可'], lat: 39.02, lon: 125.75, rec: false, blurb: '車もまばらな広い大通りと巨大な指導者像が居並ぶ首都の中心部。', cardImg: '../north_korea/素材/ヒーロー.webp', href: '../north_korea/index.html', available: true },
    { id: 'germany', city: 'ドイツ', country: 'ドイツ', area: 'ヨーロッパ', s: 5, e: 10, season: '5〜6月・9〜10月', hours: 13.5, budgetArr: ['budget2'], tags: ['歴史', 'グルメ', '古城', 'クリスマスマーケット'], lat: 52.52, lon: 13.4, rec: false, blurb: '石畳に響くビールジョッキの乾杯の音と、焼きたてプレッツェルの香ばしい匂い。', cardImg: '../germany/素材/ヒーロー.webp', href: '../germany/index.html', available: true },
    { id: 'newzealand', city: 'ニュージーランド', country: 'ニュージーランド', area: 'オセアニア', s: 11, e: 3, season: '11〜3月（南半球の夏）', hours: 11, budgetArr: ['budget3'], tags: ['自然', 'アウトドア', 'マオリ文化', '映画のロケ地'], lat: -41.29, lon: 174.78, rec: false, blurb: '地熱の間欠泉から立ちのぼる湯気と、力強いハカの足踏み。', cardImg: '../newzealand/素材/ヒーロー.webp', href: '../newzealand/index.html', available: true },
    { id: 'canada', city: 'カナダ', country: 'カナダ', area: '北アメリカ', s: 6, e: 3, season: '6〜9月（夏）／12〜3月（オーロラ）', hours: 11.5, budgetArr: ['budget3'], tags: ['自然', 'アウトドア', 'オーロラ', 'カナディアンロッキー'], lat: 45.42, lon: -75.7, rec: false, blurb: '凍てつく極北の夜空に緑色のオーロラが幾重にも波打つ。', cardImg: '../canada/素材/ヒーロー.webp', href: '../canada/index.html', available: true },
    { id: 'turkey', city: 'トルコ', country: 'トルコ', area: '中東・ヨーロッパ', s: 4, e: 10, season: '4〜6月・9〜10月', hours: 13, budgetArr: ['budget2', 'budget3'], tags: ['世界遺産', 'グルメ', '歴史', '気球'], lat: 41.01, lon: 28.98, rec: false, blurb: 'アヤソフィアの尖塔が夕焼けに染まる中、香辛料バザールの灯り。', cardImg: '../turkey/素材/ヒーロー.webp', href: '../turkey/index.html', available: true },
    { id: 'mexico', city: 'メキシコ', country: 'メキシコ', area: '北米・中南米', s: 11, e: 4, season: '11〜4月', hours: 13.5, budgetArr: ['budget3', 'budget4'], tags: ['世界遺産', 'グルメ', '自然', '歴史', 'マヤ遺跡'], lat: 19.43, lon: -99.13, rec: false, blurb: 'ピラミッドの影が長く伸びる高原の夕暮れに、屋台のタコスとマリアッチ。', cardImg: '../mexico/素材/ヒーロー.webp', href: '../mexico/index.html', available: true },
    { id: 'brazil', city: 'ブラジル', country: 'ブラジル', area: '南米', s: 6, e: 9, season: '6〜9月', hours: 26.5, budgetArr: ['budget4', 'budget5'], tags: ['ビーチ', '自然', '世界遺産', 'サンバ', 'グルメ'], lat: -22.91, lon: -43.17, rec: false, blurb: 'コパカバーナの白い波打ち際にサンバの太鼓が鳴り響く。', cardImg: '../brazil/素材/ヒーロー.webp', href: '../brazil/index.html', available: true },
    { id: 'indonesia', city: 'インドネシア', country: 'インドネシア', area: '東南アジア', s: 4, e: 10, season: '4〜10月の乾季', hours: 7.5, budgetArr: ['budget1', 'budget2'], tags: ['世界遺産', '自然', 'ビーチ', 'リゾート', '棚田'], lat: -8.65, lon: 115.22, rec: true, blurb: '早朝の寺院にくゆる線香の煙と棚田を渡る朝風。', cardImg: '../indonesia/素材/ヒーロー.webp', href: '../indonesia/index.html', available: true },
    { id: 'france', city: 'フランス', country: 'フランス', area: 'ヨーロッパ', s: 4, e: 9, season: '4〜9月', hours: 14, budgetArr: ['budget2', 'budget3'], tags: ['世界遺産', 'グルメ', '都市', '歴史'], lat: 48.85, lon: 2.35, rec: false, blurb: 'セーヌ川沿いのカフェに焼きたてのパンの香りが漂う。', href: '#', available: false },
    { id: 'maldives', city: 'モルディブ', country: 'モルディブ', area: '南アジア', s: 11, e: 4, season: '11〜4月', hours: 10, budgetArr: ['budget3'], tags: ['ビーチ', 'リゾート'], lat: 4.17, lon: 73.51, rec: false, blurb: '透き通るラグーンにぽつんと浮かぶ水上コテージの木陰。', href: '#', available: false },
    { id: 'australia', city: 'オーストラリア', country: 'オーストラリア', area: 'オセアニア', s: 9, e: 2, season: '9〜2月（南半球夏）', hours: 9.5, budgetArr: ['budget2', 'budget3'], tags: ['自然', 'ビーチ', '都市', 'アウトドア'], lat: -33.87, lon: 151.21, rec: false, blurb: '赤土の大地にユーカリの匂いが立ちのぼり、コアラの寝息。', href: '#', available: false },
    { id: 'hawaii', city: 'ハワイ（アメリカ）', country: 'ハワイ（アメリカ）', area: '北アメリカ', s: 4, e: 11, season: '4〜11月', hours: 7.5, budgetArr: ['budget2', 'budget3'], tags: ['ビーチ', 'リゾート', '自然', 'アウトドア'], lat: 21.31, lon: -157.86, rec: false, blurb: '黒い火山灰の岩肌にプルメリアの花の香りが漂う。', href: '#', available: false },
    { id: 'cambodia', city: 'カンボジア', country: 'カンボジア', area: '東南アジア', s: 11, e: 3, season: '11〜3月', hours: 7.5, budgetArr: ['budget1'], tags: ['世界遺産', '歴史', '自然'], lat: 13.36, lon: 103.86, rec: false, blurb: '朝もやに包まれたアンコールワットの石塔に、鳥のさえずり。', href: '#', available: false },
    { id: 'myanmar', city: 'ミャンマー', country: 'ミャンマー', area: '東南アジア', s: 11, e: 2, season: '11〜2月', hours: 8.5, budgetArr: ['budget1'], tags: ['世界遺産', '歴史', '自然'], lat: 16.87, lon: 96.2, rec: false, blurb: '黄金の仏塔が夕焼けに染まるバガンの広大な平原。', href: '#', available: false },
    { id: 'switzerland', city: 'スイス', country: 'スイス', area: 'ヨーロッパ', s: 6, e: 9, season: '6〜9月', hours: 13.5, budgetArr: ['budget3'], tags: ['自然', 'アウトドア', '都市'], lat: 47.37, lon: 8.55, rec: false, blurb: '雪をかぶったアルプスの稜線に、氷河特急の汽笛。', href: '#', available: false },
    { id: 'czech', city: 'チェコ', country: 'チェコ', area: 'ヨーロッパ', s: 4, e: 10, season: '4〜6月・9〜10月', hours: 13.5, budgetArr: ['budget1', 'budget2'], tags: ['世界遺産', '都市', '歴史', 'グルメ'], lat: 50.08, lon: 14.44, rec: false, blurb: '赤茶けた屋根が連なるプラハの旧市街に、教会の鐘の音。', href: '#', available: false },
  ];

  window.WM_DESTINATIONS = RAW.map((d) => Object.assign({}, d, { budget: budgetLabel(d.budgetArr) }));

  window.WM_AREA_BOUNDS = {
    '東南アジア': [[92, -11], [141, 23]],
    '東アジア': [[105, 20], [146, 46]],
    '中央アジア': [[52, 34], [82, 47]],
    '南アジア': [[67, -2], [93, 32]],
    'アフリカ': [[-18, -35], [52, 37]],
    'ヨーロッパ': [[-25, 34], [41, 69]],
    'オセアニア': [[110, -48], [179, -8]],
    '北アメリカ': [[-125, 13], [-58, 51]],
    '北米・中南米': [[-118, 10], [-86, 33]],
    '南米': [[-74, -34], [-34, 5]],
    '中東・ヨーロッパ': [[25, 33], [45, 43]],
  };

  window.dispatchEvent(new Event('wm-data'));
})();
