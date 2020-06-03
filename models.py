from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text, and_, or_, desc, asc, distinct
from datetime import date, timedelta
from sqlalchemy.dialects import postgresql
from routes.utils import timeValue, interactionsList

db = SQLAlchemy()

def setSchema(schema):
    Prescription.setSchema(schema)
    Patient.setSchema(schema)
    InterventionReason.setSchema(schema)
    PrescriptionDrug.setSchema(schema)
    Outlier.setSchema(schema)
    Drug.setSchema(schema)
    MeasureUnit.setSchema(schema)
    Frequency.setSchema(schema)
    Segment.setSchema(schema)
    Department.setSchema(schema)
    Intervention.setSchema(schema)
    SegmentDepartment.setSchema(schema)
    Exams.setSchema(schema)
    PrescriptionAgg.setSchema(schema)
    MeasureUnitConvert.setSchema(schema)
    PrescriptionPic.setSchema(schema)
    OutlierObs.setSchema(schema)
    DrugAttributes.setSchema(schema)


class User(db.Model):
    __tablename__ = 'usuario'

    id = db.Column("idusuario", db.Integer, primary_key=True)
    name = db.Column('nome', db.String(250), nullable=False)
    email = db.Column("email", db.String(254), unique=True, nullable=False)
    password = db.Column('senha', db.String(128), nullable=False)
    schema = db.Column("schema", db.String, nullable=False)
    nameUrl = db.Column("getnameurl", db.String, nullable=False)
    logourl = db.Column("logourl", db.String, nullable=False)
    reports = db.Column("relatorios", postgresql.JSON, nullable=False)

    def find(id):
        return User.query.filter(User.id == id).first()

    def authenticate(email, password):
        return User.query.filter_by(email=email, password=password).first()


class Prescription(db.Model):
    __tablename__ = 'prescricao'

    id = db.Column("fkprescricao", db.Integer, primary_key=True)
    idPatient = db.Column("fkpessoa", db.Integer, nullable=False)
    admissionNumber = db.Column('nratendimento', db.Integer, nullable=True)
    idHospital = db.Column("fkhospital", db.Integer, nullable=False)
    idDepartment = db.Column("fksetor", db.Integer, nullable=False)
    idSegment = db.Column("idsegmento", db.Integer, nullable=False)
    date = db.Column("dtprescricao", db.DateTime, nullable=False)
    weight = db.Column('peso', db.Float, nullable=True)
    status = db.Column('status', db.String(1), nullable=False)
    update = db.Column("update_at", db.DateTime, nullable=True)
    user = db.Column("update_by", db.Integer, nullable=True)

    def setSchema(schema):
        Prescription.__table__.schema = schema

    def getPrescription(idPrescription):
        score = getAggScore()

        return db.session\
            .query(
                Prescription, Patient, func.trunc(0).label('daysAgo'), score,
                Department.name.label('department'), Segment.description
            )\
            .outerjoin(Patient, Patient.admissionNumber == Prescription.admissionNumber)\
            .outerjoin(Department, Department.id == Prescription.idDepartment)\
            .outerjoin(Segment, Segment.id == Prescription.idSegment)\
            .filter(Prescription.id == idPrescription)\
            .first()

def getAggScore():
    return db.session.query(func.sum(func.coalesce(func.coalesce(Outlier.manualScore, Outlier.score), 4)).label('score'))\
        .select_from(PrescriptionDrug)\
        .outerjoin(Outlier, and_(Outlier.id == PrescriptionDrug.idOutlier))\
        .filter(PrescriptionDrug.idPrescription == Prescription.id)\
        .filter(PrescriptionDrug.route != None)\
        .as_scalar()

def getScore(level):
    return db.session.query(func.count(func.coalesce(func.coalesce(Outlier.manualScore, Outlier.score), 4)).label('scoreOne'))\
        .select_from(PrescriptionDrug)\
        .outerjoin(Outlier, and_(Outlier.id == PrescriptionDrug.idOutlier))\
        .filter(PrescriptionDrug.idPrescription == Prescription.id)\
        .filter(PrescriptionDrug.route != None)\
        .filter(func.coalesce(Outlier.manualScore, Outlier.score) == level)\
        .as_scalar()

def getHighScore():
    return db.session.query(func.count(func.coalesce(func.coalesce(Outlier.manualScore, Outlier.score), 4)).label('scoreOne'))\
        .select_from(PrescriptionDrug)\
        .outerjoin(Outlier, and_(Outlier.id == PrescriptionDrug.idOutlier))\
        .filter(PrescriptionDrug.idPrescription == Prescription.id)\
        .filter(PrescriptionDrug.route != None)\
        .filter(or_(func.coalesce(Outlier.manualScore, Outlier.score) == 3, func.coalesce(Outlier.manualScore, Outlier.score) == None))\
        .as_scalar()

def getExams(typeExam):
    return db.session.query(Exams.value)\
        .select_from(Exams)\
        .filter(Exams.idPatient == Prescription.idPatient)\
        .filter(Exams.typeExam == typeExam)\
        .order_by(Exams.date.desc()).limit(1)\
        .as_scalar()

def getDrugClass(typeClass):
    return db.session.query(func.count(1).label('drugClass'))\
        .select_from(DrugAttributes)\
        .outerjoin(PrescriptionDrug, and_(DrugAttributes.idDrug == PrescriptionDrug.idDrug, DrugAttributes.idSegment == PrescriptionDrug.idSegment))\
        .filter(PrescriptionDrug.idPrescription == Prescription.id)\
        .filter(typeClass == True)\
        .as_scalar()

def getDrugRoute(route):
    return db.session.query(func.count(1).label('drugRoute'))\
        .select_from(PrescriptionDrug)\
        .filter(PrescriptionDrug.idPrescription == Prescription.id)\
        .filter(PrescriptionDrug.route.ilike(route))\
        .as_scalar()

def getDrugsCount():
    return db.session.query(func.count(1).label('drugCount'))\
        .select_from(PrescriptionDrug, Prescription)\
        .filter(PrescriptionDrug.idPrescription == Prescription.id)\
        .filter(PrescriptionDrug.route != None)\
        .as_scalar()

def getPendingInterventions():
    return db.session.query(func.count(1).label('pendingInterventions'))\
        .select_from(Intervention)\
        .join(PrescriptionDrug, Intervention.id == PrescriptionDrug.id)\
        .filter(Intervention.admissionNumber == Prescription.admissionNumber)\
        .filter(Intervention.status == 's')\
        .filter(PrescriptionDrug.idPrescription < Prescription.id)\
        .as_scalar() 

def getDrugDiff():
    return db.session.query(func.count(1).label('drugDiff'))\
        .select_from(PrescriptionDrug, Prescription)\
        .filter(PrescriptionDrug.idPrescription == Prescription.id)\
        .filter(PrescriptionDrug.route != None)\
        .filter(PrescriptionDrug.checked == True)\
        .as_scalar() 

class Patient(db.Model):
    __tablename__ = 'pessoa'

    id = db.Column("fkpessoa", db.Integer, primary_key=True)
    fkHospital = db.Column("fkhospital", db.Integer, nullable=False)
    admissionNumber = db.Column('nratendimento', db.Integer, nullable=False)
    admissionDate = db.Column('dtinternacao', db.DateTime, nullable=True)
    birthdate = db.Column('dtnascimento', db.DateTime, nullable=True)
    gender = db.Column('sexo', db.String(1), nullable=True)
    weight = db.Column('peso', db.Float, nullable=True)
    weightDate = db.Column('dtpeso', db.DateTime, nullable=True)
    skinColor = db.Column('cor', db.String, nullable=True)

    def setSchema(schema):
        Patient.__table__.schema = schema

    def getPatients(idSegment=None, idDept=[], idPrescription=None, limit=250, day=date.today(), onlyStatus=False):
        score = getAggScore()
        scoreOne = getScore(1)
        scoreTwo = getScore(2)
        scoreThree = getHighScore()
        tgo = getExams('TGO')
        tgp = getExams('TGP')
        cr = getExams('CR')
        k = getExams('K')
        na = getExams('NA')
        mg = getExams('MG')
        rni = getExams('PRO')
        pcr = getExams('PCRU')
        antimicro = getDrugClass(DrugAttributes.antimicro)
        mav = getDrugClass(DrugAttributes.mav)
        controlled = getDrugClass(DrugAttributes.controlled)
        notdefault = getDrugClass(DrugAttributes.notdefault)
        sonda = getDrugRoute("%sonda%")
        diff = getDrugDiff()
        count = getDrugsCount()
        interventions = getPendingInterventions()

        if onlyStatus:
            q = db.session.query(Prescription)
        else:
            q = db.session\
                .query(
                    Prescription, Patient, func.trunc(0).label('daysAgo'),
                    score.label('score'), scoreOne.label('scoreOne'), scoreTwo.label('scoreTwo'), scoreThree.label('scoreThree'),
                    tgo.label('tgo'), tgp.label('tgp'), cr.label('cr'), k.label('k'), na.label('na'), mg.label('mg'), rni.label('rni'),
                    antimicro.label('antimicro'), mav.label('mav'), controlled.label('controlled'), sonda.label('sonda'),
                    (count - diff).label('diff'), Department.name.label('department'), notdefault.label('notdefault'),
                    interventions.label('interventions'), pcr.label('pcr')
                )\
                .outerjoin(Patient, Patient.admissionNumber == Prescription.admissionNumber)\
                .outerjoin(Department, Department.id == Prescription.idDepartment)

        if (not(idSegment is None)):
            q = q.filter(Prescription.idSegment == idSegment)

        if (len(idDept)>0):
            q = q.filter(Prescription.idDepartment.in_(idDept))

        if (not(idPrescription is None)):
            q = q.filter(Prescription.id == idPrescription)
        else:
            q = q.filter(func.date(Prescription.date) > day)
            
        q = q.order_by(desc(Prescription.date))

        if onlyStatus:
            wrapper = q
        else:
            q = q.with_labels().subquery()

            prescritionAlias = db.aliased(Prescription, q)
            patientAlias = db.aliased(Patient, q)

            wrapper = db.session\
                .query(prescritionAlias, patientAlias,\
                        '"daysAgo"', 'score', '"scoreOne"', '"scoreTwo"', '"scoreThree"',\
                        'tgo', 'tgp', 'cr', 'k', 'na', 'mg', 'rni',\
                        'antimicro', 'mav', 'controlled', 'sonda', 'diff', 'department',\
                        'notdefault', 'interventions', 'pcr')


        return wrapper.limit(limit).all()


class Outlier(db.Model):
    __tablename__ = 'outlier'

    id = db.Column("idoutlier", db.Integer, primary_key=True)
    idDrug = db.Column("fkmedicamento", db.Integer, nullable=False)
    idSegment = db.Column("idsegmento", db.Integer, nullable=False)
    countNum = db.Column("contagem", db.Integer, nullable=True)
    dose = db.Column("doseconv", db.Float, nullable=True)
    frequency = db.Column("frequenciadia", db.Float, nullable=True)
    score = db.Column("escore", db.Integer, nullable=True)
    manualScore = db.Column("escoremanual", db.Integer, nullable=True)
    update = db.Column("update_at", db.DateTime, nullable=True)
    user = db.Column("update_by", db.Integer, nullable=True)

    def setSchema(schema):
        Outlier.__table__.schema = schema


class OutlierObs(db.Model):
    __tablename__ = 'outlierobs'

    id = db.Column("idoutlier", db.Integer, primary_key=True)
    idSegment = db.Column("idsegmento", db.Integer, nullable=False)
    idDrug = db.Column("fkmedicamento", db.Integer, nullable=False)
    dose = db.Column("doseconv", db.Float, nullable=True)
    frequency = db.Column("frequenciadia", db.Float, nullable=True)
    notes = db.Column('text', db.String, nullable=True)
    update = db.Column("update_at", db.DateTime, nullable=True)
    user = db.Column("update_by", db.Integer, nullable=True)

    def setSchema(schema):
        OutlierObs.__table__.schema = schema

class PrescriptionAgg(db.Model):
    __tablename__ = 'prescricaoagg'

    idHospital = db.Column("fkhospital", db.Integer, nullable=False)
    idDepartment = db.Column("fksetor", db.Integer, primary_key=True)
    idSegment = db.Column("idsegmento", db.Integer, nullable=False)
    idDrug = db.Column("fkmedicamento", db.Integer, primary_key=True)
    idMeasureUnit = db.Column("fkunidademedida", db.Integer, nullable=False)
    idFrequency = db.Column("fkfrequencia", db.String, primary_key=True)
    dose = db.Column("dose", db.Float, primary_key=True)
    doseconv = db.Column("doseconv", db.Float, nullable=True)
    frequency = db.Column("frequenciadia", db.Float, nullable=True)
    countNum = db.Column("contagem", db.Integer, nullable=True)

    def setSchema(schema):
        PrescriptionAgg.__table__.schema = schema

def getDrugHistory(idPrescription, admissionNumber):
    pd1 = db.aliased(PrescriptionDrug)
    pr1 = db.aliased(Prescription)

    query = db.session.query(func.concat(func.to_char(pr1.date, "DD/MM"),' (',pd1.frequency,'x ',pd1.dose,' ',pd1.idMeasureUnit,')'))\
        .select_from(pd1)\
        .join(pr1, pr1.id == pd1.idPrescription)\
        .filter(pr1.admissionNumber == admissionNumber)\
        .filter(pr1.id < idPrescription)\
        .filter(pd1.idDrug == PrescriptionDrug.idDrug)\
        .filter(pr1.date > (date.today() - timedelta(days=30)))\
        .order_by(asc(pr1.date))\
        .as_scalar()

    return func.array(query)

class PrescriptionDrug(db.Model):
    __tablename__ = 'presmed'

    id = db.Column("fkpresmed", db.Integer, primary_key=True)
    idOutlier = db.Column("idoutlier", db.Integer, nullable=False)
    idPrescription = db.Column("fkprescricao", db.Integer, nullable=False)
    idDrug = db.Column("fkmedicamento", db.Integer, nullable=False)
    idMeasureUnit = db.Column("fkunidademedida", db.Integer, nullable=False)
    idFrequency = db.Column("fkfrequencia", db.String, nullable=True)
    idSegment = db.Column("idsegmento", db.Integer, nullable=False)

    dose = db.Column("dose", db.Float, nullable=True)
    frequency = db.Column("frequenciadia", db.Float, nullable=True)
    doseconv = db.Column("doseconv", db.Float, nullable=True)
    route = db.Column('via', db.String, nullable=True)
    notes = db.Column('complemento', db.String, nullable=True)
    interval = db.Column('horario', db.String, nullable=True)
    source = db.Column('origem', db.String, nullable=True)
    default = db.Column('padronizado', db.String(1), nullable=True)

    solutionGroup = db.Column('slagrupamento', db.String(1), nullable=True)
    solutionACM = db.Column('slacm', db.String(1), nullable=True)
    solutionPhase = db.Column('sletapas', db.String(1), nullable=True)
    solutionTime = db.Column('slhorafase', db.Float, nullable=True)
    solutionTotalTime = db.Column('sltempoaplicacao', db.String(1), nullable=True)
    solutionDose = db.Column('sldosagem', db.Float, nullable=True)
    solutionUnit = db.Column('sltipodosagem', db.String(3), nullable=True)

    status = db.Column('status', db.String(1), nullable=False)
    finalscore = db.Column('escorefinal', db.Integer, nullable=True)
    near = db.Column("aprox", db.Boolean, nullable=True)
    suspendedDate = db.Column("dtsuspensao", db.DateTime, nullable=True)
    checked = db.Column("checado", db.Boolean, nullable=True)
    period = db.Column("periodo", db.Integer, nullable=True)
    update = db.Column("update_at", db.DateTime, nullable=True)
    user = db.Column("update_by", db.Integer, nullable=True)

    def setSchema(schema):
        PrescriptionDrug.__table__.schema = schema

    def findByPrescription(idPrescription, admissionNumber):

        return db.session\
            .query(PrescriptionDrug, Drug, MeasureUnit, Frequency, func.trunc(0).label('intervention'), 
                    func.coalesce(func.coalesce(Outlier.manualScore, Outlier.score), 4).label('score'),
                    DrugAttributes)\
            .outerjoin(Outlier, Outlier.id == PrescriptionDrug.idOutlier)\
            .outerjoin(Drug, Drug.id == PrescriptionDrug.idDrug)\
            .outerjoin(MeasureUnit, MeasureUnit.id == PrescriptionDrug.idMeasureUnit)\
            .outerjoin(Frequency, Frequency.id == PrescriptionDrug.idFrequency)\
            .outerjoin(DrugAttributes, and_(DrugAttributes.idDrug == PrescriptionDrug.idDrug, DrugAttributes.idSegment == PrescriptionDrug.idSegment))\
            .filter(PrescriptionDrug.idPrescription == idPrescription)\
            .order_by(asc(PrescriptionDrug.solutionGroup), asc(Drug.name))\
            .all()

    def findByPrescriptionDrug(idPrescriptionDrug):
        pd = PrescriptionDrug.query.get(idPrescriptionDrug)
        p = Prescription.query.get(pd.idPrescription)

        drugHistory = getDrugHistory(p.id, p.admissionNumber)

        return db.session\
            .query(PrescriptionDrug, drugHistory.label('drugHistory'))\
            .filter(PrescriptionDrug.id == idPrescriptionDrug)\
            .all()

class Drug(db.Model):
    __tablename__ = 'medicamento'

    id = db.Column("fkmedicamento", db.Integer, primary_key=True)
    idMeasureUnit = db.Column("fkunidademedida", db.String, nullable=False)
    idHospital = db.Column("fkhospital", db.Integer, nullable=False)
    name = db.Column("nome", db.String, nullable=False)

    def setSchema(schema):
        Drug.__table__.schema = schema

class DrugAttributes(db.Model):
    __tablename__ = 'medatributos'

    idDrug = db.Column("fkmedicamento", db.Integer, primary_key=True)
    idSegment = db.Column("idsegmento", db.Integer, primary_key=True)
    antimicro = db.Column("antimicro", db.Boolean, nullable=True)
    mav = db.Column("mav", db.Boolean, nullable=True)
    controlled = db.Column("controlados", db.Boolean, nullable=True)
    notdefault = db.Column("naopadronizado", db.Boolean, nullable=True)
    maxDose = db.Column("dosemaxima", db.Integer, nullable=True)
    kidney = db.Column("renal", db.Integer, nullable=True)
    liver = db.Column("hepatico", db.Integer, nullable=True)
    elderly = db.Column("idoso", db.Boolean, nullable=True)
    division = db.Column("divisor", db.Integer, nullable=True)
    useWeight = db.Column("usapeso", db.Boolean, nullable=True)

    def setSchema(schema):
        DrugAttributes.__table__.schema = schema

class MeasureUnit(db.Model):
    __tablename__ = 'unidademedida'

    id = db.Column("fkunidademedida", db.String, primary_key=True)
    idHospital = db.Column("fkhospital", db.Integer, nullable=False)
    description = db.Column("nome", db.String, nullable=False)

    def setSchema(schema):
        MeasureUnit.__table__.schema = schema

class MeasureUnitConvert(db.Model):
    __tablename__ = 'unidadeconverte'

    idMeasureUnit = db.Column("fkunidademedida", db.String, primary_key=True)
    idDrug = db.Column("fkmedicamento", db.Integer, primary_key=True)
    idHospital = db.Column("fkhospital", db.Integer, nullable=False)
    factor = db.Column("fator", db.String, nullable=False)

    def setSchema(schema):
        MeasureUnitConvert.__table__.schema = schema

class InterventionReason(db.Model):
    __tablename__ = 'motivointervencao'

    id = db.Column("idmotivointervencao", db.Integer, primary_key=True)
    description = db.Column("nome", db.String, nullable=False)
    mamy = db.Column("idmotivomae", db.Integer, nullable=False)

    def setSchema(schema):
        InterventionReason.__table__.schema = schema

    def findAll():
        im = db.aliased(InterventionReason)

        return db.session.query(InterventionReason, im.description)\
                .outerjoin(im, im.id == InterventionReason.mamy)\
                .order_by(InterventionReason.description)\
                .all()


class Frequency(db.Model):
    __tablename__ = 'frequencia'

    id = db.Column("fkfrequencia", db.String, primary_key=True)
    description = db.Column("nome", db.String, nullable=False)

    def setSchema(schema):
        Frequency.__table__.schema = schema


class Intervention(db.Model):
    __tablename__ = 'intervencao'

    id = db.Column("fkpresmed", db.Integer, primary_key=True)
    admissionNumber = db.Column('nratendimento', db.Integer, nullable=False)
    idInterventionReason = db.Column("idmotivointervencao", db.Integer, nullable=False)
    error = db.Column('erro', db.Boolean, nullable=True)
    cost = db.Column("custo", db.Boolean, nullable=True)
    notes = db.Column("observacao", db.String, nullable=True)
    interactions = db.Column('interacoes', postgresql.ARRAY(db.Integer), nullable=True)
    date = db.Column("dtintervencao", db.DateTime, nullable=True)
    status = db.Column('status', db.String(1), nullable=True)
    update = db.Column("update_at", db.DateTime, nullable=False)
    user = db.Column("update_by", db.Integer, nullable=False)

    def setSchema(schema):
        Intervention.__table__.schema = schema

    def validateIntervention(self):
        if self.idPrescriptionDrug is None:
            raise AssertionError(
                'Medicamento prescrito: preenchimento obrigatório')

        if self.idUser is None:
            raise AssertionError(
                'Usuário responsável: preenchimento obrigatório')

        if self.idInterventionReason is None:
            raise AssertionError(
                'Motivo intervenção: preenchimento obrigatório')

        if self.propagation is None:
            raise AssertionError('Propagação: preenchimento obrigatório')

        if self.propagation != 'S' and self.propagation != 'N':
            raise AssertionError('Propagação: valor deve ser S ou N')

        if self.notes is None:
            raise AssertionError('Observação: preenchimento obrigatório')

        prescriptionDrug = PrescriptionDrug.query.filter(
            PrescriptionDrug.id == self.idPrescriptionDrug).first()
        if (prescriptionDrug is None):
            raise AssertionError(
                'Medicamento prescrito: identificação inexistente')

        interventionReason = InterventionReason.query.filter(
            InterventionReason.id == self.idInterventionReason).first()
        if (interventionReason is None):
            raise AssertionError(
                'Motivo intervenção: identificação inexistente')

    def save(self):
        self.validateIntervention()
        if self.id == None:
            db.session.add(self)

        db.session.commit()

    def findAll(admissionNumber=None,userId=None):
        reason = db.session.query(InterventionReason.description)\
                .select_from(InterventionReason)\
                .filter(InterventionReason.id == func.any(Intervention.idInterventionReason))\
                .as_scalar()

        splitStr = '!?'
        dr1 = db.aliased(Drug)
        interactions = db.session.query(func.concat(dr1.name, splitStr, dr1.id))\
                .select_from(dr1)\
                .filter(dr1.id == func.any(Intervention.interactions))\
                .as_scalar()

        interventions = db.session\
            .query(Intervention, PrescriptionDrug, 
                    func.array(reason).label('reason'), Drug.name, 
                    func.array(interactions).label('interactions'),
                    MeasureUnit, Frequency)\
            .join(PrescriptionDrug, Intervention.id == PrescriptionDrug.id)\
            .outerjoin(Drug, Drug.id == PrescriptionDrug.idDrug)\
            .outerjoin(MeasureUnit, MeasureUnit.id == PrescriptionDrug.idMeasureUnit)\
            .outerjoin(Frequency, Frequency.id == PrescriptionDrug.idFrequency)

        if admissionNumber:
            interventions = interventions.filter(Intervention.admissionNumber == admissionNumber)
        if userId:
            interventions = interventions.filter(Intervention.user == userId)\
                            .filter(Intervention.date > (date.today() - timedelta(days=30)))

        interventions = interventions.filter(Intervention.status.in_(['s','a','n','x']))\
            .order_by(desc(Intervention.date))\
            .all()

        intervBuffer = []
        for i in interventions:
            intervBuffer.append({
                'id': i[0].id,
                'idSegment': i[1].idSegment,
                'idInterventionReason': i[0].idInterventionReason,
                'reasonDescription': (', ').join(i[2]),
                'idPrescription': i[1].idPrescription,
                'idDrug': i[1].idDrug,
                'drugName': i[3] if i[3] is not None else 'Medicamento ' + str(i[1].idDrug),
                'dose': i[1].dose,
                'measureUnit': { 'value': i[5].id, 'label': i[5].description } if i[5] else '',
                'frequency': { 'value': i[6].id, 'label': i[6].description } if i[6] else '',
                'time': timeValue(i[1].interval),
                'route': i[1].route,
                'admissionNumber': i[0].admissionNumber,
                'observation': i[0].notes,
                'error': i[0].error,
                'cost': i[0].cost,
                'interactionsDescription': (', ').join([ d.split(splitStr)[0] for d in i[4] ] ),
                'interactionsList': interactionsList(i[4], splitStr),
                'interactions': i[0].interactions,
                'date': i[0].date.isoformat(),
                'status': i[0].status
            })

        result = [i for i in intervBuffer if i['status'] == 's']
        result.extend([i for i in intervBuffer if i['status'] != 's'])

        return result


class Segment(db.Model):
    __tablename__ = 'segmento'

    id = db.Column("idsegmento", db.Integer, primary_key=True)
    description = db.Column("nome", db.String, nullable=False)
    minAge = db.Column("idade_min", db.Integer, nullable=False)
    maxAge = db.Column("idade_max", db.Integer, nullable=False)
    minWeight = db.Column("peso_min", db.Float, nullable=False)
    maxWeight = db.Column("peso_max", db.Float, nullable=False)
    status = db.Column("status", db.Integer, nullable=False)

    def setSchema(schema):
        Segment.__table__.schema = schema

    def findAll():
        return db.session\
            .query(Segment)\
            .order_by(asc(Segment.description))\
            .all()


class Department(db.Model):
    __tablename__ = 'setor'

    id = db.Column("fksetor", db.Integer, primary_key=True)
    idHospital = db.Column("fkhospital", db.Integer, nullable=False)
    name = db.Column("nome", db.String, nullable=False)

    def getAll():
        return Department.query.all()

    def setSchema(schema):
        Department.__table__.schema = schema

class SegmentDepartment(db.Model):
    __tablename__ = 'segmentosetor'

    id = db.Column("idsegmento", db.Integer, primary_key=True)
    idHospital = db.Column("fkhospital", db.Integer, primary_key=True)
    idDepartment = db.Column("fksetor", db.Integer, primary_key=True)

    def setSchema(schema):
        SegmentDepartment.__table__.schema = schema

class Exams(db.Model):
    __tablename__ = 'exame'

    idExame = db.Column("fkexame", db.Integer, nullable=False)
    idPatient = db.Column("fkpessoa", db.Integer, primary_key=True)
    date = db.Column("dtexame", db.DateTime, nullable=False)
    typeExam = db.Column("tpexame", db.String, nullable=False)
    value = db.Column("resultado", db.Float, nullable=False)
    unit = db.Column("unidade", db.String, nullable=True)

    def setSchema(schema):
        Exams.__table__.schema = schema

class PrescriptionPic(db.Model):
    __tablename__ = 'prescricaofoto'

    id = db.Column("fkprescricao", db.Integer, primary_key=True)
    picture = db.Column("foto", postgresql.JSON, nullable=False)

    def setSchema(schema):
        PrescriptionPic.__table__.schema = schema