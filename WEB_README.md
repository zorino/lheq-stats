# LHEQ Statistics Web Application

Une application web statique complète pour afficher les statistiques de la Ligue de Hockey Élite du Québec (LHEQ).

## 🏒 Fonctionnalités

### Statistiques Compilées
- **Équipes**: 23 équipes avec statistiques complètes
- **Joueurs**: 297 joueurs (attaquants, défenseurs, gardiens)
- **Matchs**: 44 matchs analysés
- **Logos**: Téléchargement automatique des logos d'équipe

### Pages Web
1. **Accueil** (`index.html`)
   - Vue d'ensemble des statistiques
   - Classement des équipes (top 10)
   - Meilleurs marqueurs (top 10)
   - Matchs récents

2. **Équipes** (`teams.html`)
   - Tableau complet avec filtres et tri
   - Statistiques détaillées: victoires, défaites, nulles, points
   - Statistiques avancées: PP%, PK%, différentiel
   - Fiches domicile/visiteur

3. **Joueurs** (`players.html`)
   - Basculement entre attaquants/défenseurs et gardiens
   - Filtres par position et équipe
   - Statistiques offensives et punitions
   - Statistiques spéciales (powerplay, infériorité numérique)

## 📊 Statistiques Disponibles

### Équipes
- Matchs joués, victoires, défaites, nulles
- Points (2 pour victoire, 1 pour nulle)
- Buts pour/contre, différentiel
- Minutes de punition (PIM)
- Buts en avantage numérique pour/contre
- Buts en infériorité numérique pour/contre
- Fiches domicile/visiteur

### Joueurs Patineurs
- Matchs joués, buts, assistances, points
- Minutes de punition
- Buts/assistances en avantage numérique
- Buts/assistances en infériorité numérique

### Gardiens
- Matchs joués, victoires, défaites, nulles
- Buts accordés, moyenne de buts accordés

## 🚀 Utilisation

### Démarrer l'Application
```bash
# Naviguer vers le dossier web
cd /home/mderaspe/projects/hockey/lheq-stats/web

# Démarrer un serveur HTTP simple
python -m http.server 8080

# Ou avec Node.js
npx http-server

# Accéder à l'application
# http://localhost:8080
```

### Recompiler les Statistiques
```bash
# Depuis le dossier racine du projet
python stats_compiler.py
```

## 🗂️ Structure des Fichiers

```
web/
├── index.html              # Page d'accueil
├── teams.html              # Page des équipes
├── players.html            # Page des joueurs
├── assets/
│   ├── css/
│   │   └── main.css        # Styles principaux
│   ├── js/
│   │   ├── main.js         # Fonctions utilitaires
│   │   ├── dashboard.js    # Page d'accueil
│   │   ├── teams.js        # Page des équipes
│   │   └── players.js      # Page des joueurs
│   └── logos/              # Logos des équipes (23 fichiers)
└── data/
    ├── teams.json          # Données des équipes
    ├── players.json        # Données des joueurs
    └── games.json          # Résumé des matchs
```

## 🎨 Fonctionnalités de l'Interface

### Navigation
- Menu de navigation responsive
- Design moderne avec dégradés bleus
- Indicateur de page active

### Filtres et Recherche
- **Équipes**: Recherche par nom, tri par diverses statistiques
- **Joueurs**: Recherche par nom, filtres par position et équipe
- Tri dynamique par colonnes

### Design Responsive
- Compatible mobile, tablette et bureau
- Tables adaptatives avec colonnes masquées sur petit écran
- Cartes pour l'affichage mobile

### Éléments Visuels
- Logos d'équipes intégrés
- Cartes de statistiques animées
- Badges de position colorés pour les joueurs
- Indicateurs visuels (positif/négatif) pour les différentiels

## 📱 Compatibilité

- **Desktop**: Toutes les fonctionnalités
- **Tablette**: Interface adaptée, colonnes simplifiées
- **Mobile**: Version optimisée avec navigation tactile

## 🔧 Technologies Utilisées

- **Frontend**: HTML5, CSS3, JavaScript ES6+
- **Backend**: Python pour compilation des données
- **Bibliothèques**:
  - Aucune dépendance externe (vanilla JS)
  - CSS Grid et Flexbox pour la mise en page
  - Fetch API pour le chargement des données

## 📈 Données Sources

Les données proviennent de 44 fichiers JSON de matchs LHEQ contenant:
- Informations de matchs détaillées
- Buts avec assistances et situations spéciales
- Punitions avec durées
- Listes de joueurs complètes
- Logos et informations d'équipes

## 🎯 Prochaines Améliorations

- Pages de détail par équipe
- Graphiques et visualisations
- Export des données (CSV, PDF)
- Comparaisons de joueurs
- Historique des matchs par équipe
- Calculs de tendances et projections

---

**Développé pour la LHEQ - Saison 2025-26**
*Application générée automatiquement à partir des données officielles*