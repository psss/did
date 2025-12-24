#!/bin/bash
echo "=== Story Points Diagnostic ==="

echo -e "\n1. Which Python is being used?"
which python3
python3 --version

echo -e "\n2. Which did is being used?"
which did
head -1 $(which did)

echo -e "\n3. Where is did installed?"
pip show did 2>/dev/null | grep Location || pip3 show did | grep Location

echo -e "\n4. Is story_points code in the file?"
grep -c "self.story_points" ~/did/did/plugins/jira.py

echo -e "\n5. What does Python import?"
python3 << 'EOF'
import did.plugins.jira
import inspect
print(f"Loading from: {inspect.getfile(did.plugins.jira)}")

# Check if the Issue class has story_points in __init__
import dis
print("\nChecking Issue.__init__ bytecode for 'story_points':")
code = did.plugins.jira.Issue.__init__.__code__
if 'story_points' in code.co_names:
    print("✓ story_points found in bytecode")
else:
    print("✗ story_points NOT in bytecode - OLD VERSION CACHED!")

# Try to create an issue with story points
from unittest.mock import Mock
try:
    mock_issue = {
        'key': 'TEST-1',
        'fields': {
            'summary': 'Test',
            'comment': {'comments': []},
            'customfield_12310243': 5.0
        }
    }
    mock_parent = Mock()
    mock_parent.options = Mock()
    mock_parent.options.format = 'text'
    mock_parent.prefix = None
    issue = did.plugins.jira.Issue(mock_issue, parent=mock_parent)
    if hasattr(issue, 'story_points'):
        print(f"✓ Issue has story_points: {issue.story_points}")
    else:
        print("✗ Issue does NOT have story_points attribute")
except Exception as e:
    print(f"✗ Error: {e}")
EOF

echo -e "\n6. Finding ALL cached bytecode:"
find ~/.local -name "*.pyc" -path "*/did/*" 2>/dev/null | head -10

echo -e "\n=== SOLUTION ==="
echo "If story_points is NOT in bytecode, run:"
echo "  rm -rf ~/.local/lib/python*/site-packages/__pycache__"
echo "  python3 -m compileall -f ~/did/did/plugins/jira.py"
echo "  did last week"
