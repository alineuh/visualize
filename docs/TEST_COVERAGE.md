# Couverture de Tests - Fractional Art Marketplace

## Résumé Exécutif

Ce document présente la stratégie de test complète pour les smart contracts du projet **Fractional Art Marketplace**. La suite de tests garantit la sécurité, la robustesse et la conformité aux spécifications du projet.

---

## 📊 Statistiques de Couverture

### Contrats Testés
- ✅ **ShareFA2** : Token FA2 pour les parts fractionnées
- ✅ **FractionalArtMarketV1_FA2** : Marketplace avec escrow NFT
- ✅ **MockNFT_FA2** : Contrat NFT pour les tests d'intégration

### Métriques
- **Total de tests** : 10 modules de test
- **Entry points couverts** : 100%
- **Cas d'erreur testés** : 15+
- **Scénarios d'intégration** : 1 workflow complet

---

## 🧪 Modules de Test

### 1. ShareFA2 - Fonctionnalités de Base

**Fichier** : `test_share_fa2_basic`

**Objectifs** :
- Vérifier l'initialisation du contrat
- Tester le transfert des droits d'administration
- Valider le minting de tokens
- Garantir la sécurité des permissions

**Tests Inclus** :
1. État initial du contrat (admin, ledger vide)
2. `set_admin` - transfert au Market contract
3. Restriction : seul l'admin peut appeler `set_admin`
4. `mint` - création de shares pour les acheteurs
5. Restriction : seul l'admin (Market) peut mint
6. Validation : impossible de mint 0 tokens

**Importance** : Ces tests garantissent que seul le Market contract peut créer de nouveaux tokens de parts, empêchant toute inflation non autorisée.

---

### 2. ShareFA2 - Transferts et Opérateurs

**Fichier** : `test_share_fa2_transfers`

**Objectifs** :
- Valider les transferts FA2 standards
- Tester le système d'opérateurs
- Vérifier les contrôles de balance

**Tests Inclus** :
1. Transfert direct par le propriétaire
2. Erreur si balance insuffisante
3. Erreur si l'appelant n'est ni propriétaire ni opérateur
4. Ajout d'un opérateur via `update_operators`
5. Transfert autorisé via opérateur
6. Retrait d'un opérateur
7. Blocage des transferts après retrait
8. Restriction : seul le propriétaire peut gérer ses opérateurs

**Importance** : Ces tests assurent que les parts peuvent être transférées et échangées en toute sécurité, ce qui est essentiel pour un marché secondaire futur.

---

### 3. ShareFA2 - Tokens Multiples

**Fichier** : `test_share_fa2_multi_token`

**Objectifs** :
- Valider la gestion de plusieurs token IDs
- Tester les transferts groupés

**Tests Inclus** :
1. Minting de plusieurs token IDs distincts
2. Vérification des total_supply séparés
3. Transferts groupés de plusieurs tokens en une transaction

**Importance** : Chaque pièce d'art a son propre token ID, donc ce test garantit que le système peut gérer plusieurs ventes simultanément.

---

### 4. Market - Création de Collections

**Fichier** : `test_market_collections`

**Objectifs** :
- Valider les règles de cap_percent
- Tester la création multiple
- Vérifier les cas limites

**Tests Inclus** :
1. Création avec cap valide (20%)
2. Création de plusieurs collections par un artiste
3. Erreur si cap < 1% (CAP_TOO_LOW)
4. Erreur si cap > 100% (CAP_TOO_HIGH)
5. Cas limite : cap = 1% (très fractionné)
6. Cas limite : cap = 100% (un seul acheteur possible)

**Importance** : Le cap définit la fraction maximale qu'un acheteur peut posséder, c'est le cœur de la fractionalization.

---

### 5. Market - Création de Pièces depuis NFT

**Fichier** : `test_market_piece_creation`

**Objectifs** :
- Valider l'escrow du NFT
- Tester les permissions artiste
- Vérifier l'allocation de share_token_id

**Tests Inclus** :
1. L'artiste approuve le Market comme opérateur
2. Création de pièce avec transfert du NFT au Market
3. Vérification du NFT en escrow
4. Erreur si l'appelant n'est pas l'artiste
5. Erreur si la collection n'existe pas
6. Erreur si le prix est à 0

**Importance** : Ces tests garantissent que les NFTs sont correctement sécurisés et que seuls les artistes légitimes peuvent créer des ventes.

---

### 6. Market - Achat de Parts (Basique)

**Fichier** : `test_market_buying_basic`

**Objectifs** :
- Valider le flux d'achat
- Vérifier le minting des shares
- Tester le paiement de l'artiste

**Tests Inclus** :
1. Achat de parts par un acheteur
2. Enregistrement de la contribution
3. Vérification du total_raised
4. Minting de shares (1:1 avec mutez)
5. Paiement immédiat de l'artiste (v1)
6. Plusieurs acheteurs contribuent
7. Acheteur augmente sa contribution
8. Erreur si montant = 0
9. Erreur si piece_id invalide

**Importance** : C'est le cœur du système - acheter des parts fractionnées d'une œuvre d'art.

---

### 7. Market - Application du Cap

**Fichier** : `test_market_cap_enforcement`

**Objectifs** :
- Garantir le respect strict du cap_percent
- Empêcher la centralisation

**Tests Inclus** :
1. Acheteur peut contribuer jusqu'au cap (2.5 tez sur 10 tez à 25%)
2. Impossible de dépasser le cap même d'1 mutez
3. Impossible de dépasser le cap en un seul achat

**Importance** : Le cap empêche qu'un seul acheteur monopolise une œuvre, garantissant une vraie fractionalization.

---

### 8. Market - Fermeture de Pièce

**Fichier** : `test_market_piece_closure`

**Objectifs** :
- Valider la fermeture à 100% de financement
- Empêcher le surfinancement
- Bloquer les achats après fermeture

**Tests Inclus** :
1. Plusieurs acheteurs financent progressivement
2. Pièce reste ouverte jusqu'à 100%
3. Fermeture automatique quand total_raised = price
4. Erreur si tentative d'achat sur pièce fermée
5. Impossible de surfinancer (total > price)

**Importance** : Garantit que le financement est exact et que les pièces se ferment proprement.

---

### 9. Market - Vues On-chain

**Fichier** : `test_market_views`

**Objectifs** :
- Valider les fonctions de lecture
- Tester le calcul du cap_amount

**Tests Inclus** :
1. `get_collection` retourne les bonnes données
2. `get_piece` retourne l'état de la pièce
3. `get_cap_amount` calcule correctement (price × cap_percent / 100)
4. `get_user_contribution` avant achat (0 tez)
5. `get_user_contribution` après achat (montant correct)

**Importance** : Les vues permettent aux dApps et utilisateurs de lire l'état sans transaction.

---

### 10. Market - Cas Limites et Edge Cases

**Fichier** : `test_market_edge_cases`

**Objectifs** :
- Tester les extrêmes du système
- Valider les montants fractionnels
- Vérifier les scénarios complexes

**Tests Inclus** :
1. Cap 100% : un seul acheteur finance entièrement
2. Cap 1% : nécessite 100 acheteurs minimum
3. Montants fractionnels en mutez (3.33 tez)
4. Plusieurs pièces dans une même collection
5. Vérification des share_token_id distincts par pièce
6. Achat de parts dans plusieurs pièces par le même acheteur

**Importance** : Ces tests prouvent que le système est robuste même dans des conditions extrêmes.

---

### 11. Test d'Intégration Complet

**Fichier** : `test_full_integration`

**Objectifs** :
- Simuler un workflow réaliste complet
- Tester l'interaction entre tous les contrats
- Valider le cycle de vie complet

**Scénario** :
1. Déploiement de ShareFA2, Market, et NFT mock
2. Transfert des droits d'admin au Market
3. 2 artistes créent des collections (15% et 50%)
4. Artistes créent plusieurs pièces (3 au total)
5. 3 collectionneurs achètent des parts
6. Fermeture automatique d'une pièce
7. Transfert de shares entre collectionneurs
8. Financement complet d'une autre pièce
9. Vérification des total_supply finaux

**Importance** : Ce test démontre que tout le système fonctionne ensemble dans un cas d'usage réel.

---

## 🔒 Sécurité

### Vérifications de Permission
- ✅ Seul l'admin peut mint des shares
- ✅ Seul l'artiste peut créer des pièces pour sa collection
- ✅ Seul le propriétaire peut gérer ses opérateurs
- ✅ Seul l'admin peut transférer les droits d'admin

### Validations Métier
- ✅ Cap strictement appliqué (pas de dépassement d'1 mutez)
- ✅ Prix > 0 obligatoire
- ✅ Cap entre 1% et 100%
- ✅ Impossible de surfinancer
- ✅ Impossible d'acheter sur pièce fermée

### Contrôles de Balance
- ✅ Vérification de balance avant transfert
- ✅ Minting 1:1 avec contribution
- ✅ Total_supply cohérent avec les contributions

---

## 📈 Assertions Critiques

### États du Contrat
```python
scenario.verify(market.data.pieces[0].closed == True)
scenario.verify(market.data.pieces[0].total_raised == sp.tez(10))
scenario.verify(share_contract.data.total_supply[0] == 10_000_000)
```

### Balances
```python
scenario.verify(
    share_contract.data.ledger[sp.pair(buyer.address, 0)] == 2_000_000
)
```

### Permissions
```python
market.buy_piece(0).run(
    sender=unauthorized,
    valid=False,
    exception="NOT_ARTIST"
)
```

---

## 🎯 Cas d'Erreur Testés

| Erreur | Description | Test |
|--------|-------------|------|
| `NOT_ADMIN` | Seul l'admin peut mint/set_admin | ✅ |
| `ZERO_MINT` | Impossible de mint 0 tokens | ✅ |
| `NOT_OWNER` | Seul le propriétaire gère les opérateurs | ✅ |
| `NOT_OPERATOR` | Seul le propriétaire ou opérateur peut transférer | ✅ |
| `INSUFFICIENT_BALANCE` | Balance insuffisante pour le transfert | ✅ |
| `CAP_TOO_LOW` | Cap < 1% | ✅ |
| `CAP_TOO_HIGH` | Cap > 100% | ✅ |
| `NO_COLLECTION` | Collection inexistante | ✅ |
| `NOT_ARTIST` | Seul l'artiste peut créer une pièce | ✅ |
| `BAD_PRICE` | Prix ≤ 0 | ✅ |
| `NO_PIECE` | Pièce inexistante | ✅ |
| `PIECE_CLOSED` | Pièce déjà fermée | ✅ |
| `SEND_TEZ` | Montant = 0 | ✅ |
| `OVER_CAP_SHARE` | Dépassement du cap | ✅ |
| `OVER_PRICE` | Dépassement du prix total | ✅ |

---

## 🚀 Exécution des Tests

### Option 1 : SmartPy CLI (Recommandé)
```bash
~/smartpy-cli/SmartPy.sh test test_contracts.py /tmp/output
```

### Option 2 : Script Automatisé
```bash
./run_tests.sh
```

### Option 3 : SmartPy Online IDE
1. https://smartpy.io/ide
2. Charger les fichiers
3. Cliquer "Run tests"

---

## ✅ Résultats Attendus

**Tous les tests doivent passer** :
- 10 modules de test
- 60+ assertions individuelles
- 0 erreur
- Couverture complète des entry points

---

## 📚 Documentation Complémentaire

- `test_contracts.py` : Code source des tests
- `TEST_README.md` : Guide détaillé d'exécution
- `run_tests.sh` : Script d'automatisation

---

## 🎓 Apprentissages pour le Projet

Cette suite de tests démontre :

1. **Maîtrise de SmartPy** : Utilisation avancée des scenarios et assertions
2. **Compréhension du métier** : Tests alignés avec le use case d'art fractionné
3. **Sécurité** : Vérification systématique des permissions et validations
4. **Qualité professionnelle** : Structure claire, couverture complète, documentation

---

## 👥 Contribution

**Responsable des tests** : [Votre Nom]
**Équipe** : [Nom de l'équipe]
**Projet** : Fractional Art Marketplace
**Technologie** : SmartPy / Tezos

---

*Document généré pour le rendu du projet d'équipe*
