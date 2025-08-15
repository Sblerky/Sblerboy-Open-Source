# Sblerboy – Open Source

_Version open source du bot Discord **Sblerboy**_

Sblerboy est un bot Discord qui permet de jouer à des jeux Game Boy directement depuis un salon Discord.  
Les joueurs contrôlent la partie en réagissant à un message dédié, et toutes les actions sont enregistrées dans un salon de logs.

---

## Fonctionnalités

- Jouer à un jeu Game Boy directement dans un salon Discord
- Suivi en temps réel des actions des joueurs dans un salon de logs
- Possibilité de changer "l'objectif actuel" en modifiant la description du salon de jeu

**Exemple en jeu :**

![Exemple de salon de jeu](https://cdn.discordapp.com/attachments/849667753295347745/874205955196346418/unknown.png)

**Exemple de logs :**

![Exemple de salon de logs](https://cdn.discordapp.com/attachments/849667753295347745/874206021818675240/unknown.png)

---

## Principe de fonctionnement

1. Le bot envoie un message principal dans un salon réservé.  
2. Les joueurs réagissent avec des émojis pour effectuer des actions dans le jeu.  
3. Chaque action est envoyée dans un salon de logs pour garder un historique.  

---

## Prérequis

- **Python 3** installé et fonctionnel
- **Un serveur Discord** dont vous êtes administrateur, avec au moins **3 salons textuels** :
  - 1 salon réservé au bot (seul le bot peut y écrire et ajouter des réactions)
  - 1 salon de logs
  - 1 salon de discussion autour du jeu
- **Un bot Discord** créé par vos soins, avec les 3 [intents privilégiés activés](https://discord.com/developers/docs/topics/gateway#enabling-privileged-intents)
- Une **ROM Game Boy** au format `.gb`

---

## Installation

1. **Cloner le dépôt**
   ```sh
   git clone https://github.com/Sblerky/Sblerboy-Open-Source.git
   cd Sblerboy-Open-Source
   pip install -r requirements.txt
   ```
2. **Configurer le bot**  
   Remplissez le fichier `config.ini` avec vos informations :

   - `ID_CHANNEL` : ID du salon textuel où le bot enverra le message de jeu  
   - `ID_GUILD` : ID du serveur Discord  
   - `ID_LOG_CHANNEL` : ID du salon de logs  
   - `ID_CHAT_CHANNEL` : ID du salon de discussion  
   - `BOT_TOKEN` : token de votre bot Discord  

3. **Placer la ROM**  
   Renommez votre ROM en `rom.gb` et placez-la dans le dossier `rom`.

4. **Lancer le bot**  
   ```sh
   python3 sblerboy.py

---

## Licence

Ce projet est distribué sous la licence **GNU General Public License v3.0 (GPL-3.0)**.  
Vous êtes libre de l'utiliser, le modifier et le redistribuer, à condition de respecter les termes de la licence.  
Pour plus d’informations, consultez le fichier [LICENSE](LICENSE) inclus dans le dépôt.
