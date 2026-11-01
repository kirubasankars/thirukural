/* Search used by the slide deck. The same suffix list is supplied by Python. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.KuralSearch = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function normalize(value) {
    return String(value || "")
      .normalize("NFC")
      .replace(/[\u200c\u200d]/g, "")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function openConsonant(form) {
    if (form.endsWith("\u0bcd") && form.length - 1 >= 3) return form.slice(0, -1);
    return "";
  }

  function tokenForms(token, suffixes) {
    const forms = [];
    function add(form) {
      if (form && forms.indexOf(form) === -1) forms.push(form);
    }
    add(token);
    add(openConsonant(token));
    for (let i = 0; i < suffixes.length; i++) {
      const suffix = suffixes[i];
      if (token.endsWith(suffix) && token.length - suffix.length >= 3) {
        const stem = token.slice(0, token.length - suffix.length);
        add(stem);
        add(openConsonant(stem));
        let bare = "";
        if (stem.endsWith("ய்") && stem.length - 2 >= 3) bare = stem.slice(0, -2);
        else if (stem.endsWith("ய") && stem.length - 1 >= 3) bare = stem.slice(0, -1);
        add(bare);
        if (bare) add(openConsonant(bare));
        break;
      }
    }
    return forms;
  }

  const STOP = {
    a: 1, an: 1, the: 1, of: 1, and: 1, or: 1, to: 1, for: 1, in: 1, on: 1, with: 1, from: 1, by: 1,
  };
  const RANK = {
    "குறள்:whole": 640,
    "குறள்:boundary": 560,
    "குறள்:stem": 480,
    "விளக்கம்:whole": 320,
    "விளக்கம்:boundary": 240,
    "விளக்கம்:stem": 160,
    "அதிகாரம்:whole": 80,
    "அதிகாரம்:boundary": 60,
    "அதிகாரம்:stem": 40,
    "குறள்:buried": 30,
    "விளக்கம்:buried": 20,
    "அதிகாரம்:buried": 10,
  };
  const FIELD_WEIGHT = { குறள்: 100, விளக்கம்: 10, அதிகாரம்: 1 };
  const THEME = 10000;
  const CONSONANTS = {
    "க": "k", "ங": "ng", "ச": "c", "ஞ": "nj", "ட": "t", "ண": "n", "த": "t", "ந": "n",
    "ப": "p", "ம": "m", "ய": "y", "ர": "r", "ல": "l", "வ": "v", "ழ": "l", "ள": "l",
    "ற": "r", "ன": "n", "ஜ": "j", "ஷ": "c", "ஸ": "c", "ஹ": "h",
  };
  const VOWEL_SIGNS = {
    "ா": "a", "ி": "i", "ீ": "i", "ு": "u", "ூ": "u", "ெ": "e", "ே": "e", "ை": "e",
    "ொ": "o", "ோ": "o", "ௌ": "o",
  };
  const INDEPENDENT = {
    "அ": "a", "ஆ": "a", "இ": "i", "ஈ": "i", "உ": "u", "ஊ": "u", "எ": "e", "ஏ": "e",
    "ஐ": "e", "ஒ": "o", "ஓ": "o", "ஔ": "o",
  };
  const LATIN = [
    ["zh", "l"], ["th", "t"], ["dh", "t"], ["aa", "a"], ["ee", "i"], ["ii", "i"],
    ["oo", "u"], ["uu", "u"], ["ai", "e"], ["au", "o"], ["ch", "c"], ["sh", "c"],
    ["ng", "ng"], ["nj", "nj"], ["ny", "nj"],
  ];
  const LATIN_SINGLE = {
    a: "a", e: "e", i: "i", o: "o", u: "u", k: "k", g: "k", s: "c", c: "c", t: "t", d: "t",
    n: "n", m: "m", y: "y", r: "r", l: "l", v: "v", w: "v", p: "p", b: "p", z: "l", j: "j", f: "p", h: "",
  };
  const VOWELS = { a: 1, e: 1, i: 1, o: 1, u: 1 };

  function englishWords(query) {
    const folded = String(query || "").toLowerCase().replace(/[\u2018\u2019]/g, "'");
    const cleaned = folded.replace(/[^a-z']+/g, " ").trim();
    if (!cleaned) return [];
    return cleaned.split(/\s+/).map(function (word) {
      return word.replace(/^'+|'+$/g, "");
    }).filter(function (word) {
      return word.length >= 2 && !STOP[word];
    });
  }

  function stemOf(word) {
    const suffixes = ["ing", "es", "ed", "s"];
    for (let i = 0; i < suffixes.length; i++) {
      const suffix = suffixes[i];
      if (suffix === "s" && word.endsWith("ss")) return "";
      if (word.endsWith(suffix) && word.length - suffix.length >= 3) {
        return word.slice(0, word.length - suffix.length);
      }
    }
    return "";
  }

  function oneEdit(left, right) {
    if (left === right || Math.abs(left.length - right.length) > 1) return false;
    let i = 0;
    let j = 0;
    let edits = 0;
    while (i < left.length && j < right.length) {
      if (left.charAt(i) === right.charAt(j)) {
        i += 1;
        j += 1;
        continue;
      }
      edits += 1;
      if (edits > 1) return false;
      if (left.length === right.length) {
        i += 1;
        j += 1;
      } else if (left.length > right.length) i += 1;
      else j += 1;
    }
    edits += (left.length - i) + (right.length - j);
    return edits === 1;
  }

  function glossaryWords(english) {
    const words = [];
    Object.keys(english).forEach(function (phrase) {
      phrase.split(" ").forEach(function (word) {
        if (words.indexOf(word) === -1) words.push(word);
      });
    });
    return words;
  }

  function candidates(word, english, knownWords) {
    const forms = [word];
    const stem = stemOf(word);
    if (stem && forms.indexOf(stem) === -1) forms.push(stem);
    const known = forms.filter(function (form) {
      return knownWords.indexOf(form) !== -1;
    });
    if (known.length) return known;
    for (let i = 0; i < forms.length; i++) {
      if (forms[i].length < 5) continue;
      const hits = knownWords.filter(function (key) {
        return Math.abs(key.length - forms[i].length) <= 1 && oneEdit(forms[i], key);
      });
      if (hits.length === 1) return [hits[0]];
    }
    return forms;
  }

  function product(lists) {
    let combos = [[]];
    lists.forEach(function (list) {
      const next = [];
      combos.forEach(function (combo) {
        list.forEach(function (item) {
          next.push(combo.concat([item]));
        });
      });
      combos = next;
    });
    return combos;
  }

  function knownPhrase(slice, english, knownWords) {
    const original = slice.join(" ");
    if (english[original]) return original;
    const choices = slice.map(function (word) {
      return candidates(word, english, knownWords);
    });
    const found = [];
    product(choices).forEach(function (combo) {
      const phrase = combo.join(" ");
      if (english[phrase] && found.indexOf(phrase) === -1) found.push(phrase);
    });
    return found.length ? found[0] : "";
  }

  function latinPlan(query, english) {
    if (/[\u0b80-\u0bff]/.test(query)) return null;
    const words = englishWords(query);
    const knownWords = glossaryWords(english);
    const groups = [];
    const pending = [];
    let index = 0;
    while (index < words.length) {
      let matched = 0;
      for (let length = 3; length >= 1; length--) {
        if (index + length > words.length) continue;
        const phrase = knownPhrase(words.slice(index, index + length), english, knownWords);
        if (!phrase) continue;
        groups.push(english[phrase]);
        matched = length;
        break;
      }
      if (matched) {
        index += matched;
        continue;
      }
      pending.push(words[index]);
      index += 1;
    }
    return { groups: groups, pending: pending };
  }

  function englishGroups(query, english) {
    const plan = latinPlan(query, english || {});
    if (!plan) return null;
    return plan.groups;
  }

  function loose(parts) {
    const folded = [];
    for (let i = 0; i < parts.length; i++) {
      if (
        parts[i] === "a" &&
        folded.length &&
        !VOWELS[folded[folded.length - 1]] &&
        i + 1 < parts.length &&
        !VOWELS[parts[i + 1]]
      ) continue;
      folded.push(parts[i]);
    }
    return folded;
  }

  function same(left, right) {
    if (left.length !== right.length) return false;
    for (let i = 0; i < left.length; i++) if (left[i] !== right[i]) return false;
    return true;
  }

  function starts(whole, prefix) {
    if (prefix.length > whole.length) return false;
    for (let i = 0; i < prefix.length; i++) if (whole[i] !== prefix[i]) return false;
    return true;
  }

  function tamilPhonemes(text) {
    const parts = [];
    let index = 0;
    while (index < text.length) {
      const char = text.charAt(index);
      if (INDEPENDENT[char]) {
        parts.push(INDEPENDENT[char]);
        index += 1;
        continue;
      }
      if (CONSONANTS[char]) {
        parts.push(CONSONANTS[char]);
        index += 1;
        if (text.charAt(index) === "\u0bcd") index += 1;
        else if (VOWEL_SIGNS[text.charAt(index)]) {
          parts.push(VOWEL_SIGNS[text.charAt(index)]);
          index += 1;
        } else parts.push("a");
        continue;
      }
      index += 1;
    }
    return parts;
  }

  function latinPhonemes(text) {
    const folded = String(text || "").toLowerCase();
    const parts = [];
    let index = 0;
    while (index < folded.length) {
      let matched = false;
      for (let i = 0; i < LATIN.length; i++) {
        const digraph = LATIN[i][0];
        if (folded.slice(index, index + digraph.length) === digraph) {
          parts.push(LATIN[i][1]);
          index += digraph.length;
          matched = true;
          break;
        }
      }
      if (matched) continue;
      const phoneme = LATIN_SINGLE[folded.charAt(index)];
      if (phoneme === undefined) return null;
      if (phoneme) parts.push(phoneme);
      index += 1;
    }
    return parts;
  }

  function phonemesOf(text) {
    if (/[\u0b80-\u0bff]/.test(text)) return tamilPhonemes(text);
    return latinPhonemes(text);
  }

  function matchKind(query, word) {
    if (!query || !query.length || !word || !word.length) return "";
    const queryLoose = loose(query);
    const wordLoose = loose(word);
    if (same(query, word) || same(queryLoose, wordLoose)) return "whole";
    if (keyExtends(word, query)) return "boundary";
    if (keyExtends(wordLoose, queryLoose)) return "stem";
    return "";
  }

  function keyExtends(longer, shorter) {
    const extra = longer.length - shorter.length;
    return shorter.length >= 4 && extra > 0 && extra <= 4 && starts(longer, shorter);
  }

  const TRAILING = ".,;:!?\"'“”‘’()[]{}…。·";

  function cleanWord(word) {
    let start = 0;
    let end = word.length;
    while (start < end && TRAILING.indexOf(word.charAt(start)) !== -1) start += 1;
    while (end > start && TRAILING.indexOf(word.charAt(end - 1)) !== -1) end -= 1;
    return word.slice(start, end);
  }

  function wordsOf(text) {
    return normalize(text).split(" ").map(cleanWord).filter(function (word) {
      return word.length >= 2;
    });
  }

  function aksharas(text) {
    let count = 0;
    for (let i = 0; i < text.length; i++) {
      const char = text.charAt(i);
      if (char !== "\u0bcd" && !VOWEL_SIGNS[char]) count += 1;
    }
    return count;
  }

  function kindOf(form, word, exact) {
    if (form.length < 2 || word.length < 2) return "";
    if (word === form) return exact ? "whole" : "stem";
    const letters = aksharas(form);
    if (word.startsWith(form) && letters >= 2 && form.length >= 3) {
      return exact ? "boundary" : "stem";
    }
    if (word.endsWith(form) && letters >= 4) return exact ? "boundary" : "stem";
    if (exact && letters >= 4 && word.indexOf(form) !== -1) return "buried";
    return "";
  }

  function createSearch(suffixes, english) {
    const gloss = english || {};

    function fieldsOf(item) {
      return [
        ["குறள்", normalize(item.kural)],
        ["விளக்கம்", normalize(item.note)],
        ["அதிகாரம்", normalize(item.title)],
      ];
    }

    function theme(tokens, title) {
      if (tokens.length < 2) return false;
      const titleWords = wordsOf(title);
      return tokens.every(function (token) {
        const forms = tokenForms(token, suffixes);
        return titleWords.some(function (word) { return forms.indexOf(word) !== -1; });
      });
    }

    function scorePhrase(fields, phrase) {
      const tokens = normalize(phrase).split(" ").filter(function (token) {
        return token.length >= 2;
      });
      if (!tokens.length) return null;
      let score = 0;
      let where = null;
      let bestRank = -1;
      let term = tokens[0];
      for (let t = 0; t < tokens.length; t++) {
        const forms = tokenForms(tokens[t], suffixes);
        let best = 0;
        let bestWhere = null;
        let bestTerm = tokens[t];
        for (let f = 0; f < fields.length; f++) {
          const label = fields[f][0];
          const textWords = wordsOf(fields[f][1]);
          for (let w = 0; w < textWords.length; w++) {
            for (let formIndex = 0; formIndex < forms.length; formIndex++) {
              const form = forms[formIndex];
              const kind = kindOf(form, textWords[w], form === tokens[t]);
              if (!kind) continue;
              const rank = RANK[label + ":" + kind];
              if (rank > best) {
                best = rank;
                bestWhere = label;
                bestTerm = kind === "whole" ? textWords[w] : form;
              }
            }
          }
        }
        if (!bestWhere) return null;
        score += best;
        if (best > bestRank) {
          bestRank = best;
          where = bestWhere;
          term = bestTerm;
        }
      }
      const title = fields[2][1];
      if (theme(tokens, title)) score += THEME;
      return where ? { score: score, where: where, term: term } : null;
    }

    function scoreGroups(fields, groups) {
      let score = 0;
      let where = null;
      let term = "";
      let bestWeight = -1;
      for (let g = 0; g < groups.length; g++) {
        const alternatives = groups[g];
        let best = 0;
        let bestScored = null;
        for (let i = 0; i < alternatives.length; i++) {
          const scored = scorePhrase(fields, alternatives[i]);
          if (!scored) continue;
          const ranked = scored.score + (alternatives.length - i);
          if (ranked > best) {
            best = ranked;
            bestScored = scored;
          }
        }
        if (!bestScored) return null;
        score += best;
        const weight = FIELD_WEIGHT[bestScored.where];
        if (weight > bestWeight) {
          bestWeight = weight;
          where = bestScored.where;
          term = bestScored.term;
        }
      }
      return where ? { score: score, where: where, term: term } : null;
    }

    function scoreRoman(fields, query) {
      let best = 0;
      let where = null;
      let term = "";
      for (let f = 0; f < fields.length; f++) {
        const label = fields[f][0];
        const textWords = wordsOf(fields[f][1]);
        for (let w = 0; w < textWords.length; w++) {
          const wordKey = phonemesOf(textWords[w]);
          if (!wordKey) continue;
          const kind = matchKind(query, wordKey);
          if (!kind) continue;
          const rank = RANK[label + ":" + kind];
          if (rank > best) {
            best = rank;
            where = label;
            term = textWords[w];
          }
        }
      }
      return where ? { score: best, where: where, term: term } : null;
    }

    function activeRoman(index, pending) {
      const active = [];
      pending.forEach(function (word) {
        const key = phonemesOf(word);
        if (!key || !key.length) return;
        const found = index.some(function (item) {
          return scoreRoman(fieldsOf(item), key);
        });
        if (found) active.push(key);
      });
      return active;
    }

    function scoreQuery(fields, query, plan, roman) {
      if (!plan) return scorePhrase(fields, query);
      const scored = plan.groups.length ? scoreGroups(fields, plan.groups) : null;
      if (plan.groups.length && !scored) return null;
      let score = scored ? scored.score : 0;
      let where = scored ? scored.where : null;
      let term = scored ? scored.term : "";
      let best = scored ? FIELD_WEIGHT[scored.where] : 0;
      for (let i = 0; i < roman.length; i++) {
        const romanScored = scoreRoman(fields, roman[i]);
        if (!romanScored) return null;
        score += romanScored.score;
        const weight = FIELD_WEIGHT[romanScored.where];
        if (weight > best) {
          best = weight;
          where = romanScored.where;
          term = romanScored.term;
        }
      }
      return where ? { score: score, where: where, term: term } : null;
    }

    function search(index, query, limit) {
      const trimmed = String(query || "").trim();
      if (/^\d+$/.test(trimmed)) {
        const number = parseInt(trimmed, 10);
        if (number >= 1 && number <= 1330) {
          return index.filter(function (item) { return item.n === number; }).map(function (item) {
            return {
              n: item.n, h: item.h, v: item.v, title: item.title, kural: item.kural,
              note: item.note, where: "குறள்", term: String(item.n), score: 1,
            };
          }).slice(0, typeof limit === "number" ? limit : undefined);
        }
      }
      const plan = latinPlan(query, gloss);
      let roman = [];
      if (plan) {
        if (!plan.groups.length && !plan.pending.length) return [];
        roman = activeRoman(index, plan.pending);
        if (!plan.groups.length && !roman.length) return [];
      }
      const hits = [];
      index.forEach(function (item) {
        const scored = scoreQuery(fieldsOf(item), query, plan, roman);
        if (!scored) return;
        hits.push({
          n: item.n,
          h: item.h,
          v: item.v,
          title: item.title,
          kural: item.kural,
          note: item.note,
          where: scored.where,
          term: scored.term,
          score: scored.score,
        });
      });
      hits.sort(function (a, b) {
        return b.score - a.score || a.n - b.n;
      });
      return typeof limit === "number" ? hits.slice(0, limit) : hits;
    }

    return {
      normalize: normalize,
      tokenForms: tokenForms,
      search: search,
      englishGroups: function (query) {
        return englishGroups(query, gloss);
      },
    };
  }

  return { createSearch: createSearch };
});
