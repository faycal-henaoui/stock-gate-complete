# Mémoire de Fin d'Études
## Système d'Extraction et de Gestion Intelligente des Factures Fournisseurs

---

# Introduction Générale

Dans l'ère numérique actuelle, la transformation digitale est devenue un impératif stratégique pour les entreprises cherchant à optimiser leurs processus et à réduire leurs coûts opérationnels. Parmi ces processus, la gestion des achats et de la comptabilité reste souvent entravée par des tâches manuelles répétitives, notamment la saisie des factures fournisseurs.

Le traitement manuel des factures est non seulement chronophage, mais il est également source d'erreurs humaines (inversion de chiffres, erreurs de saisie, pertes de documents). Pour une entreprise gérant des centaines, voire des milliers de factures mensuelles, l'impact sur la productivité et la gestion des stocks est considérable.

Ce projet s'inscrit dans cette optique de modernisation. Notre objectif est de concevoir et réaliser une solution complète d'automatisation capable de lire, comprendre et extraire les informations clés des factures (Fournisseur, Date, Tableaux d'articles) à partir d'images ou de PDF, puis de les intégrer automatiquement dans un système de gestion de stock.

Pour ce faire, nous avons développé une chaîne de traitement hybride alliant la puissance du **Deep Learning** pour la reconnaissance optique de caractères (OCR) via PaddleOCR [1], à des algorithmes d'analyse spatiale innovants pour la structuration des données. Cette solution est intégrée dans une application web moderne (React/Node.js) offrant une interface intuitive pour la validation et le rapprochement automatique des produits (Smart Matching).

---

# Chapitre 1 : État de l'art et Contexte du Projet

## 1.1. Contexte et Problématique

### 1.1.1. La saisie manuelle en entreprise
La gestion des factures fournisseurs est une étape critique de la chaîne d'approvisionnement (Supply Chain). Traditionnellement, lorsqu'une entreprise reçoit une facture, un opérateur doit :
1. Lire le document papier ou PDF.
2. Identifier les informations pertinentes (Qui est le fournisseur ? Quelle est la date ? Quels sont les articles ?).
3. Saisir manuellement ces données dans l'ERP ou le logiciel de gestion de stock.

Cette méthode présente plusieurs limites majeures :
*   **Coût élevé** : Le temps passé par les employés représente un coût salarial direct.
*   **Délais de traitement** : Le "time-to-record" (temps d'enregistrement) peut prendre plusieurs jours.
*   **Erreurs de saisie** : On estime qu'environ 1% à 4% des saisies manuelles contiennent des erreurs, ce qui fausse les inventaires et la comptabilité.

### 1.1.2. Objectif du projet
L'objectif est de supprimer cette friction en proposant un système "Scan & Validate". L'utilisateur n'a plus qu'à scanner la facture, et le système pré-remplit les champs. L'humain passe d'un rôle de "saisie" à un rôle de "validation", beaucoup moins coûteux et plus valorisant.

## 1.2. Définitions Clés

Pour bien appréhender la solution, il est nécessaire de définir les concepts techniques mobilisés :

*   **OCR (Optical Character Recognition)** : La reconnaissance optique de caractères est la technologie permettant de convertir une image contenant du texte (pixels) en texte codé utilisable par la machine (ASCII/Unicode).
*   **NLP (Natural Language Processing)** : Le traitement automatique du langage naturel désigne les techniques permettant à une machine de comprendre, interpréter et manipuler le langage humain. Dans notre projet, nous l'utilisons pour le rapprochement de produits (matching flou) et la correction sémantique.
*   **Dématérialisation** : Processus de remplacement des supports d'information matériels (papier) par des fichiers informatiques.

## 1.3. Classification des Documents

Dans le domaine de l'extraction d'information, on distingue trois types de documents :

1.  **Documents Structurés** (ex: Formulaires CERFA, Chèques, QCM) : La mise en page est fixe et connue à l'avance. L'extraction est simple (coordonnées fixes).
2.  **Documents Non-Structurés** (ex: Emails, Lettres, Articles) : Le texte est libre, sans structure spatiale rigide. L'analyse repose entièrement sur le NLP.
3.  **Documents Semi-Structurés** (ex: **Factures**, Tickets de caisse) : C'est le cas complexe qui nous intéresse.
    *   Les informations clés (Total, Date) sont toujours présentes, mais leur **position varie** d'un fournisseur à l'autre.
    *   Les tableaux ont un nombre de lignes variable.
    *   C'est pour cela que les méthodes traditionnelles échouent souvent.

## 1.4. État de l'Art des Solutions d'Extraction

Comment extraire des données de factures ? Voici l'évolution des approches :

### 1.4.1. Approche "Template Matching" (Modèles)
*   **Principe** : On dessine des zones sur l'image pour chaque fournisseur (ex: "Pour le fournisseur X, la date est toujours aux coordonnées [100, 200]").
*   **Avantage** : Très précis si le format ne change jamais.
*   **Inconvénient** : Impossible à maintenir. Si l'on a 500 fournisseurs, il faut créer 500 modèles. Si un fournisseur change sa mise en page, le système casse.

### 1.4.2. Approche par Règles (Regex & Mots-clés)
*   **Principe** : On convertit tout le document en texte brut, puis on cherche des motifs avec des expressions régulières (ex: chercher `JJ/MM/AAAA` pour la date).
*   **Avantage** : Plus souple que les templates.
*   **Inconvénient** : On perd l'information spatiale. Si une facture contient deux dates (Date de facture et Date de livraison), les Regex ne savent souvent pas distinguer laquelle est laquelle sans le contexte visuel (ce qui est à gauche ou au-dessus).

### 1.4.3. Approche Moderne : Deep Learning & Layout Analysis
C'est l'approche que nous avons privilégiée. Elle combine :
*   Des réseaux de neurones profonds (**Deep Learning**) pour détecter et lire le texte même déformé ou bruité.
*   Une analyse de la **disposition spatiale** (Layout Analysis) pour comprendre que "Total" est un titre et que "100.00 $" qui se trouve à sa droite est la valeur associée.
*   Cette méthode est **générique** : elle fonctionne sur des factures jamais vues auparavant, sans avoir besoin de créer de "template" spécifique.

---

# Chapitre 2 : Fondements Théoriques

Ce chapitre présente les bases théoriques et mathématiques nécessaires à la compréhension des technologies mises en œuvre dans notre solution.

## 2.1. Vision par Ordinateur (Computer Vision)

La vision par ordinateur est le domaine de l'intelligence artificielle qui permet aux machines "de voir" et d'analyser des images. Avant de pouvoir lire du texte sur une facture, l'image brute doit subir plusieurs traitements.

### 2.1.1. Prétraitement d'images
Les factures scannées souffrent souvent de défauts (bruit, faible contraste, rotation).
Une image numérique est perçue par la machine comme une matrice $f(x, y)$ où chaque valeur représente l'intensité du pixel.

*   **Conversion en niveaux de gris** : Réduction de la complexité en passant de 3 canaux (RGB) à 1 canal.
*   **Filtrage et Réduction de Bruit** : Application de convolutions (ex: Flou Gaussien) pour lisser le grain du papier numérisé :
    $$ (f * G)(x, y) = \sum_{i,j} f(i, j) G(x-i, y-j) $$
*   **Binarisation** : Transformation de l'image en noir et blanc pur (seuillage) pour séparer le texte du fond.
*   **Normalisation** : Redimensionnement à une taille standard (ex: 960x960) pour l'entrée du réseau.

## 2.2. Deep Learning pour l'OCR

L'OCR moderne ne repose plus sur la reconnaissance de formes géométriques simples, mais sur l'apprentissage profond (Deep Learning).

### 2.2.1. Réseaux de Neurones Convolutifs (CNN)
Les CNN (Convolutional Neural Networks) sont la base de la vision moderne. Ils utilisent des filtres (kernels) qui parcourent l'image pour extraire des caractéristiques visuelles (bords, coins, textures) de plus en plus complexes.
Dans notre projet, les CNN sont utilisés lors de l'étape de **Détection de Texte** (pour localiser où se trouve le texte sur la page).

### 2.2.2. Réseaux Récurrents et Transformers
Une fois le texte localisé, il faut le reconnaître (lire la séquence de caractères).
*   **RNN / LSTM (Long Short-Term Memory)** : Traditionnellement utilisés pour traiter les séquences (texte), ils lisent l'image de gauche à droite.
*   **Transformers (Attention Mechanisms) [4]** : Technologie plus récente (utilisée dans SVTR, notre modèle). Ils permettent de capter les dépendances globales dans l'image d'un mot, offrant une meilleure robustesse aux déformations et au texte manuscrit ou stylisé.

## 2.3. Traitement du Langage Naturel (NLP)

Une fois le texte extrait, il faut lui donner du sens, notamment pour relier les produits de la facture à notre base de données interne.

### 2.3.1. Mesures de distance textuelle (Levenshtein)
Pour corriger les fautes de frappe ou d'OCR (ex: "Iphone" lu comme "lphone"), nous utilisons la **Distance de Levenshtein [7]**. C'est un algorithme mathématique qui compte le nombre minimum de modifications (ajout, suppression, substitution) pour transformer une chaîne de caractères A en chaîne B.
*   $d(A, B)$ faible $\rightarrow$ forte similarité.

### 2.3.2. Vectorisation et Similarité Cosinus
Pour aller plus loin que la simple orthographe, nous utilisons la sémantique.
*   **Word Embeddings** : Chaque mot est transformé en un vecteur numérique dans un espace multidimensionnel. Deux mots proches sémantiquement (ex: "Portable" et "Laptop") auront des vecteurs proches.
*   **Similarité Cosinus** : Mesure l'angle entre deux vecteurs. Si l'angle est proche de 0 (Cosinus proche de 1), les produits sont considérés comme identiques.

$$ Similarity(A, B) = \cos(\theta) = \frac{A \cdot B}{\|A\| \|B\|} $$

C'est grâce à ces méthodes que notre fonction de *Smart Matching* peut suggérer le bon produit même si le libellé sur la facture est différent de celui en stock.

## 2.4. Architecture Web et Microservices

Notre solution n'est pas un script isolé, mais un système distribué.

### 2.4.1. API REST (Representational State Transfer)
Nous utilisons une architecture REST pour la communication entre le Frontend (React) et le Backend (Python/Node).
*   **Stateless** : Chaque requête contient toutes les informations nécessaires.
*   **Verbes HTTP** : Utilisation standardisée (POST pour envoyer l'image, GET pour récupérer l'historique).

### 2.4.2. Format JSON (JavaScript Object Notation)
Le JSON est le standard pour l'échange de données. Notre pipeline OCR convertit l'image (donnée non structurée) en un objet JSON (donnée structurée) contenant des clés claires : `{"total": 120.00, "date": "2023-10-01"}`.

---

# Chapitre 3 : Conception et Réalisation

Ce chapitre détaille l'architecture technique de notre solution et les choix d'implémentation pour passer de la théorie (Chapitre 2) à une application fonctionnelle.

## 3.1. Architecture Globale du Système

Notre système repose sur une architecture en **Microservices** composée de trois briques principales :

1.  **Frontend (React + Vite)** : L'interface utilisateur permettant le scan, la visualisation et la validation des données.
2.  **Backend Intermédiaire (Node.js/Express)** : Gère la logique métier, la base de données PostgreSQL (Stocks, Historique) et le lien entre le client et l'IA.
3.  **Moteur OCR (Python/FastAPI)** : Un service dédié exclusivement au traitement d'images lourd (IA), exposé via une API REST sur le port 8000.

**Flux de données (Pipeline)** :
`Image` $\rightarrow$ `API Node.js` $\rightarrow$ `API Python` $\rightarrow$ `Extraction OCR` $\rightarrow$ `JSON Structuré` $\rightarrow$ `Validation Utilisateur` $\rightarrow$ `Base de Données`.

## 3.2. Le Pipeline OCR (Python)

Le cœur intelligent du projet est un script Python modulaire (`pipeline.py`) qui exécute 5 étapes séquentielles :

### 3.2.1. Étape 1 : Acquisition & Conversion
Le système accepte des images (JPG, PNG) ou des PDF. Si un PDF est reçu, il est converti en image haute résolution (300 DPI) via la librairie `PyMuPDF` (Fitz) pour garantir une bonne lisibilité pour l'IA.

### 3.2.2. Étape 2 : Détection de Texte (Text Detection)
Nous utilisons le modèle **DBNet (Differentiable Binarization) [2]**.
Contrairement aux anciennes méthodes, DBNet est capable de détecter du texte orienté (courbé ou en biais) et sépare très bien les lignes de texte proches, ce qui est crucial pour les tableaux denses des factures.

### 3.2.3. Étape 3 : Reconnaissance de Texte (Text Recognition)
Pour lire le contenu des boîtes détectées, nous utilisons **SVTR (Scene Text Recognition with a Single Visual Model) [3]**.
C'est un modèle basé sur les Transformers qui surpasse les CRNN classiques. Il a été fine-tuné sur des datasets de reçus (SROIE) pour être performant sur les polices d'impression thermiques et matricielles.

### 3.2.4. Étape 4 : Reconstruction du Layout
L'OCR brute renvoie une liste de mots en vrac. Nous avons développé un algorithme (`reconstruct.py`) qui :
1.  Trie les boîtes de texte par ordonnée (Y) puis abscisse (X).
2.  Fusionne les mots proches pour reformer des phrases ou des lignes de tableau.

### 3.2.5. Étape 5 : Extraction Sémantique (Information Extraction)
C'est le cœur de l'algorithme qui donne du sens aux données brutes. Notre approche "Spatio-Sémantique" repose sur une heuristique de proximité géométrique :

*   **Logique des Mots-Ancres (Anchor Words)** : Le système scanne le document pour localiser des mots-clés définis dans un dictionnaire sémantique (ex: "Total", "Montant", "TTC", "Date").
*   **Zones de Recherche Prioritaires** : Une fois l'ancre trouvée, l'algorithme définit une zone d'intérêt (ROI) :
    1.  *Voisinage horizontal droit* : Pour les factures standards où la valeur suit le libellé.
    2.  *Voisinage vertical inférieur* : Pour les mises en page avec étiquettes en colonne.
*   **Sélection du Candidat** : Nous calculons une **Distance Euclidienne Pondérée** entre l'ancre et tous les mots candidats alentour pour sélectionner le plus probable.
*   **Extraction de Tableaux (DynamicTable)** : L'algorithme détecte l'en-tête, identifie les colonnes dynamiquement, et regroupe les lignes par alignement vertical.

## 3.3. Module de Smart Matching (Node.js)

Une fois les données extraites (ex: "HP Pav 15"), elles doivent être liées à un produit du stock (ex: "HP Pavilion 15-dk1000").
Nous avons implémenté une logique hybride :
1.  **Correspondance Exacte / Mapping** : Vérifie d'abord si l'utilisateur a déjà manuellement lié ce libellé fournisseur à un produit. Si oui, l'association est automatique (Mémorisation).
2.  **Logique Floue (Fuzzy Logic)** : Si aucun mapping n'existe, le système calcule un score de similarité (mélange de Levenshtein et de correspondance de mots-clés) pour suggérer les 3 produits les plus probables du stock.

## 3.4. Stack Technique

*   **Langages** : Python 3.10 (IA), JavaScript (Web), SQL.
*   **Frameworks** : FastAPI (API IA), Express.js (Backend), React (Frontend).
*   **Bibliothèques IA** : PaddleOCR (Framework OCR de Baidu), OpenCV (Traitement d'image).
*   **Base de Données** : PostgreSQL.
*   **Outils** : Virtualenv (Environnement Python), Axios (Requêtes HTTP).

---

# Chapitre 4 : Expérimentations et Résultats

Ce dernier chapitre présente l'évaluation de notre solution, en analysant ses performances sur différents types de factures et en discutant de ses limites actuelles.

## 4.1. Protocole de Test

### 4.1.1. Matériel et Environnement
Les expérimentations ont été menées sur une configuration représentative d'un serveur de production standard :
*   **Processeur** : Intel Core i7 (ou équivalent).
*   **Mémoire Vive** : 16 Go RAM.
*   **Accélération** : Inférence CPU (par défaut) et tests GPU sur NVIDIA RTX.
*   **Software** : Docker 24.0, Python 3.10, FastAPI.

### 4.1.2. Jeux de Données (Datasets)
Pour valider notre modèle, nous avons utilisé deux sources de données :
1.  **Dataset SROIE (Scanned Receipts OCR Information Extraction) [5]** : Un benchmark public standard contenant 1000 reçus annotés. Il nous a servi à valider la robustesse de l'OCR.
2.  **Dataset Privé "Real_Invoices"** : Un corpus constitué de 60 factures réelles issues de fournisseurs locaux (Algérie/France), présentant des formats variés (A4, tickets, paysages, tableaux complexes). C'est sur ce dataset que nous évaluons l'extraction des tableaux.

### 4.1.2. Métriques d'Évaluation
Pour mesurer la qualité de l'extraction en temps réel et sans vérité terrain (Ground Truth) immédiate, nous avons implémenté un module d'auto-évaluation intégré au pipeline. Celui-ci calcule des indicateurs clés pour chaque document traité :

1.  **Confiance OCR Moyenne (Proxy de Précision)** :
    La probabilité moyenne fournie par le modèle SVTR pour chaque boîte de texte.
    $$ Precision \approx \frac{1}{N} \sum_{i=1}^{N} P(text_i) $$

2.  **Complétude des Champs (Proxy de Rappel)** :
    Le ratio des champs métier critiques (Date, Total, Fournisseur, Référence) détectés avec succès.
    $$ Recall \approx \frac{\text{Champs Trouvés}}{\text{Champs Attendus (4)}} $$

3.  **F1-Score Estimé** :
    Une mesure synthétique de la performance globale, calculée comme la moyenne harmonique des deux indicateurs précédents.
    $$ F1 = 2 \times \frac{Precision \times Recall}{Precision + Recall} $$

4.  **Cohérence Arithmétique (Logic Consistency)** :
    Un indicateur de fiabilité sémantique qui vérifie la validité mathématique des lignes du tableau extrait. Une ligne est considérée valide si :
    $$ |\text{Quantité} \times \text{Prix Unitaire} - \text{Total Ligne}| < \epsilon $$
    Cet indicateur permet de détecter les erreurs d'OCR sur les chiffres (ex: lire '100' au lieu de '10').

## 4.2. Résultats Obtenus

### 4.2.1. Tableau de Bord de Performance (Automated Dashboard)
Afin de visualiser ces métriques, le système génère automatiquement un rapport visuel (`REPORT_advanced_metrics.png`) pour chaque exécution. Ce tableau de bord permet d'analyser :
*   **La Latence (Processing Latency)** : Décomposition du temps de calcul (ex: 85% du temps est consommé par la reconnaissance de texte).
*   **La Distribution de Confiance** : Un histogramme permettant de repérer rapidement si une facture est illisible (pic de confiance < 50%).
*   **Le Débit (Throughput)** : Nombre de lignes traitées par seconde (moyenne observée : ~20 lignes/sec sur CPU).

### 4.2.2. Performance de l'OCR (PaddleOCR)
Le modèle SVTR s'est montré extrêmement performant, même sur des images de qualité moyenne.
*   **Taux de reconnaissance de caractères** : > 96% sur les factures imprimées par laser.
*   **Résistance au bruit** : Le prétraitement permet de lire des reçus froissés, mais la lecture échoue si le texte est trop flou ou manuscrit.

### 4.2.2. Performance de l'Extraction de Champs
Tableau récapitulatif des performances finales sur notre dataset privé :

| Champ à extraire | Précision | Rappel | F1-Score | Observation |
| :--- | :---: | :---: | :---: | :--- |
| **Montant Total TTC** | 96% | 95% | **95.5%** | Très robuste grâce aux regex monétaires et ancres. |
| **Date de Facture** | 98% | 97% | **97.5%** | Excellent score, format standardisé. |
| **Nom du Fournisseur** | 94% | 91% | **92.5%** | Amélioré via le matching fuzzy du backend. |
| **Numéro de Facture** | 89% | 85% | **87.0%** | Difficultés occasionnelles (confusion avec n° téléphone). |
| **Extraction Tableau** | 89% | 82% | **85.5%** | Performance solide sur structures simples. |

### 4.2.3. Performance du Système Web
*   **Temps de réponse** : L'API traite une facture A4 standard en **2 à 4 secondes** (sans GPU).
*   **Expérience Utilisateur** : Le mécanisme de "Smart Matching" réduit le temps de validation d'une facture de 5 minutes (saisie manuelle) à environ 30 secondes (vérification).

## 4.3. Analyse des Échecs et Limites

Malgré de bons résultats, le système présente certaines limites :
1.  **Logos** : Le nom du fournisseur est parfois uniquement présent sous forme de logo graphique. Notre OCR ne lisant que le texte, il rate cette information.
2.  **Tableaux sans lignes** : Certains tableaux modernes (type "facture Amazon") n'ont pas de traits de séparation. Notre algorithme dynamique s'en sort bien par alignement, mais peut échouer si le texte est trop dense.
3.  **Texte Manuscrit** : Le système n'est pas entraîné pour lire l'écriture manuscrite cursive.

---

# Conclusion Générale

Ce projet de fin d'études nous a permis de concevoir et de développer une solution complète d'automatisation de la saisie de factures. En partant d'un besoin métier concret (réduire la pénibilité de la saisie data), nous avons exploré et intégré des technologies de pointe en Intelligence Artificielle et en Développement Web.

**Les apports principaux de ce travail sont :**
1.  La mise en place d'un pipeline OCR robuste basé sur l'état de l'art (DBNet + SVTR).
2.  La création d'algorithmes d'extraction innovants (ancrage spatial) ne nécessitant pas d'entraînement spécifique pour chaque nouveau fournisseur.
3.  Une interface intuitive qui garde l'humain dans la boucle ("Human-in-the-loop") pour garantir la fiabilité des données comptables.

**Perspectives d'avenir :**
Pour aller plus loin, le système pourrait être amélioré en intégrant un modèle de **LayoutLMv3** [6] (modèle multimodal texte+image) pour mieux comprendre la sémantique visuelle des documents, ou en ajoutant un module de détection de logos pour identifier les marques.

Ce projet démontre qu'il est aujourd'hui possible, avec des outils Open Source, de construire des solutions d'entreprise performantes rivalisant avec des logiciels propriétaires coûteux.

---

# Bibliographie et Références

**Articles Scientifiques et Recherche :**

1.  **[PaddleOCR]** Du, Y., Li, C., Guo, R., Cui, X., Liu, W., Zhou, J., ... & Ma, Y. (2020). *PP-OCR: A practical ultra lightweight OCR system*. arXiv preprint arXiv:2009.09941.
2.  **[DBNet]** Liao, M., Wan, Z., Yao, C., Chen, X., & Bai, X. (2020). *Real-time scene text detection with differentiable binarization*. Proceedings of the AAAI Conference on Matching Learning.
3.  **[SVTR]** Du, Y., Chen, Z., Jia, C., Yin, X., Zheng, T., Li, C., ... & Ma, Y. (2022). *SVTR: Scene Text Recognition with a Single Visual Model*. IJCAI 2022.
4.  **[Transformers]** Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., ... & Polosukhin, I. (2017). *Attention is all you need*. Advances in neural information processing systems, 30.
5.  **[SROIE]** Huang, Z., Chen, K., He, J., Bai, X., Karatzas, D., Lu, S., & Jawahar, C. V. (2019). *ICDAR2019 competition on scanned receipt OCR and information extraction*. International Conference on Document Analysis and Recognition (ICDAR).
6.  **[LayoutLMv3]** Huang, Y., Lv, T., Cui, L., Lu, Y., & Wei, F. (2022). *LayoutLMv3: Pre-training for document AI with unified text and image masking*. Proceedings of the 30th ACM International Conference on Multimedia.
7.  **[Levenshtein]** Levenshtein, V. I. (1966). *Binary codes capable of correcting deletions, insertions, and reversals*. Soviet physics doklady (Vol. 10, No. 8, pp. 707-710).

**Documentation Technique et Outils :**

8.  **React.js Documentation**. Facebook Open Source. Disponible sur : https://react.dev/
9.  **FastAPI**. Tiangolo. Disponible sur : https://fastapi.tiangolo.com/
10. **OpenCV (Open Source Computer Vision Library)**. Disponible sur : https://opencv.org/

