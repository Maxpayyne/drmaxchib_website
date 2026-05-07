---
title: 'Silage Microbiome Analysis Using QIIME 2'
description: 'Amplicon microbiome profiling of corn and alfalfa silage across ensiling time points — tracking how fermentation reshapes the microbial community.'
pubDate: 2025-01-01
category: 'research'
status: 'in-progress'
stack: ['QIIME 2', 'DADA2', 'Python', 'R', 'USDA SCINet Ceres', 'Illumina MiSeq']
tags: ['microbiome', 'silage', 'qiime2', '16S-rRNA', 'fermentation', 'dairy']
featured: false
order: 5
---

## What this project is about

Silage fermentation is fundamentally a microbial process. The quality of the final feed — its pH, organic acid profile, aerobic stability, and mycotoxin burden — is determined in large part by which microorganisms dominate the anaerobic silo environment and in what sequence. Yet the microbial ecology of silage fermentation across different forage types, hybrid classes, and management scenarios remains incompletely characterized.

This project uses amplicon-based microbiome sequencing to profile the bacterial and fungal communities present in corn and alfalfa silage at multiple time points during ensiling — from freshly chopped forage through 120 days of storage. The goal is to understand how the microbial community changes over time, which taxa dominate each phase of fermentation, and whether microbial community composition at harvest predicts silage quality and mycotoxin outcomes at feeding.

## Methods overview

**Sample collection** — Silage samples are drawn from mini-silos at five ensiling time points (0, 30, 60, 90, and 120 days), representing the arc from fresh forage through fully stabilized silage. Both corn and alfalfa forages from field trials at the Arlington Agricultural Research Station are included.

**DNA extraction** — Total DNA is extracted from homogenized silage using protocols optimized for complex plant-microbial matrices. Extraction quality is assessed by Qubit fluorometry and agarose gel before sequencing.

**Amplicon sequencing** — The 16S rRNA gene (V3-V4 region, bacteria) and ITS2 region (fungi) are amplified by PCR and sequenced on the Illumina MiSeq platform, generating paired-end reads for both bacterial and fungal community profiles from the same samples.

**Bioinformatic analysis (QIIME 2 on USDA-SCINet Ceres)** — Raw reads are imported into QIIME 2 and processed through DADA2 for denoising, chimera removal, and amplicon sequence variant (ASV) generation. Taxonomy is assigned against the SILVA (bacteria) and UNITE (fungi) reference databases. Alpha and beta diversity metrics, differential abundance testing, and community composition visualizations are generated in QIIME 2 and R.

## Status

Analysis is in progress. Sequencing is complete for the first batch of samples; QIIME 2 processing and diversity analyses are underway on Ceres.
