#!/usr/bin/env bash
# Download reference corpus MIDI files for harmonium_lab.
#
# Sources:
#   - midiworld.com (classical, public domain MIDI transcriptions)
#   - bushgrafts.com / Doug McKenzie Jazz Piano (free educational jazz MIDI)
#
# Usage:
#   ./scripts/download_corpus.sh
#   # or from harmonium_lab/:
#   make corpus

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REFS_DIR="$SCRIPT_DIR/../references"
FAIL_COUNT=0

download() {
    local dir="$1" filename="$2" url="$3"
    local path="$REFS_DIR/$dir/$filename"
    if [[ -f "$path" ]]; then
        return
    fi
    echo "  [get]  $dir/$filename"
    curl -sL --fail --max-time 15 -o "$path" "$url" || {
        echo "  [FAIL] $dir/$filename"
        rm -f "$path"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        return 0
    }
}

validate_all() {
    local invalid=0
    for f in "$REFS_DIR"/*/*.mid; do
        [[ -f "$f" ]] || continue
        local header
        header=$(head -c 4 "$f" | xxd -p 2>/dev/null || echo "")
        if [[ "$header" != "4d546864" ]]; then
            echo "  [WARN] Invalid MIDI: $f"
            rm -f "$f"
            invalid=$((invalid + 1))
        fi
    done
    return $invalid
}

MW="https://www.midiworld.com/midis/other"
BG="https://www.bushgrafts.com/jazz/Midi%20site"

echo "================================================"
echo "Downloading harmonium_lab reference corpus"
echo "================================================"
echo ""

# ══════════════════════════════════════════════════════════════════
# AMBIENT: Slow, meditative, consonant, minimal movement
# Satie, Debussy slow works, Chopin nocturnes, slow Bach
# ══════════════════════════════════════════════════════════════════
echo "=== ambient (target: 25+ files) ==="
mkdir -p "$REFS_DIR/ambient"

# Satie
download ambient satie_gymnopedie1.mid    "$MW/c3/gymnop01.mid"
download ambient satie_gymnopedie2.mid    "$MW/c3/gymnop02.mid"
download ambient satie_gnossienne4.mid    "$MW/c3/gnossie4.mid"
download ambient satie_gnossienne5.mid    "$MW/c3/gnossie5.mid"
download ambient satie_sarabande1.mid     "$MW/c3/satsara1.mid"
download ambient satie_sarabande2.mid     "$MW/c3/satsara2.mid"
download ambient satie_sarabande3.mid     "$MW/c3/satsara3.mid"

# Debussy (slow/dreamy)
download ambient debussy_reverie.mid          "$MW/c1/deb_rev.mid"
download ambient debussy_clair_de_lune.mid    "$MW/debussy/clairdelune.mid"
download ambient debussy_arabesque1.mid       "$MW/c1/arabesqu.mid"

# Chopin Nocturnes (slow, lyrical)
download ambient chopin_nocturne_op9_1.mid    "$MW/chopin/chno0901.mid"
download ambient chopin_nocturne_op9_2.mid    "$MW/chopin/chno0902.mid"
download ambient chopin_nocturne_op15_1.mid   "$MW/chopin/chno1501.mid"
download ambient chopin_nocturne_op15_2.mid   "$MW/chopin/chno1502.mid"
download ambient chopin_nocturne_op27_1.mid   "$MW/chopin/chno2701.mid"
download ambient chopin_nocturne_op27_2.mid   "$MW/chopin/chno2702.mid"
download ambient chopin_nocturne_op32_1.mid   "$MW/chopin/chno3201.mid"
download ambient chopin_nocturne_op37_2.mid   "$MW/chopin/chno3702.mid"
download ambient chopin_nocturne_op48_2.mid   "$MW/chopin/chno4802.mid"
download ambient chopin_nocturne_op55_1.mid   "$MW/chopin/chno5501.mid"
download ambient chopin_nocturne_op55_2.mid   "$MW/chopin/chno5502.mid"
download ambient chopin_nocturne_op62_1.mid   "$MW/chopin/chno6201.mid"
download ambient chopin_nocturne_op62_2.mid   "$MW/chopin/chno6202.mid"

# Beethoven (slow movements)
download ambient beethoven_moonlight_mv1.mid  "$MW/beethoven/beet27m1.mid"
download ambient beethoven_pathetique_mv2.mid "$MW/beethoven/pathet2.mid"

# Jazz ballads (very slow, ambient character)
download ambient jazz_peace_piece.mid     "$BG/PeacePiece.mid"
download ambient jazz_danny_boy.mid       "$BG/Dannyboy.mid"
download ambient jazz_dreamsville.mid     "$BG/Dreamsville.mid"
download ambient jazz_come_sunday.mid     "$BG/comesun.mid"
echo ""

# ══════════════════════════════════════════════════════════════════
# JAZZ-CALM: Relaxed ballads, smooth voicings
# ══════════════════════════════════════════════════════════════════
echo "=== jazz-calm (target: 40+ files) ==="
mkdir -p "$REFS_DIR/jazz-calm"

download jazz-calm my_foolish_heart.mid       "$BG/MyFoolishHeart.mid"
download jazz-calm but_beautiful.mid          "$BG/But%20Beautifulsolo.mid"
download jazz-calm my_funny_valentine.mid     "$BG/funny%20val%20solo.mid"
download jazz-calm moon_river.mid             "$BG/Moon%20River%203.mid"
download jazz-calm when_i_fall_in_love.mid    "$BG/When%20I%20Fall%20in%20Love.MID"
download jazz-calm lush_life.mid              "$BG/LushLife%20%20trio.mid"
download jazz-calm a_ghost_of_a_chance.mid    "$BG/Aghostofachance.mid"
download jazz-calm a_nightingale_sang.mid     "$BG/Anighting.mid"
download jazz-calm alfie.mid                  "$BG/alfiepno.mid"
download jazz-calm answer_me_my_love.mid      "$BG/Answer%20me%20My%20Love.mid"
download jazz-calm blame_it_on_my_youth.mid   "$BG/Blameiton.mid"
download jazz-calm chelsea_bridge.mid         "$BG/Chelsea%20Bridge.mid"
download jazz-calm cinema_paradiso.mid        "$BG/cinema.mid"
download jazz-calm cry_me_a_river.mid         "$BG/Cry%20me%20a%20river.mid"
download jazz-calm danny_boy.mid              "$BG/Dannyboy.mid"
download jazz-calm day_dream.mid              "$BG/Day%20Dream.mid"
download jazz-calm deep_purple.mid            "$BG/DeepPurple.mid"
download jazz-calm detour_ahead.mid           "$BG/Detour%20ahead.mid"
download jazz-calm dont_explain.mid           "$BG/Don't%20Explain%20solo.mid"
download jazz-calm emily.mid                  "$BG/emily.mid"
download jazz-calm estate.mid                 "$BG/estate.mid"
download jazz-calm for_sentimental_reasons.mid "$BG/ForSentimentalReasons.mid"
download jazz-calm georgia_on_my_mind.mid     "$BG/Georgia.mid"
download jazz-calm hymn_to_freedom.mid        "$BG/Hymn%20To%20Freedom.mid"
download jazz-calm i_fall_in_love.mid         "$BG/I%20fall%20in%20Love%20Too%20Easily.mid"
download jazz-calm i_cover_the_waterfront.mid "$BG/I%20Cover%20the%20Waterfront%20-%20solo.mid"
download jazz-calm in_a_sentimental_mood.mid  "$BG/Inasent.mid"
download jazz-calm little_girl_blue.mid       "$BG/Little%20Girl%20Blue.mid"
download jazz-calm laura.mid                  "$BG/laura.mid"
download jazz-calm love_letters.mid           "$BG/love%20letters.mid"
download jazz-calm mood_indigo.mid            "$BG/Mood%20Indigo%20-%20solo.mid"
download jazz-calm moonlight_in_vermont.mid   "$BG/moonlightinvermont.mid"
download jazz-calm my_one_and_only_love.mid   "$BG/Myoneand.mid"
download jazz-calm my_romance.mid             "$BG/My%20Romance.mid"
download jazz-calm my_ship.mid                "$BG/MyShip.mid"
download jazz-calm old_folks.mid              "$BG/Old%20Folks.mid"
download jazz-calm once_upon_a_summertime.mid "$BG/Once%20upon%20a%20summertime.mid"
download jazz-calm prelude_to_a_kiss.mid      "$BG/Prelude%20to%20a%20kiss.mid"
download jazz-calm send_in_the_clowns.mid     "$BG/send%20in%20the%20clowns.mid"
download jazz-calm skylark.mid                "$BG/Skylark%202.mid"
download jazz-calm some_other_time.mid        "$BG/Some%20Other%20Time.mid"
download jazz-calm sophisticated_lady.mid     "$BG/SophisticatedLady.mid"
download jazz-calm soul_eyes.mid              "$BG/SoulEyessolo.mid"
download jazz-calm spring_is_here.mid         "$BG/Spring%20Is%20Here%20-%20Bill%20Evans%20chords.mid"
download jazz-calm stormy_weather.mid         "$BG/stormyweather.mid"
download jazz-calm the_peacocks.mid           "$BG/McKenzie-ThePeacocks.mid"
download jazz-calm this_nearly_was_mine.mid   "$BG/This%20nearly%20was%20mine.mid"
download jazz-calm time_remembered.mid        "$BG/Time%20remembered.mid"
download jazz-calm turn_out_the_stars.mid     "$BG/turnoutthestars.mid"
download jazz-calm warm_valley.mid            "$BG/Warmvalleysolo.mid"
download jazz-calm why_did_i_choose_you.mid   "$BG/whydidi.mid"
download jazz-calm youve_changed.mid          "$BG/youhavechanged.mid"
download jazz-calm young_and_foolish.mid      "$BG/Young%20and%20Foolish.mid"
echo ""

# ══════════════════════════════════════════════════════════════════
# JAZZ-UPBEAT: Energetic, active rhythms, higher harmonic tension
# ══════════════════════════════════════════════════════════════════
echo "=== jazz-upbeat (target: 35+ files) ==="
mkdir -p "$REFS_DIR/jazz-upbeat"

download jazz-upbeat autumn_leaves.mid            "$BG/AutumnLeaves.mid"
download jazz-upbeat days_of_wine_and_roses.mid   "$BG/DaysofWine.mid"
download jazz-upbeat stella_by_starlight.mid      "$BG/Stella%20solo.mid"
download jazz-upbeat beautiful_love.mid           "$BG/Beautiful%20Love%20(Doug%20McKenzie).mid"
download jazz-upbeat it_could_happen_to_you.mid   "$BG/It%20Could%20Happen%20V2.mid"
download jazz-upbeat all_the_things_you_are.mid   "$BG/AllTheThings%20V2.mid"
download jazz-upbeat alone_together.mid           "$BG/Alone%20Together.mid"
download jazz-upbeat blue_bossa_1.mid             "$BG/BlueBossa1GM.mid"
download jazz-upbeat blue_bossa_2.mid             "$BG/BlueBossa3GM.mid"
download jazz-upbeat broadway.mid                 "$BG/broadway.mid"
download jazz-upbeat by_myself.mid                "$BG/Bymyself.mid"
download jazz-upbeat caravan.mid                  "$BG/Caravan2.mid"
download jazz-upbeat carnival.mid                 "$BG/Carnival.mid"
download jazz-upbeat cubano_chant.mid             "$BG/Cubano%20Chant%202.mid"
download jazz-upbeat dancing_on_ceiling.mid       "$BG/DancingontheCeiling.mid"
download jazz-upbeat desafinado.mid               "$BG/Desafinado.mid"
download jazz-upbeat dolphin_dance.mid            "$BG/dolphindance3.mid"
download jazz-upbeat easy_to_love.mid             "$BG/EasytoLove2.mid"
download jazz-upbeat exactly_like_you.mid         "$BG/Exactly%20Like%20You.mid"
download jazz-upbeat falling_in_love_with_love.mid "$BG/Falling%20in%20Love%20with%20Love%20trio.mid"
download jazz-upbeat good_bait.mid                "$BG/goodbaitGM.mid"
download jazz-upbeat green_dolphin_street.mid     "$BG/Green%20Dolph%20solo.mid"
download jazz-upbeat have_you_met_miss_jones.mid  "$BG/Have%20You%20Met%20-%20duet.mid"
download jazz-upbeat i_love_you.mid               "$BG/ILoveYou.mid"
download jazz-upbeat indiana.mid                  "$BG/Indiana.mid"
download jazz-upbeat it_dont_mean_a_thing.mid     "$BG/Itdon'tmeanathing.mid"
download jazz-upbeat just_friends.mid             "$BG/justfrien%20solo.mid"
download jazz-upbeat lady_be_good.mid             "$BG/ladybegood.mid"
download jazz-upbeat manteca.mid                  "$BG/manteca.mid"
download jazz-upbeat milestones.mid               "$BG/milestones.mid"
download jazz-upbeat nardis.mid                   "$BG/Nardis.mid"
download jazz-upbeat pent_up_house.mid            "$BG/pentupHouse.mid"
download jazz-upbeat recardo_bossa.mid            "$BG/Recardo.mid"
download jazz-upbeat shiny_stockings.mid          "$BG/shinystockings.mid"
download jazz-upbeat take_the_a_train.mid         "$BG/taketheatrain.mid"
download jazz-upbeat there_is_no_greater_love.mid "$BG/thereisnogreaterlove.mid"
download jazz-upbeat there_will_never_be.mid      "$BG/There%20will%20never%20be%20another%20you.mid"
download jazz-upbeat witchcraft.mid               "$BG/Witchcraft.mid"
echo ""

# ══════════════════════════════════════════════════════════════════
# TRAINING-BACKING: Clear harmony, steady rhythm, practice-friendly
# Mix of medium-tempo jazz + simple classical
# ══════════════════════════════════════════════════════════════════
echo "=== training-backing (target: 25+ files) ==="
mkdir -p "$REFS_DIR/training-backing"

download training-backing autumn_in_new_york.mid   "$BG/Autumn%20In%20NY.mid"
download training-backing easy_living.mid          "$BG/Easy%20Living%203.mid"
download training-backing over_the_rainbow.mid     "$BG/OverTheRainbowGM.mid"
download training-backing come_rain_or_shine.mid   "$BG/Come%20Rain%20or%20Come%20Shine%20V1.mid"
download training-backing dearly_beloved.mid       "$BG/dearlybeloved.mid"
download training-backing easy_does_it.mid         "$BG/Easy%20does%20it.mid"
download training-backing give_me_simple_life.mid  "$BG/simplelife.mid"
download training-backing i_should_care.mid        "$BG/McKenzie-Ishouldcare2.mid"
download training-backing if_i_were_a_bell.mid     "$BG/IfIwere.mid"
download training-backing isnt_it_romantic.mid     "$BG/Isn_t_it_Romantic.mid"
download training-backing look_silver_lining.mid   "$BG/LookfortheSilverLining.mid"
download training-backing make_someone_happy.mid   "$BG/Make%20Someone%20Happy.mid"
download training-backing pure_imagination.mid     "$BG/Pure%20Imagination.mid"
download training-backing secret_love.mid          "$BG/McKenzie-secret%20love.mid"
download training-backing someday_my_prince.mid    "$BG/Some%20day%20My%20Prince.mid"
download training-backing sweet_lorraine.mid       "$BG/Sweetlorraine.mid"
download training-backing tea_for_two.mid          "$BG/Tea%20for%20two.MID"
download training-backing the_more_i_see_you.mid   "$BG/moreicu.mid"
download training-backing try_to_remember.mid      "$BG/Try%20To%20Remember.mid"
download training-backing two_for_the_road.mid     "$BG/Two%20For%20The%20Road%205.mid"
download training-backing yesterday.mid            "$BG/Yesterday.mid"

# Simple classical (clear structure)
download training-backing mozart_k545_mv1.mid      "$MW/mozart/mozk545a.mid"
download training-backing mozart_k545_mv2.mid      "$MW/mozart/mozk545b.mid"
download training-backing mozart_k331_mv1.mid      "$MW/mozart/mozk331a.mid"
download training-backing beethoven_fur_elise.mid  "$MW/beethoven/furelise.mid"
download training-backing bach_invention4_bwv775.mid "$MW/bach/bwv775.mid"
download training-backing bach_invention5_bwv776.mid "$MW/bach/bwv776.mid"
echo ""

# ══════════════════════════════════════════════════════════════════
# CLASSICAL-SIMPLE: Clear tonal structure, smooth voice leading
# Bach inventions, Mozart sonatas, Chopin waltzes, simple Beethoven
# ══════════════════════════════════════════════════════════════════
echo "=== classical-simple (target: 30+ files) ==="
mkdir -p "$REFS_DIR/classical-simple"

# Bach Inventions
download classical-simple bach_invention1_bwv772.mid "$MW/bach/bwv772.mid"
download classical-simple bach_invention2_bwv773.mid "$MW/bach/bwv773.mid"
download classical-simple bach_invention3_bwv774.mid "$MW/bach/bwv774.mid"
download classical-simple bach_invention4_bwv775.mid "$MW/bach/bwv775.mid"
download classical-simple bach_invention5_bwv776.mid "$MW/bach/bwv776.mid"
download classical-simple bach_prelude_c_bwv846.mid  "$MW/bach/bwv846.mid"
download classical-simple bach_prelude_cm_bwv847.mid "$MW/bach/bwv847.mid"
download classical-simple bach_prelude_cs_bwv848.mid "$MW/bach/bwv848.mid"
download classical-simple bach_minuet_g_bwv841.mid   "$MW/bach/bwv841.mid"

# Mozart Piano Sonatas (selected movements)
download classical-simple mozart_k281_mv1.mid  "$MW/mozart/mozk281a.mid"
download classical-simple mozart_k281_mv2.mid  "$MW/mozart/mozk281b.mid"
download classical-simple mozart_k309_mv1.mid  "$MW/mozart/mozk309a.mid"
download classical-simple mozart_k309_mv2.mid  "$MW/mozart/mozk309b.mid"
download classical-simple mozart_k310_mv2.mid  "$MW/mozart/mozk310b.mid"
download classical-simple mozart_k331_mv2.mid  "$MW/mozart/mozk331b.mid"
download classical-simple mozart_k332_mv1.mid  "$MW/mozart/mozk332a.mid"
download classical-simple mozart_k332_mv2.mid  "$MW/mozart/mozk332b.mid"
download classical-simple mozart_k333_mv1.mid  "$MW/mozart/mozk333a.mid"
download classical-simple mozart_k333_mv2.mid  "$MW/mozart/mozk333b.mid"
download classical-simple mozart_k545_mv1.mid  "$MW/mozart/mozk545a.mid"
download classical-simple mozart_k545_mv2.mid  "$MW/mozart/mozk545b.mid"

# Beethoven (simpler works)
download classical-simple beethoven_fur_elise.mid    "$MW/beethoven/furelise.mid"
download classical-simple beethoven_romance_f.mid    "$MW/beethoven/be_roman.mid"
download classical-simple beethoven_rondo_c.mid      "$MW/beethoven/brondo.mid"
download classical-simple beethoven_sonata9_mv2.mid  "$MW/beethoven/beeth9-2.mid"

# Chopin Waltzes + Etude Op.10 No.3
download classical-simple chopin_waltz_op18.mid      "$MW/chopin/chwa18.mid"
download classical-simple chopin_waltz_op64_1.mid    "$MW/chopin/chwa6401.mid"
download classical-simple chopin_waltz_op64_2.mid    "$MW/chopin/chwa6402.mid"
download classical-simple chopin_etude_op10_3.mid    "$MW/chopin/chet1003.mid"
download classical-simple chopin_etude_op10_6.mid    "$MW/chopin/chet1006.mid"
download classical-simple chopin_preludes_op28.mid   "$MW/chopin/chopop28.mid"
echo ""

# ══════════════════════════════════════════════════════════════════
# VALIDATE + SUMMARY
# ══════════════════════════════════════════════════════════════════
echo "=== Validating MIDI files ==="
validate_all || true

echo ""
echo "=== Summary ==="
TOTAL=0
for cat in ambient jazz-calm jazz-upbeat training-backing classical-simple; do
    count=$(find "$REFS_DIR/$cat" -name "*.mid" 2>/dev/null | wc -l)
    echo "  $cat: $count files"
    TOTAL=$((TOTAL + count))
done
echo "  ─────────────────"
echo "  Total: $TOTAL files"

if [[ $FAIL_COUNT -gt 0 ]]; then
    echo ""
    echo "WARNING: $FAIL_COUNT download(s) failed (may be temporary — re-run to retry)"
fi

echo ""
echo "Done! Run 'make profiles' to rebuild reference profiles."
