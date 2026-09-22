from __future__ import annotations
from datetime import date,datetime
from decimal import Decimal
from typing import Any
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import delete,or_,select
from sqlalchemy.orm import Session
from app.audit_service import audit
from app.database import get_db
from app.dependencies import get_current_user,require_permission
from app.employee_service import bool_pt,create_employee,date_value,employee_dict,load_employee,registration_alert,update_employee
from app.models_extended import Employee,EmployeeDocumentRecord,EmployeePieceRate,EmployeeProductionEntry,EmployeePayrollStatement,EmployeeAdvance,StoredFile
from app.schemas import CurrentUser
from app.schemas_extended import EmployeeCreate,FrontRhSyncPayload,PayrollPreviewRequest,PieceRateInput,ProductionEntryInput

router=APIRouter(prefix="/employees",tags=["RH / Colaboradores"])

@router.get("",dependencies=[Depends(require_permission("rh.read"))])
def list_employees(q:str|None=None,status:str|None=None,category:str|None=None,db:Session=Depends(get_db)):
    s=select(Employee).order_by(Employee.full_name.asc())
    if q:s=s.where(or_(Employee.full_name.ilike(f"%{q}%"),Employee.cpf.ilike(f"%{q}%"),Employee.legacy_id.ilike(f"%{q}%"),Employee.position.ilike(f"%{q}%"),Employee.sector.ilike(f"%{q}%")))
    if status:s=s.where(Employee.status==status)
    if category:s=s.where(Employee.employment_category==category)
    return [{"id":e.id,"legacy_id":e.legacy_id,"full_name":e.full_name,"cpf":e.cpf,"position":e.position,"sector":e.sector,"status":e.status,"employment_category":e.employment_category,"employee_type":e.employee_type,"collaborator_model":e.collaborator_model,"salary":e.salary,"start_date":e.start_date,"registration_date":e.registration_date,"registration_alert":registration_alert(e)} for e in db.scalars(s).all()]

@router.get("/alerts/registration",dependencies=[Depends(require_permission("rh.read"))])
def alerts(db:Session=Depends(get_db)):
    rows=db.scalars(select(Employee).where(Employee.status=="Ativo",Employee.employment_category=="Sem registro")).all();return [{"employee_id":e.id,"name":e.full_name,**registration_alert(e)} for e in rows]

@router.get("/piece-rates/list",dependencies=[Depends(require_permission("rh.production.read"))])
def piece_rates(employee_id:str|None=None,db:Session=Depends(get_db)):
    s=select(EmployeePieceRate).order_by(EmployeePieceRate.created_at.desc())
    if employee_id:s=s.where(EmployeePieceRate.employee_id==employee_id)
    return [{"id":x.id,"legacy_id":x.legacy_id,"employee_id":x.employee_id,"sector":x.sector,"operation":x.operation,"product_id":x.product_id,"product_name":x.product_name,"rate":x.rate,"valid_from":x.valid_from,"valid_until":x.valid_until,"active":x.active} for x in db.scalars(s).all()]

@router.get("/production-entries/list",dependencies=[Depends(require_permission("rh.production.read"))])
def production_entries(employee_id:str|None=None,competence:str|None=None,db:Session=Depends(get_db)):
    s=select(EmployeeProductionEntry).order_by(EmployeeProductionEntry.entry_date.desc())
    if employee_id:s=s.where(EmployeeProductionEntry.employee_id==employee_id)
    rows=list(db.scalars(s).all())
    if competence:
        try:y,m=[int(x) for x in competence.split("-")];rows=[x for x in rows if x.entry_date.year==y and x.entry_date.month==m]
        except Exception:pass
    return [{"id":x.id,"legacy_id":x.legacy_id,"employee_id":x.employee_id,"production_order_id":x.production_order_id,"production_order_ref":x.production_order_ref,"entry_date":x.entry_date,"sector":x.sector,"operation":x.operation,"product_name":x.product_name,"quantity":x.quantity,"rate":x.rate,"total":x.total,"approved":x.approved} for x in rows]


@router.get("/front/state",dependencies=[Depends(require_permission("rh.read"))])
def front_state(db:Session=Depends(get_db)):
    """Retorna a fonte oficial do RH para reconstruir o front em qualquer computador."""
    employees=[]
    for base in db.scalars(select(Employee).order_by(Employee.full_name.asc())).all():
        full=employee_dict(load_employee(db,base.id),include_health=True)
        documents=[]
        for doc in db.scalars(
            select(EmployeeDocumentRecord)
            .where(EmployeeDocumentRecord.employee_id==base.id)
            .order_by(EmployeeDocumentRecord.created_at.asc())
        ).all():
            documents.append({
                "id":doc.id,
                "legacy_id":doc.legacy_id,
                "document_type":doc.document_type,
                "document_number":doc.document_number,
                "status":doc.status,
                "issue_date":doc.issue_date,
                "expires_at":doc.expires_at,
                "notes":doc.notes,
                "stored_file_id":doc.stored_file_id,
            })
        employees.append({
            "server":full,
            "front_payload":base.front_payload_json or {},
            "documents":documents,
        })

    rates=[{
        "id":x.id,"legacy_id":x.legacy_id,"employee_id":x.employee_id,
        "sector":x.sector,"operation":x.operation,"product_id":x.product_id,
        "product_name":x.product_name,"rate":x.rate,"valid_from":x.valid_from,
        "valid_until":x.valid_until,"active":x.active,
    } for x in db.scalars(select(EmployeePieceRate).order_by(EmployeePieceRate.created_at.asc())).all()]

    entries=[{
        "id":x.id,"legacy_id":x.legacy_id,"employee_id":x.employee_id,
        "production_order_id":x.production_order_id,
        "production_order_ref":x.production_order_ref,"entry_date":x.entry_date,
        "sector":x.sector,"operation":x.operation,"product_name":x.product_name,
        "quantity":x.quantity,"rate":x.rate,"total":x.total,"approved":x.approved,
    } for x in db.scalars(select(EmployeeProductionEntry).order_by(EmployeeProductionEntry.entry_date.asc())).all()]

    return {"employees":employees,"piece_rates":rates,"production_entries":entries}


@router.delete("/by-legacy/{legacy_id}",status_code=204,dependencies=[Depends(require_permission("rh.delete"))])
def remove_by_legacy(legacy_id:str,db:Session=Depends(get_db),user:CurrentUser=Depends(get_current_user)):
    e=db.scalar(select(Employee).where(Employee.legacy_id==legacy_id))
    if not e:raise HTTPException(404,"Colaborador não encontrado.")
    name=e.full_name;server_id=e.id
    db.delete(e)
    audit(db,module="RH",action="EXCLUIR",entity_type="employee",entity_id=server_id,description=name,user_id=user.id,user_name=user.full_name)
    db.commit()
    return None

@router.get("/{employee_id}",dependencies=[Depends(require_permission("rh.read"))])
def get_employee(employee_id:str,db:Session=Depends(get_db)):
    e=load_employee(db,employee_id)
    if not e:raise HTTPException(404,"Colaborador não encontrado.")
    return employee_dict(e,include_health=True)

@router.post("",status_code=201,dependencies=[Depends(require_permission("rh.write"))])
def create(payload:EmployeeCreate,db:Session=Depends(get_db),user:CurrentUser=Depends(get_current_user)):
    if not payload.full_name.strip():raise HTTPException(422,"Nome é obrigatório.")
    e=create_employee(db,payload);audit(db,module="RH",action="CRIAR",entity_type="employee",entity_id=e.id,description=e.full_name,user_id=user.id,user_name=user.full_name);db.commit();return employee_dict(load_employee(db,e.id))

@router.put("/{employee_id}",dependencies=[Depends(require_permission("rh.write"))])
def update(employee_id:str,payload:EmployeeCreate,db:Session=Depends(get_db),user:CurrentUser=Depends(get_current_user)):
    e=load_employee(db,employee_id)
    if not e:raise HTTPException(404,"Colaborador não encontrado.")
    update_employee(db,e,payload);audit(db,module="RH",action="ATUALIZAR",entity_type="employee",entity_id=e.id,description=e.full_name,user_id=user.id,user_name=user.full_name);db.commit();return employee_dict(load_employee(db,e.id))

@router.delete("/{employee_id}",status_code=204,dependencies=[Depends(require_permission("rh.delete"))])
def remove(employee_id:str,db:Session=Depends(get_db),user:CurrentUser=Depends(get_current_user)):
    e=db.get(Employee,employee_id)
    if not e:raise HTTPException(404,"Colaborador não encontrado.")
    name=e.full_name;db.delete(e);audit(db,module="RH",action="EXCLUIR",entity_type="employee",entity_id=employee_id,description=name,user_id=user.id,user_name=user.full_name);db.commit();return None

@router.post("/piece-rates",dependencies=[Depends(require_permission("rh.production.write"))])
def add_piece_rate(payload:PieceRateInput,db:Session=Depends(get_db)):
    if not db.get(Employee,payload.employee_id):raise HTTPException(404,"Colaborador não encontrado.")
    x=EmployeePieceRate(**payload.model_dump());db.add(x);db.commit();db.refresh(x);return {"id":x.id,"employee_id":x.employee_id,"rate":x.rate}

@router.post("/production-entries",dependencies=[Depends(require_permission("rh.production.write"))])
def add_production(payload:ProductionEntryInput,db:Session=Depends(get_db)):
    if not db.get(Employee,payload.employee_id):raise HTTPException(404,"Colaborador não encontrado.")
    rate=payload.rate
    if rate is None:
        r=db.scalar(select(EmployeePieceRate).where(EmployeePieceRate.employee_id==payload.employee_id,EmployeePieceRate.sector==payload.sector,EmployeePieceRate.operation==payload.operation,EmployeePieceRate.product_name==payload.product_name,EmployeePieceRate.active.is_(True)).order_by(EmployeePieceRate.valid_from.desc()))
        rate=r.rate if r else Decimal("0")
    x=EmployeeProductionEntry(legacy_id=payload.legacy_id or f"PROD-{datetime.now().timestamp()}",employee_id=payload.employee_id,production_order_id=payload.production_order_id,production_order_ref=payload.production_order_ref,entry_date=payload.entry_date,sector=payload.sector,operation=payload.operation,product_name=payload.product_name,quantity=payload.quantity,rate=rate,total=Decimal(str(payload.quantity))*Decimal(str(rate or 0)),approved=payload.approved);db.add(x);db.commit();db.refresh(x);return {"id":x.id,"employee_id":x.employee_id,"quantity":x.quantity,"rate":x.rate,"total":x.total}

@router.post("/{employee_id}/payroll/preview",dependencies=[Depends(require_permission("rh.payroll"))])
def payroll_preview(employee_id:str,payload:PayrollPreviewRequest,db:Session=Depends(get_db)):
    e=load_employee(db,employee_id)
    if not e:raise HTTPException(404,"Colaborador não encontrado.")
    try:y,m=[int(x) for x in payload.competence.split("-")]
    except Exception:raise HTTPException(422,"Competência deve usar AAAA-MM.")
    entries=db.scalars(select(EmployeeProductionEntry).where(EmployeeProductionEntry.employee_id==employee_id)).all();piece=sum((Decimal(str(x.total or 0)) for x in entries if x.entry_date.year==y and x.entry_date.month==m),Decimal("0"));rec=sum((Decimal(str(x.amount or 0)) for x in e.bonuses if x.recurring and x.active),Decimal("0"));one=sum((Decimal(str(x.amount or 0)) for x in e.bonuses if x.active and not x.recurring and x.competence in {payload.competence,f"{m:02d}/{y}"}),Decimal("0"));bonus=Decimal(str(e.fixed_bonus or 0))+Decimal(str(e.variable_bonus or 0))+rec+one;adv=sum((Decimal(str(x.amount or 0)) for x in db.scalars(select(EmployeeAdvance).where(EmployeeAdvance.employee_id==employee_id,EmployeeAdvance.competence==payload.competence)).all()),Decimal("0"));base=Decimal(str(e.salary or 0));gross=base+bonus+piece+Decimal(str(payload.other_additions));net=gross-Decimal(str(payload.transport_discount))-adv-Decimal(str(payload.other_discounts));return {"employee_id":e.id,"employee_name":e.full_name,"competence":payload.competence,"base_salary":base,"bonuses":bonus,"piece_production":piece,"transport_discount":payload.transport_discount,"advances":adv,"other_additions":payload.other_additions,"other_discounts":payload.other_discounts,"gross":gross,"net":net,"note":"Prévia administrativa. Encargos legais devem seguir as regras vigentes configuradas pela contabilidade."}

@router.post("/{employee_id}/payroll/close",dependencies=[Depends(require_permission("rh.payroll"))])
def payroll_close(employee_id:str,payload:PayrollPreviewRequest,db:Session=Depends(get_db)):
    p=payroll_preview(employee_id,payload,db);x=db.scalar(select(EmployeePayrollStatement).where(EmployeePayrollStatement.employee_id==employee_id,EmployeePayrollStatement.competence==payload.competence))
    if x is None:x=EmployeePayrollStatement(employee_id=employee_id,competence=payload.competence);db.add(x)
    x.base_salary=p["base_salary"];x.bonuses=p["bonuses"];x.piece_production=p["piece_production"];x.transport=p["transport_discount"];x.advances=p["advances"];x.other_additions=p["other_additions"];x.other_discounts=p["other_discounts"];x.gross=p["gross"];x.net=p["net"];x.status="Fechado";db.commit();return {**p,"id":x.id,"status":"Fechado"}

def front_payload(raw:dict[str,Any])->EmployeeCreate:
    personal=raw.get("personal") or {};docs=raw.get("documentsPersonal") or {};business=raw.get("business") or {};a=raw.get("addressData") or {};h=raw.get("health") or {};bank=raw.get("bank") or {};t=raw.get("transport") or {}
    contacts=[{"contact_type":"Emergência","name":c.get("name","") ,"relationship":c.get("relationship","") ,"phone":c.get("phone","") ,"priority":i+1} for i,c in enumerate(raw.get("emergency") or [])]
    deps=[]
    for d in raw.get("dependents") or []:
        al=None
        if d.get("hasAlimony") or d.get("alimonyType"):al={"active":True,"agreement_type":d.get("alimonyType","") ,"calculation_type":d.get("alimonyCalculationType") or "Valor fixo","fixed_amount":d.get("alimonyValue") or d.get("alimonyAmount") or 0,"percentage":d.get("alimonyPercent") or 0,"beneficiary":d.get("beneficiary") or ""}
        deps.append({"legacy_id":d.get("id","") ,"name":d.get("name","") ,"birth_date":date_value(d.get("birthDate")),"cpf":d.get("cpf","") ,"relationship":d.get("relationship","Filho(a)"),"ir_dependent":bool_pt(d.get("irDependent")),"alimony":al})
    bonuses=[{"legacy_id":b.get("id","") ,"bonus_type":b.get("type","") ,"description":b.get("description","") ,"amount":b.get("value",0),"competence":b.get("competence","") ,"recurring":bool(b.get("recurring")),"active":True} for b in raw.get("bonuses") or []]
    legs=[{"transport_type":x.get("type") or x.get("transportType") or "Ônibus","line":x.get("line","") ,"origin":x.get("origin","") ,"destination":x.get("destination","") ,"fare":x.get("fare",0),"uses_per_day":x.get("uses") or x.get("usesPerDay") or 0} for x in t.get("legs") or []]
    return EmployeeCreate(legacy_id=str(raw.get("id") or ""),full_name=str(raw.get("name") or "Colaborador"),social_name=personal.get("socialName","") ,collaborator_model=raw.get("collaboratorModel","Pessoa física"),employment_category=raw.get("employmentCategory","Registrado"),employee_type=raw.get("type","Operacional"),status=raw.get("status","Ativo"),birth_date=date_value(raw.get("birthDate")),sex=personal.get("sex","") ,marital_status=personal.get("maritalStatus","") ,nationality=personal.get("nationality","") ,naturality=personal.get("naturality","") ,mother_name=personal.get("motherName","") ,father_name=personal.get("fatherName","") ,cpf=raw.get("cpf","") ,rg=raw.get("rg","") ,rg_issuer=docs.get("rgIssuer","") ,rg_issue_date=date_value(docs.get("rgIssueDate")),voter_title=docs.get("voterTitle","") ,voter_zone=docs.get("voterZone","") ,voter_section=docs.get("voterSection","") ,pis=docs.get("pis","") ,ctps=docs.get("ctps","") ,cnh=docs.get("cnh","") ,cnh_category=docs.get("cnhCategory","") ,cnh_validity=date_value(docs.get("cnhValidity")),email=raw.get("email","") ,phone_primary=raw.get("phonePrimary") or raw.get("phone") or "",phone_secondary=raw.get("phoneSecondary","") ,photo_url=raw.get("photo","") ,position=raw.get("position","") ,sector=raw.get("sector","") ,work_schedule=raw.get("workSchedule","") ,scale=raw.get("scale","") ,start_date=date_value(raw.get("startDate")),registration_date=date_value(raw.get("registrationDate")),admission_date=date_value(raw.get("admission")),salary=raw.get("salary",0),fixed_bonus=raw.get("fixedBonus",0),variable_bonus=raw.get("variableBonus",0),advance_percent=raw.get("advancePercent",0),benefits=raw.get("benefits") or [],address={"cep":a.get("cep","") ,"street":a.get("street","") ,"number":a.get("number","") ,"complement":a.get("complement","") ,"neighborhood":a.get("neighborhood","") ,"city":a.get("city","") ,"state":a.get("state","") ,"residence_type":a.get("residenceType","Casa"),"house_unit":a.get("houseUnit","") ,"apartment":a.get("apartment","") ,"block":a.get("block","") ,"floor":a.get("floor","") ,"condominium":a.get("condominium","")},contacts=contacts,health={"blood_type":h.get("bloodType","") ,"has_disease":bool_pt(h.get("hasDisease")),"conditions":h.get("conditions","") ,"under_treatment":bool_pt(h.get("underTreatment")),"treatment":h.get("treatment","") ,"continuous_medication":bool_pt(h.get("continuousMedication")),"medication":h.get("medication","") ,"dosage":h.get("dosage","") ,"medication_schedule":h.get("medicationSchedule","") ,"allergies":h.get("allergies","") ,"drug_allergies":h.get("drugAllergies","") ,"restrictions":h.get("restrictions","") ,"special_need":h.get("specialNeed","") ,"health_plan":h.get("healthPlan","") ,"doctor":h.get("doctor","") ,"can_provide_medication":bool_pt(h.get("canProvideMedication")),"authorized_medication":h.get("authorizedMedication","") ,"emergency_notes":h.get("emergencyNotes","")},mei={"cnpj":business.get("cnpj","") ,"legal_name":business.get("legalName","") ,"trade_name":business.get("tradeName","") ,"municipal_registration":business.get("municipalRegistration","")},dependents=deps,bank_accounts=[{"bank":bank.get("bank","") ,"bank_code":bank.get("bankCode","") ,"agency":bank.get("agency","") ,"account":bank.get("account","") ,"account_digit":bank.get("accountDigit","") ,"account_type":bank.get("accountType","Conta corrente"),"holder":bank.get("holder","") ,"holder_document":bank.get("holderCpf","") ,"pix_type":bank.get("pixType","") ,"pix_key":bank.get("pixKey","") ,"pix_institution":bank.get("pixInstitution","") ,"portability":bool(bank.get("portability")),"origin_bank":bank.get("originBank","") ,"destination_bank":bank.get("destinationBank","") ,"receiving_bank":bank.get("receivingBank","") ,"salary_payment":bank.get("salaryPayment","Crédito em conta"),"is_primary":True}] if any(bank.values()) else [],bonuses=bonuses,transport_plan={"company_address":t.get("companyAddress","") ,"employee_address":t.get("employeeAddress","") ,"provider":t.get("provider","") ,"distance_km":t.get("distance",0),"duration_minutes":int(float(t.get("time") or 0)),"round_trip_distance_km":t.get("roundTripDistance",0),"round_trip_duration_minutes":int(float(t.get("roundTripTime") or 0)),"working_days":int(float(t.get("days") or 0)),"reviewed":bool(t.get("reviewed")),"route_data":t.get("routeData") or {},"legs":legs} if t else None)

@router.put("/sync/front",dependencies=[Depends(require_permission("rh.write"))])
def sync_front(payload:FrontRhSyncPayload,db:Session=Depends(get_db)):
    legacy_map={}
    for raw in payload.employees:
        p=front_payload(raw);e=db.scalar(select(Employee).where(Employee.legacy_id==p.legacy_id))
        if e is None:e=create_employee(db,p)
        else:update_employee(db,e,p)
        e.front_payload_json=raw
        legacy_map[p.legacy_id]=e.id

        # Sincroniza metadados de documentos sem duplicar anexos que já foram
        # enviados para /files/employee-document.
        incoming_document_ids:set[str]=set()
        for doc in raw.get("documents") or []:
            legacy_doc_id=str(doc.get("id") or "")
            server_doc_id=str(doc.get("_serverDocumentId") or "")
            stored_file_id=str(doc.get("storedFileId") or doc.get("_serverFileId") or "")
            record=None
            if server_doc_id:
                record=db.get(EmployeeDocumentRecord,server_doc_id)
                if record is not None and record.employee_id!=e.id:record=None
            if record is None and stored_file_id:
                record=db.scalar(select(EmployeeDocumentRecord).where(EmployeeDocumentRecord.employee_id==e.id,EmployeeDocumentRecord.stored_file_id==stored_file_id))
            if record is None and legacy_doc_id:
                record=db.scalar(select(EmployeeDocumentRecord).where(EmployeeDocumentRecord.employee_id==e.id,EmployeeDocumentRecord.legacy_id==legacy_doc_id))
            if record is None:
                record=EmployeeDocumentRecord(employee_id=e.id)
                db.add(record);db.flush()
            record.legacy_id=legacy_doc_id
            record.document_type=doc.get("type") or doc.get("documentType") or "Outro"
            record.document_number=doc.get("number","")
            record.status=doc.get("status","Recebido")
            record.issue_date=date_value(doc.get("issueDate") or doc.get("receivedDate"))
            record.expires_at=date_value(doc.get("expiry") or doc.get("expiresAt") or doc.get("expiryDate"))
            record.notes=doc.get("notes","")
            if stored_file_id and db.get(StoredFile,stored_file_id):record.stored_file_id=stored_file_id
            incoming_document_ids.add(record.id)

        # Remove apenas metadados sem arquivo que o usuário realmente excluiu.
        # Registros com anexo persistente são removidos pelo endpoint /files.
        for old_doc in db.scalars(select(EmployeeDocumentRecord).where(EmployeeDocumentRecord.employee_id==e.id,EmployeeDocumentRecord.stored_file_id.is_(None))).all():
            if old_doc.id not in incoming_document_ids:db.delete(old_doc)
    db.execute(delete(EmployeePieceRate).where(EmployeePieceRate.legacy_id!=""))
    for raw in payload.piece_rates:
        e=db.scalar(select(Employee).where(Employee.legacy_id==str(raw.get("employeeId") or "")))
        if not e:continue
        db.add(EmployeePieceRate(legacy_id=str(raw.get("id") or ""),employee_id=e.id,sector=raw.get("sector","") ,operation=raw.get("operation","") ,product_name=raw.get("product","") ,rate=Decimal(str(raw.get("rate") or 0)),valid_from=date_value(raw.get("validFrom")),active=True))
    for raw in payload.production_entries:
        legacy=str(raw.get("id") or "")
        if not legacy:continue
        e=db.scalar(select(Employee).where(Employee.legacy_id==str(raw.get("employeeId") or "")))
        if not e:continue
        x=db.scalar(select(EmployeeProductionEntry).where(EmployeeProductionEntry.legacy_id==legacy))
        if x is None:x=EmployeeProductionEntry(legacy_id=legacy,employee_id=e.id,entry_date=date_value(raw.get("date")) or date.today());db.add(x)
        x.employee_id=e.id;x.entry_date=date_value(raw.get("date")) or date.today();x.sector=raw.get("sector","") ;x.operation=raw.get("operation","") ;x.product_name=raw.get("product","") ;x.quantity=Decimal(str(raw.get("quantity") or 0));x.rate=Decimal(str(raw.get("rate") or 0));x.total=Decimal(str(raw.get("total") or (x.quantity*x.rate)));x.production_order_ref=raw.get("productionOrder","")
    db.commit();return {"status":"ok","employees":len(payload.employees),"piece_rates":len(payload.piece_rates),"production_entries":len(payload.production_entries),"legacy_map":legacy_map}
