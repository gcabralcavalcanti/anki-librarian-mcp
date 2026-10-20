# Taxonomy (example)

Four knowledge areas plus a branch for working tags. The first two levels below are a starting point; the tree
grows only where real cards need it (a tag exists only if a card has it).

```
Economics
├── Microeconomics          Consumer.Theory · Theory.of.the.Firm · Market.Structures · Game.Theory · Welfare · Behavioural
├── Macroeconomics
│   ├── Theory              Basic.Concepts · Growth (formal models) · Development (structural change)
│   └── Applied             National.Accounts · Public.Sector · Monetary.Economics · Financial.System · International
├── Economic.Thought        1-Precursors · 2-Classical · 3-Twentieth.Century · 4-After.2008 · To.Classify
├── Business&Management     Administration · Sales&Marketing · Accounting · Finance
└── Production&Markets      Sector.Sheets · Company.Sheets · Trade&Production · Indicators   (2010 onwards only)

Humanities
├── History                 General.History: 0-Prehistory · 1-Antiquity · 2-Middle.Ages · 3-Early.Modern · 4-Modern
│                           (1789-1848---Age.of.Revolution · 1848-1875---Age.of.Capital · 1875-1914---Age.of.Empire ·
│                            1914-1991---Age.of.Extremes) · 5-Globalisation.and.Present
├── Human.Thought           Philosophy · Political.Philosophy · Sociology · Psychology
├── Politics                International.Relations · Institutions · Elections
├── Geography               Countries.and.Regions · Physical · Human
├── Law                     General.Theory · Applied
└── Arts&Cultures           Cinema · Music · Popular.Culture · Games · Sports

Exact.Sciences
├── Quantitative            Elementary.Math · Calculus (1-Limits … 4-Differential.Equations) · Linear.Algebra ·
│                           Logic · Statistics (Basic.Concepts · Descriptive · Inference · Probability · Regressions)
├── Physics                 Mechanics · Thermodynamics · Electromagnetism · Astronomy
├── Chemistry               General · Inorganic · Organic
└── Engineering             Civil · Computing · Electrical · Mechanical

Biological.Sciences
├── Cell.and.Molecular      Bioenergetics · Biochemistry · Cytology · Genetics
├── Human.Body.and.Health   Anatomy · Diseases · Pharmacology · Nutrition · First.Aid
├── Diversity.of.Life       Kingdoms · Viruses · Systematics
└── Ecology.and.Evolution

Specifics                   Activities::YYYY.MM---Name (the batch a card came from) · Bibliographies · Curiosities
```

Root-level working tags allowed besides these: `TEMP::*` and `Update::*`.

Configure the server with the roots so it can check every new card:

```toml
[taxonomy]
roots = ["Economics", "Humanities", "Exact.Sciences", "Biological.Sciences", "Specifics"]
operational = ["TEMP", "Update"]
```
