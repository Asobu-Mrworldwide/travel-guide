/* 診断：タイプ別イラストの対応表（result.html / types.html で共用）
   ファイルは 素材/タイプイラスト/{コード}_{タイプ名}.webp。
   全16タイプ分そろっている。未作成のタイプが出たら載せなければ、呼び出し側が仮画像 TYPE_IMG_FALLBACK を使う。
   新しいイラストを追加するときは、webpを素材/タイプイラスト/に置いて下の表に1行足す。 */
const TYPE_IMG_NAMES = {
  PCSR:'中間管理職', PCSW:'別班員', PCLR:'茶道部', PCLW:'妖怪ガイドブック喰い',
  PNSR:'工場長', PNSW:'シェルパ', PNLR:'熱燗', PNLW:'週末仙人',
  FCSR:'ゴールデンレトリバー', FCSW:'イエスマン', FNSW:'桃太郎',
  FCLR:'街のトリュフ犬', FCLW:'迷ってない人', FNSR:'副本部長', FNLR:'吾輩', FNLW:'タンポポの綿毛',
};
const TYPE_IMG_FALLBACK = 'img/r/model-hero.png';
function typeImg(code) {
  return TYPE_IMG_NAMES[code] ? '素材/タイプイラスト/' + code + '_' + TYPE_IMG_NAMES[code] + '.webp' : null;
}
