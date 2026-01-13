#!/usr/bin/env python3
"""
Simple test script to verify cleaning overtime logic
"""

from generator import Generator
from datetime import datetime
import json

def test_cleaning_overtime():
    """Test the cleaning overtime assignment for today (2026-01-13)"""

    # Today is Monday, 2026-01-13
    # Collaboratore ID 2 (Elia Egizio) is absent - they normally work at Bandini 2 (luogo_id=2)
    # So someone should be assigned 20 minutes of cleaning overtime for Bandini 2

    print("=" * 60)
    print("TESTING CLEANING OVERTIME LOGIC")
    print("=" * 60)
    print()

    generator = Generator()

    day = 13
    month = 1
    year = 2026
    weekday = 'lunedi'

    print(f"Generating schedule for {weekday}, {day}/{month}/{year}")
    print()

    # Generate the schedule
    result = generator.generate(day, month, year, weekday)

    print("=" * 60)
    print("SCHEDULE OUTPUT:")
    print("=" * 60)
    print(result)
    print()

    # Read the final schedule to check cleaning overtime
    with open("final_schedule_after_substitutions.json", "r") as f:
        schedule = json.load(f)

    print("=" * 60)
    print("CLEANING OVERTIME ASSIGNMENTS:")
    print("=" * 60)

    if 'cleaning_overtime' in schedule and schedule['cleaning_overtime']:
        for cleaning in schedule['cleaning_overtime']:
            collab = generator._get_collaboratore_by_id(cleaning['collaboratore_id'])
            print(f"✓ {collab['cognome']} {collab['nome']}:")
            print(f"  - Location: {cleaning['location_name']}")
            print(f"  - Overtime: {cleaning['overtime_minutes']} minutes")
            print(f"  - New total straordinari: {collab['straordinari_svolti']} minutes")
            print()
    else:
        print("No cleaning overtime assignments found")
        print()

    print("=" * 60)
    print("LOCATION STAFFING:")
    print("=" * 60)

    # Check each location's normal vs actual staffing
    locations_normal = {}
    for collab in generator.collaboratori:
        luogo_id = collab.get('luogo_id')
        if luogo_id:
            if luogo_id not in locations_normal:
                locations_normal[luogo_id] = []
            locations_normal[luogo_id].append(collab)

    for luogo_id, collabs in locations_normal.items():
        luogo = generator._get_luogo_by_id(luogo_id)
        print(f"\n{luogo['nome']} (ID: {luogo_id}):")
        print(f"  Normal staff count: {len(collabs)}")
        print(f"  No cleaning needed: {luogo.get('no_cleaning_needed', False)}")

        # Count present at location (use string key)
        present_count = 0
        luogo_key = str(luogo_id)
        if luogo_key in schedule:
            for assignment in schedule[luogo_key]:
                collab_id = assignment['collaboratore_id']
                collab = generator._get_collaboratore_by_id(collab_id)
                if collab and collab.get('luogo_id') == luogo_id:
                    present_count += 1

        print(f"  Present at end of day: {present_count}")
        print(f"  Missing: {len(collabs) - present_count}")

        if len(collabs) - present_count > 0 and not luogo.get('no_cleaning_needed', False):
            print(f"  → Cleaning overtime needed: ✓")
        else:
            print(f"  → Cleaning overtime needed: ✗")

    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    test_cleaning_overtime()
