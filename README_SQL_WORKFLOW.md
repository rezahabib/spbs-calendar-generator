# SPBS Calendar Generator - Complete Documentation

## Overview
Automated tool to generate interactive weekly course calendars for SIUC School of Psychological and Behavioral Sciences (PSYC, BAT, CARE courses). Pulls data directly from Banner or from CSV exports.

## Two Workflows

### Workflow 1: Direct Banner Database (Recommended)
Connect directly to Banner Oracle database and generate calendar in one command.

**Requirements:**
```bash
pip install oracledb
```

**Setup:**
1. Copy `banner_config_template.py` to `banner_config.py`
2. Fill in your Banner database credentials
3. Add `banner_config.py` to `.gitignore` (never commit credentials!)

**Usage:**
```bash
# For Fall 2026
python3 generate_calendar_from_banner.py 202660

# For Spring 2027  
python3 generate_calendar_from_banner.py 202720
```

This creates `/tmp/fall2026_courses.json`, then run:
```bash
python3 build_spbs_calendar.py
```

Or use the all-in-one script:
```bash
python3 generate_spbs_calendar.py 202660
```

### Workflow 2: CSV Export (Alternative)
Export data from Banner using DBeaver or similar tool, then process the CSV.

**Steps:**
1. Run `Course_Schedule_for_Calendar.sql` in DBeaver
2. Export results as CSV
3. Run:
```bash
python3 parse_banner_csv.py
python3 build_spbs_calendar.py
```

## Files

| File | Purpose |
|------|---------|
| `generate_calendar_from_banner.py` | Queries Banner Oracle DB directly |
| `generate_spbs_calendar.py` | All-in-one wrapper (query + build) |
| `parse_banner_csv.py` | Parses CSV exports from Banner |
| `build_spbs_calendar.py` | Generates HTML calendar from JSON |
| `Course_Schedule_for_Calendar.sql` | SQL query for Banner data |
| `banner_config_template.py` | Database credentials template |

## Term Codes
- Spring: `YYYY20` (e.g., 202720 = Spring 2027)
- Summer: `YYYY40` (e.g., 202640 = Summer 2026)
- Fall: `YYYY60` (e.g., 202660 = Fall 2026)

## Filtering Rules

**Excluded:**
- Sections 700-799 (independent study/thesis) **except BAT 595-713**
- Sections 900-999 without meeting times (asynchronous online)
- Any course without meeting time

**Special Handling:**
- **PSYC 569**: Building/room left blank
- **CARE room 0323**: Building/room left blank  
- **PSYC 211**: Lectures 001-004 consolidated, labs shown separately
- **Cross-listings**: Courses with identical time/location merged (e.g., PSYC 409/509)

## Output
`SPBS202620ScheduleFall.html` - Single self-contained HTML file with:
- Three tabs (PSYC, BAT, CARE)
- Filters: days, times, course levels, distance/off-campus
- Hover tooltips for quick info
- Click modals for full details
- Responsive layout with grid alignment
- Toggle for tooltips on/off

## Database Connection Options

**Option 1: Config file** (recommended for local use)
```python
# banner_config.py
BANNER_USER = 'rmoradi'
BANNER_PASSWORD = 'your_password'
BANNER_HOST = 'banner-prod.siuc.edu'
BANNER_PORT = '1521'
BANNER_SERVICE = 'PROD'
```

**Option 2: Environment variables** (recommended for servers)
```bash
export BANNER_USER='rmoradi'
export BANNER_PASSWORD='your_password'
export BANNER_HOST='banner-prod.siuc.edu'
export BANNER_PORT='1521'
export BANNER_SERVICE='PROD'
```

## For Future Automation

**Option A: Scheduled task**
```bash
# Crontab entry to regenerate calendar when new term data available
0 6 * * MON python3 /path/to/generate_spbs_calendar.py 202660
```

**Option B: Web server integration**
Host on SPBS internal site with Flask/Django app that:
1. Triggers calendar generation on demand
2. Serves the HTML file at a permanent URL
3. Auto-refreshes when sections are updated in Banner

## Troubleshooting

**oracledb ImportError:**
```bash
pip install oracledb
```

**Database connection failed:**
- Verify credentials in `banner_config.py`
- Check VPN connection if Banner requires it
- Confirm your Banner account has read access to ODSMGR schema

**No courses extracted:**
- Check term code format (YYYYTT)
- Verify STATUS = 'A' in SQL query includes your courses
- Check subject codes match exactly ('PSYC', 'BAT', 'CARE')

## Security Notes
- **Never commit `banner_config.py`** to version control
- Add to `.gitignore` immediately
- For public GitHub repo, use environment variables instead
- Credentials should have read-only access to Banner
