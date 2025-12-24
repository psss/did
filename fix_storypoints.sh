#!/bin/bash
set -e

echo "=== Fixing Story Points Installation ==="

echo -e "\n1. Removing all old installations..."
pip uninstall -y did 2>/dev/null || true
rm -rf ~/.local/lib/python3.13/site-packages/did*
rm -rf ~/.local/lib/python3.*/site-packages/did*

echo -e "\n2. Clearing all Python caches..."
find ~/did -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find ~/did -type f -name "*.pyc" -delete 2>/dev/null || true
find ~/.local -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
python3 -m pip cache purge 2>/dev/null || true

echo -e "\n3. Reinstalling did from modified source..."
cd ~/did
pip install --user --force-reinstall --no-cache-dir -e .

echo -e "\n4. Verifying installation..."
pip show did | grep Location

echo -e "\n5. Verifying story_points code exists..."
python3 << 'EOF'
import sys
sys.dont_write_bytecode = True
from did.plugins.jira import Issue
from unittest.mock import Mock

# Test with mock data
mock_issue = {
    'key': 'TEST-123',
    'fields': {
        'summary': 'Test issue',
        'comment': {'comments': []},
        'customfield_12310243': 5.0
    }
}
mock_parent = Mock()
mock_parent.options = Mock()
mock_parent.options.format = 'text'
mock_parent.prefix = None

issue = Issue(mock_issue, parent=mock_parent)
print(f"✓ Story Points extracted: {issue.story_points}")
print(f"✓ Display format: {issue}")
EOF

echo -e "\n6. Testing with 'did last week'..."
python3 -B $(which did) last week 2>&1 | grep -A3 "Issues commented\|Issues resolved" || echo "No issues found in last week"

echo -e "\n=== Installation Complete ==="
echo "Now run 'did last week' from your terminal"
