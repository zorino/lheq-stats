// Dashboard JavaScript for LHEQ Statistics homepage
class Dashboard {
    constructor() {
        this.init();
    }

    async init() {
        try {
            await dataManager.loadData();
            this.updateStatCards();
            this.renderStandings();
            this.renderTopScorers();
        } catch (error) {
            console.error('Error initializing dashboard:', error);
            this.showError();
        }
    }

    updateStatCards() {
        const totalTeams = dataManager.teams.length;
        const totalPlayers = dataManager.players.length;
        const totalGames = dataManager.games.length;
        const totalGoals = dataManager.getTotalGoals();

        document.getElementById('total-teams').textContent = utils.formatNumber(totalTeams);
        document.getElementById('total-players').textContent = utils.formatNumber(totalPlayers);
        document.getElementById('total-games').textContent = utils.formatNumber(totalGames);
        document.getElementById('total-goals').textContent = utils.formatNumber(totalGoals);
    }

    renderStandings() {
        const standingsBody = document.getElementById('standings-body');
        const topTeams = dataManager.teams.slice(0, 15); // Top 15 teams

        standingsBody.innerHTML = '';

        topTeams.forEach((team, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${index + 1}</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <img src="${team.local_logo || 'assets/logos/default.png'}"
                             alt="${team.name}"
                             class="team-logo"
                             onerror="this.style.display='none'">
                        <span>${this.truncateTeamName(team.name)}</span>
                    </div>
                </td>
                <td>${team.games_played}</td>
                <td>${team.wins}</td>
                <td>${team.losses}</td>
                <td>${team.ties}</td>
                <td><strong>${team.points}</strong></td>
                <td>${team.goals_for}</td>
                <td>${team.goals_against}</td>
                <td class="${team.goal_differential >= 0 ? 'positive' : 'negative'}">
                    ${team.goal_differential > 0 ? '+' : ''}${team.goal_differential}
                </td>
            `;
            standingsBody.appendChild(row);
        });
    }

    renderTopScorers() {
        const scorersBody = document.getElementById('scorers-body');
        const topScorers = dataManager.getSkaters()
            .filter(player => player.games_played > 0 && player.points > 0)
            .sort((a, b) => b.points - a.points) // Sort by points descending
            .slice(0, 15); // Top 15 scorers

        scorersBody.innerHTML = '';

        if (topScorers.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="7" class="text-center">Aucun marqueur trouvé</td>';
            scorersBody.appendChild(row);
            return;
        }

        topScorers.forEach((player, index) => {
            const teamName = dataManager.getTeamName(player.team_id);
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${index + 1}</td>
                <td><strong>${player.number ? '#' + player.number + ' ' : ''}${player.name}</strong></td>
                <td>${this.truncateTeamName(teamName)}</td>
                <td>${player.games_played}</td>
                <td>${player.goals}</td>
                <td>${player.assists}</td>
                <td><strong>${player.points}</strong></td>
            `;
            scorersBody.appendChild(row);
        });
    }

    truncateTeamName(name, maxLength = 20) {
        if (name.length <= maxLength) return name;
        return name.substring(0, maxLength) + '...';
    }

    showError() {
        const container = document.querySelector('.dashboard');
        if (container) {
            container.innerHTML = `
                <div class="error-message">
                    <h3>Erreur de chargement des données</h3>
                    <p>Impossible de charger les statistiques. Veuillez réessayer plus tard.</p>
                </div>
            `;
        }
    }
}

// Add some CSS for positive/negative values and homepage layout
const style = document.createElement('style');
style.textContent = `
    .positive { color: #28a745; }
    .negative { color: #dc3545; }
    .error-message {
        text-align: center;
        padding: 3rem;
        color: #666;
    }

    /* Homepage specific table sizing */
    .content-grid {
        grid-template-columns: 60% 40%;
        gap: 2rem;
    }

    .standings {
        min-width: 0; /* Allow flex shrinking */
    }

    .top-scorers {
        min-width: 0; /* Allow flex shrinking */
    }

    /* Responsive adjustments for homepage tables */
    @media (max-width: 1024px) {
        .content-grid {
            grid-template-columns: 65% 35%;
        }
    }

    @media (max-width: 768px) {
        .content-grid {
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }
    }

    /* Make table text smaller on homepage to fit more content */
    .standings-table,
    .scorers-table {
        font-size: 0.9rem;
    }

    .standings-table th,
    .standings-table td,
    .scorers-table th,
    .scorers-table td {
        padding: 0.75rem 0.5rem;
    }
`;
document.head.appendChild(style);

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});