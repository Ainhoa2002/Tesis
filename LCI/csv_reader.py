import csv
"For reaing the lines that are input and output in the csv files"
def read_input_rows(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("Direction", "")).strip().lower() == "input": #lower for converting to lower case
                rows.append(row)
    return rows


def read_output_rows(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("Direction", "")).strip().lower() == "output":#lower for converting to lower case
                rows.append(row)
    return rows


def read_output_row(path):
    rows = read_output_rows(path)
    return rows[0] if rows else None

