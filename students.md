# Programmation de la gestion de l'irrigation

On a deux ordinateurs:
* un local qui collecte les données du terrain
* un serveur (virtuel) de l'université où les données sont recopiées et qui permet d'exécuter des programmes décidant quand il faut arroser

Selon que vous êtes du groupe 1, 2 ou 3, vous vous intéressez aux fichiers et répertoires dont le nom se termine par 1, 2 ou 3.

Dans GitHubn sarahgarre/WatWall/gw2, par exemple, le groupe 2 mettra son programme Python dans le fichier wat2.py . Un embryon est déjà là:
ne pas l'abîmer car il assure que votre programme ne fonctionne qu'à un exemplaire et peut être arrếté au besoin.

# Branchement au serveur greenwall.gembloux.uliege.be

On a défini trois utilisateurs (gw1, gw2, gw3) avec leur mot de passe. Le branchement se fait avec tout ordinateur doté d'un logiciel "rsh" (par exemple PuTTY sous Windows, rsh sous Linux).

On se branche au serveur, par exemple:

> rsh gw2@greenwall.gembloux.uliege.be

et on donne son mot de passe (communiqué séparément par votre professeur)

# Création de votre programme

Votre programme doit être en langage Python et se nommer watX.py (X=1, 2 ou 3)

Il faut le mettre dans le projet GitHub sarahgarre/WatWall/gwX  (X=1, 2 ou 3).

L'utilisation de GitHub vous sera montrée lors du Workshop: amenez votre ordinateur portable pour qu'on puisse vous aider à démarrer.

# Exécution de votre programme

On obtient alors un terminal en "lignes de commande" où nous avons défini des commandes pour vous simplifier la vie:
* ./upd.sh    ce script permet de ramener TOUTES les modifications de TOUS les groupes depuis GitHub.
* ./clean.sh  ce script arrête complètement votre programme
* ./run.sh    ce script arrêter votre programme s'il fonctionne et le redémarre. Votre programme est en arrière plan et vous pouvez vous déconnecter.
* ./look.sh   permet de voir ce qu'il y a dans le fichier qui sera envoyé pour le contrôle des valves (valve.txt) et les messages d'erreur éventuels de votre programme en arrière plan (nohup.out)
* cat watX.py     (X=1, 2 ou 3) permet de voir votre programme sur le serveur.

Le fichier "valve.txt" doit contenir vos commandes d'ouverture et de fermeture des vannes.

Il se compose de lignes indépendantes chacune indiquant un "timestamp", un point virgule de séparation, 0 ou 1 (fermé / ouvert) et une fin de ligne ( \\n )

Par exemple:
> 1580906117;1
> 1580906177;0

Le timestamp est le nombre de secondes depuis le 01/01/1970. Il se calcule avec les fonctions du module "time".

Nous vous avons mis un exemple de "watX.py" pour commencer.
