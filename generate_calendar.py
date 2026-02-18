#!/usr/bin/env python3
"""
SPBS Calendar Generator - All-in-One
One command to generate the entire calendar from Banner database to HTML.

Usage:
    python3 generate_calendar.py 202660
    
This will:
1. Connect to Banner Oracle database
2. Execute SQL query for the specified term
3. Parse and filter course data
4. Apply PSYC 211 consolidation and cross-listing merges
5. Generate interactive HTML calendar
"""

import sys
import os

# Import the query and build functions
import oracledb
import json
import re
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================

# Term code from command line or default
TERM_CODE = sys.argv[1] if len(sys.argv) > 1 else '202660'

# Database connection - try config file first, then environment variables
try:
    from banner_config import BANNER_USER, BANNER_PASSWORD, BANNER_HOST, BANNER_PORT, BANNER_SERVICE
    DB_USER = BANNER_USER
    DB_PASSWORD = BANNER_PASSWORD
    DB_HOST = BANNER_HOST
    DB_PORT = BANNER_PORT
    DB_SERVICE = BANNER_SERVICE
except ImportError:
    DB_USER = os.getenv('BANNER_USER', 'your_username')
    DB_PASSWORD = os.getenv('BANNER_PASSWORD', 'your_password')
    DB_HOST = os.getenv('BANNER_HOST', 'banner-db-host')
    DB_PORT = os.getenv('BANNER_PORT', '1521')
    DB_SERVICE = os.getenv('BANNER_SERVICE', 'banner_service_name')

# SQL Query
SQL_QUERY = """
SELECT so.ACADEMIC_PERIOD, so.COURSE_IDENTIFICATION, so.COURSE_REFERENCE_NUMBER, 
       so.OFFERING_NUMBER, so.TITLE_LONG_DESC, so.MIN_CONTACT_HOURS, so.MAX_CONTACT_HOURS,
       so.INSTRUCTION_METHOD_DESC, so.MAXIMUM_ENROLLMENT, so.ACTUAL_ENROLLMENT, 
       so.PRIMARY_INSTRUCTOR_FIRST_NAME, so.PRIMARY_INSTRUCTOR_LAST_NAME, so.PRIMARY_INSTRUCTOR_ID,
       mt.START_DATE, mt.END_DATE, mt.BEGIN_TIME, mt.END_TIME, mt.BUILDING, mt.ROOM, 
       mt.MONDAY_IND, mt.TUESDAY_IND, mt.WEDNESDAY_IND, mt.THURSDAY_IND, mt.FRIDAY_IND, 
       mt.SATURDAY_IND, mt.SUNDAY_IND 
FROM ODSMGR.SCHEDULE_OFFERING so 
LEFT JOIN ODSMGR.MEETING_TIME mt ON so.COURSE_REFERENCE_NUMBER = mt.COURSE_REFERENCE_NUMBER 
    AND so.ACADEMIC_PERIOD = mt.ACADEMIC_PERIOD  
WHERE so.ACADEMIC_PERIOD = :term_code 
  AND (so.SUBJECT = 'PSYC' OR so.SUBJECT = 'BAT' OR so.SUBJECT = 'CARE') 
  AND so.STATUS = 'A'
"""

print("=" * 70)
print("SPBS Calendar Generator - All-in-One")
print("=" * 70)
print(f"Term: {TERM_CODE}")
print()

# =============================================================================
# STEP 1: QUERY BANNER DATABASE
# =============================================================================

def parse_course_id(course_id):
    """Parse 'PSYC211' -> ('PSYC', '211')"""
    match = re.match(r'^([A-Z]+)(\d+[A-Z]?)$', course_id.strip())
    if match:
        return match.group(1), match.group(2)
    return None, None

def format_time(military):
    """Convert '1100' -> '11:00 AM', '1315' -> '01:15 PM'"""
    if not military or len(military) != 4:
        return ""
    h = int(military[:2])
    m = military[2:4]
    if h == 0:
        return f"12:{m} AM"
    elif h < 12:
        return f"{h}:{m} AM"
    elif h == 12:
        return f"12:{m} PM"
    else:
        return f"{h-12:02d}:{m} PM"

def assemble_days(row):
    """Build 'Monday,Tuesday,Thursday' from boolean columns"""
    day_map = [
        ('MONDAY_IND', 'Monday'),
        ('TUESDAY_IND', 'Tuesday'),
        ('WEDNESDAY_IND', 'Wednesday'),
        ('THURSDAY_IND', 'Thursday'),
        ('FRIDAY_IND', 'Friday'),
        ('SATURDAY_IND', 'Saturday'),
        ('SUNDAY_IND', 'Sunday')
    ]
    days = []
    for col, name in day_map:
        val = row.get(col, '')
        if val and str(val).strip():
            days.append(name)
    return ','.join(days)

def should_include(subject, number, section, meeting_time, building):
    """Apply filtering rules"""
    sec_num = int(section) if section.isdigit() else 0
    
    if 700 <= sec_num <= 799:
        if subject == 'BAT' and number in ['595'] and section == '713':
            pass
        else:
            return False
    
    if not meeting_time:
        return False
    
    return True

def format_instructor(first, last):
    """Format instructor name"""
    if not first and not last:
        return ""
    if first and last:
        return f"{first} {last}"
    return last or first or ""

print("Step 1: Querying Banner database...")
print(f"  Host: {DB_HOST}:{DB_PORT}/{DB_SERVICE}")

try:
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)
    
    cursor = connection.cursor()
    cursor.execute(SQL_QUERY, term_code=TERM_CODE)
    
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    print(f"  Retrieved {len(rows)} rows")
    
except oracledb.Error as error:
    print(f"\nDatabase error: {error}")
    sys.exit(1)

# =============================================================================
# STEP 2: PARSE COURSE DATA
# =============================================================================

print("\nStep 2: Parsing course data...")

banner_data = [dict(zip(columns, row)) for row in rows]
courses = []
psyc211_sections = {}

for row in banner_data:
    subject, number = parse_course_id(row['COURSE_IDENTIFICATION'])
    if not subject or subject not in ['PSYC', 'BAT', 'CARE']:
        continue
    
    section = row['OFFERING_NUMBER'].strip()
    meeting_time = str(row['BEGIN_TIME']).strip() if row['BEGIN_TIME'] else ''
    building = row['BUILDING'].strip() if row['BUILDING'] else ''
    room = row['ROOM'].strip() if row['ROOM'] else ''
    
    if not should_include(subject, number, section, meeting_time, building):
        continue
    
    if subject == 'PSYC' and number == '569':
        building = ""
        room = ""
    
    if subject == 'CARE' and room == '0323':
        building = ""
        room = ""
    
    start_time = format_time(meeting_time)
    end_time = format_time(str(row['END_TIME']).strip() if row['END_TIME'] else '')
    days = assemble_days(row)
    
    if not start_time or not days:
        continue
    
    instructor = format_instructor(
        row.get('PRIMARY_INSTRUCTOR_FIRST_NAME', ''),
        row.get('PRIMARY_INSTRUCTOR_LAST_NAME', '')
    )
    
    # PSYC 211 special handling
    if subject == 'PSYC' and number == '211':
        if section not in psyc211_sections:
            psyc211_sections[section] = []
        psyc211_sections[section].append({
            'crn': row['COURSE_REFERENCE_NUMBER'].strip(),
            'title': row['TITLE_LONG_DESC'].strip(),
            'credits': str(row['MIN_CONTACT_HOURS']).strip(),
            'days': days,
            'start': start_time,
            'end': end_time,
            'building': building,
            'room': room,
            'startDate': str(row['START_DATE']).split()[0] if row['START_DATE'] else '',
            'endDate': str(row['END_DATE']).split()[0] if row['END_DATE'] else '',
            'scheduleType': row['INSTRUCTION_METHOD_DESC'].strip(),
            'instructor': instructor
        })
        continue
    
    course = {
        'subject': subject,
        'number': number,
        'section': section,
        'crn': row['COURSE_REFERENCE_NUMBER'].strip(),
        'title': row['TITLE_LONG_DESC'].strip(),
        'credits': str(row['MIN_CONTACT_HOURS']).strip(),
        'term': 'Fall 2026',
        'instructor': instructor,
        'meeting': {
            'days': days,
            'start': start_time,
            'end': end_time,
            'building': building,
            'room': room,
            'startDate': str(row['START_DATE']).split()[0] if row['START_DATE'] else '',
            'endDate': str(row['END_DATE']).split()[0] if row['END_DATE'] else ''
        },
        'campus': 'Carbondale',
        'scheduleType': row['INSTRUCTION_METHOD_DESC'].strip()
    }
    courses.append(course)

# Process PSYC 211
if psyc211_sections:
    lecture_meeting = None
    for sec, meetings in psyc211_sections.items():
        lec = [m for m in meetings if m['building'] == 'LWSN' and m['room'] == '0171']
        if lec:
            lecture_meeting = lec[0]
            break
    
    if lecture_meeting:
        courses.append({
            'subject': 'PSYC',
            'number': '211',
            'section': '001-004',
            'crn': lecture_meeting['crn'],
            'title': lecture_meeting['title'],
            'credits': lecture_meeting['credits'],
            'term': 'Fall 2026',
            'instructor': lecture_meeting['instructor'],
            'meeting': {
                'days': lecture_meeting['days'],
                'start': lecture_meeting['start'],
                'end': lecture_meeting['end'],
                'building': lecture_meeting['building'],
                'room': lecture_meeting['room'],
                'startDate': lecture_meeting['startDate'],
                'endDate': lecture_meeting['endDate']
            },
            'campus': 'Carbondale',
            'scheduleType': lecture_meeting['scheduleType']
        })
    
    for sec, meetings in sorted(psyc211_sections.items()):
        labs = [m for m in meetings if not (m['building'] == 'LWSN' and m['room'] == '0171')]
        for lab in labs:
            courses.append({
                'subject': 'PSYC',
                'number': '211',
                'section': f'{sec}L',
                'crn': lab['crn'],
                'title': lab['title'],
                'credits': lab['credits'],
                'term': 'Fall 2026',
                'instructor': lab['instructor'],
                'meeting': {
                    'days': lab['days'],
                    'start': lab['start'],
                    'end': lab['end'],
                    'building': lab['building'],
                    'room': lab['room'],
                    'startDate': lab['startDate'],
                    'endDate': lab['endDate']
                },
                'campus': 'Carbondale',
                'scheduleType': lab['scheduleType']
            })

print(f"  Extracted {len(courses)} courses:")
print(f"    PSYC: {len([c for c in courses if c['subject'] == 'PSYC'])}")
print(f"    BAT: {len([c for c in courses if c['subject'] == 'BAT'])}")
print(f"    CARE: {len([c for c in courses if c['subject'] == 'CARE'])}")

# Save intermediate JSON
with open('/tmp/fall2026_courses.json', 'w') as f:
    json.dump(courses, f, indent=2)

# =============================================================================
# STEP 3: BUILD HTML CALENDAR
# =============================================================================

print("\nStep 3: Building HTML calendar...")

# Import and run the builder
try:
    import build_spbs_calendar
    print(f"\n✓ Calendar generated successfully!")
    print(f"  Output: SPBS202620ScheduleFall.html")
    print(f"  Open in browser to view")
    
except ImportError:
    print("  Running builder directly...")
    import subprocess
    result = subprocess.run([sys.executable, 'build_spbs_calendar.py'])
    if result.returncode == 0:
        print(f"\n✓ Calendar generated successfully!")
        print(f"  Output: SPBS202620ScheduleFall.html")
    else:
        print("\nError building calendar")
        sys.exit(1)
