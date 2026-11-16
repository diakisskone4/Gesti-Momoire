"""Catalogue des modèles de mémoire (source de vérité).

`sync_catalog()` crée ou met à jour les modèles en base ; il est appelé par la
migration initiale et par la commande `python manage.py sync_modeles`.
Chaque élément du plan devient un chapitre (ou une section) dans l'éditeur, avec
un texte de conseil entre crochets à remplacer par l'étudiant.
"""


def item(title, guidance, kind='chapter', sections=None):
    return {'title': title, 'type': kind, 'guidance': guidance, 'sections': sections or []}


def sec(title, guidance):
    return {'title': title, 'guidance': guidance}


def preliminaries(abstract_lang='anglais'):
    return [
        item('Dédicace', "Quelques lignes pour dédier ce travail à vos proches. Une demi-page au maximum.", 'preliminary'),
        item('Remerciements', "Remerciez l'encadreur, le co-encadreur, les membres du jury, l'institution d'accueil et les "
             "personnes qui vous ont aidé. Restez sobre : une page au maximum.", 'preliminary'),
        item('Sigles et abréviations', "Liste alphabétique des sigles utilisés, avec leur signification complète.", 'preliminary'),
        item('Résumé', f"200 à 300 mots : contexte, objectif, méthodologie, principaux résultats, conclusion. "
             f"Ajoutez 4 à 6 mots-clés. Prévoyez la traduction en {abstract_lang} (Abstract, Keywords).", 'preliminary'),
        item('Liste des tableaux et figures', "Générée à la fin de la rédaction : numéro, titre et page de chaque élément.",
             'preliminary'),
    ]


def closing(annex_hint):
    return [
        item('Conclusion générale', "Rappelez la problématique et la démarche, synthétisez les résultats au regard des "
             "hypothèses, reconnaissez les limites du travail et ouvrez des perspectives de recherche.", sections=[
                 sec('Synthèse des résultats', "Reprenez les réponses apportées à chaque question de recherche."),
                 sec('Limites et perspectives', "Limites méthodologiques, pistes pour des travaux futurs."),
             ]),
        item('Bibliographie', "Classez les références par ordre alphabétique d'auteur, dans une norme unique (APA 7e "
             "édition recommandée). N'y mettez que les sources réellement citées.", 'back'),
        item('Annexes', annex_hint, 'back'),
    ]


INTRO_GENERALE = item('Introduction générale', "L'introduction se rédige en dernier. Elle annonce le sujet sans en "
                      "livrer les résultats.", sections=[
    sec('Contexte et justification', "Situez le sujet dans son environnement (national, sectoriel) avec des données "
        "chiffrées et sourcées. Expliquez pourquoi il mérite d'être étudié."),
    sec('Problématique', "Formulez la question centrale de recherche, puis 2 ou 3 questions spécifiques."),
    sec('Objectifs et hypothèses', "Objectif général, objectifs spécifiques, hypothèses vérifiables."),
    sec('Méthodologie et annonce du plan', "Résumez la démarche en quelques lignes et annoncez les parties."),
])

CATALOG = [
    {
        'slug': 'licence-classique',
        'name': 'Mémoire de Licence — Classique',
        'tagline': 'Le format universitaire attendu par la plupart des facultés.',
        'description': "Modèle sobre et complet pour un mémoire de fin de cycle Licence (40 à 60 pages) : page de garde "
                       "institutionnelle centrée, pages liminaires, deux parties (cadre théorique, étude pratique) et "
                       "conseils de rédaction à chaque section.",
        'level': 'LICENCE', 'domain': 'Toutes disciplines', 'cover_style': 'classique', 'accent_color': '#0f766e',
        'order': 1,
        'structure': [
            *preliminaries(),
            INTRO_GENERALE,
            item('Chapitre 1 : Cadre théorique et conceptuel', "Définissez les concepts clés et présentez l'état des "
                 "connaissances sur le sujet.", sections=[
                     sec('Définition des concepts', "Définissez chaque concept à partir d'auteurs de référence, puis "
                         "donnez la définition retenue pour ce travail."),
                     sec('Revue de la littérature', "Présentez les travaux antérieurs par thème, pas auteur par auteur, "
                         "et montrez ce qui reste à étudier."),
                 ]),
            item('Chapitre 2 : Présentation du cadre d\'étude', "Décrivez la structure, la zone ou la population étudiée.",
                 sections=[
                     sec('Historique et missions', "Création, statut, missions, organigramme si pertinent."),
                     sec('Méthodologie de collecte', "Outils (questionnaire, entretien), échantillon, période, limites."),
                 ]),
            item('Chapitre 3 : Présentation et analyse des résultats', "Présentez les résultats avant de les interpréter.",
                 sections=[
                     sec('Présentation des résultats', "Tableaux et graphiques numérotés, titrés et commentés."),
                     sec('Discussion', "Confrontez les résultats aux hypothèses et à la littérature."),
                     sec('Recommandations', "Propositions concrètes, réalistes et adressées à des acteurs précis."),
                 ]),
            *closing("Questionnaire, guide d'entretien, documents internes, autorisations de recherche."),
        ],
    },
    {
        'slug': 'master-sciences-techniques',
        'name': 'Mémoire de Master — Sciences & Techniques',
        'tagline': 'Pour l\'informatique, le génie et les sciences exactes.',
        'description': "Plan orienté projet technique ou expérimental : état de l'art, analyse et conception, mise en "
                       "œuvre, tests et évaluation. Page de garde moderne à bandeau coloré, adaptée aux écoles "
                       "d'ingénieurs et aux masters scientifiques.",
        'level': 'MASTER', 'domain': 'Informatique, génie, sciences exactes', 'cover_style': 'moderne',
        'accent_color': '#1d4ed8', 'order': 2,
        'structure': [
            *preliminaries(),
            INTRO_GENERALE,
            item('Chapitre 1 : État de l\'art', "Panorama critique des solutions, méthodes ou technologies existantes.",
                 sections=[
                     sec('Notions fondamentales', "Les bases théoriques nécessaires à la compréhension du travail."),
                     sec('Travaux connexes', "Comparez les approches existantes dans un tableau (critères, forces, limites)."),
                     sec('Positionnement', "Expliquez ce que votre travail apporte par rapport à l'existant."),
                 ]),
            item('Chapitre 2 : Analyse et conception', "Du besoin à la solution.", sections=[
                sec('Analyse des besoins', "Besoins fonctionnels et non fonctionnels, acteurs, cas d'utilisation."),
                sec('Architecture de la solution', "Diagrammes (UML, architecture logicielle, schéma de montage)."),
                sec('Choix technologiques', "Justifiez chaque choix par des critères objectifs."),
            ]),
            item('Chapitre 3 : Réalisation', "Décrivez la mise en œuvre sans recopier le code.", sections=[
                sec('Environnement de travail', "Matériel, logiciels, versions."),
                sec('Implémentation', "Modules principaux, algorithmes clés (pseudo-code), captures d'écran commentées."),
            ]),
            item('Chapitre 4 : Tests, résultats et évaluation', "Montrez que la solution répond aux objectifs.", sections=[
                sec('Protocole d\'évaluation', "Jeux de données, métriques, conditions de test."),
                sec('Résultats', "Résultats chiffrés, comparaison avec l'existant, analyse des écarts."),
            ]),
            *closing("Extraits de code significatifs, manuel d'utilisation, schémas détaillés, jeux de données."),
        ],
    },
    {
        'slug': 'master-gestion-economie',
        'name': 'Mémoire de Master — Gestion & Économie',
        'tagline': 'Étude de cas d\'entreprise ou analyse économétrique.',
        'description': "Modèle en deux parties pour les sciences de gestion, la finance, le marketing et l'économie : "
                       "cadre théorique, cadre méthodologique, analyse empirique et recommandations managériales. "
                       "Page de garde élégante à double cadre.",
        'level': 'MASTER', 'domain': 'Gestion, finance, économie, marketing', 'cover_style': 'elegant',
        'accent_color': '#7c2d12', 'order': 3,
        'structure': [
            *preliminaries(),
            INTRO_GENERALE,
            item('Première partie : Cadre théorique et méthodologique', "Fondements de l'étude.", 'part'),
            item('Chapitre 1 : Revue de la littérature', "Théories mobilisées et études empiriques antérieures.", sections=[
                sec('Fondements théoriques', "Théories de référence (ex. théorie de l'agence, des parties prenantes...)."),
                sec('Revue empirique', "Résultats d'études similaires dans d'autres pays ou secteurs."),
            ]),
            item('Chapitre 2 : Méthodologie de la recherche', "Démarche permettant de tester les hypothèses.", sections=[
                sec('Modèle conceptuel et variables', "Variables dépendantes, indépendantes, de contrôle ; schéma du modèle."),
                sec('Collecte et traitement des données', "Source, échantillon, période, outils (SPSS, Stata, R, Excel)."),
            ]),
            item('Deuxième partie : Cadre empirique', "Application au terrain d'étude.", 'part'),
            item('Chapitre 3 : Présentation de l\'entreprise ou du secteur', "Contexte de l'étude de cas.", sections=[
                sec('Présentation générale', "Activités, chiffres clés, organisation, environnement concurrentiel."),
                sec('Diagnostic', "Analyse SWOT ou PESTEL appuyée par des données."),
            ]),
            item('Chapitre 4 : Résultats, discussion et recommandations', "Cœur de la contribution.", sections=[
                sec('Résultats', "Statistiques descriptives puis tests ou estimations, tableaux commentés."),
                sec('Discussion', "Validation ou rejet de chaque hypothèse, comparaison à la littérature."),
                sec('Recommandations managériales', "Actions concrètes, coût, responsable, échéance."),
            ]),
            *closing("États financiers, questionnaire, sorties du logiciel statistique, organigramme."),
        ],
    },
    {
        'slug': 'master-sciences-sociales',
        'name': 'Mémoire de Master — Sciences sociales & humaines',
        'tagline': 'Sociologie, géographie, histoire, lettres, éducation.',
        'description': "Démarche qualitative ou mixte : problématisation, terrain, analyse thématique des entretiens. "
                       "Page de garde minimaliste et aérée, très lisible.",
        'level': 'MASTER', 'domain': 'Sociologie, géographie, histoire, lettres, sciences de l\'éducation',
        'cover_style': 'minimaliste', 'accent_color': '#6d28d9', 'order': 4,
        'structure': [
            *preliminaries(),
            INTRO_GENERALE,
            item('Chapitre 1 : Cadre théorique et revue critique', "Ancrage disciplinaire du sujet.", sections=[
                sec('Approches théoriques', "Courants et auteurs mobilisés, justification du cadre retenu."),
                sec('Revue critique de la littérature', "Ce que l'on sait, les débats, les zones d'ombre."),
            ]),
            item('Chapitre 2 : Démarche méthodologique', "Rendre la recherche reproductible et crédible.", sections=[
                sec('Terrain et population', "Présentation du terrain, critères de choix des enquêtés."),
                sec('Techniques de collecte', "Entretiens semi-directifs, observation, focus groups, archives."),
                sec('Considérations éthiques', "Consentement éclairé, anonymat, restitution."),
            ]),
            item('Chapitre 3 : Analyse et interprétation', "Analyse thématique organisée par grands axes.", sections=[
                sec('Axe 1', "Présentez le thème, illustrez-le par des extraits d'entretiens anonymisés, interprétez."),
                sec('Axe 2', "Même démarche : description, verbatim, interprétation."),
                sec('Discussion générale', "Mise en perspective avec le cadre théorique."),
            ]),
            *closing("Guide d'entretien, grille d'observation, retranscriptions, cartes."),
        ],
    },
    {
        'slug': 'master-droit',
        'name': 'Mémoire de Master — Droit & Sciences politiques',
        'tagline': 'Plan juridique en deux parties et deux sous-parties.',
        'description': "Respecte la tradition du plan juridique (I/II, A/B) avec introduction substantielle. Page de "
                       "garde institutionnelle avec en-tête de la République et devise nationale.",
        'level': 'MASTER', 'domain': 'Droit public, droit privé, sciences politiques', 'cover_style': 'institutionnel',
        'accent_color': '#14532d', 'order': 5,
        'structure': [
            *preliminaries(),
            item('Introduction', "En droit, l'introduction est substantielle (5 à 10 pages).", sections=[
                sec('Accroche et définition des termes du sujet', "Définitions juridiques et étymologiques."),
                sec('Intérêts du sujet', "Intérêts théorique et pratique."),
                sec('Problématique et annonce du plan', "Question juridique précise, plan en deux parties annoncé."),
            ]),
            item('Première partie', "Intitulé court et explicatif, qui répond en partie à la problématique.", 'part', sections=[
                sec('A — Première sous-partie', "Phrase introductive, développement, transition."),
                sec('B — Seconde sous-partie', "Appuyez-vous sur les textes, la jurisprudence et la doctrine."),
            ]),
            item('Seconde partie', "Les deux parties doivent être équilibrées.", 'part', sections=[
                sec('A — Première sous-partie', "Analyse critique, droit comparé si pertinent."),
                sec('B — Seconde sous-partie', "Propositions de réforme ou d'interprétation."),
            ]),
            item('Conclusion', "Bilan et ouverture, sans résumé exhaustif.", sections=[]),
            item('Bibliographie', "Distinguez : ouvrages généraux, ouvrages spéciaux, thèses et mémoires, articles, "
                 "textes législatifs et réglementaires, jurisprudence.", 'back'),
            item('Annexes', "Textes de loi, décisions de justice, conventions internationales.", 'back'),
        ],
    },
    {
        'slug': 'these-doctorat',
        'name': 'Thèse de Doctorat',
        'tagline': 'Structure complète pour une thèse de 200 pages et plus.',
        'description': "Page de garde de thèse avec composition du jury, date de soutenance et école doctorale. Plan en "
                       "parties et chapitres, avec articulations (introductions et conclusions partielles) et index.",
        'level': 'DOCTORAT', 'domain': 'Toutes disciplines', 'cover_style': 'these', 'accent_color': '#1e3a8a',
        'order': 6,
        'structure': [
            *preliminaries(),
            item('Introduction générale', "Problématique, revue de littérature synthétique, positionnement, "
                 "contributions attendues, méthodologie générale, annonce du plan.", sections=[
                     sec('Contexte et enjeux scientifiques', "Pourquoi cette question est importante pour la discipline."),
                     sec('Question de recherche et contributions', "Contributions originales attendues."),
                     sec('Architecture de la thèse', "Logique d'enchaînement des parties."),
                 ]),
            item('Première partie : Fondements théoriques', "Introduction de partie : ce que la partie démontre.", 'part'),
            item('Chapitre 1 : Revue systématique de la littérature', "Méthode de recherche documentaire, synthèse, "
                 "lacunes identifiées.", sections=[
                     sec('Méthode de revue', "Bases interrogées, mots-clés, critères d'inclusion."),
                     sec('Synthèse critique', "Organisation thématique et chronologique."),
                 ]),
            item('Chapitre 2 : Cadre conceptuel et hypothèses', "Modèle de recherche et hypothèses détaillées.", sections=[]),
            item('Deuxième partie : Études empiriques', "Une étude par chapitre, chacune avec sa méthode et ses résultats.", 'part'),
            item('Chapitre 3 : Étude 1', "Objectif, méthode, résultats, discussion partielle.", sections=[]),
            item('Chapitre 4 : Étude 2', "Objectif, méthode, résultats, discussion partielle.", sections=[]),
            item('Chapitre 5 : Discussion générale', "Intégration des résultats, apports théoriques, managériaux ou "
                 "sociétaux, limites.", sections=[]),
            *closing("Instruments de mesure, protocoles, autorisations éthiques, publications issues de la thèse."),
            item('Index', "Index des auteurs et des notions, généré automatiquement en fin de rédaction.", 'back'),
        ],
    },
    {
        'slug': 'rapport-stage-licence-pro',
        'name': 'Rapport de stage — Licence professionnelle',
        'tagline': 'Le rapport de fin de stage, structuré comme l\'attendent les jurys.',
        'description': "Pour les licences professionnelles, BTS et DUT : présentation de la structure d'accueil, "
                       "déroulement du stage, analyse d'une problématique observée et bilan personnel. Page de garde "
                       "classique avec mention de l'entreprise et du maître de stage.",
        'level': 'LICENCE', 'domain': 'Toutes filières professionnelles', 'cover_style': 'classique',
        'accent_color': '#0e7490', 'order': 7,
        'structure': [
            *preliminaries(),
            item('Introduction', "Présentez le cadre du stage (période, structure, service), son objectif et le plan "
                 "du rapport. Une à deux pages.", sections=[
                     sec('Contexte et objectifs du stage', "Pourquoi ce stage, ce que vous deviez y apprendre ou produire."),
                     sec('Annonce du plan', "Les trois parties du rapport en une phrase chacune."),
                 ]),
            item('Chapitre 1 : Présentation de la structure d\'accueil', "Décrivez l'entreprise de façon factuelle et "
                 "sourcée (documents internes, site officiel).", sections=[
                     sec('Historique, statut et activités', "Date de création, forme juridique, secteur, chiffres clés."),
                     sec('Organisation', "Organigramme commenté et place du service d'accueil."),
                     sec('Service d\'accueil', "Missions du service, effectif, outils utilisés."),
                 ]),
            item('Chapitre 2 : Déroulement du stage', "Montrez concrètement ce que vous avez fait.", sections=[
                sec('Tâches réalisées', "Classez-les par nature ou par période ; illustrez par des exemples précis."),
                sec('Compétences mobilisées et acquises', "Reliez chaque tâche aux enseignements de la formation."),
                sec('Difficultés rencontrées', "Difficultés réelles et solutions apportées."),
            ]),
            item('Chapitre 3 : Analyse d\'une problématique observée', "Approfondissez un dysfonctionnement ou une "
                 "opportunité constaté pendant le stage.", sections=[
                     sec('Constat et diagnostic', "Décrivez la situation avec des données (observations, chiffres)."),
                     sec('Propositions d\'amélioration', "Solutions réalistes, coût, délai, acteurs concernés."),
                 ]),
            item('Conclusion et bilan personnel', "Synthèse du stage, apports professionnels et personnels, "
                 "projet professionnel.", sections=[]),
            item('Bibliographie et webographie', "Documents de l'entreprise, ouvrages et sites consultés, dans une "
                 "norme unique.", 'back'),
            item('Annexes', "Attestation de stage, organigramme, documents produits, fiches de procédure.", 'back'),
        ],
    },
    {
        'slug': 'licence-informatique-projet',
        'name': 'Mémoire de Licence — Informatique & Réseaux',
        'tagline': 'Conception et réalisation d\'une application ou d\'un réseau.',
        'description': "Projet de fin de cycle Licence en informatique, génie logiciel ou réseaux et télécoms : "
                       "étude de l'existant, cahier des charges, conception (UML / Merise), réalisation et tests. "
                       "Page de garde moderne à bandeau.",
        'level': 'LICENCE', 'domain': 'Informatique, génie logiciel, réseaux et télécoms', 'cover_style': 'moderne',
        'accent_color': '#0369a1', 'order': 8,
        'structure': [
            *preliminaries(),
            INTRO_GENERALE,
            item('Chapitre 1 : Étude de l\'existant', "Comprendre le fonctionnement actuel avant de proposer une solution.",
                 sections=[
                     sec('Présentation de la structure', "Activités, organisation, système d'information actuel."),
                     sec('Critique de l\'existant', "Points forts, insuffisances, besoins non couverts."),
                     sec('Solutions envisageables', "Comparez 2 ou 3 options et justifiez celle retenue."),
                 ]),
            item('Chapitre 2 : Cahier des charges et conception', "Spécifier puis modéliser la solution.", sections=[
                sec('Besoins fonctionnels et non fonctionnels', "Liste des fonctionnalités, acteurs, contraintes."),
                sec('Modélisation', "Diagrammes de cas d'utilisation, de classes et de séquence (UML) ou MCD/MLD (Merise)."),
                sec('Architecture technique', "Architecture logicielle ou topologie réseau, choix des technologies."),
            ]),
            item('Chapitre 3 : Réalisation et tests', "Présenter la solution obtenue.", sections=[
                sec('Environnement de développement', "Langages, frameworks, SGBD, équipements, versions."),
                sec('Présentation de la solution', "Captures d'écran commentées des principales fonctionnalités."),
                sec('Tests et sécurité', "Scénarios de test, résultats, mesures de sécurité mises en place."),
            ]),
            *closing("Manuel d'utilisation, scripts de configuration, dictionnaire de données, extraits de code."),
        ],
    },
    {
        'slug': 'licence-economie-gestion',
        'name': 'Mémoire de Licence — Économie, Gestion & Comptabilité',
        'tagline': 'Étude de cas simple et rigoureuse sur une entreprise ou un secteur.',
        'description': "Pour les licences en sciences économiques, gestion, comptabilité-finance, banque et "
                       "marketing : cadre théorique, présentation de la structure, analyse des données et "
                       "recommandations. Page de garde élégante à double cadre.",
        'level': 'LICENCE', 'domain': 'Économie, gestion, comptabilité, banque, marketing', 'cover_style': 'elegant',
        'accent_color': '#a16207', 'order': 9,
        'structure': [
            *preliminaries(),
            INTRO_GENERALE,
            item('Chapitre 1 : Cadre théorique', "Concepts et travaux de référence sur le sujet.", sections=[
                sec('Définition des concepts clés', "Ex. : performance, contrôle interne, rentabilité, fidélisation."),
                sec('Revue de la littérature', "Travaux théoriques et études empiriques proches de votre sujet."),
            ]),
            item('Chapitre 2 : Présentation de la structure et méthodologie', "Terrain et démarche.", sections=[
                sec('Présentation de la structure', "Activités, organisation, chiffres clés sur 3 à 5 ans."),
                sec('Méthodologie', "Documents analysés (états financiers, rapports), questionnaire, outils de calcul."),
            ]),
            item('Chapitre 3 : Analyse, résultats et recommandations', "Interprétez les données, puis proposez.",
                 sections=[
                     sec('Analyse des données', "Ratios, tableaux d'évolution, graphiques commentés."),
                     sec('Interprétation des résultats', "Vérification des hypothèses."),
                     sec('Recommandations', "Mesures concrètes et réalistes pour la structure étudiée."),
                 ]),
            *closing("États financiers, tableaux de calcul, questionnaire, organigramme."),
        ],
    },
    {
        'slug': 'master-sante-publique',
        'name': 'Mémoire de Master — Santé publique & Sciences de la santé',
        'tagline': 'Structure IMRaD pour les études épidémiologiques et cliniques.',
        'description': "Format scientifique IMRaD (Introduction, Méthodes, Résultats, Discussion) adapté à la santé "
                       "publique, aux sciences infirmières, à la nutrition et à la biologie médicale. Inclut les "
                       "considérations éthiques. Page de garde moderne à bandeau.",
        'level': 'MASTER', 'domain': 'Santé publique, épidémiologie, sciences infirmières, nutrition',
        'cover_style': 'moderne', 'accent_color': '#be123c', 'order': 10,
        'structure': [
            *preliminaries(),
            item('Introduction', "Problème de santé étudié, ampleur (données sourcées), justification, question de "
                 "recherche.", sections=[
                     sec('Contexte et justification', "Données épidémiologiques mondiales, nationales et locales."),
                     sec('Question de recherche et hypothèses', "Formulation précise et vérifiable."),
                     sec('Objectifs', "Objectif général et objectifs spécifiques (mesurables)."),
                 ]),
            item('Chapitre 1 : Revue de la littérature', "État des connaissances sur le problème de santé.", sections=[
                sec('Généralités', "Définitions, physiopathologie ou déterminants, prise en charge."),
                sec('Études antérieures', "Résultats d'études similaires (prévalence, facteurs associés)."),
            ]),
            item('Chapitre 2 : Méthodologie', "Section décisive : elle doit permettre de reproduire l'étude.", sections=[
                sec('Type, cadre et période d\'étude', "Étude transversale, cas-témoins, cohorte... ; lieu ; dates."),
                sec('Population et échantillonnage', "Critères d'inclusion et d'exclusion, calcul de la taille d'échantillon."),
                sec('Variables et collecte des données', "Variables étudiées, outil de collecte, pré-test."),
                sec('Analyse statistique', "Logiciel (Epi Info, SPSS, Stata, R), tests utilisés, seuil de significativité."),
                sec('Considérations éthiques', "Autorisation du comité d'éthique, consentement éclairé, confidentialité."),
            ]),
            item('Chapitre 3 : Résultats', "Présentez les résultats sans les interpréter.", sections=[
                sec('Caractéristiques de la population', "Tableau sociodémographique."),
                sec('Résultats principaux', "Fréquences, associations (OR, IC 95 %, p), tableaux et figures numérotés."),
            ]),
            item('Chapitre 4 : Discussion', "Interprétez et comparez.", sections=[
                sec('Limites de l\'étude', "Biais possibles et leur influence sur les résultats."),
                sec('Discussion des résultats', "Comparaison avec la littérature, explications possibles."),
            ]),
            *closing("Questionnaire, fiche de consentement, autorisation éthique, tableaux complémentaires."),
        ],
    },
    {
        'slug': 'master-agronomie-environnement',
        'name': 'Mémoire de Master — Agronomie & Environnement',
        'tagline': 'Essais au champ, enquêtes agricoles et études environnementales.',
        'description': "Pour l'agronomie, l'élevage, les eaux et forêts, la géologie et les sciences de "
                       "l'environnement : présentation de la zone d'étude, matériel et méthodes, résultats et "
                       "discussion. Page de garde classique universitaire.",
        'level': 'MASTER', 'domain': 'Agronomie, élevage, eaux et forêts, environnement', 'cover_style': 'classique',
        'accent_color': '#15803d', 'order': 11,
        'structure': [
            *preliminaries(),
            INTRO_GENERALE,
            item('Chapitre 1 : Synthèse bibliographique', "Connaissances sur l'espèce, la culture ou le milieu étudié.",
                 sections=[
                     sec('Généralités', "Botanique, écologie, exigences agro-climatiques ou caractéristiques du milieu."),
                     sec('Travaux antérieurs', "Résultats d'essais ou d'études comparables."),
                 ]),
            item('Chapitre 2 : Présentation de la zone d\'étude', "Cadre physique et humain.", sections=[
                sec('Situation géographique', "Carte de localisation, coordonnées."),
                sec('Climat, sols et végétation', "Données pluviométriques et de température sur plusieurs années."),
                sec('Activités socio-économiques', "Systèmes de production, population."),
            ]),
            item('Chapitre 3 : Matériel et méthodes', "Doit permettre de reproduire l'expérimentation.", sections=[
                sec('Matériel', "Matériel végétal ou animal, intrants, équipements de mesure."),
                sec('Dispositif expérimental ou d\'enquête', "Plan (blocs de Fisher, randomisation), traitements, échantillon."),
                sec('Paramètres mesurés et analyse des données', "Variables, protocole de mesure, ANOVA ou autres tests."),
            ]),
            item('Chapitre 4 : Résultats et discussion', "Résultats chiffrés puis interprétation.", sections=[
                sec('Résultats', "Tableaux et graphiques avec tests de comparaison des moyennes."),
                sec('Discussion', "Comparaison avec la littérature, explication des écarts."),
                sec('Recommandations', "Pour les producteurs, les services techniques et la recherche."),
            ]),
            *closing("Fiches d'enquête, données brutes, photos de l'essai, cartes."),
        ],
    },
    {
        'slug': 'master-genie-civil',
        'name': 'Mémoire de Master — Génie civil & BTP',
        'tagline': 'Étude technique, dimensionnement et estimation d\'un ouvrage.',
        'description': "Pour le génie civil, les travaux publics, l'hydraulique et l'architecture : présentation du "
                       "projet, études préliminaires, dimensionnement, impact environnemental et devis estimatif. "
                       "Page de garde moderne à bandeau.",
        'level': 'MASTER', 'domain': 'Génie civil, BTP, hydraulique, architecture', 'cover_style': 'moderne',
        'accent_color': '#b45309', 'order': 12,
        'structure': [
            *preliminaries(),
            INTRO_GENERALE,
            item('Chapitre 1 : Présentation du projet', "Cadre et données de base.", sections=[
                sec('Contexte et localisation', "Maître d'ouvrage, site, objectifs de l'ouvrage."),
                sec('Données de base', "Plans, données topographiques, géotechniques et hydrologiques."),
            ]),
            item('Chapitre 2 : Études préliminaires et conception', "Choisir la variante.", sections=[
                sec('Analyse des variantes', "Comparaison technique et économique des solutions possibles."),
                sec('Hypothèses de calcul', "Normes (Eurocodes, BAEL...), charges, matériaux."),
            ]),
            item('Chapitre 3 : Dimensionnement', "Cœur technique du mémoire.", sections=[
                sec('Descente des charges', "Méthode et résultats synthétisés dans des tableaux."),
                sec('Calcul des éléments', "Dalles, poutres, poteaux, fondations ou ouvrages hydrauliques."),
                sec('Vérifications', "États limites, logiciel utilisé (Robot, CYPE, etc.), comparaison avec le calcul manuel."),
            ]),
            item('Chapitre 4 : Impact environnemental et estimation du coût', "Faisabilité du projet.", sections=[
                sec('Notice d\'impact environnemental et social', "Impacts identifiés et mesures d'atténuation."),
                sec('Devis quantitatif et estimatif', "Métrés, prix unitaires, coût total, planning des travaux."),
            ]),
            *closing("Plans, notes de calcul détaillées, rapports géotechniques, devis complet."),
        ],
    },
    {
        'slug': 'master-communication-journalisme',
        'name': 'Mémoire de Master — Communication & Journalisme',
        'tagline': 'Analyse de discours, de médias ou de stratégies de communication.',
        'description': "Pour les sciences de l'information et de la communication, le journalisme, la communication "
                       "d'entreprise et le marketing digital : corpus, grille d'analyse, résultats et plan de "
                       "communication. Page de garde minimaliste.",
        'level': 'MASTER', 'domain': 'Communication, journalisme, médias, marketing digital',
        'cover_style': 'minimaliste', 'accent_color': '#c2410c', 'order': 13,
        'structure': [
            *preliminaries(),
            INTRO_GENERALE,
            item('Chapitre 1 : Cadre théorique', "Théories de la communication mobilisées.", sections=[
                sec('Concepts clés', "Ex. : agenda-setting, cadrage médiatique, réception, image de marque."),
                sec('Revue de la littérature', "Études antérieures sur le média, l'organisation ou le public étudié."),
            ]),
            item('Chapitre 2 : Méthodologie', "Construire et justifier le corpus.", sections=[
                sec('Constitution du corpus', "Médias, période, critères de sélection des articles, émissions ou publications."),
                sec('Grille d\'analyse', "Analyse de contenu, sémiotique ou de discours : catégories retenues."),
                sec('Entretiens et enquête complémentaires', "Professionnels interrogés, questionnaire auprès du public."),
            ]),
            item('Chapitre 3 : Résultats et analyse', "Présentez puis interprétez.", sections=[
                sec('Analyse quantitative', "Fréquences, thèmes dominants, tonalité (tableaux, graphiques)."),
                sec('Analyse qualitative', "Extraits commentés du corpus et des entretiens."),
            ]),
            item('Chapitre 4 : Discussion et recommandations', "Portée des résultats.", sections=[
                sec('Discussion', "Confrontation avec le cadre théorique."),
                sec('Plan de communication proposé', "Cibles, messages, canaux, calendrier, budget, indicateurs."),
            ]),
            *closing("Grille d'analyse, extraits du corpus, guide d'entretien, questionnaire."),
        ],
    },
    {
        'slug': 'these-exercice-medecine',
        'name': 'Thèse d\'exercice — Médecine, Pharmacie & Odontologie',
        'tagline': 'La thèse de fin d\'études médicales, au format des facultés de santé.',
        'description': "Thèse d'exercice pour l'obtention du diplôme d'État de docteur en médecine, pharmacie ou "
                       "chirurgie dentaire : généralités, méthodologie, résultats, commentaires et discussion, "
                       "serment. Page de garde de thèse avec composition du jury.",
        'level': 'DOCTORAT', 'domain': 'Médecine, pharmacie, odontologie', 'cover_style': 'these',
        'accent_color': '#9f1239', 'order': 14,
        'structure': [
            *preliminaries(),
            item('Introduction', "Intérêt du sujet, ampleur du problème, justification de l'étude.", sections=[]),
            item('Objectifs', "Objectif général et objectifs spécifiques, formulés avec des verbes mesurables.",
                 sections=[]),
            item('Chapitre 1 : Généralités', "Revue des connaissances sur la pathologie ou le médicament étudié.",
                 sections=[
                     sec('Définition et épidémiologie', "Données mondiales, africaines et nationales sourcées."),
                     sec('Physiopathologie et diagnostic', "Signes cliniques, examens complémentaires."),
                     sec('Traitement et prévention', "Protocoles en vigueur, recommandations."),
                 ]),
            item('Chapitre 2 : Méthodologie', "Cadre, type et période d'étude, population, échantillonnage, "
                 "variables, collecte, analyse et éthique.", sections=[
                     sec('Cadre et type d\'étude', "Service, hôpital, période ; étude rétrospective ou prospective."),
                     sec('Population et critères', "Critères d'inclusion et de non-inclusion, taille de l'échantillon."),
                     sec('Collecte, analyse et éthique', "Fiche d'enquête, logiciel, tests, avis du comité d'éthique."),
                 ]),
            item('Chapitre 3 : Résultats', "Données sociodémographiques, cliniques, paracliniques, thérapeutiques et "
                 "évolutives, en tableaux et figures numérotés.", sections=[]),
            item('Chapitre 4 : Commentaires et discussion', "Limites de l'étude puis discussion de chaque résultat "
                 "avec la littérature.", sections=[]),
            item('Conclusion et recommandations', "Conclusion brève, recommandations adressées aux autorités, au "
                 "personnel de santé et à la population.", sections=[]),
            item('Références bibliographiques', "Norme de Vancouver : références numérotées dans l'ordre d'apparition.",
                 'back'),
            item('Annexes', "Fiche d'enquête, fiche signalétique, résumé en anglais.", 'back'),
            item('Serment', "Serment d'Hippocrate ou serment de Galien selon la faculté.", 'back'),
        ],
    },
]


def sync_catalog(template_model, price):
    """Crée ou met à jour les modèles du catalogue.
    Le prix n'est fixé qu'à la création : l'administrateur peut ensuite le modifier."""
    created = 0
    for data in CATALOG:
        defaults = {k: v for k, v in data.items() if k != 'slug'}
        _, was_created = template_model.objects.update_or_create(
            slug=data['slug'], defaults=defaults, create_defaults={**defaults, 'price': price},
        )
        created += was_created
    return created
