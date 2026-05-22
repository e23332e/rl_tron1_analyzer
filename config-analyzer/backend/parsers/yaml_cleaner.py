"""Preprocess IsaacLab YAML to remove Python-specific tags.

Handles:
- !!python/tuple (inline and block forms)
- !!python/object/apply:builtins.slice
- YAML anchors/references (&id001, *id001)
"""

import re
import yaml


def preprocess_yaml(text: str) -> str:
    """Replace Python-specific YAML tags with standard YAML constructs.

    Strategy: Process line-by-line to handle block structures correctly.
    """
    lines = text.splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # First: strip YAML anchors and replace references
        # &id001 anchors - remove them entirely
        line = re.sub(r'&\w+\s*', '', line)
        # *id001 references - replace with null
        line = re.sub(r'\*\w+', 'null', line)

        # Handle !!python/tuple appearing ANYWHERE on the line
        if '!!python/tuple' in line:
            # Inline form: key: !!python/tuple [val1, val2, ...]
            if re.search(r'!!python/tuple\s*\[', line):
                line = re.sub(r'!!python/tuple\s*\[(.+?)\]', r'[\1]', line)
            else:
                # Block form: key: !!python/tuple or - !!python/tuple
                # Remove the !!python/tuple tag, keep the structure
                line = re.sub(r'!!python/tuple\s*', '', line)

            result.append(line)
            i += 1
            continue

        # Handle !!python/object/apply:builtins.slice
        if '!!python/object/apply:' in line:
            # key: !!python/object/apply:builtins.slice → key: null
            key_match = re.match(r'^(\s*[-]?\s*\S.*):\s*!!python/object/apply:', line)
            if key_match:
                result.append(key_match.group(1) + ": null")
                i += 1
                # Skip following block sequence items (slice internals with - null, - null, - null)
                skip_depth = 0
                while i < len(lines):
                    current_line = lines[i]
                    # Detect block entry depth by indentation
                    if re.match(r'^\s+-\s+', current_line):
                        i += 1
                        continue
                    # Also skip indented null entries and continuation lines
                    if re.match(r'^\s+(null|\d+|None)\s*$', current_line):
                        i += 1
                        continue
                    # Stop if we hit a new key at the same or higher level
                    if re.match(r'^(\s{0,2}|\s{4})\w', current_line) and ':' in current_line:
                        break
                    # Skip nested !!python/object entries
                    if '!!python/object/apply:' in current_line:
                        i += 1
                        continue
                    i += 1
                continue
            else:
                line = re.sub(r'!!python/object/apply:\S+', 'null', line)

        result.append(line)
        i += 1

    return '\n'.join(result)


def safe_load_yaml(filepath: str) -> dict:
    """Load a YAML file with preprocessing for Python tags."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        raw_text = f.read()
    clean_text = preprocess_yaml(raw_text)
    return yaml.safe_load(clean_text) or {}
