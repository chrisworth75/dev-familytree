#!/bin/bash
# Overnight shared match import script
# Created: 6 January 2026

cd /Users/chris/dev-familytree
source venv/bin/activate

LOG="/tmp/overnight_shared_import.log"

echo "============================================================" >> $LOG
echo "OVERNIGHT SHARED MATCH IMPORT" >> $LOG
echo "Started: $(date)" >> $LOG
echo "============================================================" >> $LOG

# Wait for current import to finish (check every 30 seconds)
echo "Waiting for current import to finish..." >> $LOG
while pgrep -f "import_shared_matches.py" > /dev/null; do
    sleep 30
done
echo "Current import finished at $(date)" >> $LOG

# Small delay to ensure clean state
sleep 10

# Check current stats
echo "" >> $LOG
echo "Pre-import stats:" >> $LOG
sqlite3 genealogy.db "SELECT COUNT(*) || ' total shared match records' FROM shared_match;" >> $LOG
sqlite3 genealogy.db "SELECT COUNT(DISTINCT match1_id) || ' matches with shared data' FROM shared_match;" >> $LOG

# Run import for 15-19 cM matches
echo "" >> $LOG
echo "Starting 15-19 cM import at $(date)" >> $LOG
echo "============================================================" >> $LOG

python scripts/import_shared_matches.py --min-cm 15 --delay 0.5 >> $LOG 2>&1

echo "" >> $LOG
echo "============================================================" >> $LOG
echo "OVERNIGHT IMPORT COMPLETE" >> $LOG
echo "Finished: $(date)" >> $LOG
echo "============================================================" >> $LOG

# Final stats
echo "" >> $LOG
echo "Post-import stats:" >> $LOG
sqlite3 genealogy.db "SELECT COUNT(*) || ' total shared match records' FROM shared_match;" >> $LOG
sqlite3 genealogy.db "SELECT COUNT(DISTINCT match1_id) || ' matches with shared data' FROM shared_match;" >> $LOG
