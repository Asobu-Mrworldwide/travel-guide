/* World Mappy 掲載国データ（実データ）— トップページの地図・索引カードで共有。
   追加・変更はこのファイルだけ編集すればOK。
   rec: true = 地図にデフォルト表示する「おすすめ」
   months: ベストシーズンの月（1〜12、複数可・非連続もOK） */
(function () {
  window.WM_DESTINATIONS = [
    { id: 'malaysia', visa: true, rec: true, name: 'マレーシア', nameEn: 'Malaysia', area: '東南アジア', hours: 7, budget: '格安', tags: ['ビーチ', '世界遺産', 'グルメ', '自然', '都市', '歴史'], months: [3,4,5,6,7,8,9,10], lat: 3.14, lon: 101.69, blurb: '右にマレー系、左にインド系、後ろを向けば中華系。異なる民族が共生する光景が新鮮。', url: 'malaysia/index.html', img: 'malaysia/素材/ヒーロー.webp' },
    { id: 'thailand', visa: true, rec: true, name: 'タイ', nameEn: 'Thailand', area: '東南アジア', hours: 7, budget: '格安', tags: ['ビーチ', '世界遺産', 'グルメ', '都市', 'リゾート', '歴史'], months: [11,12,1,2,3,4], lat: 13.75, lon: 100.5, blurb: '朝は寺院で線香の煙、昼は屋台でガパオ、夜は街が別の顔を見せる。料理も景色も物価も、全部が旅人の味方。', url: 'thailand/index.html', img: 'thailand/素材/ヒーロー.webp' },
    { id: 'uzbekistan', visa: true, rec: false, name: 'ウズベキスタン', nameEn: 'Uzbekistan', area: '中央アジア', hours: 14, budget: '格安', tags: ['世界遺産', '歴史', 'グルメ', '自然', '都市'], months: [4,5,6,9,10], lat: 41.31, lon: 69.28, blurb: 'シルクロードの古都が残る中央アジアの秘境。青タイルの霊廟と圧倒的なホスピタリティ', url: 'uzbekistan/index.html', img: 'uzbekistan/素材/ヒーロー.webp' },
    { id: 'south_africa', visa: true, rec: false, name: '南アフリカ共和国', nameEn: 'South Africa', area: 'アフリカ', hours: 24, budget: '中級', tags: ['サファリ', '絶景', '世界遺産', 'グルメ'], months: [9,10,11], lat: -25.75, lon: 28.19, blurb: '日本のほぼ反対。あれ？聞いてた話と違う、、自然と都市の融合が気持ちいい。ごはんも結構口に合うじゃないか。', url: 'south_africa/index.html', img: 'south_africa/素材/ヒーロー.webp' },
    { id: 'taiwan', visa: true, rec: true, name: '台湾', nameEn: 'Taiwan', area: '東アジア', hours: 4, budget: '格安', tags: ['グルメ', '夜市', '歴史', '絶景'], months: [3,4,10,11], lat: 25.03, lon: 121.56, blurb: '九份の石段に赤提灯が連なる夕暮れ、湯けむりと夜市の喧騒、屋台の油の匂いが旧き良き台湾の路地に立ちのぼる', url: 'taiwan/index.html', img: 'taiwan/素材/ヒーロー.webp' },
    { id: 'singapore', visa: true, rec: false, name: 'シンガポール', nameEn: 'Singapore', area: '東南アジア', hours: 8, budget: '中級', tags: ['グルメ', '都市', '夜景', '家族旅行'], months: [2,3,4], lat: 1.35, lon: 103.82, blurb: 'マリーナベイの摩天楼にスーパーツリーの光が灯り、屋台街のラクサとチキンライスの湯気が夜風に流れる', url: 'singapore/index.html', img: 'singapore/素材/ヒーロー.webp' },
    { id: 'srilanka', visa: true, rec: false, name: 'スリランカ民主社会主義共和国', nameEn: 'Sri Lanka', area: '南アジア', hours: 10, budget: '中級', tags: ['世界遺産', '紅茶', '自然', 'グルメ'], months: [12,1,2,3], lat: 6.93, lon: 79.85, blurb: '霧に沈む中央高地を走る紅茶列車の車窓いっぱいに、摘みたての茶葉の香りと涼しい風が静かにきらめく', url: 'srilanka/index.html', img: 'srilanka/素材/ヒーロー.webp' },
    { id: 'korea', visa: true, rec: true, name: '韓国', nameEn: 'Korea', area: '東アジア', hours: 2.5, budget: '格安', tags: ['グルメ', '都市', '歴史'], months: [4,5,9,10,11], lat: 37.57, lon: 126.98, blurb: '飛行機2時間・時差なしなのに、近すぎて逆に新鮮。宮殿もカフェも本気の異文化がそこにある。', url: 'korea/index.html', img: 'korea/素材/ヒーロー.webp' },
    { id: 'laos', visa: true, rec: false, name: 'ラオス人民民主共和国', nameEn: 'Laos', area: '東南アジア', hours: 13, budget: '格安', tags: ['世界遺産', '自然', '歴史'], months: [11,12,1,2], lat: 17.97, lon: 102.6, blurb: '托鉢僧の静かな列と川面にたつ朝もやが、メコン河畔にたたずむ古都ルアンパバーンの朝をそっと包み込む', url: 'laos/index.html', img: 'laos/素材/ヒーロー.webp' },
    { id: 'vietnam', visa: true, rec: false, name: 'ベトナム', nameEn: 'Vietnam', area: '東南アジア', hours: 6.5, budget: '格安', tags: ['ビーチ', '世界遺産', 'グルメ', '自然', '歴史'], months: [12,1,2,3,4,5], lat: 21.03, lon: 105.85, blurb: '赤い提灯が石畳の運河に揺れるホイアンの夕暮れ、バイクの喧騒とフォーの湯気が旧市街の路地に漂う', url: 'vietnam/index.html', img: 'vietnam/素材/ヒーロー.webp' },
    { id: 'philippines', visa: true, rec: false, name: 'フィリピン', nameEn: 'Philippines', area: '東南アジア', hours: 5, budget: '格安', tags: ['ビーチ', 'リゾート', 'グルメ', '自然', 'ダイビング'], months: [12,1,2,3,4,5], lat: 14.6, lon: 120.98, blurb: '切り立つ石灰岩の断崖が抱くエメラルドのラグーンで、バンカーボートの航跡と潮騒の匂いが陽光にきらめく', url: 'philippines/index.html', img: 'philippines/素材/ヒーロー.webp' },
    { id: 'spain', visa: true, rec: true, name: 'スペイン', nameEn: 'Spain', area: 'ヨーロッパ', hours: 17, budget: '中級', tags: ['世界遺産', 'グルメ', '建築', '歴史'], months: [4,5,6,9,10], lat: 40.42, lon: -3.70, blurb: '灼熱の太陽の下、真っ赤な衣装のフラメンコの足音とギターの旋律がタパスバルの喧騒とともに沸き立つ', url: 'spain/index.html', img: 'spain/素材/ヒーロー.webp' },
    { id: 'italy', visa: true, rec: true, name: 'イタリア', nameEn: 'Italy', area: 'ヨーロッパ', hours: 13, budget: '中級', tags: ['世界遺産', 'グルメ', '建築', '歴史'], months: [4,5,6,9,10], lat: 41.9, lon: 12.5, blurb: '石畳に響くヴェスパの音とジェラート片手の観光客が、古代遺跡と教会の鐘の音に溶け込んでいく', url: 'italy/index.html', img: 'italy/素材/ヒーロー.webp' },
    { id: 'north_korea', visa: false, rec: false, name: '北朝鮮', nameEn: 'North Korea (DPRK)', area: '東アジア', hours: 10, budget: '高級', tags: ['史跡', '特殊事情', 'ツアー限定', '現在渡航不可'], months: [4,5,9,10], lat: 39.02, lon: 125.75, blurb: '車もまばらな広い大通りと巨大な指導者像が居並ぶ首都の中心部を、案内員同行の一団がそっと歩き抜ける', url: 'north_korea/index.html', img: 'north_korea/素材/ヒーロー.webp' },
    { id: 'germany', visa: true, rec: false, name: 'ドイツ', nameEn: 'Germany', area: 'ヨーロッパ', hours: 14, budget: '中級', tags: ['歴史', 'グルメ', '古城', 'クリスマスマーケット'], months: [5,6,9,10], lat: 52.52, lon: 13.4, blurb: '石畳に響くビールジョッキの乾杯の音と、焼きたてプレッツェルの香ばしい匂いが古城の丘へ静かに広がる', url: 'germany/index.html', img: 'germany/素材/ヒーロー.webp' },
    { id: 'newzealand', visa: true, rec: true, name: 'ニュージーランド', nameEn: 'New Zealand', area: 'オセアニア', hours: 11, budget: '高級', tags: ['自然', 'アウトドア', 'マオリ文化', '映画のロケ地'], months: [11,12,1,2,3], lat: -41.29, lon: 174.78, blurb: '地熱の間欠泉から立ちのぼる湯気と、力強いハカの足踏みが、氷河と羊の牧草地へ静かに染み渡る', url: 'newzealand/index.html', img: 'newzealand/素材/ヒーロー.webp' },
    { id: 'canada', visa: true, rec: true, name: 'カナダ', nameEn: 'Canada', area: '北アメリカ', hours: 13, budget: '高級', tags: ['自然', 'アウトドア', 'オーロラ', 'カナディアンロッキー'], months: [6,7,8,9,12,1,2,3], lat: 45.42, lon: -75.7, blurb: '凍てつく極北の夜空に緑色のオーロラが幾重にも波打ち、湖面に張りつめた氷の静寂が辺り一帯をそっと静める', url: 'canada/index.html', img: 'canada/素材/ヒーロー.webp' },
    { id: 'turkey', visa: true, rec: false, name: 'トルコ', nameEn: 'Turkey', area: 'ヨーロッパ', hours: 13, budget: '中級', tags: ['世界遺産', 'グルメ', '歴史', '気球'], months: [4,5,6,9,10], lat: 39.93, lon: 32.86, blurb: 'アヤソフィアの尖塔が夕焼けに染まる中、香辛料バザールの灯りとチャイの湯気が石畳にゆらりと揺らめく', url: 'turkey/index.html', img: 'turkey/素材/ヒーロー.webp' },
    { id: 'mexico', visa: true, rec: false, name: 'メキシコ', nameEn: 'Mexico', area: '北アメリカ', hours: 14, budget: '高級', tags: ['世界遺産', 'グルメ', '自然', '歴史', 'マヤ遺跡'], months: [11,12,1,2,3,4], lat: 19.43, lon: -99.13, blurb: 'ピラミッドの影が長く伸びる高原の夕暮れに、屋台のタコスと陽気なマリアッチの音色が街角を彩る', url: 'mexico/index.html', img: 'mexico/素材/ヒーロー.webp' },
    { id: 'brazil', visa: true, rec: false, name: 'ブラジル', nameEn: 'Brazil', area: '南米', hours: 28, budget: '高級', tags: ['ビーチ', '自然', '世界遺産', 'サンバ', 'グルメ'], months: [6,7,8,9], lat: -22.9, lon: -43.2, blurb: 'コパカバーナの白い波打ち際にサンバの太鼓が鳴り響き、丘の上からキリスト像がリオの夜景をそっと見守る', url: 'brazil/index.html', img: 'brazil/素材/ヒーロー.webp' },
    // インドネシア: イラスト未生成のため準備中（indonesia/ 配下のページ・JSONはコミット済み、画像が揃い次第ここへ戻す）
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
    '南米': [[-82, -34], [-34, 13]],
  };
  window.dispatchEvent(new Event('wm-data'));
})();
