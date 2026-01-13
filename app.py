from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import json
import os
from datetime import datetime
from generator import Generator

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

DATA_DIR = 'data'

def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return [] if filename != 'orari_pomeriggio.json' else {}

def save_json(filename, data):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/luoghi', methods=['GET', 'POST'])
def luoghi():
    if request.method == 'POST':
        luoghi_data = load_json('luoghi.json')

        nome = request.form.get('nome')
        descrizione = request.form.get('descrizione')
        min_collaboratori = int(request.form.get('min_collaboratori', 1))
        no_cleaning_needed = request.form.get('no_cleaning_needed') == 'on'

        luogo = {
            'id': len(luoghi_data) + 1,
            'nome': nome,
            'descrizione': descrizione,
            'min_collaboratori': min_collaboratori,
            'no_cleaning_needed': no_cleaning_needed
        }

        luoghi_data.append(luogo)
        save_json('luoghi.json', luoghi_data)

        return redirect(url_for('luoghi'))

    luoghi_data = load_json('luoghi.json')
    return render_template('luoghi.html', luoghi=luoghi_data)

@app.route('/luoghi/elimina/<int:id>', methods=['POST'])
def elimina_luogo(id):
    luoghi_data = load_json('luoghi.json')
    luoghi_data = [l for l in luoghi_data if l['id'] != id]
    save_json('luoghi.json', luoghi_data)
    return redirect(url_for('luoghi'))

@app.route('/collaboratori', methods=['GET', 'POST'])
def collaboratori():
    if request.method == 'POST':
        collaboratori_data = load_json('collaboratori.json')

        nome = request.form.get('nome')
        cognome = request.form.get('cognome')
        luogo_id = int(request.form.get('luogo_id')) if request.form.get('luogo_id') else None
        luogo_secondario_id = int(request.form.get('luogo_secondario_id')) if request.form.get('luogo_secondario_id') else None
        fisso_nel_luogo = request.form.get('fisso_nel_luogo') == 'on'

        orari_settimanali = {}
        giorni = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato']
        for giorno in giorni:
            inizio = request.form.get(f'{giorno}_inizio')
            fine = request.form.get(f'{giorno}_fine')
            if inizio and fine:
                orari_settimanali[giorno] = {
                    'inizio': inizio,
                    'fine': fine
                }

        ultima_sostituzione = request.form.get('ultima_sostituzione') or None
        straordinari_svolti = int(request.form.get('straordinari_svolti', 0))
        no_overtime_allowed = request.form.get('no_overtime_allowed') == 'on'

        collaboratore = {
            'id': len(collaboratori_data) + 1,
            'nome': nome,
            'cognome': cognome,
            'luogo_id': luogo_id,
            'luogo_secondario_id': luogo_secondario_id,
            'fisso_nel_luogo': fisso_nel_luogo,
            'orari_settimanali': orari_settimanali,
            'ultima_sostituzione': ultima_sostituzione,
            'straordinari_svolti': straordinari_svolti,
            'no_overtime_allowed': no_overtime_allowed
        }

        collaboratori_data.append(collaboratore)
        save_json('collaboratori.json', collaboratori_data)

        return redirect(url_for('collaboratori'))

    collaboratori_data = load_json('collaboratori.json')
    luoghi_data = load_json('luoghi.json')
    return render_template('collaboratori.html', collaboratori=collaboratori_data, luoghi=luoghi_data)

@app.route('/collaboratori/elimina/<int:id>', methods=['POST'])
def elimina_collaboratore(id):
    collaboratori_data = load_json('collaboratori.json')
    collaboratori_data = [c for c in collaboratori_data if c['id'] != id]
    save_json('collaboratori.json', collaboratori_data)
    return redirect(url_for('collaboratori'))

@app.route('/collaboratori/modifica/<int:id>', methods=['GET', 'POST'])
def modifica_collaboratore(id):
    collaboratori_data = load_json('collaboratori.json')
    luoghi_data = load_json('luoghi.json')

    # Find the collaboratore to edit
    collaboratore = next((c for c in collaboratori_data if c['id'] == id), None)
    if not collaboratore:
        return redirect(url_for('collaboratori'))

    if request.method == 'POST':
        # Update collaboratore data
        collaboratore['nome'] = request.form.get('nome')
        collaboratore['cognome'] = request.form.get('cognome')
        collaboratore['luogo_id'] = int(request.form.get('luogo_id')) if request.form.get('luogo_id') else None
        collaboratore['luogo_secondario_id'] = int(request.form.get('luogo_secondario_id')) if request.form.get('luogo_secondario_id') else None
        collaboratore['fisso_nel_luogo'] = request.form.get('fisso_nel_luogo') == 'on'

        # Update orari settimanali
        orari_settimanali = {}
        giorni = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato']
        for giorno in giorni:
            inizio = request.form.get(f'{giorno}_inizio')
            fine = request.form.get(f'{giorno}_fine')
            if inizio and fine:
                orari_settimanali[giorno] = {
                    'inizio': inizio,
                    'fine': fine
                }
        collaboratore['orari_settimanali'] = orari_settimanali

        # Update new fields
        collaboratore['ultima_sostituzione'] = request.form.get('ultima_sostituzione') or None
        collaboratore['straordinari_svolti'] = int(request.form.get('straordinari_svolti', 0))
        collaboratore['no_overtime_allowed'] = request.form.get('no_overtime_allowed') == 'on'

        save_json('collaboratori.json', collaboratori_data)
        return redirect(url_for('collaboratori'))

    return render_template('modifica_collaboratore.html', collaboratore=collaboratore, luoghi=luoghi_data)

@app.route('/coperture-fisse', methods=['GET', 'POST'])
def coperture_fisse():
    if request.method == 'POST':
        coperture_data = load_json('coperture_fisse.json')

        collaboratore_id = int(request.form.get('collaboratore_id'))
        giorno_settimana = request.form.get('giorno_settimana')
        luogo_coperto_id = int(request.form.get('luogo_coperto_id'))

        copertura = {
            'id': len(coperture_data) + 1,
            'collaboratore_id': collaboratore_id,
            'giorno_settimana': giorno_settimana,
            'luogo_coperto_id': luogo_coperto_id
        }

        coperture_data.append(copertura)
        save_json('coperture_fisse.json', coperture_data)

        return redirect(url_for('coperture_fisse'))

    coperture_data = load_json('coperture_fisse.json')
    collaboratori_data = load_json('collaboratori.json')
    luoghi_data = load_json('luoghi.json')
    return render_template('coperture_fisse.html', coperture=coperture_data, collaboratori=collaboratori_data, luoghi=luoghi_data)

@app.route('/coperture-fisse/elimina/<int:id>', methods=['POST'])
def elimina_copertura(id):
    coperture_data = load_json('coperture_fisse.json')
    coperture_data = [c for c in coperture_data if c['id'] != id]
    save_json('coperture_fisse.json', coperture_data)
    return redirect(url_for('coperture_fisse'))

@app.route('/orari-pomeriggio', methods=['GET', 'POST'])
def orari_pomeriggio():
    if request.method == 'POST':
        orari_data = {}

        giorni = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato']
        for giorno in giorni:
            attivo = request.form.get(f'{giorno}_attivo')
            if attivo:
                ora_fine = request.form.get(f'{giorno}_fine')
                num_collaboratori = request.form.get(f'{giorno}_num_collaboratori')
                if ora_fine:
                    orari_data[giorno] = {
                        'attivo': True,
                        'ora_fine': ora_fine,
                        'num_collaboratori': int(num_collaboratori) if num_collaboratori else 0
                    }

        save_json('orari_pomeriggio.json', orari_data)
        return redirect(url_for('orari_pomeriggio'))

    orari_data = load_json('orari_pomeriggio.json')
    return render_template('orari_pomeriggio.html', orari=orari_data)

@app.route('/turnazioni', methods=['GET', 'POST'])
def turnazioni():
    if request.method == 'POST':
        turnazioni_data = load_json('turnazioni.json')

        collaboratore_id = int(request.form.get('collaboratore_id'))
        giorno_settimana = request.form.get('giorno_settimana')
        mese = request.form.get('mese')
        anno = int(request.form.get('anno'))
        fa_pomeriggio = request.form.get('fa_pomeriggio') == 'on'
        ora_ingresso_alternativa = request.form.get('ora_ingresso_alternativa') if fa_pomeriggio else None

        turnazione = {
            'id': len(turnazioni_data) + 1,
            'collaboratore_id': collaboratore_id,
            'giorno_settimana': giorno_settimana,
            'mese': mese,
            'anno': anno,
            'fa_pomeriggio': fa_pomeriggio,
            'ora_ingresso_alternativa': ora_ingresso_alternativa
        }

        turnazioni_data.append(turnazione)
        save_json('turnazioni.json', turnazioni_data)

        return redirect(url_for('turnazioni'))

    turnazioni_data = load_json('turnazioni.json')
    collaboratori_data = load_json('collaboratori.json')
    return render_template('turnazioni.html', turnazioni=turnazioni_data, collaboratori=collaboratori_data)

@app.route('/turnazioni/elimina/<int:id>', methods=['POST'])
def elimina_turnazione(id):
    turnazioni_data = load_json('turnazioni.json')
    turnazioni_data = [t for t in turnazioni_data if t['id'] != id]
    save_json('turnazioni.json', turnazioni_data)
    return redirect(url_for('turnazioni'))

@app.route('/assenze', methods=['GET', 'POST'])
def assenze():
    if request.method == 'POST':
        assenze_data = load_json('assenze.json')

        collaboratore_id = int(request.form.get('collaboratore_id'))
        data = request.form.get('data')
        tutto_giorno = request.form.get('tutto_giorno') == 'on'
        ora_inizio = request.form.get('ora_inizio') if not tutto_giorno else None
        ora_fine = request.form.get('ora_fine') if not tutto_giorno else None

        assenza = {
            'id': len(assenze_data) + 1,
            'collaboratore_id': collaboratore_id,
            'data': data,
            'tutto_giorno': tutto_giorno,
            'ora_inizio': ora_inizio,
            'ora_fine': ora_fine
        }

        assenze_data.append(assenza)
        save_json('assenze.json', assenze_data)

        return redirect(url_for('assenze'))

    assenze_data = load_json('assenze.json')
    collaboratori_data = load_json('collaboratori.json')
    return render_template('assenze.html', assenze=assenze_data, collaboratori=collaboratori_data)

@app.route('/assenze/elimina/<int:id>', methods=['POST'])
def elimina_assenza(id):
    assenze_data = load_json('assenze.json')
    assenze_data = [a for a in assenze_data if a['id'] != id]
    save_json('assenze.json', assenze_data)
    return redirect(url_for('assenze'))

@app.route('/genera', methods=['GET', 'POST'])
def genera():
    if request.method == 'POST':
        # Get the date from the form
        data_str = request.form.get('data')
        data = datetime.strptime(data_str, '%Y-%m-%d')

        # Extract day, month, year
        day = data.day
        month = data.month
        year = data.year

        # Map weekday to Italian
        giorni_settimana = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato', 'domenica']
        weekday = giorni_settimana[data.weekday()]

        generator = Generator()
        sostituzioni = generator.generate(
            day=day,
            month=month,
            year=year,
            weekday=weekday
        )

        # Store the schedule data in session for the "Ufficializza" action
        # Read the schedule from the JSON file that was just written
        with open('final_schedule_after_substitutions.json', 'r') as f:
            schedule = json.load(f)

        session['last_schedule'] = schedule
        session['last_date'] = data_str

        return render_template('genera.html', sostituzioni=sostituzioni, generato=True)

    return render_template('genera.html', sostituzioni=None, generato=False)

@app.route('/ufficializza', methods=['POST'])
def ufficializza():
    # Get the schedule from session
    schedule = session.get('last_schedule')
    date_str = session.get('last_date')

    if not schedule or not date_str:
        return jsonify({'success': False, 'message': 'Nessuna sostituzione da ufficializzare'}), 400

    # Load collaboratori data
    collaboratori_data = load_json('collaboratori.json')

    # Create a map of collaboratore_id to collaboratore for easy lookup
    collab_map = {c['id']: c for c in collaboratori_data}

    # Track all collaborators who did substitutions
    substitute_ids = set()

    # Process location-based substitutes
    for luogo_id, collaboratori in schedule.items():
        if luogo_id in ['afternoon_subs', 'cleaning_overtime']:
            continue

        for collaboratore in collaboratori:
            if collaboratore.get('is_substitute', False):
                substitute_ids.add(collaboratore['collaboratore_id'])

    # Process afternoon substitutes
    if 'afternoon_subs' in schedule:
        for collaboratore in schedule['afternoon_subs']:
            substitute_ids.add(collaboratore['collaboratore_id'])

    # Update ultima_sostituzione for all substitutes
    for collab_id in substitute_ids:
        if collab_id in collab_map:
            collab_map[collab_id]['ultima_sostituzione'] = date_str

    # Process cleaning overtime assignments
    if 'cleaning_overtime' in schedule:
        for cleaning in schedule['cleaning_overtime']:
            collab_id = cleaning['collaboratore_id']
            overtime_minutes = cleaning['overtime_minutes']

            if collab_id in collab_map:
                current_overtime = collab_map[collab_id].get('straordinari_svolti', 0)
                collab_map[collab_id]['straordinari_svolti'] = current_overtime + overtime_minutes

    # Save the updated collaboratori data
    save_json('collaboratori.json', collaboratori_data)

    # Clear the session data
    session.pop('last_schedule', None)
    session.pop('last_date', None)

    return jsonify({'success': True, 'message': 'Sostituzioni ufficializzate con successo!'})


if __name__ == '__main__':
    app.run(debug=True)
