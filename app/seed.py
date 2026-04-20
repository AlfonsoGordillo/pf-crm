from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User, Lead, Activity
from app.auth import hash_password
import random

LEADS_DATA = [
    # stage, name, company, email, phone, industry, score, value, notes, days_ago
    ("nuevo", "Carlos Mendoza", "Inmobiliaria Pacífico", "c.mendoza@inmpac.com", "+57 300 123 4567", "inmobiliaria", 0, 15000, "Interesado en agente de atención 24/7 para propiedades", 2),
    ("nuevo", "María González", "Clínica Los Andes", "mgonzalez@clinandes.com", "+57 311 987 6543", "salud", 0, 8000, "Necesita automatizar agendamiento de citas", 3),
    ("nuevo", "Roberto Vargas", "Fintech Capital", "rvargas@fintechcap.io", "+52 55 1234 5678", "fintech", 0, 25000, "Busca detección de fraude en tiempo real", 1),
    ("nuevo", "Ana Restrepo", "Boutique Moda CR", "ana@modacr.com", "+506 8888 1234", "retail", 0, 5000, "Quiere agente de ventas para e-commerce", 4),
    ("nuevo", "Diego Morales", "LogiTech SA", "dmorales@logitech.sa", "+57 320 555 7890", "tecnología", 0, 12000, "Soporte técnico automatizado para clientes SaaS", 1),
    ("contactado", "Laura Jiménez", "Farmacia Vida", "laura@farmavida.com", "+57 301 222 3344", "salud", 35, 7000, "Demo programada para la próxima semana", 7),
    ("contactado", "Juan Pérez", "Constructora Alfa", "jperez@conalfa.com", "+57 315 444 5566", "inmobiliaria", 28, 20000, "Tiene 3 proyectos activos, evalúa AaaS para ventas", 5),
    ("contactado", "Sofía Torres", "E-commerce Plus", "storres@ecomplus.co", "+57 312 666 7788", "retail", 40, 9000, "Comparando con competencia genérica", 6),
    ("contactado", "Alejandro Ríos", "Banco Digital MX", "arios@bancodigitalmx.com", "+52 55 9876 5432", "fintech", 32, 30000, "Interesado en AI-Finance para cierre contable", 8),
    ("contactado", "Patricia Moreno", "HR Solutions", "pmoreno@hrsolutions.co", "+57 318 111 2233", "tecnología", 38, 11000, "Quiere agente Aria para RRHH", 4),
    ("contactado", "Fernando Castro", "Manufactura ABC", "fcastro@mfgabc.com", "+57 313 333 4455", "manufactura", 25, 18000, "Evaluando automatización de reportes", 9),
    ("contactado", "Valentina López", "Legal Consulting", "vlopez@legalco.com", "+57 317 777 8899", "legal", 30, 6000, "Necesita gestión de PQRS para clientes", 6),
    ("calificado", "Andrés Gómez", "Proptech Innovation", "agomez@proptech.io", "+57 310 100 2000", "inmobiliaria", 78, 22000, "Confirmó presupuesto. Decision en 2 semanas", 12),
    ("calificado", "Camila Herrera", "MediApp", "cherrera@mediapp.co", "+57 314 200 3000", "salud", 82, 14000, "CEO muy interesado. Requiere demo con equipo técnico", 10),
    ("calificado", "Santiago Díaz", "Retail360", "sdiaz@retail360.co", "+57 316 300 4000", "retail", 71, 8500, "Tiene 5 tiendas, quiere piloto en 1", 11),
    ("calificado", "Isabella Martínez", "FinSmart", "imartinez@finsmart.io", "+52 55 4444 3333", "fintech", 85, 28000, "Urgente: cierre fiscal en 3 meses", 8),
    ("calificado", "Sebastián Ruiz", "DevOps Corp", "sruiz@devopscorp.com", "+57 319 400 5000", "tecnología", 74, 16000, "Evalúa plan Growth. 3 agentes necesarios", 14),
    ("calificado", "Natalia Flores", "UniEdu Platform", "nflores@uniedu.co", "+57 321 500 6000", "educación", 68, 10000, "Plataforma educativa con 50k usuarios", 9),
    ("calificado", "Luis Ramírez", "AutoParts MX", "lramirez@autoparts.mx", "+52 55 5555 4444", "manufactura", 76, 13000, "Reportes automáticos mensuales prioritarios", 13),
    ("calificado", "Elena Vega", "Constructora Sur", "evega@constsur.com", "+57 322 600 7000", "inmobiliaria", 80, 19000, "Referencias de Carlos Mendoza (cliente Meridian)", 10),
    ("propuesta", "Marcos Silva", "PayMX", "msilva@paymx.io", "+52 55 6666 5555", "fintech", 88, 32000, "Propuesta enviada el lunes. Esperando feedback board", 18),
    ("propuesta", "Carolina Medina", "Clínica Norte", "cmedina@clinorte.com", "+57 323 700 8000", "salud", 83, 11000, "Aprobación de directivos pendiente", 15),
    ("propuesta", "Pablo Estrada", "Supermercados Central", "pestrada@supcentral.com", "+57 324 800 9000", "retail", 86, 15000, "Propuesta para 3 agentes. Negociando precio", 20),
    ("propuesta", "Adriana Benítez", "PropSearch", "abenitez@propsearch.co", "+57 325 900 1000", "inmobiliaria", 79, 21000, "Plan Growth aprobado. Ajustes en integraciones", 16),
    ("propuesta", "Rodrigo Campos", "SaaS Factory", "rcampos@saasfactory.io", "+57 326 010 1100", "tecnología", 91, 24000, "Cierre estimado para fin de mes", 22),
    ("propuesta", "Daniela Romero", "LegalTech Pro", "dromero@legaltech.pro", "+57 327 120 1200", "legal", 77, 9000, "Revisión legal del contrato en proceso", 19),
    ("ganado", "Miguel Ángel Torres", "TechStart Lima", "matorres@techstart.pe", "+51 1 234 5678", "tecnología", 92, 18000, "Firmado plan Growth. Onboarding completado", 30),
    ("ganado", "Juliana Ospina", "FintechPay", "jospina@fintechpay.co", "+57 328 230 1300", "fintech", 95, 26000, "AI-Finance implementado. NPS: 9/10", 45),
    ("ganado", "Hernando Reyes", "Constructora Premium", "hreyes@constpremium.com", "+57 329 340 1400", "inmobiliaria", 89, 35000, "Plan Enterprise. Agente Rex + AI-Finance", 60),
    ("perdido", "Tomás Vargas", "Retail Basic", "tvargas@retailbasic.com", "+57 330 450 1500", "retail", 18, 4000, "Decidió solución interna. Revisar en Q3", 25),
]

ACTIVITY_TEMPLATES = {
    "nuevo": [("note", "Lead registrado en el sistema CRM")],
    "contactado": [
        ("call", "Primera llamada realizada. Lead mostró interés inicial"),
        ("email", "Email de presentación enviado con brochure de productos"),
    ],
    "calificado": [
        ("call", "Llamada de calificación completada. Presupuesto confirmado"),
        ("meeting", "Demo de 30 minutos realizada via Zoom"),
        ("ai_qualify", "Lead calificado por IA: score asignado automáticamente"),
    ],
    "propuesta": [
        ("email", "Propuesta comercial enviada"),
        ("call", "Seguimiento post-propuesta. Sin objeciones mayores"),
        ("meeting", "Reunión con equipo técnico del cliente"),
    ],
    "ganado": [
        ("email", "Contrato firmado. Bienvenida enviada"),
        ("note", "Onboarding iniciado. Cliente asignado a equipo de implementación"),
    ],
    "perdido": [
        ("call", "Llamada de cierre. Razón: solución interna más económica"),
        ("note", "Marcado como perdido. Re-contactar en Q3 2026"),
    ],
}


async def seed_database(db: AsyncSession):
    existing = await db.execute(select(User))
    if existing.scalar_one_or_none():
        return

    demo_user = User(
        email="demo@projectsfactory.io",
        name="Demo User",
        password_hash=hash_password("demo123"),
    )
    db.add(demo_user)

    for (stage, name, company, email, phone, industry, score, value, notes, days_ago) in LEADS_DATA:
        created = datetime.utcnow() - timedelta(days=days_ago)
        last_contact = created + timedelta(days=random.randint(0, max(1, days_ago - 1)))
        lead = Lead(
            name=name, company=company, email=email, phone=phone,
            industry=industry, stage=stage, score=score, value=value,
            notes=notes, assigned_to="Demo User",
            last_contact=last_contact, created_at=created, updated_at=created,
        )
        db.add(lead)
        await db.flush()

        for (act_type, act_desc) in ACTIVITY_TEMPLATES.get(stage, []):
            activity = Activity(
                lead_id=lead.id, type=act_type, description=act_desc,
                created_at=created + timedelta(hours=random.randint(1, 48)),
            )
            db.add(activity)

    await db.commit()
