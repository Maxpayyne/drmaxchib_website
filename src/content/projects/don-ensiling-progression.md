---
title: 'Tracking DON Accumulation and Progression During Corn Ensiling'
description: 'Longitudinal study of DON and DON3G across five ensiling time points — tracking toxin changes from harvest through 120 days of silage storage.'
pubDate: 2022-01-01
updatedDate: 2024-01-01
category: 'research'
status: 'shipped'
stack: ['DNA extraction', 'qPCR', 'LC-MS/MS', 'Mini-silos', 'SAS', 'R', 'Linear mixed models']
tags: ['fusarium', 'mycotoxins', 'DON', 'DON3G', 'ensiling', 'silage', 'dairy']
featured: true
order: 2
---

## The question

Dairy farmers and nutritionists routinely test corn silage for DON before feeding — but when should they test? Silage DON concentrations are not static. The fermentation process transforms the chemical composition of the feed, and emerging evidence suggested that DON can increase substantially during the early weeks of ensiling. This project tracked exactly how and when that happens, and why.

The related question: DON3G — a modified, plant-defense form of DON that standard immunoassay tests miss — what role does it play in the final toxin burden of stored silage?

## Approach and methods

The same Arlington ARS field trials that produced the hybrid class data (see companion project) were used here to generate fresh whole-plant corn silage samples from both BMR and conventional hybrids, across two seasons (2020–2021) and multiple fungicide treatments.

**Mini-silo ensiling** — Freshly chopped whole-plant samples were packed into laboratory mini-silos and stored at controlled conditions. Samples were destructively harvested at five time points: at harvest (day 0), and at 30, 60, 90, and 120 days of ensiling. This design made it possible to observe the full fermentation arc rather than a single snapshot.

**Silage quality analysis** — Each time-point sample was analyzed for standard nutritional and fermentation parameters: moisture, starch, neutral detergent fiber (aNDF), total tract NDF digestibility (TTNDFD), and milk production potential (MILK2006 index).

**Toxin quantification (LC-MS/MS)** — Both DON and DON3G concentrations were measured at each time point using LC-MS/MS, providing simultaneous detection of both compounds. The high sensitivity and specificity of mass spectrometry was essential here — immunoassay-based tests used in commercial labs do not detect DON3G at all, meaning routine testing systematically underestimates total toxin burden.

**Statistical modeling** — Linear mixed models in SAS were used to evaluate the effects of hybrid class, fungicide treatment, ensiling duration, and their interactions on DON and DON3G concentrations, with year as a random effect.

## Key findings

DON concentration was lowest at harvest and increased most sharply in the first 30 days of ensiling. The early anaerobic phase, before fermentation fully stabilizes the silo environment, is when fungal activity is still possible and when the DON3G-to-DON conversion is most active.

The DON3G–DON relationship was the most striking finding: when DON3G was high at harvest, DON was low — and vice versa. After 30 days of ensiling, that relationship inverted. DON3G concentration at harvest predicted DON concentration at 30 days with meaningful accuracy, suggesting that pre-storage DON3G measurement could serve as an early warning tool.

Hybrid class again dominated over fungicide treatment as a driver of outcomes. Feeding decisions for silage corn should weight hybrid selection heavily, and toxin testing should account for ensiling duration and include assays capable of detecting DON3G.

## Published work

**Chibuogwu, M. O.**, Reed, H., Groves, C. L., Mueller, B., Barrett-Wilt, G., & Smith, D. (2024). Effects of hybrid class and ensiling duration on the accumulation of deoxynivalenol and the relationship with its derivative, deoxynivalenol-3-glucoside while ensiling corn for silage. *Plant Disease*.

<a href="https://doi.org/10.1094/PDIS-06-24-1166-RE" target="_blank" rel="noopener">doi.org/10.1094/PDIS-06-24-1166-RE ↗</a>

**Chibuogwu, M. O.**, Mueller, B., Groves, C. L., Tenuta, A. U., Chilvers, M. I., Wise, K. A., & Smith, D. (2025). Where's DON? Understanding where deoxynivalenol accumulates in corn silage. *Crop Protection Network*, CPN-5018.

<a href="https://cropprotectionnetwork.org/publications/wheres-don-understanding-where-deoxynivalenol-don-accumulates-in-corn-silage" target="_blank" rel="noopener">Read on Crop Protection Network ↗</a>
