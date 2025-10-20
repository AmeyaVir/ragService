import os
import re
import sys

# Define the directory to search and the absolute imports to fix
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
MODULES_TO_FIX = [
    "config",
    "database",
    "celery_app",
    "services.gdrive_service", 
    "services.rag_service",
    "services.neo4j_service",
    "parsers.document_parser",
]

def fix_backend_imports(backend_dir: str, modules_to_fix: list):
    """
    Scans Python files in the backend directory and converts absolute 
    internal imports to relative imports, with robust encoding handling.
    """
    if not os.path.isdir(backend_dir):
        print(f"ERROR: Backend directory not found at {backend_dir}")
        sys.exit(1)

    print(f"Scanning and fixing internal imports in: {backend_dir}")
    print("-" * 50)
    
    fixed_files_count = 0
    
    target_modules_pattern = '|'.join([re.escape(m.split('.')[-1]) for m in modules_to_fix])
    
    # Regex to find absolute imports that should be relative. 
    # This remains the same logic.
    import_regex = re.compile(
        r'^(from\s+|import\s+)(' + target_modules_pattern + r')(\s+.*)$', 
        re.MULTILINE
    )

    for root, _, files in os.walk(backend_dir):
        for filename in files:
            if filename.endswith('.py'):
                filepath = os.path.join(root, filename)
                relative_filepath = os.path.relpath(filepath, BACKEND_DIR)
                
                try:
                    # FIX: Read the file content using a more permissive encoding 
                    # and the 'ignore' handler for safety, as the file is text.
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception as e:
                    print(f"  \u274c FAILED to read {relative_filepath} due to encoding error: {e}")
                    continue

                # Replace absolute imports with relative imports (e.g., 'from config' -> 'from .config')
                new_content = import_regex.sub(r'\1.\2\3', content)

                if new_content != content:
                    # Write the modified content back to the file
                    try:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"  \u2705 Fixed imports in: {relative_filepath}")
                        fixed_files_count += 1
                    except Exception as e:
                        print(f"  \u274c FAILED to write fixed content to {relative_filepath}: {e}")

    print("-" * 50)
    print(f"Import fixing complete. Total files modified: {fixed_files_count}")


if __name__ == "__main__":
    # Ensure this script is run from the project root: ~/rag-folder/code_repo_clean_exploded/
    fix_backend_imports(BACKEND_DIR, MODULES_TO_FIX)
