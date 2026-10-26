# Phase 3 — Odométrie et asservissement de cap

**Statut :** Complète
**Période :** Juillet — Août 2026
**Prérequis :** Phase 2 validée (téléopération fonctionnelle)

---

## Objectif de la phase

Doter le robot d'une estimation de sa propre position. À l'issue de cette phase, le robot
doit pouvoir répondre, à tout instant, à la question : où suis-je par rapport à mon point
de départ ?

Cette estimation prend la forme d'une pose dans le plan :

- `x` — déplacement longitudinal, en mètres
- `y` — déplacement latéral, en mètres
- `theta` — cap, en radians

Le repère est celui du point de départ, fixé au sol au moment de l'initialisation.

### Pourquoi cette phase est nécessaire

La Phase 5 exige une navigation autonome d'un point A vers un point B. Un robot incapable
d'estimer sa position ne peut ni savoir qu'il progresse vers sa cible, ni savoir qu'il est
arrivé. L'odométrie est la condition préalable à toute forme de navigation.

### Distinction avec l'asservissement

Une confusion fréquente mérite d'être levée. Faire rouler le robot droit et savoir où il
se trouve sont deux problèmes distincts.

**Rouler droit** relève de l'asservissement : on compare les vitesses des deux chaînes de
propulsion et on corrige celle qui dévie. C'est un problème de commande.

**Savoir où l'on est** relève de l'odométrie : on intègre les rotations de roues pour
estimer une pose. C'est un problème d'estimation.

Un robot peut rouler parfaitement droit et posséder une odométrie fausse. L'inverse est
également possible. Les deux problèmes sont traités séparément, dans cet ordre : le
déséquilibre moteur est caractérisé en premier, parce qu'un biais systématique sur la
propulsion corrompt l'estimation de pose de manière cumulative.

---

## Structure de la phase

| Partie | Objet | Statut |
|---|---|---|
| 1 | Caractérisation du déséquilibre moteur | Complète |
| 2 | Relation impulsions vers distance métrique | Complète |
| 3 | Intégration de pose par odométrie différentielle | Complète |
| 4 | Fusion inertielle et asservissement de cap | Complète |

---

# Partie 1 — Caractérisation du déséquilibre moteur

## Contexte

Lors des essais de téléopération, le robot dévie systématiquement de sa trajectoire
lorsqu'une consigne identique est appliquée aux deux moteurs. La déviation est constante
en direction, ce qui exclut une cause aléatoire et oriente vers un déséquilibre mécanique
reproductible.

Cette déviation doit être caractérisée avant toute implémentation d'odométrie. Un robot
qui ne roule pas droit sous consigne symétrique introduit une erreur systématique dans
l'intégration de pose, et cette erreur est cumulative : elle ne se corrige pas d'elle-même
au fil du parcours.

## Objectif

Déterminer si le déséquilibre entre les deux chaînes de propulsion est :

1. reproductible à consigne fixe (dispersion faible entre essais identiques)
2. constant à travers la plage de fonctionnement (indépendant de la consigne et du sens)

Ces deux conditions déterminent si une correction en boucle ouverte, par coefficient
multiplicatif fixe, est défendable. Si l'une des deux n'est pas satisfaite, un coefficient
unique constitue une fiction : il serait juste en un point de fonctionnement et faux
partout ailleurs.

## Méthode

Le module Hiwonder expose les compteurs d'encodeurs cumulés au registre 60
(`MOTOR_ENCODER_TOTAL_ADDR`), sous forme de quatre entiers 32 bits signés en
little-endian, un par port moteur.

Protocole de mesure :

1. Lecture des compteurs avant l'essai
2. Application d'une consigne identique sur les deux moteurs
3. Attente d'une durée fixe
4. Arrêt, puis lecture des compteurs après l'essai
5. Calcul du ratio des incréments : `ratio = delta_droite / delta_gauche`

Un ratio supérieur à 1 indique que le moteur droit accumule plus d'impulsions que le
gauche pour une même consigne, donc qu'il tourne plus vite.

**Conditions expérimentales.** Les essais sont conduits robot au sol, chenilles en contact
avec la surface réelle. Un essai roues en l'air mesurerait le déséquilibre à vide, ce qui
exclut le patinage des chenilles et la friction du sol, deux composantes du phénomène
réel.

Six points de fonctionnement : consignes 30, 50 et 80, en marche avant et en marche
arrière. Trois essais par point, soit dix-huit essais au total. Durée de trois secondes
par essai.

Script : `scripts/phase3/motor_balance.py`

## Résultats

| Consigne | Ratio D/G | Écart-type | Coefficient droite |
|---|---|---|---|
| +30 | 1,0408 | 0,0028 | 0,9608 |
| -30 | 1,0345 | 0,0048 | 0,9667 |
| +50 | 1,0378 | 0,0086 | 0,9636 |
| -50 | 1,0348 | 0,0099 | 0,9664 |
| +80 | 1,0423 | 0,0050 | 0,9594 |
| -80 | 1,0342 | 0,0087 | 0,9669 |

**Écart entre points de fonctionnement :** 0,0081 (0,8 %)
**Écart-type maximal :** 0,0099 (1,0 %)

## Interprétation

### Le déséquilibre paraît réel et systématique

Le ratio est supérieur à 1 sur les dix-huit essais, sans exception. Le moteur droit tourne
plus vite que le gauche pour une consigne identique, d'environ 4 %. L'invariance du signe
semble éliminer l'hypothèse d'une fluctuation aléatoire.

### Le déséquilibre paraît indépendant du point de fonctionnement

L'écart entre le ratio le plus faible (1,0342 à -80) et le plus élevé (1,0423 à +80) est
de 0,8 %. Cette variation est inférieure à la dispersion observée entre essais identiques
(jusqu'à 1,0 %). La variation entre consignes n'est donc pas distinguable du bruit de
mesure.

### Correction initialement retenue

Les deux conditions posées en objectif paraissent satisfaites. Un coefficient
multiplicatif unique appliqué au moteur droit est donc adopté.

**K_RIGHT = 0,9639**, appliqué avant l'écriture I2C, sur la consigne du moteur droit
uniquement.

### Asymétrie avant/arrière : observée, quantifiée, écartée

Le ratio moyen est systématiquement plus élevé en marche avant (1,0403) qu'en marche
arrière (1,0345). L'écart est de 0,58 %, et le signe est constant sur les trois vitesses
testées, ce qui exclut le hasard.

L'origine est probablement mécanique : tension de chenille asymétrique, jeu directionnel
dans la transmission, ou friction dépendante du sens de rotation.

Cet écart n'est toutefois pas corrigé, et ce choix est délibéré : 0,58 % est inférieur à
la dispersion résiduelle de 1,0 % observée entre essais identiques. Introduire deux
coefficients distincts selon le sens ajouterait de la complexité sans produire
d'amélioration mesurable. La correction serait perdue dans le bruit.

## Observation annexe qui s'avérera décisive

Les compteurs accumulés sur trois secondes évoluent peu avec la consigne : environ 6800
impulsions à la consigne 30, contre 7300 à la consigne 80. Une augmentation de consigne de
167 % ne produit qu'une augmentation de 7 % de la distance parcourue.

Deux hypothèses, non départagées à ce stade : soit les moteurs saturent bien en dessous de
la consigne maximale, soit la consigne du module n'est pas linéaire en vitesse.

Cette observation n'affecte pas la calibration présente, qui repose sur un ratio et non
sur une valeur absolue. Elle est en revanche bloquante pour la Partie 3 : sans relation
établie entre impulsions et distance réelle, l'estimation de pose sera fausse.

Elle se révélera aussi être la clé qui invalide le coefficient K_RIGHT.

---

# Partie 2 — Conversion impulsions vers mètres

## Découverte préalable : la régulation est déjà dans le module

Avant de construire l'odométrie, un test de profil consigne-vitesse a été mené pour
résoudre l'anomalie relevée en Partie 1.

### Mesure

Le robot roule tout droit pendant une durée fixe à des consignes croissantes. On relève la
vitesse en impulsions par seconde.

| Consigne | Impulsions/s | Régime |
|---|---|---|
| 10 | 1004 | linéaire |
| 20 | 1934 | linéaire |
| 30 | 2517 | coude |
| 40 | 2596 | plateau |
| 50 | 2587 | plateau |
| 60 | 2588 | plateau |
| 80 | 2564 | plateau |
| 100 | 2558 | plateau |

### Interprétation

De 10 à 20, la vitesse double quand la consigne double : le régime est linéaire. À partir
de 40, la vitesse plafonne. La consigne 40 et la consigne 100 produisent la même vitesse.

Cela explique l'anomalie de la Partie 1, et invalide sa conclusion. Le déséquilibre de 4 %
avait été mesuré à la consigne 50, c'est-à-dire en pleine saturation. Deux points sur le
plateau ne sont pas comparables : le déséquilibre observé était un artefact du régime
saturé, non un déséquilibre réel des moteurs.

### Vérification en régime non saturé

Le même test de ligne droite, sans aucune correction, à la consigne 20, répété quatre
fois. Écart entre les deux encodeurs :

| Essai | Écart droite - gauche |
|---|---|
| 1 | +0,99 % |
| 2 | +0,45 % |
| 3 | -0,26 % |
| 4 | -0,29 % |

Le signe de l'écart change d'un essai à l'autre. Ce n'est pas un biais systématique, c'est
du bruit oscillant autour de zéro. En régime non saturé, les deux moteurs sont équilibrés.

### Conclusion

La documentation du module confirme qu'il assure une régulation de vitesse en boucle
fermée à partir de ses propres encodeurs. En régime non saturé, cette régulation équilibre
les deux moteurs sans intervention logicielle.

**Conséquence : K_RIGHT est fixé à 1,0.** La correction n'est pas supprimée du code mais
neutralisée, avec un commentaire expliquant la décision. La plage de consigne exploitable
est [10, 30] ; au-delà, augmenter la consigne ne change pas la vitesse.

Cette conclusion illustre une démarche : une correction adoptée en Partie 1 a été remise
en cause à la lumière de nouvelles mesures, et retirée parce qu'elle corrigeait un artefact
plutôt qu'un phénomène réel.

## Mesure de la conversion

### Objectif

Déterminer combien de mètres au sol correspondent à une impulsion d'encodeur. Cette
constante est indispensable à toute estimation de distance.

### Méthode

Le robot roule tout droit à la consigne 20 (régime non saturé) pendant une durée fixe. La
distance réelle parcourue est mesurée au sol au mètre ruban, et comparée au nombre
d'impulsions accumulées.

### Résultats

Quatre essais, distance réelle constante de 90 cm :

| Essai | Impulsions moyennes | mètres/impulsion |
|---|---|---|
| 1 | 10036 | 8,97e-5 |
| 2 | 9965 | 9,03e-5 |
| 3 | 10046 | 8,96e-5 |
| 4 | 9905 | 9,09e-5 |

Moyenne des impulsions : 9988, dispersion de plus ou moins 0,7 %.

**Constante retenue : metres_par_pulse = 9,01e-5 m/impulsion**, portée à 1,05e-4 après
ajout de la rampe de démarrage.

### Écart avec la valeur théorique

La valeur théorique, calculée à partir des spécifications héritées (circonférence
15,71 cm, environ 6653 impulsions par tour), était de 2,36e-5 m/impulsion. La valeur
mesurée au sol est 3,8 fois plus grande.

Un écart de ce facteur ne peut pas s'expliquer par le patinage, qui ferait perdre 10 à
30 % de distance, pas 280 %. L'explication est que les spécifications héritées ne
correspondent pas aux moteurs réels du châssis : la documentation moteur est incomplète,
et la constante héritée provenait vraisemblablement d'un autre modèle.

C'est la justification même de la mesure au sol : elle a détecté une erreur d'un facteur
3,8 dans une constante qui aurait faussé toute l'odométrie si elle avait été utilisée telle
quelle.

## Entraxe effectif

### Pourquoi l'entraxe géométrique ne suffit pas

L'entraxe géométrique du châssis est de 16 cm. Mais sur un véhicule à chenilles, la
rotation ne pivote pas autour de cet entraxe : les chenilles glissent latéralement.
L'entraxe qui gouverne réellement la rotation, dit entraxe effectif, est plus grand et doit
être mesuré.

### Principe

En rotation sur place, si chaque chenille parcourt une distance d en sens opposé, l'angle
de rotation theta est lié à l'entraxe effectif E par :

```
E = 2 * d / theta
```

En faisant tourner le robot d'un angle connu et en mesurant d via les encodeurs, on isole
E.

### Méthode et résultats

Le robot tourne sur place à la consigne 15 pendant 15 secondes, puis s'arrête
automatiquement. Le nombre de tours effectués est compté visuellement. Faire plusieurs
tours plutôt qu'un seul dilue l'erreur de lecture de l'angle.

| Mesure | Tours | Distance par chenille | Entraxe effectif |
|---|---|---|---|
| 1 | 1 | 65,7 cm | 20,9 cm |
| 2 | 3 | 206,3 cm | 21,9 cm |

**Constante retenue : entraxe_effectif = 0,219 m**

Rapport à l'entraxe géométrique : 1,37. Cette valeur est dans la plage attendue pour un
chenillard (typiquement 1,3 à 1,6), ce qui confirme la cohérence de la mesure.

**Observation annexe.** Lors de la rotation, les deux encodeurs affichaient un écart de
5 impulsions sur 23000, soit 0,02 %. En rotation comme en translation, la régulation
interne équilibre les deux chaînes de manière quasi parfaite dans la plage non saturée.

---

# Partie 3 — Intégration de pose

## Principe

À chaque cycle, les incréments d'impulsions sont convertis en distances parcourues par
chaque chenille. La distance du centre et la variation de cap s'en déduisent, puis la pose
est intégrée :

```
d_centre = (d_gauche + d_droite) / 2
d_theta  = (d_droite - d_gauche) / entraxe_effectif

theta += d_theta
x     += d_centre * cos(theta)
y     += d_centre * sin(theta)
```

## Points d'attention

**Fréquence d'intégration.** Une fréquence trop faible dégrade l'approximation : entre deux
lectures, la trajectoire est supposée rectiligne, ce qui est d'autant plus faux que
l'intervalle est long. Fréquence retenue : 20 Hz.

**Robustesse aux lectures corrompues.** L'intégration est cumulative : une lecture
aberrante n'est jamais rattrapée, son erreur persiste indéfiniment dans la pose. Compte
tenu de l'historique de défaillances du bus I2C sur ce montage, un filtre de plausibilité
rejette tout incrément supérieur à 500 impulsions par cycle.

**Débordement des compteurs.** Les compteurs sont des entiers 32 bits signés. Le
débordement est lointain, mais l'intégration porte sur les incréments, jamais sur les
valeurs absolues, afin d'y être insensible.

## Validation en translation

Le robot avance tout droit à la consigne 20 pendant 5 secondes, l'odométrie étant calculée
en direct.

| Grandeur | Valeur estimée | Valeur réelle | Écart |
|---|---|---|---|
| Distance (x) | 0,815 m | 0,80 m | +1,9 % |

**L'estimation de distance est fidèle à moins de 2 %.** La constante metres_par_pulse est
validée.

## Dérive en cap

Le même essai a produit un theta final de 12,9 degrés et un y final de 0,178 m, alors que
le robot était censé aller tout droit.

### Analyse

L'observation directe du robot explique cette dérive. Au démarrage, le robot pivote
brièvement vers la droite, puis la régulation interne rattrape et il roule droit. Ce pivot
initial provient d'une asymétrie de friction statique : au démarrage, un moteur réagit
avant l'autre.

L'intégration étant cumulative, ce pivot de départ reste inscrit dans theta jusqu'à la
fin, même si le robot roule droit ensuite. Le cap n'est jamais corrigé, car les deux roues
enregistrent ce pivot de manière symétrique : les encodeurs ne peuvent pas distinguer un
pivot réel du châssis d'un déplacement voulu.

### Conclusion

L'odométrie par encodeurs seuls est fiable en translation et déficiente en cap. Ce
résultat n'est pas un défaut d'implémentation : c'est la limite structurelle de l'odométrie
par encodeurs sur un chenillard. Les chenilles glissent, et le glissement n'est pas
mesurable par les encodeurs.

Référence « encodeurs seuls », à comparer après l'ajout de la centrale inertielle :

| Grandeur | Encodeurs seuls |
|---|---|
| Erreur de distance | +1,9 % |
| Dérive de cap sur 0,8 m | 12,9 degrés |
| Dérive latérale | 0,178 m |

---

# Partie 4 — Fusion inertielle et asservissement de cap

## Objectif

Corriger la limite mise en évidence en Partie 3. Deux buts distincts :

1. Que l'odométrie sache réellement de combien le robot a tourné (mesure du cap).
2. Que le robot aille physiquement droit (asservissement de cap).

Matériel : centrale inertielle MPU6050 (GY-521), gyroscope trois axes, sur le bus I2C à
l'adresse 0x68.

## Rappel chiffré du problème

Sur un parcours en ligne droite, le robot déviait réellement de 5 cm au sol, mais
l'odométrie encodeurs seuls n'en voyait que 0,8 cm. Les deux chenilles tournent à la même
vitesse, mais le châssis glisse latéralement. Le patinage est invisible aux encodeurs par
nature : ils mesurent la rotation des roues, pas le déplacement réel.

## Validation du gyroscope

Le module répond à l'adresse 0x68, aux côtés du Hiwonder à 0x34.

- Biais du gyroscope au repos : environ 40 LSB, faible et propre
- Valeur stable proche de zéro, robot immobile
- Réponse proportionnelle à la rotation
- Signe cohérent : rotation gauche positive, rotation droite négative

Une calibration du biais robot immobile est faite au démarrage de chaque script, sur 200
échantillons. Sans cette calibration, le gyroscope dérive de plusieurs degrés par minute
même immobile.

## Étape 1 : fusion pour l'odométrie

Script : `scripts/phase3/odom_fusion.py`

### Principe

Le cap est estimé par fusion des deux sources via un filtre complémentaire :

```
d_theta = ALPHA * d_theta_gyro + (1 - ALPHA) * d_theta_encodeurs
```

avec ALPHA = 0,98 : le gyroscope domine, car il ne subit pas le patinage. La distance reste
estimée par les encodeurs, le gyroscope ne mesurant pas les translations.

Un filtre de Kalman n'a pas été retenu : le filtre complémentaire est simple, peu coûteux
en calcul, et suffisant lorsque les rôles des capteurs sont clairement séparés. Une
solution plus complexe devrait démontrer sa nécessité, non la postuler.

### Résultat

Même parcours en ligne droite qu'en Partie 3 :

| | Encodeurs seuls | Fusion IMU |
|---|---|---|
| Déviation réelle au sol | 5 cm | 7 cm |
| Déviation vue par l'odométrie | 0,8 cm | 4,2 cm |

L'odométrie est passée de « aveugle au patinage », où elle voyait six fois trop peu, à
« proche de la réalité ».

## Étape 2 : asservissement de cap

Script : `scripts/phase3/heading_control.py`

### Principe

Le gyroscope ne sert plus seulement à mesurer, mais à corriger. À chaque cycle, l'écart
entre le cap courant et le cap cible est calculé, et la commande des moteurs est ajustée :

```
erreur = cap_cible - theta
correction = KP * erreur
vitesse_gauche = base - correction
vitesse_droite = base + correction
```

Contrairement à un coefficient fixe, la correction est recalculée en continu à partir de la
déviation réelle mesurée. Elle s'adapte donc au patinage, à la charge de la batterie et au
sol, sans réglage préalable.

### Incident : emballement initial

Au premier essai, le robot est parti en vrille, cap à 144 degrés et correction saturée.
Cause : le signe de la correction était inversé. Au lieu de contre-braquer, le code
amplifiait la déviation, créant une rétroaction positive.

Correction : inversion du signe dans la commande moteur et réduction du gain par sécurité.

### Réglage du gain

| KP | Comportement |
|---|---|
| 1,5 | Correction nerveuse, mouvement brusque |
| 0,9 | Un peu vif |
| 0,6 | Doux mais déviation un peu plus grande |
| 0,7 | Retenu : correction douce et déviation réduite |

### Résultat

| Méthode | Déviation réelle sur 2 m |
|---|---|
| Encodeurs seuls, sans rampe | 11,5 cm |
| Encodeurs avec rampe de démarrage | 5 à 7 cm |
| Asservissement gyroscope (KP=0,7) | environ 1 cm |

Sur 3 mètres avec asservissement : déviation de 3 à 4 cm, cap final toujours sous 2 degrés,
sur quatre essais.

Observation notée : selon les essais, le robot part parfois droit d'emblée, parfois il
dévie légèrement puis revient sur sa ligne. Cette variabilité reflète le caractère
aléatoire du patinage ; l'asservissement compense à chaque fois, ce qui explique un
résultat final constant malgré un patinage variable. C'est la démonstration concrète de
l'avantage de la boucle fermée sur un coefficient fixe.

## Étape 3 : rotation de 90 degrés

Script : `scripts/phase3/turn_90.py`

### Principe

Le robot pivote sur place, l'angle étant intégré à partir du gyroscope. Les moteurs sont
coupés avant d'atteindre 90 degrés, pour laisser l'inertie finir la rotation.

### Réglage

Première approche : vitesse de rotation 12, compensation par une grande tolérance. Rejetée
car l'inertie ajoutait environ 22 degrés après la coupure, ce qui est trop et peu fiable.

Solution retenue : réduire la vitesse de rotation pour diminuer l'inertie.

| Réglage | Effet |
|---|---|
| TURN_SPEED = 7 | Rotation lente, faible inertie |
| TURN_CUTOFF = 80 deg | L'inertie finit à 90 deg |

Résultat : le gyroscope coupe à environ 80 degrés, reproductible à moins de 0,5 degré près
entre essais. Un virage lent mais reproductible vaut mieux qu'un virage rapide et
imprévisible.

### Incident : rotation infinie

Au premier essai, le robot tournait sans jamais s'arrêter, l'angle descendant jusqu'à
-1452 degrés avant interruption manuelle.

Cause : le gyroscope retourne des valeurs négatives pour une rotation vers la gauche sur ce
montage. La condition d'arrêt vérifiait `while angle_deg < CUTOFF_DEG`, toujours vraie
puisque l'angle descendait vers -80 au lieu de monter vers +80.

Correction : `while abs(angle_deg) < CUTOFF_DEG`.

**Leçon :** vérifier le signe des valeurs brutes d'un capteur d'orientation avant d'écrire
une condition d'arrêt. La convention dépend du montage physique, pas du code.

## Étape 4 : parcours en carré

Script : `scripts/phase3/square_path.py`

### Principe

Enchaînement automatique : avancer 1 m avec asservissement de cap, tourner 90 degrés,
répété quatre fois. Le robot devrait revenir à son point de départ.

Ce parcours est le test le plus informatif de la phase : il accumule les erreurs de
translation et de rotation, et il est représentatif d'un déplacement réel.

### Incident : robot qui tourne en avançant

Les côtés du carré n'étaient pas droits, le robot déviant continuellement au lieu de tracer
des segments nets.

Cause : la fonction d'avance ne corrigeait le cap qu'au démarrage, pas à chaque cycle, et
l'enchaînement avance/rotation mélangeait les deux mouvements.

Correction : le cap est recalculé et corrigé à chaque itération pendant toute la durée du
déplacement, les fonctions d'avance et de rotation sont complètement séparées, et une pause
de stabilisation de 0,5 s est insérée entre chaque mouvement.

### Résultats, cinq essais

| Essai | Distance par côté | Cap final (cible 270 deg) |
|---|---|---|
| 1 | 100,1 à 101,2 cm | 269,4 deg |
| 2 | 100,1 à 101,2 cm | 265,6 deg |
| 3 | 100,3 à 101,2 cm | 266,3 deg |
| 4 | 100,0 à 101,1 cm | 270,6 deg |
| 5 | 100,0 à 100,7 cm | 270,3 deg |

Cap final moyen : 268,4 degrés, soit environ 2 degrés d'erreur après quatre rotations.

Erreur de bouclage mesurée au sol, trois essais : 12 cm, 16 cm, 12 cm. Moyenne 13,3 cm sur
un périmètre de 4 mètres, soit 3,3 % d'erreur cumulée.

---

# Constantes établies

| Constante | Valeur | Source |
|---|---|---|
| METRES_PAR_PULSE | 1,05e-4 m/impulsion | Mesure au sol, 4 essais, avec rampe |
| ENTRAXE_EFF | 0,219 m | Méthode rotation, 2 mesures indépendantes |
| K_RIGHT | 1,0 (neutralisé) | Régulation interne suffisante hors saturation |
| Plage de consigne utile | 10 à 30 | Profil de saturation mesuré |
| KP asservissement cap | 0,7 | Réglage empirique, 4 gains testés |
| TURN_SPEED | 7 | Compensation de l'inertie |
| TURN_CUTOFF | 80 deg | Coupure moteurs, l'inertie finit à 90 deg |
| ALPHA fusion | 0,98 | Gyroscope dominant dans le filtre complémentaire |
| Fréquence d'odométrie | 20 Hz | Choix de conception |
| MAX_DELTA_PULSES | 500 | Filtre de plausibilité sur les incréments |

---

# Bilan de la phase

Les deux objectifs de départ sont atteints :

- Le robot va physiquement droit (asservissement gyroscope, déviation d'environ 1 %).
- L'odométrie sait où il est (fusion gyroscope-encodeurs).

La démonstration est chiffrée de bout en bout : encodeurs seuls (11,5 cm de dérive sur
2 m), puis rampe de démarrage (5 à 7 cm), puis asservissement (environ 1 cm). Le parcours
en carré valide l'odométrie sur un trajet avec virages et fournit la mesure d'erreur de
bouclage : 13,3 cm sur 4 mètres, soit 3,3 %.

## Limite résiduelle

L'asservissement corrige les écarts de cap, c'est-à-dire la rotation du châssis. Il ne
corrige pas le glissement latéral pur : si les deux chenilles glissent du même côté
simultanément, le châssis ne tourne pas et le gyroscope ne détecte rien.

Les valeurs obtenues sont dans la plage attendue pour un chenillard sans référence externe.
La réponse structurelle est l'ajout d'une référence externe (caméra, LiDAR) en Phase 5, qui
permettra de recaler la pose estimée sur des repères observables plutôt que de l'intégrer
indéfiniment.

## Ce que cette phase a démontré méthodologiquement

**Une mesure hors de la plage de fonctionnement utile n'est pas valide, même si elle est
reproductible.** Le déséquilibre moteur de 4 %, mesuré trois fois avec un faible
écart-type, était un artefact de saturation. Le profil consigne-vitesse aurait dû être
établi avant toute mesure comparative.

**Une constante héritée d'une documentation peut être fausse d'un facteur 3,8.** Seule la
mesure directe sur le système réel fait foi.

**Une correction adoptée doit pouvoir être retirée.** K_RIGHT a été implémenté, puis
neutralisé lorsque de nouvelles mesures ont montré qu'il corrigeait un artefact. Le code
conserve la trace de cette décision.

---

## Suite

Phase 4 — évitement d'obstacles. Intégration des trois capteurs HC-SR04 dans la boucle de
contrôle, en complément de l'odométrie établie ici.
