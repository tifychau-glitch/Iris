# Research Guide: How to Find Missing Site Data

When a user provides an address or partial listing, use this guide to fill in missing evaluation fields through web search. Research proactively — don't leave fields as "Unknown" when the data is findable.

---

## 1. Traffic Counts (AADT)

AADT (Annual Average Daily Traffic) is the most important number to find. Every state DOT publishes traffic count data.

**Search strategy:**
1. Try: `"[road name] [city] [state] AADT traffic count"`
2. Try: `"[state] DOT traffic count map [road name]"`
3. Go directly to the state DOT traffic count viewer:
   - Georgia: https://www.dot.ga.gov/Applications/TrafficDataTrafficCounter/
   - Texas: https://www.txdot.gov/data-maps/roadway-inventory/traffic-count.html
   - Florida: https://www.fdot.gov/statistics/trafficdata/
   - Tennessee: https://www.tn.gov/tdot/traffic-operations-division/traffic-engineering/traffic-count-data.html
   - Arizona: https://adot.gov/travel/roads/highway-performance/traffic-monitoring/
   - North Carolina: https://connect.ncdot.gov/resources/State-Mapping/Pages/Traffic-Survey-Maps.aspx
   - For other states: search `"[state] DOT traffic count data interactive map"`

**What to extract:**
- AADT for the main road in front of the site
- Year of the count (counts more than 5 years old should be noted)
- If the site is on a secondary road, also get the AADT of the nearest major road

**Fallback:** Google Maps satellite view often shows road classifications that help estimate traffic type. A 4-lane divided arterial in a suburban retail corridor typically sees 15,000-35,000 AADT. A 2-lane rural highway typically sees 5,000-15,000.

---

## 2. Demographics (Population + Income)

**Best free sources:**
1. **Census Reporter** – https://censusreporter.org — Search by address, get 1-mile, 3-mile, 5-mile radius demographics instantly. Best tool for quick lookups.
2. **City-Data.com** – https://www.city-data.com — Search by city name or zip code. Good for median household income and population.
3. **US Census American Community Survey** – https://data.census.gov — Official source, more complex but authoritative.
4. **SimplyAnalytics** or **STDBonline** — Professional demographic tools; only use if user has access.

**Search strategy:**
- Try: `"population [city] [state] [zip code] median household income"`
- Or go directly to censusreporter.org and search the address

**What to extract:**
- Total population within 1-mile radius
- Total population within 3-mile radius
- Median household income (3-mile radius)
- Population growth trend (if available)
- Note: Census Reporter shows all three of these in a single profile page

---

## 3. Nearby Competitors (Tunnel Car Washes)

This is critical and easy to find. A "competitor" means **tunnel car washes only** — not self-serve bays or gas station washes.

**Search strategy:**
1. Search Google Maps (via web search): `"tunnel car wash near [address]"` or `"express car wash [city] [state]"`
2. Also try: `"[city] [state] car wash site:google.com/maps"`
3. Look for brand names like Mister Car Wash, Zips Car Wash, Magnolia Car Wash, Cobblestone, Quick Quack, Tommy's Express, Caliber Car Wash, WashU, Club Car Wash
4. Check if any competitors appear within 1 mile, 2 miles, and 3 miles

**What to note:**
- Name and address of each competitor
- Estimated distance from subject site (in miles)
- Whether they appear to be on the same side of the main road
- Any visible signals of quality (newer location = stronger competition)

**If you can't find specific competitors:** Note that no tunnel car washes were found in web search results for that city/area, and flag it as likely underserved (which is a positive signal for the small-town exception).

---

## 4. Nearby Retail Anchors

Retail context tells you whether this is a real daily-errand corridor.

**Search strategy:**
1. Search: `"grocery stores near [address]"` — Kroger, Publix, Safeway, Walmart Supercenter, Aldi, Food Lion, HEB, Winn-Dixie
2. Search: `"Walmart near [address]"`, `"Target near [address]"`, `"Lowe's near [address]"`
3. Search: `"fast food restaurants near [address]"` for QSR density signal
4. Look at the listing's aerial photo or Google Maps satellite view for retail context

**What to look for:**
- Any grocery store within 0.5 miles = strong positive signal
- Walmart Supercenter within 1 mile = strong positive signal
- Dense QSR/fast food strip = good daily traffic indicator
- Hospital or college nearby = consistent daily traffic generator
- "Retail park" or shopping center = confirms active corridor

---

## 5. Zoning Status

Don't guess from the zoning label (e.g., "C-2"). Look up whether car wash is actually permitted.

**Search strategy:**
1. Try: `"[city] [state] zoning code car wash permitted use"`
2. Try: `"[city] municipal code car wash conditional use"`
3. Search the city's official municipal code: `site:[city].gov zoning "car wash"`
4. Many cities post their zoning ordinances at `[city].gov/planning` or `[city].gov/zoning`
5. For unincorporated county land: search `"[county] county zoning ordinance car wash"`

**What to determine:**
- Is car wash listed as a permitted use, conditional use, or special use in the applicable zone?
- Is any mention of "drive-through" or "drive-in facility" (often how car washes are classified)?
- Are there any specific requirements (stacking, setbacks, buffers) listed?

**Important caveat:** Even if you find the zoning code online, always recommend the user contact the planning department directly for written confirmation. Online codes may be outdated.

---

## 6. Speed Limits

Speed limits are almost always findable.

**Search strategy:**
1. Google Maps: Search the address and use Street View (describe what you see)
2. Try: `"speed limit [road name] [city] [state]"`
3. State DOT speed limit databases sometimes list posted limits by road segment
4. City/county engineering departments sometimes post speed limit data online

**Judgment when you can't find exact speed:**
- Interstate highway or expressway: 65-70 mph → not viable for stop-in
- US Highway / major state route through suburban area: typically 45-55 mph → borderline
- City arterial with traffic signals every 0.5 mile: typically 35-45 mph → ideal
- Downtown / commercial strip: typically 25-35 mph → good for visibility

---

## 7. Going-Home Side

This takes local knowledge and some inference.

**How to determine it:**
1. Find where the residential neighborhoods are relative to the site (Google Maps satellite view)
2. Find where major employers are (Google search: `"largest employers [city] [state]"`)
3. The "going-home side" is the side of the road that people travel on when returning from work/shopping to residential areas
4. In most suburban markets: people commute toward the city in the morning, return outbound in the evening — so the site should be on the outbound/residential side

**Note in evaluation:** State your reasoning. "The site is on the westbound side of Hwy 20, and most residential development is to the west of the commercial corridor — this appears to be the going-home direction."

---

## 8. Lot Shape and Physical Constraints

**How to research:**
1. Search the county property appraiser / assessor GIS for a parcel map: `"[county] county property appraiser GIS [parcel ID or address]"`
2. Most counties have a free public GIS viewer that shows parcel boundaries
3. Google Maps satellite view shows approximate lot shape and surrounding context
4. If a listing was shared, the property plat (survey) is the most reliable source

**What to look for:**
- Is the lot roughly rectangular or irregular/triangular?
- Are there any visible constraints (ponds, easements, adjacent buildings)?
- Is there adequate depth from the road?

---

## Research Output Format

After completing research, summarize what you found before running the evaluation. Format like this:

```
RESEARCH FINDINGS (auto-researched before evaluation)
────────────────────────────────────────────────────
Traffic (AADT): [value] — Source: [Georgia DOT / estimated / listing]
Population (1 mi / 3 mi): [values] — Source: [Census Reporter / listing]
Median HHI (3 mi): [value] — Source: [Census Reporter / listing]
Tunnel competitors found: [list names + distance, or "None found within 3 miles"]
Retail anchors: [list key anchors found]
Zoning status: [what you found, or "Could not confirm — recommend city contact"]
Speed limit: [value or estimated range]
Going-home side: [assessment + reasoning]
────────────────────────────────────────────────────
Note: Fields marked "estimated" should be verified before LOI.
```

Then proceed with the full evaluation using this researched data.
