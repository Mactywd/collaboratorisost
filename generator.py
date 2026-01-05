import json
from datetime import time

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
                start_hour, start_minute = map(int, start_time.split(':'))
                start_time_obj = time(start_hour, start_minute)
                target_time = time(8, 20)
                if start_time_obj <= target_time:
                    amount += 1
            min_required = self.luoghi[luogo_id - 1]['min_collaboratori']

            print(f"Luogo: {luogo["nome"]} ({luogo_id}). Num: {amount}. Min: {min_required}")

            if amount == min_required:
                luogo_info[luogo_id] = "EXACT"
            elif amount > min_required:
                luogo_info[luogo_id] = f"+{amount - min_required}"
            else:
                luogo_info[luogo_id] = f"-{min_required - amount}"
        
        return luogo_info

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
                    for sub_luogo_id in self.sub_order:
                        if sub_luogo_id in schedule and luogo_info[sub_luogo_id].startswith("+"):
                            for sub in schedule[sub_luogo_id]:
                                collaboratore = self._get_collaboratore_by_id(sub['collaboratore_id'])
                                if collaboratore and collaboratore['fisso_nel_luogo'] == False:
                                    
                                    # Apply schedule modification
                                    print(f"Reassigning Collaboratore ID {collaboratore['id']} from Luogo ID {sub_luogo_id} to Luogo ID {luogo_id}")
                                    schedule[sub_luogo_id].remove(sub)
                                    if luogo_id not in schedule:
                                        schedule[luogo_id] = []
                                    schedule[luogo_id].append({
                                        'collaboratore_id': collaboratore['id'],
                                        'start': sub['start'],
                                        'end': sub['end'],
                                        'original_luogo_id': sub_luogo_id
                                    })
                                    # Update luogo_info
                                    luogo_info = self._calculate_luogo_info(schedule)

                                    amount_needed -= 1
                                    if amount_needed == 0:
                                        break
                            if amount_needed == 0:
                                break
                    # If after going through sub_order we still need more, break to avoid infinite loop
                    if amount_needed > 0:
                        print("Not enough available collaborators to cover the shortage.")
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
                        
    def generate(self, day, month, year, weekday):
        schedule = self.generate_schedule(day, month, year, weekday)

        with open("final_schedule_after_substitutions.json", "w") as final_file:
            json.dump(schedule, final_file, indent=4)
        
        parsed = self.parse_result(schedule, weekday)
        
        with open("parsed_schedule.json", "w") as parsed_file:
            json.dump(parsed, parsed_file, indent=4)
        
        return parsed