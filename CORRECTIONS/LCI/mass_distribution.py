"""Simple mass distribution visualization used for quick checks.

Generates a bar and pie chart of hard-coded subsystem masses and saves
two PNG files in the current directory.
"""

import matplotlib.pyplot as plt


# -----------------------
# Total mass
# -----------------------
m_mex = 18.23
m_magnet = 57.45
m_cable = 106.35
m_tot = m_mex + m_magnet + m_cable
m_mex_rel = m_mex / m_tot * 100
m_magnet_rel = m_magnet / m_tot * 100
m_cable_rel = m_cable / m_tot * 100

print("=== Masses ===\n")
print(f"Total mass:        {m_tot:.2f} kg; MEXICO CONVERTER: {m_mex_rel:.1f} %; MAGNET: {m_magnet_rel:.1f} %; CABLE: {m_cable_rel:.1f} %\n")
print(f"MEXICO CONVERTER:  {m_mex:.2f} kg")
print(f"MAGNET:            {m_magnet:.2f} kg")
print(f"CABLE:             {m_cable:.2f} kg")

# Mass values for each subsystem
labels = ['MEXICO CONVERTER', 'MAGNET', 'CABLE']
masses = [m_mex, m_magnet, m_cable]

# Bar chart
plt.figure(figsize=(8, 5))
plt.bar(labels, masses, color=['#4F81BD', '#C0504D', '#9BBB59'])
plt.ylabel('Mass (kg)')
plt.title('Mass distribution over subsystems and sections')
plt.tight_layout()
plt.savefig('mass_distribution_bar.png')

plt.show()
plt.close()  # Ensure the bar chart window is closed before showing the pie chart

# Pie chart
plt.figure(figsize=(6, 6))
plt.pie(
    masses,
    labels=labels,
    autopct='%1.1f%%',
    labeldistance=0.55,
    pctdistance=0.78,
    colors=['#4F81BD', '#C0504D', '#9BBB59']
)
plt.title(f'Mass distribution over subsystems and sections\nTotal mass: {m_tot:.2f} kg')
plt.tight_layout()
plt.savefig('mass_distribution_pie.png')
plt.show()  # Show the pie chart after saving
