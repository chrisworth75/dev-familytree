# Family Tree Web App

A minimal Spring Boot application for sharing family tree diagrams with family members.

## Features

- **Secure Login**: Form-based authentication with Spring Security
- **Per-User Access Control**: Each tree can be restricted to specific users
- **Static SVG Trees**: Pre-generated tree diagrams served as inline SVG
- **Ancestry-Style UI**: Card-based interface for tree selection

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
    │   │   └── TreeController.java      # Tree view
    │   └── model/
    │       └── FamilyTreeConfig.java    # Tree record
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
- [ ] Query interface for genealogy.db
- [ ] GEDCOM export
- [ ] Interactive SVG with person details
