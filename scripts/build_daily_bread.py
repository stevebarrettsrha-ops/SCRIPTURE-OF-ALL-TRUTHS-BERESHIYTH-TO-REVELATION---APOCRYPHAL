#!/usr/bin/env python3
"""
build_daily_bread.py

Builds assets/DailyBread.js — the pool the home page draws today's portion
from. Every verse of all 104 books is read, and the passages that stand on
their own as encouragement are kept, tagged with a theme, and written out as
a compact table of references. The verse text itself is never copied: the
page reads it from assets/text/ at run time, so a portion can never drift
from the canon.

A portion is a **passage, never a lone line**. A single verse lifted out of
its paragraph is often either a fragment ("and your ears hear a word behind
you …") or a saying with nothing around it to say what it means. So a verse
that qualifies is only a seed: the paragraph it belongs to is grown around
it, backwards to the sentence that begins the thought and forwards until the
thought lands, and the whole passage is what gets served.

Selection, in order:

  * a seed verse must read as a complete thought — long enough to stand up,
    short enough to take in at a glance, ending in a full stop;
  * it must carry at least one note of encouragement (trust, refuge, mercy,
    joy, light, healing, promise …);
  * it must carry none of the hard matter that needs its surrounding
    chapter to be read rightly — slaughter, plague, curse, judgement
    poured out, uncleanness, betrayal, genealogy and census;
  * the paragraph grown around it must be two to four verses, must begin
    where a sentence begins, must land on a full stop, and every verse in
    it must be as clean as the seed. A seed with no safe paragraph around
    it is dropped rather than served bare;
  * passages from one chapter never overlap, and no more than a few are
    taken from any one chapter, so the year does not settle into one book.

Usage:
    python3 scripts/build_daily_bread.py
"""
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_DIR = ROOT / "assets" / "text"
INDEX_PATH = ROOT / "assets" / "index.json"
CURATED_PATH = ROOT / "assets" / "daily-bread.json"
OUTPUT = ROOT / "assets" / "DailyBread.js"

TAG = re.compile(r"<[^>]+>")
MAX_PER_CHAPTER = 3
MIN_CHARS = 58
MAX_CHARS = 340

# The shape of a portion. Two verses at least, so nothing is served as a
# bare line; four at most, so it is still a morning's reading and not a
# chapter. The character bounds are what a paragraph looks like on screen.
MIN_VERSES = 2
MAX_VERSES = 4
MIN_PASSAGE_CHARS = 170
MAX_PASSAGE_CHARS = 620

# Where a daily portion may come from. The books of teaching, prophecy,
# wisdom and the Messianic writings speak directly to the reader; the
# narrative and genealogical books tell a story that needs its chapter
# around it, so a single verse lifted out of them rarely encourages.
SOURCE_BOOKS = {
    # Torah — Debarim alone, which is addressed to the reader throughout
    "dabarim",
    # Wisdom and song
    "tehillim", "mishle", "iyob", "qoheleth", "ekah",
    # The Prophets
    "yashayahu", "yirmayahu", "yahazqal", "hoshea", "yoal", "amos",
    "obadyahu", "yonah", "mikah", "nahum", "habaqquq", "tsephanyahu", "haggai",
    "zakaryahu", "malaki",
    # The Messianic writings
    "mattithyahu", "mark", "luke", "yahuchanon", "romans",
    "1corinthians", "2corinthians", "galatians", "ephesians", "philippians",
    "colossians", "1thessalonians", "2thessalonians", "1timothy", "2timothy",
    "titus", "ibrim", "yaaqob", "1kepha", "2kepha",
    "1yahuchanon", "2yahuchanon", "3yahuchanon", "yahudah", "hazon",
    # Wisdom from the apocrypha
    "apoc-sirach", "apoc-wisdom",
}

# ---------------------------------------------------------------- themes
# Each theme is a bank of short reflections. A portion drawn from the pool
# is given the reflection whose turn it is that day, so the same verse read
# years apart is not framed the same way twice.
THEMES = {
    "trust": [
        "Trust is not a feeling to work up but a weight to hand over. Hand today's over.",
        "What you lean on decides how far you can walk. Lean here.",
        "Faith is not certainty about the road; it is certainty about the One leading.",
        "You are not asked to see the whole way — only to trust the One who does.",
        "Put your confidence where it cannot be embarrassed.",
        "Rest is what trust feels like from the inside.",
        "The safest place to put your weight today is on Yahuah's word.",
        "Doubt asks what if; trust asks who — and the answer settles it.",
    ],
    "refuge": [
        "A refuge is no use admired from a distance. Go in.",
        "Shelter is not the absence of storm but the presence of the One who holds it.",
        "Run to the strong tower before you are tired, not after.",
        "The walls that keep you were not built by you.",
        "You are not exposed today, however it feels.",
        "Hiding in Yahuah is not cowardice; it is wisdom.",
        "The safest ground is the ground He is standing on.",
        "Whatever is chasing you cannot follow you here.",
    ],
    "strength": [
        "Strength that comes from Him does not run out when yours does.",
        "You were never meant to carry today on your own reserves.",
        "Ask for the strength before you attempt the task.",
        "Weakness is not disqualification; it is the doorway.",
        "What is too heavy for you is not too heavy for Him.",
        "Endurance is strength stretched over time — and it is given, not summoned.",
        "Be strong in the strength that is lent, not the strength that is spent.",
        "The arm that upholds you today is not your own.",
    ],
    "comfort": [
        "Grief is not rebuked here; it is met.",
        "He does not wait for you to be composed before He draws near.",
        "Comfort is not a distraction from the wound but a hand upon it.",
        "You are seen in the place you thought no one was looking.",
        "The One who counts the stars is close to the broken-hearted.",
        "Let yourself be comforted; it is not weakness to be held.",
        "Nothing about your sorrow is too small for His attention.",
        "The tears you are hiding are already known.",
    ],
    "hope": [
        "Expectancy is not optimism; it is memory of what He has already done.",
        "The wait is not wasted, and it is not forever.",
        "What is promised is as certain as what is already given.",
        "Hope set on Yahuah has never been put to shame.",
        "Hold on — mornings in His hands have never failed to arrive.",
        "The end of this is not the end of you.",
        "Expect good from Him today; it is not presumption, it is trust.",
        "What you are waiting for is not in doubt, only in transit.",
    ],
    "joy": [
        "Joy is not the reward for a good day; it is strength for a hard one.",
        "Gladness is a discipline of remembering.",
        "Rejoicing is not pretending — it is looking somewhere else.",
        "Sing before the answer comes; that is what faith sounds like.",
        "The joy of Yahuah is not fragile, so neither is your day.",
        "Delight is a form of praise you can practise anywhere.",
        "Let something good today be noticed and named.",
        "Gladness given by Him outlasts the reason you were sad.",
    ],
    "guidance": [
        "Guidance is given to feet already moving.",
        "The next step lit is enough; take it.",
        "Ask before you plan, not after the plan fails.",
        "He leads — that means someone is ahead of you on this road.",
        "Direction comes to those who stay near enough to hear it.",
        "The way you should go is not hidden from those who ask.",
        "Let Him choose the turn today.",
        "Being led is more restful than deciding alone.",
    ],
    "mercy": [
        "Kindness is not earned here; it is poured.",
        "His compassions are new — including for what you did yesterday.",
        "Come as you are; that is the only way anyone has ever come.",
        "Forgiveness offered and not taken helps no one. Take it.",
        "Mercy is not owed to you, which is exactly what makes it good news.",
        "The Judge of all the earth is also the One washing your feet.",
        "There is more grace in Him than there is failure in you.",
        "Be as merciful today as you have been treated.",
    ],
    "provision": [
        "What He requires of you, He supplies to you.",
        "Bread for today has never once failed to arrive.",
        "Your Father knows what you need before you ask.",
        "Look at what has already been given before you name what is missing.",
        "Enough is a gift; learn to see it.",
        "Provision is often ordinary. Notice it anyway.",
        "He who feeds the birds has not forgotten your table.",
        "Give thanks for today's portion; tomorrow's will be there tomorrow.",
    ],
    "wisdom": [
        "Wisdom is asked for, not accumulated.",
        "Understanding begins where self-reliance ends.",
        "A wise step today is worth a clever plan tomorrow.",
        "Listen longer than you speak, and you will already be wiser.",
        "Instruction accepted is a shortcut you cannot buy.",
        "The fear of Yahuah is not fright; it is the beginning of seeing straight.",
        "Choose the good you know over the good you can argue for.",
        "Let today's decision be one you would want read aloud.",
    ],
    "love": [
        "You are loved first, before you did anything with it.",
        "Being loved is not a reward; it is the ground you stand on.",
        "Love that has no beginning has no reason to end.",
        "Let yourself be loved today, and then pass it on undiluted.",
        "The measure of His love is not your performance.",
        "Loving-kindness follows you — it does not merely wait for you.",
        "Nothing you did today changed how He feels about you.",
        "Love is the last word here, and it always was.",
    ],
    "shalom": [
        "Peace is not the absence of trouble but the presence of the One over it.",
        "Let the shalom given to you actually be received.",
        "Stillness is not idleness; it is trust holding its ground.",
        "A quiet heart is not a small thing — it is a fought-for thing.",
        "Peace guards; let it stand at the gate of your thoughts today.",
        "Be at rest: what is out of your hands is not out of His.",
        "Shalom is wholeness, not merely quiet.",
        "Take the peace He gives rather than the peace the day offers.",
    ],
    "light": [
        "Light does not argue with darkness; it ends it.",
        "The lamp lights the step, not the whole road — and that is mercy.",
        "Walk in what you can see, and more will be shown.",
        "You are not left to feel your way today.",
        "What is hidden is not hidden from Him.",
        "Let one thing you do today be visible enough to point past you.",
        "Morning always comes to those who wait for it.",
        "The light of life is a Person, not a mood.",
    ],
    "deliverance": [
        "The rescue you need is not beyond His reach.",
        "He has done this before, and He has not lost the skill.",
        "Cry out — that is not weakness, it is the appointed way.",
        "What holds you does not hold Him.",
        "Deliverance often begins before you feel it.",
        "The pit is not your address.",
        "He saves — that is not a slogan, it is His character.",
        "Look back at what you have already been carried through.",
    ],
    "praise": [
        "Thanksgiving is the gate; you always know the way in.",
        "Praise re-orders a day that has gone crooked.",
        "Bless Him before you ask; it will change what you ask for.",
        "Say aloud one thing He has done. It is harder to despair afterwards.",
        "Worship is not flattery; it is accuracy.",
        "Let today's smallest mercy be named and thanked for.",
        "Gratitude is memory doing its proper work.",
        "Give Him the praise due to His Name, and the day rights itself.",
    ],
    "faithfulness": [
        "He is not weighing whether to keep His word.",
        "What He said stands, whatever today looks like.",
        "Great is His trustworthiness — new this morning, new tomorrow.",
        "He has never yet been late to Himself.",
        "The promise does not depend on your grip but on His.",
        "Steady is a quality of His, and it can become one of yours.",
        "He finishes what He begins, including you.",
        "Faithfulness is not glamorous; it is everything.",
    ],
}
THEME_NAMES = sorted(THEMES)

# Keywords that decide the theme, checked in this order.
THEME_WORDS = [
    ("refuge", r"\b(refuge|stronghold|shelter|hiding place|shield|fortress|rock of|"
               r"under his wings|strong tower)\b"),
    ("deliverance", r"\b(deliver|delivered|deliverance|rescue|redeem|redeemed|"
                    r"redemption|saved|saves|salvation|set free|ransom)\b"),
    ("comfort", r"\b(comfort|comforts|comforted|broken-hearted|heal|heals|healed|"
                r"binds up|wipe away|tears|mourn|weeping)\b"),
    ("strength", r"\b(strength|strengthen|strengthens|strong|might|power|uphold|"
                 r"upholds|sustain|endure|endurance)\b"),
    ("trust", r"\b(trust|trusts|trusted|believe|belief|rely|commit your|lean not|"
              r"depend)\b"),
    ("hope", r"\b(hope|expectancy|expectation|wait for|waited|await|patiently)\b"),
    ("joy", r"\b(joy|joyful|rejoice|rejoices|rejoicing|glad|gladness|delight|"
            r"delights|sing|singing)\b"),
    ("shalom", r"\b(shalom|peace|peaceful|quiet|rest|rests|still|calm)\b"),
    ("light", r"\b(light|lamp|shine|shines|shining|morning|dawn|bright)\b"),
    ("mercy", r"\b(mercy|mercies|compassion|compassions|kindness|chen|forgive|"
              r"forgives|forgiven|gracious|pardon)\b"),
    ("love", r"\b(love|loves|loved|loving|beloved|everlasting love)\b"),
    ("provision", r"\b(provide|provides|provision|feed|feeds|supply|supplies|"
                  r"satisfy|satisfies|bread|fill|fills|enough|lack)\b"),
    ("guidance", r"\b(guide|guides|lead|leads|leading|path|paths|way you should|"
                 r"teach|teaches|instruct|counsel|direct)\b"),
    ("wisdom", r"\b(wisdom|wise|understanding|knowledge|discern|prudence|"
               r"instruction)\b"),
    ("faithfulness", r"\b(faithful|faithfulness|trustworthiness|everlasting|"
                     r"never leave|not forsake|steadfast|covenant|berith)\b"),
    ("praise", r"\b(praise|praises|bless|blessed|baruk|thank|thanks|thanksgiving|"
               r"halleluyah|exalt|magnify|glorify)\b"),
]
THEME_RES = [(name, re.compile(pat, re.I)) for name, pat in THEME_WORDS]

UPLIFT = re.compile(
    r"\b(trust|refuge|strength|strengthen|hope|joy|rejoice|glad|delight|shalom|"
    r"peace|rest|comfort|heal|mercy|mercies|compassion|kindness|chen|forgive|"
    r"love|loved|beloved|faithful|trustworthiness|everlasting|deliver|save|"
    r"saves|salvation|redeem|light|lamp|shine|guide|lead|teach|counsel|wisdom|"
    r"understanding|bless|baruk|blessed|praise|thank|thanksgiving|halleluyah|"
    r"provide|satisfy|uphold|sustain|shepherd|good|goodness|righteous|"
    r"righteousness|life|live|grace|glory|esteem|promise|remember|near|"
    r"answer|hear|hears|heard|help|helper|shield|stronghold|rock|fear not|"
    r"do not fear|be strong|take heart|new every morning)\b", re.I)

# A note strong enough to carry a whole day on its own.
STRONG = re.compile(
    r"\b(refuge|stronghold|strong tower|deliver|delivers|delivered|"
    r"deliverance|salvation|saves|redeem|redeemer|shalom|trust|trusts|"
    r"mercy|mercies|compassion|compassions|kindness|chesed|chen|comfort|"
    r"comforts|heal|heals|healed|everlasting|faithful|trustworthiness|"
    r"strength|strengthens|uphold|upholds|sustain|hope|expectancy|joy|"
    r"rejoice|glad|gladness|light|lamp|shepherd|guide|guides|leads me|"
    r"wisdom|understanding|forgive|forgives|forgiven|blessed|baruk|"
    r"berakah|praise|thanksgiving|halleluyah|rest|near to all|do not fear|"
    r"fear not|be strong|take heart|new every morning|love|loved|beloved)\b",
    re.I)

# The same words with the ground cut from under them — "not of shalom",
# "loved evil", "no rest" — must not be read as encouragement.
GOOD_THING = (r"shalom|peace|rest|joy|hope|mercy|mercies|kindness|comfort|"
              r"compassion|compassions|chen|grace|favour|value|life|deliver|"
              r"deliverance|redeem|redeemed|redemption|save|saved|salvation|"
              r"light|love|trust|strength|help|healing|bread|food|water|feed")
NEGATED = re.compile(
    r"\b(not|no|never|nor|without|neither|cease|ceased|lack|lacks|lacked|"
    r"fail|fails|failed|refuse|refused|deny|denied|far from)\b[^.;:!?]{0,28}?"
    r"\b(" + GOOD_THING + r")\b", re.I)

# And the same undoing said the other way round — "Has His kindness ceased",
# "the promise failed", "has He forgotten to show chen".
# A negation inside the gap turns the sense back the right way round —
# "His compassions do not fail" is the promise, not its loss — so the gap
# is only read as far as the first "not".
NEGATED_AFTER = re.compile(
    r"\b(" + GOOD_THING + r"|promise|compassions?|chen)\b"
    r"(?:(?!\b(?:not|never|nor|no)\b)[^.;:!?]){0,28}?"
    r"\b(ceased?|failed?|forgotten|forsaken|rejected|withheld|shut up|"
    r"run out|no more|gone)\b", re.I)

# Matter that no single verse can carry on its own, whatever surrounds it.
HARD_AVOID = re.compile(
    r"\b(slaughter\w*|slain|slew|slay|kill|killed|blood|bloody|corpse|carcass|"
    r"dead body|plague|leprosy|leprous|boils|dung\w*|urine|vomit|worm|maggot|"
    r"harlot|whore|whoring|adultery|adulterous|abomination|"
    r"abominations|incest|nakedness|menstru|foreskin|circumcise|circumcised|"
    r"census|numbered|cubits|shekels|begat|genealogy|reigned|encamped|"
    r"pitched|smote|smitten|tribute|spoil|plunder|dungeon|prisoner|bondage|"
    r"drunk|drunkard|slander|scoff|scorn|mock|mocked|oppress|oppressed|"
    r"locust|locusts|criminal|chains|dies|unbelieving|unbelief|enslaved|"
    r"sour wine|sponge|reed|stake|impale\w*|crucif\w*|foe|foes|downfall|"
    r"rotten|controversy|reprove|reproves|cut off|cut out|sharpness|"
    r"howl\w*|melt away|trodden|carved image|graven image|molten image|"
    r"epileptic|avenge\w*|millstone|assail|crush\w*|loathe\w*|cruel|"
    r"harsh|frighten\w*|shudder\w*|struck me|drink offering|"
    r"idol|idols|demon|demons|satan|devil|beliar|sacrifice|burnt offerings?|"
    r"tithes|firstlings|tortur\w*|torment\w*|blasphem\w*|persecut\w*|"
    r"insulter|insulters|flee|flees|fled|"
    r"unclean|uncleanness|years old|days of the life|died|dying|"
    r"smite|smitten|smote|under the ban|utterly destroy|dispossess|"
    r"drive out|drove out|sinner|sinners|wicked|wickedness|lying|lie|lies|"
    r"wail|wailing|dirge|woe|beware|take heed|scribes|Pharisees|Sadducees|accusation|accuse|accused|shortened|withered|"
    r"deceit|deceive|deceived|liar|folly|arrogant|envy|greed|greedy|"
    r"strife|quarrel|siege|captive|captivity|famine|beast of|yoke of|"
    r"whore|whored|whoredom|sewer|sulphur|brimstone|scourge|scourges|"
    r"snares|scorching|tear off|torn|devour|devoured|swallow up)\b",
    re.I)

# "Deliver" is the warmest word in the concordance and the coldest: the same
# verb carries Yasharal out of Mitsrayim and Yahusha into the hands of the
# kohanim. Handing a person over is never a portion, whatever the verb.
BETRAYAL = re.compile(
    r"\b(betray|betrays|betrayed|betrayer|betraying|"
    r"deliver(?:s|ed|ing)?\s+(?:him|her|them|me|us|you|up)\b[^.;:!?]{0,20}\bup\b|"
    r"deliver(?:s|ed|ing)?\s+up\b|deliver(?:s|ed|ing)?\s+(?:him|her|them|me|us|you)\s+to\b|"
    r"handed?\s+over|given\s+over|"
    r"thirty pieces|kiss(?:ed)? him|arrest|seize him|took him)\b", re.I)

# Matter that belongs in a portion only when it is being overcome — "I fear
# no evil", "shall not perish", "shall not be put to shame".
SOFT_AVOID = re.compile(
    r"\b(evil|wicked|wickedness|shame|ashamed|reproach|perish|perished|"
    r"fear|afraid|dread|terror|destroy|destroyed|destruction|desolate|"
    r"wrath|fury|anger|angry|vengeance|curse|cursed|judgement|judgment|"
    r"condemn|condemned|punish|punishment|sin|sinned|sinner|sinners|"
    r"iniquity|transgression|transgressions|lawless|guilty|enemy|enemies|"
    r"adversary|adversaries|sword|war|battle|trouble|troubles|distress|"
    r"sorrow|sorrows|grief|weep|wept|mourn|mourning|lament|die|death|"
    r"futility|vanity|"
    r"humbled my|wasted away|consumed|faint|feeble|"
    r"trespass|trespasses|offence|offense|rebel|rebelled|rebellion|"
    r"grave|pit|sheol|hell|fall|fallen|stumble|hate|hated|hatred|"
    r"forsake|forsaken|cast off|wander|stray|astray|darkness|shadow)\b",
    re.I)

# What rescues a soft word: the verse says it is undone.
RESCUED = re.compile(
    r"\b(no|not|never|nor|neither|none|nothing|without|free from|saved from|"
    r"delivered from|deliver|delivers|delivered|redeem|redeems|redeemed|"
    r"out of|overcome|overcomes|conquer|conquers|swallowed up|"
    r"turn from|turns from|forgive|forgives|forgiven|heal|heals|healed|"
    r"though|even though|yet)\b[^.;:!?]{0,30}?$", re.I)


def soft_is_rescued(text):
    """Every soft word in the verse is one the verse itself overturns."""
    for m in SOFT_AVOID.finditer(text):
        before = text[max(0, m.start() - 34):m.start()]
        if not RESCUED.search(before):
            return False
    return True


# A portion has to speak: to the reader, or about the One the reader came
# for. A verse with neither is a piece of narrative.
ADDRESS = re.compile(r"\b(you|your|yours|thee|thy|thine|ye|us|our|ours|we|"
                     r"me|my|mine|whoever|whosoever|everyone|anyone|"
                     r"blessed is|baruk is)\b", re.I)
DIVINE = re.compile(r"\b(Yahuah|Aluahim|Aloah|Mashiach|Yahusha|Ruach|Most High|"
                    r"Almighty|Al|He|His|Him|Father|Master|Sovereign)\b")

# Narrative gives itself away by naming people and moving them about.
NARRATIVE = re.compile(
    r"\b(said to|says to|answered|answering|replied|spoke to him|"
    r"went out|went up|came to him|came to her|arose|departed|returned|"
    r"dwelt|journeyed|camped|bore him|conceived|camels|donkeys|"
    r"tent|tents|jar|wife of|daughter of|army|chariot|news|"
    r"one of them|the rest said|ran and|took a|gave it to him|"
    r"brought him|reported to|my own hand|written to you|"
    r"how i am doing|concerning maidens|greeting of|"
    r"a certain|asked him|asked her|asking him|questioned|urged|"
    r"came near|drew near to him|sent him|sending him|and he said|"
    r"and they said|and she said|as they were|when they had)\b", re.I)

# Names that carry no theological weight in a lifted verse. Divine and
# set-apart vocabulary is excluded from the count.
NOT_A_NAME = {
    "yahuah", "aluahim", "aloah", "al", "mashiach", "yahusha", "yasharal",
    "ruach", "qodesh", "torah", "shabbath", "shalom", "chen", "chesed",
    "sheol", "tsiyon", "yahrushalayim", "amen", "selah", "halleluyah",
    "besorah", "hwhy", "baruk", "berakah", "mal", "kohen", "nabi", "i",
    # Capitalised words that are titles or vocabulary, not people
    "word", "name", "lord", "master", "sovereign", "most", "high",
    "almighty", "father", "son", "spirit", "holy", "set", "apart", "king",
    "shamayim", "heaven", "redeemer", "saviour", "savior", "shepherd",
    "rock", "way", "truth", "life", "wisdom", "the", "and", "but", "for",
    "let", "see", "look", "yea", "surely", "blessed", "happy", "how",
    "who", "what", "when", "then", "now", "therefore", "because", "yet",
    "his", "he", "she", "they", "we", "you", "your", "my", "our", "their",
    "elohim", "adonai", "yah", "immerser", "messiah", "gospel", "good",
}
NAME_RE = re.compile(r"\b([A-ZĂĔÀ-ɏḀ-ỿ][a-zà-ɏḁ-ỿ'’‛]{2,})")


SENTENCE_START = re.compile(r'(^|[.!?;:”"“\'‘(]\s*)$')


def proper_names(text):
    """Proper names in a verse, other than the set-apart vocabulary.

    A capital that merely opens a sentence or a quotation is not a name.
    """
    out = set()
    for m in NAME_RE.finditer(text):
        if SENTENCE_START.search(text[:m.start()]):
            continue
        w = m.group(1)
        k = unicodedata.normalize("NFD", w)
        k = "".join(c for c in k if unicodedata.category(c) != "Mn").lower()
        k = k.replace("’", "").replace("'", "").replace("‛", "")
        if k in NOT_A_NAME:
            continue
        out.add(k)
    return out


# A warning is not a portion, however true it is.
WARNING = re.compile(
    r"\b(if you do not|unless you|neither shall|shall not enter|shall not "
    r"inherit|do not think|beware|take heed|how shall you|why do you|"
    r"cursed is|cursed be|it shall not go well|without understanding|"
    r"did not turn back|have not turned back|reject forever|"
    r"still without|do you not|did not believe|do not believe|"
    r"are you also|have you not|have you heard|what do you know|"
    r"do you limit|are they withheld|where are your|where are their)\b",
    re.I)

# Verses that are really lists, headings or fragments.
LIST_LIKE = re.compile(r"\bson of\b.*\bson of\b|\bthe sons of\b|^\s*and\s+\w+\s*,",
                       re.I)
DIGITS = re.compile(r"\d")


def plain(t):
    return TAG.sub("", t).strip()


# Words that carry a note without naming it outright, used only when none of
# the theme vocabularies above appears.
SECOND_PASS = [
    ("refuge", r"\b(help|helper|shield|rock|safe|safety|keep|keeps|kept|guard|"
               r"guards|watch over|preserve)\b"),
    ("strength", r"\b(fear not|do not fear|be strong|take heart|courage|"
                 r"courageous|arise|stand)\b"),
    ("comfort", r"\b(near|nearer|hear|hears|heard|answer|answers|answered|cry|"
                r"call upon|listen)\b"),
    ("faithfulness", r"\b(promise|promised|remember|remembers|remembered|word of|"
                     r"declares|oath|swore)\b"),
    ("light", r"\b(life|live|lives|living|alive|day|days)\b"),
    ("praise", r"\b(good|goodness|glory|esteem|great|greatness|holy|set-apart|"
               r"name of)\b"),
    ("wisdom", r"\b(righteous|righteousness|upright|blameless|truth|true)\b"),
]
SECOND_RES = [(name, re.compile(pat, re.I)) for name, pat in SECOND_PASS]


def theme_of(text):
    """The theme a verse speaks most of, not merely the first one it mentions."""
    scores = Counter()
    for name, rx in THEME_RES:
        hits = len(rx.findall(text))
        if hits:
            scores[name] += hits
    if scores:
        best = max(scores.values())
        # Ties go to the theme listed first, which is the more specific one.
        for name, _ in THEME_RES:
            if scores.get(name) == best:
                return name
    for name, rx in SECOND_RES:
        if rx.search(text):
            return name
    return None


def qualifies(text):
    if not (MIN_CHARS <= len(text) <= MAX_CHARS):
        return False
    # Many verses open with the Name in parentheses — "(YAHUAH) HWHY is my
    # shepherd" — or with a quotation mark.
    opener = text.lstrip("“‘\"'(")
    if not opener or not opener[0].isupper():
        return False
    # A portion should land, not leave a thought hanging. A poetic line
    # closing on a semicolon still lands; a question does too when the
    # answer is the encouragement ("Whom should I fear?").
    if text[-1] not in '.!;”’"':
        if text[-1] == "?" and not (STRONG.search(text) and
                                    not SOFT_AVOID.search(text)):
            return False
        if text[-1] not in '.!;”’"?':
            return False
    if HARD_AVOID.search(text) or BETRAYAL.search(text):
        return False
    if SOFT_AVOID.search(text) and not soft_is_rescued(text):
        return False
    if NEGATED.search(text):
        return False
    if not UPLIFT.search(text):
        return False
    # It must carry a note strong enough to stand alone, or two quieter
    # ones together.
    if not STRONG.search(text):
        quiet = set(w.lower() for w in UPLIFT.findall(text))
        if len(quiet) < 2:
            return False
    if WARNING.search(text):
        return False
    if LIST_LIKE.search(text):
        return False
    if NARRATIVE.search(text):
        return False
    # It must either speak to the reader, or say something of Yahuah worth
    # carrying: "Yahuah is good to all" needs no second person.
    if not DIVINE.search(text):
        return False
    if not (ADDRESS.search(text) or STRONG.search(text)):
        return False
    # Several people named is a scene, not a portion.
    if len(proper_names(text)) >= 3:
        return False
    if len(DIGITS.findall(text)) > 2:
        return False
    # A verse that is mostly names reads as a list, not a portion.
    words = re.findall(r"[A-Za-zÀ-ɏḀ-ỿ'’]+", text)
    if not words:
        return False
    caps = sum(1 for w in words[1:] if w[:1].isupper())
    if caps > len(words) * 0.34:
        return False
    return True


# ------------------------------------------------------------- passages
# A verse that opens with one of these is answering something said in the
# verse before it — "Therefore …", "For …", "so that …". Served alone it
# begins in the middle of a thought, so the verse before must come with it.
# A verse that opens in lower case is plainly a continuation of the last.
OPENS_LOWER = re.compile(r"^\s*[“‘\"'(–— ]*[a-zà-ɏḁ-ỿ]")
DEPENDENT = re.compile(
    r"^\s*[“‘\"'(–— ]*(?:therefore|thus|so|then|for|because|but|yet|which|"
    r"who|whom|whose|nor|neither|since|though|although|however|wherefore|"
    r"hence|that)\b", re.I)

# A capitalised "And …" is not a continuation: Hebrew keeps it at the head
# of complete sentences, and a portion may open there.

# Where a thought lands. A verse ending in a comma or a dash is still
# talking; one ending here has finished.
LANDS = re.compile(r"[.!?”’\"]\s*$")

# A companion verse does not have to preach — it has to be safe to read
# beside the seed. It must not drag in the matter the seed was chosen for
# avoiding, and it must not be a scene with a cast.
def companion_ok(text):
    if not text or len(text) > MAX_CHARS:
        return False
    if HARD_AVOID.search(text) or BETRAYAL.search(text):
        return False
    if SOFT_AVOID.search(text) and not soft_is_rescued(text):
        return False
    if NEGATED.search(text) or NEGATED_AFTER.search(text):
        return False
    if WARNING.search(text) or LIST_LIKE.search(text) or NARRATIVE.search(text):
        return False
    if len(proper_names(text)) >= 3:
        return False
    if len(DIGITS.findall(text)) > 2:
        return False
    words = re.findall(r"[A-Za-zÀ-ɏḀ-ỿ'’]+", text)
    if len(words) < 4:
        return False
    caps = sum(1 for w in words[1:] if w[:1].isupper())
    return caps <= len(words) * 0.34


def leans_back(text):
    """This verse leans on the one before it and cannot open a portion."""
    return bool(OPENS_LOWER.match(text) or DEPENDENT.match(text))


def passage_ok(text):
    """The paragraph as a whole is what the reader meets, so it is judged
    as a whole: one bad line in it spoils the portion however good the
    verse at its heart."""
    if HARD_AVOID.search(text) or BETRAYAL.search(text):
        return False
    if SOFT_AVOID.search(text) and not soft_is_rescued(text):
        return False
    if NEGATED.search(text) or NEGATED_AFTER.search(text):
        return False
    if WARNING.search(text):
        return False
    if LIST_LIKE.search(text) or NARRATIVE.search(text):
        return False
    # A portion is not an interrogation. One or two questions can carry a
    # thought ("Whom should I fear?"); a paragraph of them is an argument
    # with the reader in the middle of it.
    if text.count("?") >= 3:
        return False
    if len(proper_names(text)) >= 3:
        return False
    if not STRONG.search(text):
        return False
    # Two different notes of encouragement across the paragraph: enough
    # that the portion is about something, not merely free of trouble.
    if len(set(w.lower() for w in UPLIFT.findall(text))) < 2:
        return False
    if not (ADDRESS.search(text) and DIVINE.search(text)):
        return False
    words = re.findall(r"[A-Za-zÀ-ɏḀ-ỿ'’]+", text)
    caps = sum(1 for w in words[1:] if w[:1].isupper())
    return caps <= len(words) * 0.30


def score_passage(text, verse_count):
    """How well a paragraph carries a day. Warmth counts for it, hard
    matter and a crowd of names count against it and a short reading is
    preferred to a long one that says no more."""
    strong = len(STRONG.findall(text))
    notes = len(set(w.lower() for w in UPLIFT.findall(text)))
    soft = len(SOFT_AVOID.findall(text))
    return (3 * strong + 2 * notes - 5 * soft
            - 3 * len(proper_names(text)) - 2 * (verse_count - MIN_VERSES))


def build_passage(verses, seed, taken):
    """Choose the paragraph to serve around a seed verse.

    Every window of two to four verses that contains the seed is considered;
    the one that reads best as a whole is returned as (first verse, last
    verse, passage). None means no window around this seed is fit to serve —
    the seed is then dropped rather than served as a bare line.
    """
    texts = [plain(v["t"]) for v in verses]
    best = None
    for lo in range(max(0, seed - MAX_VERSES + 1), seed + 1):
        if leans_back(texts[lo]):
            continue
        for hi in range(seed, min(len(verses), lo + MAX_VERSES)):
            if hi - lo + 1 < MIN_VERSES or not LANDS.search(texts[hi]):
                continue
            window = range(lo, hi + 1)
            # A few books number their verses with gaps in them. The
            # reference printed on the page is a range, so the verses in it
            # have to run without one.
            if verses[hi]["n"] - verses[lo]["n"] != hi - lo:
                continue
            if any(verses[i]["n"] in taken for i in window):
                continue
            if any(i != seed and not companion_ok(texts[i]) for i in window):
                continue
            text = " ".join(texts[i] for i in window)
            if not (MIN_PASSAGE_CHARS <= len(text) <= MAX_PASSAGE_CHARS):
                continue
            if not passage_ok(text):
                continue
            mark = score_passage(text, hi - lo + 1)
            if best is None or mark > best[0]:
                best = (mark, verses[lo]["n"], verses[hi]["n"], text)
    if best is None:
        return None
    return best[1], best[2], best[3]


def main():
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    order = [b["id"] for b in index["books"]]

    pool = defaultdict(list)
    per_theme = Counter()
    scanned = 0
    curated_refs = set()
    for e in json.loads(CURATED_PATH.read_text(encoding="utf-8"))["pool"]:
        for n in range(e["from"], e["to"] + 1):
            curated_refs.add((e["book"], e["chapter"], n))

    for bid in order:
        if bid not in SOURCE_BOOKS:
            continue
        path = TEXT_DIR / f"{bid}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for cn in sorted(data["chapters"], key=lambda x: int(x)):
            verses = data["chapters"][cn].get("verses", [])
            kept = 0
            taken = set()
            for i, v in enumerate(verses):
                scanned += 1
                if kept >= MAX_PER_CHAPTER:
                    break
                if v["n"] in taken:
                    continue
                if (bid, int(cn), v["n"]) in curated_refs:
                    continue          # already served as a featured portion
                text = plain(v["t"])
                if not qualifies(text):
                    continue
                grown = build_passage(verses, i, taken)
                if grown is None:      # no paragraph around it — leave it out
                    continue
                first, last, passage = grown
                if any((bid, int(cn), n) in curated_refs
                       for n in range(first, last + 1)):
                    continue          # the paragraph runs into a featured one
                theme = theme_of(passage)
                if theme is None:      # nothing to frame it with — leave it out
                    continue
                pool[bid].append([int(cn), first, last, THEME_NAMES.index(theme)])
                taken.update(range(first, last + 1))
                per_theme[theme] += 1
                kept += 1

    total = sum(len(v) for v in pool.values())
    verse_count = sum(r[2] - r[1] + 1 for rows in pool.values() for r in rows)

    curated = json.loads(CURATED_PATH.read_text(encoding="utf-8"))["pool"]
    featured = [
        {"b": e["book"], "c": e["chapter"], "f": e["from"], "t": e["to"],
         "th": e["theme"], "r": e["reflection"]}
        for e in curated
    ]

    js = [HEADER]
    js.append("  var THEME_NAMES = " + json.dumps(THEME_NAMES) + ";\n")
    js.append("  var REFLECTIONS = " + json.dumps(
        {k: THEMES[k] for k in THEME_NAMES}, ensure_ascii=False, indent=2
    ).replace("\n", "\n  ") + ";\n")
    js.append("  var FEATURED = " + json.dumps(featured, ensure_ascii=False,
                                               indent=1).replace("\n", "\n  ") + ";\n")
    js.append("  // book id -> [chapter, first verse, last verse, theme index] …\n")
    js.append("  var POOL = {\n")
    for bid in order:
        if not pool[bid]:
            continue
        rows = ",".join("[%d,%d,%d,%d]" % tuple(r) for r in pool[bid])
        js.append(f'    "{bid}": [{rows}],\n')
    js[-1] = js[-1].rstrip(",\n") + "\n"
    js.append("  };\n")
    js.append(BODY)
    OUTPUT.write_text("".join(js), encoding="utf-8")

    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    print(f"  verses scanned   {scanned}")
    print(f"  featured (hand-written reflections)  {len(featured)}")
    books_used = sum(1 for rows in pool.values() if rows)
    print(f"  pool             {total} passages ({verse_count} verses, "
          f"{verse_count / total:.1f} a portion) from {books_used} books")
    print(f"  portions total   {total + len(featured)}  "
          f"({(total + len(featured)) / 365.25:.1f} years without repeat)")
    print("  by theme:")
    for t, n in per_theme.most_common():
        print(f"     {t:14s} {n}")


HEADER = '''// DailyBread.js
// The pool the home page draws today's portion from.
//
// GENERATED by scripts/build_daily_bread.py — edit that script, not this
// file. It reads every verse of all 104 books and keeps the passages that
// stand on their own as encouragement (see the commentary there for the
// rules). Every portion is a paragraph of two to four verses: a single line
// lifted out of its place too often says nothing on its own.
//
//   BesorahDailyBread.forDay(dayNumber)  -> {book, chapter, from, to,
//                                            theme, reflection}
//   BesorahDailyBread.size               -> how many portions exist
//
// Only references are stored. The verse text is read from assets/text/ at
// run time, so a portion can never drift from the canon.
//
// A portion is chosen by walking the pool with a stride that is coprime
// with its length: every portion is served exactly once before any is
// served twice, and the cycle runs the better part of a year. A shorter
// pool of paragraphs is worth more than a long one of bare lines.
(function (global) {
  "use strict";

'''

BODY = '''
  // Flatten the per-book table once, on first use.
  var flat = null;
  function entries() {
    if (flat) return flat;
    flat = [];
    for (var bid in POOL) {
      if (!POOL.hasOwnProperty(bid)) continue;
      var rows = POOL[bid];
      for (var i = 0; i < rows.length; i++) {
        flat.push([bid, rows[i][0], rows[i][1], rows[i][2], rows[i][3]]);
      }
    }
    return flat;
  }

  function gcd(a, b) { while (b) { var t = a % b; a = b; b = t; } return a; }

  // A stride near the golden section of the total spreads consecutive days
  // across different books; coprimality guarantees full coverage.
  var strideCache = {};
  function strideFor(total) {
    if (strideCache[total]) return strideCache[total];
    var s = Math.floor(total * 0.6180339887) || 1;
    while (gcd(s, total) !== 1) s++;
    strideCache[total] = s;
    return s;
  }

  function total() { return FEATURED.length + entries().length; }

  // The portion for a given day number (days since the epoch, local time).
  function forDay(day) {
    var n = total();
    if (!n) return null;
    day = Math.floor(day);
    var idx = ((day % n) * strideFor(n)) % n;
    if (idx < 0) idx += n;

    if (idx < FEATURED.length) {
      var f = FEATURED[idx];
      return {
        book: f.b, chapter: f.c, from: f.f, to: f.t,
        theme: f.th, reflection: f.r
      };
    }
    var e = entries()[idx - FEATURED.length];
    var theme = THEME_NAMES[e[4]] || "trust";
    var bank = REFLECTIONS[theme];
    var line = bank[Math.abs(day + idx) % bank.length];
    return {
      book: e[0], chapter: e[1], from: e[2], to: e[3],
      theme: theme.charAt(0).toUpperCase() + theme.slice(1),
      reflection: line
    };
  }

  global.BesorahDailyBread = {
    forDay: forDay,
    get size() { return total(); },
    THEME_NAMES: THEME_NAMES
  };
})(typeof window !== "undefined" ? window : this);
'''


if __name__ == "__main__":
    main()
