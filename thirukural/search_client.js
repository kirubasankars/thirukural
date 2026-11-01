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

  function englishGroups(query, english) {
    if (/[\u0b80-\u0bff]/.test(query)) return null;
    const words = englishWords(query);
    if (!words.length) return [];
    const groups = [];
    let index = 0;
    while (index < words.length) {
      let matched = false;
      for (let length = 3; length >= 1; length--) {
        if (index + length > words.length) continue;
        const phrase = words.slice(index, index + length).join(" ");
        const terms = english[phrase];
        if (terms && terms.length) {
          groups.push(terms);
          index += length;
          matched = true;
          break;
        }
      }
      if (!matched) return [];
    }
    return groups;
  }

  function createSearch(suffixes, english) {
    const gloss = english || {};
    const weight = { குறள்: 100, விளக்கம்: 10, அதிகாரம்: 1 };

    function fieldsOf(item) {
      return [
        ["குறள்", normalize(item.kural)],
        ["விளக்கம்", normalize(item.note)],
        ["அதிகாரம்", normalize(item.title)],
      ];
    }

    function scorePhrase(fields, phrase) {
      const tokens = normalize(phrase).split(" ").filter(function (token) {
        return token.length >= 2;
      });
      if (!tokens.length) return null;
      const forms = tokens.map(function (token) {
        return tokenForms(token, suffixes);
      });
      let score = 0;
      let where = null;
      for (let t = 0; t < tokens.length; t++) {
        let best = 0;
        let bestWhere = null;
        for (let f = 0; f < fields.length; f++) {
          const label = fields[f][0];
          const text = fields[f][1];
          let matched = 0;
          if (text.indexOf(tokens[t]) !== -1) matched = weight[label] * 10 + 5;
          else if (forms[t].some(function (form) {
            return form !== tokens[t] && text.indexOf(form) !== -1;
          })) matched = weight[label] * 10;
          if (matched > best) {
            best = matched;
            bestWhere = label;
          }
        }
        if (!best) return null;
        score += best;
        if (!where || weight[bestWhere] > weight[where]) where = bestWhere;
      }
      return where ? { score: score, where: where } : null;
    }

    function scoreGroups(fields, groups) {
      let score = 0;
      let where = null;
      for (let g = 0; g < groups.length; g++) {
        const alternatives = groups[g];
        let best = 0;
        let bestWhere = null;
        for (let i = 0; i < alternatives.length; i++) {
          const scored = scorePhrase(fields, alternatives[i]);
          if (!scored) continue;
          const ranked = scored.score + (alternatives.length - i);
          if (ranked > best) {
            best = ranked;
            bestWhere = scored.where;
          }
        }
        if (!bestWhere) return null;
        score += best;
        if (!where || weight[bestWhere] > weight[where]) where = bestWhere;
      }
      return where ? { score: score, where: where } : null;
    }

    function search(index, query, limit) {
      const groups = englishGroups(query, gloss);
      if (groups && !groups.length) return [];
      const hits = [];
      index.forEach(function (item) {
        const fields = fieldsOf(item);
        const scored = groups ? scoreGroups(fields, groups) : scorePhrase(fields, query);
        if (!scored) return;
        hits.push({
          n: item.n,
          h: item.h,
          v: item.v,
          title: item.title,
          kural: item.kural,
          note: item.note,
          where: scored.where,
          score: scored.score,
        });
      });
      hits.sort(function (a, b) {
        return b.score - a.score || a.n - b.n;
      });
      return typeof limit === "number" ? hits.slice(0, limit) : hits;
    }

    return { normalize: normalize, tokenForms: tokenForms, search: search, englishGroups: function (query) {
      return englishGroups(query, gloss);
    } };
  }

  return { createSearch: createSearch };
});
