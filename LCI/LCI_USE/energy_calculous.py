
# ---------------------------------------------------------
# FCC-ee Corrector Circuit – Use Phase Loss & Energy Model
# ---------------------------------------------------------
# -----------------------
# INPUT PARAMETERS
# -----------------------

# Electrical parameters
I = 10.0                     # Circuit current [A]
R_magnet = 8.52e-3           # Magnet resistance [Ohm] (8.52 mOhm)
R_cable_km = 1.95            # Cable resistance [Ohm/km]
cable_length_km = 0.97567       # Total cable loop length [km]
eff_conv = 0.80  # Converter efficiency [-]
V_out=40    # Converter output voltage [V]        

# Operational parameters
days_per_year = 185          # Operating days per year
hours_per_day = 24           # Hours per day
lifetime_years = 15          # FCC-ee operational lifetime [years]

# -----------------------
# LOSS CALCULATIONS
# -----------------------

# Cable resistance
R_cable = R_cable_km * cable_length_km

# Magnet losses (Joule losses)
P_magnet = I**2 * R_magnet   # [W]

# Cable losses (Joule losses)
P_cable = I**2 * R_cable     # [W]

# Converter output power
#(if we knoe the output voltage) P_out = I*V_out# [W]
P_out = P_magnet + P_cable  # [W]

# Converter losses
P_conv = P_out * (1 / eff_conv - 1)  # [W]

# Total instantaneous losses
P_loss = P_magnet + P_cable + P_conv  # [W]
prop_loss_magnet = P_magnet / P_loss  # Proportion of losses relative to output power 
prop_loss_cable = P_cable / P_loss
prop_loss_conv = P_conv / P_loss
# -----------------------
# TIME INTEGRATION
# -----------------------

# Total operational time [h]
T_op = days_per_year * hours_per_day * lifetime_years

# Energy losses [kWh]
E_loss_total_kWh = P_loss * T_op / 1000
# Energy losses [MJ]
E_loss_total_MJ = E_loss_total_kWh * 3.6

# -----------------------
# RESULTS OUTPUT
# -----------------------

print("=== FCC-ee Corrector Circuit Use Phase ===\n")
print(f"Magnet resistance:        {R_magnet} W")
print(f"Cable resistance:         {R_cable:.2f} W")
print(f"Magnet losses:        {P_magnet} W, {prop_loss_magnet} of total losses")
print(f"Cable losses:         {P_cable} W, {prop_loss_cable} of total losses")
print(f"Converter losses:     {P_conv} W, {prop_loss_conv} of total losses")
print(f"Total power losses:   {P_loss} W\n")

print(f"Total operational time: {T_op:.0f} h")
print(f"Lifetime energy losses: {E_loss_total_MJ} MJ")
