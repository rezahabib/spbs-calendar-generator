import csv
import json
import re

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
            pass  # include
        else:
            return False
    
    # Exclude courses with no meeting time
    if not meeting_time:
        return False
    
    # For sections 900-999 (online), include only if they have meeting times (synchronous)
    # Already handled above - if no meeting_time, already excluded
    
    return True

# Parse CSV
courses = []
psyc211_sections = {}  # Track PSYC 211 lecture vs lab meetings

with open('/mnt/user-data/uploads/SCHEDULE_OFFERING_MEETING_TIME_202602172327.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        subject, number = parse_course_id(row['COURSE_IDENTIFICATION'])
        if not subject or subject not in ['PSYC', 'BAT', 'CARE']:
            continue
        
        section = row['OFFERING_NUMBER'].strip()
        meeting_time = row['BEGIN_TIME'].strip()
        building = row['BUILDING'].strip()
        room = row['ROOM'].strip()
        
        if not should_include(subject, number, section, meeting_time, building):
            continue
        
        # Special cases
        # PSYC 569: blank building/room
        if subject == 'PSYC' and number == '569':
            building = ""
            room = ""
        
        # CARE courses with room "0323": blank both
        if subject == 'CARE' and room == '0323':
            building = ""
            room = ""
        
        start_time = format_time(meeting_time)
        end_time = format_time(row['END_TIME'].strip())
        days = assemble_days(row)
        
        if not start_time or not days:
            continue
        
        # Special handling for PSYC 211 - collect all meetings
        if subject == 'PSYC' and number == '211':
            key = f"{section}_{building}_{room}"
            if section not in psyc211_sections:
                psyc211_sections[section] = []
            psyc211_sections[section].append({
                'crn': row['COURSE_REFERENCE_NUMBER'].strip(),
                'title': row['TITLE_LONG_DESC'].strip(),
                'credits': row['MIN_CONTACT_HOURS'].strip(),
                'days': days,
                'start': start_time,
                'end': end_time,
                'building': building,
                'room': room,
                'startDate': row['START_DATE'].strip().split()[0] if row['START_DATE'].strip() else '',
                'endDate': row['END_DATE'].strip().split()[0] if row['END_DATE'].strip() else '',
                'scheduleType': row['INSTRUCTION_METHOD_DESC'].strip()
            })
            continue
        
        course = {
            'subject': subject,
            'number': number,
            'section': section,
            'crn': row['COURSE_REFERENCE_NUMBER'].strip(),
            'title': row['TITLE_LONG_DESC'].strip(),
            'credits': row['MIN_CONTACT_HOURS'].strip(),
            'term': 'Fall 2026',
            'instructor': '',  # Not populated yet
            'meeting': {
                'days': days,
                'start': start_time,
                'end': end_time,
                'building': building,
                'room': room,
                'startDate': row['START_DATE'].strip().split()[0] if row['START_DATE'].strip() else '',
                'endDate': row['END_DATE'].strip().split()[0] if row['END_DATE'].strip() else ''
            },
            'campus': 'Carbondale',
            'scheduleType': row['INSTRUCTION_METHOD_DESC'].strip()
        }
        courses.append(course)

# Process PSYC 211 - consolidate lectures, add labs with L suffix
if psyc211_sections:
    # All sections share common lecture time: T/R 09:35-10:50 in LWSN 0171
    # Create one consolidated lecture entry
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
            'instructor': '',
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
    
    # Add individual lab sections (the ones NOT in LWSN 0171)
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
                'instructor': '',
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

print(f"Extracted {len(courses)} courses")
print(f"PSYC: {len([c for c in courses if c['subject'] == 'PSYC'])}")
print(f"BAT: {len([c for c in courses if c['subject'] == 'BAT'])}")
print(f"CARE: {len([c for c in courses if c['subject'] == 'CARE'])}")

# Save to JSON
with open('/tmp/fall2026_courses_csv.json', 'w') as f:
    json.dump(courses, f, indent=2)
print("Saved to /tmp/fall2026_courses_csv.json")
