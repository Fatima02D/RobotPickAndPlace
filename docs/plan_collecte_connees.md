# Plan de Collecte de Données

**Projet :** Robot Mobile Autonome Pick & Place
**Auteure :** Saida Fatimatou Zahraa Diouf

---

## Vue d'ensemble

Ce document structure la collecte de données pour les huit phases du projet, afin de
produire des résultats rigoureux et reproductibles. Chaque protocole précise les
variables, les conditions contrôlées, et la façon dont les mesures seront traitées.

---

## Principes de collecte

### Standards de qualité

- Minimum trois essais par condition
- Protocole écrit avant la mesure, et respecté sans modification en cours de série
- Conditions contrôlées et notées : surface, tension de batterie, température
- Unités SI, avec précision de l'instrument indiquée
- Incertitudes mesurées et rapportées, jamais estimées après coup

### Outils de mesure

| Instrument | Précision |
|---|---|
| Mètre ruban | plus ou moins 0,5 cm |
| Chronomètre numérique | plus ou moins 0,01 s |
| Multimètre | tension et courant |
| Rapporteur | plus ou moins 1 degré |
| Caméra | analyse vidéo image par image si nécessaire |
| Ruban de marquage au sol | repères de distance |

### Règle sur la validité d'une mesure

Une mesure prise hors de la plage de fonctionnement utile du système n'est pas valide,
même si elle est reproductible. La Phase 3 en donne l'exemple : un déséquilibre moteur
de 4 %, mesuré trois fois avec un faible écart-type, s'est révélé être un artefact de
saturation des moteurs. Le profil consigne-vitesse doit être établi avant toute mesure
comparative.

---

## Phase 1 — Contrôle moteur

### Expérience 1.1 : Relation consigne-vitesse

**Question :** quelle est la relation entre la consigne envoyée au module et la vitesse
réelle du robot ?

**Variables :**
- Indépendante : consigne (10, 20, 30, 40, 50, 60, 80, 100)
- Dépendante : vitesse en impulsions par seconde et en cm/s
- Contrôlées : tension de batterie, surface (carrelage plat), charge embarquée

**Protocole :**
1. Charger la batterie complètement et noter la tension
2. Placer le robot sur une ligne de départ marquée
3. Démarrer chronomètre et robot simultanément
4. Arrêter après exactement 3,00 secondes
5. Mesurer la distance parcourue en ligne droite
6. Relever les compteurs d'encodeurs avant et après
7. Répéter trois fois par consigne

**Tableau de données :**

| Consigne | Tension | Essai 1 | Essai 2 | Essai 3 | Moyenne | Écart-type | Vitesse |
|---|---|---|---|---|---|---|---|
| 10 | | | | | | | |
| 20 | | | | | | | |
| 30 | | | | | | | |
| 40 | | | | | | | |
| 50 | | | | | | | |

**Calculs :**
- Vitesse moyenne = distance moyenne / 3,00 s
- Écart-type = racine de la somme des écarts au carré divisée par n
- Coefficient de variation = écart-type / moyenne, exprimé en pourcentage

**Graphique à produire :** consigne en abscisse, vitesse en ordonnée, points avec barres
d'erreur à plus ou moins un écart-type, et identification visuelle du coude de
saturation.

**Résultat obtenu :** régime linéaire de 10 à 30, plateau de saturation à partir de 40.
Plage exploitable : 10 à 30.

---

### Expérience 1.2 : Consommation de courant

**Question :** comment la consommation varie-t-elle avec la consigne ?

**Protocole :**
1. Insérer le multimètre en série avec la batterie
2. Mesurer le courant pour chaque consigne, robot en mouvement
3. Noter consigne, courant en mA, et durée de fonctionnement

| Consigne | Courant (mA) | Puissance (W) | Autonomie estimée (min) |
|---|---|---|---|
| 10 | | | |
| 20 | | | |
| 30 | | | |

**Calculs :**
- Puissance = tension multipliée par courant, divisée par 1000
- Autonomie = capacité de la batterie divisée par le courant, multipliée par 60

---

## Phase 2 — Téléopération

### Expérience 2.1 : Latence commande-réponse

**Question :** quel est le délai entre l'action sur le joystick et le mouvement du robot ?

**Protocole :**
1. Ajouter un horodatage dans le message UART émis par l'ESP32
2. Noter t1 à l'appui sur le joystick
3. Noter t2 à la réception sur le Raspberry Pi
4. Noter t3 au démarrage observé du moteur, par analyse vidéo
5. Répéter vingt fois

| Essai | t1 (ms) | t2 (ms) | t3 (ms) | Latence comm. | Latence totale |
|---|---|---|---|---|---|
| 1 | | | | t2-t1 | t3-t1 |
| ... | | | | | |
| 20 | | | | | |

**Graphique :** histogramme des latences totales.

---

### Expérience 2.2 : Fiabilité de la liaison

**Question :** combien de trames sont perdues entre l'ESP32 et le Raspberry Pi ?

**Protocole :**
1. Numéroter chaque trame émise par l'ESP32
2. Compter les trames reçues et les numéros manquants côté Raspberry Pi
3. Faire tourner pendant cent secondes à 50 Hz, soit 5000 trames attendues

```
Trames émises  : 5000
Trames reçues  : ____
Taux de succès : ____ %
Taux de perte  : ____ %
```

---

## Phase 3 — Odométrie

### Expérience 3.1 : Précision de trajectoire

**Question :** quelle est l'erreur de trajectoire selon la méthode employée ?

**Protocole :**
1. Tracer une ligne droite de 200 cm au sol
2. Placer le robot au départ, aligné avec la ligne
3. Commander une avance en ligne droite
4. Mesurer la déviation latérale à 50, 100, 150 et 200 cm
5. Répéter cinq fois

| Essai | Dév. 50 cm | Dév. 100 cm | Dév. 150 cm | Dév. 200 cm |
|---|---|---|---|---|
| 1 | | | | |
| ... | | | | |
| 5 | | | | |
| Moyenne | | | | |

**Comparaison des trois méthodes :**

| Méthode | Déviation sur 2 m | Amélioration |
|---|---|---|
| Encodeurs seuls, sans rampe | 11,5 cm | référence |
| Encodeurs avec rampe | 5 à 7 cm | 48 % |
| Asservissement gyroscope | environ 1 cm | 91 % |

Calcul de l'amélioration : écart entre avant et après, divisé par la valeur avant,
exprimé en pourcentage.

---

### Expérience 3.2 : Conversion impulsions vers mètres

**Question :** combien de mètres au sol correspondent à une impulsion d'encodeur ?

**Protocole :**
1. Marquer une distance connue au sol, mesurée au mètre ruban
2. Relever les compteurs d'encodeurs avant et après le parcours
3. Rouler en régime non saturé uniquement
4. Répéter quatre fois

| Essai | Distance réelle | Impulsions | m/impulsion |
|---|---|---|---|
| 1 | 90 cm | 10036 | 8,97e-5 |
| 2 | 90 cm | 9965 | 9,03e-5 |
| 3 | 90 cm | 10046 | 8,96e-5 |
| 4 | 90 cm | 9905 | 9,09e-5 |

**Point de vigilance :** comparer systématiquement la valeur mesurée à la valeur
théorique issue des spécifications. Un écart supérieur à 30 % ne s'explique pas par le
patinage et signale une spécification erronée.

---

### Expérience 3.3 : Précision de rotation

**Question :** quelle est la précision et la répétabilité des rotations ?

**Protocole :**
1. Marquer l'orientation initiale au sol
2. Commander des rotations de 45, 90, 180, 270 et 360 degrés
3. Mesurer l'angle réel au rapporteur
4. Répéter dix fois par angle

| Angle cible | Angle moyen mesuré | Écart-type | Erreur |
|---|---|---|---|
| 45 deg | | | |
| 90 deg | | | |
| 180 deg | | | |
| 270 deg | | | |
| 360 deg | | | |

---

### Expérience 3.4 : Erreur de bouclage

**Question :** quelle erreur s'accumule sur un trajet fermé ?

**Protocole :**
1. Marquer le point de départ au sol, avec un repère précis sur la chenille
2. Exécuter un parcours en carré : quatre côtés de 1 m, quatre rotations de 90 degrés
3. Mesurer la distance entre le repère de départ et sa position finale
4. Noter aussi le cap final estimé par l'odométrie
5. Répéter au moins trois fois

| Essai | Erreur de bouclage | Cap final estimé |
|---|---|---|
| 1 | 12 cm | 269,4 deg |
| 2 | 16 cm | 265,6 deg |
| 3 | 12 cm | 266,3 deg |
| Moyenne | 13,3 cm | 267,1 deg |

Erreur cumulée sur le périmètre de 4 m : 3,3 %.

Le parcours en carré est le test le plus informatif de la phase : il accumule les erreurs
de translation et de rotation, et il est représentatif d'un déplacement réel.

---

## Phase 4 — Évitement d'obstacles

### Expérience 4.1 : Précision du capteur ultrason

**Question :** quelle est la précision du HC-SR04 ?

**Protocole :**
1. Placer un obstacle plan à des distances connues : 10, 20, 30, 40, 50 cm
2. Mesurer cinquante fois chaque distance
3. Calculer moyenne et écart-type

| Distance réelle | Distance mesurée | Écart-type | Erreur |
|---|---|---|---|
| 10,0 cm | | | |
| 20,0 cm | | | |
| 30,0 cm | | | |
| 40,0 cm | | | |
| 50,0 cm | | | |

---

### Expérience 4.2 : Distance seuil optimale

**Question :** quelle distance de déclenchement minimise les collisions sans ralentir
inutilement le robot ?

**Protocole :**
1. Placer dix obstacles dans une zone de 2 m par 2 m
2. Tester les seuils 10, 20, 30, 40 et 50 cm
3. Pour chaque seuil, lancer le robot cinq fois
4. Compter les collisions et mesurer le temps de traversée

| Seuil | Collisions sur 5 | Temps moyen | Efficacité |
|---|---|---|---|
| 10 cm | | | |
| 20 cm | | | |
| 30 cm | | | |
| 40 cm | | | |
| 50 cm | | | |

Calcul de l'efficacité : nombre de traversées réussies divisé par le temps moyen.

---

## Phase 5 — Navigation autonome

### Expérience 5.1 : Erreur de positionnement

**Question :** comment l'erreur s'accumule-t-elle avec la distance ?

**Protocole :**
1. Placer des repères tous les 50 cm jusqu'à 300 cm
2. Commander le robot vers chaque point
3. Mesurer la position réelle et la comparer à la position estimée

| Cible | Position estimée | Position réelle | Erreur | Erreur relative |
|---|---|---|---|---|
| 50 cm | | | | |
| 100 cm | | | | |
| 150 cm | | | | |
| 200 cm | | | | |
| 250 cm | | | | |
| 300 cm | | | | |

**Graphique :** distance parcourue en abscisse, erreur cumulée en ordonnée.

---

## Phase 6 — Vision

### Expérience 6.1 : Taux de détection

**Question :** dans quelles conditions la balle est-elle détectée de façon fiable ?

**Variables à faire varier :** distance, éclairage, angle de vue, arrière-plan.

| Condition | Détections sur 20 | Faux positifs | Taux |
|---|---|---|---|
| Distance 30 cm, lumière du jour | | | |
| Distance 60 cm, lumière du jour | | | |
| Distance 30 cm, éclairage artificiel | | | |
| Arrière-plan chargé | | | |

---

### Expérience 6.2 : Précision de localisation par vision

**Question :** avec quelle précision la position de la balle est-elle estimée ?

**Protocole :** placer la balle à des positions connues, comparer avec l'estimation
issue du traitement d'image, vingt répétitions par position.

---

## Phase 7 — Bras robotique

### Expérience 7.1 : Taux de réussite de préhension

**Question :** quel pourcentage d'objets sont saisis avec succès ?

**Protocole :**
1. Placer dix objets identiques (cubes de 3 cm)
2. Tenter la saisie cinq fois par objet, soit cinquante tentatives
3. Classer chaque tentative : réussite complète, saisie partielle, échec

| Objet | Réussite | Partielle | Échec | Taux |
|---|---|---|---|---|
| 1 | | | | |
| ... | | | | |
| 10 | | | | |
| Total | sur 50 | sur 50 | sur 50 | |

---

### Expérience 7.2 : Répétabilité du positionnement

**Question :** quelle est la répétabilité du bras ?

**Protocole :** commander une position cible, mesurer la position réelle vingt fois,
calculer l'écart-type sur chaque axe.

```
Position cible   : (10,0 ; 15,0 ; 5,0) cm
Moyenne mesurée  : (____ ; ____ ; ____) cm
Écart-type       : (____ ; ____ ; ____) cm
Précision globale: plus ou moins ____ cm
```

---

## Phase 8 — Intégration finale

### Expérience 8.1 : Taux de réussite de la mission complète

**Question :** le système pick and place est-il fiable de bout en bout ?

**Mission standard :**
- Point A : (0, 0)
- Objet à : (50, 50)
- Point B : (100, 0)

**Protocole :** lancer trente missions complètes, noter chaque étape.

| Mission | Nav. A vers objet | Saisie | Nav. objet vers B | Dépose | Succès total |
|---|---|---|---|---|---|
| 1 | | | | | |
| ... | | | | | |
| 30 | | | | | |
| Taux | | | | | |

---

### Expérience 8.2 : Robustesse

**Question :** le système fonctionne-t-il dans des conditions variées ?

| Scénario | Réussites sur 10 | Temps moyen | Notes |
|---|---|---|---|
| Position nominale | | | |
| Objet déplacé de 5 cm | | | |
| Obstacle imprévu sur le trajet | | | |
| Surface inclinée à 5 degrés | | | |
| Batterie à 50 % | | | |

---

## Visualisations à produire

Pour chaque phase :

**Graphiques de performance.** Format PNG haute résolution (300 dpi), axes étiquetés avec
unités, légende claire, barres d'erreur systématiques.

**Tableaux de données.** Données brutes conservées séparément des données traitées, pour
que les calculs restent vérifiables.

**Photos du montage expérimental.** Repères de distance visibles, configuration lisible,
éclairage adéquat.

---

## Liste de vérification avant chaque collecte

- [ ] Protocole écrit et relu
- [ ] Instruments de mesure vérifiés
- [ ] Conditions environnementales notées
- [ ] Tension de batterie mesurée et notée
- [ ] Tableau de données préparé
- [ ] Caméra prête si nécessaire
- [ ] Code de test validé sur un essai à blanc

---

## Organisation des fichiers de données

```
data/
|-- phase1_moteurs/
|   |-- profil_consigne_vitesse.csv
|   |-- consommation.csv
|
|-- phase3_odometrie/
|   |-- desequilibre_moteur.csv
|   |-- conversion_impulsions.csv
|   |-- parcours_carre.csv
|
|-- phase4_obstacles/
|   |-- precision_hcsr04.csv
|
|-- graphiques/
```

Sauvegarde : dépôt GitHub, plus une copie locale.
