# WhatDropsHere – Konzept

Stand: 01.11.2026

## Ziel

Eine persönliche Drop-Statistik pro Beutequelle (Rohstoffvorkommen, Behälter, Leichen, Taschendiebstahl).
Beim Anvisieren einer Quelle steht neben dem Fadenkreuz, was diese Quelle mir bisher gegeben hat.

Keine vollständige Loot-Tabelle wie in WoW: In ESO droppt fast alles fast überall, und Materialstufen hängen vom Level ab.
Der Mehrwert sind die eigenen Zahlen, z. B.:

> *Schwere Truhe (Vvardenfell) – 47× geöffnet · 3× Set-Item (Gold) · 1× Stilseite*
> *Eisenerz – Ø 3,4 · 8 % Stilmaterial · 2 % Härtungsmittel*

## Abgrenzung zu vorhandenen Addons

| Addon | Was es macht | Was fehlt |
|---|---|---|
| LootLog | durchsuchbares Protokoll aller Beute, Set-Erkennung | keine Quelle |
| Votan's Fisherman | Fischgründe: Position, Köder, Fang am Fadenkreuz | nur Fischgründe |
| RareFishTracker | seltene Fische pro Zone (über Errungenschaften) | keine Quellen, keine Positionen |
| HarvestMap | Positionen von Vorkommen, Truhen, schweren Säcken, Diebeshorten | keine Beute |
| Farming Party Plus, LWT Loot Tracker, GREED | Beute pro Session, Spieler oder Gruppe | keine Quelle |
| LootDrop Reborn | Beute-Einblendung als Stapel am Bildschirmrand | keine Quelle, keine Statistik |
| Advanced Loot Tracker | Beute von dir und der Gruppe, Filter nach Qualität und Name | keine Quelle |
| Filtered Loot Tracker | Beute von dir und der Gruppe, frei konfigurierbare Filter | keine Quelle |
| Loot Tracker Solution | Beute- und Goldstatistik mit TTC/MM-Preisen, Kategorien über `GetItemLinkFilterTypeInfo` | keine Quelle |
| LibLootSummary | Bibliothek für Beute-Zusammenfassungen im Chat | (nützlich für die Debug-Ausgabe) |

Alle geprüften Tracker hören nur auf `EVENT_LOOT_RECEIVED`. Dieses Event enthält keine Quelle; keiner nutzt
`GetLootTargetInfo()` oder das Fadenkreuz (geprüft am 01.11.2026).
Die Kombination *Quelle → Beute* mit Anzeige am Fadenkreuz ist damit weiterhin neu.

## Erfassung

- `EVENT_LOOT_UPDATED` + `GetLootTargetInfo()` → Name der Quelle
- `GetNumLootItems()` / `GetLootItemInfo(i)` / `GetLootItemLink(i)` → Items, Anzahl, Qualität, Typ
- `EVENT_LOOT_RECEIVED` → Fälle ohne Lootfenster (Taschendiebstahl über `isPickpocketLoot`, Auto-Loot)
- Bei Auto-Loot: letztes Interaktionsziel merken und Beute innerhalb eines kurzen Zeitfensters zuordnen

### Zusammenspiel mit Auto-Loot-Addons

Geprüft: Much Smarter AutoLoot (MSAL) 6.1.1 und Smarter AutoLoot 1.8.0 (je nach Charakter aktiv).

- Beide hören auf `EVENT_LOOT_UPDATED`, rufen `LootItemById()` für die gewünschten Items auf und schließen mit `EndLooting()`.
- MSAL drosselt nur (Latenz + 100 ms zwischen zwei Durchläufen), es verzögert nicht. Smarter AutoLoot handelt sofort.
- `LootItemById()` ist eine Anfrage an den Server. Im selben Event-Durchlauf ist die Lootliste noch vollständig lesbar,
  egal ob unser Handler vor oder nach dem Auto-Loot-Addon läuft. (Im Spiel bestätigen.)
- `EVENT_LOOT_UPDATED` feuert nach jedem genommenen Item erneut mit kürzerer Liste.

**Strategie: erfassen, was die Quelle *angeboten* hat, nicht was genommen wurde.**

1. Eine Plünder-Sitzung beginnt mit dem ersten `EVENT_LOOT_UPDATED` und endet mit `EVENT_LOOT_CLOSED`.
2. Beim ersten Update: Quelle (`GetLootTargetInfo()`) und komplette Liste sichern.
3. Bei weiteren Updates: nur `lootId`s hinzufügen, die noch nicht gesehen wurden.
4. Bei `EVENT_LOOT_CLOSED`: Sitzung in die Datenbank schreiben.

So verfälschen die Filter des Auto-Loot-Addons die Statistik nicht: Was liegen bleibt, wird trotzdem gezählt.
`EVENT_LOOT_RECEIVED` dient nur als Ersatz für Fälle ohne Lootliste (Taschendiebstahl).

### Beute ohne Lootfenster („Nehmen")

Kleintiere (Insekten, Quallen, Motten, Schmetterlinge …) und einzelne Gegenstände werden mit „Nehmen" eingesammelt,
ohne Kampf und ohne Lootfenster. Sie liefern Köder und Handwerkswaren (z. B. Schmetterlingsflügel).

- Beim Drücken der Interaktionstaste wird das Ziel gemerkt: Hook auf `INTERACTIVE_WHEEL_MANAGER:StartInteraction`
  (Tastatur und Gamepad rufen das laut `bindings.xml` vor `GameCameraInteractStart` auf), Name aus `GetGameCameraInteractableActionInfo()`.
- `EVENT_LOOT_RECEIVED` innerhalb von 3 Sek. danach, ohne offenes Lootfenster → gehört zu diesem Ziel.
- Alle Items einer Interaktion bilden eine Sitzung; gespeichert wird 1 Sek. nach dem letzten Item.
- Taschendiebstahl nutzt dieselbe gemerkte Interaktion als Opfernamen (vorher: Ziel unter dem Fadenkreuz).

### Erneut geöffnete Quellen (Reste im Lootfenster)

MSAL kann so eingestellt werden, dass nur ein Teil automatisch genommen wird; der Rest bleibt im Lootfenster.
Schließt man es und öffnet dieselbe Leiche/Truhe erneut, würde dieselbe Beute ein zweites Mal gezählt.

- Die `lootId`s der letzten Lootfenster-Sitzung werden gemerkt.
- Öffnet man danach eine Quelle mit demselben Namen und tauchen dort bekannte `lootId`s auf, gilt sie als erneut geöffnet:
  bekannte Einträge und Gold werden nicht erneut gezählt. Ohne neue Einträge wird gar nichts gespeichert (Debug: „erneut geöffnet").
- Zwei verschiedene Leichen mit gleichem Namen werden weiterhin getrennt gezählt, weil ihre `lootId`s verschieden sind.
- Einschränkung: Erkannt wird nur die **zuletzt** geöffnete Quelle. A öffnen, B öffnen, zurück zu A → A zählt doppelt.

### Flächenplündern (AoE-Loot)

MSAL schaltet die Spieleinstellung `LOOT_SETTING_AOE_LOOT` **ein** (und das eingebaute Auto-Loot aus).
Damit landen die Leichen in der Nähe in **einem** Lootfenster, `GetLootTargetInfo()` liefert aber nur **einen** Namen.
Genau das Problem „Weltboss + namenlose Adds".

- Beim Speichern `GetSetting(SETTING_TYPE_LOOT, LOOT_SETTING_AOE_LOOT)` mitprüfen.
- Eine Plünderung mit AoE-Loot als **Sammelplünderung** markieren und getrennt speichern
  (z. B. „Weltboss X + Umgebung"), statt sie dem einen Namen gutzuschreiben.
- Option im Menü: „Sammelplünderungen in die Statistik einbeziehen" (aus/ein).
- Wer genaue Zahlen will, kann AoE-Loot in den Spieleinstellungen abschalten. MSAL setzt es aber beim Laden ggf. wieder.

**Schlüssel einer Quelle:** Name + Zone (`zoneId`). ESO liefert keine eindeutige ID pro Objekt; alle „Eisenerz"-Vorkommen einer Zone landen bewusst im selben Eintrag.

## Kategorien

**Seit Datenversion 2 (06.11.2026): Jeder Fund wird mit Item-ID gespeichert**, zusätzlich seine Kategorie
und bei Set-Ausrüstung das Set. Ob ein Item mit Namen oder als Kategorie erscheint, entscheidet erst die Anzeige.
Damit wirkt jede Anzeige-Einstellung auch rückwirkend. (Vorher wurde nur ab einer Speicher-Schwelle die Item-ID
gespeichert, darunter nur die Kategorie; das ließ sich nachträglich nicht mehr aufschlüsseln.)

Anzeige-Modus je Kategorie (`CAT.ModeOf`):

| Immer mit Namen (DETAIL) | Mit Namen ab Schwelle (DETAIL_Q) | Immer als Kategorie (COUNT) |
|---|---|---|
| Einrichtung, Baupläne, Stilbücher, Stilseiten | Rezepte, Behälter | Ausrüstung ohne Set, Gefährten-Ausrüstung |
| Schatzkarten, Vermessungsberichte, Trophäen | alle Handwerksmaterialien, Härtungsmittel | Schätze, Trash |
| Sammlungsstücke, Spuren | Reagenzien, Lösungsmittel, Zutaten, Runen | Köder, Tränke, Essen, Glyphen, Werkzeug |

Set-Ausrüstung erscheint zusammengefasst pro Set (setId + Platz).

- Set-Items: **setId** speichern, nicht den Namen. Der Name wird bei der Anzeige in der eingestellten Sprache geholt.
- Keine kompletten Itemlinks speichern, nur Item-ID, Zähler, Qualität und Kategorie.
- Größe: grob 100–150 Byte pro Item und Quelle in der Speicherdatei. Bei 10–30 verschiedenen Items pro Quelle
  sind 1000 Quellen etwa 2–5 MB; unkritisch (HarvestMap und Master Merchant speichern deutlich mehr).

### Stoff und Leder

Das Spiel unterscheidet Stoff und Leder nicht über den Itemtyp (beides `ITEMTYPE_CLOTHIER_(RAW_)MATERIAL`).
`WDH_Categories.lua` führt deshalb eine Liste der 20 Leder-IDs (roh und veredelt, alle Stufen; Quelle: CraftingMaterialLevelDisplay)
→ `MAT_LEATHER`, alles andere Schneidermaterial → `MAT_CLOTH` (Stoff). Daten von vor dieser Änderung stehen gemischt unter „Stoff".

### Zwei Schwellwerte (beide nur für die Anzeige)

1. **Anzeigen ab Qualität** (`showQuality`): darunter erscheint ein Eintrag gar nicht am Fadenkreuz
2. **Mit Namen anzeigen ab Qualität** (`nameQuality`): darunter erscheinen Items der DETAIL_Q-Kategorien in ihrer Kategorie

### Rohstoffe

Pro Quelle:
- Anzahl der Plünderungen
- Hauptrohstoff: Minimum, Maximum, Summe (→ Durchschnitt)
- Beifang: Zähler pro Kategorie (Köder, Stilmaterial, Härtungsmittel …)
- Runensteine über `ITEMTYPE_ENCHANTING_RUNE_*`

## Anzeige am Fadenkreuz

- Hook nach dem Vorbild von Votan's Fisherman: `ZO_PreHookHandler(RETICLE.interact, "OnEffectivelyShown", …)`.
  Wird nur aufgerufen, wenn der Interaktionstext sichtbar ist. Idee übernehmen, Code nicht kopieren, Votan im Kommentar danken.
- Ziel auslesen mit `GetGameCameraInteractableActionInfo()` (Vorkommen, Behälter, Leichen).
- Label an `RETICLE.interactContext` verankern.
- Im Kampf ausblenden: `EVENT_PLAYER_COMBAT_STATE` / `IsUnitInCombat("player")`.
- Lebende NPCs (`reticleover`) erst später; die Erkennung hat Lücken (siehe CompanionRapportCooldown) und im Kampf wird ohnehin ausgeblendet.

**Umsetzung (Phase 2, `WDH_Hud.lua`):**
- Statt des Hooks von Votan: `SecurePostHook(RETICLE, "TryHandlingInteraction", …)`. Läuft jedes Bild, solange kein Lootfenster offen ist;
  der Text wird nur neu gebaut, wenn sich Ziel oder Daten ändern.
- Label als Kind von `RETICLE.interact`, unter `RETICLE.additionalInfo` (Schlossstufe o. ä.) verankert → verschwindet automatisch mit der Interaktionsanzeige.
- Inhalt: Kopfzeile „12x geplündert · Ø 4 Gold", dann Einträge ab Anzeige-Schwelle, sortiert nach Qualität und Anzahl,
  je Eintrag Anzahl und Anteil der Plünderungen in %. Höchstens 6 Einträge, Rest als „+N weitere (/wdh name)".
- Befehle: `/wdh_hud` (an/aus), `/wdh_show 0-5` (Anzeige-Schwelle, Standard 1 = ab weiß).

**Lebende Ziele (vorgezogen aus Phase 5):**
- Zweites Label für `reticleover` (kein Spieler, nicht tot), nur wenn keine Interaktionsanzeige sichtbar ist.
  Aktualisiert per `SecurePostHook(RETICLE, "UpdateInteractText", …)`, Elternteil `RETICLE.control`, Position unter `RETICLE.interact`.
- Nur eindeutige Zuordnungen (Name + Zone); Sammelplünderungen (`#aoe`) werden hier nicht gezeigt.
- Im Kampf ausgeblendet; die Anzeige ist also vor allem beim Anschleichen bzw. Anvisieren aus der Distanz sichtbar.
- Befehl `/wdh_units` (an/aus).

## Einstellungsmenü und Art der Quelle

`WDH_Menu.lua` (LibAddonMenu-2.0, optional; ohne Bibliothek bleiben die Slash-Befehle). Grundsatz:
**Anzeige-Einstellungen filtern nur die Anzeige, gespeichert wird immer alles.**

Art der Quelle (`rec.type`), erkannt beim Plündern:
- `enemy`: `IsGameCameraInteractableUnitMonster()` beim Öffnen des Lootfensters bzw. beim Druck auf E
  (so ermittelt auch das Spiel den Plündersound in `ZO_PlayLootWindowSound`)
- `resource`: `GetInteractionType() == INTERACTION_HARVEST` in den 3 Sek. nach dem Druck auf E (Abfrage alle 100 ms, wie HarvestMap)
- `container`: alle übrigen Lootfenster (Truhen, Säcke, Fässer, Kisten, Rucksäcke …)
- `theft`: Quelle gehört jemandem (`isOwned` aus `GetLootTargetInfo()` bzw. `GetGameCameraInteractableActionInfo()`).
  Eigener Schlüssel `name#theft`, damit eine gestohlene „Kiste" die freien Kisten nicht verfälscht.
  Die Anzeige sucht bei einem fremden Ziel am Fadenkreuz den `#theft`-Eintrag.
- `other`: Taschendiebstahl und „Nehmen" ohne Lootfenster
- `container` ist der Rückfall und überschreibt eine einmal erkannte Art nicht. Alte Einträge ohne Art werden immer angezeigt.

## Koordinaten

- **Nur für feste, seltene Quellen:** Truhen, schwere Säcke, Diebeshorte, Weltbosse.
- **Nicht** für Fässer, Kisten, Urnen, normale NPCs und Tiere (zu viele, NPCs laufen herum, wenig Nutzen).
- Keine Triangulation nötig: Votan's Fisherman trianguliert, weil Fischgründe weit weg liegen. Behälter plündert man aus 2–3 m, die eigene Position (LibGPS) reicht.
- Vorher prüfen, ob HarvestMap das schon abdeckt, um doppelte Arbeit zu vermeiden.

## Hilfsbibliotheken

- **LibSets:** Dropzonen (`GetDropZonesBySetId`) und Dropart (`GetDropMechanic`) pro Set → „ungewöhnlicher Drop" markieren, wenn ein Set hier eigentlich nicht hingehört.
- **LibAddonMenu-2.0:** Einstellungen
- **LibGPS:** nur für Phase 4
- **LibLeadDrop** (CC BY-SA 2.5, Daten von UESP): pro Antiquität die Dropzonen (`GetLeadDropZones`) und ein Hinweistext,
  woher die Spur kommt (`getLeadDropHint`, mit Quell-Link). Später nutzbar, um eigene Spurenfunde mit den UESP-Angaben
  zu vergleichen oder im Tooltip anzuzeigen. Nur zur Laufzeit abfragen, nicht mitliefern (sonst gelten Namensnennung und ShareAlike).
- **Spuren:** Im Lootfenster gibt es keine Antiquitäten-ID. `EVENT_LOOT_RECEIVED` liefert sie bei
  `lootType == LOOT_TYPE_ANTIQUITY_LEAD` im Parameter `itemId` (so machen es LootDrop und LootLog).
- **UespLog:** nicht nötig. Es ist ein Sammler, der zur UESP hochlädt, und liefert keine Item-Datenbank für das Spiel. Alle Infos kommen aus dem Itemlink (`GetItemLinkSetInfo`, `GetItemLinkItemType`, `GetItemLinkEquipType`, `GetItemLinkDisplayQuality`, `GetItemLinkFurnitureDataId`, `IsItemLinkSetCollectionPiece`).

## Testergebnisse

**01.11.2026, Vvardenfell, mit MSAL, Flächenplündern an:**
- Erfassung und Kategorien funktionieren bei Vorkommen (Holz, Erz, Runenstein), Tier und NPC-Leiche.
- Beifang wird erkannt (Kernholz, Regulus, Platinstaub, Weltliche Rune).
- `targetType` war bei **allen** Quellen 1 (Vorkommen, Tier, NPC). Der Typ unterscheidet die Quellenarten also nicht.
- Einmal kam kein `EVENT_LOOT_CLOSED`. Deshalb wird eine Sitzung jetzt auch nach 5 Sek. ohne Update
  (wenn das Lootfenster nicht sichtbar ist) und vor einem Ladebildschirm gespeichert.
- Gold war überall 0, auch beim Banditen. Jetzt wird es wie bei MSAL über `LOOT_SHARED:GetLootCurrencyInformation()` gelesen.

**01.11.2026, zweiter Test (Vvardenfell, MSAL):**
- **Gold funktioniert** über `LOOT_SHARED` (Netchgauner-Eisenhaut: 49 Gold). Die anderen Quellen hatten wirklich keins.
- **Kleintiere funktionieren** („Nehmen" → Köder).
- **Fass** lief über den Weg ohne Lootfenster (`targetType=nil`), Schwerer Sack und Trinkschlauch dagegen mit Lootfenster.
  Die Zuordnung stimmte trotzdem. Beide Wege landen im selben Eintrag, weil der Schlüssel nur der Name ist.
- „Neues Ziel ohne LOOT_CLOSED" kam wieder nach einem **Runenstein** (wie beim ersten Mal nach Rubediterz). Wird abgefangen.
- Keine Meldung „Beute ohne Lootfenster" mehr.
- Noch nicht getestet: Flächenplündern mit mehreren Leichen, Spuren, Taschendiebstahl, Set-Drops.

**01.11.2026, dritter Test (Vvardenfell, MSAL):**
- `EVENT_LOOT_RECEIVED` kommt **nach** `EVENT_LOOT_CLOSED` (MSAL schließt das Fenster, bevor der Server die Items bestätigt).
  Deshalb ist es richtig, die angebotene Liste zu zählen und nicht den Empfang. Spuren werden über denselben Weg
  nachträglich der letzten Quelle zugeordnet.
- Die Debug-Meldung „kurz nach Lootfenster" kam dadurch für jedes Item. Jetzt nur noch, wenn das Item **nicht** in der Lootliste stand.
- **Zunderfliege** (Kleintier, „Nehmen") öffnet ein Lootfenster (`targetType=1`), anders als Fässer im zweiten Test.
- Denata (blau) wird wie gewollt ab Speicher-Schwelle einzeln gespeichert.

**01.11.2026, vierter Test (Eiermine von Matus-Akin, Gruppe Grollgarde-Rüpel, Flächenplündern an):**
- Gruppe erst komplett besiegt, dann geplündert (alle Leichen dicht beieinander). Trotzdem hatte jede Leiche ein
  **eigenes** Lootfenster mit eigenem Inhalt, `AoE-Ziel=false`, `targetType=1`.
  Kein Hinweis darauf, dass Beute mehrerer Leichen in einem Fenster zusammengefasst wurde.
- Mehrere „Interaktion: Durchsuchen" ohne Lootfenster = im Kampf unterbrochene Versuche. Werden nicht gespeichert.
- Da alle Gegner gleich hießen, ist die Zuordnung hier ohnehin eindeutig.
- Offen: Wie Flächenplündern in ESO genau wirkt (ein Fenster für alle oder Beute der Nachbarn direkt ins Inventar).
  Neue Debug-Zeile „Beute während Lootfenster, aber nicht in dessen Liste" macht den zweiten Fall sichtbar.
- Nächster Test: zwei **verschiedene** Gegnertypen dicht beieinander erledigen, dann einen plündern.

## Beta 0.2.0 (06.11.2026)

Veröffentlichung als Beta, weil vieles allein nicht absehbar testbar ist. Debug-Ausgabe ist ab dieser Version
standardmäßig aus (bestehende Einstellungen bleiben). Nur deutsche Texte.

**Todos nach der Beta:**
- [ ] **Datenbanken extern zusammenführen** (ähnlich HarvestMapData): Skript außerhalb des Spiels, Ergebnis als
      „Gemeinschaftsdaten" getrennt von den eigenen Daten. Hürde: Quellen sind über den Namen gespeichert (sprachabhängig).
- [ ] **Anzeige feiner steuern**, z. B. für Rohstoffe Minimum–Maximum pro Plünderung statt Gesamtmenge
      (`min`/`max` werden seit Phase 1 je Kategorie und Item gespeichert). Entspricht Phase 3.
- [ ] **Heatmap** für bestimmte Rohstoffe/Set-Items zum Farmen. Braucht Positionen (Phase 4) zumindest grob,
      z. B. pro Karte in Raster-Zellen statt exakter Koordinaten.
- [x] Englische Texte (`lang/en.lua` als Standard, `lang/de.lua` überschreibt; Manifest mit `$(language)`), seit 0.3.0-beta.

**Ideen für später:**
- Normal/Veteran in Verliesen und Prüfungen unterscheiden (`GetCurrentZoneDungeonDifficulty()`), gleiche Zonen-ID.
- Statistiken teilen: Datei tauschen + Skript zum Zusammenführen als „Gemeinschaftsdaten" (getrennt von eigenen Daten).
  Hürde: Quellen sind über den Namen gespeichert, also sprachabhängig. Server wie bei HarvestMapData nur bei vielen Nutzern.

## Offene Fragen (im Spiel prüfen)

- [ ] Ist die Lootliste vollständig lesbar, wenn MSAL bzw. Smarter AutoLoot im selben Event schon `LootItemById()` aufgerufen hat?
- [ ] Welchen Namen liefert `GetLootTargetInfo()` bei einer Sammelplünderung (AoE-Loot)? Den der angeklickten Leiche?
- [ ] Gibt es bei AoE-Loot irgendeinen Hinweis, wie viele Leichen beteiligt waren?
- [ ] Fadenkreuz: Erscheint die Anzeige bei Vorkommen, Behältern, Leichen und Kleintieren? Passt die Position, stört sie?
- [ ] Art der Quelle: Stimmt `Art=` im Debug für Leichen (enemy), Vorkommen und Runensteine (resource), Truhen/Säcke (container)?
      Wohin fallen Kleintiere mit Lootfenster (Zunderfliege)?
- [ ] Taschendiebstahl noch nicht getestet.
- [ ] Diebstahl aus fremden Behältern: Erscheint `[Diebstahl]` bzw. `Art=theft`? Auch beim Stehlen einzelner Gegenstände ohne Lootfenster?
- [ ] Erneut geöffnete Quelle: Bleiben die `lootId`s beim zweiten Öffnen gleich? (Debug muss „erneut geöffnet" zeigen.)
- [ ] Lebende Ziele: Erscheint die Anzeige beim Anvisieren? Welche Gegner werden nicht erkannt (vgl. CompanionRapportCooldown)?
- [ ] Fadenkreuz: Stimmt der Name am Fadenkreuz mit dem Namen im Lootfenster überein (z. B. bei Leichen)?
- [ ] **Rucksack** („Nehmen") wurde nicht erfasst. Vermutung: Lootfenster ohne Namen der Quelle → Sitzung wurde stillschweigend verworfen.
      Jetzt: Rückfall auf den Namen der letzten Interaktion, dazu Debug-Zeilen „Interaktion: …", „ohne Namen verworfen", „kurz nach Lootfenster".
- [ ] Kleintiere: Wird die Beute nach „Nehmen" dem richtigen Tier zugeordnet? Wie heißt die Quelle (Tiername)?
- [ ] Bleibt die Meldung „Beute ohne Lootfenster" danach noch für etwas anderes als Quest- oder Belohnungs-Items?
- [x] Gibt es `INTERACT_TARGET_TYPE_AOE_LOOT`? Ja, laut ESOUIDocumentation (API 101051). Im Spiel noch mit mehreren Leichen prüfen.
- [x] Kommt `EVENT_LOOT_RECEIVED` noch während das Lootfenster offen ist oder erst danach? Mit MSAL erst danach.
      Alternative laut API-Doku: `GetLootAntiquityLeadId(lootId)` liefert die ID direkt im Lootfenster.
- [x] `GetLootCurrency(CURT_MONEY)` liefert `unownedCurrency, ownedCurrency` (API-Doku). Trotzdem war Gold im Test 0 → jetzt über `LOOT_SHARED`; im Spiel prüfen.
- [ ] Feuert `EVENT_LOOT_UPDATED` auch beim eingebauten Auto-Loot (ohne Addon)?
- [ ] Wie heißen Leichen am Fadenkreuz („Durchsuchen" + Name)? Gleicht der Name dem Lootfenster?
- [ ] Wie verhalten sich Taschendiebstahl, Diebeshorte und Safes?
- [ ] Wo trennt man „seltene" von „normalen" Materialien sauber über Itemtyp / Specialized Itemtype?

## Reihenfolge

1. Beute erfassen und kategorisieren, Name + Zone als Schlüssel, Debug-Ausgabe im Chat
2. Anzeige am Fadenkreuz für Vorkommen, Behälter und Leichen, Ausblenden im Kampf, Qualitätsschwellen
3. Mengenstatistik für Rohstoffe und Beifang
4. Koordinaten für feste Quellen, nur falls HarvestMap das nicht abdeckt
5. Später: lebende NPCs, Taschendiebstahl je NPC-Typ
