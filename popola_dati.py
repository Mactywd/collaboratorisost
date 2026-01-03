import csv
import json
import re

# Mappatura mesi in italiano
MESI = {
    'gennaio': 'gennaio',
    'febbraio': 'febbraio',
    'marzo': 'marzo',
    'aprile': 'aprile',
    'maggio': 'maggio',
    'giugno': 'giugno',
    'luglio': 'luglio',
    'agosto': 'agosto',
    'settembre': 'settembre',
    'ottobre': 'ottobre',
    'novembre': 'novembre',
    'dicembre': 'dicembre'
}

GIORNI = {
    'Lunedi': 'lunedi',
    'Martedi': 'martedi',
    'Mercoledi': 'mercoledi',
    'Giovedi': 'giovedi',
    'Venerdi': 'venerdi'
}

def parse_orario(orario_str):
    """Estrae l'orario base da una stringa (es. '7:54 - 14:57' o '7:54 - 14:57 (novembre 10:48 - 18:00)')"""
    if 'assente' in orario_str.lower():
        return None

    # Estrae solo la parte prima della parentesi
    orario_base = orario_str.split('(')[0].strip()

    # Rimuove eventuali note dopo l'orario (es. "in Portineria", "al Bar")
    orario_base = re.split(r'\s+(in|al)\s+', orario_base)[0].strip()

    # Parse orario (es. "7:54 - 14:57")
    match = re.match(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', orario_base)
    if match:
        return {
            'inizio': match.group(1),
            'fine': match.group(2)
        }
    return None

def parse_turnazione(orario_str):
    """Estrae la turnazione mensile se presente (es. '(novembre 10:48 - 18:00)')"""
    match = re.search(r'\((\w+)\s+(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\)', orario_str)
    if match:
        mese = match.group(1).lower()
        if mese in MESI:
            return {
                'mese': MESI[mese],
                'ora_inizio': match.group(2),
                'ora_ingresso': match.group(2)
            }
    return None

def parse_copertura(orario_str):
    """Estrae la copertura fissa se presente (es. 'in Portineria', 'al Bar')"""
    match = re.search(r'(in|al)\s+(.+?)$', orario_str)
    if match:
        return match.group(2).strip()
    return None

# Leggi CSV
luoghi_set = set()
collaboratori = []
turnazioni = []
coperture = []

with open('Orari Collaboratori - Foglio1.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)

    collab_id = 1
    turn_id = 1
    cop_id = 1

    for row in reader:
        # Estrai nome e cognome
        nome_completo = row['Nome (P = Part Time)'].replace(' (P)', '').strip()
        parti_nome = nome_completo.split()
        cognome = parti_nome[0]
        nome = ' '.join(parti_nome[1:]) if len(parti_nome) > 1 else ''

        # Luogo di competenza
        luogo_assegnazione = row['Assegnazione'].strip()
        luoghi_set.add(luogo_assegnazione)

        # Orari settimanali
        orari_settimanali = {}

        for giorno_it, giorno_key in GIORNI.items():
            if giorno_it in row:
                orario_str = row[giorno_it].strip()
                orario = parse_orario(orario_str)

                if orario:
                    orari_settimanali[giorno_key] = orario

                # Controlla turnazione
                turnazione = parse_turnazione(orario_str)
                if turnazione:
                    turnazioni.append({
                        'id': turn_id,
                        'collaboratore_id': collab_id,
                        'giorno_settimana': giorno_key,
                        'mese': turnazione['mese'],
                        'anno': 2025,
                        'fa_pomeriggio': True,
                        'ora_ingresso_alternativa': turnazione['ora_ingresso']
                    })
                    turn_id += 1

                # Controlla copertura fissa
                copertura = parse_copertura(orario_str)
                if copertura:
                    luoghi_set.add(copertura)
                    # Aggiungiamo la copertura dopo aver creato tutti i luoghi
                    coperture.append({
                        'collaboratore_id': collab_id,
                        'giorno_settimana': giorno_key,
                        'luogo_coperto_nome': copertura
                    })

        # Determina se il collaboratore è fisso nel luogo (solo Maria Pragliola in Palestra)
        fisso_nel_luogo = (cognome == 'Pragliola' and nome == 'Maria' and luogo_assegnazione == 'Palestra')

        # Crea collaboratore
        collaboratori.append({
            'id': collab_id,
            'nome': nome,
            'cognome': cognome,
            'luogo_nome': luogo_assegnazione,
            'fisso_nel_luogo': fisso_nel_luogo,
            'orari_settimanali': orari_settimanali
        })

        collab_id += 1

# Crea luoghi.json
luoghi = []
luogo_map = {}
for idx, luogo_nome in enumerate(sorted(luoghi_set), 1):
    # Determina il numero minimo di collaboratori (0 per Pendolo e Segreteria, 1 per gli altri)
    min_collaboratori = 0 if luogo_nome in ['Pendolo', 'Segreteria'] else 1

    luogo = {
        'id': idx,
        'nome': luogo_nome,
        'descrizione': '',
        'min_collaboratori': min_collaboratori
    }
    luoghi.append(luogo)
    luogo_map[luogo_nome] = idx

# Associa luogo_id ai collaboratori
for collab in collaboratori:
    collab['luogo_id'] = luogo_map.get(collab['luogo_nome'])
    del collab['luogo_nome']

# Associa luogo_id alle coperture
coperture_fisse = []
for idx, cop in enumerate(coperture, 1):
    coperture_fisse.append({
        'id': idx,
        'collaboratore_id': cop['collaboratore_id'],
        'giorno_settimana': cop['giorno_settimana'],
        'luogo_coperto_id': luogo_map.get(cop['luogo_coperto_nome'])
    })

# Crea orari_pomeriggio.json
orari_pomeriggio = {
    'martedi': {
        'attivo': True,
        'ora_fine': '18:00',
        'num_collaboratori': 2
    },
    'venerdi': {
        'attivo': True,
        'ora_fine': '18:00',
        'num_collaboratori': 4
    }
}

# Salva JSON
with open('data/luoghi.json', 'w', encoding='utf-8') as f:
    json.dump(luoghi, f, ensure_ascii=False, indent=2)

with open('data/collaboratori.json', 'w', encoding='utf-8') as f:
    json.dump(collaboratori, f, ensure_ascii=False, indent=2)

with open('data/turnazioni.json', 'w', encoding='utf-8') as f:
    json.dump(turnazioni, f, ensure_ascii=False, indent=2)

with open('data/coperture_fisse.json', 'w', encoding='utf-8') as f:
    json.dump(coperture_fisse, f, ensure_ascii=False, indent=2)

with open('data/orari_pomeriggio.json', 'w', encoding='utf-8') as f:
    json.dump(orari_pomeriggio, f, ensure_ascii=False, indent=2)

print(f"✓ Creati {len(luoghi)} luoghi")
print(f"✓ Creati {len(collaboratori)} collaboratori")
print(f"✓ Create {len(turnazioni)} turnazioni")
print(f"✓ Create {len(coperture_fisse)} coperture fisse")
print(f"✓ Configurati orari pomeriggio")
