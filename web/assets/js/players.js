// Players page JavaScript for LHEQ Statistics
class PlayersPage {
    constructor() {
        this.currentSkaters = [];
        this.currentGoalies = [];
        this.showingSkaters = true;
        this.skaterDataTable = null;
        this.goalieDataTable = null;
        this.init();
    }

    async init() {
        try {
            const tableBody = document.getElementById('skater-table-body');
            loadingUtils.showLoading(tableBody);

            await dataManager.loadData();
            this.currentSkaters = [...dataManager.getSkaters()];
            this.currentGoalies = [...dataManager.getGoalies()];

            this.setupEventListeners();
            this.populateTeamFilter();
            this.populateDivisionFilter();
            this.renderTable();

            // Initialize DataTables after DOM update - only for the initial skaters table
            setTimeout(() => {
                this.initSkaterDataTable();
            }, 100);
        } catch (error) {
            console.error('Error loading players page:', error);
            this.showError();
        }
    }

    initDataTables() {
        // Initialize Skater DataTable
        if (this.skaterDataTable) {
            this.skaterDataTable.destroy();
        }

        this.skaterDataTable = $('#skater-table').DataTable({
            paging: false,
            searching: false,
            ordering: true,
            info: false,
            columnDefs: [
                { orderable: false, targets: [0, 1, 2, 3] }, // Pos, Player, Team, Position
                { type: 'num', targets: [4, 5, 6, 7, 8, 9, 10, 11, 12] }, // Numeric columns
            ],
            order: [[7, 'desc']] // Sort by Points (Pts) descending
        });

        // Initialize Goalie DataTable
        if (this.goalieDataTable) {
            this.goalieDataTable.destroy();
        }

        this.goalieDataTable = $('#goalie-table').DataTable({
            paging: false,
            searching: false,
            ordering: true,
            info: false,
            columnDefs: [
                { orderable: false, targets: [0, 1, 2] }, // Pos, Goalie, Team
                { type: 'num', targets: [3, 4, 5, 6] }, // Numeric columns
            ],
            order: [[6, 'asc']] // Sort by GAA ascending (lower is better)
        });
    }

    initSkaterDataTable() {
        // Initialize/Re-initialize Skater DataTable
        if (this.skaterDataTable) {
            this.skaterDataTable.destroy();
        }

        this.skaterDataTable = $('#skater-table').DataTable({
            paging: false,
            searching: false,
            ordering: true,
            info: false,
            columnDefs: [
                { orderable: false, targets: [0, 1, 2, 3] }, // Pos, Player, Team, Position
                { type: 'num', targets: [4, 5, 6, 7, 8, 9, 10, 11, 12] }, // Numeric columns
            ],
            order: [[7, 'desc']] // Sort by Points (Pts) descending
        });
    }

    initGoalieDataTable() {
        // Initialize/Re-initialize Goalie DataTable
        if (this.goalieDataTable) {
            this.goalieDataTable.destroy();
        }

        // Make sure the table has the data before initializing DataTables
        const tableHasData = document.querySelectorAll('#goalie-table tbody tr').length > 0;

        if (!tableHasData) {
            return;
        }

        try {
            this.goalieDataTable = $('#goalie-table').DataTable({
                paging: false,
                searching: false,
                ordering: true,
                info: false,
                columnDefs: [
                    { orderable: false, targets: [0, 1, 2] }, // Pos, Goalie, Team
                    { type: 'num', targets: [3, 4, 5, 6, 7, 8] }, // Numeric columns
                ],
                order: [[8, 'asc']] // Sort by GAA ascending (lower is better)
            });
        } catch (error) {
            console.error('Error initializing goalie DataTable:', error);
        }
    }

    setupEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('player-search');
        searchInput.addEventListener('input', utils.debounce((e) => {
            this.handleSearch(e.target.value);
        }, 300));

        // Position filter
        const positionFilter = document.getElementById('position-filter');
        positionFilter.addEventListener('change', (e) => {
            this.handlePositionFilter(e.target.value);
        });

        // Division filter
        const divisionFilter = document.getElementById('division-filter');
        divisionFilter.addEventListener('change', (e) => {
            this.handleDivisionFilter(e.target.value);
        });

        // Team filter
        const teamFilter = document.getElementById('team-filter');
        teamFilter.addEventListener('change', (e) => {
            this.handleTeamFilter(e.target.value);
        });


        // Toggle between skaters and goalies
        const skaterBtn = document.getElementById('skater-stats-btn');
        const goalieBtn = document.getElementById('goalie-stats-btn');

        skaterBtn.addEventListener('click', () => {
            this.togglePlayerType(true);
        });

        goalieBtn.addEventListener('click', () => {
            this.togglePlayerType(false);
        });
    }

    populateTeamFilter() {
        const teamFilter = document.getElementById('team-filter');
        const teams = [...dataManager.teams].sort((a, b) => a.name.localeCompare(b.name));

        teams.forEach(team => {
            const option = document.createElement('option');
            option.value = team.id;
            option.textContent = team.name;
            teamFilter.appendChild(option);
        });
    }

    populateDivisionFilter() {
        const divisionFilter = document.getElementById('division-filter');
        const divisions = new Set();

        // Collect all unique divisions from teams data
        dataManager.teams.forEach(team => {
            if (team.division) {
                divisions.add(team.division);
            }
        });

        // Add division options to the select
        Array.from(divisions).sort().forEach(division => {
            const option = document.createElement('option');
            option.value = division;
            option.textContent = division;
            divisionFilter.appendChild(option);
        });
    }

    togglePlayerType(showSkaters) {
        this.showingSkaters = showSkaters;

        // Update button states
        const skaterBtn = document.getElementById('skater-stats-btn');
        const goalieBtn = document.getElementById('goalie-stats-btn');

        if (showSkaters) {
            skaterBtn.classList.add('active');
            goalieBtn.classList.remove('active');
            document.getElementById('skater-table').style.display = 'table';
            document.getElementById('goalie-table').style.display = 'none';
        } else {
            goalieBtn.classList.add('active');
            skaterBtn.classList.remove('active');
            document.getElementById('skater-table').style.display = 'none';
            document.getElementById('goalie-table').style.display = 'table';
        }

        // Re-apply filters for the new player type
        this.applyAllFilters();
    }

    handleSearch(searchTerm) {
        this.applyAllFilters();
    }

    handlePositionFilter(position) {
        this.applyAllFilters();
    }

    handleDivisionFilter(division) {
        this.applyAllFilters();
    }

    handleTeamFilter(teamId) {
        this.applyAllFilters();
    }


    applyAllFilters() {
        const searchInput = document.getElementById('player-search');
        const positionInput = document.getElementById('position-filter');
        const divisionInput = document.getElementById('division-filter');
        const teamInput = document.getElementById('team-filter');

        // Check if elements exist before trying to access their values
        const searchTerm = searchInput ? searchInput.value : '';
        const position = positionInput ? positionInput.value : '';
        const division = divisionInput ? divisionInput.value : '';
        const teamId = teamInput ? teamInput.value : '';


        if (this.showingSkaters) {
            let filtered = [...dataManager.getSkaters()];

            // Apply search filter
            filtered = filterUtils.searchPlayers(filtered, searchTerm);

            // Apply position filter (for skaters, this could be F or D)
            if (position) {
                filtered = filterUtils.filterPlayersByPosition(filtered, position);
            }

            // Apply division filter
            if (division) {
                filtered = filterUtils.filterPlayersByDivision(filtered, division);
            }

            // Apply team filter
            if (teamId) {
                filtered = filterUtils.filterPlayersByTeam(filtered, teamId);
            }

            this.currentSkaters = filtered;
        } else {
            let filtered = [...dataManager.getGoalies()];

            // Apply search filter
            filtered = filterUtils.searchPlayers(filtered, searchTerm);

            // Apply division filter
            if (division) {
                filtered = filterUtils.filterPlayersByDivision(filtered, division);
            }

            // Apply team filter
            if (teamId) {
                filtered = filterUtils.filterPlayersByTeam(filtered, teamId);
            }

            this.currentGoalies = filtered;
        }

        this.renderTable();
    }

    renderTable() {
        if (this.showingSkaters) {
            this.renderSkaterTable();
        } else {
            this.renderGoalieTable();
        }
    }

    renderSkaterTable() {
        // First, destroy the existing DataTable if it exists
        if (this.skaterDataTable) {
            this.skaterDataTable.destroy();
            this.skaterDataTable = null;
        }

        const tableBody = document.getElementById('skater-table-body');
        tableBody.innerHTML = '';

        if (this.currentSkaters.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="13" class="text-center">Aucun joueur trouvé</td>';
            tableBody.appendChild(row);
            return;
        }

        // Add all the rows first
        this.currentSkaters.forEach((player, index) => {
            const row = this.createSkaterRow(player, index + 1);
            tableBody.appendChild(row);
        });

        // Then initialize DataTables on the populated table
        setTimeout(() => {
            this.initSkaterDataTable();
        }, 50);
    }

    renderGoalieTable() {
        // First, destroy the existing DataTable if it exists
        if (this.goalieDataTable) {
            this.goalieDataTable.destroy();
            this.goalieDataTable = null;
        }

        const tableBody = document.getElementById('goalie-table-body');
        tableBody.innerHTML = '';

        if (this.currentGoalies.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="9" class="text-center">Aucun gardien trouvé</td>';
            tableBody.appendChild(row);
            return;
        }

        // Add all the rows first
        this.currentGoalies.forEach((goalie, index) => {
            const row = this.createGoalieRow(goalie, index + 1);
            tableBody.appendChild(row);
        });

        // Then initialize DataTables on the populated table
        setTimeout(() => {
            this.initGoalieDataTable();
        }, 50);
    }

    createSkaterRow(player, position) {
        const row = document.createElement('tr');
        const teamName = dataManager.getTeamName(player.team_id);

        row.innerHTML = `
            <td>${position}</td>
            <td><strong>${player.number ? '#' + player.number + ' ' : ''}${player.name}</strong></td>
            <td>${teamName}</td>
            <td><span class="position-badge position-${player.position}">${player.position}</span></td>
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

        return row;
    }

    createGoalieRow(goalie, position) {
        const row = document.createElement('tr');
        const teamName = dataManager.getTeamName(goalie.team_id);
        const gaa = utils.formatGoalsAgainstAverage(goalie.goals_against, goalie.games_played);

        row.innerHTML = `
            <td>${position}</td>
            <td><strong>${goalie.number ? '#' + goalie.number + ' ' : ''}${goalie.name}</strong></td>
            <td>${teamName}</td>
            <td>${goalie.games_played}</td>
            <td>${goalie.wins}</td>
            <td>${goalie.losses}</td>
            <td>${goalie.ties}</td>
            <td>${goalie.goals_against}</td>
            <td>${gaa}</td>
        `;

        return row;
    }

    showError() {
        const container = document.querySelector('.container');
        if (container) {
            container.innerHTML = `
                <div class="error-message">
                    <h3>Erreur de chargement des données</h3>
                    <p>Impossible de charger les statistiques des joueurs. Veuillez réessayer plus tard.</p>
                </div>
            `;
        }
    }
}

// Add additional CSS for players page
const style = document.createElement('style');
style.textContent = `
    .position-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        text-align: center;
        min-width: 24px;
    }

    .position-F {
        background-color: #e3f2fd;
        color: #1976d2;
    }

    .position-D {
        background-color: #f3e5f5;
        color: #7b1fa2;
    }

    .position-G {
        background-color: #e8f5e8;
        color: #388e3c;
    }

    .players-table tbody tr:hover {
        background-color: #f8f9fa;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
    }

    .error-message {
        text-align: center;
        padding: 3rem;
        color: #666;
    }

    .filters {
        flex-wrap: wrap;
        gap: 1rem;
    }

    .filter-options {
        display: flex;
        gap: 1rem;
        align-items: center;
        flex-wrap: wrap;
    }

    @media (max-width: 768px) {
        .players-table th:nth-child(n+10),
        .players-table td:nth-child(n+10) {
            display: none;
        }

        .filter-options {
            flex-direction: column;
            align-items: stretch;
        }

        .filter-options select {
            width: 100%;
        }
    }

    @media (max-width: 480px) {
        .players-table th:nth-child(n+7),
        .players-table td:nth-child(n+7) {
            display: none;
        }
    }
`;
document.head.appendChild(style);

// Initialize players page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PlayersPage();
});