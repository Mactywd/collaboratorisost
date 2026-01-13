import json
from datetime import datetime, time
import random

class Generator:
    def __init__(self):
        # Load JSON to memory
        with open('data/assenze.json', 'r') as f:
            self.assenze = json.load(f)
        with open('data/turnazioni.json', 'r') as f:
            self.turnazioni = json.load(f)
        with open('data/coperture_fisse.json', 'r') as f:
            self.coperture_fisse = json.load(f)
        with open('data/collaboratori.json', 'r') as f:
            self.collaboratori = json.load(f)
        with open('data/luoghi.json', 'r') as f:
            self.luoghi = json.load(f)
        with open('data/orari_pomeriggio.json', 'r') as f:
            self.orari_pomeriggio = json.load(f)
        with open('data/sub_order.json', 'r') as f:
            self.sub_order = json.load(f)

    def _get_collaboratore_by_id(self, id):
        for collaboratore in self.collaboratori:
            if collaboratore['id'] == id:
                return collaboratore
        return None
    def _get_luogo_by_id(self, id):
        for luogo in self.luoghi:
            if luogo['id'] == id:
                return luogo
        return None

    def _convert_month(self, criteria, month_name=None, month_index=None):
        months = {
            'gennaio': 1,
            'febbraio': 2,
            'marzo': 3,
            'aprile': 4,
            'maggio': 5,
            'giugno': 6,
            'luglio': 7,
            'agosto': 8,
            'settembre': 9,
            'ottobre': 10,
            'novembre': 11,
            'dicembre': 12
        }
        if criteria == 'index_from_name' and month_name:
            return months.get(month_name.lower())
        elif criteria == 'name_from_index' and month_index:
            for name, index in months.items():
                if index == month_index:
                    return name
        return None

    def _calculate_luogo_info(self, schedule):
        luogo_info = {}
        for luogo in self.luoghi:
            luogo_id = luogo['id']
            collaboratori = schedule.get(luogo_id, [])
            amount = 0
            # Count all collaboratori which enter earlier than "8:20"
            for collaboratore in collaboratori:
                start_time = collaboratore['start']
                print(collaboratore)
                start_hour, start_minute = map(int, start_time.split(':'))
                start_time_obj = time(start_hour, start_minute)
                target_time = time(8, 20)
                if start_time_obj <= target_time:
                    amount += 1
            
            min_required = luogo['min_collaboratori']

            if amount == min_required:
                luogo_info[luogo_id] = "EXACT"
            elif amount > min_required:
                luogo_info[luogo_id] = f"+{amount - min_required}"
            else:
                luogo_info[luogo_id] = f"-{min_required - amount}"
        
        return luogo_info

    def _is_collaborator_already_assigned(self, schedule, collaboratore_id):
        '''Check if a collaborator is already assigned as a substitute.'''
        # Check if already assigned as a substitute at any location
        for luogo_id, collaboratori in schedule.items():
            if luogo_id == 'afternoon_subs':
                continue
            for collab in collaboratori:
                if collab['collaboratore_id'] == collaboratore_id and collab.get('is_substitute', False):
                    return True

        # Check afternoon substitutes
        if 'afternoon_subs' in schedule:
            for collab in schedule['afternoon_subs']:
                if collab['collaboratore_id'] == collaboratore_id:
                    return True

        return False

    def find_substitute(self, schedule, criteria, needed_luogo_id=None):
        '''
        Find a substitute available to cover a missing shift.

        Args:
            schedule: Current schedule state
            criteria: Selection criteria ("overtime" or "substitute")
            needed_luogo_id: The location ID that needs coverage
        '''
        luogo_info = self._calculate_luogo_info(schedule)
        available_collaboratori = {}
        for luogo_id, info in luogo_info.items():
            if info.startswith("+"):
                # Find all collaboratori
                possible_subs = [c for c in self.collaboratori if c["luogo_id"] == luogo_id]
                for sub in possible_subs:
                    # Skip if already assigned
                    if self._is_collaborator_already_assigned(schedule, sub["id"]):
                        continue
                    available_collaboratori[sub["id"]] = {
                        "last_sub": sub["ultima_sostituzione"],
                        "overtime": sub["straordinari_svolti"],
                    }

        # If no available collaborators, return None
        if not available_collaboratori:
            return None

        # Choose based on selected criteria
        if criteria == "overtime":
            min_overtime = min(available_collaboratori[col_id]["overtime"] for col_id in available_collaboratori)
            for collaboratore in self.collaboratori:
                if collaboratore["id"] in available_collaboratori and collaboratore["straordinari_svolti"] == min_overtime:
                    return collaboratore
            return None

        elif criteria == "substitute":
            # PRIORITY 1: Check for luogo_secondario
            # If a collaborator has the needed location as their luogo_secondario, they are the first choice
            if needed_luogo_id is not None:
                luogo_secondario_candidates = []
                for collaboratore in self.collaboratori:
                    # Check if this collaborator has the needed location as luogo_secondario
                    if collaboratore.get("luogo_secondario_id") == needed_luogo_id:
                        # Check if they are available (not already assigned and in surplus location)
                        if collaboratore["id"] in available_collaboratori:
                            luogo_secondario_candidates.append(collaboratore)

                if luogo_secondario_candidates:
                    # Pick the first one (could add more logic here if needed)
                    chosen = luogo_secondario_candidates[0]
                    print(f"Found luogo_secondario match: {chosen['cognome']} {chosen['nome']} for luogo {needed_luogo_id}")
                    return chosen

            # PRIORITY 2: Then, look for collaboratori with "none" as last substitute date
            none_collaboratori = []
            for collaboratore in self.collaboratori:
                if collaboratore["id"] in available_collaboratori:
                    if collaboratore["ultima_sostituzione"] == None:
                        none_collaboratori.append(collaboratore)
            if none_collaboratori:
                return random.choice(none_collaboratori)

            # PRIORITY 3: If none found, pick the one with the oldest last substitute date
            available_dates = [self.collaboratori[i]["ultima_sostituzione"]
                             for i, col in enumerate(self.collaboratori)
                             if col["id"] in available_collaboratori and col["ultima_sostituzione"] is not None]

            if not available_dates:
                return None

            last_substitute = max(available_dates)
            print("Last substitute date to beat:", last_substitute)
            for collaboratore in self.collaboratori:
                if (collaboratore["id"] in available_collaboratori and
                    collaboratore["ultima_sostituzione"] == last_substitute):
                    return collaboratore
            return None

        else:
            return None


    def populate_absences(self, day, month, year, weekday):
        '''
        Populate a list containing all the shifts covered by the present collaborators.
        
        Look into:
        - assenze.json
        - turnazioni.json
        - coperture_fisse.json
        '''



        absences = []
        for assenza in self.assenze:
            # Convert date to YYYY-MM-DD for comparison
            assenza_date = assenza['data']
            assenza_day = int(assenza_date.split('-')[2])
            assenza_month = int(assenza_date.split('-')[1])
            assenza_year = int(assenza_date.split('-')[0])

            if (assenza_day == day and
                assenza_month == month and
                assenza_year == year):

                absences.append({
                    'collaboratore_id': assenza['collaboratore_id'],
                    'inizio': assenza['ora_inizio'] or 'day_start',
                    'fine': assenza['ora_fine'] or 'day_end',
                    'tipo': 'assenza'
                })

        str_month = self._convert_month('name_from_index', month_index=month)
        for turnazione in self.turnazioni:
            if (turnazione['mese'] == str_month and
                turnazione['anno'] == year and
                turnazione['giorno_settimana'] == weekday):
                absences.append({
                    'collaboratore_id': turnazione['collaboratore_id'],
                    'inizio': 'day_start',
                    'fine': turnazione['ora_ingresso_alternativa'],
                    'tipo': 'turnazione'
                })
        
        covered_locations = []
        for copertura in self.coperture_fisse:
            if copertura['giorno_settimana'] == weekday:
                collaboratore = self._get_collaboratore_by_id(copertura['collaboratore_id'])
                if collaboratore:
                    absences.append({
                        'collaboratore_id': copertura['collaboratore_id'],
                        'inizio': 'day_start',
                        'fine': 'day_end',
                        'tipo': 'copertura_fissa'
                    })
                    covered_locations.append({
                        'collaboratore_id': copertura['collaboratore_id'],
                        'luogo_id': collaboratore['luogo_id']
                    })
        
        # Create list of all currently covered locations by present collaborators
        present_locations = []
        for collaboratore in self.collaboratori:
            # If collaboratore is absent (i.e. in absences), skip
            if any(a['collaboratore_id'] == collaboratore['id'] for a in self.assenze):
                # Make sure assenza is for the current day
                is_absent_today = False
                for a in self.assenze:
                    assenza_date = a['data']
                    assenza_day = int(assenza_date.split('-')[2])
                    assenza_month = int(assenza_date.split('-')[1])
                    assenza_year = int(assenza_date.split('-')[0])
                    if (a['collaboratore_id'] == collaboratore['id'] and
                        assenza_day == day and
                        assenza_month == month and
                        assenza_year == year):
                        is_absent_today = True
                        break
                if is_absent_today:
                    continue
            # If collaboratore has a fixed location coverage today, add only the covered location
            if any(c['collaboratore_id'] == collaboratore['id'] and
                   c['giorno_settimana'] == weekday for c in self.coperture_fisse):
                print("Fixed coverage for", collaboratore['nome'])
                for c in self.coperture_fisse:
                    if (c['collaboratore_id'] == collaboratore['id'] and
                        c['giorno_settimana'] == weekday):
                        present_locations.append({
                            'collaboratore_id': collaboratore['id'],
                            'luogo_id': c['luogo_coperto_id'],
                            'start': 'day_start',
                            'end': 'day_end'
                        })
                        print("From location", collaboratore['luogo_id'], "to location", c['luogo_coperto_id'])
            
            # If collaboratore has a turnazione, add only the time for that turnazione
            elif any(t['collaboratore_id'] == collaboratore['id'] and
                     t['mese'] == str_month and
                     t['anno'] == year and
                     t['giorno_settimana'] == weekday for t in self.turnazioni):
                for t in self.turnazioni:
                    if (t['collaboratore_id'] == collaboratore['id'] and
                        t['mese'] == str_month and
                        t['anno'] == year and
                        t['giorno_settimana'] == weekday):
                        present_locations.append({
                            'collaboratore_id': collaboratore['id'],
                            'luogo_id': collaboratore['luogo_id'],
                            'start': t['ora_ingresso_alternativa'],
                            'end': self.orari_pomeriggio[weekday]['ora_fine']
                        })
            # Look for collaboratore schedule and check that they are present that day
            else:
                giorno_orario = collaboratore['orari_settimanali'].get(weekday)
                if giorno_orario:
                    present_locations.append({
                        'collaboratore_id': collaboratore['id'],
                        'luogo_id': collaboratore['luogo_id'],
                        'start': 'day_start',
                        'end': 'day_end'
                    })

        # Populate day_start and day_end based on collaboratore schedule
        for location in present_locations:
            collaboratore = self._get_collaboratore_by_id(location['collaboratore_id'])
            if not collaboratore:
                continue
            giorno_orario = collaboratore['orari_settimanali'].get(weekday)
            if giorno_orario:
                if location['start'] == 'day_start':
                    location['start'] = giorno_orario['inizio']
                if location['end'] == 'day_end':
                    location['end'] = giorno_orario['fine']
                

        with open("debug_output.json", "w") as debug_file:
            json.dump({
                "absences": absences,
                "present_locations": present_locations
            }, debug_file, indent=4)

        return absences, present_locations
    
    def _find_absent_collaborator(self, luogo_id, day, month, year):
        '''Find which collaborator from a location is absent on a given day.'''
        for collaboratore in self.collaboratori:
            if collaboratore['luogo_id'] == luogo_id:
                # Check if this collaboratore is absent today
                for assenza in self.assenze:
                    assenza_date = assenza['data']
                    assenza_day = int(assenza_date.split('-')[2])
                    assenza_month = int(assenza_date.split('-')[1])
                    assenza_year = int(assenza_date.split('-')[0])
                    if (assenza['collaboratore_id'] == collaboratore['id'] and
                        assenza_day == day and
                        assenza_month == month and
                        assenza_year == year):
                        return collaboratore
        return None

    def _find_turnazione_at_location(self, luogo_id, weekday, month, year):
        '''Find if someone at this location has a turnazione (shifted hours) today.'''
        str_month = self._convert_month('name_from_index', month_index=month)
        for collaboratore in self.collaboratori:
            if collaboratore['luogo_id'] == luogo_id:
                for turnazione in self.turnazioni:
                    if (turnazione['collaboratore_id'] == collaboratore['id'] and
                        turnazione['giorno_settimana'] == weekday and
                        turnazione['mese'] == str_month and
                        turnazione['anno'] == year):
                        return collaboratore, turnazione['ora_ingresso_alternativa']
        return None, None

    def _find_absent_afternoon_collaborator(self, day, month, year, weekday):
        '''Find which collaborator is absent and was supposed to cover afternoon shift.'''
        # Check if there's an afternoon shift today
        if weekday not in self.orari_pomeriggio or not self.orari_pomeriggio[weekday].get('attivo'):
            return None

        afternoon_end = self.orari_pomeriggio[weekday]['ora_fine']
        afternoon_end_hour, afternoon_end_minute = map(int, afternoon_end.split(':'))
        afternoon_end_time = time(afternoon_end_hour, afternoon_end_minute)

        # Find collaborators who are absent today and normally work until afternoon
        for assenza in self.assenze:
            assenza_date = assenza['data']
            assenza_day = int(assenza_date.split('-')[2])
            assenza_month = int(assenza_date.split('-')[1])
            assenza_year = int(assenza_date.split('-')[0])

            if (assenza_day == day and assenza_month == month and assenza_year == year):
                collaboratore = self._get_collaboratore_by_id(assenza['collaboratore_id'])
                if collaboratore and weekday in collaboratore['orari_settimanali']:
                    # Check if they normally work until afternoon end time
                    end_str = collaboratore['orari_settimanali'][weekday]['fine']
                    end_hour, end_minute = map(int, end_str.split(':'))
                    end_time = time(end_hour, end_minute)

                    if end_time >= afternoon_end_time:
                        return collaboratore

        # Also check if someone with a turnazione covering afternoon is absent
        str_month = self._convert_month('name_from_index', month_index=month)
        for turnazione in self.turnazioni:
            if (turnazione['giorno_settimana'] == weekday and
                turnazione['mese'] == str_month and
                turnazione['anno'] == year):
                # Check if this person is absent
                for assenza in self.assenze:
                    if assenza['collaboratore_id'] == turnazione['collaboratore_id']:
                        assenza_date = assenza['data']
                        assenza_day = int(assenza_date.split('-')[2])
                        assenza_month = int(assenza_date.split('-')[1])
                        assenza_year = int(assenza_date.split('-')[0])
                        if (assenza_day == day and assenza_month == month and assenza_year == year):
                            return self._get_collaboratore_by_id(turnazione['collaboratore_id'])

        return None

    def _count_afternoon_coverage(self, schedule, afternoon_end_str):
        '''Count how many collaborators work until afternoon end time across all locations.'''
        afternoon_end_hour, afternoon_end_minute = map(int, afternoon_end_str.split(':'))
        afternoon_end_time = time(afternoon_end_hour, afternoon_end_minute)

        count = 0
        for collaboratori in schedule.values():
            for collaboratore in collaboratori:
                end_time_str = collaboratore['end']
                end_hour, end_minute = map(int, end_time_str.split(':'))
                end_time = time(end_hour, end_minute)

                if end_time >= afternoon_end_time:
                    count += 1

        return count

    def _shift_hours_for_afternoon(self, start_str, end_str, afternoon_end_str):
        '''Shift working hours so they end at afternoon end time while maintaining duration.'''
        # Parse times
        start_hour, start_minute = map(int, start_str.split(':'))
        end_hour, end_minute = map(int, end_str.split(':'))
        afternoon_end_hour, afternoon_end_minute = map(int, afternoon_end_str.split(':'))

        # Calculate work duration in minutes
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        duration_minutes = end_minutes - start_minutes

        # Calculate new start time
        afternoon_end_minutes = afternoon_end_hour * 60 + afternoon_end_minute
        new_start_minutes = afternoon_end_minutes - duration_minutes

        new_start_hour = new_start_minutes // 60
        new_start_minute = new_start_minutes % 60

        return f"{new_start_hour:02d}:{new_start_minute:02d}", afternoon_end_str

    def generate_schedule(self, day, month, year, weekday):
        absences, present_locations = self.populate_absences(day, month, year, weekday)

        # Group present locations by luogo_id
        schedule = {}
        for location in present_locations:
            luogo_id = location['luogo_id']
            if luogo_id not in schedule:
                schedule[luogo_id] = []
            schedule[luogo_id].append({
                'collaboratore_id': location['collaboratore_id'],
                'start': location['start'],
                'end': location['end']
            })

        with open("final_schedule.json", "w") as schedule_file:
            json.dump(schedule, schedule_file, indent=4)

        luogo_info = self._calculate_luogo_info(schedule)

        for luogo_id, info in luogo_info.items():
            print(f"Luogo ID {luogo_id}: {info}")

            if info.startswith("-"):
                amount_needed = int(info[1:])
                while amount_needed > 0:

                    substitute = self.find_substitute(schedule, "substitute", needed_luogo_id=luogo_id)
                    if substitute:
                        # Check if shortage is due to turnazione
                        turnazione_person, turnazione_start = self._find_turnazione_at_location(luogo_id, weekday, month, year)

                        if turnazione_person:
                            # Someone at this location has shifted hours for afternoon
                            # Substitute only needs to cover the morning gap
                            print(f"Found substitute Collaboratore ID {substitute['id']} for morning gap at Luogo ID {luogo_id}")
                            normal_end = substitute['orari_settimanali'][weekday]['fine']

                            if luogo_id not in schedule:
                                schedule[luogo_id] = []
                            schedule[luogo_id].append({
                                'collaboratore_id': substitute['id'],
                                'start': substitute['orari_settimanali'][weekday]['inizio'],
                                'end': normal_end,
                                'partial_end': turnazione_start,
                                'original_luogo_id': substitute['luogo_id'],
                                'is_substitute': True,
                                'replaces_id': turnazione_person['id']
                            })
                        else:
                            # Regular absence, full day substitution
                            absent_collaboratore = self._find_absent_collaborator(luogo_id, day, month, year)

                            print(f"Found substitute Collaboratore ID {substitute['id']} for Luogo ID {luogo_id}")
                            if luogo_id not in schedule:
                                schedule[luogo_id] = []
                            schedule[luogo_id].append({
                                'collaboratore_id': substitute['id'],
                                'start': substitute['orari_settimanali'][weekday]['inizio'],
                                'end': substitute['orari_settimanali'][weekday]['fine'],
                                'is_substitute': True,
                                'replaces_id': absent_collaboratore['id'] if absent_collaboratore else None,
                                'original_luogo_id': substitute['luogo_id']
                            })

                        # Update luogo_info to check if substitute's original location now needs coverage
                        luogo_info = self._calculate_luogo_info(schedule)

                        # Check if the substitute's original location now needs a substitute
                        substitute_original_luogo = substitute['luogo_id']
                        if substitute_original_luogo in luogo_info and luogo_info[substitute_original_luogo].startswith("-"):
                            print(f"Substitute's original location (Luogo ID {substitute_original_luogo}) now needs coverage")
                            # Find a substitute for the substitute's original location
                            cascading_substitute = self.find_substitute(schedule, "substitute", needed_luogo_id=substitute_original_luogo)
                            if cascading_substitute:
                                print(f"Found cascading substitute Collaboratore ID {cascading_substitute['id']} for Luogo ID {substitute_original_luogo}")
                                if substitute_original_luogo not in schedule:
                                    schedule[substitute_original_luogo] = []
                                schedule[substitute_original_luogo].append({
                                    'collaboratore_id': cascading_substitute['id'],
                                    'start': cascading_substitute['orari_settimanali'][weekday]['inizio'],
                                    'end': cascading_substitute['orari_settimanali'][weekday]['fine'],
                                    'is_substitute': True,
                                    'replaces_id': substitute['id'],
                                    'original_luogo_id': cascading_substitute['luogo_id']
                                })
                                # Update luogo_info again after cascading substitution
                                luogo_info = self._calculate_luogo_info(schedule)
                            else:
                                print(f"No cascading substitute found for Luogo ID {substitute_original_luogo}")

                        amount_needed -= 1
                    else:
                        print("No available substitute found.")
                        break

        # Handle afternoon shift coverage (school-wide, not location-specific)
        if weekday in self.orari_pomeriggio and self.orari_pomeriggio[weekday].get('attivo'):
            afternoon_end = self.orari_pomeriggio[weekday]['ora_fine']
            required_afternoon = self.orari_pomeriggio[weekday]['num_collaboratori']

            # Count how many collaborators work until afternoon end time across all locations
            afternoon_count = self._count_afternoon_coverage(schedule, afternoon_end)
            print(f"Afternoon coverage: {afternoon_count}/{required_afternoon} until {afternoon_end}")

            while afternoon_count < required_afternoon:
                substitute = self.find_substitute(schedule, "substitute", needed_luogo_id=None)
                if substitute:
                    # Calculate shifted hours
                    original_start = substitute['orari_settimanali'][weekday]['inizio']
                    original_end = substitute['orari_settimanali'][weekday]['fine']
                    new_start, new_end = self._shift_hours_for_afternoon(original_start, original_end, afternoon_end)

                    # Find who they're replacing for afternoon
                    absent_afternoon = self._find_absent_afternoon_collaborator(day, month, year, weekday)

                    print(f"Found afternoon substitute Collaboratore ID {substitute['id']}: {new_start}-{new_end}")

                    # Store afternoon substitutes separately (not tied to a specific location)
                    if 'afternoon_subs' not in schedule:
                        schedule['afternoon_subs'] = []
                    schedule['afternoon_subs'].append({
                        'collaboratore_id': substitute['id'],
                        'start': new_start,
                        'end': new_end,
                        'is_substitute': True,
                        'is_afternoon_sub': True,
                        'replaces_id': absent_afternoon['id'] if absent_afternoon else None,
                        'original_luogo_id': substitute['luogo_id']
                    })
                    afternoon_count += 1

                    # Update luogo_info and check if substitute's original location now needs coverage
                    luogo_info = self._calculate_luogo_info(schedule)
                    substitute_original_luogo = substitute['luogo_id']
                    if substitute_original_luogo in luogo_info and luogo_info[substitute_original_luogo].startswith("-"):
                        print(f"Afternoon substitute's original location (Luogo ID {substitute_original_luogo}) now needs coverage")
                        # Find a substitute for the substitute's original location
                        cascading_substitute = self.find_substitute(schedule, "substitute", needed_luogo_id=substitute_original_luogo)
                        if cascading_substitute:
                            print(f"Found cascading substitute Collaboratore ID {cascading_substitute['id']} for Luogo ID {substitute_original_luogo}")
                            if substitute_original_luogo not in schedule:
                                schedule[substitute_original_luogo] = []
                            schedule[substitute_original_luogo].append({
                                'collaboratore_id': cascading_substitute['id'],
                                'start': cascading_substitute['orari_settimanali'][weekday]['inizio'],
                                'end': cascading_substitute['orari_settimanali'][weekday]['fine'],
                                'is_substitute': True,
                                'replaces_id': substitute['id'],
                                'original_luogo_id': cascading_substitute['luogo_id']
                            })
                            # Update luogo_info again after cascading substitution
                            luogo_info = self._calculate_luogo_info(schedule)
                        else:
                            print(f"No cascading substitute found for Luogo ID {substitute_original_luogo}")
                else:
                    print("No available substitute found for afternoon coverage.")
                    break
        return schedule
    
    def parse_result(self, schedule, weekday):
        result = {}
        for luogo_id, collaboratori in schedule.items():
            # Get string of luogo
            luogo_str = self._get_luogo_by_id(int(luogo_id))['nome']
            if luogo_str not in result:
                result[luogo_str] = {}
            for collaboratore in collaboratori:
                collab_id = collaboratore['collaboratore_id']
                collab = self._get_collaboratore_by_id(collab_id)
                collab_str = f"{collab['cognome']} {collab['nome']}"
                if not "original_luogo_id" in collaboratore or len(collaboratori) == 1:
                    result[luogo_str][collab_str] = {
                        'start': collaboratore['start'],
                        'end': collaboratore['end']
                    }
                else:
                    # This was a substitution. If it substituted someone who
                    # was doing the afternoon shift, after they come back
                    # they need to go back to their original location.
                    # So first we check if the other person was doing
                    # the afternoon shift.
                    print("Substitution detected for", collab_str)
                    for other_collaboratore in [c for c in collaboratori if c != collaboratore]:
                        other_start = other_collaboratore['start']
                        # Check if it is greater than their usual start time
                        other_usual_start = self._get_collaboratore_by_id(other_collaboratore['collaboratore_id'])['orari_settimanali'].get(weekday).get('inizio')
                        # Convert time strings to datetime objects for comparison
                        other_start_hour, other_start_minute = map(int, other_start.split(':'))
                        other_start_time = time(other_start_hour, other_start_minute)
                        
                        other_usual_start_hour, other_usual_start_minute = map(int, other_usual_start.split(':'))
                        other_usual_start_time = time(other_usual_start_hour, other_usual_start_minute)
                        
                        if other_start_time > other_usual_start_time:
                            result[luogo_str][collab_str] = {
                                'start': collaboratore['start'],
                                'partial_end': other_start,
                                'move_back_to': self._get_luogo_by_id(collaboratore['original_luogo_id'])['nome'],
                                'end': collaboratore['end']
                            }
                        else:
                            result[luogo_str][collab_str] = {
                                'start': collaboratore['start'],
                                'end': collaboratore['end']
                            }
        return dict(sorted(result.items()))

    def parse_substitutions_only(self, schedule):
        '''
        Parse only substitutions and return as a formatted string.
        '''
        result = []

        # Process location-based substitutes
        for luogo_id, collaboratori in schedule.items():
            # Skip special keys
            if luogo_id in ['afternoon_subs', 'cleaning_overtime']:
                continue

            luogo_str = self._get_luogo_by_id(int(luogo_id))['nome']
            subs_for_location = []

            for collaboratore in collaboratori:
                # Only include substitutes
                if collaboratore.get('is_substitute', False):
                    collab_id = collaboratore['collaboratore_id']
                    collab = self._get_collaboratore_by_id(collab_id)
                    collab_str = f"{collab['cognome']} {collab['nome']}"
                    start = collaboratore['start']
                    end = collaboratore['end']

                    # Check if it's a partial substitution (covering morning gap for turnazione)
                    if 'partial_end' in collaboratore and 'original_luogo_id' in collaboratore:
                        partial_end = collaboratore['partial_end']
                        original_luogo = self._get_luogo_by_id(collaboratore['original_luogo_id'])
                        original_luogo_str = original_luogo['nome']
                        replaces_id = collaboratore.get('replaces_id')
                        if replaces_id:
                            absent_collab = self._get_collaboratore_by_id(replaces_id)
                            absent_str = f"{absent_collab['cognome']} {absent_collab['nome']}"
                            subs_for_location.append(f"- {collab_str} entra alle {start}, alle {partial_end} torna a {original_luogo_str}, esce alle {end} (sostituisce {absent_str})")
                        else:
                            subs_for_location.append(f"- {collab_str} entra alle {start}, alle {partial_end} torna a {original_luogo_str}, esce alle {end}")
                    else:
                        # Regular full-day substitution
                        replaces_id = collaboratore.get('replaces_id')
                        if replaces_id:
                            absent_collab = self._get_collaboratore_by_id(replaces_id)
                            absent_str = f"{absent_collab['cognome']} {absent_collab['nome']}"
                            subs_for_location.append(f"- {collab_str} entra alle {start} ed esce alle {end} (sostituisce {absent_str})")
                        else:
                            subs_for_location.append(f"- {collab_str} entra alle {start} ed esce alle {end}")

            # Only add location if it has substitutions
            if subs_for_location:
                result.append(f"{luogo_str}:")
                result.extend(subs_for_location)
                result.append("")  # Empty line between locations

        # Process afternoon substitutes separately
        if 'afternoon_subs' in schedule:
            result.append("POMERIGGIO:")
            for collaboratore in schedule['afternoon_subs']:
                collab_id = collaboratore['collaboratore_id']
                collab = self._get_collaboratore_by_id(collab_id)
                collab_str = f"{collab['cognome']} {collab['nome']}"
                start = collaboratore['start']
                end = collaboratore['end']

                replaces_id = collaboratore.get('replaces_id')
                if replaces_id:
                    absent_collab = self._get_collaboratore_by_id(replaces_id)
                    absent_str = f"{absent_collab['cognome']} {absent_collab['nome']}"
                    result.append(f"- {collab_str} entra alle {start} ed esce alle {end} (sostituisce {absent_str})")
                else:
                    result.append(f"- {collab_str} entra alle {start} ed esce alle {end}")
            result.append("")

        # Process cleaning overtime assignments
        if 'cleaning_overtime' in schedule and schedule['cleaning_overtime']:
            result.append("STRAORDINARI PER PULIZIA:")
            for cleaning in schedule['cleaning_overtime']:
                collab_id = cleaning['collaboratore_id']
                collab = self._get_collaboratore_by_id(collab_id)
                collab_str = f"{collab['cognome']} {collab['nome']}"
                location_name = cleaning['location_name']
                overtime_minutes = cleaning['overtime_minutes']
                result.append(f"- {collab_str}: {overtime_minutes} minuti per pulizia di {location_name}")
            result.append("")

        return "\n".join(result).strip()

    def assign_cleaning_overtime(self, schedule, weekday):
        """
        Assigns cleaning overtime to collaborators when someone is missing from a location.
        Each location has N people who normally work there, and they all clean at the end of the day.
        If someone is missing (even if minimum coverage is met), someone else needs to do 20 minutes
        of cleaning overtime.
        """
        # Initialize cleaning_overtime list if not exists
        if 'cleaning_overtime' not in schedule:
            schedule['cleaning_overtime'] = []

        # Track who has already been assigned cleaning overtime today (max 20 minutes per day)
        assigned_today = set()

        # For each location, count how many people normally work there
        locations_normal_count = {}
        for collaboratore in self.collaboratori:
            luogo_id = collaboratore.get('luogo_id')
            if luogo_id is not None:
                if luogo_id not in locations_normal_count:
                    locations_normal_count[luogo_id] = 0
                locations_normal_count[luogo_id] += 1

        # For each location, count how many people are present at the end of the day
        for luogo_id, normal_count in locations_normal_count.items():
            # Check if this location needs cleaning
            luogo = self._get_luogo_by_id(luogo_id)
            if not luogo:
                continue

            if luogo.get('no_cleaning_needed', False):
                print(f"Location {luogo['nome']} doesn't need cleaning, skipping")
                continue

            # Count people present at the end of day at this location
            present_count = self._count_present_at_end_of_day(schedule, luogo_id)

            missing_count = normal_count - present_count

            if missing_count > 0:
                print(f"Location {luogo['nome']} is missing {missing_count} people for cleaning")

                # For each missing person, assign cleaning overtime
                for _ in range(missing_count):
                    overtime_person = self._find_cleaning_overtime_candidate(schedule, weekday, assigned_today)

                    if overtime_person:
                        print(f"Assigning cleaning overtime to {overtime_person['nome']} {overtime_person['cognome']} for location {luogo['nome']}")

                        # Mark this person as assigned today (they can't be assigned again)
                        assigned_today.add(overtime_person['id'])

                        # Record the cleaning overtime assignment
                        schedule['cleaning_overtime'].append({
                            'collaboratore_id': overtime_person['id'],
                            'location_id': luogo_id,
                            'location_name': luogo['nome'],
                            'overtime_minutes': 20
                        })
                    else:
                        print(f"WARNING: No one available for cleaning overtime at location {luogo['nome']}")

        return schedule

    def _count_present_at_end_of_day(self, schedule, luogo_id):
        """
        Count how many people are ACTUALLY present at this location at the end of the day.

        This includes:
        - People normally assigned there who are present
        - Regular substitutes working at this location
        - Afternoon substitutes working at this location
        - People with turnazione (they come late but leave at normal time, so they can clean)

        The key principle: whoever is physically at a location at end of day can clean that location.
        """
        count = 0
        present_ids = set()

        # First, identify who is doing afternoon shifts elsewhere
        afternoon_sub_ids = set()
        if 'afternoon_subs' in schedule:
            for assignment in schedule['afternoon_subs']:
                afternoon_sub_ids.add(assignment['collaboratore_id'])

        # Count people in the regular schedule at this location
        if luogo_id in schedule:
            for assignment in schedule[luogo_id]:
                collab_id = assignment['collaboratore_id']

                # Skip if this person is doing afternoon shift elsewhere
                # (they won't be here at end of day)
                if collab_id in afternoon_sub_ids:
                    collab = self._get_collaboratore_by_id(collab_id)
                    if collab and collab.get('luogo_id') == luogo_id:
                        # This person normally works here but is doing afternoon elsewhere
                        continue

                # Anyone assigned to this location at end of day can clean
                if 'end' in assignment:
                    present_ids.add(collab_id)
                    count += 1

        # Count afternoon substitutes at this location
        if 'afternoon_subs' in schedule:
            for assignment in schedule['afternoon_subs']:
                # Check if this afternoon sub is assigned to this location
                # Afternoon subs replace someone, so we need to find which location
                replaces_id = assignment.get('replaces_id')
                if replaces_id:
                    replaced_collab = self._get_collaboratore_by_id(replaces_id)
                    if replaced_collab and replaced_collab.get('luogo_id') == luogo_id:
                        # This afternoon sub is covering this location
                        collab_id = assignment['collaboratore_id']
                        if collab_id not in present_ids:
                            count += 1

        return count

    def _find_cleaning_overtime_candidate(self, schedule, weekday, assigned_today):
        """
        Find the best candidate for cleaning overtime.
        Criteria:
        - Must be present that day
        - Must not have no_overtime_allowed flag set
        - Must not have already been assigned cleaning overtime today (max 20 min/day)
        - Select the one with least straordinari_svolti
        """
        candidates = []

        # Get all collaborators who are present that day
        present_ids = set()
        for luogo_id, assignments in schedule.items():
            if luogo_id == 'afternoon_subs' or luogo_id == 'cleaning_overtime':
                continue
            for assignment in assignments:
                present_ids.add(assignment['collaboratore_id'])

        # Filter candidates
        for collaboratore in self.collaboratori:
            # Must be present that day
            if collaboratore['id'] not in present_ids:
                continue

            # Must be able to do overtime
            if collaboratore.get('no_overtime_allowed', False):
                continue

            # Must not have already been assigned cleaning overtime today
            if collaboratore['id'] in assigned_today:
                continue

            # Must have working hours on this day
            if weekday not in collaboratore.get('orari_settimanali', {}):
                continue

            candidates.append(collaboratore)

        if not candidates:
            return None

        # Select the one with least overtime
        min_overtime = min(c.get('straordinari_svolti', 0) for c in candidates)
        for candidate in candidates:
            if candidate.get('straordinari_svolti', 0) == min_overtime:
                return candidate

        return None

    def generate(self, day, month, year, weekday):
        schedule = self.generate_schedule(day, month, year, weekday)

        # Assign cleaning overtime if needed
        schedule = self.assign_cleaning_overtime(schedule, weekday)

        with open("final_schedule_after_substitutions.json", "w") as final_file:
            json.dump(schedule, final_file, indent=4)

        substitutions_text = self.parse_substitutions_only(schedule)

        with open("parsed_schedule.json", "w") as parsed_file:
            json.dump({"substitutions_text": substitutions_text}, parsed_file, indent=4)

        return substitutions_text