#!/usr/bin/env python3

import json
import requests
import urllib.parse
from datetime import datetime

class FinalWorkingLHEQScraper:
    def __init__(self):
        self.api_base_url = "https://pub-api.play.spordle.com/api/sp/games"
        self.api_key = "f08ed9064e3cdc382e6abb305ff543d0150fb52f"
        self.headers = {
            "Authorization": f"API-Key {self.api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json"
        }

        # Create directories for outputs
        import os
        os.makedirs("gamesheets", exist_ok=True)
        os.makedirs("games", exist_ok=True)
        os.makedirs("logs", exist_ok=True)

    def build_api_url(self, start_date, end_date, skip=0):
        """Build the API URL with proper filters"""
        filter_obj = {
            "order": "startTime ASC",
            "skip": skip,
            "where": {
                "and": [
                    {
                        "date": {
                            "between": [start_date, end_date]
                        }
                    },
                    {
                        "categoryId": "ba267b3e-9734-478c-a9e2-4890895cfc47"
                    },
                    {
                        "scheduleId": {
                            "inq": [182366]
                        }
                    },
                    {
                        "officeId": 9175
                    }
                ]
            },
            "include": [
                "teamStats",
                "surface",
                "office",
                "awayTeam",
                "homeTeam",
                "externalProviders"
            ]
        }

        # Convert to JSON and URL encode
        filter_json = json.dumps(filter_obj, separators=(',', ':'))
        filter_encoded = urllib.parse.quote(filter_json)

        return f"{self.api_base_url}?filter={filter_encoded}"

    def fetch_games_for_month(self, start_date, end_date):
        """Fetch all games for a specific date range"""
        print(f"📅 Fetching games from {start_date} to {end_date}...")

        all_games = []
        skip = 0
        batch_size = 100

        while True:
            api_url = self.build_api_url(start_date, end_date, skip)

            try:
                response = requests.get(api_url, headers=self.headers, timeout=30)
                response.raise_for_status()

                data = response.json()
                games_batch = data if isinstance(data, list) else data.get('data', [])

                if not games_batch:
                    break

                all_games.extend(games_batch)
                print(f"📋 Found {len(games_batch)} games in this batch (total: {len(all_games)})")

                if len(games_batch) < batch_size:
                    break

                skip += len(games_batch)

            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching games: {e}")
                break

        return all_games

    def is_game_completed(self, game):
        """Check if a game is completed by looking at teamStats"""
        team_stats = game.get('teamStats', [])

        if not team_stats:
            return False

        # If we have team stats with goals scored, the game is completed
        for stat in team_stats:
            if stat.get('goalFor') is not None:
                return True

        return False

    def extract_scores(self, game):
        """Extract home and away scores from teamStats"""
        team_stats = game.get('teamStats', [])
        home_team_id = game.get('homeTeamId')
        away_team_id = game.get('awayTeamId')

        home_score = None
        away_score = None

        for stat in team_stats:
            team_id = stat.get('teamId')
            goals = stat.get('goalFor')

            if team_id == home_team_id:
                home_score = goals
            elif team_id == away_team_id:
                away_score = goals

        return home_score, away_score

    def fetch_team_members(self, team_id):
        """Fetch complete team roster using members endpoint"""
        # Build filter for all team positions
        team_filter = {
            "where": {
                "positions": {
                    "inq": ["F", "C", "D", "G", "Head Coach", "Assistant Coach", "Goaltending Coach", "Manager", "Trainer", "Safety Person"]
                },
                "teamId": int(team_id)
            }
        }

        # URL encode the filter
        filter_json = json.dumps(team_filter, separators=(',', ':'))
        filter_encoded = urllib.parse.quote(filter_json)
        members_url = f"https://pub-api.play.spordle.com/api/sp/members?filter={filter_encoded}"

        try:
            response = requests.get(members_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching team members for team {team_id}: {e}")
            return None

    def fetch_boxscore(self, game_id):
        """Fetch detailed boxscore data for a game"""
        boxscore_url = f"{self.api_base_url}/{game_id}/boxScore"

        try:
            response = requests.get(boxscore_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching boxscore for game {game_id}: {e}")
            return None

    def fetch_game_details_with_players(self, game_id):
        """Fetch detailed game information including player lists"""
        # URL-encoded filter for including team details and players
        filter_str = '{"include":["teamStats","surface","schedule",{"awayTeam":["category"]},{"homeTeam":["category"]},"category","externalProviders"]}'
        filter_encoded = urllib.parse.quote(filter_str)
        details_url = f"{self.api_base_url}/{game_id}?filter={filter_encoded}"

        try:
            response = requests.get(details_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching game details for game {game_id}: {e}")
            return None

    def download_gamesheet_pdf(self, game_id, away_team, home_team):
        """Download the PDF gamesheet for a completed game"""
        pdf_url = f"https://pdf.play.spordle.com/game/{game_id}?locale=fr"

        try:
            response = requests.get(pdf_url, headers=self.headers, timeout=30)
            response.raise_for_status()

            # Create safe filename
            safe_away = away_team.replace(' ', '_').replace('/', '_').replace('\\', '_')
            safe_home = home_team.replace(' ', '_').replace('/', '_').replace('\\', '_')
            filename = f"gamesheets/game_{game_id}_{safe_away}_vs_{safe_home}.pdf"

            with open(filename, 'wb') as f:
                f.write(response.content)

            print(f"📄 Downloaded PDF: {filename}")
            return filename

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error downloading PDF for game {game_id}: {e}")
            return None

    def save_individual_game_file(self, game_data):
        """Save individual game data to a JSON file"""
        game_id = game_data.get('id')
        away_team = game_data.get('away_team', 'Unknown').replace(' ', '_').replace('/', '_').replace('\\', '_')
        home_team = game_data.get('home_team', 'Unknown').replace(' ', '_').replace('/', '_').replace('\\', '_')
        date = game_data.get('date', 'unknown')

        filename = f"games/game_{game_id}_{date}_{away_team}_vs_{home_team}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(game_data, f, indent=2, ensure_ascii=False)
            print(f"   💾 Game data saved: {filename}")
            return filename
        except Exception as e:
            print(f"   ⚠️ Error saving game file: {e}")
            return None

    def process_games(self, api_games, fetch_detailed_stats=True):
        """Process games from API data with optional detailed stats fetching"""
        print(f"🔄 Processing {len(api_games)} games from API...")

        final_games = []
        scheduled_games = []

        for i, game in enumerate(api_games, 1):
            try:
                game_id = game.get('id')
                status = game.get('status', '').upper()

                # Extract team information
                home_team = game.get('homeTeam', {})
                away_team = game.get('awayTeam', {})

                home_team_name = home_team.get('name', 'Unknown') if home_team else 'Unknown'
                away_team_name = away_team.get('name', 'Unknown') if away_team else 'Unknown'

                # Extract date/time
                start_time = game.get('startTime', '')
                date_str = game.get('date', '')

                # Check if game is completed and extract scores
                is_completed = self.is_game_completed(game)
                home_score, away_score = self.extract_scores(game)

                processed_game = {
                    'id': game_id,
                    'status': 'FINAL' if is_completed else 'SCHEDULED',
                    'original_status': status,
                    'home_team': home_team_name,
                    'away_team': away_team_name,
                    'date': date_str,
                    'start_time': start_time,
                    'home_score': home_score,
                    'away_score': away_score,
                    'detail_url': f"https://lheq.qc.ca/calendrier/{game_id}",
                    'gamesheet_pdf_url': f"https://pdf.play.spordle.com/game/{game_id}?locale=fr" if is_completed else None
                }

                # Fetch detailed stats for completed games
                if is_completed and fetch_detailed_stats:
                    print(f"📊 [{i}/{len(api_games)}] Fetching detailed stats for game {game_id}...")

                    # Fetch boxscore (goals, assists, penalties)
                    boxscore = self.fetch_boxscore(game_id)
                    if boxscore:
                        processed_game['boxscore'] = boxscore
                        print(f"   ✅ Boxscore data fetched")

                    # Fetch detailed game info with players
                    game_details = self.fetch_game_details_with_players(game_id)
                    if game_details:
                        processed_game['detailed_game_info'] = game_details
                        print(f"   ✅ Player details fetched")

                    # Fetch complete team rosters
                    home_team_id = game.get('homeTeamId')
                    away_team_id = game.get('awayTeamId')

                    if home_team_id:
                        home_members = self.fetch_team_members(home_team_id)
                        if home_members:
                            processed_game['home_team_roster'] = home_members
                            print(f"   ✅ Home team roster fetched ({len(home_members)} members)")

                    if away_team_id:
                        away_members = self.fetch_team_members(away_team_id)
                        if away_members:
                            processed_game['away_team_roster'] = away_members
                            print(f"   ✅ Away team roster fetched ({len(away_members)} members)")

                    # Download PDF gamesheet
                    pdf_filename = self.download_gamesheet_pdf(game_id, away_team_name, home_team_name)
                    if pdf_filename:
                        processed_game['gamesheet_pdf_file'] = pdf_filename

                # Save individual game file
                individual_file = self.save_individual_game_file(processed_game)
                if individual_file:
                    processed_game['individual_file'] = individual_file

                if is_completed:
                    final_games.append(processed_game)
                    print(f"✅ FINAL: {away_team_name} vs {home_team_name} - {away_score}-{home_score} (ID: {game_id})")
                else:
                    scheduled_games.append(processed_game)
                    print(f"📅 SCHEDULED: {away_team_name} vs {home_team_name} on {date_str} (ID: {game_id})")

            except Exception as e:
                print(f"⚠️ Error processing game: {e}")
                continue

        print(f"\n📊 SUMMARY:")
        print(f"   ✅ FINAL games: {len(final_games)}")
        print(f"   📅 SCHEDULED games: {len(scheduled_games)}")

        return final_games, scheduled_games

    def run(self, start_date=None, end_date=None, fetch_detailed_stats=True):
        """Fetch games for a specified date range"""
        # Set defaults to current month if not provided
        if start_date is None or end_date is None:
            import calendar
            from datetime import date
            today = date.today()
            start_date = f"{today.year}-{today.month:02d}-01"

            # Calculate last day of current month
            last_day = calendar.monthrange(today.year, today.month)[1]
            end_date = f"{today.year}-{today.month:02d}-{last_day:02d}"

        print(f"🏒 LHEQ SCRAPER - {start_date} to {end_date}")
        print("=" * 70)

        try:
            # Fetch games from API
            api_games = self.fetch_games_for_month(start_date, end_date)

            if not api_games:
                print("❌ No games found from API")
                return

            # Process games
            final_games, scheduled_games = self.process_games(api_games, fetch_detailed_stats)

            # Combine all games
            all_games = final_games + scheduled_games

            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/lheq_final_september_2025_{timestamp}.json"

            result_data = {
                'timestamp': timestamp,
                'date_range': f"{start_date} to {end_date}",
                'total_games': len(all_games),
                'final_games_count': len(final_games),
                'scheduled_games_count': len(scheduled_games),
                'final_games': final_games,
                'scheduled_games': scheduled_games,
                'all_games': all_games
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)

            print(f"\n🏆 API SCRAPING COMPLETE!")
            print(f"📊 Total games found: {len(all_games)}")
            print(f"✅ Final games: {len(final_games)}")
            print(f"📅 Scheduled games: {len(scheduled_games)}")
            print(f"💾 Results saved to: {filename}")

            # Show final games with enhanced data
            if final_games:
                print(f"\n🎯 FINAL GAMES WITH ENHANCED DATA:")
                games_with_boxscore = sum(1 for g in final_games if g.get('boxscore'))
                games_with_players = sum(1 for g in final_games if g.get('detailed_game_info'))
                games_with_home_roster = sum(1 for g in final_games if g.get('home_team_roster'))
                games_with_away_roster = sum(1 for g in final_games if g.get('away_team_roster'))
                games_with_pdfs = sum(1 for g in final_games if g.get('gamesheet_pdf_file'))

                print(f"   📊 Games with boxscore data: {games_with_boxscore}/{len(final_games)}")
                print(f"   👥 Games with player data: {games_with_players}/{len(final_games)}")
                print(f"   🏠 Games with home team rosters: {games_with_home_roster}/{len(final_games)}")
                print(f"   🚌 Games with away team rosters: {games_with_away_roster}/{len(final_games)}")
                print(f"   📄 Games with downloaded PDFs: {games_with_pdfs}/{len(final_games)}")

                print(f"\n🏒 SAMPLE GAMES:")
                for game in final_games[:3]:  # Show first 3 as example
                    print(f"   • {game['away_team']} vs {game['home_team']} ({game['away_score']}-{game['home_score']})")
                    print(f"     📊 Boxscore: {'✅' if game.get('boxscore') else '❌'}")
                    print(f"     👥 Players: {'✅' if game.get('detailed_game_info') else '❌'}")

                    home_roster_count = len(game.get('home_team_roster', []))
                    away_roster_count = len(game.get('away_team_roster', []))
                    print(f"     🏠 Home roster: {'✅' if home_roster_count > 0 else '❌'} ({home_roster_count} members)")
                    print(f"     🚌 Away roster: {'✅' if away_roster_count > 0 else '❌'} ({away_roster_count} members)")

                    print(f"     📄 PDF: {'✅' if game.get('gamesheet_pdf_file') else '❌'}")
                    print(f"     🔗 Detail: {game['detail_url']}")
                    print()

                if len(final_games) > 3:
                    print(f"   ... and {len(final_games) - 3} more games")

            return final_games, scheduled_games

        except Exception as e:
            print(f"❌ Scraper error: {e}")
            return [], []

if __name__ == "__main__":
    import sys

    scraper = FinalWorkingLHEQScraper()

    # Parse command line arguments
    if len(sys.argv) >= 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
        print(f"🗓️ Using custom date range: {start_date} to {end_date}")
        scraper.run(start_date, end_date)
    elif len(sys.argv) == 2:
        print("❌ Error: Please provide both start_date and end_date")
        print("Usage: python lheq_scraper.py <start_date> <end_date>")
        print("Example: python lheq_scraper.py 2025-10-01 2025-10-31")
    else:
        print("🗓️ Using default date range (current month)")
        scraper.run()