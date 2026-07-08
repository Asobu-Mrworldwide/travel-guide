#!/usr/bin/env python3
"""
国ページ自動生成スクリプト
使い方:  python generate.py <country_id>
例:      python generate.py thailand

読み込み: <country_id>/<country_id>.json
         assets/country_template.html
出力:     <country_id>/index.html
"""
import json, re, os, sys, urllib.parse


# ──────────────────────────────────────────
# 移動アイコン（transit行 / pre_transit）
# ──────────────────────────────────────────
TRANSIT_ICONS = {
    'ferry': '<svg xmlns="http://www.w3.org/2000/svg" width="2em" height="2em" viewBox="0 0 128 128"><path d="M0 0h128v128H0z" fill="none"/><path fill="#fff" d="m73.16 20.34l.33-2.16H61.37l-.85 2.16z"/><path fill="#855c52" d="M55.17 61.02H5.6a2.68 2.68 0 0 1 0-5.36h49.56c1.48 0 2.68 1.2 2.68 2.68l-.08 1.6c.01 1.49-1.11 1.08-2.59 1.08"/><path fill="#855c52" d="m10.85 72.67l.07-16.21h5.32l-.08 16.21zm11.33-.04l.07-16.21h5.32l-.08 16.21zm11.35.04l.08-16.21h5.31l-.07 16.21z"/><path fill="#ed6c30" d="M56.4 31.12h16.17l.58-10.78H60.52c-1.96 5.04-4.12 10.78-4.12 10.78M73.66 17.1c0-2.16-2.16-2.16-2.16-2.16h-6.47s-2.34-.08-3.23 2.16c-.14.35-.28.71-.43 1.08h12.12z"/><path fill="#006ca2" d="M12.12 75.79s1.85 3.49 4.28 7.97c.68 1.26 5.94 2.65 6.78 3.96c4.22 6.51 8.02 11.92 8.94 13.2c1.92 2.67 4.7 7.99 13.7 7.99H128V75.79z"/><path fill="#40c0e7" d="M127.36 71.61H11.02c-.48 0-.79.51-.57.93l2.66 5.12l114.25.34c.35 0 .64-.29.64-.64v-5.11c0-.35-.29-.64-.64-.64"/><path fill="#78a3ad" d="M128 46.38H57.9c-1.72 0-4.01 1.1-5.08 2.44l-13.48 22.8H128z"/><path fill="#78a3ad" d="M53.37 57.23L40.76 31.1H128v6H50.32l8.45 17.53z"/><path fill="#78a3ad" d="m128 34.1l-79.17-.52l5.92 22.35H128z"/><path fill="#40c0e7" d="M127.94 113.52H8.35c-1.3 0-2.37-1.07-2.37-2.37s1.07-2.37 2.37-2.37h119.58v4.74z"/><path fill="#fff" d="M73.87 65.06h-6.33c-.87 0-1.58-.71-1.58-1.58v-7.81c0-.87.71-1.58 1.58-1.58h6.33c.87 0 1.58.71 1.58 1.58v7.81c.01.87-.7 1.58-1.58 1.58m14.74 0h-6.33c-.87 0-1.58-.71-1.58-1.58v-7.81c0-.87.71-1.58 1.58-1.58h6.33c.87 0 1.58.71 1.58 1.58v7.81c0 .87-.71 1.58-1.58 1.58m14.74 0h-6.33c-.87 0-1.58-.71-1.58-1.58v-7.81c0-.87.71-1.58 1.58-1.58h6.33c.87 0 1.58.71 1.58 1.58v7.81c0 .87-.71 1.58-1.58 1.58m14.74 0h-6.33c-.87 0-1.58-.71-1.58-1.58v-7.81c0-.87.71-1.58 1.58-1.58h6.33c.87 0 1.58.71 1.58 1.58v7.81c0 .87-.71 1.58-1.58 1.58M55.97 55.01l-4.58 8.11c-.47.84.13 1.88 1.09 1.88h7.14c.69 0 1.26-.56 1.26-1.26v-8.11c0-.69-.56-1.26-1.26-1.26h-2.55c-.46.01-.87.25-1.1.64M115.04 46H77.79c-2.55 0-4.63-2.07-4.63-4.62s2.07-4.62 4.63-4.62h37.25c2.55 0 4.62 2.07 4.62 4.62c.01 2.55-2.06 4.62-4.62 4.62"/><path fill="#78a3ad" d="M62.17 37.25h-25.5c-1.7 0-3.08-1.38-3.08-3.08s1.38-3.08 3.08-3.08h25.5c1.7 0 3.08 1.38 3.08 3.08s-1.38 3.08-3.08 3.08"/><path fill="#fff" d="M50.5 37.17h15.39v3.89H52.26zm2.76 7.21h12.63v3.54h-11.1z"/><path fill="#78a3ad" d="M87.58 35.92h3.67v10.67h-3.67zm14 0h3.67v10.67h-3.67z"/></svg>',
    'taxi': '<svg xmlns="http://www.w3.org/2000/svg" width="2em" height="2em" viewBox="0 0 128 128"><path d="M0 0h128v128H0z" fill="none"/><path fill="#78a3ad" d="M67.5 41.68c-.51 0-.93-.65-.93-1.44v-6.38c0-.79-.64-1.43-1.43-1.43h-4.49c-.79 0-1.44.65-1.44 1.43v6.38c0 .79-.42 1.44-.93 1.44s-.94.65-.94 1.43v2.54c0 .79.42 1.43.94 1.43h9.23c.51 0 .93-.64.93-1.43v-2.54c0-.78-.42-1.43-.94-1.43"/><defs><path id="SVGl3RsjXQW" d="M121.57 79.19c-4.68-4.68-12-6.14-12-6.14s-3.83-9.95-7.06-14.28c-8.78-11.8-19.77-14.44-37.58-14.44c-12.31 0-24.53.47-34.54 13.08c-3.83 4.83-10.11 15.64-10.11 15.64s-10.01 2.24-15.07 7.88c-3.88 4.32-6.79 18.9-1.67 24.01c4.73 4.73 9.89 7.06 13.32 7.06h95.17c5.17 0 9.52-2.6 12.24-6.96c4.66-7.48 1.97-21.17-2.7-25.85"/></defs><use fill="#fcc21b" href="#SVGl3RsjXQW"/><clipPath id="SVGL121CcaL"><use href="#SVGl3RsjXQW"/></clipPath><path fill="#f79329" d="M-4.13 85.07h42.18v14.88H-4.13zm91.83 0h42.39v14.88H87.7z" clip-path="url(#SVGL121CcaL)"/><path fill="#2f2f2f" d="M40.72 109.71c0 6.24-5.06 11.31-11.3 11.31c-6.25 0-11.31-5.06-11.31-11.31c0-6.24 5.06-11.29 11.31-11.29c6.24 0 11.3 5.05 11.3 11.29m68.28 0c0 6.24-5.07 11.31-11.3 11.31c-6.25 0-11.31-5.06-11.31-11.31c0-6.24 5.06-11.29 11.31-11.29c6.23 0 11.3 5.05 11.3 11.29M60 86.46h-2.67c-.11 0-.2.06-.24.16l-4.31 11.46c-.03.08-.02.17.03.23c.05.07.12.12.21.12h2.83c.11 0 .21-.07.24-.18l.66-1.97h3.85l.65 1.97c.04.11.13.18.25.18h2.82c.08 0 .16-.05.21-.12c.05-.06.06-.15.04-.23l-4.31-11.46c-.06-.1-.15-.16-.26-.16m-2.46 7.4l1.12-3.37l1.12 3.37zm24.6-7.4h-2.83c-.14 0-.25.12-.25.26v11.46c0 .14.12.26.25.26h2.83c.14 0 .26-.12.26-.26V86.72c0-.14-.12-.26-.26-.26m-8.37 6.03l3.78-5.63c.06-.08.06-.18.02-.27a.25.25 0 0 0-.23-.13h-3.19c-.08 0-.16.05-.21.11l-2.12 3.08l-2.13-3.08a.24.24 0 0 0-.21-.11H66.3c-.09 0-.18.05-.22.13c-.04.09-.04.19.01.27l3.79 5.63l-3.81 5.55c-.06.07-.06.18-.02.26c.04.09.12.14.23.14h3.35c.08 0 .17-.05.21-.12l1.98-2.94l1.97 2.94c.05.07.13.12.21.12h3.35a.254.254 0 0 0 .21-.4zm-19.62-3.82V86.6c0-.14-.12-.26-.26-.26H42.92c-.13 0-.25.12-.25.26v2.07c0 .14.12.26.25.26h3.97v9.25c0 .14.12.26.25.26h2.51c.14 0 .26-.12.26-.26v-9.25h3.97c.15-.01.27-.12.27-.26"/><path fill="#40c0e7" d="M58.6 71.35c0 2.85-1.83 3.81-4.08 3.81H38.57c-5.52 0-2.55-8.34 2.84-14.25s13.69-6.38 14.83-6.09c2.2.54 2.36 2.58 2.36 4.81zm6.89 0c0 2.85 2.66 3.81 5.89 3.81H92.4c7.98 0 3.35-11.62-4.76-17.09c-5.76-3.88-17.09-3.54-18.74-3.26c-3.19.54-3.41 2.58-3.41 4.81z"/></svg>',
    'plane': '<svg xmlns="http://www.w3.org/2000/svg" width="2em" height="2em" viewBox="0 0 128 128"><path d="M0 0h128v128H0z" fill="none"/><path fill="#0f6da0" d="m84.7 42.3l-40.3-5.5c-1.4-.2-2.9-.1-4.3.2c-2.2.5-2.6 3.5-.6 4.6l19.9 10.1z"/><circle cx="73.4" cy="64.8" r="3.5" fill="#78a3ad"/><circle cx="110.6" cy="42" r="3.5" fill="#78a3ad"/><path fill="#0f6da0" d="M113.4 24.4s.2 4.1-7 6.2c-1.1.4.2 4.3 1.2 4.3c1.2 0 14.8-4.7 14.6-9.4c-3-1.3-8.8-1.1-8.8-1.1"/><path fill="#757f3f" d="M128 117.2c0 1.5-1.2 2.7-2.7 2.7H2.6c-1.5 0-2.7-1.2-2.7-2.7s1.2-2.7 2.7-2.7h122.7c1.5 0 2.7 1.2 2.7 2.7"/><path fill="#48c0e5" d="M12.9 64c-.8-.7-.6-2.1.4-2.6c13-6.1 84-39.1 91.1-42.5c7.8-3.7 13.6.7 15.6 2.4s4.3.5 5.7 2.6c1.4 2 1 7.6-14.7 14.8c-16.9 7.8-51.8 23.8-58.9 26.8c-6.8 2.9-27.8 8.2-39.2-1.5"/><path fill="#0f6da0" d="M87 49.4c.3-.3.4-.8.2-1.2c-.7-1.3-2.8-4-7.7-4c-5.1 0-18.2 7.8-24 11.1c-.9.5-.9 1.7 0 2.3c1.3.7 1.7 2.4 1 3.7L44.1 82.9c-.7 1.3.3 2.9 1.8 2.9h1.3c2.8 0 5.5-1.2 7.4-3.2zM24.6 62.6c-2.3 1.2-5.1 2.6-6.5 3.4c-.3.2-.6.5-.8.9l-1.8 6.7c-.4 1.8 1.9 2.9 3.1 1.5l8.4-11c.9-1.3-.4-2.6-2.4-1.5m4.1-7.7c-.3-1.4-6.5-.9-11.5-3.1c-6.6-2.9-10.3-4.9-13.5-6.4c-1.7-.8-3.3.8-2.1 2.5l11 15.7c.3.4.9.5 1.3.3c0 0 9.9-5.2 14.8-9m92.2-33.1s-1.9 2.7-6.5 5.1c-1.1.6-2.5.1-3-1c-.4-1-.1-2.1.8-2.7c.7-.5 1.6-1.1 2.2-1.5c1.4-1.2 2.6-2.6 2.6-2.6s1.6 1 3.9 2.7"/></svg>',
    'walk': '<svg xmlns="http://www.w3.org/2000/svg" width="2em" height="2em" viewBox="0 0 36 36"><path d="M0 0h36v36H0z" fill="none"/><path fill="#292f33" d="m17.989 34.975l.052.016a1.5 1.5 0 0 1-.042-.383c0-.303.156-.869.199-.95s.09-.139.194-.11c.079.022.685.326 1.072.341c.719.027 1.066-.618 1.066-.618s.399.228.716.413c.318.185.687.462.959.627c.232.141.497.208.771.243s.497.023.563.029s.621-.061.641.488l-.003.127l.054-.026s.048.17.052.202c.004.033.024.052-.046.096s-.378.176-.77.274s-1.028.243-1.519.243s-.909-.098-1.151-.156c-.243-.058-.763-.169-.813-.146s-.116.191-.173.243c-.058.052-1.61-.081-1.721-.104a.18.18 0 0 1-.146-.162v-.649c-.002-.027.021-.045.045-.038M7.042 31.223l.504-.429a.038.038 0 0 1 .059.012l.022.051c.041-.059.12-.158.269-.285c.235-.2.777-.454.868-.473c.091-.02.167-.022.213.077c.035.076.199.746.444 1.056c.454.575 1.184.418 1.184.418l.153.828c.067.368.096.838.148 1.158c.044.273.167.523.322.758c.154.236.31.4.35.456s.457.441.045.82l-.101.081l.055.025s-.1.149-.122.174s-.025.053-.104.028s-.386-.177-.721-.416c-.336-.24-.868-.637-1.192-1.018c-.325-.381-.524-.77-.64-.996s-.373-.703-.424-.727s-.224.036-.303.026s-1.001-1.302-1.057-1.403s-.005-.193.028-.221"/><path fill="#f9ca55" d="M16.7 12.243c-.927.96-3.062 2.89-3.109 3.121c-.251 1.223-.614 2.606-.52 3.454c.068.615-.376 1.298-.551 1.583c-.218.354-.781.898-1.141.86c-.224-.023-.567-.43-.384-.636c.357-.4.298-1.009.522-1.559c.449-1.105.045-3.194.661-4.563c.256-.567.733-1.693 2.824-3.626c.511.462 1.698 1.366 1.698 1.366"/><path fill="#ffdc5d" d="M16.995 1.384c1.593-.627 4.077.182 4.365 2.043c.287 1.848-.239 4.747-1.863 4.572c-1.702-.184-3.448-.554-4.138-2.307s.043-3.681 1.636-4.308"/><path fill="#ffdc5d" d="M15.811 6.143c-2.318-2.723 3.266-2.458 3.266-2.458c1.057.038.329 1.799.827 2.761c.341.665-1.095 1.018-1.095 1.018s-.659-.01-.694.79v.007c-.008.204.013.445.108.769c.473 1.601-1.677 2.582-2.149.978c-.187-.635-.114-1.193-.02-1.708l.009-.046c.144-.766.322-1.437-.252-2.111"/><path fill="#ffac33" d="M15.175 2.026c1.061-1.242 2.58-1.901 5.019-.791c.994.452 1.439.285 1.58.484c.679.953-.246 2.01-.608 1.799c-1.148-.669-2.183-.47-2.447.014s-.021 1.354-.234 1.359c-.579.015-.485-.552-.714-.878c-.375-.534-.946-.232-1.071.362c-.099.471 0 1.271.77 1.412c-.523 1.151-1.56 1.502-1.56 1.502s-.337.132-.912-1.001c-.576-1.134-.877-3.029.177-4.262"/><path fill="#2a6797" d="M19.938 34.203c1.266.109 1.853-.233 1.721-.416c-.165-.228-.128-.397-.13-.536c-.028-2.441.471-5.991.471-5.991c0-.348-.003-.813-.312-1.562c-.778-1.883-3.951-7.69-3.951-7.69a2 2 0 0 0-2.729-.744c-.959.548-1.122 1.405-.744 2.729c.715 2.508 2.965 5.602 3.903 7.477c-.224 2.121.174 3.853-.035 5.857c-.03.288.54.767 1.806.876"/><path fill="#4289c1" d="M9.203 31.931c.364.553.97.942 1.598.838c1.269-1.924 4.955-5.321 4.955-5.321c.241-.25.562-.587.86-1.341c.748-1.895 2.498-8.277 2.498-8.277a2 2 0 0 0-1.446-2.43c-1.07-.272-1.783.232-2.43 1.446c-1.227 2.301-1.757 6.09-2.384 8.09c-1.87 1.568-2.383 3.603-4.275 5.151c.065.857.26 1.291.624 1.844"/><path fill="#77b255" d="M13 20s0 1 2 1h4.898c.415-2 .027-5.004-.006-7.765c-.043-3.623-2.298-5.609-3.71-5.155c-1.846.594-2.693 2.641-2.932 5.858S13 20 13 20"/><path fill="#ffdc5d" d="M18.25 11.792c.167 1.399.322 4.433.479 4.625c.833 1.021 1.722 2.24 2.479 2.729c.549.354.811 1.174.927 1.507c.144.414.213 1.238-.057 1.507c-.169.168-.73.177-.776-.11c-.09-.559-.626-.917-.927-1.467c-.604-1.104-2.583-2.167-3.292-3.584c-.294-.588-.896-1.729-1.083-4.729c.72-.11 2.25-.478 2.25-.478"/></svg>',
    'train': '<svg xmlns="http://www.w3.org/2000/svg" width="2em" height="2em" viewBox="0 0 128 128"><g><g><path style="fill:#543529;" d="M29.3,105.76c0,0-0.37,1.11-0.38,1.98s0.12,2.64,1.68,2.64c2.02,0,24.86-0.07,35.87,0s31.28-0.14,32.7-0.22c1.42-0.07,1.03-3.22,0.94-4.3L29.3,105.76z"/><path style="fill:#874D36;" d="M102.23,116.02l2.89,1.99c0,0,1.87,1.63,2.12,2.61c0.25,0.98-0.33,2.84-1.16,3.23L62.74,124l-40.42-0.12c-0.63-0.16-1.39-0.77-1.58-1.89s0.43-2.37,0.82-3.15c0.39-0.78,8.43-2.81,8.43-2.81L102.23,116.02z"/><path style="fill:#B88956;" d="M25.89,113.94c-0.78,0.01-1.35,0.94-1.82,1.55c-1.22,1.57-1.99,2.56-2.5,3.35c-0.7,1.09,0.7,2.03,1.95,2.03s83.39,0.12,83.59-0.41c0.27-0.7-1.33-3.09-2.65-5.29c-0.46-0.77-1.46-1.82-2.36-1.81L25.89,113.94z"/><path style="fill:#A06841;" d="M32.22,100.82l-2.78,4.53c-0.48,0.78,0.08,1.78,1,1.78l68.52-0.04c0.91,0,1.47-0.99,1.01-1.77l-2.69-4.51H32.22z"/><g><g><path style="fill:#88857C;" d="M47.25,101.55l-8.15,22.39h-4.94l-2.83-5.39l9.04-19.45C40.37,99.09,47.7,100.1,47.25,101.55z"/><path style="fill:#C8C9C6;" d="M28.81,123.97c0.12-0.42,8.45-17.94,8.45-17.94c0.52-1.09,4.91-0.6,4.2,1.46s-5.74,16.44-5.74,16.44L28.81,123.97z"/></g><g><path style="fill:#88857C;" d="M79.99,101.55l8.19,22.36l4.89-0.01l2.84-5.35l-9.04-19.45C86.88,99.09,79.54,100.1,79.99,101.55z"/><path style="fill:#C8C9C6;" d="M98.42,123.88c-0.12-0.42-8.47-17.91-8.47-17.91c-0.52-1.09-4.91-0.6-4.2,1.46c0.72,2.06,5.76,16.47,5.76,16.47L98.42,123.88z"/></g></g></g><path style="fill:#82AEC0;" d="M100.2,98.08c0.14,1.71-0.9,3.24-2.36,3.48c-4.85,0.77-16.44,2.24-34.54,2.24c-17.97,0-29.3-1.45-34.09-2.23c-1.48-0.24-2.51-1.8-2.35-3.53L26.84,80.9h73.38L100.2,98.08z"/><path style="fill:#546E7A;" d="M26.84,80.9l0,6.06c0,0,17.38,0.9,36.68,0.9s36.69-1.04,36.69-1.04V80.9H26.84z"/><path style="fill:#E0E0E0;" d="M63.38,84.79l0.14-24.05l-37.7-7.16L25.16,77l0,5.59c0,0.89,0.69,1.62,1.57,1.67C29.9,84.45,38.98,84.79,63.38,84.79z"/><g><path style="fill:#2167A1;" d="M96.76,8.01C91.92,6.04,82.26,4,63.53,4S35.13,6.04,30.29,8.01C28.3,8.82,27,11.96,27,14.14l-1.18,39.43l10.53,15.61l26.91,13.01c33.58,0,38.83-0.29,38.83-0.29l-2.05-67.76C100.05,11.96,98.75,8.82,96.76,8.01z"/><path style="fill:#2686C6;" d="M94.49,9.42c-4.53-1.84-13.44-3.68-30.96-3.68S37.09,7.58,32.57,9.42c-1.86,0.76-3.08,3.03-3.08,5.07l0.16,24.39c0.03,5.42,3.57,10.2,8.74,11.83l25.86,8.75l24.82-8.67c5.18-1.67,8.68-6.51,8.65-11.95l-0.16-24.25C97.56,12.55,96.35,10.18,94.49,9.42z"/></g><g><g><polygon style="fill:#BAE2FD;" points="93.51,31.48 66.25,31.48 66.61,14.81 91.48,14.81 "/><path style="fill:#37474F;" d="M91.64,12.95H67.06c-0.92,0-1.65,0.99-1.59,2.16l0.46,16.19c0.05,1.07,0.75,1.9,1.59,1.9h25.35c1.22,0,2.12-1.44,1.86-2.96l-1.55-15.7C93.03,13.61,92.38,12.95,91.64,12.95z M69.23,15.72h20.45c0.73,0,1.36,0.63,1.54,1.53l0.95,10.64c0.26,1.29-0.5,2.54-1.54,2.54H69.5c-0.83,0-1.52-0.82-1.58-1.88l-0.26-10.64C67.58,16.73,68.31,15.72,69.23,15.72z"/></g><g><polygon style="fill:#BAE2FD;" points="34.49,31.48 61.75,31.48 61.39,14.81 36.52,14.81 "/><path style="fill:#37474F;" d="M34.81,14.54l-1.55,15.7c-0.26,1.52,0.64,2.96,1.86,2.96h25.35c0.84,0,1.53-0.83,1.59-1.9l0.46-16.19c0.06-1.17-0.67-2.16-1.59-2.16H36.36C35.62,12.95,34.97,13.61,34.81,14.54z M60.35,17.91l-0.26,10.64c-0.06,1.06-0.75,1.88-1.58,1.88H37.36c-1.04,0-1.8-1.25-1.54-2.54l0.95-10.64c0.18-0.9,0.81-1.53,1.54-1.53h20.45C59.69,15.72,60.42,16.73,60.35,17.91z"/></g></g><g><g><g><g><path style="fill:#01579B;" d="M84.01,43.89c-1.15-2.57-3.12-3.54-5.19-3.03c-2.07,0.51-3.14,2.55-2.83,4.66c0.41,2.87,3.06,5.7,6.42,4.12C84.59,48.62,85.15,46.43,84.01,43.89z"/></g></g><g><g><circle style="fill:#F44336;" cx="79.73" cy="44.6" r="3.13"/></g></g></g><g><g><g><path style="fill:#01579B;" d="M43.99,43.89c1.15-2.57,3.12-3.54,5.19-3.03c2.07,0.51,3.14,2.55,2.83,4.66c-0.41,2.87-3.06,5.7-6.42,4.12C43.41,48.62,42.85,46.43,43.99,43.89z"/></g></g><g><g><circle style="fill:#F44336;" cx="48.27" cy="44.6" r="3.13"/></g></g></g></g><path style="fill:#E0E0E0;" d="M63.53,60.73l-37.7-7.16L25.16,77l0,5.59c0,0.89,0.69,1.62,1.57,1.67c3.17,0.19,12.25,0.53,36.65,0.53c0.05,0,0.09,0,0.14,0c0,0,2.15-4.36,2.15-11.7S63.53,60.73,63.53,60.73z"/><path style="fill:#BDBDBD;" d="M63.53,60.73l37.7-7.16L101.89,77l0,5.59c0,0.89-0.69,1.62-1.57,1.67c-3.17,0.19-12.25,0.53-36.65,0.53c-0.05,0-0.09,0-0.14,0V60.73z"/><path style="opacity:0.2;fill:#424242;" d="M25.16,82.59c0,0.89,0.69,1.62,1.57,1.67c3.17,0.19,12.25,0.53,36.65,0.53c0.05,0,0.09,0,0.14,0l0,0v0c0.05,0,0.09,0,0.14,0c24.4,0,33.48-0.34,36.65-0.53c0.88-0.05,1.57-0.78,1.57-1.67l0-5.54H25.16L25.16,82.59z"/><path style="fill:#94D1E0;" d="M31.7,89.75c-1.38-0.14-2.57,0.95-2.57,2.34c0,3.12,0.05,6.52,2.21,7.19c2.38,0.74,15.73,1.48,22.07,1.68c1.38,0.04,2.49-1.11,2.41-2.48l-0.3-5.1c-0.07-1.22-1.07-2.18-2.29-2.21C45.36,91.04,36.12,90.2,31.7,89.75z"/><g><g><g><g><circle style="fill:#757575;" cx="85.76" cy="66.23" r="5.88"/></g></g><g><g><circle style="fill:#FFFDE7;" cx="85.76" cy="66.82" r="4.32"/></g></g></g><g><g><g><circle style="fill:#9E9E9E;" cx="42.24" cy="66.23" r="5.88"/></g></g><g><g><circle style="fill:#FFFDE7;" cx="42.24" cy="66.82" r="4.32"/></g></g></g></g></g><g><g><g><g><polygon style="fill:#FFFFFF;" points="57.55,30.42 50.22,30.42 40.72,15.72 48.06,15.72 "/></g></g></g><g><g><g><polygon style="fill:#FFFFFF;" points="87.28,30.42 79.94,30.42 70.45,15.72 77.78,15.72 "/></g></g></g></g></svg>',
    'local_train': '<svg xmlns="http://www.w3.org/2000/svg" width="2em" height="2em" viewBox="0 0 36 36"><path fill="#939598" d="M0 34h36v2H0z"/><path fill="#58595B" d="M8 32c0-1.657-1.344-3-3-3s-3 1.343-3 3 1.343 3 3 3 3-1.343 3-3z"/><path fill="#292F33" d="M7 32c0-1.105-.896-2-2-2s-2 .895-2 2 .896 2 2 2 2-.895 2-2z"/><path fill="#58595B" d="M16 32c0-1.657-1.344-3-3-3s-3 1.343-3 3 1.343 3 3 3 3-1.343 3-3z"/><path fill="#292F33" d="M15 32c0-1.105-.896-2-2-2s-2 .895-2 2 .896 2 2 2 2-.895 2-2z"/><circle fill="#58595B" cx="32" cy="32" r="3"/><circle fill="#292F33" cx="32" cy="32" r="2"/><circle fill="#58595B" cx="24" cy="32" r="3"/><circle fill="#292F33" cx="24" cy="32" r="2"/><path fill="#5C913B" d="M0 28h36v4H0z"/><path fill="#FFE8B6" d="M0 16h36v12H0z"/><path fill="#FFAC33" d="M0 26h36v2H0z"/><path fill="#77B255" d="M32.555 14H3.445C1.969 14 .693 14.81 0 16h36c-.693-1.19-1.969-2-3.445-2z"/><path d="M5 22c0 .553-.447 1-1 1H2c-.552 0-1-.447-1-1v-2c0-.553.448-1 1-1h2c.553 0 1 .447 1 1v2zm6 0c0 .553-.447 1-1 1H8c-.552 0-1-.447-1-1v-2c0-.553.448-1 1-1h2c.553 0 1 .447 1 1v2zm6 0c0 .553-.447 1-1 1h-2c-.553 0-1-.447-1-1v-2c0-.553.447-1 1-1h2c.553 0 1 .447 1 1v2zm6 0c0 .553-.447 1-1 1h-2c-.553 0-1-.447-1-1v-2c0-.553.447-1 1-1h2c.553 0 1 .447 1 1v2zm6 0c0 .553-.447 1-1 1h-2c-.553 0-1-.447-1-1v-2c0-.553.447-1 1-1h2c.553 0 1 .447 1 1v2zm6 0c0 .553-.447 1-1 1h-2c-.553 0-1-.447-1-1v-2c0-.553.447-1 1-1h2c.553 0 1 .447 1 1v2z" fill="#55ACEE"/></svg>',
    'bus': '<svg xmlns="http://www.w3.org/2000/svg" width="2em" height="2em" viewBox="0 0 512 512"><path d="M0 0h512v512H0z" fill="none"/><path fill="#E5E4DF" d="M489.137 438.203H22.863c-8.773 0-15.885-7.112-15.885-15.885V171.522c0-23.364 18.94-42.304 42.304-42.304h355.592c55.31 0 100.147 44.838 100.147 100.147v192.952c.001 8.774-7.111 15.886-15.884 15.886"/><path fill="#6EB51C" d="M492.439 440.136H19.561c-6.949 0-12.583-5.634-12.583-12.583v-70.756h498.043v70.756c.001 6.949-5.633 12.583-12.582 12.583"/><path fill="#4D8226" d="M6.978 328.714h498.043v27.871H6.978zm55.667 111.394c0-35.752 28.983-64.736 64.736-64.736s64.736 28.983 64.736 64.736m266.684 0c0-35.752-28.983-64.736-64.736-64.736s-64.736 28.983-64.736 64.736"/><path fill="#2B3B47" d="M178.041 440.108c0 27.979-22.681 50.66-50.66 50.66s-50.66-22.681-50.66-50.66s22.681-50.66 50.66-50.66s50.66 22.682 50.66 50.66m216.024-50.66c-27.979 0-50.66 22.681-50.66 50.66s22.681 50.66 50.66 50.66s50.66-22.681 50.66-50.66s-22.681-50.66-50.66-50.66"/><path fill="#597B91" d="M158.934 440.108c0 17.427-14.127 31.554-31.554 31.554s-31.554-14.127-31.554-31.554s14.127-31.554 31.554-31.554s31.554 14.128 31.554 31.554m235.131-31.553c-17.427 0-31.554 14.127-31.554 31.554s14.127 31.554 31.554 31.554s31.554-14.127 31.554-31.554s-14.127-31.554-31.554-31.554"/><path fill="#FF473E" d="M492.51 341.702h12.512V283.71H492.51c-7.4 0-13.399 5.999-13.399 13.399v31.193c0 7.401 5.999 13.4 13.399 13.4"/><path fill="#FFD469" d="M24.16 368.813H6.978v45.271H24.16c7.4 0 13.399-5.999 13.399-13.399v-18.473c0-7.4-5.999-13.399-13.399-13.399"/><path fill="#00B1FF" d="M94.781 298.291H15.978V172.897H94.78c13.552 0 24.538 10.986 24.538 24.538v76.318c.001 13.552-10.985 24.538-24.537 24.538m116.598-54.897v-61.965a7.2 7.2 0 0 0-7.2-7.2h-49.445a7.2 7.2 0 0 0-7.2 7.2v61.965a7.2 7.2 0 0 0 7.2 7.2h49.445a7.2 7.2 0 0 0 7.2-7.2m90.266 0v-61.965a7.2 7.2 0 0 0-7.2-7.2H245a7.2 7.2 0 0 0-7.2 7.2v61.965a7.2 7.2 0 0 0 7.2 7.2h49.445a7.2 7.2 0 0 0 7.2-7.2m81.267 0v-61.965a7.2 7.2 0 0 0-7.2-7.2h-49.445a7.2 7.2 0 0 0-7.2 7.2v61.965a7.2 7.2 0 0 0 7.2 7.2h49.445a7.2 7.2 0 0 0 7.2-7.2m90.267 0v-61.965a7.2 7.2 0 0 0-7.2-7.2h-49.445a7.2 7.2 0 0 0-7.2 7.2v61.965a7.2 7.2 0 0 0 7.2 7.2h49.445a7.2 7.2 0 0 0 7.2-7.2"/></svg>',
}

def _resolve_transit_icon(obj):
    """obj: dict with boolean flags ferry/taxi/plane/walk/train/local_train -> icon SVG html (bus if none set)"""
    for key in ('ferry', 'taxi', 'plane', 'walk', 'train', 'local_train'):
        if obj.get(key):
            return TRANSIT_ICONS[key]
    return TRANSIT_ICONS['bus']



# ──────────────────────────────────────────
# テンプレートエンジン
# ──────────────────────────────────────────

def _get(path, ctx):
    """ドット記法でコンテキストから値を取得  例: "overview.difficulty_pct" """
    val = ctx
    for p in path.split('.'):
        if isinstance(val, dict):
            val = val.get(p)
        elif isinstance(val, list):
            try:
                val = val[int(p)]
            except (ValueError, IndexError):
                val = None
        else:
            val = None
        if val is None:
            return ''
    return '' if val is None else val


def _load_icon(key, ctx):
    """
    アイコンをキー名で解決する。優先順位:
    1. 素材/絵文字/<key>.svg が存在すればSVGを返す
    2. assets/icons.json にキーがあれば絵文字を返す
    3. どちらもなければキー名をそのまま返す
    """
    root_dir   = ctx.get('__root_dir__', '')
    assets_dir = os.path.join(root_dir, 'assets')

    svg_path = os.path.join(root_dir, '素材', '絵文字', f'{key}.svg')
    if os.path.exists(svg_path):
        with open(svg_path, encoding='utf-8') as f:
            return f.read().strip()

    icons_path = os.path.join(assets_dir, 'icons.json')
    if os.path.exists(icons_path):
        with open(icons_path, encoding='utf-8') as f:
            icons = json.load(f)
        if key in icons:
            return icons[key]

    return key


def _render(text, ctx):
    """テンプレートテキストをコンテキストでレンダリング"""
    result = []
    i = 0
    n = len(text)
    while i < n:
        if text[i:i+2] == '{{':
            j = text.find('}}', i + 2)
            if j == -1:
                result.append(text[i]); i += 1; continue
            expr = text[i+2:j].strip()
            if expr.startswith('icon:'):
                icon_key = expr[5:].strip()
                resolved = _get(icon_key, ctx)
                if resolved and isinstance(resolved, str):
                    icon_key = resolved
                result.append(_load_icon(icon_key, ctx))
            else:
                result.append(str(_get(expr, ctx)))
            i = j + 2

        elif text[i:i+2] == '{%':
            j = text.find('%}', i + 2)
            if j == -1:
                result.append(text[i]); i += 1; continue
            tag = text[i+2:j].strip()

            if tag.startswith('for '):
                m = re.match(r'for\s+(\w+)\s+in\s+([\w.]+)', tag)
                if not m:
                    i = j + 2; continue
                var_name  = m.group(1)
                list_path = m.group(2)
                items     = _get(list_path, ctx)
                inner, end_pos = _find_end(text, j + 2, 'for', 'endfor')
                if isinstance(items, list):
                    for item in items:
                        new_ctx = dict(ctx)
                        new_ctx[var_name] = item
                        result.append(_render(inner, new_ctx))
                i = end_pos

            elif tag.startswith('if '):
                condition = tag[3:].strip()
                then_block, else_block, end_pos = _find_if(text, j + 2)
                val = _get(condition, ctx)
                if val:
                    result.append(_render(then_block, ctx))
                elif else_block is not None:
                    result.append(_render(else_block, ctx))
                i = end_pos

            elif tag in ('endif', 'endfor', 'else'):
                i = j + 2  # 親ブロックで処理済み

            else:
                i = j + 2

        else:
            result.append(text[i])
            i += 1

    return ''.join(result)


def _find_end(text, start, open_kw, close_kw):
    """ネストを考慮して閉じタグを探す。戻り値: (内部テキスト, 終了位置)"""
    depth = 1
    i = start
    while i < len(text):
        fo = text.find('{%', i)
        if fo == -1:
            break
        fc = text.find('%}', fo + 2)
        if fc == -1:
            break
        tag = text[fo+2:fc].strip()
        if tag == open_kw or tag.startswith(open_kw + ' '):
            depth += 1
            i = fc + 2
        elif tag == close_kw or tag.startswith(close_kw + ' '):
            depth -= 1
            if depth == 0:
                return text[start:fo], fc + 2
            i = fc + 2
        else:
            i = fc + 2
    return text[start:], len(text)


def _find_if(text, start):
    """if/else/endif を探す。戻り値: (then_text, else_text|None, end_pos)"""
    depth = 1
    i = start
    else_split = None
    while i < len(text):
        fo = text.find('{%', i)
        if fo == -1:
            break
        fc = text.find('%}', fo + 2)
        if fc == -1:
            break
        tag = text[fo+2:fc].strip()
        if tag.startswith('if '):
            depth += 1
            i = fc + 2
        elif tag == 'else' and depth == 1:
            else_split = (fo, fc + 2)
            i = fc + 2
        elif tag == 'endif':
            depth -= 1
            if depth == 0:
                if else_split:
                    return text[start:else_split[0]], text[else_split[1]:fo], fc + 2
                else:
                    return text[start:fo], None, fc + 2
            i = fc + 2
        else:
            i = fc + 2
    return text[start:], None, len(text)


# ──────────────────────────────────────────
# スポットデータ（分割ページ用：どのページでもポップアップを開けるよう埋め込む）
# ──────────────────────────────────────────

def build_spot_data_js(data):
    """spot_sections から num→{name,desc,img,mapUrl} の JS オブジェクトリテラルを作る"""
    country_label = data.get('map', {}).get('country_label', '')
    obj = {}
    for sec in data.get('spot_sections', []):
        city = sec.get('city_name', '')
        for sp in sec.get('spots', []):
            num = sp.get('num', '')
            if not num:
                continue
            name = sp.get('name', '')
            desc = sp.get('desc', '')
            img  = sp.get('image', '') or ''
            if sp.get('map_url'):
                map_url = sp['map_url']
            elif sp.get('no_map'):
                map_url = ''
            else:
                q = ' '.join(x for x in [name, city, country_label] if x)
                map_url = 'https://maps.google.com/?q=' + urllib.parse.quote(q, safe='')
            obj[num] = {'num': num, 'name': name, 'desc': desc, 'img': img, 'mapUrl': map_url}
    # <script> 内に安全に埋め込めるよう '<' をエスケープ
    return json.dumps(obj, ensure_ascii=False).replace('<', '\\u003c')


# ──────────────────────────────────────────
# 国一覧 (index.html) 自動更新
# ──────────────────────────────────────────

def _esc(s):
    """JS文字列内のシングルクォートをエスケープ"""
    return str(s).replace("'", "\\'")

def update_index(country_id, data, root_dir):
    """
    index.html の COUNTRIES 配列に国カードを追加する（未登録の場合のみ）。
    JSON に index_card フィールドがない場合はスキップ。
    """
    card = data.get('index_card')
    if not card:
        return

    index_path = os.path.normpath(os.path.join(root_dir, 'index.html'))
    if not os.path.exists(index_path):
        print(f'  ⚠️  index.html が見つかりません: {index_path}')
        return

    with open(index_path, encoding='utf-8') as f:
        html = f.read()

    url = f"{country_id}/index.html"
    if f"url:'{url}'" in html:
        print(f'  ℹ️  国一覧: 登録済みのためスキップ')
        return

    # カード情報を組み立て
    name       = _esc(data.get('name', ''))
    name_en    = _esc(data.get('name_en', ''))
    flag       = _esc(card.get('flag', ''))
    catch_raw  = card.get('catch', '')
    if len(catch_raw) > 60:
        print(f'  ⚠️  index_card.catch が60文字を超えています（{len(catch_raw)}文字）。60文字に切り詰めます')
        catch_raw = catch_raw[:59] + '…'
    catch_     = _esc(catch_raw)
    region     = _esc(card.get('region', ''))
    flight     = _esc(data.get('overview', {}).get('flight_hours', ''))
    best_label = _esc(card.get('best_label', ''))
    gradient   = _esc(card.get('gradient', ''))
    card_img   = _esc(f"{country_id}/{data.get('hero_image', '')}")
    budget_str = ','.join(f"'{b}'" for b in card.get('budget', []))
    months_str = ','.join(str(m) for m in card.get('best_months', []))
    tags_str   = ','.join(f"'{_esc(t)}'" for t in card.get('tags', []))

    new_entry = (
        f"  {{\n"
        f"    name:'{name}', nameEn:'{name_en}', flag:'{flag}',\n"
        f"    catch:'{catch_}',\n"
        f"    region:'{region}', flight:'{flight}', budget:[{budget_str}],\n"
        f"    bestMonths:[{months_str}], bestLabel:'{best_label}',\n"
        f"    tags:[{tags_str}],\n"
        f"    gradient:'{gradient}',\n"
        f"    cardImg:'{card_img}',\n"
        f"    url:'{url}', available:true\n"
        f"  }},\n"
    )

    # 最初の available:false ブロックの直前に挿入
    pos = html.find('available:false')
    if pos != -1:
        block_start = html.rfind('  {', 0, pos)
        if block_start == -1:
            print('  ⚠️  挿入位置が特定できませんでした')
            return
        html = html[:block_start] + new_entry + html[block_start:]
    else:
        # unavailable エントリがない場合は COUNTRIES 配列末尾へ
        arr_start = html.find('const COUNTRIES')
        end_pos   = html.find('];', arr_start)
        if end_pos == -1:
            print('  ⚠️  COUNTRIES配列が見つかりません')
            return
        html = html[:end_pos] + new_entry + html[end_pos:]

    import shutil
    shutil.copy2(index_path, index_path + '.bak')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  📋 国一覧に追加: {name}')


# ──────────────────────────────────────────
# メイン処理
# ──────────────────────────────────────────

def generate(country_id):
    tools_dir  = os.path.dirname(os.path.abspath(__file__))  # assets/tools/
    assets_dir = os.path.join(tools_dir, '..')               # assets/
    root_dir   = os.path.join(tools_dir, '..', '..')         # World guide/

    json_path = os.path.join(root_dir, country_id, f'{country_id}.json')
    tpl_path  = os.path.join(assets_dir, 'country_template.html')
    out_path  = os.path.join(root_dir, country_id, 'index.html')

    if not os.path.exists(json_path):
        print(f'❌ JSONファイルが見つかりません: {json_path}')
        sys.exit(1)
    if not os.path.exists(tpl_path):
        print(f'❌ テンプレートが見つかりません: {tpl_path}')
        sys.exit(1)

    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    with open(tpl_path, encoding='utf-8') as f:
        tpl = f.read()

    # ── グルメ・観光スポット画像の自動検出 ──────────────────────
    # 素材/グルメ/<料理名>.webp または 素材/観光スポット/<スポット名>.webp が
    # 存在すれば image フィールドを自動補完し JSON を更新する
    json_updated = False

    food_dir = os.path.join(root_dir, country_id, '素材', 'グルメ')
    for item in data.get('food_items', []):
        name     = item.get('name', '')
        img_path = os.path.join(food_dir, f'{name}.webp')
        rel_path = f'素材/グルメ/{name}.webp'
        if os.path.exists(img_path) and item.get('image') != rel_path:
            item['image'] = rel_path
            json_updated  = True
            print(f'  🖼️  グルメ画像を自動検出: {name}.webp')

    spot_dir = os.path.join(root_dir, country_id, '素材', '観光スポット')
    for section in data.get('spot_sections', []):
        for spot in section.get('spots', []):
            name     = spot.get('name', '')
            img_path = os.path.join(spot_dir, f'{name}.webp')
            rel_path = f'素材/観光スポット/{name}.webp'
            if os.path.exists(img_path) and spot.get('image') != rel_path:
                spot['image'] = rel_path
                json_updated  = True
                print(f'  🖼️  スポット画像を自動検出: {name}.webp')

    city_img_dir = os.path.join(root_dir, country_id, '素材', '都市')
    for section in data.get('spot_sections', []):
        city_id_key = section.get('city_id', '')
        if not city_id_key:
            continue
        img_path = os.path.join(city_img_dir, f'{city_id_key}.webp')
        rel_path = f'素材/都市/{city_id_key}.webp'
        if os.path.exists(img_path) and section.get('city_image') != rel_path:
            section['city_image'] = rel_path
            json_updated = True
            print(f'  🖼️  都市画像を自動検出: {city_id_key}.webp')

    # spot_points[].spot_ref / food_ref（参照先のnum）から画像を自動解決
    # 手動でimageパスを書く代わりに spot_ref: "SAM 01" や food_ref: "No.2" と書いておけば、
    # そのスポット/料理の画像が生成され次第、自動でspot_points側にも反映される
    spots_by_num = {}
    for section in data.get('spot_sections', []):
        for spot in section.get('spots', []):
            if spot.get('num'):
                spots_by_num[spot['num']] = spot
    food_by_num = {item['num']: item for item in data.get('food_items', []) if item.get('num')}

    for pt in data.get('spot_points', []):
        ref_spot = spots_by_num.get(pt.get('spot_ref')) if pt.get('spot_ref') else None
        ref_food = food_by_num.get(pt.get('food_ref')) if pt.get('food_ref') else None
        ref = ref_spot or ref_food
        if ref and ref.get('image') and pt.get('image') != ref['image']:
            pt['image'] = ref['image']
            json_updated = True
            print(f'  🖼️  観光ポイント画像を自動解決: {pt.get("spot_ref") or pt.get("food_ref")} → {pt.get("title", "")[:20]}')

    if json_updated:
        import shutil
        shutil.copy2(json_path, json_path + '.bak')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'  💾 JSON更新: {os.path.basename(json_path)}')
    # ────────────────────────────────────────────────────────────

    # トランジット行の所要時間表示: 「区間（手段・時間）」の（の前で改行して2行にする
    # ＋ 移動アイコンSVGをPython側で解決（テンプレート内の重複if/elifチェーンを廃止）
    def _break_duration(days):
        for day in days:
            if day.get('transit'):
                dur = day.get('duration')
                if dur and '（' in dur and '<br>' not in dur:
                    day['duration'] = dur.replace('（', '<br>（', 1)
                day['_icon_svg'] = _resolve_transit_icon(day)
            pre = day.get('pre_transit')
            if pre:
                dur = pre.get('duration')
                if dur and '（' in dur and '<br>' not in dur:
                    pre['duration'] = dur.replace('（', '<br>（', 1)
                pre['_icon_svg'] = _resolve_transit_icon(pre)
            note = day.get('transport_note')
            if note:
                dur = note.get('duration')
                if dur and '（' in dur and '<br>' not in dur:
                    note['duration'] = dur.replace('（', '<br>（', 1)
                note['_icon_svg'] = _resolve_transit_icon(note)
    for _plan in data.get('courses', {}).get('stable_plans', []):
        _break_duration(_plan.get('days', []))
    _break_duration(data.get('courses', {}).get('adventure_plan', {}).get('days', []))

    data['__root_dir__'] = os.path.normpath(root_dir)

    country_dir = os.path.join(root_dir, country_id)
    os.makedirs(os.path.join(country_dir, '素材', 'グルメ'),       exist_ok=True)
    os.makedirs(os.path.join(country_dir, '素材', '観光スポット'), exist_ok=True)
    os.makedirs(os.path.join(country_dir, '素材', '都市'),         exist_ok=True)
    os.makedirs(os.path.join(country_dir, 'audio'),                exist_ok=True)

    SECTIONS = ['basic', 'spots', 'food', 'course', 'budget', 'practical', 'phrases']

    if data.get('multipage'):
        # ── 分割ページモード（タブごとに個別HTML） ──
        pages = [
            ('basic',     'index.html',     '基本情報'),
            ('spots',     'spots.html',     '観光スポット'),
            ('food',      'food.html',      'グルメ'),
            ('course',    'course.html',    'モデルコース'),
            ('budget',    'budget.html',    '予算・費用'),
            ('practical', 'practical.html', '旅の準備'),
            ('phrases',   'phrases.html',   'フレーズ'),
        ]
        base_title    = data.get('page_title', '')
        name          = data.get('name', '')
        spot_data_js  = build_spot_data_js(data)
        page_order_js = json.dumps([p[1] for p in pages])
        for idx, (slug, outfile, label) in enumerate(pages):
            ctx = dict(data)
            ctx['multipage']       = True
            ctx['singlepage']      = False
            ctx['spot_data_js']    = spot_data_js
            ctx['page_order_js']   = page_order_js
            ctx['page_index']      = idx
            ctx['show']            = {s: (s == slug) for s in SECTIONS}
            ctx['nav_active']      = {s: ('active' if s == slug else '') for s in SECTIONS}
            ctx['sec_active']      = {s: ('active' if s == slug else '') for s in SECTIONS}
            ctx['needs_gmaps']     = slug in ('basic', 'budget')
            ctx['container_style'] = 'max-width:1000px' if slug in ('spots', 'food') else ''
            ctx['page_title']      = base_title if slug == 'basic' else f'{name}の{label}｜{base_title}'
            html = _render(tpl, ctx)
            with open(os.path.join(country_dir, outfile), 'w', encoding='utf-8') as f:
                f.write(html)
            print(f'  📄 {outfile}')
        print(f'✅ 生成完了（分割{len(pages)}ページ）: {country_dir}')
    else:
        # ── 従来モード（1枚のindex.htmlに全タブ） ──
        ctx = dict(data)
        ctx['multipage']       = False
        ctx['singlepage']      = True
        ctx['show']            = {s: True for s in SECTIONS}
        ctx['nav_active']      = {s: ('active' if s == 'basic' else '') for s in SECTIONS}
        ctx['sec_active']      = {s: ('active' if s == 'basic' else '') for s in SECTIONS}
        ctx['needs_gmaps']     = True
        ctx['container_style'] = ''
        html = _render(tpl, ctx)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'✅ 生成完了: {out_path}')

    update_index(country_id, data, root_dir)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('使い方: python generate.py <country_id>')
        print('例:     python generate.py thailand')
        sys.exit(1)
    generate(sys.argv[1])
