/* World Mappy 掲載国データ — 追加はこのファイルだけ編集すれば地図・索引の両方に反映されます。
   rec: true = 地図にデフォルト表示する「おすすめ」 */
(function () {
  window.WM_DESTINATIONS = [
    { id: 'bkk', visa: true, city: 'バンコク', country: 'タイ', area: '東南アジア', s: 11, e: 2, season: '11–2月', hours: 6, budget: '格安', tags: ['グルメ', '都市', '歴史'], lat: 13.75, lon: 100.5, rec: true, blurb: '屋台の煙と金色の寺院が同じ通りに並ぶ王都。物価が安く、はじめての海外旅行にも向いています。' },
    { id: 'dps', visa: true, city: 'バリ島', country: 'インドネシア', area: '東南アジア', s: 5, e: 10, season: '5–10月', hours: 7.5, budget: '中級', tags: ['ビーチ', 'リゾート', '自然'], lat: -8.65, lon: 115.22, rec: true, blurb: '棚田、断崖のビーチ、そして毎日の祈り。リゾートも自然も一島で味わえる、滞在型の南の島。' },
    { id: 'tpe', visa: true, city: '台北', country: '台湾', area: '東アジア', s: 10, e: 4, season: '10–4月', hours: 4, budget: '格安', tags: ['グルメ', '都市'], lat: 25.03, lon: 121.56, rec: true, blurb: '飛行4時間、時差1時間。夜市と小籠包だけで一日が終わる、週末で行ける食の街です。' },
    { id: 'skd', visa: true, city: 'サマルカンド', country: 'ウズベキスタン', area: '中央アジア', s: 4, e: 6, season: '4–6月', hours: 12, budget: '中級', tags: ['世界遺産', '歴史'], lat: 39.65, lon: 66.96, rec: true, blurb: 'シルクロードの結び目に残る群青のドーム群。乾いた風の四月から六月が、最も美しい季節。' },
    { id: 'mle', visa: true, city: 'モルディブ', country: 'モルディブ', area: '南アジア', s: 12, e: 4, season: '12–4月', hours: 11, budget: '高級', tags: ['ビーチ', 'リゾート'], lat: 3.2, lon: 73.22, rec: false, blurb: '水上コテージの床下にそのまま海がある島国。何もしない贅沢のために行く、静かな休暇。' },
    { id: 'rak', visa: true, city: 'マラケシュ', country: 'モロッコ', area: 'アフリカ', s: 3, e: 5, season: '3–5月', hours: 17, budget: '中級', tags: ['世界遺産', 'グルメ', '歴史'], lat: 31.63, lon: -7.99, rec: true, blurb: '迷路のような旧市街を抜けると、赤い土壁と屋台の広場。サハラへの入口にもなる街です。' },
    { id: 'lis', visa: true, city: 'リスボン', country: 'ポルトガル', area: 'ヨーロッパ', s: 4, e: 6, season: '4–6月', hours: 15, budget: '中級', tags: ['都市', 'グルメ', '歴史'], lat: 38.72, lon: -9.14, rec: true, blurb: '坂とタイルと大西洋。西欧のなかでは物価がやさしく、路面電車で一日歩ける港の首都。' },
    { id: 'zqn', visa: true, city: 'クイーンズタウン', country: 'ニュージーランド', area: 'オセアニア', s: 12, e: 3, season: '12–3月', hours: 13, budget: '中級', tags: ['自然', 'アドベンチャー'], lat: -45.03, lon: 168.66, rec: false, blurb: '日本の冬に夏が来る、湖と南アルプスの町。ハイキングも星空も気球も、ここに集まります。' },
    { id: 'mex', visa: true, city: 'メキシコシティ', country: 'メキシコ', area: '北アメリカ', s: 3, e: 5, season: '3–5月', hours: 13, budget: '中級', tags: ['グルメ', '世界遺産', '都市'], lat: 19.43, lon: -99.13, rec: false, blurb: '巨大な遺跡の上に建つ、標高2,240mの大都市。タコスと壁画とピラミッドを一度に。' },
    { id: 'kef', visa: true, city: 'レイキャビク', country: 'アイスランド', area: 'ヨーロッパ', s: 6, e: 8, season: '6–8月', hours: 15, budget: '高級', tags: ['自然', 'アドベンチャー'], lat: 64.15, lon: -21.94, rec: false, blurb: '白夜の夏は太陽が沈まない。温泉、滝、溶岩の島を車で巡る、旅慣れた人向けの北の島。' },
  ];
  window.WM_AREA_BOUNDS = {
    '東南アジア': [[92, -11], [141, 23]],
    '東アジア': [[105, 20], [146, 46]],
    '中央アジア': [[52, 34], [82, 47]],
    '南アジア': [[67, -2], [93, 32]],
    'アフリカ': [[-18, -35], [52, 37]],
    'ヨーロッパ': [[-25, 34], [41, 69]],
    'オセアニア': [[110, -48], [179, -8]],
    '北アメリカ': [[-125, 13], [-58, 51]],
  };
  window.dispatchEvent(new Event('wm-data'));
})();
