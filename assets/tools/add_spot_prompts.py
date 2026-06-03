import json

prompts = {
    "ペトロナスツインタワー": "Flat vector illustration of Petronas Twin Towers Kuala Lumpur, two soaring silver skyscrapers connected by a sky bridge, Islamic geometric patterns on facade, KLCC park and fountain in foreground, clear blue sky with white clouds, wide landscape",
    "KLタワー": "Flat vector illustration of KL Tower rising above tropical forest on Bukit Nanas hill, city skyline in background, surrounding green canopy, clear blue sky, wide landscape",
    "バトゥ洞窟": "Flat vector illustration of Batu Caves Malaysia, towering limestone cliffs with grand cave entrance, 272 colorful steps, giant golden Lord Murugan statue at base, tropical jungle on both sides, bright blue sky, wide landscape",
    "ブキッビンタン": "Flat vector illustration of Bukit Bintang Kuala Lumpur, vibrant shopping boulevard with modern malls and colorful storefronts, wide street perspective, dusk blue sky with city lights, wide landscape",
    "マスジッドネガラ（国立モスク）": "Flat vector illustration of Masjid Negara National Mosque Kuala Lumpur, blue star-shaped roof and tall minaret, reflecting pool in foreground, manicured gardens, clear blue morning sky, wide landscape",
    "ブルーモスク": "Flat vector illustration of Sultan Salahuddin Abdul Aziz Mosque Shah Alam, massive silver and blue dome with four towering minarets, reflecting pool, manicured gardens, clear blue sky, wide cinematic landscape",
    "ジョージタウン旧市街": "Flat vector illustration of George Town Penang UNESCO heritage street, colorful pastel colonial shophouses, traditional Chinese clan buildings, street art murals, warm morning light, clear blue sky, wide landscape",
    "ペナンヒル": "Flat vector illustration of Penang Hill, lush tropical forest on rolling hills, vintage funicular railway through green canopy, panoramic view of George Town and Penang Strait below, clear blue morning sky, wide landscape",
    "クー・コンシー（邸宅）": "Flat vector illustration of Khoo Kongsi clan house Penang, ornate southern Chinese temple with elaborate red and gold carved roof, dragon sculptures and red lanterns, granite courtyard, clear blue sky, wide landscape",
    "バトゥ・フェリンギビーチ": "Flat vector illustration of Batu Ferringhi beach Penang, long curved sandy beach with calm turquoise water, palm trees leaning over shore, colorful beach umbrellas, clear blue sky with fluffy clouds, wide landscape",
    "ペナン国立公園": "Flat vector illustration of Penang National Park, dense tropical rainforest meeting a secluded sandy beach, mangrove trees along calm river estuary, lush green canopy, crystal clear blue sky, wide landscape",
    "クラン・ジェッティ（桟橋集落）": "Flat vector illustration of Clan Jetties Penang, wooden stilt houses over calm harbor water, narrow wooden walkways, traditional fishing boats moored below, reflections on water, clear blue morning sky, wide landscape",
    "オランダ広場（スタダイス）": "Flat vector illustration of Dutch Square Malacca, terracotta red Stadthuys building and Christ Church, cobblestone plaza with fountain, trishaw with flowers in foreground, clear blue sky, wide landscape",
    "セントポール教会": "Flat vector illustration of St Paul Church ruins Malacca, ancient roofless church walls on hilltop, old gravestones and frangipani trees, panoramic view of Malacca city below, clear blue morning sky, wide landscape",
    "ババニョニャ遺産博物館": "Flat vector illustration of Baba Nyonya Heritage Museum Malacca, beautifully preserved Peranakan townhouse facade, ornate tiles and carved wooden shutters, narrow heritage street, clear blue sky, wide landscape",
    "ジョンカーストリート": "Flat vector illustration of Jonker Street Malacca, vibrant heritage street with colorful shophouses in red yellow blue, Chinese lanterns hanging overhead, wide street perspective, warm morning light, clear blue sky, wide landscape",
    "マラッカ川クルーズ": "Flat vector illustration of Malacca River, colorful murals on riverside walls, vibrant heritage shophouses lining the calm river, wooden tour boats on water, clear blue sky with reflections, wide landscape",
    "ポルトガル村": "Flat vector illustration of Portuguese Settlement Malacca, pastel Portuguese-style houses along waterfront, fishing boats in calm sea, old chapel with cross, tropical palms, clear blue sky, wide landscape",
    "キナバル山": "Flat vector illustration of Mount Kinabalu Sabah Malaysia, dramatic rocky granite peak rising above sea of clouds, montane forest and alpine meadows in foreground, clear blue morning sky, wide cinematic landscape",
    "セピロクオランウータン保護区": "Flat vector illustration of Sepilok Orangutan Rehabilitation Centre Sabah, lush tropical rainforest with tall trees, wooden walkway platform, orangutans in canopy, golden morning light, clear blue sky, wide landscape",
    "マヌカン島": "Flat vector illustration of Manukan Island Sabah, crystal clear turquoise water, white sandy beach fringed with swaying palms, colorful coral reef visible below surface, clear bright blue sky, wide cinematic landscape",
    "シパダン島": "Flat vector illustration of Sipadan Island Sabah, emerald tropical island rising from deep blue ocean, colorful coral and tropical fish below surface, clear blue sky, wide cinematic landscape",
    "フィリピン市場": "Flat vector illustration of Filipino Market Kota Kinabalu, colorful waterfront market stalls with fresh seafood, wooden jetties over calm harbor, fishing boats moored alongside, warm morning light, clear blue sky, wide landscape",
    "ガヤ・ストリート（日曜市）": "Flat vector illustration of Gaya Street Sunday Market Kota Kinabalu, lively street market with colorful vendor stalls, colonial shophouses on both sides, tropical parasols, warm morning light, clear blue sky, wide landscape",
    "サラワク博物館": "Flat vector illustration of Sarawak Museum Kuching, elegant colonial Edwardian white building with terracotta roof, manicured tropical gardens in foreground, clear blue morning sky, wide landscape",
    "バコ国立公園": "Flat vector illustration of Bako National Park Sarawak, dramatic sea stacks and sandstone cliffs rising from South China Sea, dense tropical rainforest on headland, white sandy beach in foreground, clear blue sky, wide cinematic landscape",
    "セメンゴ野生動物センター": "Flat vector illustration of Semenggoh Wildlife Centre Sarawak, lush tropical rainforest with tall trees and thick canopy, feeding platform among trees, morning mist, golden light, clear blue sky visible through canopy, wide landscape",
    "サラワク・カルチャービレッジ": "Flat vector illustration of Sarawak Cultural Village, traditional longhouses of indigenous tribes in lush tropical garden, carved wooden pillars and thatched roofs, clear blue sky, wide cinematic landscape",
    "クチン旧市街・ウォーターフロント": "Flat vector illustration of Kuching Waterfront Sarawak, colorful heritage shophouses along riverfront promenade, traditional sampan boats on Sarawak River, Fort Margherita visible across the water, clear blue morning sky, wide landscape",
    "クチン猫博物館": "Flat vector illustration of Cat Museum Kuching, distinctive modern building with large cat statue at entrance, surrounded by lush tropical gardens, clear blue sky with white clouds, wide landscape",
}

path = r"C:\Users\Asobu\Documents\海外情報サイト\World guide\malaysia\malaysia.json"
with open(path, encoding="utf-8") as f:
    d = json.load(f)

updated = 0
for sec in d.get("spot_sections", []):
    for spot in sec.get("spots", []):
        if spot["name"] in prompts:
            spot["prompt_en"] = prompts[spot["name"]]
            updated += 1

with open(path, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

print(f"{updated}件保存完了")
