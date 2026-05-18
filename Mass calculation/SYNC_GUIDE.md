# SINCRONIZACIÓN Y VINCULACIÓN DE DATOS
## Cómo mantener todo sincronizado después de cambios

---

## 🔗 Flujo de Sincronización

```
Excel Original (Desktop)
        ↓ (Extract nuevos datos)
        ↓
CSV Extraído
        ↓ (Re-calcular masas)
        ↓
CSV con Masas Calculadas
        ↓ (Escribir)
        ↓
BoM_UPDATED.xlsx ✓
```

---

## 🚀 Cómo Sincronizar Después de Cambios

### OPCIÓN 1: Sincronización Automática Rápida ⭐ (RECOMENDADA)

Después de hacer cambios en **cualquier** Excel, ejecuta:

```powershell
cd "c:\Users\alorzaga\Git\tesis"
python "Mass calculation\auto_sync.py"
```

**Esto automáticamente:**
1. Detecta qué archivos cambiaron
2. Re-extrae datos del Excel original
3. Re-calcula todas las masas
4. Actualiza BoM_UPDATED.xlsx
5. Te muestra un reportecon cambios

### OPCIÓN 2: Sincronización Manual Paso a Paso

Si prefieres control total:

```powershell
# Paso 1: Extraer datos del Excel original
python "Mass calculation\bom_mass_calculator_excel.py"

# Paso 2: Escribir masas en el Excel actualizado
python "Mass calculation\write_masses_to_excel.py"
```

### OPCIÓN 3: Usar la Herramienta de Sincronización Interactiva

```powershell
python "Mass calculation\bom_synchronizer.py"
```

Opciones:
- `1` = Comparar archivos (ver diferencias)
- `2` = Sincronización completa (recomendado)
- `3` = Copiar masas al Excel original

---

## 📋 Escenarios de Cambios

### Scenario A: Cambié dimensiones (L, W, H)
```
🔴 Todo debe recalcularse
✓ Solución: Ejecuta auto_sync.py o Opción 2
```

### Scenario B: Cambié densidades
```
🔴 Las masas hay que recalcular
✓ Solución: Ejecuta auto_sync.py o Opción 2
```

### Scenario C: Cambié masas directamente en BoM_UPDATED.xlsx
```
🟡 Solo ese archivo cambió
✓ Solución: Si quieres guardar cambios manuales:
   - NO ejecutes sincronización (mantendrá tus cambios)
   - O ejecuta auto_sync.py para sobrescribir
```

### Scenario D: Cambié datos en Excel ORIGINAL (Desktop)
```
🔴 Necesita sincronización completa
✓ Solución: Ejecuta auto_sync.py
```

### Scenario E: Añadí nuevos componentes
```
🔴 Hay que recalcular todo el BOM
✓ Solución: Ejecuta auto_sync.py
```

---

## 🔍 Cómo Verificar Que Todo Está Sincronizado

### Opción 1: Visual - Abre los archivos
```
BoM.xlsx (Desktop) → Columna "Mass (g)"
↕ (¿Valores iguales?)
↕
BoM_UPDATED.xlsx → Columna "Mass (g)"
```

### Opción 2: Automatizado - Ejecuta el comparador
```powershell
python "Mass calculation\bom_synchronizer.py"
# Selecciona opción 1 (COMPARE)
```

Salida esperada:
```
No changes detected between files.
```

Si say "Found X changes" → Ejecuta Opción 2 (FULL SYNC)

---

## 📝 Archivo de Log Automático

Cada sincronización crea un backup:
```
Mass calculation/
├── BoM_20260311_143022.xlsx  (backup después de sync)
├── BoM_20260311_142015.xlsx  (backup anterior)
└── ...
```

Puedes recuperar versiones anteriores si algo sale mal.

---

## 🛠️ Cuándo Sincronizar

| Acción | ¿Sincronizar? | Comando |
|--------|---------------|---------|
| Abriste y leíste datos | ❌ NO | - |
| Cambiaste dimensiones (L,W,H) | ✅ SÍ | `auto_sync.py` |
| Cambiaste densidades | ✅ SÍ | `auto_sync.py` |
| Añadiste componentes nuevos | ✅ SÍ | `auto_sync.py` |
| Editaste masas manualmente | ⚠️ QUIZÁS | Deja como está o sincroniza |
| Alguien más cambió es archivo | ✅ SÍ | `auto_sync.py` |

---

## 📊 Cono Saber Si Algo Está Desincronizado

### ✅ TODO BIEN
```
Los valores en columna "Mass (g)" son IGUALES en:
- BoM.xlsx (Desktop)
- BoM_UPDATED.xlsx (Git/tesis)
```

### ❌ DESINCRONIZADO
```
Los valores diferentes entre archivos
→ Ejecuta: python "Mass calculation\auto_sync.py"
```

---

## 🚨 Si Algo Sale Mal

### Problema: "Error al ejecutar script"
```
Solution:
1. Cierra Excel (archivos deben estar sin bloqueos)
2. Abre PowerShell como Administrador
3. Ejecuta:
   cd "c:\Users\alorzaga\Git\tesis"
   python -m pip install --upgrade openpyxl
4. Intenta de nuevo
```

### Problema: "Los valores de masa están 0 o vacíos"
```
Solution:
1. Verifica que BoM.xlsx tiene dimensiones en:
   - Columnas M (L), N (W), O (H)
2. Si faltan dimensiones, edita manualmente
3. Ejecuta auto_sync.py
```

### Problema: "Valores muy diferentes después de sincronizar"
```
Solution:
1. Abre bom_with_masses.csv
2. Revisa columna "Component Type" y "Density Used"
3. Si densidad es incorrecta, edita manualmente en Excel
4. Sincroniza de nuevo
```

---

## 🎯 Workflow Recomendado

```
1. Hago cambios en Excel
   ↓
2. Guardo Excel (Ctrl+S)
   ↓
3. Ejecuto:
   python "Mass calculation\auto_sync.py"
   ↓
4. Reviso resultados y reporte
   ↓
5. Continúo con análisis
```

---

## 💾 Guardando y Versionando

### En Git
```powershell
cd c:\Users\alorzaga\Git\tesis
git add "Mass calculation\BoM_UPDATED.xlsx"
git add "Mass calculation\bom_*.csv"
git commit -m "Update mass calculations - [fecha]"
git push
```

### Backup Manual
```powershell
# Copia BoM_UPDATED.xlsx a un lugar seguro
Copy-Item "Mass calculation\BoM_UPDATED.xlsx" "Desktop\BoM_backup_$(Get-Date -f yyyyMMdd).xlsx"
```

---

## 📞 Referencia Rápida

| Tarea | Comando |
|------|---------|
| Sincronizar todo | `python "Mass calculation\auto_sync.py"` |
| Comparar archivos | `python "Mass calculation\bom_synchronizer.py"` → opción 1 |
| Re-calcular masas | `python "Mass calculation\bom_mass_calculator_excel.py"` |
| Ver cambios | Abre `Mass calculation\bom_with_masses.csv` |
| Recuperar versión anterior | Busca `BoM_YYYYMMDD_HHMMSS.xlsx` en carpeta |

---

**CONCLUSIÓN:** Después de CUALQUIER cambio, ejecuta `auto_sync.py` y todo se sincronizará automáticamente. ✅
