import csv
def read_input_rows(path):

    """

    Lee el archivo CSV y devuelve una lista de diccionarios correspondientes a las filas donde Direction == "Input".

    """

    rows = []

    with open(path, newline='', encoding='utf-8') as f:

        reader = csv.DictReader(f)

        for row in reader:

            if row.get("Direction", "").strip() == "Input":

                rows.append(row)

    return rows


