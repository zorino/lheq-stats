class GameDetailManager {
    constructor() {
        this.gameId = null;
        this.gameData = null;
        this.init();
    }

    async init() {
        this.gameId = new URLSearchParams(window.location.search).get('id');
        if (!this.gameId) {
            window.location.href = 'games.html';
            return;
        }

        await this.loadGameData();
        this.renderGameHeader();
        this.setupDownloadButton();
        this.renderGameContent();
    }

    async loadGameData() {
        try {
            const response = await fetch(`data/games/game_${this.gameId}.json`);
            if (!response.ok) {
                throw new Error('Game not found');
            }
            this.gameData = await response.json();
        } catch (error) {
            console.error('Error loading game data:', error);
            document.body.innerHTML = '<div class="error">Match non trouvé.</div>';
        }
    }

    renderGameHeader() {
        const game = this.gameData;
        const scoreCard = document.getElementById('game-score-card');

        scoreCard.innerHTML = `
            <div class="game-matchup-header">
                <div class="team-section away">
                    <div class="team-logo">
                        ${game.boxscore?.teams?.[1]?.logoUrl ?
                            `<img src="${game.boxscore.teams[1].logoUrl}" alt="${game.away_team}">` :
                            '<div class="team-placeholder">🏒</div>'
                        }
                    </div>
                    <div class="team-info">
                        <h2>${game.away_team}</h2>
                        <div class="team-score">${game.away_score}</div>
                    </div>
                </div>

                <div class="game-info">
                    <div class="game-date">${this.formatDate(game.date)}</div>
                    <div class="game-status ${game.status.toLowerCase()}">${this.getStatusText(game.status)}</div>
                </div>

                <div class="team-section home">
                    <div class="team-info">
                        <h2>${game.home_team}</h2>
                        <div class="team-score">${game.home_score}</div>
                    </div>
                    <div class="team-logo">
                        ${game.boxscore?.teams?.[0]?.logoUrl ?
                            `<img src="${game.boxscore.teams[0].logoUrl}" alt="${game.home_team}">` :
                            '<div class="team-placeholder">🏒</div>'
                        }
                    </div>
                </div>
            </div>
        `;

        // Update page title
        document.title = `${game.away_team} @ ${game.home_team} - ${this.formatDate(game.date)} - LHEQ Statistics`;
    }

    setupDownloadButton() {
        const downloadBtn = document.getElementById('download-gamesheet');
        const viewOriginalBtn = document.getElementById('view-original');

        if (this.gameData.gamesheet_pdf_url) {
            downloadBtn.onclick = () => {
                window.open(`data/gamesheets/game_${this.gameId}.pdf`, '_blank');
            };
        } else {
            downloadBtn.style.display = 'none';
        }

        // Always show the LHEQ link using the correct URL format
        viewOriginalBtn.href = `https://page.spordle.com/fr/ligue-de-hockey-d-excellence-du-quebec-masculin/schedule/${this.gameId}`;
    }

    renderGameContent() {
        this.renderPeriodScores();
        this.renderGoals();
        this.renderPenalties();
    }

    renderPeriodScores() {
        const tbody = document.getElementById('period-scores-body');
        const game = this.gameData;

        // Calculate period scores from goals
        const homeScores = { 1: 0, 2: 0, 3: 0, 4: 0 };
        const awayScores = { 1: 0, 2: 0, 3: 0, 4: 0 };

        if (game.boxscore?.goals) {
            game.boxscore.goals.forEach(goal => {
                const period = parseInt(goal.gameTime.period);
                const isHome = goal.teamId === game.boxscore.teams[0].id;

                if (isHome) {
                    homeScores[period]++;
                } else {
                    awayScores[period]++;
                }
            });
        }

        tbody.innerHTML = `
            <tr>
                <td><strong>${game.away_team}</strong></td>
                <td>${awayScores[1]}</td>
                <td>${awayScores[2]}</td>
                <td>${awayScores[3]}</td>
                <td>${awayScores[4] || '-'}</td>
                <td><strong>${game.away_score}</strong></td>
            </tr>
            <tr>
                <td><strong>${game.home_team}</strong></td>
                <td>${homeScores[1]}</td>
                <td>${homeScores[2]}</td>
                <td>${homeScores[3]}</td>
                <td>${homeScores[4] || '-'}</td>
                <td><strong>${game.home_score}</strong></td>
            </tr>
        `;
    }

    renderGoals() {
        const goalsList = document.getElementById('goals-list');
        const goals = this.gameData.boxscore?.goals || [];

        if (goals.length === 0) {
            goalsList.innerHTML = '<div class="no-data">Aucun but marqué dans ce match.</div>';
            return;
        }

        goalsList.innerHTML = goals.map(goal => this.createGoalCard(goal)).join('');
    }

    createGoalCard(goal) {
        const game = this.gameData;
        const isHome = goal.teamId === game.boxscore.teams[0].id;
        const teamName = isHome ? game.home_team : game.away_team;

        const assists = goal.assists?.map(assist =>
            `${assist.fullName} (#${assist.number})`
        ).join(', ') || 'Aucune aide';

        const goalType = [];
        if (goal.isPowerplay) goalType.push('Jeu de puissance');
        if (goal.isShorthanded) goalType.push('Infériorité numérique');
        if (goal.isEmptyNet) goalType.push('Filet désert');
        if (goal.isPenaltyShot) goalType.push('Tir de pénalité');

        return `
            <div class="goal-card ${isHome ? 'home' : 'away'}">
                <div class="goal-header">
                    <div class="goal-scorer">
                        <strong>${goal.participant.fullName}</strong> (#${goal.participant.number})
                    </div>
                    <div class="goal-time">
                        ${goal.gameTime.period}e période - ${goal.gameTime.minutes}:${goal.gameTime.seconds.toString().padStart(2, '0')}
                    </div>
                </div>
                <div class="goal-details">
                    <div class="goal-team">${teamName}</div>
                    <div class="goal-assists">Aides: ${assists}</div>
                    ${goalType.length > 0 ? `<div class="goal-type">${goalType.join(', ')}</div>` : ''}
                </div>
            </div>
        `;
    }

    renderPenalties() {
        const penaltiesList = document.getElementById('penalties-list');
        const penalties = this.gameData.boxscore?.penalties || [];

        if (penalties.length === 0) {
            penaltiesList.innerHTML = '<div class="no-data">Aucune pénalité dans ce match.</div>';
            return;
        }

        penaltiesList.innerHTML = penalties.map(penalty => this.createPenaltyCard(penalty)).join('');
    }

    createPenaltyCard(penalty) {
        const game = this.gameData;
        const isHome = penalty.teamId === game.boxscore.teams[0].id;
        const teamName = isHome ? game.home_team : game.away_team;

        return `
            <div class="penalty-card ${isHome ? 'home' : 'away'}">
                <div class="penalty-header">
                    <div class="penalty-player">
                        <strong>${penalty.participant.fullName}</strong> (#${penalty.participant.number})
                    </div>
                    <div class="penalty-time">
                        ${penalty.gameTime.period}e période - ${penalty.gameTime.minutes}:${penalty.gameTime.seconds.toString().padStart(2, '0')}
                    </div>
                </div>
                <div class="penalty-details">
                    <div class="penalty-team">${teamName}</div>
                    <div class="penalty-infraction">${penalty.infraction} - ${this.formatPenaltyDuration(penalty.duration)} min</div>
                </div>
            </div>
        `;
    }



    formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-CA', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    getStatusText(status) {
        switch (status) {
            case 'FINAL': return 'Terminé';
            case 'LIVE': return 'En cours';
            case 'SCHEDULED': return 'À venir';
            default: return status;
        }
    }

    formatPenaltyDuration(duration) {
        // Handle both object and number formats
        if (typeof duration === 'object' && duration !== null) {
            if (duration.minutes !== undefined) {
                return duration.minutes;
            }
            if (duration.value !== undefined) {
                return duration.value;
            }
            if (duration.name !== undefined) {
                // Convert penalty type name to minutes
                const name = duration.name.toLowerCase();
                if (name.includes('minor')) return 2;
                if (name.includes('major')) return 5;
                if (name.includes('misconduct')) return 10;
                if (name.includes('match')) return 'Match';
            }
            // If it's an object but we can't extract a meaningful value
            return '?';
        }
        // If it's already a number or string
        return duration || '?';
    }
}

// Tab functionality
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');

    // Add active class to clicked button
    event.target.classList.add('active');
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new GameDetailManager();
});