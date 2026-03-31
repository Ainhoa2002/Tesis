import pandas as pd
import os
import argparse
import sys
import re

def normalize_key(val):
    """Remove quotes, all whitespace, and lowercase for robust matching."""
    if pd.isna(val):
        return ''
    return re.sub(r'\s+', '', str(val).replace('"', '').replace("'", '')).lower()

def find_target_files(root_dir, suffix="_ipe_flows_from_parameters.csv"):
    """Yield all CSV files ending with the given suffix under root_dir."""
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if f.endswith(suffix):
                yield os.path.join(dirpath, f)

def fill_columns_from_library(target_file, lib_df, key_col_lib='Ecoinvent_flow', key_col_target='Flow', fill_cols=None):
    # Lista para guardar los flujos que no se pudieron rellenar
    missing_rows = []
    """
    Llena las columnas especificadas en el archivo target_file usando lib_df.
    """
    if fill_cols is None:
        fill_cols = ['Flow', 'UUID', 'Unit', 'Amount', 'Direction', 'uuid']

    try:
        df = pd.read_csv(target_file, dtype=str, keep_default_na=False)
    except Exception as e:
        print(f"Error reading {target_file}: {e}")
        return

    if key_col_target not in df.columns:
        print(f"Warning: {target_file} has no column '{key_col_target}'. Skipping.")
        return

    if key_col_lib not in lib_df.columns:
        print(f"Library missing key column '{key_col_lib}'. Aborting.")
        sys.exit(1)

    # Normalize keys for robust matching
    lib_df['_norm_key'] = lib_df[key_col_lib].apply(normalize_key)
    df['_norm_key'] = df[key_col_target].apply(normalize_key)

    # Build mapping from normalized key to library row
    lib_dict = lib_df.drop_duplicates('_norm_key').set_index('_norm_key')[fill_cols].to_dict('index')

    # Add missing columns to target
    for col in fill_cols:
        if col not in df.columns:
            df[col] = ''

    import difflib
    lib_keys = list(lib_dict.keys())
    for idx, row in df.iterrows():
        norm_key = row['_norm_key']
        matched = False
        if norm_key in lib_dict:
            lib_row = lib_dict[norm_key]
            matched = True
        else:
            # Fuzzy match: get the closest match if available
            close_matches = difflib.get_close_matches(norm_key, lib_keys, n=1, cutoff=0.7)
            if close_matches:
                lib_row = lib_dict[close_matches[0]]
                matched = True
            else:
                missing_rows.append(row[key_col_target])
                continue
        for col in fill_cols:
            # Only fill UUID if empty
            if col.lower() == 'uuid':
                if (col in df.columns and str(row.get(col, '')).strip() != ''):
                    continue  # Do not overwrite existing UUID
            if col in lib_row and pd.notna(lib_row[col]) and str(lib_row[col]).strip() != '':
                df.at[idx, col] = str(lib_row[col])
        # Always set Direction to Input
        if 'Direction' in df.columns:
            df.at[idx, 'Direction'] = 'Input'

    df.drop(columns=['_norm_key'], inplace=True)
    try:
        df.to_csv(target_file, index=False, encoding='utf-8')
        print(f"Updated: {target_file}")
    except Exception as e:
        print(f"Error writing {target_file}: {e}")

    if missing_rows:
        print(f"WARNING: The following rows in {target_file} could not be filled:")
        for val in missing_rows:
            print(f"  - {val}")

def main():
    parser = argparse.ArgumentParser(description='Fill columns in _ipe_flows_from_parameters CSV files using a library.')
    parser.add_argument('--library', default='LCI_CONNECTION/LCI/component_library_ecoinvent_uuid_map.csv',
                        help='Ruta al archivo CSV de la librería (por defecto: LCI_CONNECTION/LCI/component_library_ecoinvent_uuid_map.csv)')
    parser.add_argument('--root', default='.',
                        help='Root directory to search for target files (default: current directory)')
    args = parser.parse_args()

    try:
        lib_df = pd.read_csv(args.library, dtype=str, keep_default_na=False)
        print(f"Loaded library from {args.library}")
    except Exception as e:
        print(f"Error loading library {args.library}: {e}")
        sys.exit(1)

    # Use the correct key column for the library
    lib_key_col = 'Ecoinvent_flow' if 'Ecoinvent_flow' in lib_df.columns else 'Flow'
    fill_cols = ['Flow', 'UUID', 'Unit', 'Amount', 'Direction', 'uuid']
    available_fill = [col for col in fill_cols if col in lib_df.columns]
    if not available_fill:
        print("Library does not contain any of the required columns: Flow, UUID, Unit, Amount, Direction, uuid")
        sys.exit(1)

    target_key_col = 'Flow'
    count = 0
    for target_file in find_target_files(args.root):
        fill_columns_from_library(target_file, lib_df, key_col_lib=lib_key_col, key_col_target=target_key_col, fill_cols=available_fill)
        count += 1

    print(f"\nProcessed {count} file(s).")

if __name__ == '__main__':
    main()
