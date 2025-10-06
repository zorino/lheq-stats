// Main JavaScript file for LHEQ Statistics
class DataManager {
    constructor() {
        this.teams = [];
        this.players = [];
        this.games = [];
        this.loaded = false;
    }

    async loadData() {
        if (this.loaded) return;

        try {
            // Load all data files
            const [teamsResponse, playersResponse, gamesResponse] = await Promise.all([
                fetch('data/teams.json'),
                fetch('data/players.json'),
                fetch('data/games.json')
            ]);

            this.teams = await teamsResponse.json();
            this.players = await playersResponse.json();
            this.games = await gamesResponse.json();

            // Create team lookup for easy access
            this.teamLookup = {};
            this.teams.forEach(team => {
                this.teamLookup[team.id] = team;
            });

            this.loaded = true;
            console.log('Data loaded successfully');
        } catch (error) {
            console.error('Error loading data:', error);
            throw error;
        }
    }

    getTeam(teamId) {
        return this.teamLookup[teamId];
    }

    getTeamById(teamId) {
        return this.teamLookup[teamId];
    }

    getAllPlayers() {
        return this.players;
    }

    getTeamName(teamId) {
        const team = this.getTeam(teamId);
        return team ? team.name : 'Unknown Team';
    }

    getTeamLogo(teamId) {
        const team = this.getTeam(teamId);
        return team && team.local_logo ? team.local_logo : 'assets/logos/default.png';
    }

    getPlayersByTeam(teamId) {
        return this.players.filter(player => player.team_id === teamId);
    }

    getSkaters() {
        return this.players.filter(player => player.position !== 'G');
    }

    getGoalies() {
        return this.players.filter(player => player.position === 'G' && player.games_played > 0);
    }

    getTotalGoals() {
        return this.players.reduce((total, player) => total + player.goals, 0);
    }

    getRecentGames(limit = 10) {
        return this.games
            .sort((a, b) => new Date(b.date) - new Date(a.date))
            .slice(0, limit);
    }
}

// Utility functions
const utils = {
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-CA', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },

    formatNumber(num) {
        return num.toLocaleString('fr-CA');
    },

    formatPercentage(numerator, denominator) {
        if (denominator === 0) return '0.0%';
        return ((numerator / denominator) * 100).toFixed(1) + '%';
    },

    formatGoalsAgainstAverage(goalsAgainst, gamesPlayed) {
        if (gamesPlayed === 0) return '0.00';
        return (goalsAgainst / gamesPlayed).toFixed(2);
    },

    createElement(tag, className = '', textContent = '') {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (textContent) element.textContent = textContent;
        return element;
    },

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// DataTables integration - no custom sorting needed

// Table utilities
const tableUtils = {
    createTeamRow(team, position) {
        const row = document.createElement('tr');

        // Calculate percentages
        const ppPercent = utils.formatPercentage(
            team.powerplay_goals_for,
            team.powerplay_goals_for + team.powerplay_goals_against
        );
        const pkPercent = utils.formatPercentage(
            team.powerplay_goals_against,
            team.powerplay_goals_for + team.powerplay_goals_against
        );

        row.innerHTML = `
            <td>${position}</td>
            <td><img src="${team.local_logo || 'assets/logos/default.png'}" alt="${team.name}" class="team-logo" onerror="this.style.display='none'"></td>
            <td><strong>${team.name}</strong></td>
            <td>${team.games_played}</td>
            <td>${team.wins}</td>
            <td>${team.losses}</td>
            <td>${team.ties}</td>
            <td><strong>${team.points}</strong></td>
            <td>${team.goals_for}</td>
            <td>${team.goals_against}</td>
            <td class="${team.goal_differential >= 0 ? 'positive' : 'negative'}">${team.goal_differential > 0 ? '+' : ''}${team.goal_differential}</td>
            <td>${team.penalty_minutes}</td>
            <td>${ppPercent}</td>
            <td>${pkPercent}</td>
            <td>${team.home_wins}-${team.home_losses}-${team.home_ties} / ${team.away_wins}-${team.away_losses}-${team.away_ties}</td>
        `;

        return row;
    },

    createPlayerRow(player, position, dataManager) {
        const row = document.createElement('tr');
        const teamName = dataManager.getTeamName(player.team_id);

        if (player.position === 'G') {
            // Goalie row
            const gaa = utils.formatGoalsAgainstAverage(player.goals_against, player.games_played);
            row.innerHTML = `
                <td>${position}</td>
                <td><strong>${player.name}</strong></td>
                <td>${teamName}</td>
                <td>${player.games_played}</td>
                <td>${player.wins}</td>
                <td>${player.losses}</td>
                <td>${player.ties}</td>
                <td>${player.goals_against}</td>
                <td>${gaa}</td>
            `;
        } else {
            // Skater row
            row.innerHTML = `
                <td>${position}</td>
                <td><strong>${player.name}</strong></td>
                <td>${teamName}</td>
                <td>${player.position}</td>
                <td>${player.games_played}</td>
                <td>${player.goals}</td>
                <td>${player.assists}</td>
                <td><strong>${player.points}</strong></td>
                <td>${player.penalty_minutes}</td>
                <td>${player.powerplay_goals}</td>
                <td>${player.powerplay_assists}</td>
                <td>${player.shorthanded_goals}</td>
                <td>${player.shorthanded_assists}</td>
            `;
        }

        return row;
    },

    createGameCard(game, dataManager) {
        const card = document.createElement('div');
        card.className = 'game-card';

        const homeTeam = dataManager.getTeam(game.home_team_id) || { name: game.home_team };
        const awayTeam = dataManager.getTeam(game.away_team_id) || { name: game.away_team };

        card.innerHTML = `
            <div class="game-teams">
                <div class="game-team">
                    <img src="${dataManager.getTeamLogo(homeTeam.id)}" alt="${homeTeam.name}" onerror="this.style.display='none'">
                    <div>${homeTeam.name}</div>
                </div>
                <div class="game-score">
                    ${game.home_score} - ${game.away_score}
                </div>
                <div class="game-team">
                    <img src="${dataManager.getTeamLogo(awayTeam.id)}" alt="${awayTeam.name}" onerror="this.style.display='none'">
                    <div>${awayTeam.name}</div>
                </div>
            </div>
            <div class="game-date">
                ${utils.formatDate(game.date)}
            </div>
        `;

        return card;
    }
};

// Search and filter utilities
const filterUtils = {
    searchTeams(teams, searchTerm) {
        if (!searchTerm) return teams;
        return teams.filter(team =>
            team.name.toLowerCase().includes(searchTerm.toLowerCase())
        );
    },

    searchPlayers(players, searchTerm) {
        if (!searchTerm) return players;
        return players.filter(player =>
            player.name.toLowerCase().includes(searchTerm.toLowerCase())
        );
    },

    filterPlayersByPosition(players, position) {
        if (!position) return players;
        return players.filter(player => player.position === position);
    },

    filterPlayersByTeam(players, teamId) {
        if (!teamId) return players;
        return players.filter(player => player.team_id == teamId);
    },

    filterPlayersByDivision(players, division) {
        if (!division) return players;
        return players.filter(player => {
            const team = dataManager.getTeam(player.team_id);
            return team && team.division === division;
        });
    },

    sortData(data, sortBy, ascending = false) {
        return [...data].sort((a, b) => {
            let aVal = a[sortBy];
            let bVal = b[sortBy];

            // Handle string sorting
            if (typeof aVal === 'string') {
                return ascending ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }

            // Handle number sorting
            return ascending ? aVal - bVal : bVal - aVal;
        });
    }
};

// Loading utilities
const loadingUtils = {
    showLoading(element) {
        element.innerHTML = '<div class="loading">Chargement des données...</div>';
    },

    hideLoading(element) {
        const loading = element.querySelector('.loading');
        if (loading) loading.remove();
    }
};

// Initialize global data manager
const dataManager = new DataManager();

// Export for other modules
window.dataManager = dataManager;
window.utils = utils;
window.tableUtils = tableUtils;
window.filterUtils = filterUtils;
window.loadingUtils = loadingUtils;