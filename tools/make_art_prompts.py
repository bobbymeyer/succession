"""Generate `art/prompts.txt` and `art/filenames.txt` for a Krea-2 batch run.

One line per card in `cards.build_cards()`, same order in both files, so a
"read line N from each" workflow lines the prompt up with its output name.

Every card gets the same recipe, per the art brief:

* two on-flavour Hellenistic historical features,
* two strange fantasy features,
* one very weird surreal element,

wrapped in a framing that depends on the card kind -- courtiers are portraits,
action cards show two characters interacting, events are large-scale spectacle.
The world is Hellenistic Greek and the successor kingdoms (Macedonian,
Seleucid, Ptolemaic, Thracian, Scythian, Persian, Egyptian): explicitly not
Roman, not medieval, not modern, not futuristic.

    python tools/make_art_prompts.py          # writes the three files in art/

The images that come back are what `assets/` holds, and `art/filenames.txt` is
where its naming comes from: `tools/assets.py` checks every asset's number,
kind and slug against the card at that deck slot, so this file and that check
have to agree or the deck will not build.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from succession.cards import build_cards  # noqa: E402
from succession.enums import SEAT_ESTATE, CardKind  # noqa: E402
from tools import card_text  # noqa: E402

#: Shared positive tail. Purely an anchor for the period and the medium -- every
#: exclusion lives in `NEGATIVE` and is written to negative.txt instead, so no
#: prompt ever names a thing it does not want.
STYLE = (
    "Epic painted card illustration, oil on panel, dramatic cinematic light, "
    "deep saturated colour, fine brushwork, ornate detail, 2:3 vertical portrait "
    "aspect. Hellenistic Greek and successor-kingdom world: chiton, himation, "
    "chlamys, kausia, linothorax, bronze muscle cuirass, pteruges, Phrygian and "
    "Boeotian helms, sarissa and kopis, painted polychrome marble, Doric and "
    "Ionic columns, encaustic panel painting and Pergamene sculpture."
)

#: One shared negative prompt for the whole batch, written to negative.txt.
#: First three groups are the period exclusions from the brief; the last group
#: is ordinary render hygiene and can be cut without affecting the look.
NEGATIVE = (
    "Roman, toga, legionary, centurion, lorica segmentata, gladius, scutum, "
    "aquila standard, Latin inscription, Colosseum, Roman arch, "
    "medieval, knight, plate armour, chainmail, mail hauberk, great helm, "
    "heraldry, coat of arms, tabard, crusader, castle, gothic cathedral, "
    "pointed arch, stained glass, monk's habit, wimple, longsword, "
    "Renaissance, baroque dress, Viking, samurai, "
    "modern, contemporary clothing, suit, jeans, t-shirt, eyeglasses, "
    "wristwatch, wires, electric light, firearm, vehicle, "
    "futuristic, science fiction, cyberpunk, neon, robot, spacecraft, chrome, "
    "hologram, "
    "anime, cartoon, 3d render, cgi, photograph, watermark, signature, text, "
    "caption, logo, border frame, blurry, low resolution, malformed hands, "
    "extra fingers, extra limbs"
)

FRAMING = {
    "portrait": (
        "Epic character portrait, single figure, waist-up, facing the viewer, "
        "shallow depth of field"
    ),
    "interaction": (
        "Epic scene of two figures locked in one decisive interaction, "
        "full-length, vertical staging"
    ),
    "spectacle": (
        "Epic large-scale event, vast panoramic vertical composition, "
        "tiny human figures far below for scale"
    ),
    "throne": (
        "An empty throne, absolutely no person present, nobody seated, the "
        "unoccupied seat of office centred and waiting, vertical composition"
    ),
}

#: card name -> (two Hellenistic features, two fantasy features, one surreal element)
DETAILS: dict[str, tuple[str, str, str]] = {
    # --- Courtiers: Amonides, Old Gods, Imperial -----------------------------
    "Beloved of the Gods": (
        "a serene old priest in undyed wool himation with a saffron tainia fillet, "
        "the painted Doric porch of an ancestral temple behind him",
        "his irises are two small burning suns, and a slow ring of votive terracotta "
        "hands floats around his shoulders",
        "his own shadow has knelt on the floor and is worshipping him",
    ),
    "Keeper of the Long Peace": (
        "an old general in a green-patinaed bronze muscle cuirass, an olive wreath "
        "over grey hair, a sarissa laid unused across his knees",
        "the blade of his xiphos has been replaced by living olive wood in leaf, and "
        "bronze doves nest in the pteruges at his waist",
        "a whole war is being fought in miniature in his open palm, silent and "
        "the size of a coin",
    ),
    "Hand of the Oracle": (
        "a veiled priestess on a bronze Delphic tripod straddling a smoking fissure, "
        "laurel between her teeth",
        "her right hand is jointed marble veined with gold, and the vapour rising "
        "around her sets itself into readable archaic letters",
        "her mouth is sealed over with a smooth sheet of marble, and the room hears "
        "her anyway",
    ),
    "Weigher of Grain": (
        "a heavy-jawed grain factor in a saffron-bordered chiton, bronze balance in "
        "one fist, stamped grain sacks and a Ptolemaic measure at his hip",
        "one glowing wheat-ear in the near pan outweighs a mountain of grain in the "
        "far one, while bronze beetles crawl the sacks auditing them",
        "the grain pouring from his other hand falls upward into a hole in the sky",
    ),
    "Speaker of the Old Words": (
        "a scarred phalanx herald in a linothorax painted with archaic Greek "
        "lettering, a Boeotian helmet under his arm",
        "the letters crawl off his armour and hang burning in the air, and his "
        "breath leaves him as thin bronze script",
        "every soldier behind him has had their ears sewn shut with gold thread",
    ),
    "Wearer of the Golden Diadem": (
        "an opulent merchant-prince in a Tyrian-purple bordered himation, a gold "
        "Macedonian diadem with trailing ribbons, rings to the knuckle",
        "the diadem hovers a finger's width above his hair and turns slowly, while "
        "tetradrachms orbit his temples",
        "his face is flattened to a perfect mint-struck coin profile in full relief",
    ),
    "Tender of the Ancestral Flame": (
        "an elderly woman in a wool peplos guarding a bronze hearth-lamp, a painted "
        "family grave-stele glowing behind her",
        "the lamp flame is a small ancestor's face mid-sentence, and her hair is "
        "rising smoke",
        "her ribcage is a lit brazier, seen glowing through the skin",
    ),
    "Charioteer of the Sun Team": (
        "a wiry racer in a short exomis and leather harness, reins wound around his "
        "waist, the turning-post of a dusty hippodrome behind",
        "his four horses are made of molten daylight, and his whip is a drawn shaft "
        "of dawn",
        "the sun itself has his face, and it is looking back over its shoulder at him",
    ),
    # --- Courtiers: Mitreas, Mystery Cults, Imperial -------------------------
    "Golden Thumb": (
        "a money-changer at a marble table of tetradrachms and a black touchstone, "
        "a cult brand on his wrist, a lamp-lit stoa behind",
        "his thumb is solid gold to the knuckle, and every coin he has ever touched "
        "glows faintly in the pile",
        "his reflection in the polished table is counting a different, much larger heap",
    ),
    "Initiate of the Seven Veils": (
        "a barefoot initiate in seven layered translucent veils on black basalt steps, "
        "an Eleusinian torch guttering in one hand",
        "each veil shows a different face beneath it, and moths of beaten gold leaf "
        "circle the torch",
        "under the last veil there is a night sky with a road running away into it",
    ),
    "Crosser of Rivers": (
        "a soaked officer in a dripping chlamys with a crescent pelta shield, a "
        "pontoon of oiled skin-boats behind him",
        "the river stands upright in a wall beside him, and serpent-eels swim it "
        "wearing bronze bridles",
        "he is bone dry and the sky is soaking wet, dripping upward off the clouds",
    ),
    "Buyer of Cities": (
        "a silk-draped financier holding a model city in cupped hands, deed-papyri "
        "under his elbow, the Alexandrian harbour beyond",
        "the model city is putting out real smoke, and tiny citizens beg at the "
        "edges of his fingers",
        "a full-size city behind him is being folded up like cloth by hands that "
        "are not there",
    ),
    "Whisperer to the Serpent": (
        "a cult priest bent close to a great bronze-scaled serpent, ivy and a lamp "
        "of black oil, an underground shrine of rough-cut stone",
        "the serpent has human eyes and gilded fangs, and the priest's own tongue "
        "is forked",
        "the serpent's open mouth contains a lit colonnade with people walking in it",
    ),
    "Rider of the Long Road": (
        "a dust-caked scout in a kausia and travel chlamys with javelins at his "
        "knee, a herm milestone and a Nisean horse behind",
        "his horse's hooves leave burning prints on the road, and living maps shift "
        "and redraw themselves tattooed along his forearms",
        "the road behind him is rolling itself up like a carpet, carried by nobody",
    ),
    "Creditor of Kings": (
        "a severe banker holding a chain strung with royal seal-rings, a ledger "
        "scroll open, surrendered diadems heaped on the table as collateral",
        "the ledger's ink is alive and rewrites the debts as he reads, and a crowned "
        "shade kneels in the margin of the page",
        "dozens of kings' hands grow out of the wall behind him, holding out their rings",
    ),
    "Charioteer of the Seven Turns": (
        "a mystery-cult racer with seven scars on his chest, an initiate's veil over "
        "his racing harness, a torch-lit night hippodrome",
        "his chariot wheel is a bronze orrery of seven turning spheres, and his "
        "horses are cut out of night",
        "the racetrack is a single twisted ribbon that loops up through the stands "
        "and back",
    ),
    # --- Courtiers: Argaian, Imperial ---------------------------------------
    "Horse Breaker": (
        "a sun-blackened cavalry trainer in a worn exomis with a rawhide whip, "
        "breaking a half-wild stallion beside a stack of cavalry peltai",
        "the stallion has bronze hooves and a mane of smoke, and the rope in his "
        "fist is braided lightning",
        "the horse is standing on the sky while he stands on the ground, in the "
        "same picture",
    ),
    "Destroyer of Walls": (
        "a siege commander in a dented bronze cuirass, helmet under his arm, a "
        "burning helepolis siege tower leaning behind him",
        "his fists are cased in living stone, and the ram-heads on the engines are "
        "cast as screaming gods",
        "the breached wall is crumbling in reverse, its blocks flying back into "
        "place behind him",
    ),
    "Reader of Omens": (
        "an austere seer in an undyed himation beside a single aniconic lamp, no "
        "idols anywhere, a sky-chart unrolled on papyrus",
        "the birds overhead fly in readable letterforms, and his eyes are white "
        "with drifting constellations",
        "the papyrus is reading him: its letters have all turned to face outward",
    ),
    "Sword of the Assembly": (
        "a militant preacher in plain white with one arm raised, an Ionic civic "
        "stoa and a bronze law-stele behind him",
        "his voice leaves his mouth as a blade of white light, and the script on "
        "the stele burns as it is spoken",
        "the assembly listening to him are all identical, faceless, unfinished statues",
    ),
    "Founder of Markets": (
        "a pragmatic founder in a plain travel chlamys with surveying cord and "
        "marker stones, a new agora stoa half-raised behind",
        "market stalls sprout from the bare ground like plants, and bronze bees "
        "carry the weights to the scales",
        "the ground is laid out as a painted terracotta gameboard, grid and all",
    ),
    "Uncrowned Victor": (
        "a Panhellenic victor with victory ribbons tied on both arms, an olive "
        "wreath held in his hand instead of worn",
        "a phantom crown of light circles his head and refuses to settle, while his "
        "shadow on the wall is already wearing it",
        "everyone else in the picture is crowned, including the dogs and the horses",
    ),
    "Taker of the Citadel": (
        "the first man over the wall, blood-flecked linothorax, a scaling ladder at "
        "his back, an acropolis gate taken at dawn",
        "his banner burns with white fire, and the citadel's keys are melting in "
        "his fist",
        "he is holding a doorway in one hand, and a real staircase continues up "
        "through it",
    ),
    "Charioteer of the Iron Wheel": (
        "a grim charioteer in a plain white racing band, iron-rimmed wheels, dust "
        "to the knee, a cracked turning-post",
        "the black iron wheel keeps turning even at a standstill, and the horses "
        "wear blank bronze masks",
        "the same wheel is turning inside his chest, visible between the ribs",
    ),
    # --- Courtiers: no family, Imperial --------------------------------------
    "Silver Tongue": (
        "a slick young orator in a borrowed fine himation, mid-gesture of rhetoric, "
        "a painted stoa crowd behind him",
        "his tongue is molten silver at the tip, and his words turn into small coins "
        "as they leave his mouth",
        "the listeners' faces are slowly all becoming his face",
    ),
    "The Dog of the Agora": (
        "a Cynic philosopher on the marble agora steps in a ragged tribon cloak "
        "with a staff and a beggar's pera bag, strays around his feet",
        "the dogs have human eyes and wear bronze collars of office, and his lamp "
        "burns with black flame in full daylight",
        "he casts the shadow of a statue, plinth included",
    ),
    "Mender of Bones": (
        "a physician in a stained apron over an exomis with bronze surgical "
        "instruments laid out, an Asklepian snake-staff on the wall",
        "the broken bones on the table are knitting themselves with glowing gold, "
        "and a sealed jar beside her holds living mist",
        "her own left arm is transparent, showing the bones being set from the inside",
    ),
    "Ten Thousand Verses": (
        "a laurel-crowned rhapsode with a lyre and wine-stained fingers, a scroll "
        "spilling in coils across the floor",
        "the verses crawl off the scroll and lift away as small birds, and the lyre "
        "has a bronze mouth that sings with him",
        "the scroll is unrolling out of his own open throat",
    ),
    "Builder of the Long Aqueduct": (
        "a water-engineer sighting through a bronze diopter, lead siphon pipes and "
        "terracotta channel across a ravine in the Pergamene hills",
        "the water runs obediently uphill along the channel, and cut blocks float "
        "themselves into their courses",
        "the arches continue straight up into the clouds, and the water falls back "
        "down from there as rain",
    ),
    "Risen from the Ranks": (
        "a common soldier in an officer's cuirass that does not fit him, worn "
        "exomis beneath, calloused hands, his old phalanx file behind",
        "his old rank-tokens are burning off his belt, and a ladder of light rises "
        "under his heel",
        "he is stepping out of a statue of himself that is still cracking open "
        "behind him",
    ),
    "Coin-Counter of the Assembly": (
        "a civic treasurer at a pebble counting-board with sealed jars of "
        "tetradrachms and a stone accounts-stele",
        "the counting pebbles move themselves across the board, and a bronze "
        "ibis-headed automaton audits over his shoulder",
        "his eyes are two counting-boards with the pebbles sliding in them",
    ),
    "Widow of the Temple": (
        "an austere veiled widow in black wool before a plain white aniconic altar "
        "with a single lamp, no idols",
        "the flame leans toward her whenever she speaks, and her iron rings smoke "
        "with cold",
        "a second, taller shadow stands behind her wearing a bridal veil",
    ),
    # --- Courtiers: Barbarian ------------------------------------------------
    "Priest of the Two-Horned God": (
        "a shaven-headed Egyptian priest in pleated linen with a leopard-skin sash, "
        "in the painted hypostyle hall of a Ptolemaic temple",
        "the ram horns of Zeus-Ammon are living bone growing out of his own skull, "
        "and masked worshippers behind him have coal-bright eyes",
        "the sun sits between his horns like a struck bronze disc while it is full "
        "night everywhere else in the frame",
    ),
    "Master Mason": (
        "an Egyptian stoneworker in a linen kilt with copper chisel and mallet, "
        "granite dust in the air, a half-carved colossal head behind him",
        "the half-finished stone face is breathing, and his chisel cuts light "
        "instead of stone",
        "he is carving himself out of the same block, so there are two of him and "
        "one is unfinished",
    ),
    "Cataphract of the Iron Bridge": (
        "a Persian lancer armoured head to foot in iron scale with a faceless "
        "mask-helm and a kontos lance, his horse barded in matching scale",
        "the horse's scales glow like banked coals, and there is no face inside the "
        "mask, only cold white light",
        "the chain bridge behind him is building itself span by span as he rides "
        "off it",
    ),
    "Caravan-Lord of the Salt Road": (
        "a Persian caravan master in trousers and an embroidered kandys coat, "
        "camels loaded with slabs of rock salt on a blinding salt pan",
        "the salt crystals hum aloud and glow from within, and a bronze "
        "compass-bird perches on his wrist",
        "the caravan's shadow on the sand is a fleet of ships under full sail",
    ),
    "Hundred-Kill Rider": (
        "a Scythian horse-archer in a gold-plaqued coat and trousers with a gorytos "
        "bowcase, scalp-locks knotted on the bridle",
        "his arrows split into three in flight, and his kill-tally burns as fresh "
        "marks across his skin",
        "a hundred small watching faces surface in his horse's flank",
    ),
    "Blade for Any Banner": (
        "a Scythian mercenary in a mismatched kit: gold torc, trousers, a Thracian "
        "rhomphaia, a pelta repainted over half a dozen old devices",
        "the shield's painted device shifts to whichever army is paying, and his "
        "sword's edge is a thin line of nothing at all",
        "he casts five shadows, each one dressed in a different army's gear",
    ),
    "Warlord of the Iron Grove": (
        "a Germanic warlord with lime-washed spiked hair, a heavy torc and a long "
        "framea spear, standing in a sacred grove hung with taken shields",
        "the oaks are wrought black iron and weep rust instead of sap, and ravens "
        "of hammered bronze sit in them",
        "every empty trophy helm in the branches turns to follow him",
    ),
    "Master Swordsmith": (
        "a Germanic smith at a stone forge in a leather apron over trousers, a "
        "pattern-welded blade glowing in the tongs, charms of the old gods overhead",
        "the blade drinks the forge-light and goes black, and his anvil is a fallen "
        "meteorite still faintly warm",
        "the sparks rise and stay where they stop, as a new constellation",
    ),
    # --- Events --------------------------------------------------------------
    "Quarantine": (
        "the painted propylaea of a palace precinct barred with bronze and sealed "
        "with wax, sarissa guards at the gate, petitioners massed outside",
        "a dome of amber light stands over the inner court, and the courtiers "
        "caught inside are frozen mid-step like painted statues",
        "outside the dome all the shadows go on moving normally without their owners",
    ),
    "Siege": (
        "colossal helepolis siege towers and torsion catapults ringing a Hellenistic "
        "port city, phalanx lines drawn up under its painted marble walls",
        "the whole city is sealed inside a skin of grey glass, and the sea is "
        "stopped in mid-wave against the mole",
        "the birds hang motionless in the sky like pinned bronze ornaments",
    ),
    "Poisoning at the Feast": (
        "an enormous torch-lit symposium in a peristyle court, couches and garlands "
        "and kraters, guests recoiling from their cups in a spreading wave",
        "the wine in every kylix turns to black smoke with faces in it, and a bronze "
        "automaton cupbearer keeps calmly pouring",
        "one guest at the far end is placidly eating his own portrait off the wall",
    ),
    "Plague": (
        "a Hellenistic city under plague, bodies on the steps of a Doric sanctuary, "
        "pyre smoke rolling over the harbour, physicians masked in vinegar cloth",
        "a grey wind covered in closed eyes moves down the colonnade, and the "
        "Asklepios statues are weeping",
        "the sickness is visible as slow marble climbing people's legs and turning "
        "them into statuary where they stand",
    ),
    "Caravan": (
        "a vast trade caravan coming in through the painted gate of an Alexandrian "
        "agora, camels and mules, bales of spice, tax scribes with wax tablets",
        "one covered wagon carries a caged thunderstorm, and every lamp along the "
        "street lights itself as it passes",
        "the road it arrived on is still unrolling out from under the last camel",
    ),
    "Treasure Fleet": (
        "a great fleet of triremes and grain-ships entering harbour past a Pharos "
        "lighthouse, crowds packing the moles, gold and ivory coming ashore",
        "the sails are cloth-of-gold that pours coins as they are furled, and "
        "bronze sea-nymphs tow the lead hull in",
        "the lighthouse has bent down on its shaft like a long neck to inspect the cargo",
    ),
    "Debasement of the Coinage": (
        "a royal mint in uproar, hammer dies and blanks and toppled stacks of "
        "tetradrachms, money-changers rioting through the stoa",
        "the coins corrode to grey lead in people's hands, and the king's portrait "
        "on every one of them closes its eyes",
        "a river of coins pours out of the mint doors and runs uphill into the temple",
    ),
    "Famine": (
        "cracked farmland outside a Hellenistic polis, empty pithoi on their sides, "
        "a bread queue at the stoa, priests carrying a Demeter effigy for rain",
        "the standing wheat is grey glass and shatters at a touch, and hollow bronze "
        "locusts the size of dogs work the rows",
        "the fields are laid out as an enormous banquet table with a plate of dust "
        "set in every furrow",
    ),
    "Eclipse": (
        "a total eclipse over a Hellenistic acropolis, astronomers on the terrace "
        "with bronze geared calculators, crowds below beating bronze pans",
        "the shadow crosses the land as a wall of liquid night, and every statue "
        "turns its head to watch it come",
        "the sun's black disc is a hole with a staircase going down into it",
    ),
    "Meteor": (
        "an enormous meteor striking beyond a Hellenistic sanctuary, Doric columns "
        "toppling, priests prostrate, the sacred baetyl stone glowing on its altar",
        "the meteor is a burning bronze sphere cut with gear teeth, and its "
        "shockwave turns the air to drifting gold leaf",
        "the blast rearranges the city into a different city as it passes through, "
        "visibly, mid-frame",
    ),
    # --- Promotions ----------------------------------------------------------
    "Promotion": (
        "a diadochos king in a gold-bordered chlamys binding a white tainia ribbon "
        "around the brow of a kneeling courtier, in a painted Ionic throne-hall",
        "the ribbon burns with cold light as it is knotted, and the kneeling man's "
        "shadow stands up taller than he is",
        "his old lesser self is left standing empty beside him like a shed skin",
    ),
    "Battlefield Promotion": (
        "a scarred general pressing his own crested Phrygian helmet down onto a "
        "bloodied soldier's head amid a broken sarissa phalanx",
        "the crest catches fire as it lands, and the soldier's linothorax plates "
        "rearrange themselves into a bronze cuirass",
        "the fallen all around them sit up to applaud, politely and without a sound",
    ),
    "Consecration": (
        "an old high priest pouring scented oil over a kneeling initiate's head "
        "before a plain aniconic altar in a painted Doric temple",
        "the oil runs upward over the initiate's face and sets as gold leaf, and a "
        "column of moths rises through the smoke",
        "the painted figures on the temple wall step out of it to witness, still "
        "flat as paint",
    ),
    "Royal Charter": (
        "a Ptolemaic official pressing a royal seal into hot wax on a papyrus "
        "charter and handing it across a counting-table to a bowing merchant",
        "the seal brands a glowing sigil into the merchant's palm, and the charter "
        "grows a second page while it is being read",
        "an entire warehouse quietly arrives behind the merchant, already unloaded, "
        "from nowhere",
    ),
    "Acclamation": (
        "a herald in the agora roaring a plain-chitoned commoner's name while the "
        "man is hoisted off his feet, a rival watching from the temple steps",
        "the shout expands as a visible ring of bronze letters, and laurel sprouts "
        "between the paving stones where it passes",
        "the crowd behind them has one enormous shared face made out of all the "
        "small ones",
    ),
    # --- Demotions -----------------------------------------------------------
    "Demotion": (
        "a court chamberlain stripping the white tainia from a courtier's brow in a "
        "painted throne-hall while the household turns away",
        "the ribbon comes apart into ash-moths, and the man's ornaments drop off "
        "him like autumn leaves",
        "his name lifts off him as bronze letters and walks out of the room",
    ),
    "Heresy Accusation": (
        "a priest levelling an accusing finger at a robed cleric before a stone "
        "law-stele, witnesses clutching scrolls",
        "the accusation writes itself across the accused man's skin as it is spoken, "
        "and the lamp between them burns black",
        "his reflection in the temple's bronze doors is already recanting on its own",
    ),
    "Cashiering": (
        "an officer snapping a subordinate's sarissa across his knee in front of the "
        "drawn-up ranks, the man's cuirass already unbuckled",
        "the broken shaft bleeds light onto the sand, and the device peels off his "
        "shield and flies away",
        "his armour rusts to nothing in the two seconds the scene lasts, shown as a "
        "blur of centuries",
    ),
    "Charter Revoked": (
        "a royal agent tearing a sealed papyrus charter in half in a merchant's "
        "face, in a stoa of overturned counting-tables",
        "the two halves break into flocks of paper birds, and the coins on the table "
        "turn to coarse salt",
        "the merchant's warehouse in the background folds shut like a closing book",
    ),
    "Ostracism": (
        "two citizens at a voting table, one scratching a name onto a potsherd "
        "ostrakon and holding it up to the condemned man's face",
        "the scratched name burns on the sherd, and the condemned is going "
        "transparent from the feet up",
        "the city gate on the hillside physically rotates to turn its back on him",
    ),
    # --- Removals ------------------------------------------------------------
    "Assassination": (
        "a hooded figure in a dark himation driving a kopis into a courtier at the "
        "foot of a painted Ionic colonnade, a lamp knocked over on the flagstones",
        "the blade is a splinter of solid night, and the dying man's life leaves him "
        "as a small bronze bird",
        "their shadows on the wall show the two of them embracing instead",
    ),
    "Targeted Poisoning": (
        "a cup-bearer offering a kylix to a reclining guest at a private symposium, "
        "the two of them watching each other's eyes and nothing else",
        "a black flower turns slowly in the wine, and a small bronze taster-automaton "
        "already lies dead beside the krater",
        "a water-clock in the corner is draining upward",
    ),
    "Martyrdom": (
        "a white-robed believer kneeling willingly on temple steps as an executioner "
        "raises a kopis, a plain aniconic altar behind them",
        "light pours out of the kneeling man instead of blood, and the executioner's "
        "arms have gone to stone to the elbow",
        "every lamp in the watching crowd leans toward the kneeling man like grass "
        "in wind",
    ),
    "Battlefield Betrayal": (
        "two officers in the front rank, one driving a xiphos up under the other's "
        "cuirass as the phalanx presses forward around them",
        "the traitor's shield device is a closed eye that opens, and the victim's "
        "spear crumbles to ash in his grip",
        "the entire phalanx behind them is marching backwards in perfect order",
    ),
    "Bankruptcy": (
        "a creditor upending a debtor's strongbox over a counting-table while the "
        "debtor watches, a stoa of silent onlookers behind",
        "gold-leaf moths pour out of the box instead of coins, and the debtor's "
        "rings slide off fingers grown suddenly thin",
        "the debtor is visibly deflating like an emptied wineskin, clothes and all",
    ),
    "Mob Violence": (
        "a mob-leader dragging a fine-himationed notable down the temple steps by "
        "the shoulder, the crowd surging behind with torches",
        "faces move inside the torch flames, and the paving stones rise up to trip "
        "the falling man",
        "the statues along the temple roof lean out over the edge to watch, hands "
        "on their knees",
    ),
    # --- Defenses ------------------------------------------------------------
    "Patron Protection": (
        "an older patron stepping between an assassin and his client with one hand "
        "raised, in a lamp-lit peristyle court",
        "a shield of overlapping bronze leaves unfolds out of his sleeve, and the "
        "assassin's blade blooms into olive twigs",
        "the patron has no back: from behind he is a painted panel on a wooden strut",
    ),
    "Bodyguard": (
        "an enormous guard catching a spear-thrust aimed at his charge in his bare "
        "hand, his pelta up, the charge stumbling behind him",
        "the skin is bronze under the cut, and the spearhead bursts into black sand",
        "he is looking straight at the viewer, plainly bored, while everyone else "
        "is screaming",
    ),
    "Sanctuary": (
        "a priest filling a temple doorway with both arms out to stop an armed "
        "pursuer, a suppliant clinging to the altar behind him",
        "the threshold glows like a bar of white-hot iron the pursuer cannot cross, "
        "and the temple doors grow shut like healing skin",
        "the pursuer's weapon is already lying on the altar inside, though he is "
        "still holding it",
    ),
    "Deep Pockets": (
        "a merchant calmly pouring tetradrachms into an accuser's cupped hands "
        "across a marble table, both men seated and unhurried",
        "his purse has no bottom and the coins fall out of darkness, while the "
        "accuser's mouth seals over with gold",
        "the coins land as small closed doors instead of coins",
    ),
    "Popularity": (
        "a common man stepping back into a crowd that closes around him as a "
        "soldier reaches through for his arm",
        "the crowd fuses into a single wall of clasped hands, and the soldier's "
        "reaching arm turns to painted wood",
        "the whole crowd and the man share one continuous garment, all of them "
        "wearing the same enormous chiton",
    ),
    # --- Strips --------------------------------------------------------------
    "Castration": (
        "an officiant of Kybele in saffron cutting the woven family cord from a "
        "kneeling noble's waist with a bronze knife, tambourine and pine and a "
        "rough stone altar",
        "the cut cord is strung with small ancestral faces that go dark bead by "
        "bead, and the painted family portraits behind him blank themselves",
        "his name erases itself off the family stele while the carving tools lie "
        "untouched on the ground",
    ),
    "Excommunication": (
        "a high priest pressing an extinguished lamp against a kneeling man's "
        "forehead before the altar as the congregation turns its back",
        "the absent flame leaves a black brand shaped like an eye, and his "
        "devotional tattoos crawl off his body onto the floor",
        "a colossal pair of empty sandals behind the altar steps away and leaves",
    ),
    # --- Mutations -----------------------------------------------------------
    "Take Up the Sword": (
        "a veteran buckling a linothorax onto a scholar-courtier who is still "
        "holding a scroll, in an armoury of stacked peltai and sarissas",
        "the scroll hardens into a xiphos in his hand, and bronze pteruges grow "
        "from his belt like feathers",
        "his reflection in the shield is already a general forty years into a war",
    ),
    "Take Vows": (
        "a priest shaving a kneeling man's head and draping him in undyed wool "
        "before a temple hearth-fire",
        "the cut hair rises and becomes a ring of small flames, and his old clothes "
        "walk out of the room by themselves",
        "an unlit clay lamp inside his chest lights the moment the razor touches him",
    ),
    "Enter Trade": (
        "a merchant pressing a bronze balance and a seal-ring into a former "
        "soldier's hands across a counting-table in a lamp-lit stoa",
        "his sword melts and runs into the scale-pan as coins, and the ledger writes "
        "his new name in by itself",
        "the stoa is stacked to the roof beams with his future inventory, already there",
    ),
    "Lose Status": (
        "a chamberlain pulling a fine himation off a noble's shoulders and handing "
        "him a coarse exomis on the courtyard steps",
        "the fine cloth comes apart into a flock of gold-leaf scraps, and his rings "
        "run off his fingers like water",
        "everyone else in the picture has quietly stopped being able to see him",
    ),
    "Conversion": (
        "an initiate turning a kneeling man's face by the chin toward a second "
        "altar, two shrines standing side by side in one hall",
        "one faith's tattoos are peeling off him while the other's burn themselves "
        "on, and two gods' shadows overlap on the floor",
        "he sits on the picture's seam: his left half is painted in one temple's "
        "style and his right half in the other's",
    ),
    "Apostasy": (
        "a man tearing his own votive amulet off his neck in front of a horrified "
        "priest, on the steps of a painted temple",
        "the amulet's god-face crumbles to ash in mid-air, and every lamp in the "
        "portico gutters in a ring around him",
        "the sky above the temple is a blank unpainted panel with the underdrawing "
        "still showing",
    ),
    "Go Native": (
        "a Scythian chieftain fitting a gold torc onto an imperial officer who has "
        "traded his chlamys for trousers and a wolf pelt, at a mountain fire",
        "the new tattoos crawl into place on the officer's arms by themselves, and "
        "his Greek name falls out of his mouth as a cold bronze pebble",
        "the mountains behind them are wearing his discarded armour and standing up "
        "in it",
    ),
    "Assimilate": (
        "a court tutor draping a Greek himation over a tattooed barbarian and "
        "correcting his stance, in a gymnasium colonnade",
        "the tattoos sink under the skin like ink into water, and his broken accent "
        "hangs in the air as letters mending themselves",
        "his old self waits politely in the corner in trousers, holding his own "
        "tattoos folded like a shirt",
    ),
    "Adoption": (
        "a matriarch pressing a family signet and a cut lock of hair into a young "
        "man's hands while a blood kinsman steps back into the dark, a painted "
        "family stele behind them",
        "a new name carves itself into the stele while an older one fills with lead, "
        "and the ancestral masks on the wall open their eyes",
        "the young man's face slides into the family's shared profile like a coin "
        "being re-struck",
    ),
    # --- Pivot ---------------------------------------------------------------
    "Schismatic Event": (
        "two high priests on either side of a cracked altar, one burning a courtier's "
        "sealed oath-scroll while the other holds out a fresh sealed one, the "
        "congregation dividing behind them",
        "the crack in the altar runs on through the floor, the walls and the sky, and "
        "each half of the temple is lit by a different sun",
        "the worshippers split down the middle of their own bodies, each half walking "
        "a different way out",
    ),
    # --- Outmaneuver ---------------------------------------------------------
    "Outmaneuver": (
        "two courtiers facing each other across a petteia board of black and white "
        "pebbles, one calmly turning the whole board around, wine untouched beside them",
        "the playing pieces are tiny living courtiers, and the losing side's pieces "
        "bow toward the winner's hand",
        "the two players are the same man at two different ages, and the board they "
        "are playing on is the room they are sitting in",
    ),
}

#: The board. Each seat is drawn as the chair itself, empty, surrounded by the
#: instruments of the office it stands for -- the card is a place to put a
#: courtier, so the art must not already have one sitting in it.
SEAT_DETAILS: dict[str, tuple[str, str, str]] = {
    "Archpriest": (
        "an empty high-backed throne of ivory and cedar on a temple dais, its "
        "arms worn smooth by generations of hands, a bronze censer smoking beside it",
        "the throne's back is a pair of folded bronze wings, and the censer smoke "
        "holds the shape of a seated figure who is not there",
        "the empty chair's own shadow has knelt on the floor in front of it",
    ),
    "Oracle": (
        "an empty tripod seat of blackened bronze standing over a cleft in bare "
        "rock, laurel scattered across the stone floor",
        "vapour rising through the tripod freezes into hanging ribbons of glass, "
        "each ribbon showing a different sky",
        "the chasm beneath the seat is full of stars instead of darkness",
    ),
    "Lord General": (
        "an empty campaign chair of iron and stretched hide on a field of snapped "
        "sarissas, a bronze muscle cuirass propped against its leg",
        "the chair is assembled entirely from captured spears, and a map of a war "
        "burns slowly across its seat without ever being consumed",
        "the folding stool casts the shadow of an entire army",
    ),
    "Captain of the Guard": (
        "an empty stone seat in a palace antechamber, a tall shield and a sheathed "
        "kopis leaned against the wall on either side of it",
        "the shields ranked along the corridor have open watching eyes, and the "
        "seat's armrests end in bronze hands still gripping",
        "every doorway in the corridor behind the chair opens onto the same doorway",
    ),
    "Keeper of the Treasury": (
        "an empty seat of dark oiled wood behind a counting-table, bronze scales "
        "and stacked tetradrachms, ledgers racked on the wall",
        "the chair's legs are struck coins fused into columns, and the scales hang "
        "level weighing light against light",
        "coins pour upward off the floor into a jar that never fills",
    ),
    "Master of the Market": (
        "an empty overseer's chair on a stone platform above an emptied agora, "
        "measuring vessels and a standard weight chained to its arm",
        "the awnings over the stalls below are woven from trade routes drawn in "
        "coloured thread, and the standard weight floats a finger above its chain",
        "every stall in the market below is a reflection of the same single stall",
    ),
    "Voice of the People": (
        "an empty speaker's seat of plain limestone at the top of the assembly "
        "steps, a worn rostrum stone set before it",
        "the amphitheatre behind is filled with cloaks that hold their shape with "
        "nobody inside them, all leaning forward to listen",
        "the chair is the only thing in the scene casting sound where it should "
        "cast a shadow",
    ),
}

#: The shared negative cannot exclude people -- forty of the cards are
#: portraits. The seats are the opposite problem: a model shown a throne will
#: put somebody on it unless told twice, so they get their own negative, which
#: is the shared one plus everything that means "occupied".
SEAT_NEGATIVE_EXTRA = (
    "person, people, figure, human, man, woman, king, queen, emperor, priest, "
    "soldier, crowd in foreground, seated figure, enthroned ruler, portrait, "
    "face, hands on the armrests, occupied seat, someone sitting"
)

KIND_FRAMING = {
    CardKind.COURTIER: "portrait",
    CardKind.EVENT: "spectacle",
}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def build_lines() -> tuple[list[str], list[str]]:
    prompts: list[str] = []
    filenames: list[str] = []
    seen: set[str] = set()

    for card in build_cards():
        if card.name in seen:
            continue  # extra Outmaneuver copies share one illustration
        seen.add(card.name)

        try:
            historical, fantastic, surreal = DETAILS[card.name]
        except KeyError:  # pragma: no cover - guard for new cards
            raise SystemExit(f"No art details written for card: {card.name!r}")

        framing = FRAMING[KIND_FRAMING.get(card.kind, "interaction")]
        prompts.append(
            f"{framing}. {historical}. {fantastic}. {surreal}. {STYLE}"
        )
        n = len(filenames) + 1
        filenames.append(f"{n:02d}_{slug(card.kind.value)}_{slug(card.name)}")

    # The seat cards come after the agendas in the printed order, and the art
    # is numbered to match the slot it lands in. The agendas are the gap: they
    # are set type on parchment and have no illustration to generate.
    start = len(filenames) + len(card_text.AGENDA_TEXT) + 1
    for offset, seat in enumerate(SEAT_ESTATE):
        historical, fantastic, surreal = SEAT_DETAILS[seat.value]
        prompts.append(
            f"{FRAMING['throne']}. {historical}. {fantastic}. {surreal}. {STYLE}"
        )
        filenames.append(f"{start + offset:02d}_seat_{slug(seat.value)}")

    return prompts, filenames


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "art"
    out.mkdir(parents=True, exist_ok=True)
    prompts, filenames = build_lines()
    (out / "prompts.txt").write_text("\n".join(prompts) + "\n", encoding="utf-8")
    (out / "filenames.txt").write_text("\n".join(filenames) + "\n", encoding="utf-8")
    # One line, shared by every prompt. If your loader reads the negative file
    # line by line alongside the positives, repeat it 84 times:
    #   yes "$(cat art/negative.txt)" | head -n $(wc -l < art/prompts.txt) > batch.txt
    (out / "negative.txt").write_text(NEGATIVE + "\n", encoding="utf-8")
    (out / "negative-seats.txt").write_text(
        NEGATIVE + ", " + SEAT_NEGATIVE_EXTRA + "\n", encoding="utf-8"
    )
    print(
        f"wrote {len(prompts)} prompts, {len(filenames)} filenames, "
        f"2 negatives (the seats need their own)"
    )


if __name__ == "__main__":
    main()
