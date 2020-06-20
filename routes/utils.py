from flask_api import status
from datetime import date, datetime, timedelta

def data2age(birthdate):
    if birthdate is None: return ''

    days_in_year = 365.2425
    birthdate = birthdate.split('T')[0]
    birthdate = datetime.strptime(birthdate, '%Y-%m-%d')
    age = int ((datetime.today() - birthdate).days / days_in_year)
    return age

def lenghStay(admissionDate):
    if admissionDate is None: return ''

    days = int ((datetime.today() - admissionDate).days)
    return days

def is_float(s):
    try:
        float(s)
        return True
    except:
        return False

def timeValue(time):
    numeric = str(time).strip().replace(' ','')
    if not is_float(numeric): return str(time).strip()
    else:
      timeList = str(time).strip().split(' ')
      if len(timeList) == 1:
        return 'Às ' + str(time).strip() + ' Horas'
      elif len(timeList) < 6:
        return 'às ' + ('h, às ').join(timeList) + 'h'
      else:
        return time

def freqValue(freq):
    if freq == 33: return 'SN'
    elif freq == 44: return 'ACM'
    elif freq == 99: return 'N/D'
    else: return freq

def none2zero(s):
    return s if is_float(s) else 0

def strNone(s):
    return '' if s is None else str(s)

def interactionsList(drugList, splitStr):
    result = []
    for d in drugList:
        part = d.split(splitStr)
        result.append({'name': part[0], 'idDrug': part[1]})

    return result

typeRelations = {}
typeRelations['dm'] = 'Duplicidade Medicamentosa'
typeRelations['dt'] = 'Duplicidade Terapêutica'
typeRelations['it'] = 'Interação Medicamentosa'
typeRelations['iy'] = 'Imcompatibilidade em Y'

examsName = {
    'cr':  'Creatinina',
    'mdrd':'MDRD',
    'cg':  'CG',
    'ckd': 'CKD-EPI',
    'pcru': 'PCR',
    'pcr': 'PCR',
    'rni': 'RNI',
    'pro': 'RNI',
    'tgo': 'TGO',
    'tgp': 'TGP',
    'k':   'Potássio',
    'na':  'Sódio',
    'mg':  'Magnésio',
    'h_eritr': 'Eritócitos',
    'h_hematoc': 'Hematócrito',
    'h_hemogl': 'Hemoglobina',
    'h_plt': 'Plaquetas',
    'h_vcm': 'V.C.M.',
    'h_hcm': 'H.C.M.',
    'h_chcm': 'C.H.C.M.',
    'h_rdw': 'R.D.W.',
    'h_conleuc': 'Leucóticos',
    'h_conbaso': 'Basófilos',
    'h_coneos': 'Eosinófilos',
    'h_consegm': 'Neutrófitos',
    'h_conlinfoc': 'Linfócitos',
    'h_conmono': 'Monócitos',
}

examsRef = {
    'tgo': { 'min': 0,   'max': 34,  'ref': 'até 34 U/L - Método: Cinético optimizado UV' },
    'tgp': { 'min': 0,   'max': 49,  'ref': '10 a 49 U/L - Método: Cinético optimizado UV' },
    'k':   { 'min': 3.5, 'max': 5.5, 'ref': '3,5 a 5,5 mEq/L - Método: Eletrodo Seletivo' },
    'na':  { 'min': 132, 'max': 146, 'ref': '132 a 146 mEq/L - Método: Eletrodo Seletivo' },
    'mg':  { 'min': 1.3, 'max': 2.7, 'ref': '1,3 a 2,7 mg/dl - Método: Clorofosfonazo III 1' },
    'rni': { 'min': 0,   'max': 1.3, 'ref': 'até 1,3 - Método: Coagulométrico automatizado ACL TOP 550' },
    'pro': { 'min': 0,   'max': 1.3, 'ref': 'até 1,3 - Método: Coagulométrico automatizado ACL TOP 550' },
    'cr':  { 'min': 0.3, 'max': 1.3, 'ref': '0,3 a 1,3 mg/dL (IFCC)' },
    'pcr': { 'min': 0,   'max': 3,   'ref': 'até 3,0 mg/L' },
    'pcru':{ 'min': 0,   'max': 3,   'ref': 'até 3,0 mg/L' },
    'h_plt':        { 'min': 150000, 'max': 440000},
    'h_vcm':        { 'min': 80,     'max': 98},
    'h_rdw':        { 'min': 0,      'max': 15},
    'h_hcm':        { 'min': 28,     'max': 32},
    'h_chcm':       { 'min': 32,     'max': 36},
    'h_hematoc':    { 'min': 39,     'max': 53},
    'h_hemogl':     { 'min': 12.8,   'max': 17.8},
    'h_eritr':      { 'min': 4.5,    'max': 6.1},
    'h_conleuc':    { 'min': 3600,   'max': 11000},
    'h_conlinfoc':  { 'min': 1000,   'max': 4500},
    'h_conmono':    { 'min': 100,    'max': 1000},
    'h_coneos':     { 'min': 0,      'max': 500},
    'h_conbaso':    { 'min': 0,      'max': 220},
    'h_consegm':    { 'min': 1500,   'max': 7000},
}

examEmpty = { 'value': None, 'alert': False, 'ref': None }

def examAlerts(p, patient):
    exams = {'tgo': p[7], 'tgp': p[8], 'cr': p[9], 'k': p[10], 'na': p[11], 'mg': p[12], 'rni': p[13], 'pcr': p[22]}
    exams['mdrd'] = mdrd_calc(str(p[9]), patient.birthdate, patient.gender, patient.skinColor)
    exams['cg'] = cg_calc(str(p[9]), patient.birthdate, patient.gender, patient.weight)
    exams['ckd'] = ckd_calc(str(p[9]), patient.birthdate, patient.gender, patient.skinColor)

    result = {}
    alertCount = 0
    for e in exams:
        value = exams[e]
        
        if value is None: 
            result[e] = examEmpty
        else:
            if e in ['mdrd', 'cg', 'ckd']:
                result[e] = value
                alertCount += int(value['alert'])
            else:            
                ref = examsRef[e]
                alert = not (value >= ref['min'] and value <= ref['max'] )
                alertCount += int(alert)
                result[e] = { 'value': value, 'alert': alert }

    return result['tgo'], result['tgp'], result['cr'], result['mdrd'], result['cg'],\
            result['k'], result['na'], result['mg'], result['rni'],\
            result['pcr'], result['ckd'], alertCount

def formatExam(exam, type):
    if exam is not None:
        if type in examsRef:
            ref = examsRef[type]
            alert = not (exam.value >= ref['min'] and exam.value <= ref['max'] )
            if not 'ref' in ref:
                ref['ref'] = 'de ' + str(ref['min']) + ' a ' + str(ref['max']) + ' ' + strNone(exam.unit) 
        else:
            ref = {'ref' : None, 'min': None , 'max': None}
            alert = False

        return { 'value': float(exam.value), 'unit': strNone(exam.unit), 'alert': alert,\
                 'date' : exam.date.isoformat(), 'ref': ref['ref'],
                 'min': ref['min'], 'max': ref['max']}
    else:
        examEmpty['date'] = None
        return examEmpty

def period(tuples):
    if len(tuples) > 0:
        last30 = (datetime.today() - timedelta(days=30))
        last = datetime.strptime(tuples[0].split(' ')[0]+'/'+str(last30.year), '%d/%m/%Y')
        more = last < last30

        dates = list(set([t.split(' ')[0] for t in tuples]))

        return ('+' if more else '') + str(len(dates)) + 'D'
    else:
        return '0D'

# Modification of Diet in Renal Disease
# based on https://www.kidney.org/content/mdrd-study-equation
# eGFR = 175 x (SCr)-1.154 x (age)-0.203 x 0.742 [if female] x 1.212 [if Black]
def mdrd_calc(cr, birthdate, gender, skinColor):
    if not is_float(cr): return examEmpty
    if birthdate is None: return examEmpty 
    
    age = data2age(birthdate.isoformat())
    if age == 0: return examEmpty

    eGFR = 175 * (float(cr))**(-1.154) * (age)**(-0.203)

    if gender == 'F': eGFR *= 0.742
    if skinColor == 'Negra': eGFR *= 1.212


    return { 'value': round(eGFR,1), 'ref': 'maior que 50 mL/min', 'alert': (eGFR < 50) }

# Cockcroft-Gault
# based on https://www.kidney.org/professionals/KDOQI/gfr_calculatorCoc
# CCr = {((140–age) x weight)/(72xSCr)} x 0.85 (if female)
def cg_calc(cr, birthdate, gender, weight):
    if not is_float(cr): return examEmpty
    if not is_float(weight): return examEmpty
    if birthdate is None: return examEmpty

    age = data2age(birthdate.isoformat())
    if age == 0: return examEmpty

    ccr = ((140 - age) * float(weight)) / (72 * float(cr))
    if gender == 'F': ccr *= 0.85

    return { 'value': round(ccr,1), 'ref': 'maior que 50 mL/min', 'alert': (ccr < 50) }

# Chronic Kidney Disease Epidemiology Collaboration
# based on https://www.kidney.org/professionals/kdoqi/gfr_calculator
def ckd_calc(cr, birthdate, gender, skinColor):
    if not is_float(cr): return examEmpty
    if birthdate is None: return examEmpty

    age = data2age(birthdate.isoformat())
    if age == 0: return examEmpty

    if gender == 'F':
        g = 0.7
        s = 166 if skinColor == 'Negra' else 144
        e = -1.209 if float(cr) > g else -0.329
    else:
        g = 0.9
        s = 163 if skinColor == 'Negra' else 141
        e = -1.209 if float(cr) > g else -0.411

    eGFR = s * (float(cr)/g)**(e) * (0.993)**(age)

    return { 'value': round(eGFR,1), 'ref': 'maior que 50 mL/min', 'alert': (eGFR < 50) }


def tryCommit(db, recId):
    try:
        db.session.commit()

        return {
            'status': 'success',
            'data': recId
        }, status.HTTP_200_OK
    except AssertionError as e:
        db.engine.dispose()

        return {
            'status': 'error',
            'message': str(e)
        }, status.HTTP_400_BAD_REQUEST
    except Exception as e:
        db.engine.dispose()

        return {
            'status': 'error',
            'message': str(e)
        }, status.HTTP_500_INTERNAL_SERVER_ERROR