#!/usr/bin/env bash
# Download reference corpus MIDI files for harmonium_lab.
#
# Sources:
#   - midiworld.com (classical, public domain)
#   - bushgrafts.com / Doug McKenzie Jazz Piano (free educational jazz MIDI)
#
# Usage:
#   ./scripts/download_corpus.sh
#   # or from harmonium_lab/:
#   make corpus

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REFS_DIR="$SCRIPT_DIR/../references"

download() {
    local dir="$1" filename="$2" url="$3"
    local path="$REFS_DIR/$dir/$filename"
    if [[ -f "$path" ]]; then
        echo "  [skip] $dir/$filename (exists)"
        return
    fi
    echo "  [get]  $dir/$filename"
    curl -sL --fail -o "$path" "$url" || {
        echo "  [FAIL] $dir/$filename — $url"
        rm -f "$path"
        return 1
    }
}

validate() {
    local path="$1"
    local header
    header=$(head -c 4 "$path" | xxd -p 2>/dev/null || echo "")
    if [[ "$header" != "4d546864" ]]; then
        echo "  [WARN] Invalid MIDI: $path"
        return 1
    fi
    return 0
}

echo "================================================"
echo "Downloading harmonium_lab reference corpus"
echo "================================================"
echo ""

# --- ambient: Satie + Debussy (slow, meditative, consonant) ---
echo "=== ambient (Satie, Debussy) ==="
mkdir -p "$REFS_DIR/ambient"
download ambient satie_gymnopedie1.mid    "https://www.midiworld.com/midis/other/c3/gymnop01.mid"
download ambient satie_gymnopedie2.mid    "https://www.midiworld.com/midis/other/c3/gymnop02.mid"
download ambient satie_gnossienne4.mid    "https://www.midiworld.com/midis/other/c3/gnossie4.mid"
download ambient satie_gnossienne5.mid    "https://www.midiworld.com/midis/other/c3/gnossie5.mid"
download ambient satie_sarabande1.mid     "https://www.midiworld.com/midis/other/c3/satsara1.mid"
download ambient debussy_reverie.mid      "https://www.midiworld.com/midis/other/c1/deb_rev.mid"
download ambient debussy_clair_de_lune.mid "https://www.midiworld.com/midis/other/debussy/clairdelune.mid"
echo ""

# --- jazz-calm: ballads from Doug McKenzie ---
echo "=== jazz-calm (Doug McKenzie ballads) ==="
mkdir -p "$REFS_DIR/jazz-calm"
download jazz-calm my_foolish_heart.mid    "https://www.bushgrafts.com/jazz/Midi%20site/MyFoolishHeart.mid"
download jazz-calm but_beautiful.mid       "https://www.bushgrafts.com/jazz/Midi%20site/But%20Beautifulsolo.mid"
download jazz-calm my_funny_valentine.mid  "https://www.bushgrafts.com/jazz/Midi%20site/funny%20val%20solo.mid"
download jazz-calm moon_river.mid          "https://www.bushgrafts.com/jazz/Midi%20site/Moon%20River%203.mid"
download jazz-calm when_i_fall_in_love.mid "https://www.bushgrafts.com/jazz/Midi%20site/When%20I%20Fall%20in%20Love.MID"
download jazz-calm lush_life.mid           "https://www.bushgrafts.com/jazz/Midi%20site/LushLife%20%20trio.mid"
echo ""

# --- jazz-upbeat: uptempo standards from Doug McKenzie ---
echo "=== jazz-upbeat (Doug McKenzie uptempo) ==="
mkdir -p "$REFS_DIR/jazz-upbeat"
download jazz-upbeat autumn_leaves.mid          "https://www.bushgrafts.com/jazz/Midi%20site/AutumnLeaves.mid"
download jazz-upbeat days_of_wine_and_roses.mid "https://www.bushgrafts.com/jazz/Midi%20site/DaysofWine.mid"
download jazz-upbeat stella_by_starlight.mid    "https://www.bushgrafts.com/jazz/Midi%20site/Stella%20solo.mid"
download jazz-upbeat beautiful_love.mid         "https://www.bushgrafts.com/jazz/Midi%20site/Beautiful%20Love%20(Doug%20McKenzie).mid"
download jazz-upbeat it_could_happen_to_you.mid "https://www.bushgrafts.com/jazz/Midi%20site/It%20Could%20Happen%20V2.mid"
echo ""

# --- training-backing: medium-tempo pieces for practice ---
echo "=== training-backing (practice-friendly) ==="
mkdir -p "$REFS_DIR/training-backing"
download training-backing autumn_in_new_york.mid "https://www.bushgrafts.com/jazz/Midi%20site/Autumn%20In%20NY.mid"
download training-backing easy_living.mid        "https://www.bushgrafts.com/jazz/Midi%20site/Easy%20Living%203.mid"
download training-backing skylark.mid            "https://www.bushgrafts.com/jazz/Midi%20site/Skylark%202.mid"
download training-backing over_the_rainbow.mid   "https://www.bushgrafts.com/jazz/Midi%20site/OverTheRainbowGM.mid"
download training-backing debussy_arabesque1.mid "https://www.midiworld.com/midis/other/c1/arabesqu.mid"
echo ""

# --- classical-simple: Bach inventions + simple keyboard ---
echo "=== classical-simple (Bach) ==="
mkdir -p "$REFS_DIR/classical-simple"
download classical-simple bach_invention1_bwv772.mid "https://www.midiworld.com/midis/other/bach/bwv772.mid"
download classical-simple bach_invention2_bwv773.mid "https://www.midiworld.com/midis/other/bach/bwv773.mid"
download classical-simple bach_invention3_bwv774.mid "https://www.midiworld.com/midis/other/bach/bwv774.mid"
download classical-simple bach_prelude_c_bwv846.mid  "https://www.midiworld.com/midis/other/bach/bwv846.mid"
download classical-simple bach_minuet_g_bwv841.mid   "https://www.midiworld.com/midis/other/bach/bwv841.mid"
echo ""

# --- Validate all downloads ---
echo "=== Validating MIDI files ==="
FAIL=0
for f in "$REFS_DIR"/*/*.mid; do
    if ! validate "$f"; then
        FAIL=$((FAIL + 1))
    fi
done

# --- Summary ---
echo ""
echo "=== Summary ==="
TOTAL=0
for cat in ambient jazz-calm jazz-upbeat training-backing classical-simple; do
    count=$(find "$REFS_DIR/$cat" -name "*.mid" | wc -l)
    echo "  $cat: $count files"
    TOTAL=$((TOTAL + count))
done
echo "  Total: $TOTAL files"

if [[ $FAIL -gt 0 ]]; then
    echo ""
    echo "WARNING: $FAIL file(s) failed validation!"
    exit 1
fi

echo ""
echo "Done! Run 'make profiles' to build reference profiles."
