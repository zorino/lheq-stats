// Team Detail page JavaScript for LHEQ Statistics
class TeamDetailPage {
    constructor() {
        this.teamId = null;
        this.teamData = null;
        this.formations = null;
        this.players = [];
        this.teamGames = [];
        this.currentGamePage = 0;
        this.gamesPerPage = 5;
        this.skaterDataTable = null;
        this.goalieDataTable = null;
        this.init();
    }

    async init() {
        try {
            // Get team ID from URL parameter
            const urlParams = new URLSearchParams(window.location.search);
            this.teamId = urlParams.get('id');

            console.log('Team ID from URL:', this.teamId);

            if (!this.teamId) {
                this.showError('Team ID not found in URL');
                return;
            }

            // Show loading state
            this.showLoading();

            // Load data
            await dataManager.loadData();
            await this.loadFormations();

            console.log('Available teams:', dataManager.teams.map(t => ({ id: t.id, name: t.name })));

            // Get team data
            this.teamData = dataManager.getTeamById(this.teamId);
            console.log('Found team data:', this.teamData);

            if (!this.teamData) {
                this.showError(`Team not found for ID: ${this.teamId}`);
                return;
            }

            // Get players for this team
            this.players = dataManager.getAllPlayers().filter(player =>
                player.team_id == this.teamId // Use == instead of === for type coercion
            );

            // Get games for this team
            this.teamGames = dataManager.games.filter(game =>
                game.home_team === this.teamData.name || game.away_team === this.teamData.name
            ).sort((a, b) => new Date(b.date) - new Date(a.date)); // Most recent first

            console.log('Found players:', this.players.length);
            console.log('Found games:', this.teamGames.length);

            // Setup UI
            this.setupEventListeners();
            this.renderTeamHeader();
            this.renderGames();
            this.renderFormations();
            this.renderRoster();

        } catch (error) {
            console.error('Error loading team detail page:', error);
            this.showError(`Error loading team data: ${error.message}`);
        }
    }

    async loadFormations() {
        try {
            const response = await fetch('data/formations.json');
            if (response.ok) {
                this.formations = await response.json();
            } else {
                console.warn('Formations data not available');
                this.formations = {};
            }
        } catch (error) {
            console.warn('Error loading formations:', error);
            this.formations = {};
        }
    }

    setupEventListeners() {
        // Tab switching
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Game pagination
        const prevBtn = document.getElementById('games-prev');
        const nextBtn = document.getElementById('games-next');

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                this.previousGamesPage();
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                this.nextGamesPage();
            });
        }
    }

    switchTab(tabName) {
        // Update button states
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }

    renderTeamHeader() {
        // Set team name
        const teamNameEl = document.getElementById('team-name');
        if (teamNameEl) teamNameEl.textContent = this.teamData.name;

        // Set team logo
        const logoImg = document.getElementById('team-logo');
        if (logoImg) {
            // Try PNG first, fallback to JPG
            logoImg.src = `assets/logos/team_${this.teamData.id}.png`;
            logoImg.alt = `${this.teamData.name} Logo`;
            logoImg.onerror = () => {
                logoImg.src = `assets/logos/team_${this.teamData.id}.jpg`;
                logoImg.onerror = () => {
                    logoImg.style.display = 'none';
                };
            };
        }

        // Set record
        const winsEl = document.getElementById('team-wins');
        const lossesEl = document.getElementById('team-losses');
        const tiesEl = document.getElementById('team-ties');
        const pointsEl = document.getElementById('team-points');

        if (winsEl) winsEl.textContent = this.teamData.wins || 0;
        if (lossesEl) lossesEl.textContent = this.teamData.losses || 0;
        if (tiesEl) tiesEl.textContent = this.teamData.ties || 0;
        if (pointsEl) pointsEl.textContent = this.teamData.points || 0;

        // Set main stats
        const gpEl = document.getElementById('team-gp');
        const gfEl = document.getElementById('team-gf');
        const gaEl = document.getElementById('team-ga');
        const diffEl = document.getElementById('team-diff');

        if (gpEl) gpEl.textContent = this.teamData.games_played || 0;
        if (gfEl) gfEl.textContent = this.teamData.goals_for || 0;
        if (gaEl) gaEl.textContent = this.teamData.goals_against || 0;

        if (diffEl) {
            const diff = (this.teamData.goals_for || 0) - (this.teamData.goals_against || 0);
            diffEl.textContent = diff > 0 ? `+${diff}` : diff.toString();
            diffEl.className = `stat-value ${diff >= 0 ? 'positive' : 'negative'}`;
        }

        // Set records
        const homeEl = document.getElementById('team-home');
        const awayEl = document.getElementById('team-away');
        const pimEl = document.getElementById('team-pim');

        if (homeEl) {
            homeEl.textContent = `${this.teamData.home_wins || 0}-${this.teamData.home_losses || 0}-${this.teamData.home_ties || 0}`;
        }
        if (awayEl) {
            awayEl.textContent = `${this.teamData.away_wins || 0}-${this.teamData.away_losses || 0}-${this.teamData.away_ties || 0}`;
        }
        if (pimEl) {
            pimEl.textContent = this.teamData.penalty_minutes || 0;
        }

        // Set PP%
        const ppEl = document.getElementById('team-pp');
        if (ppEl) {
            const ppOpportunities = this.teamData.powerplay_opportunities || 0;
            const ppPercent = ppOpportunities > 0 ?
                ((this.teamData.powerplay_goals_for || 0) / ppOpportunities * 100).toFixed(1) + '%' : '0.0%';
            ppEl.textContent = ppPercent;
        }
    }

    renderGames() {
        this.renderGamesTable();
        this.updateGamesPagination();
    }

    renderGamesTable() {
        const tbody = document.getElementById('games-body');
        tbody.innerHTML = '';

        if (this.teamGames.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="5" class="text-center">Aucun match trouvé</td>';
            tbody.appendChild(row);
            return;
        }

        const startIndex = this.currentGamePage * this.gamesPerPage;
        const endIndex = Math.min(startIndex + this.gamesPerPage, this.teamGames.length);
        const pagingGames = this.teamGames.slice(startIndex, endIndex);

        pagingGames.forEach(game => {
            const row = this.createGameRow(game);
            tbody.appendChild(row);
        });
    }

    createGameRow(game) {
        const row = document.createElement('tr');

        // Determine if team is home or away
        const isHome = game.home_team === this.teamData.name;
        const opponentName = isHome ? game.away_team : game.home_team;

        // Determine result
        const teamScore = isHome ? game.home_score : game.away_score;
        const opponentScore = isHome ? game.away_score : game.home_score;

        let result, resultClass;
        if (teamScore > opponentScore) {
            result = 'V';
            resultClass = 'win';
        } else if (teamScore < opponentScore) {
            result = 'D';
            resultClass = 'loss';
        } else {
            result = 'N';
            resultClass = 'tie';
        }

        const date = new Date(game.date).toLocaleDateString('fr-CA', {
            day: '2-digit',
            month: '2-digit'
        });

        row.innerHTML = `
            <td>${date}</td>
            <td>${opponentName}</td>
            <td>${isHome ? 'Dom' : 'Ext'}</td>
            <td><span class="result-badge ${resultClass}">${result}</span></td>
            <td><strong>${teamScore}-${opponentScore}</strong></td>
        `;

        // Make the row clickable to navigate to game detail
        row.style.cursor = 'pointer';
        row.addEventListener('click', () => {
            window.location.href = `game-detail.html?id=${game.id}`;
        });

        return row;
    }

    updateGamesPagination() {
        const totalGames = this.teamGames.length;
        const totalPages = Math.ceil(totalGames / this.gamesPerPage);
        const startIndex = this.currentGamePage * this.gamesPerPage + 1;
        const endIndex = Math.min((this.currentGamePage + 1) * this.gamesPerPage, totalGames);

        const prevBtn = document.getElementById('games-prev');
        const nextBtn = document.getElementById('games-next');
        const infoSpan = document.getElementById('games-info');

        if (prevBtn) prevBtn.disabled = this.currentGamePage === 0;
        if (nextBtn) nextBtn.disabled = this.currentGamePage >= totalPages - 1;
        if (infoSpan) infoSpan.textContent = `Matchs ${startIndex}-${endIndex} sur ${totalGames}`;
    }

    previousGamesPage() {
        if (this.currentGamePage > 0) {
            this.currentGamePage--;
            this.renderGames();
        }
    }

    nextGamesPage() {
        const totalPages = Math.ceil(this.teamGames.length / this.gamesPerPage);
        if (this.currentGamePage < totalPages - 1) {
            this.currentGamePage++;
            this.renderGames();
        }
    }

    renderFormations() {
        const teamFormations = this.formations[this.teamId];

        if (!teamFormations) {
            return; // Keep default "no data" messages
        }

        this.renderForwardLines(teamFormations.forward_lines || []);
        this.renderDefensePairs(teamFormations.defense_pairs || []);
        this.renderPowerplayUnits(teamFormations.powerplay_units || []);
    }

    renderForwardLines(lines) {
        const container = document.getElementById('f-lines');

        if (lines.length === 0) {
            container.innerHTML = '<p class="no-data">Aucune ligne détectée</p>';
            return;
        }

        container.innerHTML = '';

        lines.forEach((line, index) => {
            const lineCard = document.createElement('div');
            lineCard.className = 'formation-card';

            let playersHtml;
            let lineLabel;

            // Use the rank from the data or fallback to index
            lineLabel = line.rank || `F${index + 1}`;

            playersHtml = line.players.map(player =>
                `<span class="player-name">${player.number ? '#' + player.number + ' ' : ''}${player.name}</span>`
            ).join(' • ');

            // Add ? for missing players if it's a pair
            if (line.type === 'pair' && line.players.length === 2) {
                playersHtml += ' • <span class="unknown-player">?</span>';
            }

            lineCard.innerHTML = `
                <div class="formation-header">
                    <h5>${lineLabel}</h5>
                    <div class="formation-stats">
                        <span class="formation-count">${line.goals || 0} buts</span>
                    </div>
                </div>
                <div class="formation-players">
                    ${playersHtml}
                </div>
            `;

            container.appendChild(lineCard);
        });
    }

    renderDefensePairs(pairs) {
        const container = document.getElementById('d-pairs');

        if (pairs.length === 0) {
            container.innerHTML = '<p class="no-data">Aucune paire détectée</p>';
            return;
        }

        container.innerHTML = '';

        pairs.forEach((pair, index) => {
            const pairCard = document.createElement('div');
            pairCard.className = 'formation-card';

            const playersHtml = pair.players.map(player =>
                `<span class="player-name">${player.number ? '#' + player.number + ' ' : ''}${player.name}</span>`
            ).join(' • ');

            const pairLabel = pair.rank || `Paire ${index + 1}`;

            pairCard.innerHTML = `
                <div class="formation-header">
                    <h5>${pairLabel}</h5>
                    <div class="formation-stats">
                        <span class="formation-count">${pair.goals || 0} buts</span>
                    </div>
                </div>
                <div class="formation-players">
                    ${playersHtml}
                </div>
            `;

            container.appendChild(pairCard);
        });
    }

    renderPowerplayUnits(units) {
        const container = document.getElementById('pp-units');

        if (units.length === 0) {
            container.innerHTML = '<p class="no-data">Aucune unité détectée</p>';
            return;
        }

        container.innerHTML = '';

        units.forEach((unit, index) => {
            const unitCard = document.createElement('div');
            unitCard.className = 'formation-card';

            let playersHtml = unit.players.map(player =>
                `<span class="player-name">${player.number ? '#' + player.number + ' ' : ''}${player.name} (${player.position})</span>`
            ).join(' • ');

            // Add ? for missing players if unit has less than 5 players
            const missingPlayers = 5 - unit.players.length;
            if (missingPlayers > 0) {
                const questionMarks = Array(missingPlayers).fill('<span class="unknown-player">?</span>').join(' • ');
                playersHtml += ' • ' + questionMarks;
            }

            const unitLabel = unit.rank || `PP ${index + 1}`;

            unitCard.innerHTML = `
                <div class="formation-header">
                    <h5>${unitLabel}</h5>
                    <div class="formation-stats">
                        <span class="formation-count">${unit.goals || 0} buts</span>
                    </div>
                </div>
                <div class="formation-players">
                    ${playersHtml}
                </div>
            `;

            container.appendChild(unitCard);
        });
    }


    renderRoster() {
        const skaters = this.players.filter(p => p.position !== 'G');
        const goalies = this.players.filter(p => p.position === 'G');

        this.renderSkaters(skaters);
        this.renderGoalies(goalies);

        // Initialize sortable tables after DOM update
        setTimeout(() => {
            this.initSortableTables(skaters, goalies);
        }, 100);
    }

    initSortableTables(skaters, goalies) {
        // Get table elements by finding the correct table IDs
        const skaterTable = document.querySelector('#skaters-tab table');
        const goalieTable = document.querySelector('#goalies-tab table');

        if (skaterTable && skaters.length > 0) {
            skaterTable.id = 'skaters-table';

            if (this.skaterDataTable) {
                this.skaterDataTable.destroy();
            }

            this.skaterDataTable = $('#skaters-table').DataTable({
                paging: false,
                searching: false,
                ordering: true,
                info: false,
                columnDefs: [
                    { orderable: false, targets: [0] }, // Player name
                    { type: 'num', targets: [2, 3, 4, 5, 6, 7, 8] }, // Numeric columns
                ],
                order: [[5, 'desc']], // Sort by Points descending
            });
        }

        if (goalieTable && goalies.length > 0) {
            goalieTable.id = 'goalies-table';

            if (this.goalieDataTable) {
                this.goalieDataTable.destroy();
            }

            this.goalieDataTable = $('#goalies-table').DataTable({
                paging: false,
                searching: false,
                ordering: true,
                info: false,
                columnDefs: [
                    { orderable: false, targets: [0] }, // Player name
                    { type: 'num', targets: [1, 2, 3, 4, 5, 6] }, // Numeric columns
                ],
                order: [[6, 'asc']], // Sort by GAA ascending
            });
        }
    }

    renderSkaters(skaters) {
        const tbody = document.getElementById('skaters-body');
        tbody.innerHTML = '';

        if (skaters.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="9" class="text-center">Aucun joueur trouvé</td>';
            tbody.appendChild(row);
            return;
        }

        // Sort by points descending
        skaters.sort((a, b) => b.points - a.points);

        skaters.forEach(player => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${player.number ? '#' + player.number + ' ' : ''}${player.name}</strong></td>
                <td><span class="position-badge position-${player.position}">${player.position}</span></td>
                <td>${player.games_played}</td>
                <td>${player.goals}</td>
                <td>${player.assists}</td>
                <td><strong>${player.points}</strong></td>
                <td>${player.penalty_minutes}</td>
                <td>${player.powerplay_goals}</td>
                <td>${player.shorthanded_goals}</td>
            `;
            tbody.appendChild(row);
        });
    }

    renderGoalies(goalies) {
        const tbody = document.getElementById('goalies-body');
        tbody.innerHTML = '';

        if (goalies.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="7" class="text-center">Aucun gardien trouvé</td>';
            tbody.appendChild(row);
            return;
        }

        // Sort by games played descending
        goalies.sort((a, b) => b.games_played - a.games_played);

        goalies.forEach(goalie => {
            const gaa = utils.formatGoalsAgainstAverage(goalie.goals_against, goalie.games_played);

            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${goalie.number ? '#' + goalie.number + ' ' : ''}${goalie.name}</strong></td>
                <td>${goalie.games_played}</td>
                <td>${goalie.wins}</td>
                <td>${goalie.losses}</td>
                <td>${goalie.ties}</td>
                <td>${goalie.goals_against}</td>
                <td>${gaa}</td>
            `;
            tbody.appendChild(row);
        });
    }

    showLoading() {
        // Don't replace the entire container, just show loading on the team name
        const teamNameEl = document.getElementById('team-name');
        if (teamNameEl) {
            teamNameEl.textContent = 'Chargement...';
        }
    }

    showError(message) {
        const main = document.querySelector('.main .container');
        main.innerHTML = `
            <div class="error-message">
                <h3>Erreur</h3>
                <p>${message}</p>
                <a href="teams.html" class="btn">Retour aux équipes</a>
            </div>
        `;
    }
}

// Add CSS styles for team detail page
const style = document.createElement('style');
style.textContent = `
    .team-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2rem;
        padding: 1.5rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .team-info {
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }

    .team-logo img {
        width: 80px;
        height: 80px;
        border-radius: 8px;
    }

    .team-details h2 {
        margin: 0 0 1rem 0;
        font-size: 2rem;
    }

    .team-stats {
        display: flex;
        gap: 2rem;
    }

    .stat-item {
        display: flex;
        flex-direction: column;
        text-align: center;
    }

    .stat-label {
        font-size: 0.9rem;
        color: #666;
        font-weight: bold;
    }

    .back-link a {
        color: #007bff;
        text-decoration: none;
        font-weight: 500;
    }

    .back-link a:hover {
        text-decoration: underline;
    }

    .content-grid {
        display: grid;
        grid-template-columns: 1fr 2fr;
        gap: 2rem;
        margin-top: 2rem;
    }

    .formations, .roster {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .formation-section {
        margin-bottom: 2rem;
    }

    .formation-section h4 {
        margin-bottom: 1rem;
        color: #333;
        border-bottom: 2px solid #007bff;
        padding-bottom: 0.5rem;
    }

    .formations-list {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .formation-card {
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 1rem;
        background: #f8f9fa;
    }

    .formation-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }

    .formation-header h5 {
        margin: 0;
        color: #333;
    }

    .formation-stats {
        display: flex;
        gap: 1rem;
        font-size: 0.9rem;
    }

    .formation-count {
        background: #007bff;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }

    .formation-assists {
        background: #ffc107;
        color: #212529;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }

    .formation-confidence {
        background: #28a745;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }

    .formation-players {
        color: #555;
        font-weight: 500;
    }

    .player-name {
        font-weight: bold;
    }

    .unknown-player {
        color: #999;
        font-style: italic;
        font-weight: normal;
    }

    .no-data {
        color: #666;
        font-style: italic;
        text-align: center;
        padding: 1rem;
    }

    .player-tabs {
        display: flex;
        margin-bottom: 1rem;
        border-bottom: 1px solid #e0e0e0;
    }

    .tab-btn {
        background: none;
        border: none;
        padding: 1rem 1.5rem;
        cursor: pointer;
        border-bottom: 2px solid transparent;
        font-weight: 500;
    }

    .tab-btn.active {
        border-bottom-color: #007bff;
        color: #007bff;
    }

    .tab-content {
        display: none;
    }

    .tab-content.active {
        display: block;
    }

    .loading-state, .error-message {
        text-align: center;
        padding: 3rem;
        color: #666;
    }

    .btn {
        display: inline-block;
        padding: 0.75rem 1.5rem;
        background: #007bff;
        color: white;
        text-decoration: none;
        border-radius: 4px;
        margin-top: 1rem;
    }

    .btn:hover {
        background: #0056b3;
    }

    @media (max-width: 768px) {
        .content-grid {
            grid-template-columns: 1fr;
        }

        .team-header {
            flex-direction: column;
            gap: 1rem;
            text-align: center;
        }

        .team-info {
            flex-direction: column;
            text-align: center;
        }

        .team-stats {
            justify-content: center;
        }

        .formation-header {
            flex-direction: column;
            gap: 0.5rem;
            text-align: center;
        }

        .formation-stats {
            justify-content: center;
        }
    }
`;
document.head.appendChild(style);

// Initialize team detail page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TeamDetailPage();
});
