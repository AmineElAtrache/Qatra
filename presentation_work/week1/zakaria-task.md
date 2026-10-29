# Script de présentation — Membre 5 : Explication, QA et Ops

Bonjour. Dans le projet Qatra, je suis responsable de la partie explication, assurance qualité et opérations.

Qatra calcule d’abord ses recommandations avec le moteur agronomique. Mon rôle est de rendre ces résultats compréhensibles pour l’agriculteur, sans modifier les calculs ni inventer de chiffres.

Pour cela, le MVP transforme les données d’une recommandation en explications en français, en arabe et en Darija. Les nombres affichés viennent directement du résultat validé. Par exemple, si la dose n’est pas fiable et que le statut est « à vérifier », le système n’affiche pas de dose précise.

J’ai aussi travaillé sur Ask Qatra, l’assistant de questions-réponses. L’agriculteur peut poser une question sur l’irrigation, le risque fongique ou le traitement. La réponse s’appuie sur sa dernière recommandation et sur les documents de référence FAO et INRA intégrés au projet.

Un point important du MVP est sa robustesse : les explications affichées reposent sur des modèles de texte prédéfinis. Le système peut tenter un appel à Ollama, mais il utilise actuellement les templates dans tous les cas. Qatra peut donc fournir ses textes même lorsque le modèle est indisponible, ce qui permet une démonstration hors ligne.

Ma partie comprend également les vérifications qualité. Les tests contrôlent la présence des trois langues, la cohérence des chiffres, le masquage de la dose quand les données doivent être vérifiées, ainsi que les réponses aux questions et l’utilisation des références.

En résumé, mon travail fait le lien entre les résultats techniques de Qatra et les besoins de l’agriculteur : expliquer clairement, répondre à ses questions et rester fiable même lorsque le modèle d’IA n’est pas disponible. Merci.

## Démonstration rapide

1. Afficher une recommandation avec une dose disponible et ses explications dans les trois langues.
2. Afficher un cas « à vérifier » et montrer que la dose précise est masquée.
3. Poser une question sur l’irrigation dans Ask Qatra et montrer que la réponse reprend les données de la dernière recommandation.
