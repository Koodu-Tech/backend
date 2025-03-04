from .main import *
from .appendix import *
from .segment import *
from routes.utils import *
from datetime import datetime
from sqlalchemy.orm import deferred
from sqlalchemy import case, BigInteger, cast, between

class Prescription(db.Model):
    __tablename__ = 'prescricao'

    id = db.Column("fkprescricao", db.Integer, primary_key=True)
    idPatient = db.Column("fkpessoa", db.Integer, nullable=False)
    admissionNumber = db.Column('nratendimento', db.Integer, nullable=True)
    idHospital = db.Column("fkhospital", db.Integer, nullable=False)
    idDepartment = db.Column("fksetor", db.Integer, nullable=False)
    idSegment = db.Column("idsegmento", db.Integer, nullable=False)
    date = db.Column("dtprescricao", db.DateTime, nullable=False)
    expire = db.Column("dtvigencia", db.DateTime, nullable=True)
    status = db.Column('status', db.String(1), nullable=False)
    bed = db.Column('leito', db.String(16), nullable=True)
    record = db.Column('prontuario', db.Integer, nullable=True)
    features = db.Column('indicadores', postgresql.JSON, nullable=True)
    notes = deferred(db.Column('evolucao', db.String, nullable=True))
    notes_at = db.Column('evolucao_at', db.DateTime, nullable=True)
    prescriber = db.Column('prescritor', db.String, nullable=True)
    agg = db.Column('agregada', db.Boolean, nullable=True)
    aggDeps = deferred(db.Column('aggsetor', postgresql.ARRAY(db.Integer), nullable=True))
    aggDrugs = deferred(db.Column('aggmedicamento', postgresql.ARRAY(db.Integer), nullable=True))
    concilia = db.Column('concilia', db.String(1), nullable=True)
    update = db.Column("update_at", db.DateTime, nullable=True)
    user = db.Column("update_by", db.Integer, nullable=True)

    def getFuturePrescription(idPrescription, admissionNumber):
        return db.session.query(Prescription)\
            .filter(Prescription.admissionNumber == admissionNumber)\
            .filter(Prescription.id > idPrescription)\
            .first()

    def lastDeptbyAdmission(idPrescription, admissionNumber):
        return db.session.query(Department.name)\
            .select_from(Prescription)\
            .outerjoin(Department, and_(Department.id == Prescription.idDepartment, Department.idHospital == Prescription.idHospital))\
            .filter(Prescription.admissionNumber == admissionNumber)\
            .filter(Prescription.id < idPrescription)\
            .order_by(desc(Prescription.id))\
            .first()

    def getPrescriptionBasic():
            return db.session\
            .query(
                Prescription, Patient, '0', '0',
                Department.name.label('department'), Segment.description, 
                Patient.observation, Prescription.notes, Patient.alert,
                Prescription.prescriber
            )\
            .outerjoin(Patient, Patient.admissionNumber == Prescription.admissionNumber)\
            .outerjoin(Department, and_(Department.id == Prescription.idDepartment, Department.idHospital == Prescription.idHospital))\
            .outerjoin(Segment, Segment.id == Prescription.idSegment)

    def getPrescription(idPrescription):
        return Prescription.getPrescriptionBasic()\
            .filter(Prescription.id == idPrescription)\
            .first()

    def getPrescriptionAgg(admissionNumber, aggDate):
        return Prescription.getPrescriptionBasic()\
            .filter(Prescription.admissionNumber == admissionNumber)\
            .filter(func.date(Prescription.date) == aggDate)\
            .order_by(asc(Prescription.date))\
            .first()

    def shouldUpdate(idPrescription):
        return db.session\
            .query(DrugAttributes.update)\
            .select_from(PrescriptionDrug)\
            .join(DrugAttributes, and_(DrugAttributes.idDrug == PrescriptionDrug.idDrug, DrugAttributes.idSegment == PrescriptionDrug.idSegment))\
            .join(Outlier, Outlier.id == PrescriptionDrug.idOutlier)\
            .filter(PrescriptionDrug.idPrescription == idPrescription)\
            .filter(or_(
                        DrugAttributes.update > (datetime.today() - timedelta(minutes=3)),
                        Outlier.update > (datetime.today() - timedelta(minutes=3))
                    ))\
            .all()

    def getHeaders(admissionNumber, aggDate):
        prescriptions = db.session.query(Prescription, Department.name)\
                    .outerjoin(Department, and_(Department.id == Prescription.idDepartment, Department.idHospital == Prescription.idHospital))\
                    .filter(Prescription.admissionNumber == admissionNumber)\
                    .filter(between(aggDate, func.date(Prescription.date), func.date(Prescription.expire)))\
                    .filter(Prescription.agg == None)\
                    .filter(Prescription.concilia == None)\
                    .filter(Prescription.idSegment != None)\
                    .all()
        headers = {}
        for p in prescriptions:
            headers[p[0].id] = {
                'date': p[0].date.isoformat() if p[0].date else None,
                'expire': p[0].expire.isoformat() if p[0].expire else None,
                'status': p[0].status,
                'bed': p[0].bed,
                'prescriber': p[0].prescriber,
                'idDepartment': p[0].idDepartment,
                'department': p[1],
                'drugs': {},
                'procedures': {},
                'solutions': {}
            }

        return headers

    def findRelation(idPrescription, admissionNumber, aggDate=None):
        pd1 = db.aliased(PrescriptionDrug)
        pd2 = db.aliased(PrescriptionDrug)
        m1 = db.aliased(Drug)
        m2 = db.aliased(Drug)
        p1 = db.aliased(Prescription)
        p2 = db.aliased(Prescription)

        if aggDate is None:
            relation = db.session.query(pd1.id, Relation, m1.name, m2.name, pd1.update)
            relation = relation\
                .join(pd2, and_(pd2.idPrescription == pd1.idPrescription, pd2.id != pd1.id))\
                .join(m1, m1.id == pd1.idDrug)\
                .join(m2, m2.id == pd2.idDrug)\
                .join(Relation, and_(Relation.sctida == m1.sctid, Relation.sctidb == m2.sctid))\
                .filter(pd1.idPrescription == idPrescription)
        else:
            relation = db.session.query(pd1.id, Relation, m1.name, m2.name, p1.expire)\
                    .select_from(p1)\
                    .join(p2, p2.admissionNumber == admissionNumber)\
                    .join(pd1, pd1.idPrescription == p1.id)\
                    .join(pd2, and_(pd2.idPrescription == p2.id, pd2.id != pd1.id))\
                    .join(m1, m1.id == pd1.idDrug)\
                    .join(m2, m2.id == pd2.idDrug)\
                    .join(Relation, and_(Relation.sctida == m1.sctid, Relation.sctidb == m2.sctid))\
                    .filter(p1.admissionNumber == admissionNumber)\
                    .filter(between(aggDate, func.date(p1.date), func.date(p1.expire)))\
                    .filter(between(aggDate, func.date(p2.date), func.date(p2.expire)))\
                    .filter(func.date(p2.expire) == func.date(p1.expire))\
                    .filter(p1.idSegment != None)

        relation = relation.filter(Relation.active == True)

        interaction = relation.filter(Relation.kind.in_(['it','dt','dm']))

        incompatible = relation.filter(Relation.kind.in_(['iy']))\
                        .filter(pd1.tube == True)\
                        .filter(pd2.tube == True)

        admissionAllergy = db.session.query(PrescriptionDrug.idDrug.label('idDrug'), func.min(PrescriptionDrug.id).label('id') )\
                      .select_from(PrescriptionDrug)\
                      .join(Prescription, Prescription.id == PrescriptionDrug.idPrescription)\
                      .filter(Prescription.admissionNumber == admissionNumber)\
                      .filter(PrescriptionDrug.allergy == 'S')\
                      .group_by(PrescriptionDrug.idDrug)\
                      .subquery()

        al = db.aliased(admissionAllergy)

        xreactivity = db.session\
            .query(pd1.id, Relation, m1.name, m2.name, pd1.update)\
            .join(al, al.c.id != pd1.id)\
            .join(m1, m1.id == pd1.idDrug)\
            .join(m2, m2.id == al.c.idDrug)\
            .join(Relation, or_(
                                and_(Relation.sctida == m1.sctid, Relation.sctidb == m2.sctid),
                                and_(Relation.sctida == m2.sctid, Relation.sctidb == m1.sctid),
                            ))\
            .filter(Relation.active == True)\
            .filter(Relation.kind.in_(['rx']))

        if aggDate is None:
            xreactivity = xreactivity.filter(pd1.idPrescription == idPrescription)
        else:
            xreactivity = xreactivity.join(Prescription, Prescription.id == pd1.idPrescription)\
                               .filter(Prescription.admissionNumber == admissionNumber)\
                               .filter(between(aggDate, func.date(Prescription.date), func.date(Prescription.expire)))\
                               .filter(Prescription.idSegment != None)

        relations = interaction.union(incompatible).union(xreactivity).all()

        results = {}
        pairs = []
        for r in relations:
            if aggDate is None:
                key = str(r[1].sctida) + '-' + str(r[1].sctidb)
            else:
                key = str(r[1].sctida) + '-' + str(r[1].sctidb) + str(r[4].day if r[4] else 0)

            if key in pairs: 
                continue;

            alert = typeRelations[r[1].kind] + ': '
            alert += strNone(r[1].text) + ' (' + strNone(r[2]) + ' e ' + strNone(r[3]) + ')'

            if r[0] in results: 
                results[r[0]].append(alert)
            else:
                results[r[0]] = [alert]

            pairs.append(key)

        return results

    def checkPrescriptions(admissionNumber, aggDate, userId):
        exists = db.session.query(Prescription)\
                    .filter(Prescription.admissionNumber == admissionNumber)\
                    .filter(Prescription.status != 's')\
                    .filter(Prescription.idSegment != None)\
                    .filter(Prescription.concilia == None)\
                    .filter(Prescription.agg == None)\
                    .filter(between(func.date(aggDate), func.date(Prescription.date), func.date(Prescription.expire)))\
                    .count()

        db.session.query(Prescription)\
                    .filter(Prescription.admissionNumber == admissionNumber)\
                    .filter(Prescription.agg != None)\
                    .filter(func.date(Prescription.date) == func.date(aggDate))\
                    .update({
                        'status': 's' if exists == 0 else '0',
                        'update': datetime.today(),
                        'user': userId
                    }, synchronize_session='fetch')        

def getDrugList():
    query = db.session.query(cast(PrescriptionDrug.idDrug,db.Integer))\
        .select_from(PrescriptionDrug)\
        .filter(PrescriptionDrug.idPrescription == Prescription.id)\
        .as_scalar()

    return func.array(query)

class Patient(db.Model):
    __tablename__ = 'pessoa'

    idPatient = db.Column("fkpessoa", db.Integer, nullable=False)
    idHospital = db.Column("fkhospital", db.Integer, nullable=False)
    admissionNumber = db.Column('nratendimento', db.Integer, primary_key=True)
    admissionDate = db.Column('dtinternacao', db.DateTime, nullable=True)
    birthdate = db.Column('dtnascimento', db.DateTime, nullable=True)
    gender = db.Column('sexo', db.String(1), nullable=True)
    weight = db.Column('peso', db.Float, nullable=True)
    height = db.Column('altura', db.Float, nullable=True)
    weightDate = db.Column('dtpeso', db.DateTime, nullable=True)
    observation = deferred(db.Column('anotacao', db.String, nullable=True))
    skinColor = db.Column('cor', db.String, nullable=True)
    update = db.Column("update_at", db.DateTime, nullable=True)
    user = db.Column("update_by", db.Integer, nullable=True)
    alert = deferred(db.Column('alertatexto', db.String, nullable=True))
    alertDate = db.Column("alertadata", db.DateTime, nullable=True)
    alertExpire = db.Column("alertavigencia", db.DateTime, nullable=True)
    alertBy = db.Column("alerta_by", db.Integer, nullable=True)
    dischargeReason = db.Column('motivoalta', db.String, nullable=True)
    dischargeDate = db.Column("dtalta", db.DateTime, nullable=True)

    def findByAdmission(admissionNumber):
        return db.session.query(Patient)\
                         .filter(Patient.admissionNumber == admissionNumber)\
                         .first()

    def getPatients(idSegment=None, idDept=[], idDrug=[], startDate=date.today(), endDate=None, pending=False, agg=False, currentDepartment=False, concilia=False):
        q = db.session\
            .query(Prescription, Patient, Department.name.label('department'))\
            .outerjoin(Patient, Patient.admissionNumber == Prescription.admissionNumber)\
            .outerjoin(Department, and_(Department.id == Prescription.idDepartment, Department.idHospital == Prescription.idHospital))

        if (not(idSegment is None)):
            q = q.filter(Prescription.idSegment == idSegment)

        if (len(idDept)>0):
            idDept = list(map(int, idDept))
            if bool(int(none2zero(currentDepartment))):
                q = q.filter(Prescription.idDepartment.in_(idDept))
            else:
                q = q.filter(postgresql.array(idDept).overlap(Prescription.aggDeps))

        if (len(idDrug)>0):
            idDrug = list(map(int, idDrug))
            q = q.filter(cast(idDrug, postgresql.ARRAY(BigInteger)).overlap(Prescription.aggDrugs))

        if bool(int(none2zero(pending))):
            q = q.filter(Prescription.status == '0')

        if bool(int(none2zero(agg))):
            q = q.filter(Prescription.agg == True)
        else:
            q = q.filter(Prescription.agg == None)

        if bool(int(none2zero(concilia))):
            q = q.filter(Prescription.concilia != None)
        else:
            q = q.filter(Prescription.concilia == None)

        if endDate is None: endDate = startDate

        q = q.filter(Prescription.date >= validate(startDate))
        q = q.filter(Prescription.date <= (validate(endDate) + timedelta(hours=23,minutes=59)))

        q = q.order_by(desc(Prescription.date))

        return q.limit(500).all()

def getDrugHistory(idPrescription, admissionNumber):
    pd1 = db.aliased(PrescriptionDrug)
    pr1 = db.aliased(Prescription)

    query = db.session.query(func.concat(func.to_char(pr1.date, "DD/MM"),' (',pd1.frequency,'x ',func.trim(func.to_char(pd1.dose,'9G999G999D99')),' ',pd1.idMeasureUnit,')'))\
        .select_from(pd1)\
        .join(pr1, pr1.id == pd1.idPrescription)\
        .filter(pr1.admissionNumber == admissionNumber)\
        .filter(pr1.id < idPrescription)\
        .filter(pd1.idDrug == PrescriptionDrug.idDrug)\
        .filter(pd1.suspendedDate == None)\
        .filter(pr1.date > (date.today() - timedelta(days=30)))\
        .order_by(asc(pr1.date))\
        .as_scalar()

    return func.array(query)

def getDrugFuture(idPrescription, admissionNumber):
    pd1 = db.aliased(PrescriptionDrug)
    pr1 = db.aliased(Prescription)

    query = db.session.query(func.concat(pr1.id,' = ',func.to_char(pr1.date, "DD/MM"),' (',pd1.frequency,'x ',pd1.dose,' ',pd1.idMeasureUnit,') via ',pd1.route,'; '))\
        .select_from(pd1)\
        .join(pr1, pr1.id == pd1.idPrescription)\
        .filter(pr1.admissionNumber == admissionNumber)\
        .filter(pr1.id > idPrescription)\
        .filter(pd1.idDrug == PrescriptionDrug.idDrug)\
        .filter(pd1.suspendedDate == None)\
        .order_by(asc(pr1.date))\
        .as_scalar()

    return func.array(query)

def getPrevNotes(admissionNumber):
    prevNotes = db.aliased(Notes)

    return db.session.query(prevNotes.notes)\
            .select_from(prevNotes)\
            .filter(prevNotes.admissionNumber == admissionNumber)\
            .filter(prevNotes.idDrug == PrescriptionDrug.idDrug)\
            .filter(prevNotes.idPrescriptionDrug < PrescriptionDrug.id)\
            .order_by(desc(prevNotes.update))\
            .limit(1)\
            .as_scalar()

class PrescriptionDrug(db.Model):
    __tablename__ = 'presmed'

    id = db.Column("fkpresmed", db.Integer, primary_key=True)
    idOutlier = db.Column("idoutlier", db.Integer, nullable=False)
    idPrescription = db.Column("fkprescricao", db.Integer, nullable=False)
    idDrug = db.Column("fkmedicamento", db.Integer, nullable=False)
    idMeasureUnit = db.Column("fkunidademedida", db.String, nullable=False)
    idFrequency = db.Column("fkfrequencia", db.String, nullable=True)
    idSegment = db.Column("idsegmento", db.Integer, nullable=False)

    dose = db.Column("dose", db.Float, nullable=True)
    frequency = db.Column("frequenciadia", db.Float, nullable=True)
    doseconv = db.Column("doseconv", db.Float, nullable=True)
    route = db.Column('via', db.String, nullable=True)
    tube = db.Column('sonda', db.Boolean, nullable=True)
    notes = db.Column('complemento', db.String, nullable=True)
    interval = db.Column('horario', db.String, nullable=True)
    source = db.Column('origem', db.String, nullable=True)
    allergy = db.Column('alergia', db.String(1), nullable=True)

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

    def findByPrescription(idPrescription, admissionNumber, aggDate=None):
        prevNotes = getPrevNotes(admissionNumber)

        q = db.session\
            .query(PrescriptionDrug, Drug, MeasureUnit, Frequency, '0',\
                    func.coalesce(func.coalesce(Outlier.manualScore, Outlier.score), 4).label('score'),
                    DrugAttributes, Notes.notes, prevNotes.label('prevNotes'), Prescription.status, Prescription.expire)\
            .outerjoin(Outlier, Outlier.id == PrescriptionDrug.idOutlier)\
            .outerjoin(Drug, Drug.id == PrescriptionDrug.idDrug)\
            .outerjoin(Notes, Notes.idPrescriptionDrug == PrescriptionDrug.id)\
            .outerjoin(Prescription, Prescription.id == PrescriptionDrug.idPrescription)\
            .outerjoin(MeasureUnit, and_(MeasureUnit.id == PrescriptionDrug.idMeasureUnit, MeasureUnit.idHospital == Prescription.idHospital))\
            .outerjoin(Frequency, and_(Frequency.id == PrescriptionDrug.idFrequency, Frequency.idHospital == Prescription.idHospital))\
            .outerjoin(DrugAttributes, and_(DrugAttributes.idDrug == PrescriptionDrug.idDrug, DrugAttributes.idSegment == PrescriptionDrug.idSegment))
        
        if aggDate is None:
            q = q.filter(PrescriptionDrug.idPrescription == idPrescription)
        else:
            q = q.filter(Prescription.admissionNumber == admissionNumber)\
                 .filter(between(aggDate, func.date(Prescription.date), func.date(Prescription.expire)))\
                 .filter(Prescription.agg == None)\
                 .filter(Prescription.concilia == None)\
                 .filter(Prescription.idSegment != None)
        
        return q.order_by(asc(Prescription.expire), desc(func.concat(PrescriptionDrug.idPrescription,PrescriptionDrug.solutionGroup)), asc(Drug.name)).all()

    def findByPrescriptionDrug(idPrescriptionDrug, future):
        pd = PrescriptionDrug.query.get(idPrescriptionDrug)
        if pd is None: return [{1: []}], None
        
        p = Prescription.query.get(pd.idPrescription)

        admissionHistory = None
        if future:
            drugHistory = getDrugFuture(p.id, p.admissionNumber)
            admissionHistory = Prescription.getFuturePrescription(p.id, p.admissionNumber)
        else:
            drugHistory = getDrugHistory(p.id, p.admissionNumber)

        return db.session\
            .query(PrescriptionDrug, drugHistory.label('drugHistory'))\
            .filter(PrescriptionDrug.id == idPrescriptionDrug)\
            .all() , admissionHistory

class Intervention(db.Model):
    __tablename__ = 'intervencao'

    id = db.Column("fkpresmed", db.Integer, primary_key=True)
    idPrescription = db.Column("fkprescricao", db.Integer, primary_key=True)
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

    def findAll(admissionNumber=None,userId=None):
        mReasion = db.aliased(InterventionReason)
        descript = case([(
                            mReasion.description != None,
                            func.concat(mReasion.description, ' - ',InterventionReason.description)
                        ),],
                        else_=InterventionReason.description)

        reason = db.session.query(descript)\
                .select_from(InterventionReason)\
                .outerjoin(mReasion, mReasion.id == InterventionReason.mamy)\
                .filter(InterventionReason.id == func.any(Intervention.idInterventionReason))\
                .as_scalar()

        splitStr = '!?'
        dr1 = db.aliased(Drug)
        interactions = db.session.query(func.concat(dr1.name, splitStr, dr1.id))\
                .select_from(dr1)\
                .filter(dr1.id == func.any(Intervention.interactions))\
                .as_scalar()

        PrescriptionB = db.aliased(Prescription)
        DepartmentB = db.aliased(Department)
        interventions = db.session\
            .query(Intervention, PrescriptionDrug, 
                    func.array(reason).label('reason'), Drug.name, 
                    func.array(interactions).label('interactions'),
                    MeasureUnit, Frequency, Prescription, User.name, 
                    Department.name, PrescriptionB.prescriber, DepartmentB.name)\
            .outerjoin(PrescriptionDrug, Intervention.id == PrescriptionDrug.id)\
            .outerjoin(Prescription, Intervention.idPrescription == Prescription.id)\
            .outerjoin(PrescriptionB, PrescriptionDrug.idPrescription == PrescriptionB.id)\
            .outerjoin(Drug, Drug.id == PrescriptionDrug.idDrug)\
            .outerjoin(MeasureUnit, and_(MeasureUnit.id == PrescriptionDrug.idMeasureUnit, MeasureUnit.idHospital == Prescription.idHospital))\
            .outerjoin(Frequency, and_(Frequency.id == PrescriptionDrug.idFrequency, Frequency.idHospital == Prescription.idHospital))\
            .outerjoin(User, User.id == Intervention.user)\
            .outerjoin(Department, and_(Department.id == PrescriptionB.idDepartment, Department.idHospital == PrescriptionB.idHospital))\
            .outerjoin(DepartmentB, and_(DepartmentB.id == Prescription.idDepartment, DepartmentB.idHospital == Prescription.idHospital))

        if admissionNumber:
            interventions = interventions.filter(Intervention.admissionNumber == admissionNumber)

        interventions = interventions.filter(Intervention.status.in_(['s','a','n','x','j']))\
                                     .order_by(desc(Intervention.date))

        interventions = interventions.limit(1500).all()

        intervBuffer = []
        for i in interventions:
            intervBuffer.append({
                'id': i[0].id,
                'idSegment': i[1].idSegment if i[1] else i[7].idSegment if i[7] else None,
                'idInterventionReason': i[0].idInterventionReason,
                'reasonDescription': (', ').join(i[2]),
                'idPrescription': i[1].idPrescription  if i[1] else i[0].idPrescription,
                'idDrug': i[1].idDrug if i[1] else None,
                'drugName': i[3] if i[3] is not None else 'Medicamento ' + str(i[1].idDrug) if i[1] else 'Intervenção no Paciente',
                'dose': i[1].dose if i[1] else None,
                'measureUnit': { 'value': i[5].id, 'label': i[5].description } if i[5] else '',
                'frequency': { 'value': i[6].id, 'label': i[6].description } if i[6] else '',
                'time': timeValue(i[1].interval) if i[1] else None,
                'route': i[1].route if i[1] else 'None',
                'admissionNumber': i[0].admissionNumber,
                'observation': i[0].notes,
                'error': i[0].error,
                'cost': i[0].cost,
                'interactionsDescription': (', ').join([ d.split(splitStr)[0] for d in i[4] ] ),
                'interactionsList': interactionsList(i[4], splitStr),
                'interactions': i[0].interactions,
                'date': i[0].date.isoformat(),
                'dateTime': i[0].date,
                'user': i[8],
                'department': i[9] if i[9] else i[11],
                'prescriber': i[10] if i[10] else i[7].prescriber if i[7] else None,
                'status': i[0].status
            })

        result = [i for i in intervBuffer if i['status'] == 's']
        result.extend([i for i in intervBuffer if i['status'] != 's'])

        return result