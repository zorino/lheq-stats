// Dashboard JavaScript for LHEQ Statistics homepage
class Dashboard {
    constructor() {
        this.init();
    }

    async init() {
        try {
            await dataManager.loadData();
            this.renderDivisionStandings();
        } catch (error) {
            console.error('Error initializing dashboard:', error);
            this.showError();
        }
    }


    renderDivisionStandings() {
        const divisions = {
            "L'Entrepôt du Hockey": 'entrepot-hockey-body',
            'Hockey Experts': 'hockey-experts-body',
            'Sports Rousseau': 'sports-rousseau-body'
        };

        Object.entries(divisions).forEach(([divisionName, bodyId]) => {
            const standingsBody = document.getElementById(bodyId);
            const divisionTeams = dataManager.teams
                .filter(team => team.division === divisionName)
                .sort((a, b) => {
                    // Sort by points descending, then by goal differential descending
                    if (b.points !== a.points) {
                        return b.points - a.points;
                    }
                    return b.goal_differential - a.goal_differential;
                });

            standingsBody.innerHTML = '';

            divisionTeams.forEach((team, index) => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${index + 1}</td>
                    <td>
                        <a href="team-detail.html?id=${team.id}" class="team-link">
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <img src="${team.local_logo || 'assets/logos/default.png'}"
                                     alt="${team.name}"
                                     class="team-logo"
                                     onerror="this.style.display='none'">
                                <span>${this.truncateTeamName(team.name)}</span>
                            </div>
                        </a>
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

    /* Homepage division tables styling */
    .divisions-container {
        display: flex;
        flex-direction: column;
        gap: 2rem;
    }

    .division-standings {
        min-width: 0;
    }

    /* Make table text smaller on homepage to fit more content */
    .standings-table {
        font-size: 0.9rem;
    }

    .standings-table th,
    .standings-table td {
        padding: 0.75rem 0.5rem;
    }

    /* Team link styling */
    .team-link {
        color: inherit;
        text-decoration: none;
        display: block;
        transition: color 0.2s ease;
    }

    .team-link:hover {
        color: #007bff;
        text-decoration: none;
    }

    .team-link:hover .team-logo {
        opacity: 0.8;
    }

    /* Responsive adjustments for division tables */
    @media (max-width: 768px) {
        .divisions-container {
            gap: 1.5rem;
        }
    }
`;
document.head.appendChild(style);

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});