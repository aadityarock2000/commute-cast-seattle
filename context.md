# CommuteCast Seattle — Project Context Handoff

## Goal of the project
The project is an early-stage data science / ML project focused on **Seattle public transit reliability**.

The core idea is **not** just to show schedules or live arrivals. The aim is to build a system that can answer questions like:

- What is the probability that a commuter arrives late?
- Which transit option is lower risk?
- How reliable is a route or transfer under current conditions?
- Eventually: how much extra buffer time should someone leave?

In plain English:
> Normal transit apps give an ETA. This project wants to estimate **confidence / risk around that ETA**.

---

## Current project framing
The project is currently being framed as a **predictive reliability problem** using public transit data.

### Likely ML framing for V1
The cleanest first ML target discussed was:

- **Binary classification**
- Predict whether a trip or arrival is **more than X minutes late**
- Example target:
  - `1` = arrival is more than 5 minutes late
  - `0` = otherwise

Other future possibilities discussed:
- Regression for delay minutes
- Transfer miss prediction
- Buffer recommendation

But for now, the focus is still **very early-stage setup**, before modeling.

---

## Why this project exists
The user became a bit unsure about what the project was actually solving, so the problem was clarified as follows:

This is a **decision-support system for commuters under uncertainty**.

Example:
- A route planner says: “You will arrive at 8:27.”
- This project wants to say: “You are expected to arrive at 8:27, but there is a 32% chance you arrive after 8:30.”

That framing is important. The project is about:
- transit reliability
- uncertainty
- risk estimation
- decision support

---

## What data sources were identified
The project uses **Seattle-area public transit data**, starting with **King County Metro**.

Two main categories of data were identified:

### 1. Static GTFS
This is the scheduled transit data:
- routes
- stops
- trips
- stop_times
- calendars / service patterns

This is the structural schedule layer.

### 2. Real-time GTFS feeds
This is the live operations layer:
- trip updates
- vehicle positions
- service alerts

This gives current operational state.

A note was also made that OneBusAway exists in the Seattle ecosystem, but it was intentionally **not chosen for the initial weekend setup**, because it may require API key approval and is not the fastest way to get moving.

---

## What the user wanted to do this weekend
The user wanted a **very small scoped weekend setup**, something possible in **1–2 hours**, so that they could spend the week on modeling.

The immediate goal was **not** to build the ML model.
The immediate goal was to prove:

- the data actually exists
- the APIs / feeds work
- the files are readable
- the project is technically viable

So this weekend task became a **data source validation / ingestion sanity-check step**.

---

## What was built
A Python script was created to do the following:

1. Create a local raw data folder
2. Download the static GTFS zip
3. Open the GTFS zip and inspect core files
4. Read key GTFS tables into pandas
5. Print basic counts and sample rows
6. Save sample CSVs locally
7. Download real-time JSON feeds
8. Save those JSON snapshots locally
9. Inspect the top-level JSON structure

This script is essentially a **source validation script**, not a modeling script.

---

## What the code is doing conceptually
The code is doing this:

- Download the official transit schedule
- Download the live operational feeds
- Save raw files locally
- Confirm the files are not empty / broken
- Inspect the structure so future parsing is easier

It is **not yet**:
- building a training dataset
- joining static and live data
- engineering features
- training a model
- producing predictions

This step was explained as:
> “Can I trust the raw inputs and begin the project?”

---

## What errors happened
The user first ran the script and encountered an error when fetching the live feed.

### First issue
They initially got a connection-related failure (`RemoteDisconnected` style issue).

That led to discussion that:
- the static GTFS had already worked
- the project was still viable
- the live layer needed more robust handling

### Second issue
They then got a more concrete error:

- `403 Client Error: Forbidden`

This turned out to be caused by using the **wrong / outdated real-time feed URL**.

The original script used a URL like:
- `trip-updates.json`

But the currently working filenames were the newer S3 object names, such as:
- `tripupdates_pb.json`
- `vehiclepositions_pb.json`
- `alerts_pb.json`

So the real issue was not their environment or logic — it was the endpoint name.

---

## What was fixed
The real-time feed URLs were updated to the currently working versions.

After changing the URLs, the script completed successfully and printed `"Done"`.

That means the data access setup now works at least at a basic level.

---

## What has been successfully validated
The following is now known:

### Static transit data works
The GTFS zip downloaded and loaded successfully.

The script successfully read key tables such as:
- `routes.txt`
- `stops.txt`
- `trips.txt`
- `stop_times.txt`

This proves the static schedule layer is available and usable.

### Real-time feed access works
After fixing the URLs, the real-time feeds also ran successfully.

So the user now has a working first-pass ingestion sanity check for:
- static schedule data
- live transit data

This is an important milestone because it proves the project is technically feasible.

---

## What has *not* been done yet
The following major project steps are still open:

### Data understanding / schema exploration
Still need to inspect:
- exact columns in each GTFS table
- exact fields in the real-time JSON payloads
- what IDs can be joined
- what granularity the records are at

### Join logic
Still need to determine:
- how static `trip_id`, `route_id`, `stop_id` connect to real-time data
- whether King County Metro IDs line up cleanly in practice
- how to track a trip through schedule + live feed

### Training dataset design
Still need to define the modeling table, for example rows like:
- route
- trip
- stop
- timestamp
- scheduled arrival
- live observed delay
- historical context
- label: late / not late

### Target definition
Still need to decide exactly what the first prediction target is:
- trip late by > 5 min?
- stop arrival late by > 5 min?
- transfer miss?
- something else?

### Snapshot collection over time
Still need to collect repeated real-time snapshots if the user wants actual historical training data from live feeds.

### Modeling
No model training has happened yet.

---

## What should likely happen next
The logical next step is **not** to jump into fancy ML yet.

The best next step is:

### Step 1: Explore the schema in detail
Create a second script or notebook that answers:
- what columns are in routes / trips / stop_times / stops?
- what fields are in trip updates / vehicle positions?
- which IDs might join across static and live data?

### Step 2: Pick a narrow scope
Limit the project to:
- one agency
- maybe one or a few routes
- maybe one commute corridor

This reduces complexity.

### Step 3: Define the unit of prediction
Decide what one row in the future training set represents:
- one trip?
- one stop event?
- one commute option?

### Step 4: Build a first merged table
Try to create a minimal merged dataset containing:
- scheduled trip info
- real-time update info
- timestamps
- route / stop / trip identifiers

### Step 5: Then move into ML
Only after the merged dataset exists should modeling begin.

---

## How to describe the current status in one sentence
> The project is in the **data ingestion and source validation phase**; static GTFS and real-time Seattle transit feeds have been successfully accessed, but the modeling dataset and prediction target have not yet been built.

---

## Good interview-style description of the current work
> I started by validating public Seattle transit data sources for a commute reliability prediction project. I built a Python ingestion script that downloads static GTFS schedules and GTFS-realtime feeds, saves raw snapshots locally, and inspects the structure of routes, stops, trips, stop times, and live feed entities. The next step is to design a merged modeling table and define the first lateness prediction target.

---

## One-paragraph summary
This project is an early-stage Seattle transit reliability ML project. The main idea is to predict not just ETA, but the risk that a commuter will be late. So far, the work has focused on validating data availability rather than modeling. A Python script was created to download static GTFS data and live GTFS-realtime feeds from King County Metro, inspect the core files and payloads, and save raw snapshots locally. The initial live-feed requests failed because the script used outdated endpoint names, but that was fixed by switching to the current real-time feed filenames. The setup now successfully completes, which proves the raw data sources are accessible. The next steps are to inspect schemas in detail, figure out join keys between static and live data, define the first prediction target, and build a usable training dataset.

---

## Suggested next prompt for another LLM
You can give another LLM this instruction:

“Help me move this project from source-validation into dataset design. I already have a working Python script that downloads King County Metro static GTFS data and real-time JSON feeds. I now want to inspect the schemas, identify join keys between static and live data, narrow the problem to one specific prediction target, and design the first modeling table for a late-arrival prediction MVP.”