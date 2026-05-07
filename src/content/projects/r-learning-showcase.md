---
title: 'Learning R Through Agricultural Data'
description: 'An R showcase for agricultural data analysis — code snippets, annotated outputs, and a path to your first working script using real research data.'
pubDate: 2026-05-04
category: 'pet'
status: 'in-progress'
stack: ['R', 'ggplot2', 'dplyr', 'tidyr', 'RStudio']
tags: ['R', 'data-science', 'teaching', 'agriculture', 'visualization']
featured: true
order: 1
---

## Why R, and why agricultural data?

R is the dominant language for statistical analysis in the life sciences, agronomy, and ecology — and it is genuinely learnable by anyone with patience and access to a laptop. The barrier is not the language itself. It is the combination of unfamiliar syntax, unhelpful error messages, and examples that use toy datasets with no connection to anything real.

This page exists to lower that barrier, using data that actually comes from agricultural research.

---

## Getting started

Before you run any code, you need two things:

1. **R** — the language engine. Download from [r-project.org](https://www.r-project.org/) — it is free and runs on Windows, Mac, and Linux.
2. **RStudio** — a much more usable interface for writing R. Download the free Desktop version from [posit.co/downloads](https://posit.co/downloads/).

Install R first, then RStudio. Open RStudio — you will see four panes. The bottom-left console is where code runs. The top-left script editor is where you write and save code. Start there.

---

## Snippet 1 — Loading and exploring a dataset

The most common first task: load data, look at its structure, check for missing values.

```r
# Load the tidyverse — a collection of packages for data work
# If you haven't installed it, run: install.packages("tidyverse")
library(tidyverse)

# Read a CSV file into a data frame
corn_data <- read_csv("silage_don_data.csv")

# Look at the first 6 rows
head(corn_data)

# Get a summary of all columns
summary(corn_data)

# Check dimensions: rows × columns
dim(corn_data)

# Check for missing values per column
colSums(is.na(corn_data))
```

**What you'll see:** A table with column names, data types, and summary statistics. The `summary()` call gives you min, max, mean, and quartiles for numeric columns — a fast health check on any dataset.

---

## Snippet 2 — Filtering and grouping

Real data analysis involves subsetting to what you need and summarizing by group.

```r
# Filter to only rows where DON exceeds 0.5 ppm
high_don <- corn_data %>%
  filter(DON_ppm > 0.5)

# Calculate mean DON by hybrid class and ensiling duration
don_summary <- corn_data %>%
  group_by(hybrid_class, days_ensiled) %>%
  summarise(
    mean_DON = mean(DON_ppm, na.rm = TRUE),
    sd_DON   = sd(DON_ppm, na.rm = TRUE),
    n        = n()
  )

print(don_summary)
```

**What you'll see:** A grouped table showing how DON concentration changes across ensiling duration for each hybrid type. The `%>%` operator (called a "pipe") passes the result of one function to the next — you read it as "and then."

---

## Snippet 3 — Visualization with ggplot2

A line plot tracking DON accumulation over the ensiling period.

```r
ggplot(don_summary, aes(x = days_ensiled, y = mean_DON, color = hybrid_class)) +
  geom_line(linewidth = 1) +
  geom_point(size = 3) +
  geom_errorbar(
    aes(ymin = mean_DON - sd_DON, ymax = mean_DON + sd_DON),
    width = 3,
    alpha = 0.4
  ) +
  labs(
    title   = "DON Accumulation During Ensiling",
    x       = "Days After Harvest",
    y       = "DON Concentration (ppm)",
    color   = "Hybrid Class",
    caption = "Error bars = ±1 SD"
  ) +
  theme_minimal(base_size = 13) +
  scale_color_manual(values = c("BMR" = "#3f7045", "Conventional" = "#8eb190"))
```

**What you'll see:** A publication-ready line chart with error bars. `ggplot2` builds plots in layers — `aes()` maps variables to visual properties, `geom_*()` functions add geometric layers, `labs()` adds titles and labels, and `theme_*()` controls the overall appearance.

---

## Snippet 4 — A simple linear model

Testing whether ensiling duration predicts DON concentration.

```r
# Fit a linear model: DON ~ days ensiled + hybrid class
model <- lm(DON_ppm ~ days_ensiled + hybrid_class, data = corn_data)

# View the model summary
summary(model)

# Check model assumptions visually
par(mfrow = c(2,2))
plot(model)
```

**What you'll see:** Coefficient estimates, standard errors, p-values, and R². The `plot(model)` call produces four diagnostic plots — residuals vs. fitted, Q-Q plot, scale-location, and Cook's distance — the standard checks for whether a linear model is appropriate for your data.

---

## Want to go further?

These resources will take you from snippets to fluency:

- [R for Data Science (free online book)](https://r4ds.hadley.nz/) — the definitive introduction by Hadley Wickham
- [The Epidemiologist R Handbook](https://epirhandbook.com/) — practical workflows for research
- [ggplot2 documentation](https://ggplot2.tidyverse.org/) — complete reference for visualization

---

## Join a training session

I run periodic workshops on R for graduate students and early-career researchers in the agricultural sciences — covering data wrangling, mixed models, and publication-quality visualization. If you'd like to be notified of upcoming sessions:

<a href="https://forms.gle/placeholder" target="_blank" rel="noopener" class="btn-register">Register interest ↗</a>

*The Google Form will collect your name, email, and research area. No spam — just session announcements.*
