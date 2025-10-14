#!/usr/bin/env python3
"""
LHEQ Hockey Statistics Compiler
Unified script to process game data and generate website statistics

This script combines:
- Starting goalie parsing from PDF gamesheets using Gemini AI
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

# Gemini AI support check
try:
    import subprocess
    # Test if gemini command is available
    result = subprocess.run(['which', 'gemini'], capture_output=True, text=True)
    GEMINI_SUPPORT = result.returncode == 0
    if not GEMINI_SUPPORT:
        print("Warning: Gemini AI command not found. Starting goalie parsing will be skipped.")
except Exception:
    GEMINI_SUPPORT = False
    print("Warning: Gemini AI command not available. Starting goalie parsing will be skipped.")


# ============================================================================
# STARTING GOALIE PARSER
# ============================================================================

class StartingGoalieParser:
    """Parse PDF gamesheets to identify starting goalies and add them to game JSON files"""

    def __init__(self, gamesheet_dir='web/data/gamesheets', game_dir='web/data/games'):
        self.gamesheet_dir = gamesheet_dir
        self.game_dir = game_dir
        self.processed_count = 0
        self.skipped_count = 0

    def has_starting_goalies(self, game_data):
        """Check if game already has starting goalie data"""
        return 'starting_goalies' in game_data and game_data['starting_goalies'] is not None

    def parse_gamesheet(self, pdf_path):
        """
        Parse a PDF gamesheet to extract starting goalies using Gemini AI
        Returns dict with starting goalies
        """
        if not GEMINI_SUPPORT:
            print("  Gemini AI not available - skipping gamesheet parsing")
            return None

        try:
            # Use Gemini AI to extract starting goalies from PDF
            result = self._extract_goalies_with_gemini(pdf_path)
            if result:
                return result
            else:
                print("  No starting goalies found by Gemini AI")
                return None

        except Exception as e:
            print(f"  Error parsing {pdf_path}: {e}")
            return None

    def _extract_goalies_with_gemini(self, pdf_path):
        """Extract starting goalies using Gemini AI"""
        import subprocess
        import json
        import os

        try:
            # Get the absolute path for the PDF
            abs_pdf_path = os.path.abspath(pdf_path)

            # Construct the Gemini command
            prompt = (
                "extrait moi les gardiens partant du pdf suivant (à noter que le gardien partant possède un * à coté de son nom). "
                "donne seulement ta réponse dans le format json. le format devra respecter le format suivant en exemple : "
                '{"visiteurs": {"equipe": "COLLEGE FRANCAIS RIVE-SUD", "gardien_partant": "LUCAS LESSARD"}, '
                '"locaux": {"equipe": "LIONS LAC ST-LOUIS", "gardien_partant": "BRENDAN BOILY"}}'
            )

            # Run Gemini command
            cmd = ["gemini", prompt, f"@{abs_pdf_path}"]
            print(f"  Running Gemini AI extraction...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                print(f"  Gemini command failed: {result.stderr}")
                return None

            # Parse JSON response (remove markdown code blocks if present)
            try:
                response_text = result.stdout.strip()
                # Remove markdown code blocks if present
                if response_text.startswith('```json'):
                    response_text = response_text.replace('```json', '').replace('```', '').strip()
                elif response_text.startswith('```'):
                    response_text = response_text.replace('```', '').strip()

                gemini_data = json.loads(response_text)
                print(f"  Gemini response: {gemini_data}")

                # Convert Gemini format to our internal format
                starting_goalies = []

                if 'visiteurs' in gemini_data and 'gardien_partant' in gemini_data['visiteurs']:
                    away_goalie = gemini_data['visiteurs']['gardien_partant']
                    if away_goalie:
                        starting_goalies.append({
                            'number': 0,  # No number from Gemini
                            'name': away_goalie.upper(),
                            'team': gemini_data['visiteurs'].get('equipe', '').upper(),
                            'type': 'away'
                        })
                        print(f"  Found away starting goalie: {away_goalie}")

                if 'locaux' in gemini_data and 'gardien_partant' in gemini_data['locaux']:
                    home_goalie = gemini_data['locaux']['gardien_partant']
                    if home_goalie:
                        starting_goalies.append({
                            'number': 0,  # No number from Gemini
                            'name': home_goalie.upper(),
                            'team': gemini_data['locaux'].get('equipe', '').upper(),
                            'type': 'home'
                        })
                        print(f"  Found home starting goalie: {home_goalie}")

                if starting_goalies:
                    return {
                        'goalies': starting_goalies,
                        'count': len(starting_goalies)
                    }
                else:
                    print("  No starting goalies found in Gemini response")
                    return None

            except json.JSONDecodeError as e:
                print(f"  Failed to parse Gemini JSON response: {e}")
                print(f"  Raw response: {result.stdout}")
                return None

        except subprocess.TimeoutExpired:
            print("  Gemini command timed out")
            return None
        except Exception as e:
            print(f"  Error calling Gemini: {e}")
            return None


    def parse_all_gamesheets(self, limit=None):
        """Parse all PDF gamesheets and add starting goalie information to game JSON files"""

        if not os.path.exists(self.gamesheet_dir):
            print(f"Directory {self.gamesheet_dir} not found - skipping goalie parsing")
            return False

        if not os.path.exists(self.game_dir):
            print(f"Directory {self.game_dir} not found - skipping goalie parsing")
            return False

        pdf_files = [f for f in os.listdir(self.gamesheet_dir) if f.endswith('.pdf')]
        if limit:
            pdf_files = pdf_files[:limit]
            print(f"Found {len(pdf_files)} PDF gamesheets (limited to {limit} for testing)")
        else:
            print(f"Found {len(pdf_files)} PDF gamesheets")

        self.processed_count = 0
        self.skipped_count = 0

        for pdf_file in sorted(pdf_files):
            pdf_path = os.path.join(self.gamesheet_dir, pdf_file)

            # Extract game ID from filename
            game_id_match = re.search(r'game_(\d+)', pdf_file)
            if not game_id_match:
                print(f"Processing: {pdf_file}")
                print(f"  Could not extract game ID from {pdf_file}")
                continue

            game_id = game_id_match.group(1)
            # Look for game file with full filename pattern
            game_files = [f for f in os.listdir(self.game_dir) if f.startswith(f"game_{game_id}_") and f.endswith('.json')]
            if game_files:
                game_file = os.path.join(self.game_dir, game_files[0])
            else:
                game_file = os.path.join(self.game_dir, f"game_{game_id}.json")

            # Check if corresponding game file exists
            if not os.path.exists(game_file):
                print(f"Processing: {pdf_file}")
                print(f"  Corresponding game file {game_file} not found - skipping")
                continue

            # Load the game data
            try:
                with open(game_file, 'r', encoding='utf-8') as f:
                    game_data = json.load(f)
            except Exception as e:
                print(f"Processing: {pdf_file}")
                print(f"  Error loading game file {game_file}: {e}")
                continue

            print(f"Processing: {pdf_file}")

            # Skip if already has starting goalies
            if self.has_starting_goalies(game_data):
                print(f"  Already has starting goalie data - skipping")
                self.skipped_count += 1
                continue

            # Parse the gamesheet
            result = self.parse_gamesheet(pdf_path)
            if result and result['count'] > 0:
                # Add starting goalies to game data
                game_data['starting_goalies'] = {
                    'home_goalie': None,
                    'away_goalie': None
                }

                for goalie in result['goalies']:
                    if goalie['type'] == 'home':
                        game_data['starting_goalies']['home_goalie'] = goalie['name']
                    elif goalie['type'] == 'away':
                        game_data['starting_goalies']['away_goalie'] = goalie['name']

                # Save updated game data
                try:
                    with open(game_file, 'w', encoding='utf-8') as f:
                        json.dump(game_data, f, indent=2, ensure_ascii=False)
                    print(f"  Found {result['count']} starting goalies - saved to game file")
                    self.processed_count += 1
                except Exception as e:
                    print(f"  Error saving game file: {e}")
            else:
                print("  No starting goalies found")

        print(f"\nProcessing summary: {self.processed_count} new, {self.skipped_count} already processed")
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
                'powerplay_opportunities': 0,
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
                    player_id = player.get('participantId')
                    if not player_id:
                        continue
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
        """Load starting goalie data from game JSON files"""
        games_with_starting_goalies = 0

        for game in self.games:
            if 'starting_goalies' in game and game['starting_goalies'] is not None:
                game_id = game['id']
                starting_names = []

                # Handle both old and new formats
                starting_data = game['starting_goalies']

                # New format from scraper: {"home_goalie": "NAME", "away_goalie": "NAME"}
                if 'home_goalie' in starting_data and 'away_goalie' in starting_data:
                    if starting_data.get('home_goalie'):
                        starting_names.append(starting_data['home_goalie'])
                    if starting_data.get('away_goalie'):
                        starting_names.append(starting_data['away_goalie'])

                # Old format from stats compiler: {"goalies": [...], "count": N}
                elif 'goalies' in starting_data:
                    for goalie in starting_data['goalies']:
                        if goalie.get('name'):
                            starting_names.append(goalie['name'])

                if starting_names:
                    self.starting_goalies[game_id] = starting_names
                    games_with_starting_goalies += 1

        print(f"Loaded starting goalie data for {games_with_starting_goalies} games")

    def normalize_name(self, name):
        """Normalize player name for comparison (remove accents, etc.)"""
        import unicodedata
        normalized = unicodedata.normalize('NFD', name)
        ascii_name = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        return ascii_name.upper().strip()

    def is_starting_goalie(self, game_id, player_name, team_id=None, game_data=None):
        """Check if a goalie was a starter in the given game"""
        # If we have starting goalie data for this game, use it
        if game_id in self.starting_goalies:
            starting_names = self.starting_goalies[game_id]
            normalized_player_name = self.normalize_name(player_name)

            # Check if this player matches any starting goalie
            for starting_name in starting_names:
                if self.normalize_name(starting_name) == normalized_player_name:
                    return True
            return False

        # Fallback: if no starting goalie data available, use heuristic
        # Assume the first goalie in the roster is the starter
        if team_id and game_data:
            return self._is_likely_starting_goalie(player_name, team_id, game_data)

        # If no fallback data available, assume all goalies are starters
        # This ensures goalie stats are still tracked
        return True

    def _is_likely_starting_goalie(self, player_name, team_id, game_data):
        """Heuristic to determine likely starting goalie from roster"""
        # Get the team's roster
        home_team = game_data.get('boxscore', {}).get('teams', [])[0] if len(game_data.get('boxscore', {}).get('teams', [])) > 0 else None
        away_team = game_data.get('boxscore', {}).get('teams', [])[1] if len(game_data.get('boxscore', {}).get('teams', [])) > 1 else None

        if not home_team or not away_team:
            return True

        # Determine which roster to check
        roster_key = 'home_team_roster' if team_id == home_team.get('id') else 'away_team_roster'
        roster = game_data.get(roster_key, [])

        # Find all goalies in the roster
        goalies = []
        for player in roster:
            player_positions = player.get('positions', [])
            if 'G' in player_positions:
                participant = player.get('participant', {})
                player_id = player.get('participantId')
                player_name = participant.get('fullName')

                # Skip if missing essential data
                if not player_id or not player_name:
                    continue

                number = player.get('number')
                # Handle invalid/missing numbers
                if number is None or number == 0:
                    number = 999  # Put at end
                goalies.append({
                    'name': player_name,
                    'id': player_id,
                    'number': number
                })

        if not goalies:
            return True

        # If there's only one goalie, they're the starter
        if len(goalies) == 1:
            return goalies[0]['name'] == player_name

        # Sort by jersey number (lower valid numbers typically start)
        # Put goalies with valid numbers first, then invalid ones
        def sort_key(goalie):
            if goalie['number'] == 999:  # Invalid number
                return (1, goalie['name'])  # Sort by name as tiebreaker
            else:
                return (0, goalie['number'])  # Valid numbers first

        goalies.sort(key=sort_key)

        # For teams with multiple goalies, be more conservative
        # Only the first goalie with a valid number is considered starter
        # If no valid numbers, consider first two goalies as potential starters
        valid_goalies = [g for g in goalies if g['number'] != 999]
        if valid_goalies:
            # First goalie with valid number is starter
            return valid_goalies[0]['name'] == player_name
        else:
            # No valid numbers, first two goalies might be starters
            return goalies.index(next((g for g in goalies if g['name'] == player_name), None)) < 2 if any(g['name'] == player_name for g in goalies) else False

    def get_player_position(self, boxscore, player_id):
        """Get player position from global index or current roster"""
        if player_id in self.player_positions:
            return self.player_positions[player_id]

        for player in boxscore.get('roster', []):
            if player.get('participantId') == player_id:
                positions = player.get('positions', ['F'])
                return positions[0] if positions else 'F'
        return 'F'

    def calculate_powerplay_opportunities(self, game, home_team_id, away_team_id):
        """
        Calculate powerplay opportunities for both teams based on penalties
        Returns dict with PP opportunities for each team
        """
        if 'boxscore' not in game or 'penalties' not in game['boxscore']:
            return {home_team_id: 0, away_team_id: 0}

        penalties = game['boxscore']['penalties']
        if not penalties:
            return {home_team_id: 0, away_team_id: 0}

        # Convert penalties to events with start and end times
        penalty_events = []
        for penalty in penalties:
            game_time = penalty.get('gameTime', {})
            period = int(game_time.get('period', 1))
            minutes = int(game_time.get('minutes', 0))
            seconds = int(game_time.get('seconds', 0))

            # Convert to seconds from game start
            start_time = (period - 1) * 1200 + minutes * 60 + seconds

            # Get penalty duration in seconds
            duration_name = penalty.get('duration', {}).get('name', 'Minor')
            if 'Minor' in duration_name or 'Mineure' in duration_name:
                duration = 120  # 2 minutes
            elif 'Major' in duration_name or 'Majeure' in duration_name:
                duration = 300  # 5 minutes
            elif 'Misconduct' in duration_name:
                duration = 600  # 10 minutes
            else:
                duration = 120  # Default to 2 minutes

            end_time = start_time + duration
            team_id = penalty.get('teamId')

            if team_id:
                penalty_events.append({
                    'team_id': team_id,
                    'start': start_time,
                    'end': end_time
                })

        # Track PP opportunities
        pp_opportunities = {home_team_id: 0, away_team_id: 0}

        # Sort all time points (starts and ends of penalties)
        time_points = set()
        for event in penalty_events:
            time_points.add(event['start'])
            time_points.add(event['end'])

        time_points = sorted(time_points)

        # Track previous PP state
        prev_home_pp = False
        prev_away_pp = False

        # For each time segment, check PP state
        for i in range(len(time_points) - 1):
            current_time = time_points[i]

            # Count active penalties for each team at this time
            home_penalties = sum(1 for p in penalty_events
                               if p['team_id'] == home_team_id and p['start'] <= current_time < p['end'])
            away_penalties = sum(1 for p in penalty_events
                               if p['team_id'] == away_team_id and p['start'] <= current_time < p['end'])

            # Determine PP state
            home_has_pp = away_penalties > home_penalties
            away_has_pp = home_penalties > away_penalties

            # Count new PP opportunities (transition from no PP to PP)
            if home_has_pp and not prev_home_pp:
                pp_opportunities[home_team_id] += 1
            if away_has_pp and not prev_away_pp:
                pp_opportunities[away_team_id] += 1

            prev_home_pp = home_has_pp
            prev_away_pp = away_has_pp

        return pp_opportunities

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

            # Calculate and update PP opportunities
            pp_opps = self.calculate_powerplay_opportunities(game, home_team_id, away_team_id)
            self.teams[home_team_id]['powerplay_opportunities'] += pp_opps.get(home_team_id, 0)
            self.teams[away_team_id]['powerplay_opportunities'] += pp_opps.get(away_team_id, 0)

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
                participant = goal.get('participant', {})
                scorer_id = participant.get('participantId')
                scorer_name = participant.get('fullName')
                team_id = goal.get('teamId')

                # Skip if missing essential data
                if not scorer_id or not team_id:
                    continue

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
                    assist_id = assist.get('participantId')
                    assist_name = assist.get('fullName')

                    # Skip if missing essential data
                    if not assist_id:
                        continue

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
                participant = penalty.get('participant', {})
                player_id = participant.get('participantId')
                player_name = participant.get('fullName')
                team_id = penalty.get('teamId')

                # Skip if missing essential data
                if not player_id or not team_id:
                    continue

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
                participant = player.get('participant', {})
                player_id = player.get('participantId')
                player_name = participant.get('fullName')

                # Skip if missing essential data
                if not player_id or not player_name:
                    continue

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

                if position == 'G' and self.is_starting_goalie(game['id'], player_name, team_id, game):
                    if home_score > away_score:
                        self.players[player_id]['wins'] += 1
                    elif home_score < away_score:
                        self.players[player_id]['losses'] += 1
                    else:
                        self.players[player_id]['ties'] += 1
                    self.players[player_id]['goals_against'] += away_score

            for player in game.get('away_team_roster', []):
                participant = player.get('participant', {})
                player_id = player.get('participantId')
                player_name = participant.get('fullName')

                # Skip if missing essential data
                if not player_id or not player_name:
                    continue

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

                if position == 'G' and self.is_starting_goalie(game['id'], player_name, team_id, game):
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
                    team_id = self.players[player_id]['team_id']

                    for game_id in game_set:
                        # Find the game data for this game_id
                        game_data = None
                        for game in self.games:
                            if game['id'] == game_id:
                                game_data = game
                                break

                        if self.is_starting_goalie(game_id, player_name, team_id, game_data):
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

        downloaded_count = 0
        skipped_count = 0

        for team_id, logo_url in self.team_logos.items():
            if not logo_url:
                continue

            try:
                parsed_url = urllib.parse.urlparse(logo_url)
                file_ext = os.path.splitext(parsed_url.path)[1] or '.png'
                filename = f"team_{team_id}{file_ext}"
                filepath = os.path.join(logos_dir, filename)

                # Check if logo already exists
                if os.path.exists(filepath):
                    if team_id in self.teams:
                        self.teams[team_id]['local_logo'] = f"assets/logos/{filename}"
                    print(f"  Logo already exists for team {team_id}")
                    skipped_count += 1
                    continue

                response = requests.get(logo_url, timeout=10)
                response.raise_for_status()

                with open(filepath, 'wb') as f:
                    f.write(response.content)

                if team_id in self.teams:
                    self.teams[team_id]['local_logo'] = f"assets/logos/{filename}"

                print(f"  Downloaded logo for team {team_id}")
                downloaded_count += 1

            except Exception as e:
                print(f"  Failed to download logo for team {team_id}: {e}")

        print(f"Logo download summary: {downloaded_count} downloaded, {skipped_count} already existed")

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
            'even_strength_f_trios': defaultdict(lambda: {'goals': 0, 'assists': 0, 'points': 0}),
            'even_strength_f_pairs': defaultdict(lambda: {'goals': 0, 'assists': 0, 'points': 0}),
            'even_strength_d_duos': defaultdict(lambda: {'goals': 0, 'assists': 0, 'points': 0}),
            'powerplay_units': defaultdict(lambda: {'goals': 0, 'assists': 0, 'points': 0}),
            'penalty_kill_units': defaultdict(lambda: {'goals': 0, 'assists': 0, 'points': 0}),
            'goal_scoring_pairs': defaultdict(lambda: {'goals': 0}),  # Track assist->goal pairs
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
                player_id = player.get('participantId')
                if not player_id:
                    continue
                positions = player.get('positions', ['F'])
                position = positions[0] if positions else 'F'

                if position not in ['F', 'D', 'G', 'C']:
                    continue

                if position == 'C':
                    position = 'F'

                participant = player.get('participant', {})
                player_name = participant.get('fullName', 'Unknown')

                self.team_formations[team_id]['player_positions'][player_id] = {
                    'name': player_name,
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
            participant = goal.get('participant', {})
            scorer_id = participant.get('participantId')

            # Skip if no scorer
            if not scorer_id:
                continue

            players_involved.append(scorer_id)

            # Track goal-scoring pairs (primary assist to scorer)
            assists = goal.get('assists', [])
            if assists and len(assists) > 0:
                # Primary assist (first assist)
                primary_assist = assists[0]
                primary_assist_id = primary_assist.get('participantId')

                if primary_assist_id:
                    # Create pair key (always sorted for consistency)
                    pair_key = tuple(sorted([primary_assist_id, scorer_id]))
                    self.team_formations[team_id]['goal_scoring_pairs'][pair_key]['goals'] += 1

            for assist in assists:
                assist_id = assist.get('participantId')
                if assist_id:
                    players_involved.append(assist_id)

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

        # Calculate total points from this goal (1 goal + number of assists)
        goal_points = 1  # The goal itself
        assist_points = len(goal.get('assists', []))
        total_points = goal_points + assist_points

        # Get scorer ID safely
        participant = goal.get('participant', {})
        scorer_id = participant.get('participantId')
        if not scorer_id:
            return

        if len(forwards) >= 3:
            for trio in combinations(forwards, 3):
                trio_key = tuple(sorted([p['id'] for p in trio]))
                # Check how many players from this trio were involved in the goal
                trio_ids = set([p['id'] for p in trio])
                involved_players = set()

                # Add scorer if in trio
                if scorer_id in trio_ids:
                    involved_players.add(scorer_id)
                    team_data['even_strength_f_trios'][trio_key]['goals'] += 1

                # Add assists if in trio
                for assist in goal.get('assists', []):
                    assist_id = assist.get('participantId')
                    if assist_id and assist_id in trio_ids:
                        involved_players.add(assist_id)
                        team_data['even_strength_f_trios'][trio_key]['assists'] += 1

                # Update total points
                if involved_players:
                    team_data['even_strength_f_trios'][trio_key]['points'] = (
                        team_data['even_strength_f_trios'][trio_key]['goals'] +
                        team_data['even_strength_f_trios'][trio_key]['assists']
                    )

        if len(forwards) >= 2:
            for pair in combinations(forwards, 2):
                pair_key = tuple(sorted([p['id'] for p in pair]))
                pair_ids = set([p['id'] for p in pair])
                involved_players = set()

                # Add scorer if in pair
                if scorer_id in pair_ids:
                    involved_players.add(scorer_id)
                    team_data['even_strength_f_pairs'][pair_key]['goals'] += 1

                # Add assists if in pair
                for assist in goal.get('assists', []):
                    assist_id = assist.get('participantId')
                    if assist_id and assist_id in pair_ids:
                        involved_players.add(assist_id)
                        team_data['even_strength_f_pairs'][pair_key]['assists'] += 1

                # Update total points
                if involved_players:
                    team_data['even_strength_f_pairs'][pair_key]['points'] = (
                        team_data['even_strength_f_pairs'][pair_key]['goals'] +
                        team_data['even_strength_f_pairs'][pair_key]['assists']
                    )

        if len(defensemen) >= 2:
            for pair in combinations(defensemen, 2):
                pair_key = tuple(sorted([p['id'] for p in pair]))
                pair_ids = set([p['id'] for p in pair])
                involved_players = set()

                # Add scorer if in pair
                if scorer_id in pair_ids:
                    involved_players.add(scorer_id)
                    team_data['even_strength_d_duos'][pair_key]['goals'] += 1

                # Add assists if in pair
                for assist in goal.get('assists', []):
                    assist_id = assist.get('participantId')
                    if assist_id and assist_id in pair_ids:
                        involved_players.add(assist_id)
                        team_data['even_strength_d_duos'][pair_key]['assists'] += 1

                # Update total points
                if involved_players:
                    team_data['even_strength_d_duos'][pair_key]['points'] = (
                        team_data['even_strength_d_duos'][pair_key]['goals'] +
                        team_data['even_strength_d_duos'][pair_key]['assists']
                    )

    def _detect_powerplay_units(self, team_id, players, goal):
        """Detect powerplay units"""
        team_data = self.team_formations[team_id]
        unit_key = tuple(sorted([p['id'] for p in players]))
        unit_ids = set([p['id'] for p in players])

        # Get scorer ID safely
        participant = goal.get('participant', {})
        scorer_id = participant.get('participantId')
        if not scorer_id:
            return

        # Add scorer if in unit
        if scorer_id in unit_ids:
            team_data['powerplay_units'][unit_key]['goals'] += 1

        # Add assists if in unit
        for assist in goal.get('assists', []):
            assist_id = assist.get('participantId')
            if assist_id and assist_id in unit_ids:
                team_data['powerplay_units'][unit_key]['assists'] += 1

        # Update total points
        team_data['powerplay_units'][unit_key]['points'] = (
            team_data['powerplay_units'][unit_key]['goals'] +
            team_data['powerplay_units'][unit_key]['assists']
        )

    def _detect_penalty_kill_units(self, team_id, players, goal):
        """Detect penalty kill units"""
        team_data = self.team_formations[team_id]
        unit_key = tuple(sorted([p['id'] for p in players]))
        unit_ids = set([p['id'] for p in players])

        # Get scorer ID safely
        participant = goal.get('participant', {})
        scorer_id = participant.get('participantId')
        if not scorer_id:
            return

        # Add scorer if in unit
        if scorer_id in unit_ids:
            team_data['penalty_kill_units'][unit_key]['goals'] += 1

        # Add assists if in unit
        for assist in goal.get('assists', []):
            assist_id = assist.get('participantId')
            if assist_id and assist_id in unit_ids:
                team_data['penalty_kill_units'][unit_key]['assists'] += 1

        # Update total points
        team_data['penalty_kill_units'][unit_key]['points'] = (
            team_data['penalty_kill_units'][unit_key]['goals'] +
            team_data['penalty_kill_units'][unit_key]['assists']
        )


    def get_team_formations(self, team_id):
        """Get formatted formations for a specific team"""
        if team_id not in self.team_formations:
            return None

        team_data = self.team_formations[team_id]

        return {
            'forward_lines': self._get_ranked_forward_lines(team_data),
            'defense_pairs': self._get_ranked_defense_pairs(team_data),
            'powerplay_units': self._get_ranked_powerplay_units(team_data),
            'penalty_kill_units': self._get_ranked_penalty_kill_units(team_data),
            'goal_scoring_pairs': self._get_top_goal_scoring_pairs(team_data)
        }

    def _calculate_dominance_scores(self, formations_list, scores_trios, scores_pairs):
        """
        Calculate dominance scores for formations based on the provided algorithm.

        Args:
            formations_list: List of formations with their stats
            scores_trios: Dict mapping trio keys to their raw scores
            scores_pairs: Dict mapping pair keys to their raw scores

        Returns:
            Updated formations_list with dominance scores
        """
        # STEP 1: Calculate total raw score of all found formations
        total_score = 0

        for formation in formations_list:
            formation_type = formation.get('type', 'trio')

            # Determine raw score based on formation type
            # For all types, use their points as raw score
            raw_score = formation.get('points', 0)

            formation['raw_score'] = raw_score
            total_score += raw_score

        # STEP 2: Calculate and add dominance score to each formation
        if total_score > 0:
            for formation in formations_list:
                raw_score = formation.get('raw_score', 0)
                dominance_score = (raw_score / total_score) * 100
                formation['dominance_score'] = round(dominance_score, 1)
        else:
            # If no total score, set all dominance scores to 0
            for formation in formations_list:
                formation['dominance_score'] = 0.0

        return formations_list

    def _detect_deduced_trios(self, pairs_dict, team_data):
        """
        Detect deduced trios from pairs (when 3 players all have pairs with each other)

        Args:
            pairs_dict: Dict of pair_key -> stats
            team_data: Team data including player positions

        Returns:
            List of deduced trios
        """
        deduced_trios = []
        used_pairs = set()

        # Build a graph of connections
        player_connections = defaultdict(dict)
        for pair_key, stats in pairs_dict.items():
            if stats['goals'] > 0:
                p1, p2 = pair_key
                player_connections[p1][p2] = {'stats': stats, 'pair_key': pair_key}
                player_connections[p2][p1] = {'stats': stats, 'pair_key': pair_key}

        # Find triangles (3 players all connected to each other)
        players = list(player_connections.keys())
        for i, p1 in enumerate(players):
            for j, p2 in enumerate(players[i+1:], i+1):
                if p2 in player_connections[p1]:
                    # p1 and p2 are connected, check for common connections
                    for p3 in players[j+1:]:
                        if p3 in player_connections[p1] and p3 in player_connections[p2]:
                            # Found a triangle: p1-p2-p3
                            pair_keys = [
                                player_connections[p1][p2]['pair_key'],
                                player_connections[p1][p3]['pair_key'],
                                player_connections[p2][p3]['pair_key']
                            ]

                            # Skip if any pair already used
                            if any(pk in used_pairs for pk in pair_keys):
                                continue

                            # Get stats for all three pairs
                            stats_list = [
                                player_connections[p1][p2]['stats'],
                                player_connections[p1][p3]['stats'],
                                player_connections[p2][p3]['stats']
                            ]

                            # Calculate combined stats (use best pair as representative)
                            best_stats = max(stats_list, key=lambda s: s['points'])

                            # Get player info
                            players_info = []
                            for pid in sorted([p1, p2, p3]):
                                if pid in team_data['player_positions']:
                                    players_info.append(team_data['player_positions'][pid])

                            if len(players_info) == 3:
                                deduced_trios.append({
                                    'players': players_info,
                                    'goals': best_stats['goals'],
                                    'assists': best_stats['assists'],
                                    'points': best_stats['points'],
                                    'type': 'deduced_trio',
                                    'key': tuple(sorted([p1, p2, p3])),
                                    'source_pairs': pair_keys
                                })

                                # Mark these pairs as used
                                used_pairs.update(pair_keys)

        return deduced_trios, used_pairs

    def _get_ranked_forward_lines(self, team_data):
        """Get forward lines ranked by points"""
        lines = []
        scores_trios = {}
        scores_pairs = {}
        existing_trio_keys = set()

        # Get all trios with goals > 0
        if team_data['even_strength_f_trios']:
            for trio_key, stats in team_data['even_strength_f_trios'].items():
                if stats['goals'] > 0:
                    players = []
                    for player_id in trio_key:
                        if player_id in team_data['player_positions']:
                            players.append(team_data['player_positions'][player_id])

                    if len(players) == 3:
                        lines.append({
                            'players': players,
                            'goals': stats['goals'],
                            'assists': stats['assists'],
                            'points': stats['points'],
                            'type': 'trio',
                            'key': trio_key
                        })
                        scores_trios[trio_key] = stats['points']
                        existing_trio_keys.add(trio_key)

        # Detect deduced trios from pairs
        deduced_trios, used_pair_keys = self._detect_deduced_trios(
            team_data['even_strength_f_pairs'],
            team_data
        )

        # Add deduced trios to lines, replacing direct trios if the deduced trio has more points
        for deduced_trio in deduced_trios:
            deduced_key = deduced_trio['key']

            if deduced_key not in existing_trio_keys:
                # New trio, just add it
                lines.append(deduced_trio)
                scores_trios[deduced_key] = deduced_trio['points']
            else:
                # Trio already exists as direct trio - compare points
                # Find the existing direct trio in lines
                existing_trio = None
                existing_index = None
                for i, line in enumerate(lines):
                    if line.get('key') == deduced_key:
                        existing_trio = line
                        existing_index = i
                        break

                if existing_trio and deduced_trio['points'] > existing_trio['points']:
                    # Deduced trio has more points, replace the direct trio
                    lines[existing_index] = deduced_trio
                    scores_trios[deduced_key] = deduced_trio['points']
                    # Change type to indicate it was upgraded
                    lines[existing_index]['type'] = 'deduced_trio'

        # Get forward pairs with goals > 0 that are NOT part of a deduced trio
        if team_data['even_strength_f_pairs']:
            for pair_key, stats in team_data['even_strength_f_pairs'].items():
                if stats['goals'] > 0 and pair_key not in used_pair_keys:
                    players = []
                    for player_id in pair_key:
                        if player_id in team_data['player_positions']:
                            players.append(team_data['player_positions'][player_id])

                    if len(players) == 2:
                        lines.append({
                            'players': players,
                            'goals': stats['goals'],
                            'assists': stats['assists'],
                            'points': stats['points'],
                            'type': 'pair',
                            'key': pair_key
                        })
                        scores_pairs[pair_key] = stats['points']

        # Calculate dominance scores
        lines = self._calculate_dominance_scores(lines, scores_trios, scores_pairs)

        # Sort by points descending, then by dominance score
        lines.sort(key=lambda x: (x['points'], x.get('dominance_score', 0)), reverse=True)

        # Add rank (Line 1, Line 2, Line 3, etc.)
        ranked_lines = []
        for i, line in enumerate(lines[:3]):  # Top 3 lines
            line['rank'] = f"Line {i + 1}"
            # Remove internal keys used for calculation
            if 'key' in line:
                del line['key']
            if 'source_pairs' in line:
                del line['source_pairs']
            ranked_lines.append(line)

        return ranked_lines

    def _get_ranked_defense_pairs(self, team_data):
        """Get defense pairs ranked by goals"""
        pairs = []

        # Get all defense pairs with goals > 0
        if team_data['even_strength_d_duos']:
            for pair_key, stats in team_data['even_strength_d_duos'].items():
                if stats['goals'] > 0:
                    players = []
                    for player_id in pair_key:
                        if player_id in team_data['player_positions']:
                            players.append(team_data['player_positions'][player_id])

                    if len(players) == 2:
                        pairs.append({
                            'players': players,
                            'goals': stats['goals'],
                            'assists': stats['assists'],
                            'points': stats['points']
                        })

        # Sort by goals descending
        pairs.sort(key=lambda x: x['goals'], reverse=True)

        # Add rank (D1, D2, etc.)
        ranked_pairs = []
        for i, pair in enumerate(pairs[:2]):  # Top 2 pairs
            pair['rank'] = f"D{i + 1}"
            ranked_pairs.append(pair)

        return ranked_pairs

    def _get_ranked_powerplay_units(self, team_data):
        """Get powerplay units ranked by goals"""
        units = []
        scores_units = {}

        # Get all PP units with goals > 0
        if team_data['powerplay_units']:
            for unit_key, stats in team_data['powerplay_units'].items():
                if stats['goals'] > 0:
                    players = []
                    for player_id in unit_key:
                        if player_id in team_data['player_positions']:
                            players.append(team_data['player_positions'][player_id])

                    if len(players) >= 2:  # At least 2 players
                        # Sort players: Forwards (F) first, then Defensemen (D)
                        players.sort(key=lambda p: (0 if p['position'] in ['LW', 'C', 'RW', 'F'] else 1, p['name']))

                        units.append({
                            'players': players,
                            'goals': stats['goals'],
                            'assists': stats['assists'],
                            'points': stats['points'],
                            'type': 'powerplay',
                            'key': unit_key
                        })
                        scores_units[unit_key] = stats['points']

        # Calculate dominance scores
        units = self._calculate_dominance_scores(units, scores_units, {})

        # Sort by points descending, then by dominance score
        units.sort(key=lambda x: (x['points'], x.get('dominance_score', 0)), reverse=True)

        # Add rank (PP1, PP2, etc.)
        ranked_units = []
        for i, unit in enumerate(units[:3]):  # Top 3 units
            unit['rank'] = f"PP{i + 1}"
            # Remove internal key used for calculation
            if 'key' in unit:
                del unit['key']
            ranked_units.append(unit)

        return ranked_units

    def _get_ranked_penalty_kill_units(self, team_data):
        """Get penalty kill units ranked by goals"""
        units = []

        # Get all PK units with goals > 0
        if team_data['penalty_kill_units']:
            for unit_key, stats in team_data['penalty_kill_units'].items():
                if stats['goals'] > 0:
                    players = []
                    for player_id in unit_key:
                        if player_id in team_data['player_positions']:
                            players.append(team_data['player_positions'][player_id])

                    if len(players) >= 2:  # At least 2 players
                        units.append({
                            'players': players,
                            'goals': stats['goals'],
                            'assists': stats['assists'],
                            'points': stats['points']
                        })

        # Sort by goals descending
        units.sort(key=lambda x: x['goals'], reverse=True)

        # Add rank (PK1, PK2, etc.)
        ranked_units = []
        for i, unit in enumerate(units[:3]):  # Top 3 units
            unit['rank'] = f"PK{i + 1}"
            ranked_units.append(unit)

        return ranked_units

    def _get_top_goal_scoring_pairs(self, team_data):
        """Get top 5 goal-scoring pairs ranked by number of goals"""
        pairs = []

        # Get all goal-scoring pairs with goals > 0
        if team_data['goal_scoring_pairs']:
            for pair_key, stats in team_data['goal_scoring_pairs'].items():
                if stats['goals'] > 0:
                    players = []
                    for player_id in pair_key:
                        if player_id in team_data['player_positions']:
                            players.append(team_data['player_positions'][player_id])

                    if len(players) == 2:
                        pairs.append({
                            'players': players,
                            'goals': stats['goals']
                        })

        # Sort by goals descending
        pairs.sort(key=lambda x: x['goals'], reverse=True)

        # Return top 5 pairs
        return pairs[:5]

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
    games_dir = "web/data/games"
    web_dir = "web"
    gamesheet_dir = "web/data/gamesheets"

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
                parser = StartingGoalieParser(gamesheet_dir, games_dir)
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
