# Corpus Python 2 : pièges non détectés par les règles

| Projet | Ligne | Piège | Comportement en Python 3 |
|---|---|---|---|
| inventory | 24 | `sum(prices) / len(prices)` | Division entière en Python 2 (résultat 2), flottante en Python 3 (2.5) |
| textstats | 14 | `string.lower(text)` | Fonction supprimée, AttributeError |
| textstats | 22 | `pairs.sort(lambda a, b: cmp(...))` | Le tri par cmp n'existe plus (utiliser `key=`), `cmp()` n'existe plus |
| textstats | 41 | `file(path, "wb")` | `file()` n'existe plus (utiliser `open`), NameError |
| bank | 18 | `__cmp__` | Ignoré en Python 3, `a > b` lève TypeError (utiliser `__lt__`, etc.) |
| bank | 21 | `__unicode__` | Doit devenir `__str__` |
| bank | 29 | `self.balance * 3 / 100` | Renvoie 21 en Python 2, 21.0 en Python 3 |