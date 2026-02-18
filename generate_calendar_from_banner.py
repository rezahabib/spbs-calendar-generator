#!/usr/bin/env python3
"""
SPBS Calendar Generator - Direct Banner Integration
Connects to Banner Oracle database, extracts course schedule, generates interactive HTML calendar.

Requirements:
    pip install oracledb
    
Database credentials should be stored in environment variables or config file.
"""

import oracledb
import json
import os
import re
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================

import sys

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

# =============================================================================
# HELPER FUNCTIONS
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
    days = [name for col, name in day_map if row.get(col, '').strip()]
    return ','.join(days)

def should_include(subject, number, section, meeting_time, building):
    """Apply filtering rules"""
    sec_num = int(section) if section.isdigit() else 0
    
    # Exclude 700-799 except BAT 595-713
    if 700 <= sec_num <= 799:
        if subject == 'BAT' and number in ['595'] and section == '713':
            pass
        else:
            return False
    
    # Exclude courses with no meeting time
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

# =============================================================================
# DATABASE CONNECTION & QUERY
# =============================================================================

def fetch_banner_data(term_code):
    """Connect to Banner and fetch course data"""
    print(f"Connecting to Banner database ({DB_HOST}:{DB_PORT}/{DB_SERVICE})...")
    
    # Create connection string
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)
    
    print(f"Querying courses for term {term_code}...")
    cursor = connection.cursor()
    cursor.execute(SQL_QUERY, term_code=term_code)
    
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    print(f"Retrieved {len(rows)} rows from Banner")
    
    # Convert to dict format
    return [dict(zip(columns, row)) for row in rows]

# =============================================================================
# COURSE PARSING
# =============================================================================

def parse_courses(banner_data):
    """Parse Banner data into course objects"""
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
        
        # Special cases
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
    
    return courses

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("SPBS Calendar Generator - Direct Banner Integration")
    print("=" * 70)
    
    try:
        # Fetch data from Banner
        banner_data = fetch_banner_data(TERM_CODE)
        
        # Parse into course objects
        courses = parse_courses(banner_data)
        
        print(f"\nExtracted {len(courses)} courses:")
        print(f"  PSYC: {len([c for c in courses if c['subject'] == 'PSYC'])}")
        print(f"  BAT: {len([c for c in courses if c['subject'] == 'BAT'])}")
        print(f"  CARE: {len([c for c in courses if c['subject'] == 'CARE'])}")
        
        # Save to JSON
        json_path = '/tmp/fall2026_courses.json'
        with open(json_path, 'w') as f:
            json.dump(courses, f, indent=2)
        print(f"\nSaved course data to {json_path}")
        
        # Now run the calendar builder
        print("\nNext step: Run build_spbs_calendar.py to generate HTML")
        
    except oracledb.Error as error:
        print(f"\nDatabase error: {error}")
    except Exception as e:
        print(f"\nError: {e}")
        raise
