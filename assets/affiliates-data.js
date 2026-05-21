/**
 * affiliates-data.js — アフィリエイト データ定義
 *
 * ここを編集するだけで全国ページに反映される。
 * 描画ロジックは affiliates.js が担当。
 *
 * ──────────────────────────────────────────
 *  テキストリンク（AFFILIATES）
 *    → 比較・予約サービスへ誘導するテキストリンク
 *    → HTML: <span data-affiliate="flights"></span>
 *
 *  説明カード（AFFILIATE_CARDS）
 *    → 代替不可サービスの説明カード（Wise・Grabなど）
 *    → HTML: <div data-affiliate-card="wise"></div>
 * ──────────────────────────────────────────
 */

/* =====================================================
   テキストリンク定義
   url は比較ページ完成後に差し替える（現在は # プレースホルダー）
   ===================================================== */
const AFFILIATES = {

  flights: {
    name:  '航空券比較',
    label: '航空券予約サイトを比較する →',
    desc:  '複数の航空会社・予約サイトを一括比較して最安値を見つけよう。',
    btn:   '比較ページを見る →',
    url:   '../compare/flights.html'
  },

  hotels: {
    name:  'ホテル比較',
    label: 'ホテル予約サイトを比較する →',
    desc:  'エリア・価格・口コミで人気ホテルを比較して選べる。',
    btn:   '比較ページを見る →',
    url:   '../compare/hotels.html'
  },

  sim: {
    name:  'eSIM・SIM比較',
    label: '海外SIMサービスを比較する →',
    desc:  '渡航先・日数・データ容量に合ったeSIM・SIMを比較して選べる。',
    btn:   '比較ページを見る →',
    url:   '../compare/sim.html'
  },

  grab: {
    name:  'Grab',
    label: 'Grabアプリを見る →',
    desc:  '東南アジアで必須の配車アプリ。乗車前に料金が確定するためぼったくりゼロ。',
    btn:   'Grabアプリを見る →',
    url:   'https://www.grab.com/',
  },

  wise: {
    name:  'Wise',
    label: 'Wiseカードについて →',
    desc:  '実勢レートに近いレートで両替・送金できるプリペイドカード。現地ATMでの引き出しも手数料が安い。',
    btn:   '公式サイトを見る →',
    url:   'https://wise.com/jp/'
  },

  trifa: {
    name:  'trifa',
    label: 'trifaについて →',
    desc:  '日本発のeSIMサービス。渡航先・日数・容量から最適なプランを選べる。アプリから前日でも購入・設定可能。',
    btn:   'trifaを見る →',
    url:   'https://trifa.jp/'
  },

  // TripAdvisor（後日判断）
  tripadvisor_malaysia: {
    name:  'TripAdvisor',
    label: 'TripAdvisorで探す →',
    desc:  '旅行者の口コミ・評判をチェックしてから観光スポットやレストランを選べる。',
    btn:   'TripAdvisorで探す →',
    url:   'https://www.tripadvisor.jp/Tourism-g293951-Malaysia-Vacations.html'
  },

};

/* =====================================================
   説明カード定義
   新しいサービスをここに追加 → HTML に1行書くだけで表示される
   ===================================================== */
const AFFILIATE_CARDS = {

  wise: {
    icon:    '💳',
    name:    'Wise',
    tagline: '現金を大量に持ち歩かなくていい',
    points: [
      '現地ATMでリンギットをその場で引き出せる',
      '実勢レートに近いレートで両替・送金できる',
      '空港の両替所より手数料が安いことが多い',
      'アプリで残高・履歴をリアルタイム管理',
    ],
    note:  '※ 月2回・合計約5万円相当までは無料でATM引き出し可能（2025年時点）',
    btn:   '公式サイトを見る →',
    url:   'https://wise.com/jp/',
    color: '#1a9068',
  },

  grab: {
    icon:    '🚗',
    name:    'Grab',
    tagline: '東南アジアで必須の配車アプリ',
    points: [
      '乗車前に料金が確定するためぼったくりゼロ',
      'タクシーより安く・英語不要で乗れる',
      'フードデリバリー・バイク配車にも対応',
      'マレーシア全土の主要都市で使用可能',
    ],
    note:  '※ 出発前にアプリをインストールしておくとスムーズ',
    btn:   'Grabアプリを見る →',
    url:   'https://www.grab.com/',
    color: '#1a9068',
  },

  sim_compare: {
    icon:    '📶',
    name:    '海外SIM・eSIM 比較',
    tagline: '渡航先・日数・データ容量で最適なプランを選べる',
    points: [
      '複数のeSIM・SIMサービスを一括比較',
      '国・地域ごとに対応プランを絞り込み',
      'SIM vs eSIM の違いと選び方を解説',
      '出発前にオンラインで申し込んですぐ使える',
    ],
    note:  '※ 掲載サービスは随時更新中',
    btn:   '比較ページを見る →',
    url:   '../compare/sim.html',
    color: '#1a9068',
  },

};
