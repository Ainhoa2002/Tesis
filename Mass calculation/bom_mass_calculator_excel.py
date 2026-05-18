#!/usr/bin/env python3
"""
Mass Calculator for Power Converter BOM
Reads extracted BOM data and calculates component masses
Outputs formatted data ready to be imported back to Excel
"""

import csv
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

# Define density defaults by component type
DENSITY_DEFAULTS = {
    'PCB': 1.4,
    'IGBT': 1.3,
    'IC': 1.2,
    'CAPACITOR': 6.5,  # MLCC
    'FILM_CAP': 1.35,  # WIMA
    'ELECTROLYTIC': 2.0,
    'INDUCTOR': 4.0,
    'RESISTOR': 7.5,
    'DIODE': 2.2,
    'LED': 1.2,
    'TRANSISTOR': 1.2,
    'RELAY': 1.2,
    'DCDC': 2.5,
    'OTHER': 1.5
}

def extract_component_type(designator, description, part_number):
    """Determine component type from designator and description"""
    des_upper = str(designator).upper()
    desc_upper = str(description).upper() if description else ""
    pn_upper = str(part_number).upper() if part_number else ""
    
    if 'PCB' in des_upper or 'PCB' in desc_upper:
        return 'PCB'
    elif any(x in des_upper for x in ['Q', 'IGBT']):
        return 'IGBT'
    elif 'CAPACITOR' in desc_upper or 'CAP' in desc_upper:
        if 'FILM' in desc_upper or 'WIMA' in pn_upper or 'MKPF' in pn_upper or 'MKP' in pn_upper:
            return 'FILM_CAP'
        elif 'ELECT' in desc_upper or 'ELYT' in pn_upper:
            return 'ELECTROLYTIC'
        else:
            return 'CAPACITOR'
    elif 'INDUCTOR' in desc_upper or 'COIL' in desc_upper or any(x in des_upper for x in ['L', 'LR']):
        return 'INDUCTOR'
    elif 'RESIST' in desc_upper or any(x in des_upper for x in ['R', 'RN']):
        return 'RESISTOR'
    elif 'DIODE' in desc_upper or 'BZV' in pn_upper or 'SM712' in pn_upper:
        return 'DIODE'
    elif 'LED' in desc_upper or any(x in des_upper for x in ['LD']):
        return 'LED'
    elif 'TRANSISTOR' in desc_upper or 'T' in des_upper:
        return 'TRANSISTOR'
    elif 'RELAY' in desc_upper or 'IC' in des_upper and 'RELAY' in desc_upper:
        return 'RELAY'
    elif 'LC/DC' in desc_upper or 'DCDC' in desc_upper or 'TRV' in pn_upper:
        return 'DCDC'
    elif any(x in des_upper for x in ['IC', 'U']):
        return 'IC'
    else:
        return 'OTHER'

def get_density(component_type, density_min=None, density_max=None):
    """Get appropriate density for component type"""
    # If explicit density range provided, use average
    if density_min is not None and density_max is not None:
        try:
            return float((float(density_min) + float(density_max)) / 2)
        except (ValueError, TypeError):
            pass
    
    # Use default for type
    return DENSITY_DEFAULTS.get(component_type, DENSITY_DEFAULTS['OTHER'])

def calculate_mass_from_volume(volume_cm3, density):
    """Calculate mass from volume and density"""
    if volume_cm3 is None or volume_cm3 == 0:
        return None
    
    try:
        vol = float(volume_cm3)
        dens = float(density)
        return vol * dens
    except (ValueError, TypeError):
        return None

def parse_mass_value(mass_str):
    """Parse mass value from string format (e.g., '0.35-0.4' or '0.017' or numeric)"""
    if not mass_str:
        return None
    
    mass_str = str(mass_str).strip()
    
    # If it's a range like "0.35-0.4", take the average
    if '-' in mass_str and mass_str[0] != '-':  # Make sure it's not a negative number
        try:
            parts = mass_str.split('-')
            if len(parts) == 2:
                low = float(parts[0])
                high = float(parts[1])
                return (low + high) / 2
        except ValueError:
            pass
    
    # Try to parse as float
    try:
        return float(mass_str)
    except ValueError:
        return None

def round_mass(mass, decimals=4):
    """Round mass to specified decimals using Decimal for precision"""
    if mass is None:
        return None
    
    # Use Decimal for precise rounding
    d = Decimal(str(mass))
    if decimals == 0:
        quantize_str = '1'
    else:
        quantize_str = '0.' + '0' * (decimals - 1) + '1'
    
    return float(d.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP))

def process_bom(input_csv):
    """Process BOM and calculate masses"""
    results = []
    
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_idx, row in enumerate(reader, 2):
            try:
                designator = row.get('Designators', '').strip()
                manufacturer = row.get('Manufacturer', '').strip()
                part_number = row.get('Part_Number', '').strip()
                description = row.get('Description', '').strip()
                quantity = row.get('Quantity')
                
                # Dimensions and volume
                L = row.get('L_mm')
                W = row.get('W_mm')
                H = row.get('H_mm')
                volume = row.get('Volume_cm3')
                
                # Density
                density_min = row.get('Density_min')
                density_max = row.get('Density_max')
                
                # Existing mass info
                mass_existing = row.get('Mass_existing', '').strip()
                
                # Determine component type
                comp_type = extract_component_type(designator, description, part_number)
                
                # Get density value
                density = get_density(comp_type, density_min, density_max)
                
                # Calculate or parse mass
                mass_final = None
                mass_source = 'CALCULATED'
                
                # Priority 1: Parse existing mass value
                if mass_existing:
                    parsed = parse_mass_value(mass_existing)
                    if parsed is not None:
                        mass_final = parsed
                        mass_source = 'EXISTING'
                
                # Priority 2: Calculate from volume and density
                if mass_final is None and volume:
                    try:
                        vol = float(volume)
                        if vol > 0:
                            mass_final = calculate_mass_from_volume(vol, density)
                            mass_source = 'CALCULATED'
                    except (ValueError, TypeError):
                        pass
                
                # Round to appropriate precision
                if mass_final is not None:
                    # Different rounding rules
                    if comp_type == 'CAPACITOR' and mass_final < 0.01:
                        mass_final = round_mass(mass_final, 4)
                    elif comp_type == 'DIODE' or comp_type == 'LED' or comp_type == 'TRANSISTOR':
                        mass_final = round_mass(mass_final, 4)
                    else:
                        mass_final = round_mass(mass_final, 4)
                
                results.append({
                    'row_num': row_idx,
                    'designators': designator,
                    'manufacturer': manufacturer,
                    'part_number': part_number,
                    'description': description,
                    'quantity': quantity,
                    'L_mm': L if L else '',
                    'W_mm': W if W else '',
                    'H_mm': H if H else '',
                    'volume_cm3': volume if volume else '',
                    'density_min': density_min if density_min else '',
                    'density_max': density_max if density_max else '',
                    'density_used': density,
                    'mass_calculated': mass_final,
                    'mass_source': mass_source,
                    'component_type': comp_type,
                    'mass_existing': mass_existing
                })
                
            except Exception as e:
                print(f"Warning: Error processing row {row_idx}: {e}")
                continue
    
    return results

def write_output_csv(results, output_path):
    """Write results to CSV format ready for Excel import"""
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header matching Excel structure
        writer.writerow([
            'Section', 'Subsection', 'Designators', 'Manufacturer', 'Part Number', 
            'Description', 'Quantity', 'L (mm)', 'W (mm)', 'H (mm)', 'Volume (cm3)',
            'Density Min (g/cm3)', 'Density Max (g/cm3)', 'Density Used', 'Mass (g)',
            'Mass Source', 'Component Type', 'Notes'
        ])
        
        for result in results:
            writer.writerow([
                '',  # Section - fill manually
                '',  # Subsection - fill manually
                result['designators'],
                result['manufacturer'],
                result['part_number'],
                result['description'],
                result['quantity'] if result['quantity'] else '',
                result['L_mm'],
                result['W_mm'],
                result['H_mm'],
                result['volume_cm3'],
                result['density_min'],
                result['density_max'],
                result['density_used'],
                result['mass_calculated'] if result['mass_calculated'] is not None else '',
                result['mass_source'],
                result['component_type'],
                f"Original mass: {result['mass_existing']}" if result['mass_existing'] else ''
            ])

def print_summary(results):
    """Print calculation summary"""
    print("\n" + "="*100)
    print("MASS CALCULATION SUMMARY")
    print("="*100)
    
    total_mass = sum(r['mass_calculated'] for r in results if r['mass_calculated'] is not None)
    calculated_count = sum(1 for r in results if r['mass_source'] == 'CALCULATED')
    existing_count = sum(1 for r in results if r['mass_source'] == 'EXISTING')
    
    print(f"\nTotal components: {len(results)}")
    print(f"Masses calculated: {calculated_count}")
    print(f"Masses from existing data: {existing_count}")
    print(f"Total BOM mass: {total_mass:.4f} g\n")
    
    # Group by component type
    by_type = {}
    for r in results:
        ctype = r['component_type']
        if ctype not in by_type:
            by_type[ctype] = {'count': 0, 'mass': 0}
        by_type[ctype]['count'] += 1
        if r['mass_calculated']:
            by_type[ctype]['mass'] += r['mass_calculated']
    
    print("By component type:")
    for ctype in sorted(by_type.keys()):
        info = by_type[ctype]
        print(f"  {ctype:20s}: {info['count']:3d} components, {info['mass']:8.4f} g")
    
    print("\n" + "="*100 + "\n")

def main():
    input_csv = Path(r"c:\Users\alorzaga\Git\tesis\Mass calculation\bom_extracted.csv")
    output_csv = Path(r"c:\Users\alorzaga\Git\tesis\Mass calculation\bom_with_masses.csv")
    
    print("Processing BOM data...")
    results = process_bom(input_csv)
    
    print(f"Calculated masses for {len(results)} components")
    
    # Write output
    write_output_csv(results, output_csv)
    print(f"Output saved to: {output_csv}")
    
    # Print summary
    print_summary(results)

if __name__ == '__main__':
    main()
