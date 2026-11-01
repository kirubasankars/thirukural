"""English words that point at Tamil words in the verses.

Each value is a set of alternatives. A verse matches an alternative when
every word in that alternative occurs. Alternatives are combined with or.
"""

import itertools
from dataclasses import dataclass

ENGLISH: dict[str, tuple[str, ...]] = {
    "god": ("கடவுள்",),
    "deity": ("கடவுள்",),
    "praise of god": ("கடவுள்",),
    "rain": ("மழை", "வான்"),
    "cloud": ("மழை",),
    "sky": ("வான்", "விசும்பு"),
    "water": ("நீர்",),
    "ascetic": ("துறவு", "நீத்தார்"),
    "renunciation": ("துறவு",),
    "renounce": ("துறவு",),
    "virtue": ("அறம்", "அறன்"),
    "dharma": ("அறம்",),
    "righteous": ("அறம்", "செங்கோல்"),
    "household": ("இல்வாழ்க்கை",),
    "domestic": ("இல்வாழ்க்கை",),
    "home": ("இல்வாழ்க்கை",),
    "family": ("இல்வாழ்க்கை", "குடி"),
    "wife": ("துணை", "மனைவி"),
    "spouse": ("துணை",),
    "husband": ("கொழுநன்",),
    "children": ("மக்கள்", "பிள்ளை"),
    "child": ("பிள்ளை", "மக்கள்"),
    "son": ("மக்கள்", "பிள்ளை"),
    "love": ("அன்பு", "காதல்"),
    "affection": ("அன்பு",),
    "hospitality": ("விருந்து",),
    "guest": ("விருந்து",),
    "kind words": ("இனிய",),
    "pleasant speech": ("இனிய",),
    "speech": ("சொல்", "இனிய"),
    "gratitude": ("நன்றி",),
    "thanks": ("நன்றி",),
    "thankful": ("நன்றி",),
    "impartial": ("நடுவு",),
    "equity": ("நடுவு",),
    "justice": ("நடுவு", "செங்கோல்"),
    "self control": ("அடக்கம்",),
    "restraint": ("அடக்கம்",),
    "conduct": ("ஒழுக்கம்",),
    "decorum": ("ஒழுக்கம்",),
    "propriety": ("ஒழுக்கம்",),
    "adultery": ("பிறன்",),
    "patience": ("பொறை",),
    "forbearance": ("பொறை",),
    "envy": ("அழுக்காறு",),
    "jealousy": ("அழுக்காறு",),
    "greed": ("அவா",),
    "covet": ("வெஃகாமை", "அவா"),
    "slander": ("புறங்கூற",),
    "gossip": ("புறங்கூற", "அலர்"),
    "backbiting": ("புறங்கூற",),
    "vain speech": ("பயனில",),
    "useless talk": ("பயனில",),
    "evil": ("தீவினை", "தீமை"),
    "sin": ("தீவினை",),
    "duty": ("ஒப்புரவு",),
    "benevolence": ("ஒப்புரவு",),
    "society": ("ஒப்புரவு",),
    "giving": ("ஈகை",),
    "gift": ("ஈகை",),
    "charity": ("ஈகை",),
    "liberality": ("ஈகை",),
    "fame": ("புகழ்",),
    "glory": ("புகழ்",),
    "renown": ("புகழ்",),
    "compassion": ("அருள்",),
    "mercy": ("அருள்",),
    "grace": ("அருள்",),
    "meat": ("புலால்",),
    "vegetarian": ("புலால்",),
    "penance": ("தவம்",),
    "austerity": ("தவம்",),
    "hypocrisy": ("கூடா ஒழுக்கம்",),
    "theft": ("களவு", "கள்ளாமை"),
    "stealing": ("களவு",),
    "steal": ("களவு",),
    "truth": ("வாய்மை", "மெய்"),
    "truthful": ("வாய்மை",),
    "lie": ("பொய்",),
    "falsehood": ("பொய்",),
    "anger": ("வெகுளி",),
    "wrath": ("வெகுளி",),
    "harm": ("இன்னா",),
    "injury": ("இன்னா",),
    "killing": ("கொலை",),
    "murder": ("கொலை",),
    "nonviolence": ("கொல்லாமை",),
    "impermanence": ("நிலையாமை",),
    "transient": ("நிலையாமை",),
    "reality": ("மெய்",),
    "desire": ("அவா",),
    "lust": ("அவா", "காமம்"),
    "fate": ("ஊழ்",),
    "destiny": ("ஊழ்",),
    "king": ("மன்னன்", "வேந்து"),
    "ruler": ("மன்னன்", "வேந்து"),
    "monarch": ("மன்னன்",),
    "learning": ("கல்வி",),
    "education": ("கல்வி",),
    "study": ("கல்வி",),
    "knowledge": ("கல்வி", "அறிவு"),
    "ignorance": ("கல்லாமை", "பேதை"),
    "listening": ("கேள்வி",),
    "wisdom": ("அறிவு",),
    "intelligence": ("அறிவு",),
    "fault": ("குற்றம்",),
    "faults": ("குற்றம்",),
    "great men": ("பெரியார்",),
    "bad company": ("சிற்றினம்",),
    "company": ("இனம்",),
    "deliberation": ("தெரிந்து",),
    "strength": ("வலி",),
    "power": ("வலி",),
    "time": ("காலம்",),
    "timing": ("காலம்",),
    "place": ("இடன்",),
    "opportunity": ("இடன்",),
    "minister": ("அமைச்சு",),
    "ministry": ("அமைச்சு",),
    "kin": ("சுற்றம்",),
    "relatives": ("சுற்றம்",),
    "vigilance": ("பொச்சாவாமை",),
    "forgetfulness": ("பொச்சாவாமை",),
    "tyranny": ("கொடுங்கோன்",),
    "tyrant": ("கொடுங்கோன்",),
    "cruelty": ("வெருவந்த",),
    "cruel": ("வெருவந்த",),
    "kindness": ("கண்ணோட்டம்", "அருள்"),
    "spy": ("ஒற்று",),
    "spies": ("ஒற்று",),
    "energy": ("ஊக்கம்",),
    "enthusiasm": ("ஊக்கம்",),
    "effort": ("ஊக்கம்", "முயற்சி"),
    "lazy": ("மடி",),
    "laziness": ("மடி",),
    "idleness": ("மடி",),
    "perseverance": ("ஆள்வினை",),
    "industry": ("ஆள்வினை",),
    "trouble": ("இடுக்கண்",),
    "adversity": ("இடுக்கண்",),
    "sorrow": ("துன்பம்", "இடுக்கண்"),
    "eloquence": ("சொல்வன்மை",),
    "purity": ("தூய்மை",),
    "firmness": ("திட்பம்",),
    "determination": ("திட்பம்",),
    "action": ("வினை",),
    "deed": ("வினை",),
    "envoy": ("தூது",),
    "ambassador": ("தூது",),
    "embassy": ("தூது",),
    "assembly": ("அவை",),
    "council": ("அவை",),
    "courage": ("அஞ்சாமை", "படைச்செருக்கு"),
    "fear": ("அச்சம்", "அஞ்சு"),
    "country": ("நாடு",),
    "nation": ("நாடு",),
    "land": ("நாடு",),
    "fort": ("அரண்",),
    "fortress": ("அரண்",),
    "wealth": ("பொருள்", "செல்வம்"),
    "money": ("பொருள்", "செல்வம்"),
    "riches": ("செல்வம்",),
    "army": ("படை",),
    "soldier": ("படை",),
    "war": ("போர்", "படை"),
    "friendship": ("நட்பு",),
    "friend": ("நட்பு",),
    "false friendship": ("கூடா நட்பு",),
    "evil friendship": ("தீ நட்பு",),
    "bad friend": ("தீ நட்பு",),
    "familiarity": ("பழைமை",),
    "intimacy": ("பழைமை",),
    "folly": ("பேதை",),
    "fool": ("பேதை",),
    "hatred": ("இகல்", "பகை"),
    "hostility": ("இகல்",),
    "enemy": ("பகை",),
    "enmity": ("பகை",),
    "woman": ("பெண்",),
    "women": ("பெண்",),
    "liquor": ("கள் உண்",),
    "wine": ("கள் உண்",),
    "alcohol": ("கள் உண்",),
    "toddy": ("கள் உண்",),
    "drinking": ("கள் உண்",),
    "gambling": ("சூது",),
    "gamble": ("சூது",),
    "medicine": ("மருந்து",),
    "disease": ("நோய்",),
    "illness": ("நோய்",),
    "health": ("மருந்து",),
    "nobility": ("குடிமை",),
    "lineage": ("குடி",),
    "honour": ("மானம்",),
    "honor": ("மானம்",),
    "dignity": ("மானம்",),
    "self respect": ("மானம்",),
    "greatness": ("பெருமை",),
    "courtesy": ("பண்பு",),
    "manners": ("பண்பு",),
    "modesty": ("நாண்",),
    "shame": ("நாண்",),
    "farming": ("உழவு",),
    "agriculture": ("உழவு",),
    "farmer": ("உழவன்", "உழவு"),
    "plough": ("உழவு",),
    "poverty": ("நல்குரவு", "வறுமை"),
    "poor": ("நல்குரவு", "வறுமை"),
    "begging": ("இரத்தல்", "இரப்பு"),
    "mendicant": ("இரத்தல்",),
    "baseness": ("கயமை",),
    "meanness": ("கயமை",),
    "beauty": ("அழகு", "நலம்"),
    "union": ("புணர்ச்சி",),
    "embrace": ("புணர்ச்சி", "முயக்கம்"),
    "romance": ("காதல்",),
    "lover": ("காதல்",),
    "rumour": ("அலர்",),
    "rumor": ("அலர்",),
    "separation": ("பிரிவு",),
    "parting": ("பிரிவு",),
    "pining": ("படர்",),
    "weeping": ("கலுழ்", "அழுத", "கண்ணீர்"),
    "tears": ("கண்ணீர்",),
    "eyes": ("கண்",),
    "eye": ("கண்",),
    "pallor": ("பசப்பு",),
    "lonely": ("தனி",),
    "loneliness": ("தனி",),
    "memory": ("நினைவு",),
    "remember": ("நினைவு",),
    "dream": ("கனவு",),
    "evening": ("பொழுது",),
    "sunset": ("பொழுது",),
    "heart": ("நெஞ்சு",),
    "sulking": ("புலவி", "ஊடல்"),
    "lovers quarrel": ("ஊடல்", "புலவி"),
    "quarrel": ("ஊடல்",),
    "death": ("சாதல்", "இறப்பு"),
    "life": ("வாழ்க்கை", "உயிர்"),
    "birth": ("பிறப்பு",),
    "world": ("உலகம்",),
    "earth": ("நிலம்", "உலகம்"),
    "food": ("உணவு",),
    "hunger": ("பசி",),
    "rice": ("கஞ்சி", "உணவு"),
    "mother": ("தாய்",),
    "father": ("தந்தை",),
    "friends": ("நட்பு",),
    "friend's test": ("நட்பு ஆராய்தல்",),
    "friends test": ("நட்பு ஆராய்தல்",),
}

_PHRASES = tuple(key for key in ENGLISH if " " in key)
_WORDS = tuple(dict.fromkeys(word for phrase in ENGLISH for word in phrase.split(" ")))


@dataclass(frozen=True)
class LatinPlan:
    """English glosses, plus leftover words that may be romanized Tamil."""

    groups: tuple[tuple[str, ...], ...]
    pending: tuple[str, ...]


def latin_plan(query: str) -> LatinPlan | None:
    """Split a Latin query into glossary groups and leftover words.

    ``None`` means the query contains Tamil. Leftover words are not in
    the glossary; the search keeps a leftover only when it is romanized
    Tamil that occurs in the corpus.
    """
    if any("\u0b80" <= char <= "\u0bff" for char in query):
        return None
    words = _english_words(query)
    if not words:
        return LatinPlan((), ())
    groups: list[tuple[str, ...]] = []
    pending: list[str] = []
    index = 0
    while index < len(words):
        matched_length = 0
        for length in (3, 2, 1):
            if index + length > len(words):
                continue
            phrase = _known_phrase(words[index : index + length])
            if phrase is None:
                continue
            groups.append(ENGLISH[phrase])
            matched_length = length
            break
        if matched_length:
            index += matched_length
            continue
        pending.append(words[index])
        index += 1
    return LatinPlan(tuple(groups), tuple(pending))


def english_groups(query: str) -> list[tuple[str, ...]] | None:
    """Tamil search groups for an English query.

    ``None`` means the query is not English. An empty list means no
    glossary word was recognized. Unrecognized words are left out, so
    one unknown word does not erase the words that are known.
    """
    plan = latin_plan(query)
    if plan is None:
        return None
    return list(plan.groups)


def _known_phrase(words: list[str]) -> str | None:
    choices = [_candidates(word) for word in words]
    original = " ".join(words)
    if original in ENGLISH:
        return original
    found: list[str] = []
    for combo in itertools.product(*choices):
        phrase = " ".join(combo)
        if phrase in ENGLISH and phrase not in found:
            found.append(phrase)
    return found[0] if found else None


def _candidates(word: str) -> list[str]:
    forms = [word]
    stem = _stem(word)
    if stem and stem not in forms:
        forms.append(stem)
    if any(_form_known(form) for form in forms):
        return [form for form in forms if _form_known(form)]
    for form in forms:
        if len(form) < 5:
            continue
        typo = _unique_typo(form)
        if typo:
            return [typo]
    return forms


def _form_known(form: str) -> bool:
    if form in ENGLISH:
        return True
    return any(form in phrase.split(" ") for phrase in _PHRASES)


def _stem(word: str) -> str | None:
    for suffix in ("ing", "es", "ed", "s"):
        if suffix == "s" and word.endswith("ss"):
            return None
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return None


def _unique_typo(word: str) -> str | None:
    hits = [
        key
        for key in _WORDS
        if abs(len(key) - len(word)) <= 1 and _one_edit(word, key)
    ]
    if len(hits) == 1:
        return hits[0]
    return None


def _one_edit(left: str, right: str) -> bool:
    if left == right or abs(len(left) - len(right)) > 1:
        return False
    index_left = 0
    index_right = 0
    edits = 0
    while index_left < len(left) and index_right < len(right):
        if left[index_left] == right[index_right]:
            index_left += 1
            index_right += 1
            continue
        edits += 1
        if edits > 1:
            return False
        if len(left) == len(right):
            index_left += 1
            index_right += 1
        elif len(left) > len(right):
            index_left += 1
        else:
            index_right += 1
    edits += (len(left) - index_left) + (len(right) - index_right)
    return edits == 1


def _english_words(query: str) -> list[str]:
    folded = query.casefold().replace("\u2019", "'").replace("\u2018", "'")
    cleaned = "".join(char if char.isalpha() or char == "'" else " " for char in folded)
    words: list[str] = []
    for word in cleaned.split():
        word = word.strip("'")
        if len(word) >= 2 and word not in _STOP:
            words.append(word)
    return words


_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "and",
        "or",
        "to",
        "for",
        "in",
        "on",
        "with",
        "from",
        "by",
    }
)
