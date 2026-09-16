/** on'yomi is conventionally set in katakana; KANJIDIC stores every reading as hiragana. */
export const katakana = (s) =>
  s.replace(/[ぁ-ゖ]/g, (c) => String.fromCharCode(c.charCodeAt(0) + 0x60));

/** "かた.る" is a stem plus okurigana; KANJIDIC also uses a leading hyphen for a
 *  suffix-only reading (-がね) and a trailing one for a prefix-only reading (かざ-).
 *  Print all three the way a dictionary would. */
export const okurigana = (s) =>
  s
    .replace(/^-/, "〜")
    .replace(/-$/, "〜")
    .replace(/\.(.+)$/, "（$1）");

/** The card back groups its words by which reading each one uses. `irr` is the bucket for
 *  jukujikun and ateji, where the compound's reading can't be derived from its characters. */
export const READING_GROUPS = [
  { key: "on", label: "音読み" },
  { key: "kun", label: "訓読み" },
  { key: "irr", label: "特別な読み" },
];
