class SimpleGamesManager {
    constructor() {
        this.games = [];
        this.teams = [];
        this.filteredGames = [];
        this.init();
    }

    async init() {
        console.log('Starting simple games manager...');
        try {
            await this.loadData();
            this.populateFilters();
            this.renderGames();
            this.setupEventListeners();
            document.getElementById('loading').style.display = 'none';
            console.log('Simple games manager initialized successfully');
        } catch (error) {
            console.error('Error initializing simple games manager:', error);
            document.getElementById('loading').innerHTML = 'Erreur lors du chargement des données: ' + error.message;
        }
    }

    async loadData() {
        try {
            console.log('Loading games and teams data...');
            const [gamesResponse, teamsResponse] = await Promise.all([
                fetch('data/games.json'),
                fetch('data/teams.json')
            ]);

            if (!gamesResponse.ok) {
                throw new Error(`Failed to load games: ${gamesResponse.status}`);
            }
            if (!teamsResponse.ok) {
                throw new Error(`Failed to load teams: ${teamsResponse.status}`);
            }

            this.games = await gamesResponse.json();
            this.teams = await teamsResponse.json();
            this.filteredGames = [...this.games];

            console.log('Loaded', this.games.length, 'games and', this.teams.length, 'teams');
        } catch (error) {
            console.error('Error loading data:', error);
            throw error;
        }
    }

    populateFilters() {
        const teamFilter = document.getElementById('team-filter');
        const divisionFilter = document.getElementById('division-filter');

        // Populate team filter
        const uniqueTeams = new Set();
        this.games.forEach(game => {
            uniqueTeams.add(game.home_team);
            uniqueTeams.add(game.away_team);
        });

        Array.from(uniqueTeams).sort().forEach(team => {
            const option = document.createElement('option');
            option.value = team;
            option.textContent = team;
            teamFilter.appendChild(option);
        });

        // Populate division filter from teams data
        const uniqueDivisions = [...new Set(this.teams.map(team => team.division).filter(Boolean))].sort();
        uniqueDivisions.forEach(division => {
            const option = document.createElement('option');
            option.value = division;
            option.textContent = division;
            divisionFilter.appendChild(option);
        });
    }

    getTeamDivision(teamName) {
        const team = this.teams.find(t => t.name === teamName);
        return team ? team.division : 'N/A';
    }

    renderGames() {
        const tbody = document.getElementById('games-table-body');
        tbody.innerHTML = '';

        if (this.filteredGames.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="no-results">Aucun match trouvé avec les filtres sélectionnés.</td></tr>';
            return;
        }

        // Sort games by date (newest first)
        const sortedGames = [...this.filteredGames].sort((a, b) => new Date(b.date) - new Date(a.date));

        sortedGames.forEach(game => {
            const row = this.createGameRow(game);
            tbody.appendChild(row);
        });
    }

    createGameRow(game) {
        const row = document.createElement('tr');
        const statusClass = game.status.toLowerCase();

        const homeDivision = this.getTeamDivision(game.home_team);
        const awayDivision = this.getTeamDivision(game.away_team);
        const division = homeDivision === awayDivision ? homeDivision : `${homeDivision} vs ${awayDivision}`;

        row.className = `game-row ${statusClass}`;
        row.style.cursor = 'pointer';
        row.onclick = () => {
            window.location.href = `game-detail.html?id=${game.id}`;
        };

        const date = new Date(game.date).toLocaleDateString('fr-CA', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });

        row.innerHTML = `
            <td style="white-space: nowrap;">${date}</td>
            <td>${game.away_team}</td>
            <td style="text-align: center; font-weight: bold; color: #2a5298;">
                ${game.away_score !== null ? game.away_score : '-'} - ${game.home_score !== null ? game.home_score : '-'}
            </td>
            <td>${game.home_team}</td>
            <td>
                <span class="status-badge ${statusClass}">
                    ${this.getStatusText(game.status)}
                </span>
            </td>
            <td>${division}</td>
        `;

        return row;
    }

    setupEventListeners() {
        // Team filter
        document.getElementById('team-filter').addEventListener('change', () => {
            this.applyFilters();
        });

        // Division filter
        document.getElementById('division-filter').addEventListener('change', () => {
            this.applyFilters();
        });
    }

    applyFilters() {
        const teamFilter = document.getElementById('team-filter').value;
        const divisionFilter = document.getElementById('division-filter').value;

        this.filteredGames = this.games.filter(game => {
            const teamMatch = !teamFilter ||
                game.home_team === teamFilter ||
                game.away_team === teamFilter;

            const homeDivision = this.getTeamDivision(game.home_team);
            const awayDivision = this.getTeamDivision(game.away_team);
            const gameDivision = homeDivision === awayDivision ? homeDivision : `${homeDivision} vs ${awayDivision}`;

            const divisionMatch = !divisionFilter || gameDivision.includes(divisionFilter);

            return teamMatch && divisionMatch;
        });

        this.renderGames();
    }

    getStatusText(status) {
        switch (status) {
            case 'FINAL': return 'Terminé';
            case 'LIVE': return 'En cours';
            case 'SCHEDULED': return 'À venir';
            default: return status;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM ready, initializing SimpleGamesManager...');
    new SimpleGamesManager();
});