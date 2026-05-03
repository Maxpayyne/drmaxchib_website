---
title: 'A weather app Nigerian farmers can actually use'
description: 'Modern, location-specific weather forecasting for Nigerian agricultural cities — built to replace the static PDF bulletins NiMet still publishes today.'
pubDate: 2026-05-03
category: 'civic'
status: 'concept'
stack: ['Astro', 'TypeScript', 'Open-Meteo API', 'Cloudflare Workers', 'Tailwind']
tags: ['nigeria', 'weather', 'agriculture', 'civic-tech']
featured: true
order: 1
---

## The problem

The [Nigerian Meteorological Agency](https://nimet.gov.ng/) publishes its forecasts as low-resolution PDF bulletins — static images of cloud icons over a country map, pushed out
at irregular intervals. For a Wisconsin farmer, this would be unthinkable. For a smallholder farmer in Kaduna trying to decide whether to plant this week, it is the
status quo.

The technology gap is not a data gap. Modern open-source forecasting APIs — [Open-Meteo](https://open-meteo.com/), NOAA GFS, ECMWF — already cover Nigeria with hourly
resolution. The gap is a delivery gap, and an interpretation gap, and a trust gap.

## What I'm building

A web product that does three things NiMet's bulletins do not:

1. **Location-specific forecasts** for the cities and farming corridors where they matter — Kaduna, Kano, Ibadan, Jos, Makurdi, Yola — at hourly resolution and seven-day
   lookahead.
2. **Agricultural framing** of the forecast: not "scattered showers" but "good window for planting maize tomorrow before 11 AM, soil moisture remains favorable through the
   weekend."
3. **Mobile-first delivery** designed to load on a 3G connection in under two seconds, because that is the connection most users will have.

## Where this is going

The first version is a static Astro site backed by serverless [Cloudflare Workers](https://workers.cloudflare.com/) calls to Open-Meteo. The next version adds SMS
delivery for users without smartphones. The longer-term ambition includes locally-trained satellite-imagery models for crop-stress monitoring — and, eventually, owned
satellite data infrastructure for the African continent.

I'm under no illusions about how hard the long arc is. The first product, though, is genuinely modest: take an excellent free API, add agricultural context, ship it
fast, and prove that the tooling problem can be solved in a weekend by one person with a laptop.

If you're a Nigerian farmer, an agronomist, or a developer who wants to help — the [contact link](/about) is on the about page.
