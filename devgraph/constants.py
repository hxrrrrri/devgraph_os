"""Project-wide constants."""

DEFAULT_CONFIG_FILE = "devgraph.toml"
DEFAULT_STORAGE_DIR = ".devgraph"
DEFAULT_IGNORE_FILE = ".devgraphignore"
DEFAULT_DASHBOARD_PORT = 38987

SUPPORTED_CODE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
    ".scala": "scala",
    ".dart": "dart",
    ".lua": "lua",
    ".sh": "bash",
    ".bash": "bash",
    ".sql": "sql",
    ".vue": "vue",
    ".svelte": "svelte",
    ".prisma": "prisma",
}

SUPPORTED_DOC_EXTENSIONS = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "rst",
    ".txt": "text",
    ".pdf": "pdf",
    ".docx": "office",
}

SUPPORTED_CONFIG_EXTENSIONS = {
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".env": "env",
}

DEFAULT_EXCLUDES = [
    ".git/**",
    ".devgraph/**",
    "node_modules/**",
    "dist/**",
    "build/**",
    ".venv/**",
    "__pycache__/**",
    "*.pyc",
    "*.lock",
]

SECRET_KEY_HINTS = (
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "passwd",
    "credential",
    "private_key",
    "access_key",
    "refresh_token",
)
