
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

# Optional sweep (descomenta para usar variaciones):
# eff_conv_values = [0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]

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

# Derived parameters
R_cable = R_cable_km * cable_length_km
hours_per_year = days_per_year * hours_per_day
T_op = lifetime_years * hours_per_year


def calculate_losses(efficiency):
    E_loss_total_Wh = 0.0
    P_magnet_avg = 0.0
    P_cable_avg = 0.0
    P_conv_avg = 0.0

    for phase in phases.values():
        t_phase = phase["years"] * hours_per_year
        I_phase = I_tt * phase["energy_ratio"]

        P_magnet = I_phase**2 * R_magnet
        P_cable = I_phase**2 * R_cable
        P_out = P_magnet + P_cable
        P_conv = P_out * (1 / efficiency - 1)
        P_loss = P_magnet + P_cable + P_conv

        E_loss_total_Wh += P_loss * t_phase

        weight = t_phase / T_op
        P_magnet_avg += P_magnet * weight
        P_cable_avg += P_cable * weight
        P_conv_avg += P_conv * weight

    P_loss_avg = P_magnet_avg + P_cable_avg + P_conv_avg
    E_loss_total_kWh = E_loss_total_Wh / 1000
    E_loss_total_MJ = E_loss_total_kWh * 3.6

    prop_loss_magnet = P_magnet_avg / P_loss_avg
    prop_loss_cable = P_cable_avg / P_loss_avg
    prop_loss_conv = P_conv_avg / P_loss_avg

    return {
        "efficiency": efficiency,
        "P_magnet_avg": P_magnet_avg,
        "P_cable_avg": P_cable_avg,
        "P_conv_avg": P_conv_avg,
        "P_loss_avg": P_loss_avg,
        "E_loss_total_MJ": E_loss_total_MJ,
        "prop_loss_magnet": prop_loss_magnet,
        "prop_loss_cable": prop_loss_cable,
        "prop_loss_conv": prop_loss_conv,
    }


def print_single_result(result):
    print("=== FCC-ee Corrector Circuit Use Phase ===\n")
    print(f"Converter efficiency:     {result['efficiency']:.2f} ({result['efficiency']*100:.0f}%)")
    print(f"Cable resistance:         {R_cable:.3f} ohm\n")
    print(f"Average magnet losses:    {result['P_magnet_avg']:.2f} W ({result['prop_loss_magnet']:.2%})")
    print(f"Average cable losses:     {result['P_cable_avg']:.2f} W ({result['prop_loss_cable']:.2%})")
    print(f"Average converter losses: {result['P_conv_avg']:.2f} W ({result['prop_loss_conv']:.2%})")
    print(f"Total average losses:     {result['P_loss_avg']:.2f} W\n")
    print(f"Total operational time:   {T_op:.0f} h")
    print(f"Lifetime energy losses:   {result['E_loss_total_MJ']:.2f} MJ")


# -----------------------
# DEFAULT RUN (single efficiency)
# -----------------------

single_result = calculate_losses(eff_conv)
print_single_result(single_result)


# -----------------------
# OPTIONAL SWEEP (descomentar para usar)
# -----------------------

# results = []
# for value in eff_conv_values:
#     results.append(calculate_losses(value))
#
# print("\n" + "=" * 90)
# print("SUMMARY: Total Lifetime Energy Losses vs Converter Efficiency")
# print("=" * 90)
# print(f"{'Efficiency':<15} {'Total Losses [MJ]':<20} {'Magnet [W]':<15} {'Cable [W]':<15} {'Converter [W]':<15}")
# print("-" * 90)
#
# for result in results:
#     print(f"{result['efficiency']:.2f} ({result['efficiency']*100:>3.0f}%)   "
#           f"{result['E_loss_total_MJ']:>15.2f}       "
#           f"{result['P_magnet_avg']:>12.2f}    "
#           f"{result['P_cable_avg']:>12.2f}    "
#           f"{result['P_conv_avg']:>12.2f}")
#
# print("=" * 90)
#
# min_losses = min(results, key=lambda x: x['E_loss_total_MJ'])
# max_losses = max(results, key=lambda x: x['E_loss_total_MJ'])
# loss_range = max_losses['E_loss_total_MJ'] - min_losses['E_loss_total_MJ']
# loss_change_percent = (loss_range / min_losses['E_loss_total_MJ']) * 100
#
# print(f"\nSensitivity Analysis:")
# print(f"  Minimum losses: {min_losses['E_loss_total_MJ']:.2f} MJ at eff_conv = {min_losses['efficiency']:.2f}")
# print(f"  Maximum losses: {max_losses['E_loss_total_MJ']:.2f} MJ at eff_conv = {max_losses['efficiency']:.2f}")
# print(f"  Range: {loss_range:.2f} MJ ({loss_change_percent:.1f}% variation)")
