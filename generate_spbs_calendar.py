#!/usr/bin/env python3
"""
SPBS Calendar - Complete Pipeline
One command to generate the entire calendar from Banner database.

Usage:
    python3 generate_spbs_calendar.py 202660

This will:
1. Connect to Banner Oracle database
2. Execute SQL query for the specified term
3. Parse and filter course data
4. Generate interactive HTML calendar
"""

import sys
import subprocess

if len(sys.argv) < 2:
    print("Usage: python3 generate_spbs_calendar.py <term_code>")
    print("Example: python3 generate_spbs_calendar.py 202660")
    sys.exit(1)

term_code = sys.argv[1]
print(f"Generating SPBS calendar for term {term_code}...")

# Step 1: Query Banner and parse data
print("\nStep 1: Querying Banner database...")
# You would update generate_calendar_from_banner.py to accept term_code as argument
result = subprocess.run(['python3', 'generate_calendar_from_banner.py', term_code])
if result.returncode != 0:
    print("Failed to query Banner database")
    sys.exit(1)

# Step 2: Build HTML calendar
print("\nStep 2: Building HTML calendar...")
result = subprocess.run(['python3', 'build_spbs_calendar.py'])
if result.returncode != 0:
    print("Failed to build calendar HTML")
    sys.exit(1)

print(f"\n✓ Calendar generated successfully!")
print(f"Output: SPBS202620ScheduleFall.html")
