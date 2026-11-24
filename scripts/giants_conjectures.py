"""Conjectured words for the gaps ("…") in the Book of Giants.

Each gap in assets/text/apoc-giants.json is filled, in order, from this
table; None leaves the gap as "…" (where nothing sensible can be offered,
such as a name cut off mid-word). The fills are the project's own guesses,
made from the story's parallels: 1 Enoch 6-16 (the Watchers' descent, the
giants, the tablets, Ḥanoḵ's message, Raphaal's binding), Bereshith 6, the
fuller translations of the same Qumran scrolls (4Q530 col. ii: the thrones
set up and the books opened; 4Q531 frag. 1: Gilgamesh's boast), Henning's
edition of the Middle Persian fragments, and "The Book of Giants — the
reconstruction, based on biblical texts" (a paraphrase that supplies its own
connecting words in brackets), whose readings are followed in chapters 1-4
wherever it offers one. They are printed
<span class="cj">, lighter and in italic like the editors' restorations,
so the scroll's own words can always be told from what is supplied.

A fill list must have exactly as many entries as the verse has gaps; the
builder stops if the text changes under it.
"""

FILLS = {
    # ---- 1: the Watchers' sin; the giants born and their violence ----
    "1:1": ["In those days the fallen mal'akim came down, and", "all things. At this time", "and the earth was filled with violence,", "people, and", "with mortal women."],
    "1:2": ["The wicked mal'akim consumed", "and they consumed", "and the birds of", "and they ate the", "they devoured."],
    "1:3": ["they sinned against, and", "earthly things;", "harsh", "upon", "as well."],
    "1:4": ["The two hundred mal'akim seized", "sheep and", "of every", "they took them for in-breeding with humans,", "of every kind."],
    "1:5": ["Then the fallen ones came, and", "all creation, and", "upon the earth. These were the ones whom", "and was defiled", "the", "they turned against mankind,", "more, and"],
    "1:6": ["The monsters sought out", "which would be destroyed or perverted.", "the", "and giants", "destroyed, though", "in their might,", "of Aluahim,", "they were abominations, and", "and the giants more", "upon it, and", "the judgment that would come", "them."],
    "1:7": ["for", "yet", "satisfy them, and it was said:", "destroyed from the face of the earth.\""],
    # ---- 2: the tablet in the water; the giants' fear and dreams ----
    "2:1": ["Mahway reported that in his dream", "and", "then", "the flood, and all the names but three had vanished."],
    "2:2": ["And the group said:"],
    "2:3": ["and who will be blamed most of", "hear", "and saying"],
    "2:4": ["together, for our wickedness is", "will be denied me", "the monsters, troubled by it,", "and troubled them."],
    "2:5": ["Then came", "Tell me the vision"],
    "2:6": ["And Mahway said:"],
    "2:7": ["And", "Ohya", "then this too may come to pass."],
    "2:8": ["We are about", "removed from", "they heard this,", "and mourned."],
    "2:9": ["Use", "the group counselled.", "Who has done this to us?", "show the most corruption to mankind."],
    "2:10": ["But", "and can resist."],
    "2:11": ["And Gilgamesh said:", "I can overcome", "now"],
    "2:12": ["are mal'akim who"],
    "2:13": ["only that, but"],
    "2:14": ["The day"],
    "2:15": ["And they were silent.", "and", "the field of battle we cannot win, I nor", "himself."],
    "2:16": ["remained,", "beings from shamayim, and", "the three."],
    "2:17": ["said Ohya, and of Gilgamesh", "in the night,", "that all the forebodings were", "the rulers of the earth, for", "the assembly."],
    # ---- 3: the dreams of the two brothers; Mahway flies to Ḥanoḵ ----
    "3:1": ["the gathering of the giants", "saying:"],
    "3:2": ["and in it were", "the garden, and"],
    "3:3": ["and suddenly the garden was ablaze, and it consumed", "and nothing was left.", "but none could interpret it."],
    "3:4": ["Then one said: Let us go"],
    "3:5": ["and thrones were set up, and the Great Qadash One sat, and the books were opened, and he made an end of us;"],
    "3:8": ["to Ḥanoḵ, so that it may be known", "he has spoken with you, and that"],
    "3:9": ["listen", "and tell us", "And Mahway went."],
    "3:10": ["Then", "and", "and came to the dwelling of Ḥanoḵ,"],
    "3:11": ["of his mission, and said he would speak with him. Flying", "came Ḥanoḵ. And Mahway said:"],
    "3:12": ["the fall of the giants", "out", "their glory, tell us whether", "days", "to our lives;", "concerning the", "and the three shoots that remained."],
    "3:13": ["And the voice said:"],
    "3:16": ["broken, and"],
    "3:18": ["come down;", "your errand and", "is upon", "go,", "and do not tarry.", "go down to the",
             "and to Ḥanoḵ", "deliver your message.\""],
    # ---- 4: Ḥanoḵ's tablet to Semjaza; the judgment ----
    "4:1": ["wrote", "written", "thus:", "greeting:", "only for the works of your hands shall you be judged, but for", "shall not escape;"],
    "4:2": ["will not escape, for they were defiled", "a heavenly mishpat."],
    "4:3": ["and"],
    "4:4": ["Your judgment is held back only"],
    "4:5": ["is a mishpat that has come"],
    "4:6": ["and turn,"],
    "4:7": ["And", "saying of Ḥanoḵ that", "or rely on them."],
    # ---- 5: Manichean: the giants' strife, the signs, Ḥanoḵ's message ----
    "5:1": ["Then the battle grew", "and every", "was fitted to the", "shot it was slain.",
            "the one who escaped;"],
    "5:2": ["has done"],
    "5:3": ["Sām:", "bound", "the day of judgment,", "like those", "for ever.", "told, so it shall be.",
            "shall escape"],
    "5:4": ["to search for", "he sought,", "hide."],
    "5:5": ["Then", "was angry, and", None],
    "5:8": ["stood", "upon the earth; and", "he gave. And he was", "and his cry went",
            "a word came down", "Sām, who took the tablet and"],
    "5:9": ["Sām", "battle,", "utter"],
    "5:10": ["Watchers", "of the garden."],
    "5:11": ["Then", "came and", "there is"],
    "5:13": ["and after the flood the earth shall bring forth", "the", "and", "shall come forth;"],
    "5:14": ["and the", "shall be abundant,", "plentiful."],
    # ---- 6: Manichean: the giants' boasts and proverbs; the Watchers' rule ----
    "6:1": ["In the house of the", "and the", "were held", "days, and", "they grew strong,", "were together, and",
            "let us go;", "is for"],
    "6:2": ["gathered", "and said:", "roar", "strength", "neck.", "colours", "held"],
    "6:3": ["flight of the"],
    "6:4": ["shining"],
    "6:6": ["rock", "beneath it."],
    "6:7": [None],
    "6:11": ["is great,"],
    "6:12": ["rose and", "I saw in my dream those who were judged."],
    "6:13": ["of the earth", "the judgment came upon them."],
    "6:14": ["And in those days", "of the sons of men", "were slain", "and the earth was laid waste."],
    "6:15": ["to the daughters of men"],
    "6:16": ["of their fathers"],
    "6:17": ["were their deeds;", "that they wanted they", "and"],
    "6:18": ["took men", "of the land,", "Watchers.", "bring them bread."],
}
