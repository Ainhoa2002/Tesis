#!/usr/bin/env python3
"""
Import component parameters from Excel into CSV format.
Excel must have the same columns as the output CSV (Designators, Section, Subsection, etc.).
This allows building component databases directly in Excel and importing to the pipeline.
"""

import csv
from pathlib import Path
import openpyxl


def import_from_excel(workbook_path, output_csv, sheet_name="Sheet1"):
    """
    Import component parameters from Excel to CSV.
    
    Args:
        workbook_path: Path to Excel file with component data
        output_csv: Output CSV path
        sheet_name: Name of the sheet to read (default: Sheet1)
    
    Returns:
        Number of rows imported
    """
    wb = openpyxl.load_workbook(workbook_path, data_only=True)
    
    try:
        ws = wb[sheet_name]
    except KeyError:
        print(f"Error: Sheet '{sheet_name}' not found in workbook")
        print(f"Available sheets: {wb.sheetnames}")
        return 0
    
    # Read header from first row
    header_row = []
    for col in range(1, ws.max_column + 1):
        cell_value = ws.cell(1, col).value
        if cell_value is None:
            break
        header_row.append(str(cell_value).strip())
    
    if not header_row:
        print("Error: Excel file has no headers in first row")
        return 0
    
    print(f"Found {len(header_row)} columns: {', '.join(header_row[:5])}...")
    
    rows = []
    
    # Read data rows
    for r in range(2, ws.max_row + 1):
        row_data = {}
        has_content = False
        
        for col_idx, field_name in enumerate(header_row, start=1):
            cell_value = ws.cell(r, col_idx).value
            
            # Convert to string and strip whitespace
            if cell_value is not None:
                row_data[field_name] = str(cell_value).strip()
                has_content = True
            else:
                row_data[field_name] = ""
        
        # Skip completely empty rows
        if has_content:
            rows.append(row_data)
    
    # Write CSV with same headers as read from Excel
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=header_row)
        writer.writeheader()
        writer.writerows(rows)
    
    return len(rows)


def main():
    mass_calc_dir = Path(__file__).parent
    
    print("=" * 70)
    print("IMPORT COMPONENT PARAMETERS FROM EXCEL")
    print("=" * 70)
    print()
    
    # Ask for Excel file path
    while True:
        excel_input = input("📁 Excel file path (full path or filename in current directory): ").strip()
        if not excel_input:
            print("❌ Path cannot be empty")
            continue
        
        excel_path = Path(excel_input)
        
        # If relative path, try to find it in mass_calc_dir first
        if not excel_path.is_absolute():
            excel_path_candidate = mass_calc_dir / excel_input
            if excel_path_candidate.exists():
                excel_path = excel_path_candidate
        
        if excel_path.exists():
            break
        else:
            print(f"❌ File not found: {excel_path}")
            print(f"   Searched in: {mass_calc_dir if not Path(excel_input).is_absolute() else 'full path'}")
            continue
    
    # Ask for CSV name
    while True:
        csv_name = input("\n📄 Output CSV filename (e.g., fuse_card_component_parameters.csv): ").strip()
        if not csv_name:
            print("❌ Filename cannot be empty")
            continue
        
        if not csv_name.endswith(".csv"):
            csv_name = csv_name + ".csv"
        
        output_csv = mass_calc_dir / csv_name
        break
    
    # Ask for sheet name
    sheet_name = input("\n📋 Sheet name (default: Sheet1): ").strip()
    if not sheet_name:
        sheet_name = "Sheet1"
    
    print()
    print(f"Importing from: {excel_path}")
    print(f"Sheet: {sheet_name}")
    print(f"Output: {output_csv}")
    print()
    
    count = import_from_excel(excel_path, output_csv, sheet_name)
    
    print(f"\n✅ Imported {count} component rows")
    print(f"✅ Output saved to: {output_csv}")


if __name__ == "__main__":
    main()
