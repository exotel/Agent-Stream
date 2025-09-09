#!/bin/bash
# Remove Emojis Script
# ===================
#
# This script removes all emojis and icons from the codebase
# to maintain a professional, text-only documentation style.
#
# Usage: ./scripts/remove_emojis.sh
#
# Author: Agent Stream Team
# Version: 2.0.0

set -euo pipefail

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Removing emojis from all files..."

# Function to remove emojis from a file
remove_emojis_from_file() {
 local file="$1"
 echo "Processing: $file"

 # Create a temporary file
 local temp_file=$(mktemp)

 # Remove common emojis and replace with text equivalents where appropriate
 sed -E '
 # Remove standalone emojis at start of lines
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g
 s/^[[:space:]]*[[:space:]]*//g

 # Remove emojis in log messages
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g

 # Remove bullet point emojis
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g
 s/[[:space:]]*//g

 # Clean up any double spaces left behind
 s/[[:space:]]{2,}/ /g

 # Clean up empty lines with just spaces
 s/^[[:space:]]*$//g
 ' "$file" > "$temp_file"

 # Replace original file with cleaned version
 mv "$temp_file" "$file"
}

# Process all relevant files
echo "Finding files to process..."

# Process Python files
find "$PROJECT_ROOT" -name "*.py" -not -path "*/backup/*" | while read -r file; do
 remove_emojis_from_file "$file"
done

# Process Markdown files
find "$PROJECT_ROOT" -name "*.md" -not -path "*/backup/*" | while read -r file; do
 remove_emojis_from_file "$file"
done

# Process Shell scripts
find "$PROJECT_ROOT" -name "*.sh" -not -path "*/backup/*" | while read -r file; do
 remove_emojis_from_file "$file"
done

echo "Emoji removal completed!"
echo ""
echo "Summary of changes:"
echo "- Removed all emoji characters from source files"
echo "- Cleaned up extra whitespace"
echo "- Maintained professional documentation style"
echo ""
echo "Files processed:"
echo "- Python source files (*.py)"
echo "- Markdown documentation (*.md)" 
echo "- Shell scripts (*.sh)"
echo ""
echo "Note: Backup files in ./backup/ were preserved unchanged" 