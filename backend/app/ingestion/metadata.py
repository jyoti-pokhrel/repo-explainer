import json
import re
from dataclasses import dataclass, field
from pathlib import Path

KNOWN_ORMS = {
    "python": {
        "django": "Django ORM",
        "sqlalchemy": "SQLAlchemy",
        "peewee": "Peewee",
        "tortoise-orm": "Tortoise ORM",
        "pony": "Pony ORM",
        "databases": "Databases",
        "orm": "Encode ORM",
        "prisma": "Prisma",
        "alembic": "Alembic (migrations)",
    },
    "javascript": {
        "prisma": "Prisma",
        "sequelize": "Sequelize",
        "typeorm": "TypeORM",
        "mongoose": "Mongoose",
        "knex": "Knex.js",
        "bookshelf": "Bookshelf",
        "objection": "Objection.js",
        "mikro-orm": "MikroORM",
        "drizzle-orm": "Drizzle ORM",
        "@prisma/client": "Prisma",
    },
    "typescript": {
        "prisma": "Prisma",
        "sequelize": "Sequelize",
        "typeorm": "TypeORM",
        "mongoose": "Mongoose",
        "knex": "Knex.js",
        "bookshelf": "Bookshelf",
        "objection": "Objection.js",
        "mikro-orm": "MikroORM",
        "drizzle-orm": "Drizzle ORM",
        "@prisma/client": "Prisma",
    },
    "go": {
        "gorm.io/gorm": "GORM",
        "github.com/go-gorm/gorm": "GORM",
        "github.com/jmoiron/sqlx": "sqlx",
        "github.com/masterminds/squirrel": "Squirrel",
        "github.com/volatiletech/sqlboiler": "SQLBoiler",
        "github.com/uptrace/bun": "Bun",
    },
    "java": {
        "spring-boot-starter-data-jpa": "Spring Data JPA",
        "hibernate-core": "Hibernate",
        "mybatis": "MyBatis",
        "eclipselink": "EclipseLink",
    },
    "rust": {
        "diesel": "Diesel",
        "sqlx": "sqlx",
        "sea-orm": "SeaORM",
        "rustorm": "RustORM",
    },
}

KNOWN_DATABASES = {
    "python": {
        "psycopg2": "PostgreSQL",
        "psycopg": "PostgreSQL",
        "pg8000": "PostgreSQL",
        "asyncpg": "PostgreSQL (async)",
        "mysqlclient": "MySQL",
        "pymysql": "MySQL",
        "mysql-connector-python": "MySQL",
        "aiomysql": "MySQL (async)",
        "pymongo": "MongoDB",
        "motor": "MongoDB (async)",
        "redis": "Redis",
        "aioredis": "Redis (async)",
        "sqlite3": "SQLite",
        "aiosqlite": "SQLite (async)",
        "cassandra-driver": "Cassandra",
        "neo4j": "Neo4j",
        "elasticsearch": "Elasticsearch",
        "influxdb": "InfluxDB",
        "boto3": "AWS (DynamoDB, etc.)",
    },
    "javascript": {
        "pg": "PostgreSQL",
        "postgres": "PostgreSQL",
        "mysql": "MySQL",
        "mysql2": "MySQL",
        "mongodb": "MongoDB",
        "mongoose": "MongoDB",
        "redis": "Redis",
        "ioredis": "Redis",
        "sqlite3": "SQLite",
        "better-sqlite3": "SQLite",
        "cassandra-driver": "Cassandra",
        "neo4j-driver": "Neo4j",
        "@elastic/elasticsearch": "Elasticsearch",
        "firebase": "Firebase",
        "@supabase/supabase-js": "Supabase (PostgreSQL)",
        "@planetscale/database": "PlanetScale (MySQL)",
    },
    "typescript": {
        "pg": "PostgreSQL",
        "postgres": "PostgreSQL",
        "mysql": "MySQL",
        "mysql2": "MySQL",
        "mongodb": "MongoDB",
        "mongoose": "MongoDB",
        "redis": "Redis",
        "ioredis": "Redis",
        "sqlite3": "SQLite",
        "better-sqlite3": "SQLite",
        "cassandra-driver": "Cassandra",
        "neo4j-driver": "Neo4j",
        "@elastic/elasticsearch": "Elasticsearch",
        "firebase": "Firebase",
        "@supabase/supabase-js": "Supabase (PostgreSQL)",
        "@planetscale/database": "PlanetScale (MySQL)",
    },
    "go": {
        "github.com/lib/pq": "PostgreSQL",
        "github.com/jackc/pgx": "PostgreSQL",
        "github.com/go-sql-driver/mysql": "MySQL",
        "go.mongodb.org/mongo-driver": "MongoDB",
        "github.com/redis/go-redis": "Redis",
        "github.com/go-redis/redis": "Redis",
        "github.com/mattn/go-sqlite3": "SQLite",
        "github.com/elastic/go-elasticsearch": "Elasticsearch",
    },
    "java": {
        "postgresql": "PostgreSQL",
        "mysql-connector-java": "MySQL",
        "mariadb-java-client": "MariaDB",
        "mongodb-driver-sync": "MongoDB",
        "jedis": "Redis",
        "lettuce": "Redis",
        "h2": "H2",
        "ojdbc": "Oracle",
        "mssql-jdbc": "SQL Server",
    },
    "rust": {
        "postgres": "PostgreSQL",
        "tokio-postgres": "PostgreSQL",
        "mysql": "MySQL",
        "mongodb": "MongoDB",
        "redis": "Redis",
        "fred": "Redis",
        "sqlite": "SQLite",
        "rusqlite": "SQLite",
    },
}

KNOWN_FRAMEWORKS = {
    "python": {
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI",
        "starlette": "Starlette",
        "tornado": "Tornado",
        "aiohttp": "aiohttp",
        "sanic": "Sanic",
        "bottle": "Bottle",
        "pyramid": "Pyramid",
        "falcon": "Falcon",
        "litestar": "Litestar",
        "quart": "Quart",
        "celery": "Celery (task queue)",
        "dramatiq": "Dramatiq (task queue)",
        "scrapy": "Scrapy (web scraping)",
        "streamlit": "Streamlit",
        "gradio": "Gradio",
    },
    "javascript": {
        "express": "Express.js",
        "fastify": "Fastify",
        "koa": "Koa",
        "hapi": "Hapi",
        "next": "Next.js",
        "nuxt": "Nuxt.js",
        "remix": "Remix",
        "gatsby": "Gatsby",
        "svelte-kit": "SvelteKit",
        "@angular/core": "Angular",
        "react": "React",
        "vue": "Vue.js",
        "svelte": "Svelte",
        "preact": "Preact",
        "solid-js": "SolidJS",
        "nestjs": "NestJS",
        "@nestjs/core": "NestJS",
        "electron": "Electron",
        "tauri": "Tauri",
    },
    "typescript": {
        "express": "Express.js",
        "fastify": "Fastify",
        "koa": "Koa",
        "hapi": "Hapi",
        "next": "Next.js",
        "nuxt": "Nuxt.js",
        "remix": "Remix",
        "gatsby": "Gatsby",
        "svelte-kit": "SvelteKit",
        "@angular/core": "Angular",
        "react": "React",
        "vue": "Vue.js",
        "svelte": "Svelte",
        "preact": "Preact",
        "solid-js": "SolidJS",
        "nestjs": "NestJS",
        "@nestjs/core": "NestJS",
        "electron": "Electron",
        "tauri": "Tauri",
    },
    "go": {
        "github.com/gin-gonic/gin": "Gin",
        "github.com/gorilla/mux": "Gorilla Mux",
        "github.com/labstack/echo": "Echo",
        "github.com/go-chi/chi": "Chi",
        "github.com/gofiber/fiber": "Fiber",
        "github.com/valyala/fasthttp": "FastHTTP",
    },
    "java": {
        "spring-boot-starter-web": "Spring Boot",
        "spring-webmvc": "Spring MVC",
        "jakarta.ws.rs-api": "JAX-RS",
        "javax.ws.rs-api": "JAX-RS",
        "play_2.13": "Play Framework",
        "micronaut-http-server": "Micronaut",
        "quarkus-resteasy": "Quarkus",
    },
    "rust": {
        "actix-web": "Actix Web",
        "axum": "Axum",
        "rocket": "Rocket",
        "warp": "Warp",
        "poem": "Poem",
        "salvo": "Salvo",
    },
}

KNOWN_AUTH = {
    "python": {
        "pyjwt": "JWT",
        "python-jose": "JWT (JOSE)",
        "authlib": "Authlib (OAuth/OIDC)",
        "oauthlib": "OAuth",
        "requests-oauthlib": "OAuth",
        "django-allauth": "Allauth",
        "django-rest-framework-simplejwt": "SimpleJWT",
        "passlib": "Passlib (password hashing)",
        "bcrypt": "bcrypt",
    },
    "javascript": {
        "jsonwebtoken": "JWT",
        "jose": "JWT (JOSE)",
        "passport": "Passport.js",
        "next-auth": "NextAuth",
        "@auth/core": "Auth.js",
        "express-session": "Express Session",
        "cookie-session": "Cookie Session",
        "bcrypt": "bcrypt",
        "bcryptjs": "bcrypt",
    },
    "typescript": {
        "jsonwebtoken": "JWT",
        "jose": "JWT (JOSE)",
        "passport": "Passport.js",
        "next-auth": "NextAuth",
        "@auth/core": "Auth.js",
        "express-session": "Express Session",
        "cookie-session": "Cookie Session",
        "bcrypt": "bcrypt",
        "bcryptjs": "bcrypt",
    },
    "go": {
        "github.com/golang-jwt/jwt": "JWT",
        "github.com/dgrijalva/jwt-go": "JWT",
        "github.com/markbates/goth": "Goth (OAuth)",
    },
}


@dataclass
class RepoMetadata:
    project_name: str = ""
    description: str = ""
    languages: list[str] = field(default_factory=list)
    orms: list[str] = field(default_factory=list)
    databases: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    auth_methods: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    file_count: int = 0
    total_lines: int = 0
    raw_dependencies: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "description": self.description,
            "languages": self.languages,
            "orms": self.orms,
            "databases": self.databases,
            "frameworks": self.frameworks,
            "auth_methods": self.auth_methods,
            "package_managers": self.package_managers,
            "config_files": self.config_files,
            "file_count": self.file_count,
            "total_lines": self.total_lines,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RepoMetadata":
        m = cls()
        m.project_name = data.get("project_name", "")
        m.description = data.get("description", "")
        m.languages = data.get("languages", [])
        m.orms = data.get("orms", [])
        m.databases = data.get("databases", [])
        m.frameworks = data.get("frameworks", [])
        m.auth_methods = data.get("auth_methods", [])
        m.package_managers = data.get("package_managers", [])
        m.config_files = data.get("config_files", [])
        m.file_count = data.get("file_count", 0)
        m.total_lines = data.get("total_lines", 0)
        return m


def extract_metadata(repo_path: str | Path) -> RepoMetadata:
    repo_path = Path(repo_path)
    metadata = RepoMetadata()
    metadata.raw_dependencies = {}

    _parse_readme(repo_path, metadata)
    _parse_package_json(repo_path, metadata)
    _parse_requirements(repo_path, metadata)
    _parse_pyproject(repo_path, metadata)
    _parse_go_mod(repo_path, metadata)
    _parse_cargo_toml(repo_path, metadata)
    _parse_pom_xml(repo_path, metadata)
    _parse_gemfile(repo_path, metadata)
    _parse_dockerfile(repo_path, metadata)
    _parse_env_files(repo_path, metadata)
    _parse_config_files(repo_path, metadata)
    _count_files(repo_path, metadata)
    _deduplicate(metadata)

    return metadata


def _parse_readme(repo_path: Path, metadata: RepoMetadata) -> None:
    for name in ["README.md", "README.rst", "README.txt", "README"]:
        readme = repo_path / name
        if readme.exists():
            try:
                content = readme.read_text(encoding="utf-8")
                metadata.description = _extract_description(content)
                metadata.config_files.append(name)
            except (UnicodeDecodeError, OSError):
                pass
            break


def _extract_description(content: str) -> str:
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("# ") and not line.startswith("#!"):
            return line[2:].strip()
    return ""


def _parse_package_json(repo_path: Path, metadata: RepoMetadata) -> None:
    pkg_path = repo_path / "package.json"
    if not pkg_path.exists():
        return

    try:
        data = json.loads(pkg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    metadata.config_files.append("package.json")
    metadata.project_name = data.get("name", metadata.project_name)
    if data.get("description") and not metadata.description:
        metadata.description = data["description"]

    deps = data.get("dependencies", {})
    dev_deps = data.get("devDependencies", {})
    all_deps = {**deps, **dev_deps}

    metadata.raw_dependencies["javascript"] = list(all_deps.keys())

    _match_known(deps, KNOWN_ORMS, "javascript", metadata.orms)
    _match_known(deps, KNOWN_DATABASES, "javascript", metadata.databases)
    _match_known(all_deps, KNOWN_FRAMEWORKS, "javascript", metadata.frameworks)
    _match_known(all_deps, KNOWN_AUTH, "javascript", metadata.auth_methods)

    if deps or dev_deps:
        metadata.package_managers.append("npm")

    if (repo_path / "yarn.lock").exists():
        metadata.package_managers.append("yarn")
    if (repo_path / "pnpm-lock.yaml").exists():
        metadata.package_managers.append("pnpm")


def _parse_requirements(repo_path: Path, metadata: RepoMetadata) -> None:
    for name in ["requirements.txt", "requirements-dev.txt"]:
        req_file = repo_path / name
        if not req_file.exists():
            continue
        try:
            content = req_file.read_text(encoding="utf-8")
        except OSError:
            continue

        metadata.config_files.append(name)
        deps = _parse_requirements_content(content)
        metadata.raw_dependencies["python"] = deps

        _match_known(deps, KNOWN_ORMS, "python", metadata.orms)
        _match_known(deps, KNOWN_DATABASES, "python", metadata.databases)
        _match_known(deps, KNOWN_FRAMEWORKS, "python", metadata.frameworks)
        _match_known(deps, KNOWN_AUTH, "python", metadata.auth_methods)
        break


def _parse_requirements_content(content: str) -> list[str]:
    deps = []
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        pkg = re.split(r"[>=<!~\[\];]", line)[0].strip()
        if pkg:
            deps.append(pkg.lower())
    return deps


def _parse_pyproject(repo_path: Path, metadata: RepoMetadata) -> None:
    pyproject = repo_path / "pyproject.toml"
    if not pyproject.exists():
        return

    try:
        content = pyproject.read_text(encoding="utf-8")
    except OSError:
        return

    metadata.config_files.append("pyproject.toml")

    if "dependencies" in content:
        deps_section = _extract_toml_list(content, "dependencies")
        metadata.raw_dependencies["python"] = deps_section
        _match_known(deps_section, KNOWN_ORMS, "python", metadata.orms)
        _match_known(deps_section, KNOWN_DATABASES, "python", metadata.databases)
        _match_known(deps_section, KNOWN_FRAMEWORKS, "python", metadata.frameworks)
        _match_known(deps_section, KNOWN_AUTH, "python", metadata.auth_methods)

    if not metadata.project_name:
        match = re.search(r'name\s*=\s*"([^"]+)"', content)
        if match:
            metadata.project_name = match.group(1)

    if not metadata.description:
        match = re.search(r'description\s*=\s*"([^"]+)"', content)
        if match:
            metadata.description = match.group(1)

    if (repo_path / "poetry.lock").exists():
        metadata.package_managers.append("poetry")
    if (repo_path / "uv.lock").exists():
        metadata.package_managers.append("uv")


def _extract_toml_list(content: str, key: str) -> list[str]:
    deps = []
    in_deps = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith(f"{key}") and "=" in stripped:
            in_deps = True
            after_eq = stripped.split("=", 1)[1].strip()
            if after_eq.startswith("["):
                if "]" in after_eq:
                    items = after_eq.strip("[]").split(",")
                    for item in items:
                        item = item.strip().strip("\"'")
                        if item:
                            deps.append(item.lower())
                    return deps
            continue
        if in_deps:
            if stripped.startswith("]"):
                return deps
            item = stripped.strip("\"',")
            if item:
                deps.append(item.lower())
    return deps


def _parse_go_mod(repo_path: Path, metadata: RepoMetadata) -> None:
    go_mod = repo_path / "go.mod"
    if not go_mod.exists():
        return

    try:
        content = go_mod.read_text(encoding="utf-8")
    except OSError:
        return

    metadata.config_files.append("go.mod")
    metadata.languages.append("Go")

    if not metadata.project_name:
        match = re.search(r"^module\s+(\S+)", content, re.MULTILINE)
        if match:
            metadata.project_name = match.group(1)

    deps = []
    in_require = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_require = True
            continue
        if in_require:
            if stripped == ")":
                in_require = False
                continue
            parts = stripped.split()
            if parts:
                deps.append(parts[0])
        elif stripped.startswith("require "):
            parts = stripped.split()
            if len(parts) >= 2:
                deps.append(parts[1])

    metadata.raw_dependencies["go"] = deps
    _match_known(deps, KNOWN_ORMS, "go", metadata.orms)
    _match_known(deps, KNOWN_DATABASES, "go", metadata.databases)
    _match_known(deps, KNOWN_FRAMEWORKS, "go", metadata.frameworks)
    _match_known(deps, KNOWN_AUTH, "go", metadata.auth_methods)


def _parse_cargo_toml(repo_path: Path, metadata: RepoMetadata) -> None:
    cargo = repo_path / "Cargo.toml"
    if not cargo.exists():
        return

    try:
        content = cargo.read_text(encoding="utf-8")
    except OSError:
        return

    metadata.config_files.append("Cargo.toml")
    metadata.languages.append("Rust")

    if not metadata.project_name:
        match = re.search(r'name\s*=\s*"([^"]+)"', content)
        if match:
            metadata.project_name = match.group(1)

    deps = []
    in_deps = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped == "[dependencies]":
            in_deps = True
            continue
        if stripped.startswith("[") and in_deps:
            in_deps = False
        if in_deps and "=" in stripped:
            pkg = stripped.split("=")[0].strip()
            if pkg:
                deps.append(pkg.lower())

    metadata.raw_dependencies["rust"] = deps
    _match_known(deps, KNOWN_ORMS, "rust", metadata.orms)
    _match_known(deps, KNOWN_DATABASES, "rust", metadata.databases)
    _match_known(deps, KNOWN_FRAMEWORKS, "rust", metadata.frameworks)


def _parse_pom_xml(repo_path: Path, metadata: RepoMetadata) -> None:
    pom = repo_path / "pom.xml"
    if not pom.exists():
        return

    try:
        content = pom.read_text(encoding="utf-8")
    except OSError:
        return

    metadata.config_files.append("pom.xml")
    metadata.languages.append("Java")

    artifact_match = re.search(r"<artifactId>([^<]+)</artifactId>", content)
    if artifact_match and not metadata.project_name:
        metadata.project_name = artifact_match.group(1)

    deps = re.findall(r"<artifactId>([^<]+)</artifactId>", content)
    metadata.raw_dependencies["java"] = [d.lower() for d in deps]
    _match_known(deps, KNOWN_ORMS, "java", metadata.orms)
    _match_known(deps, KNOWN_DATABASES, "java", metadata.databases)
    _match_known(deps, KNOWN_FRAMEWORKS, "java", metadata.frameworks)


def _parse_gemfile(repo_path: Path, metadata: RepoMetadata) -> None:
    gemfile = repo_path / "Gemfile"
    if not gemfile.exists():
        return

    try:
        content = gemfile.read_text(encoding="utf-8")
    except OSError:
        return

    metadata.config_files.append("Gemfile")
    metadata.languages.append("Ruby")

    deps = re.findall(r"gem\s+['\"]([^'\"]+)['\"]", content)
    metadata.raw_dependencies["ruby"] = [d.lower() for d in deps]


def _parse_dockerfile(repo_path: Path, metadata: RepoMetadata) -> None:
    for name in ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"]:
        docker_file = repo_path / name
        if not docker_file.exists():
            continue
        try:
            content = docker_file.read_text(encoding="utf-8")
        except OSError:
            continue

        metadata.config_files.append(name)

        db_images = {
            "postgres": "PostgreSQL",
            "mysql": "MySQL",
            "mongo": "MongoDB",
            "redis": "Redis",
            "mariadb": "MariaDB",
            "cassandra": "Cassandra",
            "elasticsearch": "Elasticsearch",
            "neo4j": "Neo4j",
        }
        for image, db_name in db_images.items():
            if image in content.lower():
                if db_name not in metadata.databases:
                    metadata.databases.append(db_name)
        break


def _parse_env_files(repo_path: Path, metadata: RepoMetadata) -> None:
    for name in [".env", ".env.example", ".env.sample"]:
        env_file = repo_path / name
        if not env_file.exists():
            continue
        try:
            content = env_file.read_text(encoding="utf-8")
        except OSError:
            continue

        metadata.config_files.append(name)

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key = line.split("=")[0].strip().upper()
            value = line.split("=", 1)[1].strip().lower()

            if any(p in key for p in ["MONGO", "REDIS", "POSTGRES", "MYSQL", "PG", "DB_HOST", "DATABASE_URL"]):
                if "postgres" in value or "postgresql" in key:
                    if "PostgreSQL" not in metadata.databases:
                        metadata.databases.append("PostgreSQL")
                elif "mysql" in value or "mysql" in key:
                    if "MySQL" not in metadata.databases:
                        metadata.databases.append("MySQL")
                elif "mongo" in value or "mongo" in key:
                    if "MongoDB" not in metadata.databases:
                        metadata.databases.append("MongoDB")
                elif "redis" in value or "redis" in key:
                    if "Redis" not in metadata.databases:
                        metadata.databases.append("Redis")
                elif "sqlite" in value:
                    if "SQLite" not in metadata.databases:
                        metadata.databases.append("SQLite")
        break


def _parse_config_files(repo_path: Path, metadata: RepoMetadata) -> None:
    prisma_schema = repo_path / "prisma" / "schema.prisma"
    if prisma_schema.exists():
        metadata.config_files.append("prisma/schema.prisma")
        try:
            content = prisma_schema.read_text(encoding="utf-8")
            if "postgresql" in content.lower():
                if "PostgreSQL" not in metadata.databases:
                    metadata.databases.append("PostgreSQL")
            if "mysql" in content.lower():
                if "MySQL" not in metadata.databases:
                    metadata.databases.append("MySQL")
            if "sqlite" in content.lower():
                if "SQLite" not in metadata.databases:
                    metadata.databases.append("SQLite")
            if "mongodb" in content.lower():
                if "MongoDB" not in metadata.databases:
                    metadata.databases.append("MongoDB")
        except OSError:
            pass

    alembic_ini = repo_path / "alembic.ini"
    if alembic_ini.exists():
        metadata.config_files.append("alembic.ini")
        if "SQLAlchemy" not in metadata.orms:
            metadata.orms.append("SQLAlchemy")

    if _find_django_settings(repo_path):
        if "Django ORM" not in metadata.orms:
            metadata.orms.append("Django ORM")
        if "Django" not in metadata.frameworks:
            metadata.frameworks.append("Django")


def _find_django_settings(repo_path: Path) -> bool:
    for root, dirs, files in _walk_safe(repo_path):
        for f in files:
            if f == "settings.py":
                try:
                    content = (Path(root) / f).read_text(encoding="utf-8")
                    if "django" in content.lower() or "INSTALLED_APPS" in content:
                        return True
                except OSError:
                    pass
    return False


def _count_files(repo_path: Path, metadata: RepoMetadata) -> None:
    lang_extensions = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "JavaScript",
        ".tsx": "TypeScript",
        ".go": "Go",
        ".java": "Java",
        ".c": "C",
        ".cpp": "C++",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".md": "Markdown",
    }

    skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist", "target", ".idea", ".vscode"}
    count = 0
    lines = 0
    langs: set[str] = set()

    for root, dirs, files in _walk_safe(repo_path):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in lang_extensions:
                count += 1
                langs.add(lang_extensions[ext])
                try:
                    file_path = Path(root) / f
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                        lines += sum(1 for _ in fh)
                except OSError:
                    pass

    metadata.file_count = count
    metadata.total_lines = lines
    for lang in sorted(langs):
        if lang not in metadata.languages:
            metadata.languages.append(lang)


def _walk_safe(root: Path):
    try:
        dirs = []
        files = []
        for entry in root.iterdir():
            if entry.is_dir():
                dirs.append(entry.name)
            elif entry.is_file():
                files.append(entry.name)
        if dirs or files:
            yield str(root), dirs, files
        for d in dirs:
            yield from _walk_safe(root / d)
    except (PermissionError, OSError):
        return


def _match_known(
    deps: dict | list,
    known_map: dict,
    lang: str,
    target: list,
) -> None:
    if isinstance(deps, dict):
        dep_names = [d.lower() for d in deps.keys()]
    else:
        dep_names = [d.lower() for d in deps]

    lang_map = known_map.get(lang, {})
    for dep in dep_names:
        for known_key, friendly_name in lang_map.items():
            if known_key.lower() in dep or dep in known_key.lower():
                if friendly_name not in target:
                    target.append(friendly_name)


def _deduplicate(metadata: RepoMetadata) -> None:
    metadata.orms = list(dict.fromkeys(metadata.orms))
    metadata.databases = list(dict.fromkeys(metadata.databases))
    metadata.frameworks = list(dict.fromkeys(metadata.frameworks))
    metadata.auth_methods = list(dict.fromkeys(metadata.auth_methods))
    metadata.languages = list(dict.fromkeys(metadata.languages))
    metadata.package_managers = list(dict.fromkeys(metadata.package_managers))
