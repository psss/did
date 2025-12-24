#!/bin/bash
# Test script to verify Story Points installation

echo "=== Checking Python path ==="
which python3

echo -e "\n=== Checking did installation ==="
pip show did | grep Location

echo -e "\n=== Checking if jira.py has story_points code ==="
grep -c "story_points" ~/did/did/plugins/jira.py

echo -e "\n=== Clearing Python cache ==="
find ~/did -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find ~/did -type f -name "*.pyc" -delete 2>/dev/null
echo "Cache cleared"

echo -e "\n=== Testing Story Points extraction ==="
python3 -c "
from did.plugins.jira import Issue
from unittest.mock import Mock

mock_issue = {
    'key': 'TEST-123',
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

issue = Issue(mock_issue, parent=mock_parent)
print(f'Story Points: {issue.story_points}')
print(f'Display: {issue}')
"

echo -e "\n=== Running did for last week ==="
did last week | grep -A3 "Issues commented\|Issues resolved"
