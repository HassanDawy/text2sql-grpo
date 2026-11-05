# SFT correct -> GRPO wrong (36 questions, BIRD dev)

## Summary (first-pass labels by Claude, check before citing; n = 36, counts only)

- wrong table/join: 10
- value format: 4
- wrong column: 4
- ambiguous: 4
- benchmark issue: 4
- over-complicated: 3
- ignored question: 3
- grouping/DISTINCT: 2
- lucky SFT: 1
- ignored hint: 1

## 1. q14 (simple, california_schools) -> GRPO error (no such column: Enrollment (Ages 5-17))

**Question:** List the top five schools, by descending order, from the highest to the lowest, the most number of Enrollment (Ages 5-17). Please give their NCES school identification number.

**Hint:** None

**SFT (correct):**
```sql
SELECT DISTINCT T1.NCESSchool FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode ORDER BY T2.`Enrollment (Ages 5-17)` DESC LIMIT 5
```

**GRPO:**
```sql
SELECT NCESSchool FROM schools ORDER BY `Enrollment (Ages 5-17)` DESC LIMIT 5
```

**Gold:**
```sql
SELECT T1.NCESSchool FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode ORDER BY T2.`Enrollment (Ages 5-17)` DESC LIMIT 5
```

**Pattern:** wrong table/join: dropped the needed join and read an frpm column from schools

---

## 2. q71 (simple, california_schools) -> GRPO wrong_rows

**Question:** What is the district code for the School that does not offer a magnet program in the city of Fresno?

**Hint:** When magent is equal to 0 in the database, it means ths school doesn't offer a magnet program.

**SFT (correct):**
```sql
SELECT T1.`District Code` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.City = 'Fresno' AND T2.Magnet = 0
```

**GRPO:**
```sql
SELECT `District Code` FROM frpm WHERE `School Name` = ( SELECT T1.School FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T1.City = 'Fresno' AND Magnet = 0 )
```

**Gold:**
```sql
SELECT T1.`District Code` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.City = 'Fresno' AND T2.Magnet = 0
```

**Pattern:** over-complicated: subquery matching on School Name instead of the direct join

---

## 3. q166 (simple, financial) -> GRPO wrong_rows

**Question:** How many of the accounts are from Jesenik district?

**Hint:** None

**SFT (correct):**
```sql
SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A2 = 'Jesenik'
```

**GRPO:**
```sql
SELECT COUNT(*) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A2 = 'Jesenik'
```

**Gold:**
```sql
SELECT COUNT(T2.account_id) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE T1.A2 = 'Jesenik'
```

**Pattern:** wrong table/join: counted clients instead of accounts

---

## 4. q230 (challenging, toxicology) -> GRPO wrong_rows

**Question:** What are the elements of the toxicology and label of molecule TR060?

**Hint:** TR060 is the molecule id; 

**SFT (correct):**
```sql
SELECT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**GRPO:**
```sql
SELECT T1.element, T3.label FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN molecule AS T3 ON T3.molecule_id = T2.atom_id WHERE T3.molecule_id = 'TR060'
```

**Gold:**
```sql
SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'
```

**Pattern:** wrong table/join: extra join through connected, with molecule_id = atom_id

---

## 5. q308 (simple, toxicology) -> GRPO wrong_rows

**Question:** How many bonds are created by bonding atoms with chlorine element?

**Hint:** chlorine refers to element = 'cl'

**SFT (correct):**
```sql
SELECT COUNT(T2.bond_id) FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T3.bond_id = T2.bond_id WHERE T1.element = 'cl'
```

**GRPO:**
```sql
SELECT COUNT(T1.bond_id) FROM bond AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.element = 'cl'
```

**Gold:**
```sql
SELECT COUNT(T1.bond_id) FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T2.element = 'cl'
```

**Pattern:** wrong table/join: joined bond to atom on molecule_id instead of going through connected

---

## 6. q352 (moderate, card_games) -> GRPO wrong_rows

**Question:** Calculate the percentage of the cards availabe in Chinese Simplified.

**Hint:** Chinese Simplified' is the language; percentage = Divide(Sum(id where language = 'Chinese Simplified'), Count(id)) *100

**SFT (correct):**
```sql
SELECT CAST(SUM(CASE WHEN T2.language = 'Chinese Simplified' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid
```

**GRPO:**
```sql
SELECT CAST(SUM(CASE WHEN T1.language = 'Chinese Simplified' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM foreign_data AS T1 INNER JOIN cards AS T2 ON T1.multiverseid = T2.multiverseId
```

**Gold:**
```sql
SELECT CAST(SUM(CASE WHEN T2.language = 'Chinese Simplified' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid
```

**Pattern:** wrong table/join: joined on multiverseid instead of uuid

---

## 7. q376 (simple, card_games) -> GRPO wrong_rows

**Question:** What are the card layout of cards with keyword of flying?

**Hint:** None

**SFT (correct):**
```sql
SELECT DISTINCT layout FROM cards WHERE keywords = 'Flying'
```

**GRPO:**
```sql
SELECT DISTINCT layout FROM cards WHERE keywords = 'flying'
```

**Gold:**
```sql
SELECT layout FROM cards WHERE keywords = 'Flying'
```

**Pattern:** value format: 'flying' instead of 'Flying' (case)

---

## 8. q401 (moderate, card_games) -> GRPO error (no such table: frameEffects)

**Question:** What percentage of legendary frame effect cards that are only available in online game variations?

**Hint:** only available in online game variationsrefer to isOnlineOnly =1 ; legendary frame effect cards refer to frameEffects = 'legendary'; percentage refer to DIVIDE(COUNT(isOnlineOnly=1), COUNT(id)) from cards where frameEffects = 'legendary'

**SFT (correct):**
```sql
SELECT CAST(SUM(CASE WHEN isOnlineOnly = 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM cards WHERE frameEffects = 'legendary'
```

**GRPO:**
```sql
SELECT CAST(SUM(CASE WHEN T1.isOnlineOnly = 1 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM cards AS T1 INNER JOIN frameEffects AS T2 ON T1.uuid = T2.cardId WHERE T2.frameEffects = 'legendary'
```

**Gold:**
```sql
SELECT SUM(CASE WHEN isOnlineOnly = 1 THEN 1.0 ELSE 0 END) / COUNT(id) * 100 FROM cards WHERE frameEffects = 'legendary'
```

**Pattern:** wrong table/join: invented a frameEffects table (it is a column of cards); also ignored the hint

---

## 9. q449 (simple, card_games) -> GRPO wrong_rows

**Question:** What is the language of the card that has azorius watermark? List out the type of this card.

**Hint:** None

**SFT (correct):**
```sql
SELECT T2.language, T1.type FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid WHERE T1.watermark = 'azorius'
```

**GRPO:**
```sql
SELECT T1.language, T1.type FROM foreign_data AS T1 INNER JOIN cards AS T2 ON T1.uuid = T2.uuid WHERE T2.watermark = 'azorius'
```

**Gold:**
```sql
SELECT DISTINCT T2.language, T1.type FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T2.uuid = T1.uuid WHERE T1.watermark = 'azorius'
```

**Pattern:** wrong column: type taken from foreign_data instead of cards

---

## 10. q464 (simple, card_games) -> GRPO error (no such column: T2.uuid)

**Question:** Please list the names of the cards in the set "Hauptset Zehnte Edition".

**Hint:** card set "Hauptset Zehnte Edition" refers to translation = 'Hauptset Zehnte Edition'

**SFT (correct):**
```sql
SELECT T1.name FROM cards AS T1 INNER JOIN set_translations AS T2 ON T1.setCode = T2.setCode WHERE T2.translation = 'Hauptset Zehnte Edition'
```

**GRPO:**
```sql
SELECT T1.name FROM cards AS T1 INNER JOIN set_translations AS T2 ON T1.uuid = T2.uuid WHERE T2.translation = 'Hauptset Zehnte Edition'
```

**Gold:**
```sql
SELECT DISTINCT T1.name FROM cards AS T1 INNER JOIN set_translations AS T2 ON T2.setCode = T1.setCode WHERE T2.translation = 'Hauptset Zehnte Edition'
```

**Pattern:** wrong table/join: joined on uuid, which set_translations does not have

---

## 11. q470 (simple, card_games) -> GRPO wrong_rows

**Question:** When was the set of cards with "Ancestor's Chosen" released?

**Hint:** card set "Ancestor's Chosen" refers to name = 'Ancestor''s Chosen'; when released refers to releaseDate

**SFT (correct):**
```sql
SELECT T1.releaseDate FROM sets AS T1 INNER JOIN cards AS T2 ON T1.code = T2.setCode WHERE T2.name = 'Ancestor''s Chosen'
```

**GRPO:**
```sql
SELECT releaseDate FROM sets WHERE name = 'Ancestor''s Chosen'
```

**Gold:**
```sql
SELECT DISTINCT T2.releaseDate FROM cards AS T1 INNER JOIN sets AS T2 ON T2.code = T1.setCode WHERE T1.name = 'Ancestor''s Chosen'
```

**Pattern:** ambiguous: the hint calls 'Ancestor''s Chosen' a card set; gold treats it as a card name

---

## 12. q473 (moderate, card_games) -> GRPO wrong_rows

**Question:** Is the set of cards with Adarkar Valkyrie only available outside the United States?

**Hint:** card set Adarkar Valkyrie refers to name = 'Adarkar Valkyrie'; isForeignOnly = 1 means only available outside the United States;

**SFT (correct):**
```sql
SELECT CASE WHEN COUNT(T1.id) > 0 THEN 'YES' ELSE 'NO' END FROM sets AS T1 INNER JOIN cards AS T2 ON T1.id = T2.setCode WHERE T1.name = 'Adarkar Valkyrie' AND T1.isForeignOnly = 1
```

**GRPO:**
```sql
SELECT IIF(SUM(CASE WHEN T1.name = 'Adarkar Valkyrie' THEN 1 ELSE 0 END) > 0, 'Yes', 'No') FROM sets AS T1 INNER JOIN cards AS T2 ON T1.id = T2.setCode WHERE T1.isForeignOnly = 1
```

**Gold:**
```sql
SELECT IIF(isForeignOnly = 1, 'YES', 'NO') FROM cards AS T1 INNER JOIN sets AS T2 ON T2.code = T1.setCode WHERE T1.name = 'Adarkar Valkyrie'
```

**Pattern:** lucky SFT: SFT joins on sets.id = setCode (wrong key) and gets 'NO' by luck; GRPO also returns 'No' vs gold 'NO'

---

## 13. q481 (simple, card_games) -> GRPO wrong_rows

**Question:** Please list all the foreign languages in which the card "Ancestor's Chosen" has a flavor text.

**Hint:** "Ancestor''s Chosen" refers to name = 'Ancestor''s Chosen'; has a flavor text refers to flavorText is not null

**SFT (correct):**
```sql
SELECT T2.language FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid WHERE T1.name = 'Ancestor''s Chosen' AND T2.flavorText IS NOT NULL
```

**GRPO:**
```sql
SELECT DISTINCT T1.language FROM set_translations AS T1 INNER JOIN foreign_data AS T2 ON T1.id = T2.uuid INNER JOIN sets AS T3 ON T1.setCode = T3.code WHERE T3.name = 'Commander 2010' AND T2.flavorText IS NOT NULL
```

**Gold:**
```sql
SELECT T2.language FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T2.uuid = T1.uuid WHERE T1.name = 'Ancestor''s Chosen' AND T2.flavorText IS NOT NULL
```

**Pattern:** ignored question: invented the condition name = 'Commander 2010'

---

## 14. q536 (simple, codebase_community) -> GRPO wrong_rows

**Question:** How many users with more than 10 views created their account after the year 2013?

**Hint:** more than 10 views refers to Views > 10; created after the year 2013 refers to year (CreationDate) > 2013

**SFT (correct):**
```sql
SELECT COUNT(T1.Id) FROM users AS T1 INNER JOIN ( SELECT Id FROM users WHERE Views > 10 AND strftime('%Y', CreationDate) > '2013' ) AS T2 ON T1.Id = T2.Id
```

**GRPO:**
```sql
SELECT COUNT(T1.Id) FROM users AS T1 INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId WHERE T1.Views > 10 AND STRFTIME('%Y', T1.CreationDate) > '2013'
```

**Gold:**
```sql
SELECT COUNT(id) FROM users WHERE STRFTIME('%Y', CreationDate) > '2013' AND Views > 10
```

**Pattern:** over-complicated: unneeded join to posts duplicates users

---

## 15. q634 (challenging, codebase_community) -> GRPO wrong_rows

**Question:** Among posts by Harvey Motulsky and Noah Snyder, which one has higher popularity?

**Hint:** Has higher popularity means the post has higher view count ; calculation = MAX(SUM(ViewCount)) where DisplayName = 'Harvey Motulsky' OR DisplayName = 'Noah Snyder';

**SFT (correct):**
```sql
SELECT T1.DisplayName FROM users AS T1 INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId WHERE T1.DisplayName = 'Harvey Motulsky' OR T1.DisplayName = 'Noah Snyder' ORDER BY T2.ViewCount DESC LIMIT 1
```

**GRPO:**
```sql
SELECT T1.Id FROM posts AS T1 INNER JOIN users AS T2 ON T1.OwnerUserId = T2.Id WHERE T2.DisplayName = 'Harvey Motulsky' OR T2.DisplayName = 'Noah Snyder' ORDER BY T1.ViewCount DESC LIMIT 1
```

**Gold:**
```sql
SELECT T1.DisplayName FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T1.DisplayName = 'Harvey Motulsky' OR T1.DisplayName = 'Noah Snyder' GROUP BY T1.DisplayName ORDER BY SUM(T3.ViewCount) DESC LIMIT 1
```

**Pattern:** wrong column: returned post Id instead of DisplayName

---

## 16. q654 (moderate, codebase_community) -> GRPO error (no such column: T2.OwnerUserId)

**Question:** Mention the display name and location of the user who owned the excerpt post with hypothesis-testing tag.

**Hint:** user who owned the excerpt post with hypothesis-testing tag refers to OwnerUserId WHERE TagName = 'hypothesis-testing';

**SFT (correct):**
```sql
SELECT T3.DisplayName, T3.Location FROM tags AS T1 INNER JOIN posts AS T2 ON T1.ExcerptPostId = T2.Id INNER JOIN users AS T3 ON T2.OwnerUserId = T3.Id WHERE T1.TagName = 'hypothesis-testing'
```

**GRPO:**
```sql
SELECT T1.DisplayName, T1.Location FROM users AS T1 INNER JOIN tags AS T2 ON T1.Id = T2.OwnerUserId WHERE T2.TagName = 'hypothesis-testing'
```

**Gold:**
```sql
SELECT T3.DisplayName, T3.Location FROM tags AS T1 INNER JOIN posts AS T2 ON T1.ExcerptPostId = T2.Id INNER JOIN users AS T3 ON T3.Id = T2.OwnerUserId WHERE T1.TagName = 'hypothesis-testing'
```

**Pattern:** wrong table/join: skipped ExcerptPostId and read OwnerUserId from tags (ignored hint)

---

## 17. q672 (moderate, codebase_community) -> GRPO wrong_rows

**Question:** Among the users located in United Kingdom, how many users whose post have a total favorite amount of 4 or more?

**Hint:** favorite amount of 4 or more refers to FavoriteCount > = 4; Location = 'United Kingdom';

**SFT (correct):**
```sql
SELECT COUNT(T1.Id) FROM users AS T1 INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId WHERE T1.Location = 'United Kingdom' AND T2.FavoriteCount >= 4
```

**GRPO:**
```sql
SELECT COUNT(DISTINCT T1.Id) FROM users AS T1 INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId WHERE T1.Location = 'United Kingdom' AND T2.FavoriteCount >= 4
```

**Gold:**
```sql
SELECT COUNT(T1.Id) FROM users AS T1 INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId WHERE T1.Location = 'United Kingdom' AND T2.FavoriteCount >= 4
```

**Pattern:** benchmark issue: GRPO counts DISTINCT users, which fits 'how many users'; gold counts posts

---

## 18. q715 (simple, codebase_community) -> GRPO wrong_rows

**Question:** In comments with score between 1 to 5, list down the display names of the users with 0 down votes.

**Hint:** DownVotes = 0; Score BETWEEN 1 and 5

**SFT (correct):**
```sql
SELECT T2.DisplayName FROM comments AS T1 INNER JOIN users AS T2 ON T1.UserId = T2.Id WHERE T1.Score BETWEEN 1 AND 5 AND T2.DownVotes = 0
```

**GRPO:**
```sql
SELECT T2.UserDisplayName FROM users AS T1 INNER JOIN comments AS T2 ON T1.Id = T2.UserId WHERE T2.Score BETWEEN 1 AND 5 AND T1.DownVotes = 0
```

**Gold:**
```sql
SELECT T2.DisplayName FROM comments AS T1 INNER JOIN users AS T2 ON T1.UserId = T2.Id WHERE T1.Score BETWEEN 1 AND 5 AND T2.DownVotes = 0
```

**Pattern:** wrong column: comments.UserDisplayName instead of users.DisplayName

---

## 19. q849 (simple, formula_1) -> GRPO wrong_rows

**Question:** Where can the introduction of the races held on Circuit de Barcelona-Catalunya be found?

**Hint:** introduction of races refers to url; Circuit de Barcelona-Catalunya is a name of circuit;

**SFT (correct):**
```sql
SELECT url FROM circuits WHERE name = 'Circuit de Barcelona-Catalunya'
```

**GRPO:**
```sql
SELECT T1.url FROM races AS T1 INNER JOIN circuits AS T2 ON T1.circuitId = T2.circuitId WHERE T2.name = 'Circuit de Barcelona-Catalunya'
```

**Gold:**
```sql
SELECT DISTINCT T1.url FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T1.name = 'Circuit de Barcelona-Catalunya'
```

**Pattern:** ambiguous: both races and circuits have url; 'introduction of the races' fits races.url

---

## 20. q862 (simple, formula_1) -> GRPO wrong_rows

**Question:** For the Bahrain Grand Prix in 2007, how many drivers not finished the game?

**Hint:** Bahrain Grand Prix refers to races.name = 'Bahrain Grand Prix'; drivers who finished the race refers to time is not empty (i.e. time IS NOT NULL);

**SFT (correct):**
```sql
SELECT COUNT(*) FROM races AS T1 INNER JOIN results AS T2 ON T1.raceId = T2.raceId WHERE T1.name = 'Bahrain Grand Prix' AND T1.year = 2007 AND T2.time IS NULL
```

**GRPO:**
```sql
SELECT COUNT(*) FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Bahrain Grand Prix' AND T1.time IS NULL AND T1.raceId = 11
```

**Gold:**
```sql
SELECT COUNT(T3.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T1.year = 2007 AND T1.name = 'Bahrain Grand Prix' AND T2.time IS NULL
```

**Pattern:** ignored question: hard-coded raceId = 11 instead of year = 2007

---

## 21. q873 (simple, formula_1) -> GRPO wrong_rows

**Question:** What is the actual finish time for Bruce McLaren in the race No.743?

**Hint:** race number refers to raceId;

**SFT (correct):**
```sql
SELECT T1.time FROM results AS T1 INNER JOIN drivers AS T2 ON T1.driverId = T2.driverId WHERE T2.forename = 'Bruce' AND T2.surname = 'McLaren' AND T1.raceId = 743
```

**GRPO:**
```sql
SELECT T1.time FROM lapTimes AS T1 INNER JOIN results AS T2 ON T1.raceId = T2.raceId AND T1.driverId = T2.driverId INNER JOIN drivers AS T3 ON T2.driverId = T3.driverId WHERE T2.raceId = 743 AND T3.forename = 'Bruce' AND T3.surname = 'McLaren'
```

**Gold:**
```sql
SELECT T2.time FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 743 AND T1.forename = 'Bruce' AND T1.surname = 'McLaren'
```

**Pattern:** wrong table/join: time from lapTimes instead of results

---

## 22. q941 (simple, formula_1) -> GRPO wrong_rows

**Question:** How many points did Lewis Hamilton get in total in all the Formula_1 races he participated?

**Hint:** None

**SFT (correct):**
```sql
SELECT SUM(T2.points) FROM drivers AS T1 INNER JOIN results AS T2 ON T1.driverId = T2.driverId WHERE T1.forename = 'Lewis' AND T1.surname = 'Hamilton'
```

**GRPO:**
```sql
SELECT SUM(T1.points) FROM driverStandings AS T1 INNER JOIN drivers AS T2 ON T1.driverId = T2.driverId WHERE T2.forename = 'Lewis' AND T2.surname = 'Hamilton'
```

**Gold:**
```sql
SELECT SUM(T2.points) FROM drivers AS T1 INNER JOIN results AS T2 ON T1.driverId = T2.driverId WHERE T1.forename = 'Lewis' AND T1.surname = 'Hamilton'
```

**Pattern:** wrong table/join: summed driverStandings (running totals) instead of results

---

## 23. q964 (simple, formula_1) -> GRPO wrong_rows

**Question:** List out the code for drivers who have nationality in America.

**Hint:** nationality = 'America'

**SFT (correct):**
```sql
SELECT code FROM drivers WHERE nationality = 'American'
```

**GRPO:**
```sql
SELECT code FROM drivers WHERE nationality = 'America'
```

**Gold:**
```sql
SELECT code FROM drivers WHERE Nationality = 'American'
```

**Pattern:** benchmark issue: followed the hint (nationality = 'America'), but the data says 'American'

---

## 24. q991 (simple, formula_1) -> GRPO error (no such column: forname)

**Question:** What is the full name and date of birth of Austrian drivers born between 1981 and 1991?

**Hint:** Full name refers to forname, surname; Date of birth refers to dob; year(dob) BETWEEN '1981' AND '1991'; Austrian is a nationality

**SFT (correct):**
```sql
SELECT forename, surname, dob FROM drivers WHERE nationality = 'Austrian' AND dob BETWEEN '1981-01-01' AND '1991-12-31'
```

**GRPO:**
```sql
SELECT forname, surname, dob FROM drivers WHERE nationality = 'Austrian' AND dob BETWEEN '1981-01-01' AND '1991-12-31'
```

**Gold:**
```sql
SELECT forename, surname, dob FROM drivers WHERE nationality = 'Austrian' AND STRFTIME('%Y', dob) BETWEEN '1981' AND '1991'
```

**Pattern:** benchmark issue: copied the hint's typo 'forname' -> no such column

---

## 25. q1013 (simple, formula_1) -> GRPO wrong_rows

**Question:** What is the lap record for the Austrian Grand Prix Circuit?

**Hint:** lap record means the fastest time recorded which refers to time

**SFT (correct):**
```sql
SELECT T1.time FROM lapTimes AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Austrian Grand Prix' ORDER BY T1.time ASC LIMIT 1
```

**GRPO:**
```sql
SELECT T1.time FROM lapTimes AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId INNER JOIN circuits AS T3 ON T2.circuitId = T3.circuitId WHERE T3.name = 'Austrian Grand Prix Circuit' ORDER BY T1.time ASC LIMIT 1
```

**Gold:**
```sql
WITH fastest_lap_times AS ( SELECT T1.raceId, T1.fastestLapTime FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL) SELECT MIN(fastest_lap_times.fastestLapTime) as lap_record FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T2.name = 'Austrian Grand Prix'
```

**Pattern:** value format: used 'Austrian Grand Prix Circuit' from the question, not a value in the data

---

## 26. q1040 (moderate, european_football_2) -> GRPO wrong_rows

**Question:** List the top 10 players' names whose heights are above 180 in descending order of average heading accuracy.

**Hint:** heights are above 180 refers to Player.height > 180; average heading accuracy = DIVIDE(SUM(heading_accuracy), COUNT(player_fifa_api_id));

**SFT (correct):**
```sql
SELECT T1.player_name FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height > 180 GROUP BY T1.player_api_id ORDER BY AVG(T2.heading_accuracy) DESC LIMIT 10
```

**GRPO:**
```sql
SELECT T1.player_name FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height > 180 GROUP BY T1.player_name ORDER BY AVG(T2.heading_accuracy) DESC LIMIT 10
```

**Gold:**
```sql
SELECT t1.player_name FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height > 180 GROUP BY t1.id ORDER BY CAST(SUM(t2.heading_accuracy) AS REAL) / COUNT(t2.`player_fifa_api_id`) DESC LIMIT 10
```

**Pattern:** grouping/DISTINCT: GROUP BY player_name merges players with the same name

---

## 27. q1084 (challenging, european_football_2) -> GRPO wrong_rows

**Question:** Among the players born before the year 1986, how many of them would remain in his position and defense while the team attacked?

**Hint:** players born before the year 1986 refers to strftime('%Y', birthday)<'1986'; players who would remain in his position and defense while the team attacked refers to defensive_work_rate = 'high'; Should consider DISTINCT in the final result;

**SFT (correct):**
```sql
SELECT COUNT(DISTINCT T1.player_api_id) FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.birthday < '1986-01-01' AND T2.defensive_work_rate = 'high'
```

**GRPO:**
```sql
SELECT COUNT(DISTINCT T1.player_api_id) FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.birthday LIKE '%1985%' AND T2.defensive_work_rate = 'high'
```

**Gold:**
```sql
SELECT COUNT(DISTINCT t1.player_name) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.birthday) < '1986' AND t2.defensive_work_rate = 'high'
```

**Pattern:** ignored hint: birthday LIKE '%1985%' instead of year < 1986

---

## 28. q1172 (simple, thrombosis_prediction) -> GRPO wrong_rows

**Question:** How many male patients have elevated total bilirubin count?

**Hint:** male refers to SEX = 'M'; elevated means above the normal range; total bilirubin above the normal range refers to `T-BIL` >= '2.0'

**SFT (correct):**
```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.`T-BIL` >= 2
```

**GRPO:**
```sql
SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.`T-BIL` >= 2
```

**Gold:**
```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 AND T1.SEX = 'M'
```

**Pattern:** grouping/DISTINCT: dropped DISTINCT, so it counts lab rows instead of patients

---

## 29. q1187 (moderate, thrombosis_prediction) -> GRPO wrong_rows

**Question:** How many patients who were examined between 1987/7/6 and 1996/1/31 had a GPT level greater than 30 and an ALB level less than 4? List them by their ID.

**Hint:** examined between 1987/7/6 and 1996/1/31 refers to Date BETWEEN '1987-07-06' AND '1996-01-31'; GPT level greater than 30 refers to GPT > 30; ALB level less than 4 ALB < 4

**SFT (correct):**
```sql
SELECT T1.ID FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.Date BETWEEN '1987-07-06' AND '1996-01-31' AND T2.GPT > 30 AND T2.ALB < 4
```

**GRPO:**
```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.Date BETWEEN '1987-07-06' AND '1996-01-31' AND T2.GPT > 30 AND T2.ALB < 4
```

**Gold:**
```sql
SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4
```

**Pattern:** ambiguous: question asks 'how many' and 'list them by ID'; GRPO counted, gold lists

---

## 30. q1321 (moderate, student_club) -> GRPO wrong_rows

**Question:** How many events of the Student_Club did Sacha Harrison attend in 2019?

**Hint:** events attended in 2019 refers to YEAR(event_date) = 2019

**SFT (correct):**
```sql
SELECT COUNT(T1.event_id) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event INNER JOIN member AS T3 ON T3.member_id = T2.link_to_member WHERE T3.first_name = 'Sacha' AND T3.last_name = 'Harrison' AND STRFTIME('%Y', T1.event_date) = '2019'
```

**GRPO:**
```sql
SELECT COUNT(T1.link_to_event) FROM attendance AS T1 INNER JOIN member AS T2 ON T1.link_to_member = T2.member_id WHERE T2.first_name = 'Sacha' AND T2.last_name = 'Harrison' AND STRFTIME('%Y', T1.link_to_event) = '2019'
```

**Gold:**
```sql
SELECT COUNT(T1.event_id) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event INNER JOIN member AS T3 ON T2.link_to_member = T3.member_id WHERE T3.first_name = 'Sacha' AND T3.last_name = 'Harrison' AND SUBSTR(T1.event_date, 1, 4) = '2019'
```

**Pattern:** wrong column: took the year from link_to_event (an id) instead of event_date

---

## 31. q1458 (moderate, student_club) -> GRPO wrong_rows

**Question:** Calculate the difference in the percentage of members in New Jersey and Vermont.

**Hint:** SUBTRACT( DIVIDE( SUM(state = 'New Jersey'), COUNT(position = 'Member')), DIVIDE( SUM(state = 'Vermont'), COUNT(position = 'Member')) )

**SFT (correct):**
```sql
SELECT CAST(SUM(CASE WHEN T2.state = 'New Jersey' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(CASE WHEN T1.position = 'Member' THEN 1 ELSE 0 END) - CAST(SUM(CASE WHEN T2.state = 'Vermont' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(CASE WHEN T1.position = 'Member' THEN 1 ELSE 0 END) FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code
```

**GRPO:**
```sql
SELECT CAST(SUM(CASE WHEN T2.state = 'New Jersey' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(CASE WHEN T1.position = 'Member' THEN 1 ELSE NULL END) - CAST(SUM(CASE WHEN T2.state = 'Vermont' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(CASE WHEN T1.position = 'Member' THEN 1 ELSE NULL END) FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code
```

**Gold:**
```sql
SELECT CAST((SUM(CASE WHEN T2.state = 'New Jersey' THEN 1 ELSE 0 END) - SUM(CASE WHEN T2.state = 'Vermont' THEN 1 ELSE 0 END)) AS REAL) * 100 / COUNT(T1.member_id) AS diff FROM member AS T1 INNER JOIN zip_code AS T2 ON T2.zip_code = T1.zip
```

**Pattern:** benchmark issue: GRPO follows the hint (count only Members); gold divides by all members

---

## 32. q1466 (simple, student_club) -> GRPO error (no such column: college)

**Question:** Write the full name of the club member with the position of 'Secretary' and list which college the club member belongs to.

**Hint:** full name refers to first_name, last name

**SFT (correct):**
```sql
SELECT T1.first_name, T1.last_name, T2.college FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T1.position = 'Secretary'
```

**GRPO:**
```sql
SELECT first_name, last_name, college FROM member WHERE position = 'Secretary' UNION SELECT T1.first_name, T1.last_name, T2.college FROM member AS T1 INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id WHERE T1.position = 'Secretary'
```

**Gold:**
```sql
SELECT T1.first_name, T1.last_name, college FROM member AS T1 INNER JOIN major AS T2 ON T2.major_id = T1.link_to_major WHERE T1.position = 'Secretary'
```

**Pattern:** over-complicated: UNION with a branch reading college from member -> no such column

---

## 33. q1479 (moderate, debit_card_specializing) -> GRPO wrong_rows

**Question:** Which year recorded the most consumption of gas paid in CZK?

**Hint:** The first 4 strings of the Date values in the yearmonth table can represent year.

**SFT (correct):**
```sql
SELECT SUBSTR(Date, 1, 4) FROM yearmonth GROUP BY SUBSTR(Date, 1, 4) ORDER BY SUM(Consumption) DESC LIMIT 1
```

**GRPO:**
```sql
SELECT DISTINCT SUBSTR(`Date`, 1, 4) FROM yearmonth WHERE `Date` LIKE '%CZK'
```

**Gold:**
```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Pattern:** ignored question: invented Date LIKE '%CZK' and dropped the aggregation (SFT also skips the CZK filter)

---

## 34. q1493 (simple, debit_card_specializing) -> GRPO wrong_rows

**Question:** In February 2012, what percentage of customers consumed more than 528.3?

**Hint:** February 2012 refers to '201202' in yearmonth.date; The first 4 strings of the Date values in the yearmonth table can represent year; The 5th and 6th string of the date can refer to month.

**SFT (correct):**
```sql
SELECT CAST(SUM(CASE WHEN T1.Consumption > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date LIKE '201202%'
```

**GRPO:**
```sql
SELECT CAST(SUM(CASE WHEN T1.Consumption > 528.3 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.CustomerID) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T1.Date, 1, 7) = '2012-02'
```

**Gold:**
```sql
SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'
```

**Pattern:** value format: '2012-02' instead of '201202' (the hint gives the format)

---

## 35. q1514 (simple, debit_card_specializing) -> GRPO wrong_rows

**Question:** What kind of currency did the customer paid at 16:25:00 in 2012/8/24?

**Hint:** '2012/8/24' can be represented by '2012-08-24'; 

**SFT (correct):**
```sql
SELECT T1.Currency FROM customers AS T1 INNER JOIN transactions_1k AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Date = '2012-08-24' AND T2.Time = '16:25:00'
```

**GRPO:**
```sql
SELECT T1.Currency FROM customers AS T1 INNER JOIN transactions_1k AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Date = '2012-08-24' AND T2.Time = '16:25'
```

**Gold:**
```sql
SELECT DISTINCT T3.Currency FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN customers AS T3 ON T1.CustomerID = T3.CustomerID WHERE T1.Date = '2012-08-24' AND T1.Time = '16:25:00'
```

**Pattern:** value format: '16:25' instead of '16:25:00'

---

## 36. q1517 (simple, debit_card_specializing) -> GRPO wrong_rows

**Question:** For the earliest customer, what segment did he/she have?

**Hint:** None

**SFT (correct):**
```sql
SELECT T1.Segment FROM customers AS T1 INNER JOIN transactions_1k AS T2 ON T1.CustomerID = T2.CustomerID ORDER BY T2.Date ASC LIMIT 1
```

**GRPO:**
```sql
SELECT Segment FROM customers WHERE CustomerID = ( SELECT MIN(CustomerID) FROM customers )
```

**Gold:**
```sql
SELECT T2.Segment FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID ORDER BY Date ASC LIMIT 1
```

**Pattern:** ambiguous: 'earliest customer' read as smallest CustomerID; gold means earliest transaction

---

