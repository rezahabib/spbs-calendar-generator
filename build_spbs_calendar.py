import json, re
import sys

# Get term code from command line or use default
TERM_CODE = sys.argv[1] if len(sys.argv) > 1 else '202660'
json_filename = f'courses_{TERM_CODE}.json'

with open(json_filename) as f:
    courses = json.load(f)

def js_str(s):
    return s.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')

def merge_crosslisted(course_list):
    from collections import OrderedDict
    groups = OrderedDict()
    for c in course_list:
        m = c['meeting']
        key = (m['days'], m['start'], m['end'], m['building'], m['room'])
        if key not in groups:
            groups[key] = []
        groups[key].append(c)
    merged = []
    for key, grp in groups.items():
        if len(grp) == 1:
            merged.append(grp[0])
        else:
            base = grp[0]
            # Only show unique titles (avoid "Intro Psych / Intro Psych" for same-titled cross-listings)
            unique_titles = list(dict.fromkeys(g['title'] for g in grp))
            combined_title = ' / '.join(unique_titles)
            combined_number = ' / '.join(f"{g['subject']} {g['number']}" for g in grp)
            combined_section = ' / '.join(g['section'] for g in grp)
            combined_crn = ' / '.join(g['crn'] for g in grp)
            combined_instructor = ' / '.join(g['instructor'] for g in grp if g['instructor']) or ''
            merged.append({
                'title': combined_title,
                'subject': base['subject'],
                'number': combined_number,
                'section': combined_section,
                'crn': combined_crn,
                'credits': base['credits'],
                'term': base['term'],
                'instructor': combined_instructor,
                'meeting': base['meeting'],
                'campus': base['campus'],
                'scheduleType': base['scheduleType']
            })
    return merged

def make_source(prefix):
    """Generate JavaScript source for both grid and async courses"""
    filtered = [c for c in courses if c['subject'] == prefix.upper()]
    
    # Separate async courses BEFORE merging
    # (Async courses can't be reliably cross-listed without meeting times)
    grid_courses = [c for c in filtered if not c.get('isAsync', False)]
    async_courses = [c for c in filtered if c.get('isAsync', False)]
    
    # Only merge grid courses
    grid_courses = merge_crosslisted(grid_courses)
    
    def format_course(c):
        m = c['meeting']
        return (
            f'{{ title: "{js_str(c["title"])}", subject: "{c["subject"]}", number: "{js_str(c["number"])}", '
            f'section: "{js_str(c["section"])}", crn: "{js_str(c["crn"])}", credits: "{c["credits"]}", '
            f'term: "Fall 2026", instructor: "{js_str(c["instructor"])}", '
            f'meeting: {{ days: "{m["days"]}", start: "{m["start"]}", end: "{m["end"]}", '
            f'building: "{js_str(m["building"])}", room: "{m["room"]}", '
            f'startDate: "{m["startDate"]}", endDate: "{m["endDate"]}" }}, '
            f'campus: "{js_str(c["campus"])}", scheduleType: "{c["scheduleType"]}", '
            f'isAsync: {str(c.get("isAsync", False)).lower()} }}'
        )
    
    grid_lines = [' ' * 16 + format_course(c) for c in grid_courses]
    async_lines = [' ' * 16 + format_course(c) for c in async_courses]
    
    return ',\n'.join(grid_lines), ',\n'.join(async_lines)

psyc_grid, psyc_async = make_source('psyc')
bat_grid, bat_async = make_source('bat')
care_grid, care_async = make_source('care')

html = '''<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <title>Fall 2026 Weekly Calendars — Psychology, BAT &amp; CARE</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
            :root {
                --bg: #ffffff;
                --text: #0f172a;
                --muted: #475569;
                --line: #e5e7eb;
                --shadow: 0 10px 30px rgba(0,0,0,0.08);
                --gap: 6px;
                --min-height: 36px;
                --panel: #ffffff;
                --modal-backdrop: rgba(0,0,0,0.35);
                --modal-bg: #ffffff;
                --meta: #334155;
                --tab: #f8fafc;
                --tab-active: #0ea5e9;
                --tab-active-border: #0284c7;
                --tab-text: #0f172a;
                --tab-active-text: #ffffff;
                --header-bg: #f8fafc;
                --chip-bg: #f1f5f9;
                --notice-bg: #f8fafc;
                --event-text: #0f172a;
                --event-border-alpha: 0.06;
                --control-bg: #f8fafc;
                --control-border: #e5e7eb;
                --control-text: #0f172a;
                --hover: #f1f5f9;
            }
            @media (prefers-color-scheme: dark) {
                :root {
                    --bg: #1e1e1e;
                    --text: #e5e7eb;
                    --muted: #9ca3af;
                    --line: #3a3a3a;
                    --shadow: 0 10px 30px rgba(0,0,0,0.4);
                    --panel: #282828;
                    --modal-backdrop: rgba(0,0,0,0.55);
                    --modal-bg: #282828;
                    --meta: #e2e8f0;
                    --tab: #252525;
                    --tab-active: #2563eb;
                    --tab-active-border: #1d4ed8;
                    --tab-text: #e5e7eb;
                    --tab-active-text: #ffffff;
                    --header-bg: #252525;
                    --chip-bg: #1e1e1e;
                    --notice-bg: #1e1e1e;
                    --event-text: #1e1e1e;
                    --event-border-alpha: 0.25;
                    --control-bg: #252525;
                    --control-border: #3a3a3a;
                    --control-text: #e5e7eb;
                    --hover: #323232;
                }
                .event { opacity: 0.85; }
                .event:hover { opacity: 1; }
            }

            html, body { margin: 0; padding: 0; height: 100%; background: var(--bg); color: var(--text);
                font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Inter, "Helvetica Neue", Arial; }
            .container { max-width: 100%; margin: 24px auto 48px; padding: 0 24px; }
            header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
            h1 { font-size: 22px; margin: 0; letter-spacing: 0.2px; }
            .term-chip { background: var(--chip-bg); border: 1px solid var(--line); color: var(--muted);
                padding: 4px 10px; border-radius: 999px; font-size: 12px; margin-left: 8px; }

            .tabs { display: flex; gap: 8px; margin: 12px 0 20px; flex-wrap: wrap; }
            .tab { padding: 8px 18px; border-radius: 8px; border: 1px solid var(--line);
                background: var(--tab); color: var(--tab-text); font-size: 14px; font-weight: 500;
                cursor: pointer; transition: background 0.15s, color 0.15s, border-color 0.15s; }
            .tab:hover { background: var(--line); }
            .tab.active { background: var(--tab-active); border-color: var(--tab-active-border); color: var(--tab-active-text); }

            .filters { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px;
                background: var(--header-bg); border: 1px solid var(--line); border-radius: 12px;
                padding: 14px 16px; margin-bottom: 16px; }
            .filter-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; font-size: 13px; }
            .filter-row label { display: flex; align-items: center; gap: 4px; cursor: pointer; }
            .filter-row input[type="checkbox"] { accent-color: var(--tab-active); }
            .filter-row input[type="range"] { accent-color: var(--tab-active); width: 120px; }
            .levels-row { grid-column: 1 / -1; }
            .search-box { grid-column: 1 / -1; gap: 8px; }
            .search-box input[type="text"] { flex: 1; min-width: 200px; padding: 6px 10px; border-radius: 7px;
                border: 1px solid var(--control-border); background: var(--control-bg); color: var(--control-text); font-size: 13px; }
            .filter-actions { display: flex; gap: 6px; }
            .btn { padding: 5px 12px; border-radius: 7px; border: 1px solid var(--line); background: var(--control-bg);
                color: var(--control-text); font-size: 12px; cursor: pointer; font-weight: 500; }
            .btn:hover { background: var(--line); }

            .cal-wrap { display: none; }
            .cal-wrap.active { display: block; overflow-x: auto; }

            .calendar { border: 1px solid var(--line); border-radius: 14px; overflow: hidden; box-shadow: var(--shadow); width: 100%; box-sizing: border-box; }
            .calendar-grid { display: grid; grid-template-columns: 90px repeat(5, 1fr); min-width: 700px; width: 100%; box-sizing: border-box; }
            .cell { border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); }
            .cell:last-child { border-right: none; }
            .cell.header { background: var(--header-bg); padding: 10px 8px; font-size: 12px; font-weight: 600;
                text-align: center; letter-spacing: 0.3px; text-transform: uppercase; color: var(--muted); border-bottom: 2px solid var(--line); }
            .cell.time-col { background: var(--header-bg); position: relative; }
            .time-slot { height: 60px; box-sizing: border-box; display: flex; align-items: flex-start; border-top: 1px solid var(--line); }
            .time-slot:first-child { border-top: none; }
            .time-label { font-size: 11px; color: var(--muted); padding-left: 6px; white-space: nowrap; margin-top: 3px; line-height: 14px; }
            .cell.day-col { position: relative; height: 780px; }
            .day-body { position: relative; width: 100%; height: 100%;
                background-image: repeating-linear-gradient(to bottom, var(--line) 0px, var(--line) 1px, transparent 1px, transparent 60px);
                background-position: 0 60px; }

            .event { position: absolute; border-radius: 8px; border: 1px solid; padding: 5px 7px;
                box-sizing: border-box; overflow: hidden; cursor: pointer;
                background: linear-gradient(135deg, var(--bg1) 0%, var(--bg2) 100%);
                transition: filter 0.12s, box-shadow 0.12s;
                box-shadow: 0 1px 4px rgba(0,0,0,calc(var(--event-border-alpha)*3)); }
            .event:hover { filter: brightness(0.95); box-shadow: 0 3px 10px rgba(0,0,0,0.14); z-index: 100 !important; }
            .tooltip {
                position: fixed; z-index: 9999; pointer-events: none;
                background: var(--modal-bg); border: 1px solid var(--line);
                border-radius: 10px; padding: 10px 14px;
                box-shadow: 0 6px 24px rgba(0,0,0,0.18);
                font-size: 12.5px; line-height: 1.55; max-width: 260px;
                opacity: 0; transition: opacity 0.15s ease;
            }
            .tooltip.visible { opacity: 1; }
            .tooltip-title { font-weight: 700; font-size: 13px; margin-bottom: 4px; color: var(--fg); }
            .tooltip-row { color: var(--muted); }
            .tooltip-row span { color: var(--fg); font-weight: 500; }
            .tooltip-toggle { margin-left: auto; font-size: 12px; padding: 4px 12px; border-radius: 20px; border: 1px solid var(--line); background: var(--tab-active); color: #fff; cursor: pointer; white-space: nowrap; }
            .tooltip-toggle.off { background: var(--bg); color: var(--muted); }
            .event .title { font-size: 11px; font-weight: 700; color: var(--event-text); line-height: 1.3;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .event .meta { font-size: 10px; color: var(--event-text); opacity: 0.75; line-height: 1.3;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 1px; }

            .modal { display: none; position: fixed; inset: 0; background: var(--modal-backdrop);
                z-index: 1000; align-items: center; justify-content: center; padding: 16px; }
            .modal.open { display: flex; }
            .modal-card { background: var(--modal-bg); border-radius: 16px; max-width: 560px; width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.25); overflow: hidden; }
            .modal-header { display: flex; align-items: center; justify-content: space-between;
                padding: 16px 20px 12px; border-bottom: 1px solid var(--line); }
            .modal-title { font-size: 16px; font-weight: 700; color: var(--text); }
            .close-btn { background: none; border: none; font-size: 13px; color: var(--muted); cursor: pointer;
                padding: 4px 10px; border-radius: 6px; border: 1px solid var(--line); }
            .close-btn:hover { background: var(--line); }
            .modal-body { padding: 16px 20px 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px 20px; }
            .detail { display: flex; flex-direction: column; gap: 2px; }
            .detail span { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); }
            .detail p { margin: 0; font-size: 14px; color: var(--text); }

            .notice { padding: 10px 16px; background: var(--notice-bg); border-top: 1px solid var(--line);
                font-size: 12px; color: var(--muted); }

            .cal-content-wrapper { display: flex; gap: 24px; align-items: flex-start; }
            .calendar-container { flex: 1; min-width: 0; }
            
            .async-section { 
                width: 320px; 
                flex-shrink: 0;
                position: sticky;
                top: 20px;
                max-height: calc(100vh - 40px);
                overflow-y: auto;
            }
            .async-section h3 { 
                font-size: 16px; 
                font-weight: 700; 
                margin: 0 0 12px 0; 
                color: var(--text);
                padding: 12px 16px;
                background: var(--panel);
                border: 1px solid var(--line);
                border-radius: 8px 8px 0 0;
            }
            .async-list { 
                display: flex; 
                flex-direction: column; 
                gap: 8px;
            }
            .async-item { 
                padding: 12px 16px; 
                background: var(--panel); 
                border: 1px solid var(--line); 
                border-radius: 8px; 
                cursor: pointer; 
                transition: all 0.2s ease;
            }
            .async-item:hover { 
                background: var(--hover); 
                box-shadow: 0 2px 8px rgba(0,0,0,0.1); 
                transform: translateX(-2px);
            }
            .async-item-title { font-size: 13px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
            .async-item-meta { font-size: 12px; color: var(--muted); }

            @media (max-width: 900px) {
                .calendar-grid { grid-template-columns: 50px repeat(5, 1fr); }
                .filters { grid-template-columns: 1fr; }
                .modal-body { grid-template-columns: 1fr; }
                .event .meta { white-space: normal; }
                .cal-content-wrapper { flex-direction: column; }
                .async-section { 
                    width: 100%; 
                    position: static;
                    max-height: none;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>
                    Fall 2026 — Weekly Class Calendars
                    <span class="term-chip">Aug 17–Dec 11/13</span>
                </h1>
            </header>

            <nav class="tabs" role="tablist" aria-label="Calendars">
                <button class="tab active" data-target="psyc" role="tab" aria-selected="true" aria-controls="cal-psyc">Psychology (PSYC)</button>
                <button class="tab" data-target="bat" role="tab" aria-selected="false" aria-controls="cal-bat">Behavior Analysis &amp; Therapy (BAT)</button>
                <button class="tab" data-target="care" role="tab" aria-selected="false" aria-controls="cal-care">Counseling &amp; Rehabilitation (CARE)</button>
                <button id="tooltipToggle" class="tooltip-toggle" aria-pressed="true" title="Toggle hover tooltips">Tooltips: On</button>
            </nav>

            <!-- PSYC Filters -->
            <section class="filters" id="filters-psyc" aria-label="PSYC filters">
                <div class="filter-row" data-prefix="psyc">
                    <label>Days:</label>
                    <label><input type="checkbox" data-role="day" value="Monday" checked /> Mon</label>
                    <label><input type="checkbox" data-role="day" value="Tuesday" checked /> Tue</label>
                    <label><input type="checkbox" data-role="day" value="Wednesday" checked /> Wed</label>
                    <label><input type="checkbox" data-role="day" value="Thursday" checked /> Thu</label>
                    <label><input type="checkbox" data-role="day" value="Friday" checked /> Fri</label>
                </div>
                <div class="filter-row" data-prefix="psyc">
                    <label>Time:</label>
                    <span>Start</span>
                    <input type="range" min="8" max="20" step="1" value="8" data-role="start" />
                    <span>End</span>
                    <input type="range" min="9" max="21" step="1" value="21" data-role="end" />
                </div>
                <div class="filter-row levels-row" data-prefix="psyc">
                    <label>Levels:</label>
                    <label><input type="checkbox" data-role="level" value="100" checked />100</label>
                    <label><input type="checkbox" data-role="level" value="200" checked />200</label>
                    <label><input type="checkbox" data-role="level" value="300" checked />300</label>
                    <label><input type="checkbox" data-role="level" value="400" checked />400</label>
                    <label><input type="checkbox" data-role="level" value="500" checked />500</label>
                </div>
                <div class="filter-row search-box" data-prefix="psyc">
                    <input type="text" data-role="search" placeholder="Search: 331, 44* (wildcard), title, instructor..." />
                    <div class="filter-actions">
                        <button class="btn" data-role="showall">Show all</button>
                        <button class="btn" data-role="reset">Reset</button>
                        <button class="btn" data-role="apply">Apply</button>
                    </div>
                </div>
            </section>

            <!-- Psychology Calendar -->
            <section id="cal-psyc" class="cal-wrap active" aria-labelledby="tab-psyc">
                <div class="cal-content-wrapper">
                    <div class="calendar-container">
                        <div class="calendar">
                            <div class="calendar-grid">
                                <div class="cell header">Time</div>
                                <div class="cell header">Monday</div>
                                <div class="cell header">Tuesday</div>
                                <div class="cell header">Wednesday</div>
                                <div class="cell header">Thursday</div>
                                <div class="cell header">Friday</div>
                                <div class="cell time-col">
                                    <div class="time-slot"><span class="time-label">8:00 AM</span></div>
                                    <div class="time-slot"><span class="time-label">9:00 AM</span></div>
                                    <div class="time-slot"><span class="time-label">10:00 AM</span></div>
                                    <div class="time-slot"><span class="time-label">11:00 AM</span></div>
                                    <div class="time-slot"><span class="time-label">12:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">1:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">2:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">3:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">4:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">5:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">6:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">7:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">8:00 PM</span></div>
                                </div>
                                <div class="cell day-col"><div class="day-body" id="psyc-Monday"></div></div>
                                <div class="cell day-col"><div class="day-body" id="psyc-Tuesday"></div></div>
                                <div class="cell day-col"><div class="day-body" id="psyc-Wednesday"></div></div>
                                <div class="cell day-col"><div class="day-body" id="psyc-Thursday"></div></div>
                                <div class="cell day-col"><div class="day-body" id="psyc-Friday"></div></div>
                            </div>
                            <div class="notice">
                                Use the filters above to refine by day, time, level, distance/off-campus, or search by number/title/instructor.
                            </div>
                        </div>
                    </div>
                    <div class="async-section" id="psyc-async-section" style="display: none;">
                        <h3>Online Asynchronous</h3>
                        <div class="async-list" id="psyc-async-list"></div>
                    </div>
                </div>
            </section>

            <!-- BAT Filters -->
            <section class="filters" id="filters-bat" aria-label="BAT filters" style="display: none;">
                <div class="filter-row" data-prefix="bat">
                    <label>Days:</label>
                    <label><input type="checkbox" data-role="day" value="Monday" checked /> Mon</label>
                    <label><input type="checkbox" data-role="day" value="Tuesday" checked /> Tue</label>
                    <label><input type="checkbox" data-role="day" value="Wednesday" checked /> Wed</label>
                    <label><input type="checkbox" data-role="day" value="Thursday" checked /> Thu</label>
                    <label><input type="checkbox" data-role="day" value="Friday" checked /> Fri</label>
                </div>
                <div class="filter-row" data-prefix="bat">
                    <label>Time:</label>
                    <span>Start</span>
                    <input type="range" min="8" max="20" step="1" value="8" data-role="start" />
                    <span>End</span>
                    <input type="range" min="9" max="21" step="1" value="21" data-role="end" />
                </div>
                <div class="filter-row levels-row" data-prefix="bat">
                    <label>Levels:</label>
                    <label><input type="checkbox" data-role="level" value="200" checked />200</label>
                    <label><input type="checkbox" data-role="level" value="500" checked />500</label>
                </div>
                <div class="filter-row search-box" data-prefix="bat">
                    <input type="text" data-role="search" placeholder="Search: 503, 5* (wildcard), title, instructor..." />
                    <div class="filter-actions">
                        <button class="btn" data-role="showall">Show all</button>
                        <button class="btn" data-role="reset">Reset</button>
                        <button class="btn" data-role="apply">Apply</button>
                    </div>
                </div>
            </section>

            <!-- BAT Calendar -->
            <section id="cal-bat" class="cal-wrap" aria-labelledby="tab-bat">
                <div class="cal-content-wrapper">
                    <div class="calendar-container">
                        <div class="calendar">
                            <div class="calendar-grid">
                                <div class="cell header">Time</div>
                                <div class="cell header">Monday</div>
                                <div class="cell header">Tuesday</div>
                                <div class="cell header">Wednesday</div>
                                <div class="cell header">Thursday</div>
                                <div class="cell header">Friday</div>
                                <div class="cell time-col">
                                    <div class="time-slot"><span class="time-label">8:00 AM</span></div>
                                    <div class="time-slot"><span class="time-label">9:00 AM</span></div>
                                    <div class="time-slot"><span class="time-label">10:00 AM</span></div>
                                    <div class="time-slot"><span class="time-label">11:00 AM</span></div>
                                    <div class="time-slot"><span class="time-label">12:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">1:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">2:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">3:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">4:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">5:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">6:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">7:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">8:00 PM</span></div>
                                </div>
                                <div class="cell day-col"><div class="day-body" id="bat-Monday"></div></div>
                                <div class="cell day-col"><div class="day-body" id="bat-Tuesday"></div></div>
                                <div class="cell day-col"><div class="day-body" id="bat-Wednesday"></div></div>
                                <div class="cell day-col"><div class="day-body" id="bat-Thursday"></div></div>
                                <div class="cell day-col"><div class="day-body" id="bat-Friday"></div></div>
                            </div>
                            <div class="notice">
                                Use the filters above to refine by day, time, level, distance/off-campus, or search by number/title/instructor.
                            </div>
                        </div>
                    </div>
                    <div class="async-section" id="bat-async-section" style="display: none;">
                        <h3>Online Asynchronous</h3>
                        <div class="async-list" id="bat-async-list"></div>
                    </div>
                </div>
            </section>

            <!-- CARE Filters -->
            <section class="filters" id="filters-care" aria-label="CARE filters" style="display: none;">
                <div class="filter-row" data-prefix="care">
                    <label>Days:</label>
                    <label><input type="checkbox" data-role="day" value="Monday" checked /> Mon</label>
                    <label><input type="checkbox" data-role="day" value="Tuesday" checked /> Tue</label>
                    <label><input type="checkbox" data-role="day" value="Wednesday" checked /> Wed</label>
                    <label><input type="checkbox" data-role="day" value="Thursday" checked /> Thu</label>
                    <label><input type="checkbox" data-role="day" value="Friday" checked /> Fri</label>
                </div>
                <div class="filter-row" data-prefix="care">
                    <label>Time:</label>
                    <span>Start</span>
                    <input type="range" min="8" max="20" step="1" value="8" data-role="start" />
                    <span>End</span>
                    <input type="range" min="9" max="21" step="1" value="21" data-role="end" />
                </div>
                <div class="filter-row levels-row" data-prefix="care">
                    <label>Levels:</label>
                    <label><input type="checkbox" data-role="level" value="200" checked />200</label>
                    <label><input type="checkbox" data-role="level" value="400" checked />400</label>
                    <label><input type="checkbox" data-role="level" value="500" checked />500</label>
                </div>
                <div class="filter-row search-box" data-prefix="care">
                    <input type="text" data-role="search" placeholder="Search: 500, 5* (wildcard), title, instructor..." />
                    <div class="filter-actions">
                        <button class="btn" data-role="showall">Show all</button>
                        <button class="btn" data-role="reset">Reset</button>
                        <button class="btn" data-role="apply">Apply</button>
                    </div>
                </div>
            </section>

            <!-- CARE Calendar -->
            <section id="cal-care" class="cal-wrap" aria-labelledby="tab-care">
                <div class="cal-content-wrapper">
                    <div class="calendar-container">
                        <div class="calendar">
                            <div class="calendar-grid">
                                <div class="cell header">Time</div>
                                <div class="cell header">Monday</div>
                                <div class="cell header">Tuesday</div>
                                <div class="cell header">Wednesday</div>
                                <div class="cell header">Thursday</div>
                                <div class="cell header">Friday</div>
                                <div class="cell time-col">
                                    <div class="time-slot"><span class="time-label">8:00 AM</span></div>
                                    <div class="time-slot"><span class="time-label">9:00 AM</span></div>
                                    <div class="time-slot"><span class="time-label">10:00 AM</span></div>
                                    <div class="time-slot"><span class="time-label">11:00 AM</span></div>
                                    <div class="time-slot"><span class="time-label">12:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">1:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">2:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">3:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">4:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">5:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">6:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">7:00 PM</span></div>
                                    <div class="time-slot"><span class="time-label">8:00 PM</span></div>
                                </div>
                                <div class="cell day-col"><div class="day-body" id="care-Monday"></div></div>
                                <div class="cell day-col"><div class="day-body" id="care-Tuesday"></div></div>
                                <div class="cell day-col"><div class="day-body" id="care-Wednesday"></div></div>
                                <div class="cell day-col"><div class="day-body" id="care-Thursday"></div></div>
                                <div class="cell day-col"><div class="day-body" id="care-Friday"></div></div>
                            </div>
                            <div class="notice">
                                Use the filters above to refine by day, time, level, distance/off-campus, or search by number/title/instructor.
                            </div>
                        </div>
                    </div>
                    <div class="async-section" id="care-async-section" style="display: none;">
                        <h3>Online Asynchronous</h3>
                        <div class="async-list" id="care-async-list"></div>
                    </div>
                </div>
            </section>
        </div>

        <!-- Shared Modal -->
        <div class="modal" id="modal">
            <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
                <div class="modal-header">
                    <div class="modal-title" id="modalTitle"></div>
                    <button class="close-btn" id="modalClose" aria-label="Close">Close</button>
                </div>
                <div class="modal-body" id="modalBody"></div>
            </div>
        </div>

        <script>
            const ALL_PREFIXES = ["psyc", "bat", "care"];

            // Tabs
            document.querySelectorAll(".tab").forEach(btn => {
                btn.addEventListener("click", () => {
                    const targetId = btn.dataset.target;
                    document.querySelectorAll(".tab").forEach(b => { b.classList.remove("active"); b.setAttribute("aria-selected","false"); });
                    btn.classList.add("active");
                    btn.setAttribute("aria-selected","true");
                    document.querySelectorAll(".cal-wrap").forEach(s => s.classList.remove("active"));
                    document.getElementById(`cal-${targetId}`).classList.add("active");
                    ALL_PREFIXES.forEach(p => {
                        const el = document.getElementById(`filters-${p}`);
                        if (el) el.style.display = (p === targetId) ? "grid" : "none";
                    });
                });
            });

            // Layout constants
            const dayIds = ["Monday","Tuesday","Wednesday","Thursday","Friday"];
            const hourHeight = 60;
            const dayStart = 8;

            function splitDays(dayStr) { return dayStr.split(",").map(s => s.trim()); }
            function parseTime12h(str) {
                const [time, ampmRaw] = str.split(" ");
                const ampm = ampmRaw.trim().toUpperCase();
                let [h, m] = time.split(":").map(Number);
                if (ampm === "PM" && h !== 12) h += 12;
                if (ampm === "AM" && h === 12) h = 0;
                return h + m/60;
            }
            function levelOf(numStr) {
                const n = parseInt(numStr, 10);
                if (isNaN(n)) return null;
                return Math.floor(n / 100) * 100;
            }

            const courseColors = {};
            const palette = [
                ["#e0f2fe","#bae6fd","#0284c7"],
                ["#ede9fe","#ddd6fe","#7c3aed"],
                ["#fee2e2","#fecaca","#b91c1c"],
                ["#ffedd5","#fed7aa","#c2410c"],
                ["#dcfce7","#bbf7d0","#15803d"],
                ["#fce7f3","#fbcfe8","#be185d"],
                ["#fef9c3","#fde68a","#a16207"],
                ["#dbeafe","#bfdbfe","#1d4ed8"],
                ["#e9d5ff","#d8b4fe","#7c3aed"],
                ["#ccfbf1","#99f6e4","#0f766e"],
                ["#e2e8f0","#cbd5e1","#334155"],
                ["#fef3c7","#fde68a","#92400e"],
                ["#d1fae5","#a7f3d0","#065f46"]
            ];
            let colorIdx = 0;
            function colorFor(courseKey) {
                if (!courseColors[courseKey]) {
                    courseColors[courseKey] = palette[colorIdx % palette.length];
                    colorIdx++;
                }
                const [c1,c2,border] = courseColors[courseKey];
                return { c1, c2, border };
            }

            function layoutDay(events, colEl) {
                const items = events.map(e => ({
                    ...e,
                    _start: parseTime12h(e.startTime),
                    _end: parseTime12h(e.endTime)
                })).sort((a,b) => a._start - b._start || a._end - b._end);

                // Assign columns greedily (side-by-side)
                const columns = [];
                items.forEach(it => {
                    let slot = -1;
                    for (let i = 0; i < columns.length; i++) {
                        if (columns[i] <= it._start + 1e-6) { slot = i; break; }
                    }
                    if (slot === -1) { columns.push(it._end); slot = columns.length - 1; }
                    else { columns[slot] = it._end; }
                    it._col = slot;
                });

                // Group into clusters to find total cols per cluster
                const clusters = [];
                let cur = [], curEnd = -Infinity;
                items.forEach(it => {
                    if (!cur.length || it._start < curEnd - 1e-6) { cur.push(it); curEnd = Math.max(curEnd, it._end); }
                    else { clusters.push(cur); cur = [it]; curEnd = it._end; }
                });
                if (cur.length) clusters.push(cur);
                clusters.forEach(cluster => {
                    const totalCols = Math.max(...cluster.map(x => x._col)) + 1;
                    cluster.forEach(it => { it._totalCols = totalCols; });
                });

                items.forEach(ev => {
                    const top = Math.max(0, (ev._start - dayStart) * hourHeight);
                    const height = Math.max(36, (ev._end - ev._start) * hourHeight - 6);
                    const el = document.createElement("div");
                    el.className = "event";
                    el.style.top = `${top}px`;
                    el.style.height = `${height}px`;
                    el.setAttribute("role", "button");
                    el.setAttribute("tabindex", "0");

                    const { c1, c2, border } = colorFor(ev.courseKey);
                    el.style.setProperty("--bg1", c1);
                    el.style.setProperty("--bg2", c2);
                    el.style.borderColor = border;

                    const short = `${ev.subject} ${ev.number}-${ev.section}`;
                    const time = `${ev.startTime}–${ev.endTime}`;
                    const locParts = [ev.building, ev.room].filter(Boolean);
                    el.innerHTML = `
                        <div class="title">${short}</div>
                        <div class="meta">${ev.title}</div>
                        <div class="meta">${time}${locParts.length ? " • " + locParts.join(" ") : ""}</div>
                    `;
                    el.addEventListener("click", () => openModal(ev));
                    el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openModal(ev); }});
                    el.addEventListener("mouseenter", (e) => showTooltip(ev, e.clientX, e.clientY));
                    el.addEventListener("mousemove",  (e) => positionTooltip(e.clientX, e.clientY));
                    el.addEventListener("mouseleave", () => hideTooltip());
                    ev._el = el;
                    colEl.appendChild(el);
                });

                // Side-by-side with slight overlap: each box is 1/n + small bonus, offset by 1/n
                const overlapBonus = 6; // px each box bleeds into the next
                const containerWidth = colEl.clientWidth || colEl.getBoundingClientRect().width || 0;
                items.forEach(it => {
                    const n = it._totalCols;
                    it._el.style.zIndex = it._col + 1;
                    if (containerWidth > 0) {
                        const slotW = containerWidth / n;
                        const w = slotW + (it._col < n - 1 ? overlapBonus : 0);
                        it._el.style.width = `${w}px`;
                        it._el.style.left = `${it._col * slotW}px`;
                    } else {
                        const pct = 100 / n;
                        it._el.style.width = `calc(${pct}% + ${it._col < n - 1 ? overlapBonus : 0}px)`;
                        it._el.style.left = `${pct * it._col}%`;
                    }
                });
            }

            // Modal
            const modal = document.getElementById("modal");
            const modalTitle = document.getElementById("modalTitle");
            const modalBody = document.getElementById("modalBody");
            function openModal(ev) {
                modalTitle.textContent = `${ev.subject} ${ev.number} — ${ev.title}`;
                const loc = [ev.building, ev.room].filter(Boolean).join(" ") || "—";
                const instr = ev.instructor || "—";
                const campus = ev.campus || "—";
                modalBody.innerHTML = `
                    <div class="detail"><span>Section / CRN</span><p>${ev.section} / ${ev.crn}</p></div>
                    <div class="detail"><span>Credits</span><p>${ev.credits}</p></div>
                    <div class="detail"><span>Day(s)</span><p>${ev.day}</p></div>
                    <div class="detail"><span>Time</span><p>${ev.startTime} – ${ev.endTime}</p></div>
                    <div class="detail"><span>Location</span><p>${loc}</p></div>
                    <div class="detail"><span>Instructor</span><p>${instr}</p></div>
                    <div class="detail"><span>Campus</span><p>${campus}</p></div>
                    <div class="detail"><span>Dates</span><p>${ev.startDate} – ${ev.endDate}</p></div>
                    <div class="detail"><span>Type</span><p>${ev.scheduleType}</p></div>
                    <div class="detail"><span>Term</span><p>${ev.term}</p></div>
                `;
                modal.classList.add("open");
            }
            document.getElementById("modalClose").addEventListener("click", () => modal.classList.remove("open"));
            modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.remove("open"); });
            document.addEventListener("keydown", (e) => { if (e.key === "Escape") modal.classList.remove("open"); });

            // Wildcard search helper
            function wildcardMatch(text, pattern) {
                // No wildcards - use simple substring match
                if (pattern.indexOf('*') === -1 && pattern.indexOf('?') === -1) {
                    return text.includes(pattern);
                }
                
                // Split pattern by * and check each part exists in order
                const parts = pattern.split('*');
                let lastIndex = 0;
                
                for (let i = 0; i < parts.length; i++) {
                    const part = parts[i];
                    if (!part) continue; // empty part from consecutive **
                    
                    const idx = text.indexOf(part, lastIndex);
                    if (idx === -1) return false;
                    lastIndex = idx + part.length;
                }
                
                return true;
            }

            // Data sources - Grid courses (with meeting times)
            const PSYC_SOURCE = [
''' + psyc_grid + '''
            ];

            const BAT_SOURCE = [
''' + bat_grid + '''
            ];

            const CARE_SOURCE = [
''' + care_grid + '''
            ];

            // Async online courses (no meeting times)
            const PSYC_ASYNC = [
''' + psyc_async + '''
            ];

            const BAT_ASYNC = [
''' + bat_async + '''
            ];

            const CARE_ASYNC = [
''' + care_async + '''
            ];

            function expandTimed(source, prefix) {
                const out = [];
                source.forEach(s => {
                    const m = s.meeting;
                    if (!m || !m.days || !m.start || !m.end) return;
                    splitDays(m.days).forEach(day => {
                        out.push({
                            domPrefix: prefix,
                            courseKey: `${s.subject} ${s.number}`,
                            title: s.title,
                            subject: s.subject,
                            number: s.number,
                            section: s.section,
                            crn: s.crn,
                            credits: s.credits,
                            term: s.term,
                            instructor: s.instructor || "",
                            day,
                            allDays: m.days,
                            startTime: m.start,
                            endTime: m.end,
                            building: m.building,
                            room: m.room,
                            startDate: m.startDate,
                            endDate: m.endDate,
                            campus: s.campus,
                            scheduleType: s.scheduleType
                        });
                    });
                });
                return out;
            }

            const PSYC_TIMED_ALL  = expandTimed(PSYC_SOURCE,  "psyc");
            const BAT_TIMED_ALL   = expandTimed(BAT_SOURCE,   "bat");
            const CARE_TIMED_ALL  = expandTimed(CARE_SOURCE,  "care");

            const defaultLevels = {
                psyc: new Set([100,200,300,400,500]),
                bat:  new Set([200,500]),
                care: new Set([200,400,500])
            };

            const state = {
                psyc: { days: new Set(dayIds), startHour: 8, endHour: 21, levels: new Set([100,200,300,400,500]), search: "" },
                bat:  { days: new Set(dayIds), startHour: 8, endHour: 21, levels: new Set([200,500]),             search: "" },
                care: { days: new Set(dayIds), startHour: 8, endHour: 21, levels: new Set([200,400,500]),         search: "" }
            };

            function applyFilters(prefix, allEvents) {
                const st = state[prefix];
                const q = st.search.trim().toLowerCase();
                return allEvents.filter(ev => {
                    if (!st.days.has(ev.day)) return false;
                    const s = parseTime12h(ev.startTime), e = parseTime12h(ev.endTime);
                    if (s < st.startHour || e > st.endHour) return false;
                    const lvl = levelOf(ev.number);
                    if (lvl && !st.levels.has(lvl)) return false;
                    if (q) {
                        const hay = [`${ev.subject} ${ev.number}`, ev.number, ev.title, ev.instructor]
                            .filter(Boolean).join(" ").toLowerCase();
                        if (!wildcardMatch(hay, q)) return false;
                    }
                    return true;
                });
            }

            function layoutIntoColumns(timed, prefix) {
                const byDay = dayIds.reduce((acc, d) => (acc[d] = [], acc), {});
                timed.forEach(c => { if (byDay[c.day]) byDay[c.day].push(c); });
                dayIds.forEach(d => {
                    const colEl = document.getElementById(`${prefix}-${d}`);
                    if (!colEl) return;
                    colEl.innerHTML = "";
                    if (byDay[d].length) layoutDay(byDay[d], colEl);
                });
            }

            function allTimedFor(prefix) {
                if (prefix === "psyc")  return PSYC_TIMED_ALL;
                if (prefix === "bat")   return BAT_TIMED_ALL;
                if (prefix === "care")  return CARE_TIMED_ALL;
            }

            function renderCalendar(prefix) {
                const filtered = applyFilters(prefix, allTimedFor(prefix));
                layoutIntoColumns(filtered, prefix);
                renderAsyncCourses(prefix);
            }

            function renderAsyncCourses(prefix) {
                const asyncSection = document.getElementById(`${prefix}-async-section`);
                const asyncList = document.getElementById(`${prefix}-async-list`);
                
                // Get async courses for this prefix
                let asyncSource = [];
                if (prefix === "psyc") asyncSource = PSYC_ASYNC;
                else if (prefix === "bat") asyncSource = BAT_ASYNC;
                else if (prefix === "care") asyncSource = CARE_ASYNC;
                
                if (asyncSource.length === 0) {
                    asyncSection.style.display = "none";
                    return;
                }
                
                // Apply search filter to async courses
                const searchTerm = state[prefix].search.toLowerCase();
                const filtered = searchTerm ? asyncSource.filter(course => {
                    const hay = [`${course.subject} ${course.number}`, course.number, course.title, course.instructor]
                        .map(x => (x || "").toLowerCase()).join(" ");
                    return wildcardMatch(hay, searchTerm);
                }) : asyncSource;
                
                if (filtered.length === 0) {
                    asyncSection.style.display = "none";
                    return;
                }
                
                asyncSection.style.display = "block";
                asyncList.innerHTML = "";
                
                filtered.forEach(course => {
                    const item = document.createElement("div");
                    item.className = "async-item";
                    item.innerHTML = `
                        <div class="async-item-title">${course.subject} ${course.number} — ${course.title}</div>
                        <div class="async-item-meta">
                            ${course.section ? `Section ${course.section} • ` : ""}${course.credits} credits
                            ${course.instructor ? ` • ${course.instructor}` : ""}
                        </div>
                    `;
                    
                    // Convert course to event format for modal
                    const eventData = {
                        subject: course.subject,
                        number: course.number,
                        title: course.title,
                        section: course.section,
                        crn: course.crn,
                        credits: course.credits,
                        day: "Asynchronous",
                        startTime: "—",
                        endTime: "—",
                        building: course.meeting.building || "—",
                        room: course.meeting.room || "—",
                        instructor: course.instructor || "—",
                        campus: course.campus,
                        startDate: course.meeting.startDate,
                        endDate: course.meeting.endDate,
                        scheduleType: course.scheduleType,
                        term: course.term
                    };
                    
                    // Make clickable to show modal
                    item.addEventListener("click", () => {
                        openModal(eventData);
                    });
                    
                    // Add tooltip on hover
                    item.addEventListener("mouseenter", (e) => {
                        if (!tooltipsEnabled) return;
                        const rect = item.getBoundingClientRect();
                        tooltip.innerHTML = `
                            <div class="tooltip-title">${course.subject} ${course.number} — ${course.title}</div>
                            <div class="tooltip-row">Section: <span>${course.section}</span></div>
                            <div class="tooltip-row">CRN: <span>${course.crn}</span></div>
                            <div class="tooltip-row">Credits: <span>${course.credits}</span></div>
                            ${course.instructor ? `<div class="tooltip-row">Instructor: <span>${course.instructor}</span></div>` : ""}
                            <div class="tooltip-row">Format: <span>Online Asynchronous</span></div>
                        `;
                        
                        // Position tooltip to the LEFT of async card (in right sidebar)
                        // This prevents blocking cards below in the list
                        const tooltipWidth = 260; // approximate width
                        const x = rect.left - tooltipWidth - 10; // 10px gap
                        const y = rect.top + (rect.height / 2);
                        
                        tooltip.style.left = Math.max(10, x) + "px";
                        tooltip.style.top = y + "px";
                        tooltip.style.transform = "translateY(-50%)"; // Center vertically
                        tooltip.classList.add("visible");
                    });
                    
                    item.addEventListener("mouseleave", () => {
                        tooltip.classList.remove("visible");
                        tooltip.style.transform = ""; // Reset transform for grid tooltips
                    });
                    
                    asyncList.appendChild(item);
                });
            }

            function connectFilters(prefix) {
                const container = document.querySelector(`.filters#filters-${prefix}`);
                if (!container) return;

                container.querySelectorAll('input[data-role="day"]').forEach(cb => {
                    cb.addEventListener("change", () => {
                        if (cb.checked) state[prefix].days.add(cb.value);
                        else state[prefix].days.delete(cb.value);
                        renderCalendar(prefix);
                    });
                });

                const startEl = container.querySelector('input[data-role="start"]');
                const endEl   = container.querySelector('input[data-role="end"]');
                const clampTimes = () => {
                    let s = parseInt(startEl.value, 10);
                    let e = parseInt(endEl.value, 10);
                    if (e <= s) e = s + 1;
                    state[prefix].startHour = s;
                    state[prefix].endHour = e;
                };
                startEl.addEventListener("input", () => { clampTimes(); renderCalendar(prefix); });
                endEl.addEventListener("input",   () => { clampTimes(); renderCalendar(prefix); });
                clampTimes();

                container.querySelectorAll('input[data-role="level"]').forEach(cb => {
                    cb.addEventListener("change", () => {
                        const lvl = parseInt(cb.value, 10);
                        if (cb.checked) state[prefix].levels.add(lvl);
                        else state[prefix].levels.delete(lvl);
                        renderCalendar(prefix);
                    });
                });

                const searchEl = container.querySelector('input[data-role="search"]');
                let debounce;
                searchEl.addEventListener("input", () => {
                    clearTimeout(debounce);
                    debounce = setTimeout(() => {
                        state[prefix].search = searchEl.value;
                        renderCalendar(prefix);
                    }, 180);
                });

                container.querySelector('button[data-role="reset"]').addEventListener("click", () => {
                    state[prefix] = {
                        days: new Set(dayIds),
                        startHour: 8, endHour: 21,
                        levels: new Set(defaultLevels[prefix]),
                        search: ""
                    };
                    container.querySelectorAll('input[data-role="day"]').forEach(cb => cb.checked = true);
                    startEl.value = 8; endEl.value = 21;
                    container.querySelectorAll('input[data-role="level"]').forEach(cb => {
                        cb.checked = defaultLevels[prefix].has(parseInt(cb.value, 10));
                    });
                    searchEl.value = "";
                    renderCalendar(prefix);
                });

                container.querySelector('button[data-role="apply"]').addEventListener("click", () => renderCalendar(prefix));
                container.querySelector('button[data-role="showall"]').addEventListener("click", () => {
                    container.querySelector('button[data-role="reset"]').click();
                });
            }

            // Tooltip
            const tooltip = document.createElement("div");
            tooltip.className = "tooltip";
            document.body.appendChild(tooltip);

            let tooltipsEnabled = true;
            document.getElementById("tooltipToggle").addEventListener("click", function() {
                tooltipsEnabled = !tooltipsEnabled;
                this.textContent = tooltipsEnabled ? "Tooltips: On" : "Tooltips: Off";
                this.classList.toggle("off", !tooltipsEnabled);
                this.setAttribute("aria-pressed", tooltipsEnabled);
                if (!tooltipsEnabled) hideTooltip();
            });

            function showTooltip(ev, mouseX, mouseY) {
                if (!tooltipsEnabled) return;
                const loc = [ev.building, ev.room].filter(Boolean).join(" ") || "—";
                const instr = ev.instructor || "—";
                const days = ev.allDays || ev.day || "—";
                tooltip.innerHTML = `
                    <div class="tooltip-title">${ev.subject} ${ev.number} — ${ev.title}</div>
                    <div class="tooltip-row">Section: <span>${ev.section}</span></div>
                    <div class="tooltip-row">Time: <span>${ev.startTime}–${ev.endTime}</span></div>
                    <div class="tooltip-row">Days: <span>${days}</span></div>
                    <div class="tooltip-row">Location: <span>${loc}</span></div>
                    <div class="tooltip-row">Instructor: <span>${instr}</span></div>
                    <div class="tooltip-row">Credits: <span>${ev.credits}</span></div>
                `;
                positionTooltip(mouseX, mouseY);
                tooltip.classList.add("visible");
            }

            function positionTooltip(x, y) {
                const tw = tooltip.offsetWidth || 260;
                const th = tooltip.offsetHeight || 140;
                const vw = window.innerWidth, vh = window.innerHeight;
                let left = x + 14, top = y + 14;
                if (left + tw > vw - 8) left = x - tw - 14;
                if (top + th > vh - 8) top = y - th - 14;
                tooltip.style.left = left + "px";
                tooltip.style.top  = top  + "px";
            }

            function hideTooltip() { tooltip.classList.remove("visible"); }

            ALL_PREFIXES.forEach(p => connectFilters(p));
            ALL_PREFIXES.forEach(p => renderCalendar(p));

            // Initial filter visibility
            document.getElementById("filters-bat").style.display  = "none";
            document.getElementById("filters-care").style.display = "none";

            // Re-layout when calendar column widths change (window resize)
            if (window.ResizeObserver) {
                const ro = new ResizeObserver(() => {
                    ALL_PREFIXES.forEach(p => renderCalendar(p));
                });
                document.querySelectorAll(".day-body").forEach(el => ro.observe(el));
            } else {
                window.addEventListener("resize", () => {
                    ALL_PREFIXES.forEach(p => renderCalendar(p));
                });
            }
        </script>
    </body>
</html>'''

output_filename = f'SPBS{TERM_CODE}Schedule.html'
with open(output_filename, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Written: {len(html)} chars")
