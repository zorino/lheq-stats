# LHEQ Stats Website Compilation Workflow

This document describes the complete workflow to compile and update the LHEQ Statistics website.

## Directory Structure

```
lheq-stats/
├── games/                      # Individual game JSON files (45 files)
├── gamesheets/                 # PDF gamesheets (44 files)
├── logs/                       # Scraper output logs (lheq_final_*.json)
├── starting_goalies.json       # Parsed starting goalie data
├── lheq_scraper.py            # Game data scraper (run separately for updates)
├── lheq_stats.py              # **MAIN UNIFIED COMPILER** (runs all processing steps)
└── web/
    ├── data/                   # Website data files
    │   ├── teams.json          # Team statistics
    │   ├── players.json        # Player statistics
    │   ├── games.json          # Game summaries
    │   ├── divisions.json      # Division mappings (static)
    │   └── formations.json     # Probable line combinations
    ├── index.html              # Website homepage
    ├── teams.html              # Teams page
    ├── team-detail.html        # Individual team page
    └── players.html            # Players page
```

## Quick Start - Complete Workflow

### **Single Command to Update Everything:**

```bash
python lheq_stats.py
```

This unified script runs all processing steps in the correct order:
1. Parse starting goalies from PDF gamesheets
2. Compile team and player statistics
3. Assign divisions to teams
4. Analyze line combinations

After running, open `web/index.html` in a browser to view the updated website.

---

## Step-by-Step Workflow

### Step 1: Scrape Game Data (When New Games Are Played)
```bash
python lheq_scraper.py
```

**Purpose**: Fetches game data from LHEQ API and downloads PDF gamesheets

**Inputs**:
- LHEQ API (https://pub-api.play.spordle.com/api/sp/games)

**Outputs**:
- `games/game_*.json` - Individual game files with full boxscore data
- `gamesheets/game_*.pdf` - PDF gamesheets for each game

**When to run**:
- Initial setup
- Weekly/after new games are played to fetch new data
- **Note**: This step is separate and must be run manually when you want to update game data

---

### Step 2: Process All Statistics (Unified Command)
```bash
python lheq_stats.py
```

**Purpose**: Complete statistics processing pipeline

**What it does**:
1. **Parse Starting Goalies** - Extracts starting goalie info from PDF gamesheets using OCR
2. **Compile Statistics** - Processes all game data into team and player stats
3. **Assign Divisions** - Maps teams to their divisions using fuzzy matching
4. **Analyze Formations** - Determines probable line combinations from goals/assists data

**Inputs**:
- `games/*.json` - All individual game files
- `gamesheets/*.pdf` - PDF gamesheets for goalie parsing
- `web/data/divisions.json` - Division reference data (static)

**Outputs**:
- `starting_goalies.json` - Starting goalie data per game
- `web/data/teams.json` - Complete team statistics with divisions
- `web/data/players.json` - Complete player statistics
- `web/data/games.json` - Game summaries
- `web/data/formations.json` - Probable line combinations by team

**When to run**:
- After running `lheq_scraper.py`
- After any manual changes to game data
- Whenever you want to rebuild the website statistics

**Dependencies**: Tesseract OCR and Poppler (for PDF processing)

---

## Advanced Usage - Running Individual Steps

You can run individual steps using the `--step` flag:

```bash
# Run only starting goalie parsing
python lheq_stats.py --step goalies

# Run only statistics compilation
python lheq_stats.py --step stats

# Run only division assignment
python lheq_stats.py --step divisions

# Run only formation analysis
python lheq_stats.py --step formations
```

### Additional Options

```bash
# Skip goalie parsing (if already done)
python lheq_stats.py --skip-goalies

# Skip logo downloads (faster, uses existing logos)
python lheq_stats.py --skip-logos
```

---

## Complete Update Workflow

To update the website after new games are played:

```bash
# 1. Fetch new game data from LHEQ API
python lheq_scraper.py

# 2. Process all statistics (single command!)
python lheq_stats.py
```

That's it! Open `web/index.html` in a browser to view the updated website.

---

## Data Flow Diagram

```
lheq_scraper.py
    ↓
games/*.json + gamesheets/*.pdf
    ↓
lheq_stats.py (Unified Processing)
    │
    ├─→ Parse Starting Goalies
    │       ↓
    │   starting_goalies.json
    │
    ├─→ Compile Statistics
    │       ↓
    │   web/data/teams.json
    │   web/data/players.json
    │   web/data/games.json
    │
    ├─→ Assign Divisions
    │       ↓
    │   web/data/teams.json (updated)
    │
    └─→ Analyze Formations
            ↓
        web/data/formations.json
    ↓
Website Ready (open web/index.html)
```

---

## Script Dependencies

### Python Packages Required
```bash
pip install requests selenium beautifulsoup4 webdriver-manager
pip install pdf2image pytesseract pillow pdfplumber
```

### System Dependencies
- **Tesseract OCR**: For game sheet parsing
- **Poppler**: For PDF to image conversion

---

## Key Notes

1. **Simplified Workflow**: Use `lheq_stats.py` instead of running 4 separate scripts

2. **Correct Execution Order**: The unified script ensures all steps run in the correct order automatically

3. **Starting Goalies**: Goalie games played only counts games where the goalie was marked with "*" in the PDF gamesheet

4. **Division Data**: `web/data/divisions.json` is a static reference file and should not be modified

5. **Error Handling**: The unified script continues processing even if optional steps (like goalie parsing) fail

6. **Incremental Updates**: When new games are added, simply run `lheq_scraper.py` followed by `lheq_stats.py` to update everything

7. **Backup Files**: The web/data directory may contain backup files (`*_backup.json`) - these are previous versions and can be ignored
