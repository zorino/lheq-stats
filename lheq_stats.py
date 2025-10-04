#!/usr/bin/env python3
"""
LHEQ Hockey Statistics Compiler
Unified script to process game data and generate website statistics

This script combines:
- Starting goalie parsing from PDF gamesheets
- Team and player statistics compilation
- Division assignment to teams
- Formation/line combination analysis
"""

import json
import os
import sys
import re
import argparse
import requests
import urllib.parse
from collections import defaultdict, Counter
from datetime import datetime
from difflib import SequenceMatcher
from itertools import combinations

# PDF processing imports
try:
    import pdfplumber
    from pdf2image import convert_from_path
    import pytesseract
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: PDF processing libraries not available. Install pdf2image, pytesseract, and pdfplumber for full functionality.")


# ============================================================================
# STARTING GOALIE PARSER
# ============================================================================

class StartingGoalieParser:
    """Parse PDF gamesheets to identify starting goalies marked with asterisk (*)"""

    def __init__(self, gamesheet_dir='gamesheets', output_file='starting_goalies.json'):
        self.gamesheet_dir = gamesheet_dir
        self.output_file = output_file
        self.starting_goalies_data = {}

    def parse_gamesheet(self, pdf_path):
        """
        Parse a PDF gamesheet to extract starting goalies marked with *
        Returns dict with starting goalies
        """
        if not PDF_SUPPORT:
            print("PDF support not available - skipping gamesheet parsing")
            return None

        try:
            # Use OCR to extract text from PDF image
            images = convert_from_path(pdf_path, first_page=1, last_page=1)

            if not images:
                return None

            # Extract text using OCR
            text = pytesseract.image_to_string(images[0])

            if not text:
                return None

            # Look for goalie entries with asterisk
            lines = text.split('\n')
            starting_goalies = []
            seen_goalies = set()  # Prevent duplicates

            # Find goalies marked with * (may or may not have G)
            for line in lines:
                # Must have asterisk
                if '*' not in line:
                    continue

                # Multiple patterns to handle OCR variations
                # IMPORTANT: Also match patterns where * is at end without G
                # Use IGNORECASE to handle mixed-case OCR output
                patterns = [
                    r'(\d+)/\s*([a-zA-Z][a-zA-Z\s\-\']+?)\s*\*\s*G',  # Number/ Name * G (with slash)
                    r'(\d+)\s+([a-zA-Z][a-zA-Z\s\-\']+?)\s*\*\s*$',  # Number Name * (end of line)
                    r'(\d+)\s+([a-zA-Z][a-zA-Z\s\-\']+?)\s*\*\s*G',  # Number Name * G
                    r'(\d+)\s*\|?([a-zA-Z\s\-\']+?)\s*\*\s*G',    # Number | Name * G
                    r'\|(\d+)\|([a-zA-Z\s\-\']+?)\s*\*\s*G',      # |Number| Name * G
                    r'(\d+)/([a-zA-Z\s\-\']+?)\s*\*\s*$',         # Number/Name * (end of line)
                    r'(\d+)[^\w]*([a-zA-Z][a-zA-Z\s\-\']*?)\s*\*\s*G',  # Number Name * G (loose)
                    r'([a-zA-Z\s\-\']{5,})\s*\*\s*G',             # Name * G (no number)
                    r'([a-zA-Z\s\-\']{5,})\s*\*\s*$',             # Name * (no number, end of line)
                ]

                for pattern in patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        groups = match.groups()
                        number = 0
                        name = ''

                        # Try to extract number and name
                        if len(groups) == 2:
                            if groups[0].isdigit():
                                number = groups[0]
                                name = groups[1].strip()
                            else:
                                # Pattern matched name only, no number
                                number = 0
                                name = groups[0].strip()
                        elif len(groups) == 1:
                            # Name only pattern
                            number = 0
                            name = groups[0].strip()
                        else:
                            continue

                        # Clean up name (remove extra pipes and spaces)
                        name = re.sub(r'[|]+', ' ', name).strip()
                        name = re.sub(r'\s+', ' ', name)  # Collapse multiple spaces

                        # Remove common OCR artifacts
                        name = re.sub(r'\d+$', '', name).strip()  # Remove trailing numbers
                        name = re.sub(r'^[|/\-\s]+', '', name).strip()  # Remove leading junk

                        # Convert to uppercase for consistency
                        name = name.upper()

                        # More lenient sanity check - must be at least 5 chars for a name
                        if name and len(name) >= 5 and name not in seen_goalies:
                            goalie_entry = {
                                'number': int(number) if str(number).isdigit() else 0,
                                'name': name,
                                'line': line.strip()
                            }
                            starting_goalies.append(goalie_entry)
                            seen_goalies.add(name)
                            print(f"  Found starting goalie: #{number} {name}")
                            break

            # Return the goalies found
            return {
                'goalies': starting_goalies,
                'count': len(starting_goalies)
            }

        except Exception as e:
            print(f"  Error parsing {pdf_path}: {e}")
            return None

    def parse_all_gamesheets(self):
        """Parse all PDF gamesheets and extract starting goalie information"""

        if not os.path.exists(self.gamesheet_dir):
            print(f"Directory {self.gamesheet_dir} not found - skipping goalie parsing")
            return False

        pdf_files = [f for f in os.listdir(self.gamesheet_dir) if f.endswith('.pdf')]
        print(f"Found {len(pdf_files)} PDF gamesheets")

        for pdf_file in sorted(pdf_files):
            pdf_path = os.path.join(self.gamesheet_dir, pdf_file)
            print(f"Processing: {pdf_file}")

            # Extract game ID from filename
            game_id_match = re.search(r'game_(\d+)', pdf_file)
            if not game_id_match:
                print(f"  Could not extract game ID from {pdf_file}")
                continue

            game_id = int(game_id_match.group(1))

            # Parse the gamesheet
            result = self.parse_gamesheet(pdf_path)
            if result and result['count'] > 0:
                self.starting_goalies_data[game_id] = result
                print(f"  Found {result['count']} starting goalies")
            else:
                print("  No starting goalies found")

        # Save the results
        with open(self.output_file, 'w') as f:
            json.dump(self.starting_goalies_data, f, indent=2)

        print(f"\nSaved starting goalie data to {self.output_file}")
        print(f"Successfully processed {len(self.starting_goalies_data)} gamesheets")
        return True


# ============================================================================
# HOCKEY STATISTICS COMPILER
# ============================================================================

class HockeyStatsCompiler:
    """Processes JSON game files to compile team and player statistics"""

    def __init__(self, games_dir, web_dir):
        self.games_dir = games_dir
        self.web_dir = web_dir
        self.teams = {}
        self.players = {}
        self.games = []
        self.team_logos = {}
        self.player_positions = {}
        self.starting_goalies = {}

    def load_games(self):
        """Load all JSON game files"""
        print("Loading game files...")
        game_files = [f for f in os.listdir(self.games_dir) if f.endswith('.json')]

        for filename in sorted(game_files):
            file_path = os.path.join(self.games_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    game_data = json.load(f)

                if game_data.get('status') == 'FINAL' and 'boxscore' in game_data:
                    self.games.append(game_data)
                    print(f"  Loaded: {filename}")
                else:
                    print(f"  Skipped (not final): {filename}")
            except Exception as e:
                print(f"  Error loading {filename}: {e}")

        print(f"Total games loaded: {len(self.games)}")

    def initialize_team_stats(self, team_id, team_name):
        """Initialize team statistics structure"""
        if team_id not in self.teams:
            self.teams[team_id] = {
                'id': team_id,
                'name': team_name,
                'games_played': 0,
                'wins': 0,
                'losses': 0,
                'ties': 0,
                'points': 0,
                'goals_for': 0,
                'goals_against': 0,
                'goal_differential': 0,
                'penalty_minutes': 0,
                'powerplay_goals_for': 0,
                'powerplay_goals_against': 0,
                'shorthanded_goals_for': 0,
                'shorthanded_goals_against': 0,
                'home_wins': 0,
                'home_losses': 0,
                'home_ties': 0,
                'away_wins': 0,
                'away_losses': 0,
                'away_ties': 0,
                'logo_url': None
            }

    def initialize_player_stats(self, player_id, player_name, team_id, position):
        """Initialize player statistics structure"""
        if player_id not in self.players:
            self.players[player_id] = {
                'id': player_id,
                'name': player_name,
                'team_id': team_id,
                'position': position,
                'games_played': 0,
                'goals': 0,
                'assists': 0,
                'points': 0,
                'penalty_minutes': 0,
                'powerplay_goals': 0,
                'powerplay_assists': 0,
                'shorthanded_goals': 0,
                'shorthanded_assists': 0,
                'wins': 0,
                'losses': 0,
                'ties': 0,
                'goals_against': 0
            }

    def build_player_positions_index(self):
        """Build a global index of player positions from all rosters"""
        print("Building player positions index...")

        for game in self.games:
            for roster_key in ['home_team_roster', 'away_team_roster']:
                for player in game.get(roster_key, []):
                    player_id = player['participantId']
                    positions = player.get('positions', ['F'])
                    position = positions[0] if positions else 'F'

                    # Handle different position types
                    if position == 'C':
                        position = 'F'
                    elif position in ['Trainer', 'Assistant Coach', 'Head Coach', 'Safety Person', 'Goaltending Coach']:
                        position = 'Coach'
                    elif position not in ['G', 'D', 'F']:
                        position = 'F'

                    self.player_positions[player_id] = position

        print(f"Built position index for {len(self.player_positions)} players")

    def load_starting_goalies(self):
        """Load starting goalie data from parsed PDF gamesheets"""
        starting_goalies_file = 'starting_goalies.json'

        if not os.path.exists(starting_goalies_file):
            print(f"Warning: {starting_goalies_file} not found. Goalie statistics may be inaccurate.")
            return

        try:
            with open(starting_goalies_file, 'r') as f:
                data = json.load(f)

            # Convert game IDs to integers and create mapping
            for game_id_str, game_data in data.items():
                game_id = int(game_id_str)
                starting_names = [goalie['name'] for goalie in game_data['goalies']]
                self.starting_goalies[game_id] = starting_names

            print(f"Loaded starting goalie data for {len(self.starting_goalies)} games")

        except Exception as e:
            print(f"Error loading starting goalies: {e}")
            print("Proceeding without starting goalie data.")

    def normalize_name(self, name):
        """Normalize player name for comparison (remove accents, etc.)"""
        import unicodedata
        normalized = unicodedata.normalize('NFD', name)
        ascii_name = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        return ascii_name.upper().strip()

    def is_starting_goalie(self, game_id, player_name):
        """Check if a goalie was a starter in the given game"""
        # If no starting goalie data for this game, don't count any goalies
        if game_id not in self.starting_goalies:
            return False

        # Get list of starting goalie names for this game
        starting_names = self.starting_goalies[game_id]
        normalized_player_name = self.normalize_name(player_name)

        # Check if this player matches any starting goalie
        for starting_name in starting_names:
            if self.normalize_name(starting_name) == normalized_player_name:
                return True

        return False

    def get_player_position(self, boxscore, player_id):
        """Get player position from global index or current roster"""
        if player_id in self.player_positions:
            return self.player_positions[player_id]

        for player in boxscore.get('roster', []):
            if player['participantId'] == player_id:
                positions = player.get('positions', ['F'])
                return positions[0] if positions else 'F'
        return 'F'

    def process_games(self):
        """Process all games to compile statistics"""
        print("Processing game statistics...")

        self.build_player_positions_index()
        self.load_starting_goalies()

        player_games = {}

        for game in self.games:
            if 'boxscore' not in game:
                continue

            boxscore = game['boxscore']
            home_score = game.get('home_score', 0)
            away_score = game.get('away_score', 0)

            teams = boxscore.get('teams', [])
            if len(teams) < 2:
                continue

            home_team = teams[0]
            away_team = teams[1]
            home_team_id = home_team['id']
            away_team_id = away_team['id']
            home_team_name = home_team['name']
            away_team_name = away_team['name']

            # Store logos
            if home_team.get('logoUrl'):
                self.team_logos[home_team_id] = home_team['logoUrl']
            if away_team.get('logoUrl'):
                self.team_logos[away_team_id] = away_team['logoUrl']

            # Initialize teams
            self.initialize_team_stats(home_team_id, home_team_name)
            self.initialize_team_stats(away_team_id, away_team_name)

            self.teams[home_team_id]['logo_url'] = home_team.get('logoUrl')
            self.teams[away_team_id]['logo_url'] = away_team.get('logoUrl')

            # Update games played
            self.teams[home_team_id]['games_played'] += 1
            self.teams[away_team_id]['games_played'] += 1

            # Update goals
            self.teams[home_team_id]['goals_for'] += home_score
            self.teams[home_team_id]['goals_against'] += away_score
            self.teams[away_team_id]['goals_for'] += away_score
            self.teams[away_team_id]['goals_against'] += home_score

            # Determine outcome
            if home_score > away_score:
                self.teams[home_team_id]['wins'] += 1
                self.teams[home_team_id]['home_wins'] += 1
                self.teams[home_team_id]['points'] += 2
                self.teams[away_team_id]['losses'] += 1
                self.teams[away_team_id]['away_losses'] += 1
            elif away_score > home_score:
                self.teams[away_team_id]['wins'] += 1
                self.teams[away_team_id]['away_wins'] += 1
                self.teams[away_team_id]['points'] += 2
                self.teams[home_team_id]['losses'] += 1
                self.teams[home_team_id]['home_losses'] += 1
            else:
                self.teams[home_team_id]['ties'] += 1
                self.teams[home_team_id]['home_ties'] += 1
                self.teams[home_team_id]['points'] += 1
                self.teams[away_team_id]['ties'] += 1
                self.teams[away_team_id]['away_ties'] += 1
                self.teams[away_team_id]['points'] += 1

            # Process goals
            for goal in boxscore.get('goals', []):
                scorer_id = goal['participant']['participantId']
                scorer_name = goal['participant']['fullName']
                team_id = goal['teamId']

                position = self.get_player_position(boxscore, scorer_id)
                if position == 'C':
                    position = 'F'
                self.initialize_player_stats(scorer_id, scorer_name, team_id, position)

                self.players[scorer_id]['goals'] += 1
                self.players[scorer_id]['points'] += 1

                if scorer_id not in player_games:
                    player_games[scorer_id] = set()
                player_games[scorer_id].add(game['id'])

                if goal.get('isPowerplay'):
                    self.players[scorer_id]['powerplay_goals'] += 1
                    self.teams[team_id]['powerplay_goals_for'] += 1
                    opponent_id = away_team_id if team_id == home_team_id else home_team_id
                    self.teams[opponent_id]['powerplay_goals_against'] += 1

                if goal.get('isShorthanded'):
                    self.players[scorer_id]['shorthanded_goals'] += 1
                    self.teams[team_id]['shorthanded_goals_for'] += 1
                    opponent_id = away_team_id if team_id == home_team_id else home_team_id
                    self.teams[opponent_id]['shorthanded_goals_against'] += 1

                # Process assists
                for assist in goal.get('assists', []):
                    assist_id = assist['participantId']
                    assist_name = assist['fullName']

                    position = self.get_player_position(boxscore, assist_id)
                    if position == 'C':
                        position = 'F'
                    self.initialize_player_stats(assist_id, assist_name, team_id, position)

                    self.players[assist_id]['assists'] += 1
                    self.players[assist_id]['points'] += 1

                    if assist_id not in player_games:
                        player_games[assist_id] = set()
                    player_games[assist_id].add(game['id'])

                    if goal.get('isPowerplay'):
                        self.players[assist_id]['powerplay_assists'] += 1
                    if goal.get('isShorthanded'):
                        self.players[assist_id]['shorthanded_assists'] += 1

            # Process penalties
            for penalty in boxscore.get('penalties', []):
                if 'participant' not in penalty or 'participantId' not in penalty['participant']:
                    continue

                player_id = penalty['participant']['participantId']
                player_name = penalty['participant']['fullName']
                team_id = penalty['teamId']

                duration_name = penalty.get('duration', {}).get('name', '')
                if 'Minor' in duration_name or 'Mineure' in duration_name:
                    penalty_minutes = 2
                elif 'Major' in duration_name or 'Majeure' in duration_name:
                    penalty_minutes = 5
                elif 'Misconduct' in duration_name:
                    penalty_minutes = 10
                else:
                    penalty_minutes = 2

                position = self.get_player_position(boxscore, player_id)
                if position == 'C':
                    position = 'F'
                self.initialize_player_stats(player_id, player_name, team_id, position)

                self.players[player_id]['penalty_minutes'] += penalty_minutes
                self.teams[team_id]['penalty_minutes'] += penalty_minutes

                if player_id not in player_games:
                    player_games[player_id] = set()
                player_games[player_id].add(game['id'])

            # Process rosters for goalie stats
            for player in game.get('home_team_roster', []):
                player_id = player['participantId']
                player_name = player['participant']['fullName']
                team_id = home_team_id
                position = self.get_player_position(boxscore, player_id)

                if position not in ['F', 'D', 'G', 'C']:
                    continue

                if position == 'C':
                    position = 'F'

                self.initialize_player_stats(player_id, player_name, team_id, position)

                if player_id not in player_games:
                    player_games[player_id] = set()
                player_games[player_id].add(game['id'])

                if position == 'G' and self.is_starting_goalie(game['id'], player_name):
                    if home_score > away_score:
                        self.players[player_id]['wins'] += 1
                    elif home_score < away_score:
                        self.players[player_id]['losses'] += 1
                    else:
                        self.players[player_id]['ties'] += 1
                    self.players[player_id]['goals_against'] += away_score

            for player in game.get('away_team_roster', []):
                player_id = player['participantId']
                player_name = player['participant']['fullName']
                team_id = away_team_id
                position = self.get_player_position(boxscore, player_id)

                if position not in ['F', 'D', 'G', 'C']:
                    continue

                if position == 'C':
                    position = 'F'

                self.initialize_player_stats(player_id, player_name, team_id, position)

                if player_id not in player_games:
                    player_games[player_id] = set()
                player_games[player_id].add(game['id'])

                if position == 'G' and self.is_starting_goalie(game['id'], player_name):
                    if away_score > home_score:
                        self.players[player_id]['wins'] += 1
                    elif away_score < home_score:
                        self.players[player_id]['losses'] += 1
                    else:
                        self.players[player_id]['ties'] += 1
                    self.players[player_id]['goals_against'] += home_score

        # Update games_played
        for player_id, game_set in player_games.items():
            if player_id in self.players:
                if self.players[player_id]['position'] == 'G':
                    started_games = 0
                    player_name = self.players[player_id]['name']
                    for game_id in game_set:
                        if self.is_starting_goalie(game_id, player_name):
                            started_games += 1
                    self.players[player_id]['games_played'] = started_games
                else:
                    self.players[player_id]['games_played'] = len(game_set)

        # Calculate goal differentials
        for team in self.teams.values():
            team['goal_differential'] = team['goals_for'] - team['goals_against']

        print(f"Processed {len(self.teams)} teams and {len(self.players)} players")

    def download_team_logos(self):
        """Download team logos to assets folder"""
        print("Downloading team logos...")
        logos_dir = os.path.join(self.web_dir, 'assets', 'logos')
        os.makedirs(logos_dir, exist_ok=True)

        for team_id, logo_url in self.team_logos.items():
            if not logo_url:
                continue

            try:
                parsed_url = urllib.parse.urlparse(logo_url)
                file_ext = os.path.splitext(parsed_url.path)[1] or '.png'
                filename = f"team_{team_id}{file_ext}"
                filepath = os.path.join(logos_dir, filename)

                response = requests.get(logo_url, timeout=10)
                response.raise_for_status()

                with open(filepath, 'wb') as f:
                    f.write(response.content)

                if team_id in self.teams:
                    self.teams[team_id]['local_logo'] = f"assets/logos/{filename}"

                print(f"  Downloaded logo for team {team_id}")

            except Exception as e:
                print(f"  Failed to download logo for team {team_id}: {e}")

    def save_data(self):
        """Save compiled statistics to JSON files"""
        print("Saving statistics data...")

        data_dir = os.path.join(self.web_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)

        # Sort teams by points
        teams_list = sorted(
            self.teams.values(),
            key=lambda x: (-x['points'], -x['goal_differential'], x['name'])
        )

        # Sort players by points
        players_list = sorted(
            self.players.values(),
            key=lambda x: (-x['points'], -x['goals'], x['name'])
        )

        # Save teams
        with open(os.path.join(data_dir, 'teams.json'), 'w', encoding='utf-8') as f:
            json.dump(teams_list, f, indent=2, ensure_ascii=False)

        # Save players
        with open(os.path.join(data_dir, 'players.json'), 'w', encoding='utf-8') as f:
            json.dump(players_list, f, indent=2, ensure_ascii=False)

        # Save games
        games_summary = []
        for game in self.games:
            games_summary.append({
                'id': game['id'],
                'date': game['date'],
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'home_score': game.get('home_score', 0),
                'away_score': game.get('away_score', 0),
                'status': game['status']
            })

        with open(os.path.join(data_dir, 'games.json'), 'w', encoding='utf-8') as f:
            json.dump(games_summary, f, indent=2, ensure_ascii=False)

        print(f"Saved data files to {data_dir}")
        print(f"\nSummary:")
        print(f"  Teams: {len(teams_list)}")
        print(f"  Players: {len(players_list)}")
        print(f"  Games: {len(games_summary)}")

        if teams_list:
            print(f"\nTop team: {teams_list[0]['name']} ({teams_list[0]['points']} pts)")

        if players_list:
            print(f"Top scorer: {players_list[0]['name']} ({players_list[0]['points']} pts)")

    def compile_all(self):
        """Run the complete compilation process"""
        self.load_games()
        self.process_games()
        self.download_team_logos()
        self.save_data()


# ============================================================================
# DIVISION ASSIGNER
# ============================================================================

class DivisionAssigner:
    """Assigns teams to divisions using fuzzy string matching"""

    def __init__(self, web_dir):
        self.web_dir = web_dir

    def similarity(self, a, b):
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def normalize_team_name(self, name):
        """Normalize team name for better matching"""
        name = name.lower()

        replacements = {
            'grenadiers lac st-louis': 'grenadiers du lac st-louis',
            'lions lac st-louis': 'lions du lac st-louis',
            'citadelles rouyn-noranda': 'citadelles de rouyn-noranda',
            'seigneurs mille-îles': 'seigneurs des mille-îles',
            'conquérants basses-laurentides': 'conquérants basses-laurentides',
            'forestiers abitibi-témiscaming': 'forestiers abitibi-témiscaming',
        }

        for old, new in replacements.items():
            if old in name:
                name = new
                break

        return name

    def assign_divisions(self):
        """Assign divisions to all teams"""
        print("Assigning divisions to teams...")

        teams_file = os.path.join(self.web_dir, 'data', 'teams.json')
        divisions_file = os.path.join(self.web_dir, 'data', 'divisions.json')

        with open(teams_file, 'r', encoding='utf-8') as f:
            teams = json.load(f)

        with open(divisions_file, 'r', encoding='utf-8') as f:
            divisions_data = json.load(f)

        team_to_division = divisions_data['team_to_division']

        for team in teams:
            team_name = team['name']
            division_found = None
            best_match_score = 0
            best_match_division = None

            # Try exact match first
            for div_team_name, division in team_to_division.items():
                if self.normalize_team_name(team_name) == self.normalize_team_name(div_team_name):
                    division_found = division
                    break

            # Try fuzzy matching
            if not division_found:
                for div_team_name, division in team_to_division.items():
                    score = self.similarity(self.normalize_team_name(team_name), self.normalize_team_name(div_team_name))
                    if score > best_match_score:
                        best_match_score = score
                        best_match_division = division

                if best_match_score > 0.7:
                    division_found = best_match_division
                    print(f"  Fuzzy match: '{team_name}' -> '{best_match_division}' (score: {best_match_score:.2f})")

            # Add division
            if division_found:
                team['division'] = division_found
                print(f"  ✓ {team_name} -> {division_found}")
            else:
                team['division'] = "Unknown"
                print(f"  ✗ No division found for: {team_name}")

        # Save updated teams
        with open(teams_file, 'w', encoding='utf-8') as f:
            json.dump(teams, f, indent=2, ensure_ascii=False)

        # Print summary
        division_counts = {}
        for team in teams:
            div = team['division']
            division_counts[div] = division_counts.get(div, 0) + 1

        print("\nDivision Summary:")
        for division, count in division_counts.items():
            print(f"  {division}: {count} teams")


# ============================================================================
# FORMATION DETECTOR
# ============================================================================

class FormationDetector:
    """Analyzes goals and assists to detect forward trios and defense duos"""

    def __init__(self, games_data):
        self.games = games_data
        self.team_formations = defaultdict(lambda: {
            'even_strength_f_trios': defaultdict(int),
            'even_strength_f_pairs': defaultdict(int),
            'even_strength_d_duos': defaultdict(int),
            'powerplay_units': defaultdict(int),
            'penalty_kill_units': defaultdict(int),
            'player_positions': {}
        })

    def analyze_formations(self):
        """Main method to analyze all formations"""
        print("Analyzing player formations from goals and assists...")

        for game in self.games:
            if 'boxscore' not in game:
                continue

            self._build_position_map(game)
            self._analyze_goals(game)

        self._calculate_confidence_scores()
        print(f"Formation analysis completed for {len(self.team_formations)} teams")

    def _build_position_map(self, game):
        """Build position mapping for players in this game"""
        teams = game.get('boxscore', {}).get('teams', [])
        if len(teams) < 2:
            return

        home_team_id = teams[0]['id']
        away_team_id = teams[1]['id']

        for roster_key in ['home_team_roster', 'away_team_roster']:
            team_id = home_team_id if roster_key == 'home_team_roster' else away_team_id

            for player in game.get(roster_key, []):
                player_id = player['participantId']
                positions = player.get('positions', ['F'])
                position = positions[0] if positions else 'F'

                if position not in ['F', 'D', 'G', 'C']:
                    continue

                if position == 'C':
                    position = 'F'

                self.team_formations[team_id]['player_positions'][player_id] = {
                    'name': player['participant']['fullName'],
                    'position': position,
                    'number': player.get('number')
                }

    def _analyze_goals(self, game):
        """Analyze each goal for formation patterns"""
        boxscore = game.get('boxscore', {})

        for goal in boxscore.get('goals', []):
            team_id = goal.get('teamId')
            if not team_id:
                continue

            players_involved = []
            players_involved.append(goal['participant']['participantId'])

            for assist in goal.get('assists', []):
                players_involved.append(assist['participantId'])

            self._detect_formations_in_goal(team_id, players_involved, goal)

    def _detect_formations_in_goal(self, team_id, players_involved, goal):
        """Detect formation patterns in a single goal"""
        if len(players_involved) < 2:
            return

        team_data = self.team_formations[team_id]
        positioned_players = []

        for player_id in players_involved:
            if player_id in team_data['player_positions']:
                player_info = team_data['player_positions'][player_id]
                positioned_players.append({
                    'id': player_id,
                    'name': player_info['name'],
                    'position': player_info['position']
                })

        if len(positioned_players) < 2:
            return

        is_powerplay = goal.get('isPowerplay', False)
        is_shorthanded = goal.get('isShorthanded', False)

        forwards = [p for p in positioned_players if p['position'] == 'F']
        defensemen = [p for p in positioned_players if p['position'] == 'D']

        if is_powerplay:
            self._detect_powerplay_units(team_id, positioned_players, goal)
        elif is_shorthanded:
            self._detect_penalty_kill_units(team_id, positioned_players, goal)
        else:
            self._detect_even_strength_formations(team_id, forwards, defensemen, goal)

    def _detect_even_strength_formations(self, team_id, forwards, defensemen, goal):
        """Detect even strength formations"""
        team_data = self.team_formations[team_id]

        if len(forwards) >= 3:
            for trio in combinations(forwards, 3):
                trio_key = tuple(sorted([p['id'] for p in trio]))
                team_data['even_strength_f_trios'][trio_key] += 1

        if len(forwards) >= 2:
            for pair in combinations(forwards, 2):
                pair_key = tuple(sorted([p['id'] for p in pair]))
                team_data['even_strength_f_pairs'][pair_key] += 1

        if len(defensemen) >= 2:
            for pair in combinations(defensemen, 2):
                pair_key = tuple(sorted([p['id'] for p in pair]))
                team_data['even_strength_d_duos'][pair_key] += 1

    def _detect_powerplay_units(self, team_id, players, goal):
        """Detect powerplay units"""
        team_data = self.team_formations[team_id]
        unit_key = tuple(sorted([p['id'] for p in players]))
        team_data['powerplay_units'][unit_key] += 1

    def _detect_penalty_kill_units(self, team_id, players, goal):
        """Detect penalty kill units"""
        team_data = self.team_formations[team_id]
        unit_key = tuple(sorted([p['id'] for p in players]))
        team_data['penalty_kill_units'][unit_key] += 1

    def _calculate_confidence_scores(self):
        """Calculate confidence scores for formations"""
        for team_id, team_data in self.team_formations.items():
            if team_data['even_strength_f_trios']:
                max_trio_count = max(team_data['even_strength_f_trios'].values())
                for trio_key in team_data['even_strength_f_trios']:
                    count = team_data['even_strength_f_trios'][trio_key]
                    confidence = min(100, (count / max(max_trio_count, 1)) * 100)
                    team_data['even_strength_f_trios'][trio_key] = {
                        'count': count,
                        'confidence': round(confidence, 1)
                    }

            if team_data['even_strength_d_duos']:
                max_duo_count = max(team_data['even_strength_d_duos'].values())
                for duo_key in team_data['even_strength_d_duos']:
                    count = team_data['even_strength_d_duos'][duo_key]
                    confidence = min(100, (count / max(max_duo_count, 1)) * 100)
                    team_data['even_strength_d_duos'][duo_key] = {
                        'count': count,
                        'confidence': round(confidence, 1)
                    }

    def get_team_formations(self, team_id):
        """Get formatted formations for a specific team"""
        if team_id not in self.team_formations:
            return None

        team_data = self.team_formations[team_id]

        return {
            'f_lines': self._get_optimal_forward_lines(team_data),
            'd_pairs': self._get_optimal_defense_pairs(team_data),
            'powerplay_units': self._get_special_teams_units(team_data, 'powerplay_units'),
            'penalty_kill_units': self._get_special_teams_units(team_data, 'penalty_kill_units')
        }

    def _get_optimal_forward_lines(self, team_data):
        """Get optimal forward line combinations"""
        trio_candidates = []
        if team_data['even_strength_f_trios']:
            for trio_key, trio_data in team_data['even_strength_f_trios'].items():
                if isinstance(trio_data, dict):
                    count = trio_data['count']
                    confidence = trio_data['confidence']
                else:
                    count = trio_data
                    confidence = 50.0

                if count >= 1:
                    players = []
                    for player_id in trio_key:
                        if player_id in team_data['player_positions']:
                            players.append(team_data['player_positions'][player_id])

                    if len(players) == 3:
                        trio_candidates.append({
                            'players': players,
                            'player_ids': set(trio_key),
                            'count': count,
                            'confidence': confidence,
                            'is_trio': True
                        })

        pair_candidates = []
        if team_data['even_strength_f_pairs']:
            for pair_key, pair_data in team_data['even_strength_f_pairs'].items():
                count = pair_data if isinstance(pair_data, int) else pair_data['count']
                if count >= 2:
                    players = []
                    for player_id in pair_key:
                        if player_id in team_data['player_positions']:
                            players.append(team_data['player_positions'][player_id])

                    if len(players) == 2:
                        pair_candidates.append({
                            'players': players,
                            'player_ids': set(pair_key),
                            'count': count,
                            'confidence': min(100, count * 20),
                            'is_trio': False
                        })

        all_candidates = trio_candidates + pair_candidates
        all_candidates.sort(key=lambda x: x['count'], reverse=True)

        assigned_lines = []
        used_players = set()

        for candidate in all_candidates:
            if not candidate['player_ids'].intersection(used_players):
                assigned_lines.append({
                    'players': candidate['players'],
                    'count': candidate['count'],
                    'confidence': candidate['confidence'],
                    'type': 'Trio' if candidate['is_trio'] else 'Duo'
                })
                used_players.update(candidate['player_ids'])

                if len(assigned_lines) >= 4:
                    break

        return assigned_lines

    def _get_optimal_defense_pairs(self, team_data):
        """Get optimal defense pair combinations"""
        pair_candidates = []
        if team_data['even_strength_d_duos']:
            for pair_key, pair_data in team_data['even_strength_d_duos'].items():
                if isinstance(pair_data, dict):
                    count = pair_data['count']
                    confidence = pair_data['confidence']
                else:
                    count = pair_data
                    confidence = 50.0

                if count >= 1:
                    players = []
                    for player_id in pair_key:
                        if player_id in team_data['player_positions']:
                            players.append(team_data['player_positions'][player_id])

                    if len(players) == 2:
                        pair_candidates.append({
                            'players': players,
                            'player_ids': set(pair_key),
                            'count': count,
                            'confidence': confidence
                        })

        pair_candidates.sort(key=lambda x: x['count'], reverse=True)

        assigned_pairs = []
        used_players = set()

        for candidate in pair_candidates:
            if not candidate['player_ids'].intersection(used_players):
                assigned_pairs.append({
                    'players': candidate['players'],
                    'count': candidate['count'],
                    'confidence': candidate['confidence']
                })
                used_players.update(candidate['player_ids'])

                if len(assigned_pairs) >= 3:
                    break

        return assigned_pairs

    def _get_special_teams_units(self, team_data, unit_type):
        """Get special teams units"""
        units = []
        if team_data[unit_type]:
            sorted_units = sorted(
                team_data[unit_type].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]

            for unit_key, count in sorted_units:
                if count >= 1:
                    players = []
                    for player_id in unit_key:
                        if player_id in team_data['player_positions']:
                            players.append(team_data['player_positions'][player_id])

                    if len(players) >= 2:
                        units.append({
                            'players': players,
                            'count': count,
                            'confidence': min(100, count * 20)
                        })

        return units

    def export_formations(self, output_file):
        """Export formations to JSON file"""
        formations_data = {}

        for team_id in self.team_formations:
            formations_data[team_id] = self.get_team_formations(team_id)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(formations_data, f, indent=2, ensure_ascii=False)

        print(f"Formations exported to {output_file}")


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def main():
    """Main function to orchestrate the complete workflow"""

    parser = argparse.ArgumentParser(
        description='LHEQ Hockey Statistics Compiler - Process game data and generate website statistics'
    )
    parser.add_argument(
        '--step',
        choices=['goalies', 'stats', 'divisions', 'formations', 'all'],
        default='all',
        help='Run a specific step or all steps (default: all)'
    )
    parser.add_argument(
        '--skip-goalies',
        action='store_true',
        help='Skip goalie parsing step'
    )
    parser.add_argument(
        '--skip-logos',
        action='store_true',
        help='Skip logo download step'
    )

    args = parser.parse_args()

    # Configuration
    games_dir = "/home/mderaspe/projects/hockey/lheq-stats/games"
    web_dir = "/home/mderaspe/projects/hockey/lheq-stats/web"
    gamesheet_dir = "gamesheets"

    print("=" * 70)
    print("LHEQ HOCKEY STATISTICS COMPILER")
    print("=" * 70)
    print()

    success = True

    try:
        # Step 1: Parse Starting Goalies
        if args.step in ['goalies', 'all'] and not args.skip_goalies:
            print("\n" + "=" * 70)
            print("STEP 1: PARSING STARTING GOALIES FROM PDF GAMESHEETS")
            print("=" * 70)
            try:
                parser = StartingGoalieParser(gamesheet_dir)
                parser.parse_all_gamesheets()
                print("✓ Starting goalie parsing completed")
            except Exception as e:
                print(f"✗ Starting goalie parsing failed: {e}")
                print("Continuing with remaining steps...")

        # Step 2: Compile Statistics
        if args.step in ['stats', 'all']:
            print("\n" + "=" * 70)
            print("STEP 2: COMPILING TEAM AND PLAYER STATISTICS")
            print("=" * 70)
            compiler = HockeyStatsCompiler(games_dir, web_dir)
            compiler.compile_all()

            if args.skip_logos:
                print("(Skipped logo download as requested)")

            print("✓ Statistics compilation completed")

        # Step 3: Assign Divisions
        if args.step in ['divisions', 'all']:
            print("\n" + "=" * 70)
            print("STEP 3: ASSIGNING DIVISIONS TO TEAMS")
            print("=" * 70)
            assigner = DivisionAssigner(web_dir)
            assigner.assign_divisions()
            print("✓ Division assignment completed")

        # Step 4: Analyze Formations
        if args.step in ['formations', 'all']:
            print("\n" + "=" * 70)
            print("STEP 4: ANALYZING LINE COMBINATIONS")
            print("=" * 70)

            # Load games
            print("Loading game files for formation analysis...")
            games = []
            for filename in os.listdir(games_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(games_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            game_data = json.load(f)
                            if game_data.get('status') == 'FINAL' and 'boxscore' in game_data:
                                games.append(game_data)
                    except Exception as e:
                        print(f"  Error loading {filename}: {e}")

            print(f"Loaded {len(games)} games for formation analysis")

            # Analyze formations
            detector = FormationDetector(games)
            detector.analyze_formations()

            # Export results
            output_file = os.path.join(web_dir, 'data', 'formations.json')
            detector.export_formations(output_file)
            print("✓ Formation analysis completed")

        print("\n" + "=" * 70)
        print("ALL STEPS COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\nWebsite data files have been updated in: {web_dir}/data/")
        print("You can now open web/index.html in a browser to view the statistics.")
        print()

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        success = False

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
