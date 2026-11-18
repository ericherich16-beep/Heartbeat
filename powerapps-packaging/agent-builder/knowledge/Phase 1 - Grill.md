# Phase 1 - Grill

**Goal:** understand the idea well enough that the spec writes itself. You interview, the user decides. Work in the spirit of "grill me": be relentless, go one question at a time, and walk the decision tree until no branch is left open.

## How to grill

1. **Start with what they've got.** Ask the user to describe the idea in their own words: who it's for, what problem it solves, and what they do today instead (spreadsheet, paper, email).
2. **One question per message.** Each question comes with **your recommended answer** and one line on why, so the user can just say "yes".
3. **Go branch by branch.** Finish a topic before moving on. When an answer opens new questions, follow them first.
4. **Challenge vague answers.** "Track everything" → *which fields, who enters them, when?* "Managers approve" → *which managers, and what happens if they reject?*
5. **Point out conflicts** between answers straight away, and ask which one wins.
6. **Ask about today's data.** If an existing spreadsheet or list exists, ask for its column headers. Never ask for real data. Fictional examples are enough.
7. **Keep a running tally** after every 5 questions: *decided / still open*.

## Topics to cover, in this order

| # | Topic | What you must end up knowing |
|---|---|---|
| 1 | Purpose | Problem, who benefits, what "done" looks like, what's out of scope |
| 2 | Users and roles | Each role, what it can see and do, and how a role is decided (a list of people, a SharePoint group) |
| 3 | Things being tracked | Each record type (becomes a list), its fields, which are required, and the choices for each choice field |
| 4 | Files | Any documents or photos, which record they belong to (becomes a document library), size and type limits |
| 5 | Life cycle | Statuses and every allowed move between them, who can make each move, and what's blocked |
| 6 | Rules | Calculations, validation, due dates, overdue logic, duplicates, revisions |
| 7 | Screens | What each role needs to see first, the main lists, detail pages and forms, and phone vs tablet vs desktop |
| 8 | Automation | Anything automatic (emails, Teams posts, file saves), its trigger and recipients. Remind them of FLOW-01: standard connectors only |
| 9 | Volume | Expected rows per year (delegation, APP-09) and how far back history goes |
| 10 | Environment | Does the environment have Dataverse (needed for solutions, PKG-06)? Which SharePoint site? Can they install pac? Any connector policy (FLOW-01)? |
| 11 | Testing | Who tests, and what a realistic test scenario is for each role |

## Finish

1. **Write a grill summary:** one short section per topic above, then a list of **decisions** (D-01, D-02…), then **open questions** with your recommended answers.
2. **Ask:** "Is anything wrong or missing?" Fix it until the user says it's complete.
3. **Output a PROJECT STATE** with Phase: Grill complete, and the summary attached under *Notes*.
4. **Move to Phase 2 - Spec.**
