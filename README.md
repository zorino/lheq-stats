# LHEQ Hockey Statistics

Complete web application for the Ligue de Hockey d'Excellence du Québec (LHEQ), providing comprehensive game data, detailed player statistics, and team analytics.

## Features

✅ **Game Data Collection**: Python-based scraping system for games, scores, and game sheets
✅ **Player Statistics**: Individual stats for skaters (goals, assists, points, PIM) and goalies (GP, W/L/T, GA, GAA)
✅ **Team Standings**: Complete team statistics including W/L/T records, goals for/against, home/away splits
✅ **Division Organization**: Teams organized into three divisions (L'Entrepôt du Hockey, Hockey Experts, Sports Rousseau)
✅ **Formation Analysis**: Analyzes probable line combinations based on on-ice goal/assist data
✅ **Interactive Web Interface**: Filter by division, team, position with sortable DataTables
✅ **Starting Goalie Tracking**: Parses PDF game sheets to identify starting goalies (marked with "*")

## Project Structure

### Core Python Scripts
- **`lheq_stats.py`** - Unified statistics compiler (runs all processing steps)
- `lheq_scraper.py` - Scrapes game data and downloads PDF gamesheets from LHEQ API

### Web Application (`web/`)
- `index.html` - Homepage with recent games and overview
- `teams.html` - Team standings with division filtering
- `team-detail.html` - Individual team page with roster, stats, and formations
- `players.html` - Player statistics with filtering by division, team, and position
- `assets/js/` - JavaScript for data management, filtering, and DataTables
- `data/` - JSON data files (teams, players, games, divisions, formations)

### Data Files
- `web/data/teams.json` - Team statistics and division assignments
- `web/data/players.json` - Player statistics (skaters and goalies)
- `web/data/games.json` - Game results and scores
- `web/data/divisions.json` - Division organization and team mappings
- `web/data/formations.json` - Probable line combinations by team
- `web/data/games/` - Individual game JSON files with detailed statistics
- `web/data/gamesheets/` - Downloaded PDF gamesheets for each game
- `starting_goalies.json` - Starting goalie data extracted from game sheets

## Usage

### Quick Start - Complete Workflow

```bash
# 1. Scrape game data (when new games are available)
python lheq_scraper.py

# 2. Process all statistics with single command
python lheq_stats.py

# 3. View the website
# Open web/index.html in a web browser
```

### What `lheq_stats.py` Does

The unified statistics compiler automatically runs all processing steps in the correct order:

1. **Parse Starting Goalies** - Extracts starting goalie info from PDF gamesheets using Gemini AI
2. **Compile Statistics** - Processes game data to generate team and player statistics
3. **Assign Divisions** - Maps teams to divisions using fuzzy string matching
4. **Analyze Formations** - Determines probable line combinations from goals/assists data

### Advanced Options

```bash
# Run specific steps only
python lheq_stats.py --step goalies      # Parse starting goalies only
python lheq_stats.py --step stats        # Compile statistics only
python lheq_stats.py --step divisions    # Assign divisions only
python lheq_stats.py --step formations   # Analyze formations only

# Skip optional steps
python lheq_stats.py --skip-goalies      # Skip goalie parsing
python lheq_stats.py --skip-logos        # Skip logo downloads
```

For detailed workflow information, see [WORKFLOW.md](WORKFLOW.md).

## Key Features

### Player Statistics
- **Skaters**: Goals, Assists, Points, Penalty Minutes, Powerplay/Shorthanded stats
- **Goalies**: Games Played, Wins, Losses, Ties, Goals Against, GAA
- **Starting Goalies**: Only counts games where goalie was marked with "*" in game sheet

### Team Statistics
- **Record**: Games Played, Wins, Losses, Ties, Points
- **Scoring**: Goals For, Goals Against, Goal Differential
- **Discipline**: Penalty Minutes
- **Home/Away Splits**: Win/loss/tie records for home and away games
- **Division Assignment**: Teams organized into three divisions

### Formation Analysis
- **Forward Trios**: Identifies probable forward line combinations
- **Defense Pairings**: Analyzes defensive pair combinations
- **Based on Goals/Assists**: Uses actual on-ice data to determine linemates
- **Incomplete Formations**: Shows "?" for missing players in partial lines

### Web Interface
- **Division Filter**: Filter teams and players by division
- **Team Filter**: View players from specific teams
- **Position Filter**: Separate views for forwards, defensemen, and goalies
- **Search**: Find players by name
- **Sortable Tables**: Click column headers to sort (powered by DataTables)
- **Team Detail Pages**: Complete roster, stats, and probable formations for each team

## Dependencies

### Python Packages
```bash
pip install requests
```

### System Dependencies
- **Gemini AI CLI** (for game sheet parsing) - Install from [Google AI Studio](https://ai.google.dev/)
  - Required for extracting starting goalie information from PDF gamesheets
  - Uses the `gemini` command-line tool with French language prompts

## Divisions

The LHEQ is organized into three divisions:

### L'Entrepôt du Hockey (8 teams)
- Albatros de l'Est-du-Québec
- As de Québec
- Blizzard Séminaire St-François
- Canam de Beauce-Appalaches
- Cascades Élite
- Corsaires de Pointe-Lévy
- Espoirs Saguenay - Lac St-Jean
- Estacades de la Mauricie
- Nord-Côtiers

### Hockey Experts (7 teams)
- Collège Français Rive-Sud
- Dynamiques de CCL
- Grenadiers du Lac St-Louis
- Harfangs de Sherbrooke
- Lions du Lac St-Louis
- Noir et Or De Mortagne
- Vert et Noir école Fadette

### Sports Rousseau (8 teams)
- Citadelles de Rouyn-Noranda
- Conquérants Basses-Laurentides
- Forestiers Abitibi-Témiscaming
- Intrépide de l'Outaouais
- National de Montréal
- Pionniers de Lanaudière
- Rocket Jr de Laval
- Seigneurs des Mille-Îles
- Sélects du Nord

## Technical Notes

### Game Sheet Parsing
- PDF game sheets accessed via: `https://pdf.play.spordle.com/game/{GAME_ID}?locale=fr`
- Gemini AI used to extract starting goalie information from PDFs
- Starting goalies identified by "*" marker next to their name in the gamesheet
- French language prompts ensure accurate extraction: "extrait moi les gardiens partant du pdf suivant"

### Statistics Calculation
- **Team Points**: 2 points for win, 1 point for tie, 0 for loss
- **Goalie GAA**: (Goals Against × Game Length) / Minutes Played
- **Starting Goalie Games**: Only counts games where goalie was marked with "*" in game sheet
