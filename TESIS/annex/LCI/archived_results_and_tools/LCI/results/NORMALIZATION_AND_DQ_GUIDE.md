# LCA Normalization & Data Quality Guide

## Overview

This guide explains how to enable and use **Normalization** and **Data Quality** features in the result extraction script.

---

## 1. NORMALIZATION

### What is Normalization?

**Normalization** divides LCA results by reference values to make different impact categories comparable on the same scale.

**Example:**
- Raw Climate Change impact: 1000 kg CO2-eq
- Normalization factor: 8500 kg CO2-eq per person per year (Europe average)
- Normalized result: 1000 ÷ 8500 = **0.118 person-equivalents**

This lets you compare: "My product causes 0.118 times the average person's climate impact"

### When to Use Normalization

✓ When comparing multiple products/systems
✓ When trying to understand impact in relative terms
✓ When performing weighted/characterization analysis
✓ When benchmarking against averages/standards

### How to Enable Normalization

**Step 1:** Edit `global_parameters.json` in the LCI folder

**Step 2:** Add normalization configuration to `result_extraction` section:

```json
{
  "parameters": {
    "result_extraction": {
      "product_systems_result_analysis": ["Your System Name"],
      "lcia_methodology": "EF v3.1",
      
      // NEW: Add this section
      "normalization": {
        "enabled": true,
        "nw_set_name": null
      },
      
      "sankey": { ... }
    }
  }
}
```

### Configuration Parameters

#### `normalization.enabled` 
- **Type:** Boolean (true/false)
- **Default:** false
- **Effect:** 
  - `true` = Calculate and save normalized results
  - `false` = Skip normalization (faster)

#### `normalization.nw_set_name`
- **Type:** String or null
- **Default:** null
- **Options:**
  - `null` = Use default NwSet from LCIA method
  - `"EF v3.1 Europe"` = Use specific regional NwSet
  - `"ReCiPe Endpoint Europe"` = Method-specific set
- **To find available sets:** Check openLCA LCIA method configuration

### Output

When normalization is enabled, the `*_impacts.csv` file will include:

| Impact category | Amount (Raw) | Amount (Normalized) | Unit | Normalized Unit |
|---|---|---|---|---|
| Climate Change | 1000 | 0.118 | kg CO2-eq | kg CO2-eq/ref |
| Water Depletion | 500 | 0.25 | m³ | m³/ref |

---

## 2. DATA QUALITY

### What is Data Quality?

**Data Quality** retrieves the **reliability scores** you've already set in openLCA for each process and flow.

These scores document how trustworthy your LCA data is:
- Measured data = high quality
- Estimated data = lower quality
- This helps interpret results with appropriate confidence

### Your DQ Scores in openLCA

You've already assigned quality scores to your processes. This script **extracts and reports** those scores.

#### A. Pedigree Matrix (Process-Level)

Format: `(score1;score2;score3;score4;score5)`

Each score represents reliability in different aspects:
- **1** = Measured/Actual Data (HIGH QUALITY ✓)
- **2** = Manufacturer Data  
- **3** = Literature/Industry Average
- **4** = Estimated (LOW QUALITY ⚠)
- **5** = Guessed/Not specified (WORST ✗)
- **n.a.** = Not applicable for this indicator

**Example:** `(3;2;4;n.a.;2)`
- Indicator 1: score=3 (medium - literature value)
- Indicator 2: score=2 (good - manufacturer data)
- Indicator 3: score=4 (poor - estimated)
- Indicator 4: n.a. (not applicable)
- Indicator 5: score=2 (good - manufacturer data)

Lower average = more reliable data

#### B. Per-Flow Quality Scores (Exchange-Level)

Each input/output can have its own quality score:
- **More granular** than process-level
- Allows different quality for different flows
- Example: Steel supplier = high quality, transport distance = low quality

#### C. Uncertainty Information

You may also have set uncertainty ranges for flows:
- **Distribution Type:** Normal, Lognormal, Uniform, etc.
- **Standard Deviation:** Variability of the data
- **Min/Max Values:** Range of possible values

### When to Use Data Quality Info

✓ When interpreting LCA results critically
✓ When identifying uncertain processes
✓ When prioritizing where to collect better data
✓ When performing sensitivity analysis
✓ For data quality reports to stakeholders

### How to Enable Data Quality Extraction

This extracts **your existing DQ scores** from openLCA.

**Step 1:** Edit `global_parameters.json`

**Step 2:** Add data quality configuration:

```json
{
  "parameters": {
    "result_extraction": {
      "product_systems_result_analysis": ["Your System Name"],
      "lcia_methodology": "EF v3.1",
      
      // NEW: Add this section to extract YOUR DQ scores
      "data_quality": {
        "include_process_dq": true,
        "include_exchange_dq": true,
        "export_dq_system_info": true
      },
      
      "sankey": { ... }
    }
  }
}
```

### What Gets Extracted

**ALL contributing processes** across the entire supply chain:
- Process-level pedigree matrix scores (if `include_process_dq: true`)
- Per-flow quality scores (if `include_exchange_dq: true`)
- Uncertainty ranges you've defined
- Quality summary statistics

**Not just one sample** – comprehensive report of all data quality

### Configuration Parameters

#### `data_quality.include_process_dq`
- **Type:** Boolean
- **Default:** false
- **Effect:** Extract pedigree matrix scores for entire process
- **Output:** Process-level DQ entry (pedigree matrix)

#### `data_quality.include_exchange_dq`
- **Type:** Boolean
- **Default:** false
- **Effect:** Extract DQ for each individual input/output flow
- **Output:** Per-flow quality scores and uncertainty ranges
- **Note:** More detailed than process-level

#### `data_quality.export_dq_system_info`
- **Type:** Boolean
- **Default:** false
- **Effect:** Export the DQ system definition (scoring schema)
- **Output:** What each DQ score position means
- **Use case:** Understanding DQ system used in the method

### Output

When data quality extraction is enabled, a `*_data_quality.json` file is created with:

```json
{
  "system": "Buck Converter System",
  "lcia_method": "EF v3.1",
  "summary": {
    "total_processes": 45,
    "processes_with_dq": 38,
    "average_dq_entry": "Average Quality Score: 2.8",
    "quality_distribution": {
      "High (1-2)": 12,
      "Medium (2-3)": 18,
      "Low (3-5)": 15
    }
  },
  "processes": [
    {
      "process_name": "Steel production, converter, unalloyed",
      "process_id": "abc123...",
      "process_dq_entry": "(3;2;4;n.a.;2)",
      "impact_contribution": {
        "category": "Climate Change",
        "contribution": 250.5,
        "unit": "kg CO2-eq"
      },
      "dq_system": "ecoinvent 3.8 DQ System",
      "has_uncertainties": true,
      "indicators": [
        {
          "name": "Reliability of source",
          "position": 1,
          "scores": [
            {
              "value": 1,
              "label": "Verified data from supplier",
              "uncertainty": 1.05
            },
            {
              "value": 3,
              "label": "Average literature value",
              "uncertainty": 1.2
            }
          ]
        }
      ]
    },
    // ... more processes
  ]
}
```

**What this shows:**
- **Quality Summary:** Overall data quality assessment
  - Total processes analyzed
  - How many have DQ scores
  - Average quality score
  - Distribution (how many are high/medium/low quality)

- **Per-Process Detail:** For each contributing process:
  - Your DQ pedigree matrix score
  - Which impact category it contributes to
  - How much it contributes
  - What the scores mean (indicator definitions)
  - Uncertainty multipliers if set

---

## 3. COMPLETE EXAMPLE: global_parameters.json

Here's a complete example with both normalization and data quality enabled:

```json
{
  "parameters": {
    "result_extraction": {
      "product_systems_result_analysis": [
        "Buck Converter System",
        "Li-ion Battery Module"
      ],
      "lcia_methodology": "EF v3.1",
      "impact_categories": [
        "Climate Change",
        "Water Depletion",
        "Resource Depletion"
      ],
      "number_top_contributors": 5,
      
      "normalization": {
        "enabled": true,
        "nw_set_name": null
      },
      
      "data_quality": {
        "include_process_dq": true,
        "include_exchange_dq": true,
        "export_dq_system_info": true
      },
      
      "sankey": {
        "sankey_mode": 1,
        "sankey_top_flows": 10,
        "sankey_top_impacts": 5,
        "sankey_max_depth": 3
      }
    }
  }
}
```

---

## 4. OUTPUT FILES

### With Normalization Enabled

**File:** `{system}_{method}_impacts.csv`

Contains both raw and normalized values for comparison:
```
Impact category,Amount (Raw),Amount (Normalized),Unit,Normalized Unit
Climate Change,1000.5,0.118,kg CO2-eq,kg CO2-eq/ref
Water Depletion,500.2,0.25,m³,m³/ref
```

### With Data Quality Enabled

**File:** `{system}_{method}_data_quality.json`

Contains:
- Process pedigree matrix (quality of entire process data)
- Exchange-level quality scores (for each input/output)
- Uncertainty information (distributions, ranges)
- DQ system metadata (definitions of what scores mean)

---

## 5. INTERPRETING RESULTS

### Reading Normalized Impacts

**Normalized value < 1.0**
- Your impact is BELOW the reference (good)
- Example: 0.5 = half the average impact

**Normalized value = 1.0**
- Your impact equals the reference (average)

**Normalized value > 1.0**
- Your impact is ABOVE the reference (concerning)
- Example: 2.5 = 2.5 times the average impact

### Reading Data Quality Report

The report shows:

**Summary Section:**
- **total_processes:** How many processes contribute to impacts
- **processes_with_dq:** How many have DQ scores set (vs empty)
- **average_dq_entry:** Overall data quality (lower = better)
- **quality_distribution:** How many are high/medium/low quality

**Quality Tiers:**
- **High (1-2):** Measured/reliable data ✓ 
  - Can be trusted for decision-making
  - Low uncertainty

- **Medium (2-3):** Mixed quality ⚠
  - Acceptable for most analyses
  - Moderate uncertainty
  - Monitor in sensitivity analysis

- **Low (3-5):** Estimated/less reliable ✗
  - Use cautiously
  - Flag for data collection/refinement
  - May dominate overall uncertainty

**Per-Process Info:**
Shows which processes have low quality → identify improvement priorities

**Example Interpretation:**
```
Average Quality Score: 2.8 = Acceptable, leaning toward medium quality
Quality Distribution:
  - High (1-2): 12 processes = Good data foundation
  - Medium (2-3): 18 processes = Moderate confidence
  - Low (3-5): 15 processes = Areas needing data refinement
  
→ Overall assessment: System has reasonable data quality but some 
  processes could use better data collection

---

## 6. TROUBLESHOOTING

### "No Normalization Sets found"
- **Problem:** LCIA method has no NwSet
- **Solution:** Choose a different LCIA method that includes normalization sets
- **Methods with NwSets:** EF v3.1, ReCiPe, TRACI

### "NwSet 'X' not found"
- **Problem:** Specified NwSet name doesn't exist
- **Solution:** Set `nw_set_name` to `null` to use default, or check available sets in openLCA

### Data quality JSON is empty
- **Problem:** Contributing processes don't have DQ data in openLCA
- **Solution:** Add DQ info to processes in openLCA first

---

## 7. WORKFLOW SUMMARY

```
1. Configure global_parameters.json
   ├─ Set product systems to analyze
   ├─ Enable normalization (optional)
   └─ Enable data quality (optional)

2. Run result_extraction.py
   $ python LCI/result_extraction.py

3. Check output files in LCI/results/
   ├─ *_impacts.csv (with raw + normalized if enabled)
   ├─ *_inventory.csv
   ├─ *_upstream.csv
   ├─ *_sankey.json
   └─ *_data_quality.json (if enabled)

4. Interpret results
   ├─ Analyze normalized values
   ├─ Review data quality scores
   ├─ Identify uncertain/low-quality data
   └─ Plan data collection improvements
```

---

## 8. FURTHER READING

- **Normalization in LCA:** ISO 14040/44 standards
- **Data Quality:** ecoinvent DQ System documentation
- **Uncertainty Analysis:** openLCA Documentation
- **EF method:** European Commission Product Environmental Footprint (PEF)
