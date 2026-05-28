"""
Role: Fill IPE columns for Mexico converter components using library mappings.

Brief: Specialized version for the Mexico converter components that populates
UUIDs and background references required for that converter's IPE files.
"""

import pandas as pd
import os
import argparse
import sys
import re
import logging

# interactive-safe output helper
_IS_TTY = sys.stdout.isatty()
# Purpose: Out.
def _out(msg: str, level: str = "info") -> None:
    if _IS_TTY:
        print(msg)
    else:
        getattr(logging, level)(msg)


# Purpose: Normalize key.
def normalize_key(val):
    """Remove quotes, all whitespace, and lowercase for robust matching."""
    if pd.isna(val):
        return ''
    return re.sub(r'\s+', '', str(val).replace('"', '').replace("'", '')).lower()

# Purpose: Find target files.
def find_target_files(root_dir, suffix="_ipe_flows_from_parameters.csv"):
    """Yield all CSV files ending with the given suffix under root_dir."""
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if f.endswith(suffix):
                yield os.path.join(dirpath, f)

# Purpose: Fill columns from library.
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
        logging.exception("Error reading %s", target_file)
        _out(f"Error reading {target_file}: {e}", level="error")
        return

    if key_col_target not in df.columns:
        _out(f"Warning: {target_file} has no column '{key_col_target}'. Skipping.", level="warning")
        return

    if key_col_lib not in lib_df.columns:
        _out(f"Library missing key column '{key_col_lib}'. Aborting.", level="error")
        logging.error("Library missing key column '%s'", key_col_lib)
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
        direction_val = str(row.get('Direction', '')).strip().lower()
        is_output_row = direction_val == 'output'

        # Output rows are intentional summary rows; do not try to fill/warn.
        if is_output_row:
            continue

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
        # Non-output rows are import inputs.
        if 'Direction' in df.columns:
            df.at[idx, 'Direction'] = 'Input'

    df.drop(columns=['_norm_key'], inplace=True)
    try:
        df.to_csv(target_file, index=False, encoding='utf-8')
        _out(f"Updated: {target_file}")
    except Exception as e:
        logging.exception("Error writing %s", target_file)
        _out(f"Error writing {target_file}: {e}", level="error")

    if missing_rows:
        _out(f"WARNING: The following rows in {target_file} could not be filled:", level="warning")
        for val in missing_rows:
            _out(f"  - {val}", level="warning")


# Purpose: Fill uuid provider from library.
def fill_uuid_provider_from_library(target_file, provider_df, key_col_target='Flow'):
    """Fill UUID_provider in one ipe file using provider library.

    Matching logic:
    - target Flow -> provider Ecoinvent_flow_reference (normalized)
    - copy provider UUID_provider into target UUID_provider

    Rules:
    - no warning for non-matching flows
    - do not overwrite output rows
    - return number of rows filled in this run
    """
    try:
        df = pd.read_csv(target_file, dtype=str, keep_default_na=False)
    except Exception as e:
        logging.exception("Error reading %s", target_file)
        _out(f"Error reading {target_file}: {e}", level="error")
        return 0

    if key_col_target not in df.columns:
        return 0

    provider_key_col = 'Ecoinvent_flow_reference'
    provider_uuid_col = 'UUID_provider'
    if provider_key_col not in provider_df.columns or provider_uuid_col not in provider_df.columns:
        _out(
            "Provider library missing required columns: "
            "Ecoinvent_flow_reference, UUID_provider",
            level="error",
        )
        logging.error("Provider library missing required columns: %s", provider_df.columns)
        sys.exit(1)

    if 'UUID_provider' not in df.columns:
        df['UUID_provider'] = ''

    provider_tmp = provider_df.copy()
    provider_tmp['_norm_key'] = provider_tmp[provider_key_col].apply(normalize_key)
    provider_dict = (
        provider_tmp.drop_duplicates('_norm_key')
        .set_index('_norm_key')[provider_uuid_col]
        .to_dict()
    )

    filled_count = 0
    for idx, row in df.iterrows():
        direction_val = str(row.get('Direction', '')).strip().lower()
        if direction_val == 'output':
            continue

        norm_key = normalize_key(row.get(key_col_target, ''))
        provider_uuid = str(provider_dict.get(norm_key, '')).strip()
        if provider_uuid == '':
            continue

        old_val = str(row.get('UUID_provider', '')).strip()
        if old_val == provider_uuid:
            continue

        df.at[idx, 'UUID_provider'] = provider_uuid
        filled_count += 1

    try:
        df.to_csv(target_file, index=False, encoding='utf-8')
    except Exception as e:
        logging.exception("Error writing %s", target_file)
        _out(f"Error writing {target_file}: {e}", level="error")
        return 0

    return filled_count

# Purpose: Main.
def main():
    parser = argparse.ArgumentParser(description='Fill columns in _ipe_flows_from_parameters CSV files using a library.')
    parser.add_argument('--library', default='LCI_CONNECTION/LCI/component_library_ecoinvent_uuid_map.csv',
                        help='Ruta al archivo CSV de la librería (por defecto: LCI_CONNECTION/LCI/component_library_ecoinvent_uuid_map.csv)')
    parser.add_argument('--provider-library', default='component_library_ecoinvent_uuid_provider_map.csv',
                        help='Path al CSV de provider map (default: component_library_ecoinvent_uuid_provider_map.csv)')
    parser.add_argument('--root', default='.',
                        help='Root directory to search for target files (default: current directory)')
    args = parser.parse_args()

    try:
        lib_df = pd.read_csv(args.library, dtype=str, keep_default_na=False)
        _out(f"Loaded library from {args.library}")
    except Exception as e:
        logging.exception("Error loading library %s", args.library)
        _out(f"Error loading library {args.library}: {e}", level="error")
        sys.exit(1)

    try:
        provider_df = pd.read_csv(args.provider_library, dtype=str, keep_default_na=False)
        _out(f"Loaded provider library from {args.provider_library}")
    except Exception as e:
        logging.exception("Error loading provider library %s", args.provider_library)
        _out(f"Error loading provider library {args.provider_library}: {e}", level="error")
        sys.exit(1)

    # Use the correct key column for the library
    lib_key_col = 'Ecoinvent_flow' if 'Ecoinvent_flow' in lib_df.columns else 'Flow'
    fill_cols = ['Flow', 'UUID', 'Unit', 'Amount', 'Direction', 'uuid']
    available_fill = [col for col in fill_cols if col in lib_df.columns]
    if not available_fill:
        _out("Library does not contain any of the required columns: Flow, UUID, Unit, Amount, Direction, uuid", level="error")
        logging.error("Library columns available: %s", lib_df.columns)
        sys.exit(1)

    target_key_col = 'Flow'
    count = 0
    provider_filled_total = 0
    for target_file in find_target_files(args.root):
        fill_columns_from_library(target_file, lib_df, key_col_lib=lib_key_col, key_col_target=target_key_col, fill_cols=available_fill)
        provider_filled_total += fill_uuid_provider_from_library(target_file, provider_df, key_col_target=target_key_col)
        count += 1

    _out(f"\nProcessed {count} file(s).")
    _out(f"number of flows that have provider: {provider_filled_total}")

if __name__ == '__main__':
    main()
