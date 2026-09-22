from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.config import settings
from app.models_extended import Employee, EmployeeAddress, EmployeeContact, EmployeeHealth, EmployeeMEI, EmployeeDependent, EmployeeAlimony, EmployeeBankAccount, EmployeeBonus, EmployeeTransportPlan, EmployeeTransportLeg
from app.schemas_extended import EmployeeCreate


def d(value) -> Decimal:
    return Decimal(str(value or 0))


def date_value(value: Any) -> date | None:
    if not value: return None
    if isinstance(value, date): return value
    try: return date.fromisoformat(str(value)[:10])
    except ValueError: return None


def bool_pt(value: Any) -> bool:
    if isinstance(value, bool): return value
    return str(value or "").strip().lower() in {"sim","true","1","yes","s"}


def load_employee(db: Session, employee_id: str) -> Employee | None:
    return db.scalar(select(Employee).where(Employee.id == employee_id).options(
        selectinload(Employee.address), selectinload(Employee.contacts), selectinload(Employee.health), selectinload(Employee.mei),
        selectinload(Employee.dependents).selectinload(EmployeeDependent.alimony), selectinload(Employee.bank_accounts), selectinload(Employee.bonuses),
        selectinload(Employee.transport_plan).selectinload(EmployeeTransportPlan.legs), selectinload(Employee.piece_rates), selectinload(Employee.production_entries)
    ))


def replace_nested(db: Session, employee: Employee, payload: EmployeeCreate) -> None:
    if payload.address is not None:
        if employee.address is None: employee.address = EmployeeAddress(employee_id=employee.id)
        for k,v in payload.address.model_dump().items(): setattr(employee.address,k,v)
    employee.contacts.clear()
    for x in payload.contacts: employee.contacts.append(EmployeeContact(**x.model_dump()))
    if payload.health is not None:
        if employee.health is None: employee.health = EmployeeHealth(employee_id=employee.id)
        for k,v in payload.health.model_dump().items(): setattr(employee.health,k,v)
    if payload.mei is not None and (payload.collaborator_model.upper()=="MEI" or payload.employment_category.upper()=="MEI" or payload.mei.cnpj):
        if employee.mei is None: employee.mei = EmployeeMEI(employee_id=employee.id)
        for k,v in payload.mei.model_dump().items(): setattr(employee.mei,k,v)
    elif employee.mei is not None:
        db.delete(employee.mei); employee.mei = None
    employee.dependents.clear()
    for x in payload.dependents:
        dep = EmployeeDependent(**x.model_dump(exclude={"alimony"}))
        employee.dependents.append(dep)
        if x.alimony is not None: dep.alimony = EmployeeAlimony(**x.alimony.model_dump())
    employee.bank_accounts.clear()
    for x in payload.bank_accounts: employee.bank_accounts.append(EmployeeBankAccount(**x.model_dump()))
    employee.bonuses.clear()
    for x in payload.bonuses: employee.bonuses.append(EmployeeBonus(legacy_id=x.legacy_id, bonus_type=x.bonus_type, description=x.description, amount=x.amount, competence=x.competence, recurring=x.recurring, active=x.active))
    if payload.transport_plan is not None:
        tp = payload.transport_plan
        if employee.transport_plan is None: employee.transport_plan = EmployeeTransportPlan(employee_id=employee.id)
        plan = employee.transport_plan
        for k,v in tp.model_dump(exclude={"legs"}).items(): setattr(plan,k,v)
        plan.monthly_cost = sum((d(x.fare)*d(x.uses_per_day)*Decimal(str(tp.working_days or 0)) for x in tp.legs), Decimal("0"))
        plan.legs.clear()
        for x in tp.legs: plan.legs.append(EmployeeTransportLeg(**x.model_dump()))


def create_employee(db: Session, payload: EmployeeCreate) -> Employee:
    legacy_id = payload.legacy_id.strip() or f"COL-{abs(hash((payload.full_name, date.today().isoformat())))%100000000}"
    employee = Employee(legacy_id=legacy_id, full_name=payload.full_name)
    db.add(employee); db.flush(); update_employee(db,employee,payload); return employee


def update_employee(db: Session, employee: Employee, payload: EmployeeCreate) -> Employee:
    simple = payload.model_dump(exclude={"address","contacts","health","mei","dependents","bank_accounts","bonuses","transport_plan","benefits"})
    if not simple.get("legacy_id"): simple.pop("legacy_id",None)
    for k,v in simple.items(): setattr(employee,k,v)
    employee.benefits_json = payload.benefits
    replace_nested(db,employee,payload); db.flush(); return employee


def employee_dict(e: Employee, include_health: bool=True) -> dict[str,Any]:
    data={k:getattr(e,k) for k in ["id","legacy_id","full_name","social_name","collaborator_model","employment_category","employee_type","status","birth_date","sex","marital_status","nationality","naturality","mother_name","father_name","cpf","rg","rg_issuer","rg_issue_date","voter_title","voter_zone","voter_section","pis","ctps","cnh","cnh_category","cnh_validity","email","phone_primary","phone_secondary","photo_url","position","sector","work_schedule","scale","start_date","registration_date","admission_date","termination_date","salary","fixed_bonus","variable_bonus","advance_percent","notes","created_at","updated_at"]}
    data["benefits"]=e.benefits_json or []
    data["address"]={k:getattr(e.address,k) for k in ["cep","street","number","complement","neighborhood","city","state","residence_type","house_unit","apartment","block","floor","condominium"]} if e.address else None
    data["contacts"]=[{"id":x.id,"contact_type":x.contact_type,"name":x.name,"relationship":x.relationship,"phone":x.phone,"priority":x.priority} for x in e.contacts]
    if include_health: data["health"]={k:getattr(e.health,k) for k in ["blood_type","has_disease","conditions","under_treatment","treatment","continuous_medication","medication","dosage","medication_schedule","allergies","drug_allergies","restrictions","special_need","health_plan","doctor","can_provide_medication","authorized_medication","emergency_notes"]} if e.health else None
    data["mei"]={"cnpj":e.mei.cnpj,"legal_name":e.mei.legal_name,"trade_name":e.mei.trade_name,"municipal_registration":e.mei.municipal_registration} if e.mei else None
    data["dependents"]=[]
    for x in e.dependents:
        row={"id":x.id,"legacy_id":x.legacy_id,"name":x.name,"birth_date":x.birth_date,"cpf":x.cpf,"relationship":x.relationship,"ir_dependent":x.ir_dependent,"alimony":None}
        if x.alimony: row["alimony"]={k:getattr(x.alimony,k) for k in ["active","agreement_type","calculation_type","fixed_amount","percentage","beneficiary","bank","agency","account","pix_key","notes"]}
        data["dependents"].append(row)
    data["bank_accounts"]=[{k:getattr(x,k) for k in ["id","bank","bank_code","agency","account","account_digit","account_type","holder","holder_document","pix_type","pix_key","pix_institution","portability","origin_bank","destination_bank","receiving_bank","salary_payment","is_primary"]} for x in e.bank_accounts]
    data["bonuses"]=[{"id":x.id,"legacy_id":x.legacy_id,"bonus_type":x.bonus_type,"description":x.description,"amount":x.amount,"competence":x.competence,"recurring":x.recurring,"active":x.active} for x in e.bonuses]
    if e.transport_plan:
        p=e.transport_plan
        data["transport_plan"]={"company_address":p.company_address,"employee_address":p.employee_address,"provider":p.provider,"distance_km":p.distance_km,"duration_minutes":p.duration_minutes,"round_trip_distance_km":p.round_trip_distance_km,"round_trip_duration_minutes":p.round_trip_duration_minutes,"working_days":p.working_days,"reviewed":p.reviewed,"monthly_cost":p.monthly_cost,"route_data":p.route_data,"legs":[{"id":x.id,"transport_type":x.transport_type,"line":x.line,"origin":x.origin,"destination":x.destination,"fare":x.fare,"uses_per_day":x.uses_per_day} for x in p.legs]}
    else: data["transport_plan"]=None
    return data


def registration_alert(e:Employee)->dict[str,Any]:
    if e.employment_category=="MEI": return {"level":"mei","days":0,"label":"MEI"}
    if e.employment_category=="Registrado": return {"level":"ok","days":0,"label":"Registrado"}
    if e.employment_category!="Sem registro" or not e.start_date: return {"level":"neutral","days":0,"label":e.employment_category}
    days=max(0,(date.today()-e.start_date).days)
    level="danger" if days>=settings.registration_alert_danger_days else "warning" if days>=settings.registration_alert_warning_days else "ok"
    return {"level":level,"days":days,"label":f"{days} dia(s) sem registro"}
