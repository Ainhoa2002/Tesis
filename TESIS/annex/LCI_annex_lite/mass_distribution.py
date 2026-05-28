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

import logging

logging.info("=== Masses ===\n")
logging.info("Total mass:        %.2f kg; MEXICO CONVERTER: %.1f %%; MAGNET: %.1f %%; CABLE: %.1f %%\n", m_tot, m_mex_rel, m_magnet_rel, m_cable_rel)
logging.info("MEXICO CONVERTER:  %.2f kg", m_mex)
logging.info("MAGNET:            %.2f kg", m_magnet)
logging.info("CABLE:             %.2f kg", m_cable)

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
