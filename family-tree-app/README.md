# Family Tree Web App

A minimal Spring Boot application for sharing family tree diagrams with family members.

## Features

- **Secure Login**: Form-based authentication with Spring Security
- **Per-User Access Control**: Each tree can be restricted to specific users
- **Static SVG Trees**: Pre-generated tree diagrams served as inline SVG
- **Ancestry-Style UI**: Card-based interface for tree selection
- **REST API**: Query ancestors, descendants, and census records (no auth required)

## Tech Stack

- Java 17
- Spring Boot 3.4.1
- Thymeleaf (server-side rendering)
- Spring Security (form login)
- SQLite (for future database queries)

## Quick Start

```bash
cd family-tree-app
mvn spring-boot:run
```

App runs at http://localhost:3500

## REST API

The API is publicly accessible (no authentication required) and can be used by scripts or other applications.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/persons/{id}` | Person details with immediate family (mother, father, spouses, children) |
| GET | `/api/persons/{id}/ancestors?generations=N` | Ancestors up to N generations (default 10, max 20) |
| GET | `/api/persons/{id}/descendants?generations=N` | Descendants down to N generations (default 10, max 20) |
| GET | `/api/persons/{id}/census` | Linked census records with confidence scores |
| GET | `/api/persons/search?name=X&birthPlace=Y&limit=N` | Search by name and/or birthplace (limit default 50, max 500) |

### Examples

```bash
# Get person with family context
curl http://localhost:3500/api/persons/1

# Get ancestors (5 generations)
curl "http://localhost:3500/api/persons/1/ancestors?generations=5"

# Get descendants
curl http://localhost:3500/api/persons/1/descendants

# Get census records
curl http://localhost:3500/api/persons/1/census

# Search by surname
curl "http://localhost:3500/api/persons/search?name=Wrathall"

# Search by birthplace
curl "http://localhost:3500/api/persons/search?birthPlace=Yorkshire"
```

### Response Examples

**Person with family:**
```json
{
  "person": {"id": 1, "forename": "Henry S.", "surname": "Wrathall", ...},
  "mother": null,
  "father": null,
  "spouses": [{"id": 2, "forename": "Mary Alice", "surname": "Metcalfe", ...}],
  "children": [{"id": 3, "forename": "Constance V.", ...}, ...]
}
```

**Census record:**
```json
[{
  "year": 1901,
  "registrationDistrict": "West Derby",
  "nameAsRecorded": "Henry S. Wrathall",
  "ageAsRecorded": 58,
  "occupation": "Chemical Merchant",
  "confidence": 0.95
}]
```

## Test Users

| Username | Password | Access |
|----------|----------|--------|
| chris | changeme | All trees |
| family-au | changeme | Worthington, Goodall |
| family-ca | changeme | (configure in application.yml) |
| family-uk | changeme | Worthington, Wood, Goodall, Heywood |

**Note:** Change passwords before deploying to production!

## Configuration

Trees are configured in `src/main/resources/application.yml`:

```yaml
familytree:
  trees:
    - slug: worthington
      displayName: Worthington Family
      subtitle: Yorkshire, England
      initials: WF
      avatarColor: blue
      personCount: 156
      allowedUsers:
        - chris
        - family-au
        - family-uk
```

### Adding a New Tree

1. Add the tree definition to `application.yml`
2. Place the SVG file at `src/main/resources/static/trees/{slug}.svg`
3. Restart the app

### Avatar Colors

Available colors: `blue`, `teal`, `green`, `olive`, `brown`, `rust`, `rose`, `purple`, `slate`

## Project Structure

```
family-tree-app/
├── pom.xml
└── src/main/
    ├── java/com/familytree/
    │   ├── FamilyTreeApplication.java
    │   ├── config/
    │   │   ├── SecurityConfig.java      # Auth & users
    │   │   └── TreesConfig.java         # YAML tree config
    │   ├── controller/
    │   │   ├── HomeController.java      # Landing page
    │   │   ├── LoginController.java
    │   │   ├── PersonApiController.java # REST API
    │   │   └── TreeController.java      # Tree view
    │   ├── model/
    │   │   ├── CensusRecord.java        # Census record
    │   │   ├── FamilyTreeConfig.java    # Tree config
    │   │   └── Person.java              # Person with family links
    │   └── repository/
    │       ├── CensusRepository.java    # Census queries
    │       └── PersonRepository.java    # Person/ancestor queries
    └── resources/
        ├── application.yml
        ├── static/
        │   ├── css/style.css
        │   └── trees/*.svg              # Tree diagrams
        └── templates/
            ├── home.html                # Tree card grid
            ├── login.html
            └── tree-view.html           # SVG viewer
```

## Future Enhancements

- [ ] Database-backed user management
- [x] ~~Query interface for genealogy.db~~ (REST API implemented)
- [ ] GEDCOM export
- [ ] Interactive SVG with person details
