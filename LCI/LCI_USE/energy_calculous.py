
# ---------------------------------------------------------
# FCC-ee Corrector Circuit – Use Phase Loss & Energy Model
# ---------------------------------------------------------
# ---------------------------------------------------------
# FCC-ee Corrector Circuit – Use Phase Loss & Energy Model
# FINAL PHYSICALLY CORRECT VERSION
# ---------------------------------------------------------

# -----------------------
# INPUT PARAMETERS
# -----------------------

I_tt = 10.0                 # Current at top energy [A]
R_magnet = 1.924            # Magnet resistance [Ohm]
R_cable_km = 1.95           # Cable resistance [Ohm/km]
cable_length_km = 0.97567   # Cable loop length [km]
eff_conv = 0.80             # Converter efficiency [-]

# -----------------------
# FCC-ee OPERATION PROFILE
# -----------------------

phases = {
    "Z":  {"energy_ratio": 46/183,  "years": 4},
    "W":  {"energy_ratio": 81/183,  "years": 2},
    "H":  {"energy_ratio": 120/183, "years": 3},
    "tt": {"energy_ratio": 1.0,     "years": 6},
}

# Operational parameters
days_per_year = 185
hours_per_day = 24
lifetime_years = 15

# -----------------------
# DERIVED PARAMETERS
# -----------------------

R_cable = R_cable_km * cable_length_km

hours_per_year = days_per_year * hours_per_day
T_op = lifetime_years * hours_per_year

# -----------------------
# LOSS CALCULATION
# -----------------------

E_loss_total_Wh = 0

P_magnet_avg = 0
P_cable_avg = 0
P_conv_avg = 0

for phase in phases.values():

    t_phase = phase["years"] * hours_per_year
    I_phase = I_tt * phase["energy_ratio"]

    # Joule losses
    P_magnet = I_phase**2 * R_magnet
    P_cable = I_phase**2 * R_cable

    # Converter losses
    P_out = P_magnet + P_cable
    P_conv = P_out * (1/eff_conv - 1)

    P_loss = P_magnet + P_cable + P_conv

    # Energy integration
    E_loss_total_Wh += P_loss * t_phase

    # Time-weighted averages
    weight = t_phase / T_op
    P_magnet_avg += P_magnet * weight
    P_cable_avg += P_cable * weight
    P_conv_avg += P_conv * weight

# -----------------------
# FINAL RESULTS
# -----------------------

P_loss_avg = P_magnet_avg + P_cable_avg + P_conv_avg

E_loss_total_kWh = E_loss_total_Wh / 1000
E_loss_total_MJ = E_loss_total_kWh * 3.6

prop_loss_magnet = P_magnet_avg / P_loss_avg
prop_loss_cable = P_cable_avg / P_loss_avg
prop_loss_conv = P_conv_avg / P_loss_avg

# -----------------------
# OUTPUT
# -----------------------

print("=== FCC-ee Corrector Circuit Use Phase ===\n")

print(f"Cable resistance:         {R_cable:.3f} ohm\n")

print(f"Average magnet losses:    {P_magnet_avg:} W ({prop_loss_magnet:})")
print(f"Average cable losses:     {P_cable_avg:} W ({prop_loss_cable:})")
print(f"Average converter losses: {P_conv_avg:} W ({prop_loss_conv:})")
print(f"Total average losses:     {P_loss_avg:} W\n")

print(f"Total operational time:   {T_op:.0f} h")
print(f"Lifetime energy losses:   {E_loss_total_MJ:.2f} MJ")
# ---------------------------------------------------------
# FCC-ee Corrector Circuit – Use Phase Loss & Energy Model
# FINAL PHYSICALLY CORRECT VERSION
# ---------------------------------------------------------

# -----------------------
# INPUT PARAMETERS
# -----------------------

I_tt = 10.0                 # Current at top energy [A]
R_magnet = 1.924            # Magnet resistance [Ohm]
R_cable_km = 1.95           # Cable resistance [Ohm/km]
cable_length_km = 0.97567   # Cable loop length [km]
eff_conv = 0.80             # Converter efficiency [-]

# -----------------------
# FCC-ee OPERATION PROFILE
# -----------------------

phases = {
    "Z":  {"energy_ratio": 46/183,  "years": 4},
    "W":  {"energy_ratio": 81/183,  "years": 2},
    "H":  {"energy_ratio": 120/183, "years": 3},
    "tt": {"energy_ratio": 1.0,     "years": 6},
}

# Operational parameters
days_per_year = 185
hours_per_day = 24
lifetime_years = 15

# -----------------------
# DERIVED PARAMETERS
# -----------------------

R_cable = R_cable_km * cable_length_km

hours_per_year = days_per_year * hours_per_day
T_op = lifetime_years * hours_per_year

# -----------------------
# LOSS CALCULATION
# -----------------------

E_loss_total_Wh = 0

P_magnet_avg = 0
P_cable_avg = 0
P_conv_avg = 0

for phase in phases.values():

    t_phase = phase["years"] * hours_per_year
    I_phase = I_tt * phase["energy_ratio"]

    # Joule losses
    P_magnet = I_phase**2 * R_magnet
    P_cable = I_phase**2 * R_cable

    # Converter losses
    P_out = P_magnet + P_cable
    P_conv = P_out * (1/eff_conv - 1)

    P_loss = P_magnet + P_cable + P_conv

    # Energy integration
    E_loss_total_Wh += P_loss * t_phase

    # Time-weighted averages
    weight = t_phase / T_op
    P_magnet_avg += P_magnet * weight
    P_cable_avg += P_cable * weight
    P_conv_avg += P_conv * weight

# -----------------------
# FINAL RESULTS
# -----------------------

P_loss_avg = P_magnet_avg + P_cable_avg + P_conv_avg

E_loss_total_kWh = E_loss_total_Wh / 1000
E_loss_total_MJ = E_loss_total_kWh * 3.6

prop_loss_magnet = P_magnet_avg / P_loss_avg
prop_loss_cable = P_cable_avg / P_loss_avg
prop_loss_conv = P_conv_avg / P_loss_avg

# -----------------------
# OUTPUT
# -----------------------

print("=== FCC-ee Corrector Circuit Use Phase ===\n")

print(f"Cable resistance:         {R_cable:.3f} ohm\n")

print(f"Average magnet losses:    {P_magnet_avg:.2f} W ({prop_loss_magnet:.2%})")
print(f"Average cable losses:     {P_cable_avg:.2f} W ({prop_loss_cable:.2%})")
print(f"Average converter losses: {P_conv_avg:.2f} W ({prop_loss_conv:.2%})")
print(f"Total average losses:     {P_loss_avg:.2f} W\n")

print(f"Total operational time:   {T_op:.0f} h")
print(f"Lifetime energy losses:   {E_loss_total_MJ:.2f} MJ")
# ---------------------------------------------------------
# FCC-ee Corrector Circuit – Use Phase Loss & Energy Model
# FINAL PHYSICALLY CORRECT VERSION
# ---------------------------------------------------------

# -----------------------
# INPUT PARAMETERS
# -----------------------

I_tt = 10.0                 # Current at top energy [A]
R_magnet = 1.924            # Magnet resistance [Ohm]
R_cable_km = 1.95           # Cable resistance [Ohm/km]
cable_length_km = 0.97567   # Cable loop length [km]
eff_conv = 0.80             # Converter efficiency [-]

# -----------------------
# FCC-ee OPERATION PROFILE
# -----------------------

phases = {
    "Z":  {"energy_ratio": 46/183,  "years": 4},
    "W":  {"energy_ratio": 81/183,  "years": 2},
    "H":  {"energy_ratio": 120/183, "years": 3},
    "tt": {"energy_ratio": 1.0,     "years": 6},
}

# Operational parameters
days_per_year = 185
hours_per_day = 24
lifetime_years = 15

# -----------------------
# DERIVED PARAMETERS
# -----------------------

R_cable = R_cable_km * cable_length_km

hours_per_year = days_per_year * hours_per_day
T_op = lifetime_years * hours_per_year

# -----------------------
# LOSS CALCULATION
# -----------------------

E_loss_total_Wh = 0

P_magnet_avg = 0
P_cable_avg = 0
P_conv_avg = 0

for phase in phases.values():

    t_phase = phase["years"] * hours_per_year
    I_phase = I_tt * phase["energy_ratio"]

    # Joule losses
    P_magnet = I_phase**2 * R_magnet
    P_cable = I_phase**2 * R_cable

    # Converter losses
    P_out = P_magnet + P_cable
    P_conv = P_out * (1/eff_conv - 1)

    P_loss = P_magnet + P_cable + P_conv

    # Energy integration
    E_loss_total_Wh += P_loss * t_phase

    # Time-weighted averages
    weight = t_phase / T_op
    P_magnet_avg += P_magnet * weight
    P_cable_avg += P_cable * weight
    P_conv_avg += P_conv * weight

# -----------------------
# FINAL RESULTS
# -----------------------

P_loss_avg = P_magnet_avg + P_cable_avg + P_conv_avg

E_loss_total_kWh = E_loss_total_Wh / 1000
E_loss_total_MJ = E_loss_total_kWh * 3.6

prop_loss_magnet = P_magnet_avg / P_loss_avg
prop_loss_cable = P_cable_avg / P_loss_avg
prop_loss_conv = P_conv_avg / P_loss_avg

# -----------------------
# OUTPUT
# -----------------------

print("=== FCC-ee Corrector Circuit Use Phase ===\n")

print(f"Cable resistance:         {R_cable} ohm\n")

print(f"Average magnet losses:    {P_magnet_avg} W ({prop_loss_magnet})")
print(f"Average cable losses:     {P_cable_avg} W ({prop_loss_cable})")
print(f"Average converter losses: {P_conv_avg} W ({prop_loss_conv})")
print(f"Total average losses:     {P_loss_avg} W\n")

print(f"Total operational time:   {T_op} h")
print(f"Lifetime energy losses:   {E_loss_total_MJ} MJ")
























""" # Electrical parameters
I = 6.572                    # Circuit current [A]
R_magnet = 1.924           # Magnet resistance [Ohm]
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
print(f"Magnet resistance:        {R_magnet} ohm")
print(f"Cable resistance:         {R_cable:.2f} ohm")
print(f"Magnet losses:        {P_magnet} W, {prop_loss_magnet} of total losses")
print(f"Cable losses:         {P_cable} W, {prop_loss_cable} of total losses")
print(f"Converter losses:     {P_conv} W, {prop_loss_conv} of total losses")
print(f"Total power losses:   {P_loss} W\n")

print(f"Total operational time: {T_op:.0f} h")
print(f"Lifetime energy losses: {E_loss_total_MJ} MJ")
 """