"""
Unchanged since 2023-04-18
Unused
"""
from pathlib import Path

from bridgebots import build_lin_str, parse_pbn

sample_pbn_path = Path("/Users/frice/Downloads/day6.pbn")
deal_records = parse_pbn(sample_pbn_path)
print(f"parsed {len(deal_records)} deal records")
for deal_record in deal_records:
    print(build_lin_str(deal_record.deal, deal_record.board_records[0]))