"""
Role: Energy calculations for the Use phase (renewables and mixes).

Brief: Helper functions to compute energy-related IPE inputs such as
renewable mixes and energy allocation during the Use phase.
"""


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
eff_conv_values = [0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
# cable_length_scenarios_m = [140, 420, 700, "baseline", 1200, 1400, 1600]

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
hours_per_year = days_per_year * hours_per_day
T_op = lifetime_years * hours_per_year


def calculate_losses(efficiency, cable_length_km_value=cable_length_km):
    R_cable = R_cable_km * cable_length_km_value
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
        "cable_length_km": cable_length_km_value,
        "R_cable": R_cable,
        "P_magnet_avg": P_magnet_avg,
        "P_cable_avg": P_cable_avg,
        "P_conv_avg": P_conv_avg,
        "P_loss_avg": P_loss_avg,
        "E_loss_total_MJ": E_loss_total_MJ,
        "prop_loss_magnet": prop_loss_magnet,
        "prop_loss_cable": prop_loss_cable,
        "prop_loss_conv": prop_loss_conv,
    }


import logging


def print_single_result(result):
    logging.info("=== FCC-ee Corrector Circuit Use Phase ===\n")
    logging.info("Converter efficiency:     %.2f (%.0f%%)", result['efficiency'], result['efficiency'] * 100)
    logging.info("Cable length:             %.5f km", result['cable_length_km'])
    logging.info("Cable resistance:         %.3f ohm\n", result['R_cable'])
    logging.info("Average magnet losses:    %.2f W (%.2f%%)", result['P_magnet_avg'], result['prop_loss_magnet'] * 100)
    logging.info("Average cable losses:     %.2f W (%.2f%%)", result['P_cable_avg'], result['prop_loss_cable'] * 100)
    logging.info("Average converter losses: %.2f W (%.2f%%)", result['P_conv_avg'], result['prop_loss_conv'] * 100)
    logging.info("Total average losses:     %.2f W\n", result['P_loss_avg'])
    logging.info("Total operational time:   %.0f h", T_op)
    logging.info("Lifetime energy losses:   %.2f MJ", result['E_loss_total_MJ'])


# -----------------------
# DEFAULT RUN (single efficiency)
# -----------------------

single_result = calculate_losses(eff_conv)
print_single_result(single_result)


# # -----------------------
# # OPTIONAL SWEEP (EFFICIENCY SWEEP, descomentar para usar)
# #CONTROL+K+C COMENTAR
# #CONTROL+K+U DESCOMENTAR
# # -----------------------

# results = []
# for value in eff_conv_values:
#     results.append(calculate_losses(value))

# print("\n" + "=" * 90)
# print("SUMMARY: Total Lifetime Energy Losses vs Converter Efficiency")
# print("=" * 90)
# print(f"{'Efficiency':<15} {'Total Losses [MJ]':<20} {'Δ vs 80% [MJ]':<14} {'Δ vs 80% [%]':<14} {'Magnet [W]':<15} {'Cable [W]':<15} {'Converter [W]':<15} {'Magnet %':<10} {'Cable %':<10} {'Converter %':<12}")
# print("-" * 90)

# baseline_result = None
# for r in results:
#     if abs(r['efficiency'] - eff_conv) < 1e-9:
#         baseline_result = r
#         break
# if baseline_result is None:
#     baseline_MJ = calculate_losses(eff_conv)['E_loss_total_MJ']
# else:
#     baseline_MJ = baseline_result['E_loss_total_MJ']

# for result in results:
#     delta_MJ = result['E_loss_total_MJ'] - baseline_MJ
#     delta_pct = (delta_MJ / baseline_MJ) * 100
#     print(f"{result['efficiency']:.2f} ({result['efficiency']*100:>3.0f}%)   "
#           f"{result['E_loss_total_MJ']:>15.2f}   "
#           f"{delta_MJ:>10.2f}   "
#           f"{delta_pct:>10.2f}%   "
#           f"{result['P_magnet_avg']:>12.2f}    "
#           f"{result['P_cable_avg']:>12.2f}    "
#           f"{result['P_conv_avg']:>12.2f}    "
#           f"{result['prop_loss_magnet']:>8.2%}   "
#           f"{result['prop_loss_cable']:>8.2%}   "
#           f"{result['prop_loss_conv']:>10.2%}")

# print("=" * 90)

# min_losses = min(results, key=lambda x: x['E_loss_total_MJ'])
# max_losses = max(results, key=lambda x: x['E_loss_total_MJ'])
# loss_range = max_losses['E_loss_total_MJ'] - min_losses['E_loss_total_MJ']
# loss_change_percent = (loss_range / min_losses['E_loss_total_MJ']) * 100

# print(f"\nSensitivity Analysis:")
# print(f"  Minimum losses: {min_losses['E_loss_total_MJ']:.2f} MJ at eff_conv = {min_losses['efficiency']:.2f}")
# print(f"  Maximum losses: {max_losses['E_loss_total_MJ']:.2f} MJ at eff_conv = {max_losses['efficiency']:.2f}")
# print(f"  Range: {loss_range:.2f} MJ ({loss_change_percent:.1f}% variation)")


# -----------------------
# OPTIONAL SWEEP (cable length)
# -----------------------

# cable_length_scenarios_factor = [0.15, 0.4, 0.7, 1.0, 1.3, 1.65]
# cable_length_results = []

# for factor in cable_length_scenarios_factor:
#     cable_length_km_value = cable_length_km * float(factor)
#     cable_length_m_value = cable_length_km_value * 1000
#     scenario_label = "baseline" if factor == 1.0 else f"{factor:.0%} ({cable_length_m_value:.1f} m)"

#     result = calculate_losses(eff_conv, cable_length_km_value=cable_length_km_value)
#     result["cable_length_m"] = cable_length_m_value
#     result["cable_length_factor"] = factor
#     result["scenario_label"] = scenario_label
#     cable_length_results.append(result)

# print("\n" + "=" * 96)
# print("SUMMARY: Total Lifetime Energy Losses vs Cable Length")
# print("=" * 96)
# print(f"{'Scenario':<12} {'Cable Length [m]':<18} {'Total Losses [MJ]':<20} {'Magnet [W]':<15} {'Cable [W]':<15} {'Converter [W]':<15} {'Magnet %':<10} {'Cable %':<10} {'Converter %':<12}")
# print("-" * 96)

# for result in cable_length_results:
#     print(f"{result['scenario_label']:<12} {result['cable_length_m']:<18.1f} {result['E_loss_total_MJ']:>15.2f}       "
#           f"{result['P_magnet_avg']:>12.2f}    "
#           f"{result['P_cable_avg']:>12.2f}    "
#           f"{result['P_conv_avg']:>12.2f}    "
#           f"{result['prop_loss_magnet']:>8.2%}   "
#           f"{result['prop_loss_cable']:>8.2%}   "
#           f"{result['prop_loss_conv']:>10.2%}")

# print("=" * 96)

# numeric_results = [result for result in cable_length_results if result["scenario_label"] != "baseline"]
# if numeric_results:
#     min_losses = min(numeric_results, key=lambda x: x['E_loss_total_MJ'])
#     max_losses = max(numeric_results, key=lambda x: x['E_loss_total_MJ'])
#     loss_range = max_losses['E_loss_total_MJ'] - min_losses['E_loss_total_MJ']
#     loss_change_percent = (loss_range / min_losses['E_loss_total_MJ']) * 100

#     print(f"\nSensitivity Analysis:")
#     print(f"  Minimum losses: {min_losses['E_loss_total_MJ']:.2f} MJ at cable_length = {min_losses['cable_length_m']:.1f} m")
#     print(f"  Maximum losses: {max_losses['E_loss_total_MJ']:.2f} MJ at cable_length = {max_losses['cable_length_m']:.1f} m")
#     print(f"  Range: {loss_range:.2f} MJ ({loss_change_percent:.1f}% variation)")
