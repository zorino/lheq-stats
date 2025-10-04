class GamesManager {
    constructor() {
        this.games = [];
        this.teams = [];
        this.dataTable = null;
        this.init();
    }

    async init() {
        try {
            await this.loadData();
            this.populateFilters();
            this.initializeDataTable();
            this.setupEventListeners();
            document.getElementById('loading').style.display = 'none';
        } catch (error) {
            console.error('Error initializing games manager:', error);
            document.getElementById('loading').innerHTML = 'Erreur lors du chargement des données.';
        }
    }

    async loadData() {
        try {
            console.log('Loading games and teams data...');
            const [gamesResponse, teamsResponse] = await Promise.all([
                fetch('data/games.json'),
                fetch('data/teams.json')
            ]);

            if (!gamesResponse.ok || !teamsResponse.ok) {
                throw new Error('Failed to fetch data');
            }

            this.games = await gamesResponse.json();
            this.teams = await teamsResponse.json();

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

    initializeDataTable() {
        console.log('Initializing DataTable with', this.games.length, 'games');

        const gameData = this.games.map(game => {
            const homeDivision = this.getTeamDivision(game.home_team);
            const awayDivision = this.getTeamDivision(game.away_team);
            const division = homeDivision === awayDivision ? homeDivision : `${homeDivision} vs ${awayDivision}`;

            return [
                game.date, // ISO format date for sorting
                game.away_team,
                `${game.away_score !== null ? game.away_score : '-'} - ${game.home_score !== null ? game.home_score : '-'}`,
                game.home_team,
                this.getStatusBadge(game.status),
                division,
                game.id // Hidden column for click handling
            ];
        });

        try {
            this.dataTable = $('#games-datatable').DataTable({
                data: gameData,
                columns: [
                    {
                        title: 'Date',
                        type: 'date',
                        render: function(data) {
                            return new Date(data).toLocaleDateString('fr-CA', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric'
                            });
                        }
                    },
                    { title: 'Équipe Visiteur' },
                    {
                        title: 'Score',
                        orderable: false
                    },
                    { title: 'Équipe Domicile' },
                    {
                        title: 'Statut',
                        orderable: false
                    },
                    { title: 'Division' },
                    {
                        title: 'ID',
                        visible: false,
                        searchable: false
                    }
                ],
                order: [[0, 'desc']], // Sort by date descending
                pageLength: 25,
                responsive: true,
                language: {
                    search: "Rechercher:",
                    lengthMenu: "Afficher _MENU_ matchs par page",
                    info: "Affichage de _START_ à _END_ sur _TOTAL_ matchs",
                    infoEmpty: "Aucun match trouvé",
                    infoFiltered: "(filtré de _MAX_ matchs au total)",
                    paginate: {
                        first: "Premier",
                        last: "Dernier",
                        next: "Suivant",
                        previous: "Précédent"
                    },
                    emptyTable: "Aucun match disponible"
                },
                createdRow: (row, data, dataIndex) => {
                    const gameId = data[6];
                    const game = this.games.find(g => g.id == gameId);
                    const statusClass = game ? game.status.toLowerCase() : '';

                    $(row).addClass(`game-row ${statusClass}`);
                    $(row).css('cursor', 'pointer');
                    $(row).on('click', () => {
                        window.location.href = `game-detail.html?id=${gameId}`;
                    });
                }
            });

            console.log('DataTable initialized successfully');
        } catch (error) {
            console.error('Error initializing DataTable:', error);
            throw error;
        }
    }

    setupEventListeners() {
        // Team filter
        document.getElementById('team-filter').addEventListener('change', (e) => {
            const selectedTeam = e.target.value;
            if (selectedTeam) {
                // Search for games containing this team (either home or away)
                this.dataTable.columns([1, 3]).search(selectedTeam).draw();
            } else {
                this.dataTable.columns([1, 3]).search('').draw();
            }
        });

        // Division filter
        document.getElementById('division-filter').addEventListener('change', (e) => {
            const selectedDivision = e.target.value;
            this.dataTable.column(5).search(selectedDivision).draw();
        });
    }

    getStatusBadge(status) {
        const statusClass = status.toLowerCase();
        const statusText = this.getStatusText(status);

        return `<span class="status-badge ${statusClass}">${statusText}</span>`;
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

// Initialize when DOM and jQuery are ready
$(document).ready(() => {
    console.log('DOM ready, initializing GamesManager...');
    new GamesManager();
});