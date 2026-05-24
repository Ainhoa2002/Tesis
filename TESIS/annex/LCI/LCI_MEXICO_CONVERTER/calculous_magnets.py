import math

rho_cu = 8960          # kg/m^3
rho_fe = 4800
L_ind1 = 5.9             # m
d_ind1 = 2e-3            # m
L_t1 = 2*3.9 +0.4           # m
d_t1 = 0.8e-3            # m
L_t2 = 2*3*0.72+0.12             # m
d_t2 = 1.5e-3            # m



m_cu1 = rho_cu * L_ind1 * math.pi * (d_ind1/2)**2
m_cut1 = rho_cu * L_t1 * math.pi * (d_t1/2)**2
m_cut2 = rho_cu * L_t2 * math.pi * (d_t2/2)**2

m_fe1 = 0.338847
m_ny1 = 0.0012
m_ptfe1= 0.0016
m_plas1=0.0338

m_total1 = m_cu1 + m_fe1 + m_ny1 + m_ptfe1
per_cu1 = m_cu1 / m_total1 * 100
per_fe1 = m_fe1 / m_total1 * 100
per_ny1 = m_ny1 / m_total1 * 100
per_ptfe1 = m_ptfe1 / m_total1 * 100
per_plas1 = m_plas1 / m_total1 * 100
print(L_t1, d_t1, L_t2, d_t2)
print(m_cu1)
print(m_cut1)
print(m_cut2)
print(m_total1)
print(f"Copper: {per_cu1:.2f}%")
print(f"Steel: {per_fe1:.2f}%")
print(f"Nylon: {per_ny1:.2f}%")
print(f"PTFE: {per_ptfe1:.2f}%")
print(f"Plastic: {per_plas1:.2f}%")