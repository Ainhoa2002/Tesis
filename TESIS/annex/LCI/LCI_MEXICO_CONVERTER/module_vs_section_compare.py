#!/usr/bin/env python3
"""Compare module and section *_ipe_flows_from_parameters.csv files.

Creates a markdown report with ONLY_IN_MODULE, ONLY_IN_SECTION, AMOUNT_DIFFERENCES and PROVIDER_DIFFS.
Supports excluding module filename substrings (e.g. input modules like caen_els).
"""
from pathlib import Path
import csv
import argparse
import math
import re


def read_created_flows(path: Path):
    created = set()
    if not path.exists():
        return created
    with path.open(newline='', encoding='utf-8-sig') as f:
        for row in csv.reader(f):
            if row and row[0].strip():
                created.add(row[0].strip())
    return created


def to_float(text):
    try:
        return float(str(text).replace(',', '.'))
    except Exception:
        return 0.0


def load_totals(paths, created):
    totals = {}
    providers = {}
    rows_count = {}
    for path in paths:
        with path.open(newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get('Direction', '').strip().lower() != 'input':
                    continue
                unit = (r.get('Unit') or '').strip().strip('"')
                if unit.lower() == 'lu':
                    continue
                flow = (r.get('Flow') or '').strip().strip('"')
                if not flow or flow in created:
                    continue
                key = (flow, unit)
                val = to_float(r.get('Amount') or r.get('Total_mass_kg'))
                totals[key] = totals.get(key, 0.0) + val
                prov = (r.get('UUID_provider') or '').strip()
                if prov:
                    providers.setdefault(key, set()).add(prov)
                rows_count[key] = rows_count.get(key, 0) + 1
    return totals, providers, rows_count


def write_md(report_path: Path, only_in_module, only_in_section, amount_diffs, provider_diffs):
    def clean_cell(x):
        if x is None:
            return ''
        s = str(x)
        s = s.replace('|', '&#124;')
        s = s.replace('\n', ' ')
        return s

    def join_provs(provs):
        return ', '.join(provs) if provs else ''

    with report_path.open('w', encoding='utf-8') as f:
        f.write('# Module vs Section Mismatches (fixed)\n')
        f.write('\nComparison scope: input rows only, excluding `LU` and created-flows keys.\n\n')
        f.write('## Summary:\n\n')
        f.write(f'- ONLY_IN_MODULE: {len(only_in_module)}\n')
        f.write(f'- ONLY_IN_SECTION: {len(only_in_section)}\n')
        f.write(f'- AMOUNT_DIFFERENCES: {len(amount_diffs)}\n\n')

        if only_in_module:
            f.write('## Only in module files\n\n')
            f.write('| Flow | Unit | Amount | Source examples |\n')
            f.write('| --- | --- | ---: | --- |\n')
            for (flow, unit), (amt, samples) in sorted(only_in_module.items()):
                sample_str = ', '.join(samples[:3]) if samples else ''
                f.write(f'| {clean_cell(flow)} | {clean_cell(unit)} | {amt:.12g} | {clean_cell(sample_str)} |\n')
            f.write('\n')

        if amount_diffs:
            f.write('## Amount differences\n\n')
            f.write('| Flow | Unit | Module amount | Section amount | Delta |\n')
            f.write('| --- | --- | ---: | ---: | ---: |\n')
            # sort by absolute delta descending for easier triage
            for (flow, unit), (m, s, d) in sorted(amount_diffs.items(), key=lambda kv: abs(kv[1][2]), reverse=True):
                f.write(f'| {clean_cell(flow)} | {clean_cell(unit)} | {m:.12g} | {s:.12g} | {d:.12g} |\n')
            f.write('\n')

        if provider_diffs:
            f.write('## Provider differences (amounts equal)\n\n')
            f.write('| Flow | Unit | Amount | Module providers | Section providers |\n')
            f.write('| --- | --- | ---: | --- | --- |\n')
            for rec in provider_diffs:
                f.write('| {} | {} | {:0.12g} | {} | {} |\n'.format(
                    clean_cell(rec['flow']),
                    clean_cell(rec['unit']),
                    rec['amount'],
                    clean_cell(join_provs(rec['module_providers'])),
                    clean_cell(join_provs(rec['section_providers'])),
                ))
            f.write('\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', default='LCI/LCI_MEXICO_CONVERTER', help='base folder with _ipe_flows_from_parameters.csv files')
    p.add_argument('--exclude', action='append', default=[], help='module filename substring to exclude (can repeat)')
    p.add_argument('--out', default='LCI/LCI_MEXICO_CONVERTER/cutoff_module_vs_section_mismatch_report_fixed.md', help='output markdown report')
    p.add_argument('--tol', type=float, default=1e-9, help='tolerance for amount equality')
    args = p.parse_args()

    base = Path(args.base)
    created = read_created_flows(base / 'created_flows_uuid_map.csv')

    module_files = [p for p in base.glob('*_ipe_flows_from_parameters.csv') if not p.name.startswith('SECTION_')]
    # apply excludes by substring
    if args.exclude:
        lowered = [s.lower() for s in args.exclude]
        module_files = [p for p in module_files if not any(x in p.name.lower() for x in lowered)]

    section_files = sorted(base.glob('SECTION_*_ipe_flows_from_parameters.csv'))

    module_totals, module_prov, module_rows = load_totals(module_files, created)
    section_totals, section_prov, section_rows = load_totals(section_files, created)

    keys_module = set(module_totals.keys())
    keys_section = set(section_totals.keys())

    only_in_module = {}
    for key in sorted(keys_module - keys_section):
        only_in_module[key] = (module_totals[key], [p.name for p in module_files if key in _keys_in_file(p, created)])

    only_in_section = {}
    for key in sorted(keys_section - keys_module):
        only_in_section[key] = section_totals[key]

    amount_diffs = {}
    provider_diffs = []
    common = sorted(keys_module & keys_section)
    uuid_re = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
    def extract_uuids(iterable_of_strings):
        uuids = set()
        for s in iterable_of_strings:
            for m in uuid_re.findall(s or ''):
                uuids.add(m.lower())
        return sorted(uuids)

    for key in common:
        m = module_totals[key]
        s = section_totals[key]
        if not math.isclose(m, s, rel_tol=0.0, abs_tol=args.tol):
            amount_diffs[key] = (m, s, m - s)
        else:
            mprov = extract_uuids(module_prov.get(key, set()))
            sprov = extract_uuids(section_prov.get(key, set()))
            if mprov != sprov:
                provider_diffs.append({
                    'flow': key[0],
                    'unit': key[1],
                    'amount': m,
                    'module_providers': mprov,
                    'section_providers': sprov,
                    'module_rows': module_rows.get(key, 0),
                    'section_rows': section_rows.get(key, 0),
                })

    write_md(Path(args.out), only_in_module, only_in_section, amount_diffs, provider_diffs)


def _keys_in_file(path, created):
    # helper returning keys present in a file (flow, unit)
    keys = set()
    with path.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get('Direction', '').strip().lower() != 'input':
                continue
            unit = (r.get('Unit') or '').strip().strip('"')
            if unit.lower() == 'lu':
                continue
            flow = (r.get('Flow') or '').strip().strip('"')
            if not flow or flow in created:
                continue
            keys.add((flow, unit))
    return keys


if __name__ == '__main__':
    main()