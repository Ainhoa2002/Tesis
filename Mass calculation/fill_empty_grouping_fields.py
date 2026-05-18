#!/usr/bin/env python3
"""
Fill empty Section and Subsection values from the row above.
"""

import csv
from pathlib import Path


def fill_empty_grouping_fields(csv_path):
    """Fill empty Section/Subsection with values from previous row."""
    rows = []
    
    # Read current CSV
    with open(csv_path, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    # Fill empty values from previous row
    for i in range(1, len(rows)):
        current_row = rows[i]
        prev_row = rows[i - 1]
        
        # If Section is empty, take from previous row
        if not current_row.get('Section', '').strip():
            current_row['Section'] = prev_row.get('Section', '')
        
        # If Subsection is empty, take from previous row
        if not current_row.get('Subsection', '').strip():
            current_row['Subsection'] = prev_row.get('Subsection', '')
    
    # Write back CSV
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    return len(rows)


def main():
    csv_path = Path(r"c:\Users\alorzaga\Git\tesis\Mass calculation\inverter_power_card_component_parameters.csv")
    
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return
    
    print(f"Filling empty Section/Subsection values from previous rows...")
    count = fill_empty_grouping_fields(csv_path)
    
    print(f"✅ Processed {count} rows")
    print(f"Updated file: {csv_path}")


if __name__ == "__main__":
    main()
