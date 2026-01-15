#!/bin/bash
# Batch search FreeCEN for all My Tree surnames
# Searches each census year separately to avoid 1000 result limit

cd /Users/chris/dev-familytree
source venv/bin/activate

SURNAMES=(
    "Virgo"
    "Wrathall"
    "Worthington"
    "Tart"
    "Wood"
    "Heywood"
    "Parker"
    "Yates"
    "Price"
    "Metcalfe"
    "Goodall"
    "Barker"
    "Brown"
    "Davies"
    "Downham"
    "Eatock"
    "Ellwood"
    "Harrison"
    "Heyes"
    "Hollows"
    "Melling"
    "Morphet"
    "Narney"
    "Roberts"
    "Sabin"
    "Thompson"
)

YEARS=(1841 1851 1861 1871 1881 1891 1901)

echo "Starting batch FreeCEN search at $(date)"
echo "========================================"

total_surnames=${#SURNAMES[@]}
surname_count=0

for surname in "${SURNAMES[@]}"; do
    surname_count=$((surname_count + 1))
    echo ""
    echo "[$surname_count/$total_surnames] Processing: $surname"
    echo "========================================"

    for year in "${YEARS[@]}"; do
        echo "  Searching $surname in $year census..."

        # Run with --details to get relationship and occupation
        python scripts/search_freecen.py --surname "$surname" --year "$year" --details 2>&1 | grep -E "Parsed|CSV written|No results|Fetched|Completed"

        # Small delay between searches
        sleep 1
    done

    # Show progress
    if [ -f output/freecen_results.csv ]; then
        lines=$(wc -l < output/freecen_results.csv)
        echo "  Total records so far: $lines"
    fi

    # Delay between surnames
    sleep 2
done

echo ""
echo "========================================"
echo "Batch complete at $(date)"
if [ -f output/freecen_results.csv ]; then
    echo "Total records: $(wc -l < output/freecen_results.csv)"
fi
