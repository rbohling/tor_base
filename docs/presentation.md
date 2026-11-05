# Tor Base — presentation and speaker notes

Editable presentation: https://chatgpt.com/space/page_61712d8a50988191bb9f1b2e3aa6accd

Export to PowerPoint from the presentation menu. Update slide 7 after running MySQL and Tor experiments.

## Slide 1: A real database behind an onion website

Tor Base
Individual graduate database project

### Speaker notes

I built a small private notes application. Users sign in and manage their own notes. Flask runs the website and MySQL stores the records. Tor supplies another way to reach the same application. The goal is to explain the database architecture and evaluate it in a controlled lab.

## Slide 2: Tor changes the connection

Tor Browser reaches the onion service.
The onion service forwards the request to Flask.
Flask checks the user and queries MySQL.

### Speaker notes

The database does not need special onion SQL. Tor forwards web requests to the application. MySQL stays on a private Docker network and has no published host port. The local URL and onion URL reach the same application. Source: https://community.torproject.org/onion-services/setup/

## Slide 3: Three tables keep the design small

Users store account identities and password hashes.
Categories store shared labels.
Posts link each note to its owner and category.

### Speaker notes

There are three normalized tables. A post has a foreign key to its user and category. This avoids repeating account details and category names in every note. A composite index on user ID and title supports the owner-filtered title-prefix search. See sql/schema.sql and docs/schema.mmd.

## Slide 4: The live demo follows one note

Sign in as Alice and create a note.
Search for its title, then edit it.
Sign in as Bob and verify it stays private.
Return as Alice and delete it.

### Speaker notes

Use two browser sessions or log out between accounts. Show the note in MySQL after saving it. To demonstrate authorization, try the known edit URL as Bob: the application should return 404. It applies the owner filter to reads, updates and deletes. Deletion is immediate, so use a disposable demo note.

## Slide 5: SQL does the database work

Joins connect notes with users and categories.
A CTE summarizes notes per category.
A window function ranks each user’s categories.
Transactions commit or roll back changes.

### Speaker notes

Open sql/analysis.sql and explain one query at a time. A CTE gives a temporary name to an intermediate result. DENSE_RANK ranks categories within each user. A transaction makes a change durable when committed and lets us undo uncommitted work with rollback. The test suite checks foreign-key rejection and rollback.

## Slide 6: Two experiments answer different questions

Database: does the composite index help?
Application: how do local and onion response times differ?
Each experiment saves raw measurements.

### Speaker notes

Seed 20,000 synthetic notes. The SQL benchmark alternates optimizer-choice and composite-index-ignored queries and saves EXPLAIN ANALYZE plans. Other indexes remain in the baseline. Run the HTTP comparison from one client, with warmups and alternating requests. Report failures and medians. HTTP time includes application and network work. Source: https://dev.mysql.com/doc/refman/8.4/en/explain.html

## Slide 7: What has been verified so far

9 application tests passed with SQLite.
MySQL integration tests are configured in GitHub Actions.
Live MySQL, onion access and timings remain to be run.

### Speaker notes

This slide distinguishes completed checks from pending experiments. The build environment did not provide Docker or VirtualBox. The nine tests cover login, CRUD, owner isolation, CSRF, injection and HTML escaping, validation, foreign keys, rollback and CLI behavior. Before the final class presentation, run the supplied deployment and benchmarks and replace this slide with actual evidence. No benchmark numbers have been invented.

## Slide 8: The main lesson

An onion website can use an ordinary MySQL database.
Application code controls access to private records.
Database speed and network response time need separate measurements.

### Speaker notes

My project shows the connection between a privacy network and ordinary database design. Tor does not replace authentication, database permissions or application security. This is a small educational lab with fictional notes. It has no production login throttling or account recovery. Finish by showing actual results and explaining the limits of a one-client experiment. Sources: https://community.torproject.org/onion-services/setup/ and https://flask.palletsprojects.com/en/stable/web-security/

