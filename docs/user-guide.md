# User guide / Guide utilisateur

Updated / Mise à jour : **2026-10-07** · Version : **1.0.0** (guide only / guide uniquement)

[English](#english) · [Français](#francais) · [Technical reference](../README.md)

<a id="english"></a>
## English

### What is this application for?

It helps you follow your Clash Royale clan: members, donations, activity, wars,
and possible promotions. It opens in your web browser, but runs on your computer.
It does not play battles, promote players, or kick members for you.

You do not need to write code. First-time installation needs Docker and a Clash
Royale API key. If those are unfamiliar, ask someone to help with installation
once. After that, opening the launcher and clicking **Start and open** is enough.

### 1. Get the application

Ask the person distributing the application for the **application folder and
the launcher for your computer, from the same version**. Keep them together in
a permanent folder such as Documents → Clan Manager, not inside a ZIP archive.

For **v1.0.0**, open [Release downloads](https://github.com/RaphaelDP/clash-royale-manager/releases/tag/v1.0.0).
Download **clan-manager-v1.0.0-source.zip** and your platform's file under **Assets**:
**windows.exe**, **linux-x86_64.AppImage.tar.gz**, **macos-intel.app.zip**, or
**macos-apple-silicon.app.zip** (all prefixed with **clan-manager-v1.0.0-**).
Extract the source and launcher archives. Place the launcher in the subfolder
listed below; rename the Windows file to **windows_launcher.exe**.
The source ZIP contains the application files directly; no inner project.zip
step is needed for this release download.

If the maintainer instead directs you to a GitHub Actions build:

1. Open [Desktop launchers on GitHub](https://github.com/RaphaelDP/clash-royale-manager/actions/workflows/launchers.yml)
   and sign in.
2. Open the successful run recommended by the maintainer. Scroll to **Artifacts**,
   the downloadable files near the bottom.
3. Download **project-source**. Extract it, then extract the **project.zip**
   inside it. The resulting application folder contains **docker-compose.yml**.
4. Download the launcher matching your computer from that **same run**.
   Extract any ZIP or other archive until you reach the file below.
5. Put that file inside the indicated subfolder of your application folder.

| Your computer | Download | File | Where to put it |
| --- | --- | --- | --- |
| Windows | launcher-windows-2022 | windows_launcher.exe | launch/windows |
| Mac with Apple M-series chip | launcher-macos-15 | macos_launcher.app | launch/macos |
| Mac with Intel processor | launcher-macos-15-intel | macos_launcher.app | launch/macos |
| Linux, Intel/AMD 64-bit | launcher-ubuntu-22.04 | linux_launcher.AppImage | launch/linux |

On a Mac, **Apple menu → About This Mac** tells you whether it has an Apple chip
or Intel processor. The names above describe the build machines; they are not a
promise that every older operating system is supported.

GitHub requires sign-in to download these files, and downloads may expire.
If they are missing, ask the maintainer for a fresh build.
[GitHub download help](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).

### 2. Install Docker once

Use the [official Docker installation page](https://docs.docker.com/get-started/get-docker/)
and choose your operating system. On Windows and Mac, install and open Docker
Desktop; finish any restart/setup it requests. On Linux, ask for help installing
Docker with Compose and allowing your account to use it.

Docker runs the application in the background. It must be running before the
launcher can start the dashboard. You do not need Python.

The launchers are unsigned. If your computer blocks one, verify that it came
from this project's maintainer before using your operating system's option to
allow that particular application. Do not disable protection for all downloads.
On Linux, open the AppImage's **Properties → Permissions** and allow execution
if necessary. Some Linux systems also need an AppImage/FUSE compatibility package.

### 3. Set up your clan

1. Double-click the launcher.
2. If **Locate application** appears, choose the extracted folder containing
   **docker-compose.yml**.
3. Open **Application settings** and complete the two fields below.

| Field | What to enter |
| --- | --- |
| CR_API_TOKEN | Your API key from the [Clash Royale developer portal](https://developer.clashroyale.com/). |
| CLAN_TAG | Your clan's tag from Clash Royale, including its initial **#**. |

An API key is a private access code, not your game password. Sign in to the
developer portal, create a key, and authorize the public Internet IP address of
the computer running the application. If you do not know that address, ask the
person helping you install it. Changing Internet connections, using a VPN, or an
address change by your provider may require updating the key's allowed address.

Keep the other settings at their defaults. The default timezone is Europe/Paris;
change it only if you want automatic tasks to follow another timezone.
**DISCORD_WEBHOOK_URL** is optional: leave it blank unless you want daily reports
and already have a webhook for your Discord channel.

The launcher creates its settings file automatically. You do not need to find or
edit a hidden file. Confirm the settings dialog, then click **Start and open**.
The first start downloads/builds the application and can take several minutes.
Wait for completion; repeated clicking does not speed it up.

Success means your browser displays **Clash Royale Clan Manager** and the pages
open. The address is [localhost:8501](http://localhost:8501), meaning this computer.

### 4. Daily use

Open Docker, open the launcher, and click **Start and open**.

| I want to… | Open… |
| --- | --- |
| See the clan's overall situation | **Overview** |
| Find a member or filter roles | **Members** |
| See one player's profile and progress | **Player** |
| Review scores and promotion suggestions | **Promotions** |
| Follow the current week and past wars | **Wars** |
| Check automatic tasks or change their schedule | **Settings** |

On **Overview**, **Refresh Clan Members** and **Refresh War Data** fetch newer
information. **Recalculate Contribution Scores** updates scores from collected
data. Wait for the result before repeating an action. A browser refresh alone
does not force a new API download.

“Training days” is normal: those three days do not count as missed war attacks.
Past war results remain visible. New installations have little personal history;
charts grow as the application collects data.

In **Settings → Scheduler**, leave the defaults unless you want different times.
**Save schedule** applies changes within about five seconds.
For daily collections and reports to run, the computer must stay awake, Docker
must stay open, and the application must remain running. It cannot collect while
the computer is off.

### 5. Close or reopen

| What you do | What happens |
| --- | --- |
| Close the browser tab or launcher window | Background collection continues. |
| Dashboard sidebar **Close → Dashboard only** | Dashboard stops; automatic tasks continue. Reopen with the launcher's **Start and open**. |
| Dashboard sidebar **Close → Everything**, or launcher **Stop all** | Dashboard and automatic tasks stop. Your saved data stays. |
| Turn off/suspend the computer | Collection stops until it can run again. |

After choosing a dashboard Close option, click **Confirm close** to apply it;
**Cancel** leaves the application running.

To stop everything and free the application's network port, use **Stop all**.
Docker may report an unhealthy dashboard while you deliberately keep only the
scheduler running; reopen the dashboard to restore it.

### 6. Update and keep your data

**Update application does not download a new version.** First obtain the new
application files from the maintainer.

1. Click **Stop all**.
2. Copy the entire existing application folder to a safe place as a backup,
   including hidden files. It contains your private settings and history.
3. Following the maintainer's instructions, replace the application source files
   with the new version. Keep your existing **.env**, **data**, **backups**, and
   **logs**. Keep the same application folder name and location.
4. Install the matching new launcher if supplied.
5. Open the launcher and click **Update application**. Wait for it to finish.

Do not send your backup folder to other people: it includes your private API key.
Automatic database backups are kept in **backups** while the application runs;
they do not back up the entire application or settings. For a restore, ask the
maintainer to follow the [restore procedure](../README.md#backup-and-restore).
There is no restore wizard.

### If something goes wrong

| Problem | Try this |
| --- | --- |
| Docker is unavailable | Open Docker Desktop and wait until ready. On Linux, ask your installer to check Docker access. |
| Application folder not found | Choose the extracted folder containing docker-compose.yml, not the ZIP or launcher-only folder. |
| Browser cannot connect | Click **Start and open**. Wait for startup; check Docker is running. |
| Access denied / 403 | Check the API key and its allowed public IP address. |
| Data looks old | Check **Settings → Job Health**, then use the appropriate refresh button. |
| Few or empty charts | Allow collection time; some charts need several days of snapshots. |
| Port already in use | Stop another Clan Manager instance; ask for help if the port belongs to another application. |
| Not enough disk space | Free space, then retry. Do not delete your data folder. |

For help, give the maintainer the error message, operating system, application
version, and steps you took. Never send the API key, Discord webhook, or **.env**.
Use the dashboard on a trusted computer/network; it has no login screen.

<a id="francais"></a>
## Français

### À quoi sert cette application ?

Elle vous aide à suivre votre clan Clash Royale : membres, dons, activité,
guerres et suggestions de promotion. Elle s'affiche dans votre navigateur, mais
fonctionne sur votre ordinateur. Elle ne joue pas de combats et ne promeut ni
n'exclut de membres à votre place.

Vous n'avez pas besoin de programmer. La première installation demande Docker
et une clé d'accès à l'API Clash Royale. Si ces termes ne vous parlent pas,
demandez de l'aide pour cette première étape. Ensuite, il suffit d'ouvrir le
lanceur et de cliquer sur **Start and open**.

Les boutons de l'application sont actuellement en anglais. Ce guide conserve
leurs noms exacts pour vous permettre de les retrouver.

### 1. Récupérer l'application

Demandez à la personne qui vous fournit l'application **le dossier de
l'application et le lanceur adapté à votre ordinateur, de la même version**.
Gardez-les ensemble dans un dossier permanent, par exemple Documents →
Clan Manager. Ne lancez pas l'application depuis une archive ZIP.

Pour **v1.0.0**, ouvrez [les téléchargements de la version](https://github.com/RaphaelDP/clash-royale-manager/releases/tag/v1.0.0).
Dans **Assets**, téléchargez **clan-manager-v1.0.0-source.zip** et le fichier
adapté : **windows.exe**, **linux-x86_64.AppImage.tar.gz**, **macos-intel.app.zip**
ou **macos-apple-silicon.app.zip** (tous précédés de **clan-manager-v1.0.0-**).
Décompressez les archives et placez le lanceur dans le sous-dossier indiqué
ci-dessous. Renommez le fichier Windows en **windows_launcher.exe**.
Le ZIP de cette version contient directement les fichiers de l'application :
il n'y a pas de second project.zip à extraire.

Si le responsable vous dirige plutôt vers une compilation GitHub Actions :

1. Ouvrez [Desktop launchers sur GitHub](https://github.com/RaphaelDP/clash-royale-manager/actions/workflows/launchers.yml)
   et connectez-vous à votre compte.
2. Ouvrez l'exécution réussie indiquée par le responsable du projet. Descendez
   jusqu'à **Artifacts**, la liste des fichiers téléchargeables.
3. Téléchargez **project-source**, décompressez-le, puis décompressez également
   **project.zip** à l'intérieur. Le dossier obtenu contient **docker-compose.yml**.
4. Depuis cette **même exécution**, téléchargez le lanceur correspondant à votre
   ordinateur. Décompressez toutes les archives jusqu'au fichier indiqué.
5. Placez ce fichier dans le sous-dossier correspondant du dossier de l'application.

| Ordinateur | Téléchargement | Fichier | Sous-dossier |
| --- | --- | --- | --- |
| Windows | launcher-windows-2022 | windows_launcher.exe | launch/windows |
| Mac avec puce Apple M | launcher-macos-15 | macos_launcher.app | launch/macos |
| Mac avec processeur Intel | launcher-macos-15-intel | macos_launcher.app | launch/macos |
| Linux, Intel/AMD 64 bits | launcher-ubuntu-22.04 | linux_launcher.AppImage | launch/linux |

Sur Mac, **menu Apple → À propos de ce Mac** indique le type de puce.
Ces noms désignent les machines de compilation ; ils ne garantissent pas la
compatibilité avec toutes les anciennes versions des systèmes.

GitHub demande une connexion pour télécharger ces fichiers. Les téléchargements
peuvent expirer : s'ils ont disparu, demandez une nouvelle compilation au
responsable. [Aide GitHub](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).

### 2. Installer Docker une fois

Ouvrez la [page officielle d'installation de Docker](https://docs.docker.com/get-started/get-docker/)
et choisissez votre système. Sur Windows et Mac, installez et ouvrez Docker
Desktop ; terminez les étapes demandées, y compris un éventuel redémarrage.
Sur Linux, demandez de l'aide pour installer Docker avec Compose et autoriser
votre compte à l'utiliser.

Docker fait fonctionner l'application en arrière-plan. Il doit être démarré
avant le lancement du tableau de bord. Python n'est pas nécessaire.

Les lanceurs ne sont pas signés. Si votre ordinateur en bloque un, vérifiez sa
provenance auprès du responsable du projet avant d'autoriser cette application
dans les réglages de votre système. Ne désactivez pas la protection générale.
Sur Linux, autorisez si nécessaire l'exécution de l'AppImage dans
**Propriétés → Permissions**. Certains systèmes nécessitent aussi un paquet
de compatibilité AppImage/FUSE.

### 3. Configurer votre clan

1. Double-cliquez sur le lanceur.
2. Si **Locate application** apparaît, choisissez le dossier décompressé qui
   contient **docker-compose.yml**.
3. Ouvrez **Application settings** et renseignez les deux champs suivants.

| Champ | Valeur à renseigner |
| --- | --- |
| CR_API_TOKEN | Votre clé API obtenue sur le [portail développeur Clash Royale](https://developer.clashroyale.com/). |
| CLAN_TAG | Le tag de votre clan, visible dans Clash Royale, avec le **#** initial. |

La clé API est un code d'accès privé, pas votre mot de passe de jeu. Connectez-vous
au portail développeur, créez une clé et autorisez l'adresse IP publique de
l'ordinateur qui exécutera l'application. Si vous ne connaissez pas cette
adresse, demandez de l'aide. Un changement de connexion, un VPN ou un changement
d'adresse par votre opérateur peut nécessiter de modifier l'adresse autorisée.

Conservez les autres valeurs par défaut. Le fuseau horaire proposé est
Europe/Paris ; changez-le seulement si vous souhaitez programmer les tâches
dans un autre fuseau. **DISCORD_WEBHOOK_URL** est facultatif : laissez-le vide,
sauf si vous voulez des rapports quotidiens et disposez déjà d'un webhook pour
votre salon Discord.

Le lanceur crée automatiquement le fichier de configuration. Vous n'avez pas
besoin de modifier un fichier caché. Validez la fenêtre de configuration puis
cliquez sur **Start and open**. Le premier démarrage télécharge et prépare
l'application ; cela peut prendre plusieurs minutes. Attendez la fin :
cliquer plusieurs fois n'accélère pas le démarrage.

Tout est prêt quand **Clash Royale Clan Manager** s'affiche dans votre navigateur
et que les pages s'ouvrent. L'adresse [localhost:8501](http://localhost:8501)
désigne votre propre ordinateur.

### 4. Utilisation quotidienne

Ouvrez Docker, puis le lanceur, et cliquez sur **Start and open**.

| Vous voulez… | Ouvrez… |
| --- | --- |
| Voir la situation générale du clan | **Overview** |
| Trouver un membre ou filtrer les rôles | **Members** |
| Consulter le profil et la progression d'un joueur | **Player** |
| Examiner les scores et suggestions de promotion | **Promotions** |
| Suivre la semaine actuelle et les guerres passées | **Wars** |
| Vérifier ou programmer les tâches automatiques | **Settings** |

Dans **Overview**, **Refresh Clan Members** actualise les membres et
**Refresh War Data** actualise les guerres. **Recalculate Contribution Scores**
recalcule les scores à partir des données collectées. Attendez le résultat avant
de recommencer. Actualiser uniquement le navigateur ne force pas une nouvelle
récupération depuis l'API.

Le message « Training days » est normal : les trois jours d'entraînement ne
comptent pas comme des attaques de guerre manquées. Les anciens résultats restent
disponibles. Après une première installation, l'historique est limité ; les
graphiques se remplissent au fil des collectes.

Dans **Settings → Scheduler**, conservez les horaires par défaut si vous n'avez
pas de besoin particulier. **Save schedule** applique vos changements sous
environ cinq secondes. Pour les collectes et rapports automatiques, l'ordinateur
doit rester allumé et éveillé, Docker ouvert et l'application en fonctionnement.
Aucune collecte n'est possible lorsque l'ordinateur est éteint.

### 5. Fermer et rouvrir

| Action | Résultat |
| --- | --- |
| Fermer l'onglet du navigateur ou la fenêtre du lanceur | Les tâches continuent en arrière-plan. |
| Dans la barre latérale : **Close → Dashboard only** | Le tableau de bord s'arrête, les tâches continuent. Rouvrez avec **Start and open** dans le lanceur. |
| **Close → Everything** ou **Stop all** dans le lanceur | Tout s'arrête ; les données enregistrées sont conservées. |
| Éteindre ou mettre l'ordinateur en veille | La collecte s'interrompt jusqu'à ce qu'elle puisse reprendre. |

Après avoir choisi une option dans **Close**, cliquez sur **Confirm close**
pour confirmer ; **Cancel** laisse l'application en fonctionnement.

Pour tout arrêter et libérer le port réseau de l'application, utilisez **Stop all**.
Docker peut signaler un tableau de bord indisponible si vous avez volontairement
gardé seulement les tâches automatiques. Rouvrez le tableau de bord pour rétablir
son état de santé.

### 6. Mettre à jour et conserver ses données

**Update application ne télécharge pas une nouvelle version.** Récupérez d'abord
les nouveaux fichiers auprès du responsable du projet.

1. Cliquez sur **Stop all**.
2. Copiez tout le dossier actuel dans un endroit sûr, y compris les fichiers
   cachés. Cette sauvegarde contient votre configuration privée et votre historique.
3. En suivant les instructions du responsable, remplacez les fichiers du programme
   par la nouvelle version. Conservez vos **.env**, **data**, **backups** et **logs**.
   Gardez le même nom et le même emplacement pour le dossier de l'application.
4. Installez aussi le nouveau lanceur correspondant, s'il est fourni.
5. Ouvrez le lanceur, cliquez sur **Update application** et attendez la fin.

Ne partagez pas votre dossier de sauvegarde : il contient votre clé API.
Les sauvegardes automatiques de la base se trouvent dans **backups** lorsque
l'application fonctionne ; elles n'incluent pas tout le programme ni sa
configuration. Pour restaurer, demandez au responsable de suivre la
[procédure technique](../README.md#backup-and-restore). Il n'existe pas
d'assistant graphique de restauration.

### En cas de problème

| Problème | Que faire ? |
| --- | --- |
| Docker indisponible | Ouvrez Docker Desktop et attendez qu'il soit prêt. Sur Linux, faites vérifier les autorisations. |
| Dossier introuvable | Choisissez le dossier décompressé contenant docker-compose.yml, pas une archive ou le seul lanceur. |
| Le navigateur ne se connecte pas | Cliquez sur **Start and open**, attendez et vérifiez que Docker fonctionne. |
| Accès refusé / 403 | Vérifiez la clé API et l'adresse IP publique qu'elle autorise. |
| Données anciennes | Consultez **Settings → Job Health**, puis utilisez le bouton d'actualisation adapté. |
| Graphiques vides | Laissez la collecte fonctionner ; certains graphiques demandent plusieurs jours d'historique. |
| Port déjà utilisé | Arrêtez une autre instance de Clan Manager ; demandez de l'aide si une autre application utilise ce port. |
| Disque plein | Libérez de l'espace puis réessayez. Ne supprimez pas votre dossier data. |

Pour obtenir de l'aide, transmettez le message d'erreur, votre système, la version
de l'application et les étapes suivies. Ne transmettez jamais votre clé API,
webhook Discord ou fichier **.env**. Utilisez le tableau de bord sur un ordinateur
et un réseau de confiance : il n'a pas d'écran de connexion.
