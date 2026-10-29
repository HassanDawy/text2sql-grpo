## 1. q917 (simple, formula_1)

**Question:** Which website should I go to if I want to know more about Anthony Davidson?

**Hint:** website refers to url

**Predicted:**
```sql
SELECT T1.url FROM circuits AS T1 INNER JOIN races AS T2 ON T1.circuitId = T2.circuitId INNER JOIN results AS T3 ON T2.raceId = T3.raceId INNER JOIN drivers AS T4 ON T3.driverId = T4.driverId WHERE T4.forename = 'Anthony' AND T4.surname = 'Davidson'
```

**Gold:**
```sql
SELECT url FROM drivers WHERE forename = 'Anthony' AND surname = 'Davidson'
```

**Pattern:**

wrong join/table

## 2. q985 (simple, formula_1)

**Question:** Among the drivers who participated in the French Grand Prix, who has the slowest time in the 3rd lap.

**Hint:** slowest time refers to Max(time);

**Predicted:**
```sql
SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T1.driverId = T2.driverId INNER JOIN lapTimes AS T3 ON T2.resultId = T3.raceId WHERE T2.raceId = 1 AND T3.lap = 3 ORDER BY T3.time ASC LIMIT 1
```

**Gold:**
```sql
SELECT T1.driverId FROM lapTimes AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.name = 'French Grand Prix' AND T1.lap = 3 ORDER BY T1.time DESC LIMIT 1
```

**Pattern:**

wrong table and extra columns selected

---

## 3. q66 (simple, california_schools)

**Question:** Between 1/1/2000 to 12/31/2005, how many directly funded schools opened in the county of Stanislaus?

**Hint:** Directly funded schools refers to FundingType = 'Directly Funded'

**Predicted:**
```sql
SELECT COUNT(CDSCode) FROM schools WHERE County = 'Stanislaus' AND FundingType = 'Directly Funded' AND OpenDate BETWEEN '2000-01-01' AND '2005-12-31'
```

**Gold:**
```sql
SELECT COUNT(School) FROM schools WHERE strftime('%Y', OpenDate) BETWEEN '2000' AND '2005' AND County = 'Stanislaus' AND FundingType = 'Directly funded'
```

**Pattern:**

wrong column selected

---

## 4. q511 (moderate, card_games)

**Question:** What is the most common visual frame effects among the incredibly powerful foils?

**Hint:** when both cardKingdomFoilId and cardKingdomId are not null, this foil is incredibly powerful; most common visual frame effects refers to MAX(frameEffects)

**Predicted:**
```sql
SELECT frameEffects FROM cards WHERE cardKingdomFoilId IS NOT NULL AND cardKingdomId IS NOT NULL ORDER BY frameEffects DESC LIMIT 1
```

**Gold:**
```sql
SELECT frameEffects FROM cards WHERE cardKingdomFoilId IS NOT NULL AND cardKingdomId IS NOT NULL GROUP BY frameEffects ORDER BY COUNT(frameEffects) DESC LIMIT 1
```

**Pattern:**

wrong sorting

---

## 5. q1200 (moderate, thrombosis_prediction)

**Question:** What proportion of patients who had signs of thrombocytopenia had SLE diagnosed?

**Hint:** thrombocytopenia' refers to symptoms; 'SLE' refers to diagnosis; calculation =  DIVIDE(SUM(DIAGNOSIS LIKE '%ITP%'), SUM(DIAGNOSIS LIKE '%SLE%')) MULTIPLY 100

**Predicted:**
```sql
SELECT CAST(SUM(CASE WHEN T2.DIAGNOSIS LIKE '%ITP%' THEN 1 ELSE 0 END) AS REAL) * 100 / SUM(CASE WHEN T2.DIAGNOSIS LIKE '%SLE%' THEN 1 ELSE 0 END) FROM Examination AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T1.Symptoms = 'thrombocytopenia'
```

**Gold:**
```sql
SELECT CAST(SUM(CASE WHEN Diagnosis = 'SLE' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(ID) FROM Examination WHERE Symptoms = 'thrombocytopenia'
```

**Pattern:**

misread hint


## 6. q1144 (simple, european_football_2)

**Question:** Please state the finishing rate and curve score of the player who has the heaviest weight.

**Hint:** finishing rate refer to finishing; curve score refer to curve; heaviest weight refers to MAX(weight)

**Predicted:**
```sql
SELECT T1.finishing, T1.curve FROM Player_Attributes AS T1 INNER JOIN Player AS T2 ON T1.player_api_id = T2.player_api_id ORDER BY T2.weight DESC LIMIT 1
```

**Gold:**
```sql
SELECT id, finishing, curve FROM Player_Attributes WHERE player_api_id = ( SELECT player_api_id FROM Player ORDER BY weight DESC LIMIT 1 ) LIMIT 1
```

**Pattern:**

missing column, unnecessary join

---

## 7. q952 (simple, formula_1)

**Question:** Which constructors have been ranked 1?

**Hint:** None

**Predicted:**
```sql
SELECT T2.name FROM results AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId WHERE T1.position = 1
```

**Gold:**
```sql
SELECT DISTINCT T2.name FROM results AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.rank = 1
```

**Pattern:**

missing distinct, wrong column compared in WHERE

---

## 8. q640 (moderate, codebase_community)

**Question:** Calculate the difference in view count from post posted by Mornington and view count from posts posted by Amos.

**Hint:** calculation = SUBTRACT(SUM(ViewCount where DisplayName = 'Mornington'), SUM(ViewCount where DisplayName = 'Amos'));

**Predicted:**
```sql
SELECT SUM(CASE WHEN T2.DisplayName = 'Mornington' THEN T1.ViewCount ELSE 0 END) - SUM(CASE WHEN T2.DisplayName = 'Amos' THEN T1.ViewCount ELSE 0 END) AS diff FROM posts AS T1 INNER JOIN users AS T2 ON T1.OwnerUserId = T2.Id
```

**Gold:**
```sql
SELECT SUM(IIF(T1.DisplayName = 'Mornington', T3.ViewCount, 0)) - SUM(IIF(T1.DisplayName = 'Amos', T3.ViewCount, 0)) AS diff FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T3.Id = T2.PostId
```

**Pattern:** 

---

## 9. q1115 (challenging, european_football_2)

**Question:** What percentage is Landon Donovan's overall rating higher than Jordan Bowery on 2013/7/12?

**Hint:** Landon Donovan's refers to player_name = 'Landon Donovan'; Jordan Bowery refers to player_name = 'Jordan Bowery'; percentage refers to DIVIDE(SUBTRACT(player_name = 'Landon Donovan' overall_rating; player_name = 'Jordan Bowery' overall_rating), player_name = 'Landon Donovan' overall_rating)*100

**Predicted:**
```sql
SELECT CAST((SUM(CASE WHEN T1.player_name = 'Landon Donovan' THEN T2.overall_rating ELSE 0 END) - SUM(CASE WHEN T1.player_name = 'Jordan Bowery' THEN T2.overall_rating ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN T1.player_name = 'Landon Donovan' THEN T2.overall_rating ELSE 0 END) FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T2.date = '2013-07-12'
```

**Gold:**
```sql
SELECT (SUM(CASE WHEN t1.player_name = 'Landon Donovan' THEN t2.overall_rating ELSE 0 END) * 1.0 - SUM(CASE WHEN t1.player_name = 'Jordan Bowery' THEN t2.overall_rating ELSE 0 END)) * 100 / SUM(CASE WHEN t1.player_name = 'Landon Donovan' THEN t2.overall_rating ELSE 0 END) LvsJ_percent FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE SUBSTR(t2.`date`, 1, 10) = '2013-07-12'
```

**Pattern:** 

---

## 10. q864 (simple, formula_1)

**Question:** For the race happened on 2015/11/29, how many drivers finished the game?

**Hint:** game and race are synonyms; drivers who finished the race should have record in time;

**Predicted:**
```sql
SELECT COUNT(T1.driverId) FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.date = '2015-11-29'
```

**Gold:**
```sql
SELECT COUNT(T2.driverId) FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId WHERE T1.date = '2015-11-29' AND T2.time IS NOT NULL
```

**Pattern:** 

---

## 11. q1388 (moderate, student_club)

**Question:** Which students manage to generate the highest income. State his/her full name along with the income source.

**Hint:** name of students means the full name; full name refers to first_name, last_name; generate the highest income refers to MAX(income.amount);

**Predicted:**
```sql
SELECT T1.first_name, T1.last_name, T2.source FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member ORDER BY T2.amount DESC LIMIT 1
```

**Gold:**
```sql
SELECT T1.first_name, T1.last_name, T2.source FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member GROUP BY T1.first_name, T1.last_name, T2.source ORDER BY SUM(T2.amount) DESC LIMIT 1
```

**Pattern:** 

---

## 12. q415 (challenging, card_games)

**Question:** What percentage of cards with format commander and legal status do not have a content warning?

**Hint:** do not have a content warning refers to hasContentWarning = 0; percentage refers to DIVIDE(COUNT(hasContentWarning = 0),COUNT(ID))*100 where format = 'commander' AND Status = 'legal';

**Predicted:**
```sql
SELECT CAST(SUM(CASE WHEN T1.hasContentWarning = 0 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM cards AS T1 INNER JOIN legalities AS T2 ON T1.uuid = T2.uuid WHERE T2.format = 'commander' AND T2.status = 'legal'
```

**Gold:**
```sql
SELECT CAST(SUM(CASE WHEN T1.hasContentWarning = 0 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM cards AS T1 INNER JOIN legalities AS T2 ON T1.uuid = T2.uuid WHERE T2.format = 'commander' AND T2.status = 'Legal'
```

**Pattern:** 

---

## 13. q1186 (moderate, thrombosis_prediction)

**Question:** Lists all patients by ID who were diagnosed with Behcet's and had their exams between 01/01/197 and 12/31/1997.

**Hint:** 'Behcet' refers to diagnosis; exam between 01/01/1997 and 12/31/1997 refers to YEAR(Description) > = '1997-1-1' AND YEAR(Description) < '1998-1-1'

**Predicted:**
```sql
SELECT T1.ID FROM Patient AS T1 INNER JOIN Examination AS T2 ON T1.ID = T2.ID WHERE T1.Description LIKE '%Behcet%' AND T2.`Examination Date` BETWEEN '1970-01-01' AND '1997-12-31'
```

**Gold:**
```sql
SELECT ID FROM Examination WHERE `Examination Date` BETWEEN '1997-01-01' AND '1997-12-31' AND Diagnosis = 'Behcet'
```

**Pattern:** 

---

## 14. q251 (moderate, toxicology)

**Question:** What is the least common element of all carcinogenic molecules?

**Hint:** label = '+' mean molecules are carcinogenic

**Predicted:**
```sql
SELECT T1.element FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+' GROUP BY T1.element ORDER BY COUNT(T1.element) ASC LIMIT 1
```

**Gold:**
```sql
SELECT T.element FROM ( SELECT T2.element, COUNT(DISTINCT T2.molecule_id) FROM molecule AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.label = '+' GROUP BY T2.element ORDER BY COUNT(DISTINCT T2.molecule_id) LIMIT 1 ) t
```

**Pattern:** 

---

## 15. q587 (moderate, codebase_community)

**Question:** Calculate the average view count of each post tagged as 'humor' and list the title and the comment of each post.

**Hint:** tagged as  'humor' refers to tag = '<humor>'; comment of the post refers to Text; average view count = AVG(ViewCount)

**Predicted:**
```sql
SELECT AVG(T1.ViewCount), T1.Title, T2.Text FROM posts AS T1 INNER JOIN comments AS T2 ON T1.Id = T2.PostId INNER JOIN tags AS T3 ON T1.Tags = T3.Id WHERE T3.TagName = 'humor'
```

**Gold:**
```sql
SELECT AVG(T2.ViewCount), T2.Title, T1.Text FROM comments AS T1 INNER JOIN posts AS T2 ON T2.Id = T1.PostId  WHERE T2.Tags = '<humor>' GROUP BY T2.Title, T1.Text 
```

**Pattern:** 

---

## 16. q252 (simple, toxicology)

**Question:** What are the atoms that can bond with the atom that has the element lead?

**Hint:** atom that has the element lead refers to atom_id where element = 'pb'

**Predicted:**
```sql
SELECT T2.atom_id2 FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'pb'
```

**Gold:**
```sql
SELECT T2.atom_id, T2.atom_id2 FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id WHERE T1.element = 'pb'
```

**Pattern:** 

---

## 17. q184 (simple, financial)

**Question:** How many female customers have a junior credit card?

**Hint:** Female refers to gender = 'F'

**Predicted:**
```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN card AS T2 ON T1.client_id = T2.disp_id WHERE T1.gender = 'F' AND T2.type = 'junior'
```

**Gold:**
```sql
SELECT COUNT(T1.client_id) FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN card AS T3 ON T2.disp_id = T3.disp_id WHERE T1.gender = 'F' AND T3.type = 'junior'
```

**Pattern:** 

---

## 18. q1488 (simple, debit_card_specializing)

**Question:** Who among KAM's customers consumed the most? How much did it consume?

**Hint:** None

**Predicted:**
```sql
SELECT T1.CustomerID, T1.Consumption FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Segment = 'KAM' ORDER BY T1.Consumption DESC LIMIT 1
```

**Gold:**
```sql
SELECT T2.CustomerID, SUM(T2.Consumption) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'KAM' GROUP BY T2.CustomerID ORDER BY SUM(T2.Consumption) DESC LIMIT 1
```

**Pattern:** 

---

## 19. q479 (moderate, card_games)

**Question:** Among the cards with converted mana cost higher than 5 in the set Coldsnap, how many of them have unknown power?

**Hint:** card set Coldsnap refers to name = 'Coldsnap'; converted mana cost higher than 5 refers to convertedManaCost > 5; unknown power refers to power = '*' or T1.power is null

**Predicted:**
```sql
SELECT COUNT(T1.id) FROM cards AS T1 INNER JOIN sets AS T2 ON T1.setCode = T2.code WHERE T2.name = 'Coldsnap' AND T1.power = '*' AND T1.convertedManaCost > 5
```

**Gold:**
```sql
SELECT SUM(CASE WHEN T1.power LIKE '*' OR T1.power IS NULL THEN 1 ELSE 0 END) FROM cards AS T1 INNER JOIN sets AS T2 ON T2.code = T1.setCode WHERE T2.name = 'Coldsnap' AND T1.convertedManaCost > 5
```

**Pattern:** 

---

## 20. q1247 (challenging, thrombosis_prediction)

**Question:** Among the male patients who have a normal level of white blood cells, how many of them have an abnormal fibrinogen level?

**Hint:** male patients refers to Sex = 'M'; normal level of white blood cells refers to WBC > 3.5 and WBC <9.0; abnormal fibrinogen level refers to FG < = 150 or FG > = 450; Don't compute repetitive ones.

**Predicted:**
```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.SEX = 'M' AND T2.WBC > 3.5 AND T2.WBC < 9 AND (T2.FG <= 150 OR T2.FG >= 450)
```

**Gold:**
```sql
SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.FG <= 150 OR T2.FG >= 450 AND T2.WBC > 3.5 AND T2.WBC < 9.0 AND T1.SEX = 'M'
```

**Pattern:** 

---

