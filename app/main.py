import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from app.database import get_db, init_db, async_session
from app.models import Lead
from app.auth import verify_password, create_token, decode_token, hash_password
from app.crud import get_leads, get_lead, update_lead, add_activity, get_activities, get_dashboard_stats, get_user_by_email
from app.agent import qualify_lead, suggest_followup, draft_email
from app.seed import seed_database
from app.i18n import get_t

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_lang(request: Request) -> str:
    return request.cookies.get("pf_lang", "en")


def auth_check(request: Request):
    token = request.cookies.get("access_token")
    if not token or not decode_token(token):
        return None
    return decode_token(token)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with async_session() as db:
        await seed_database(db)
    yield


app = FastAPI(title="Projects Factory CRM", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if auth_check(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if auth_check(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    lang = get_lang(request)
    return templates.TemplateResponse("login.html", {"request": request, "t": get_t(lang), "lang": lang})


@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        lang = get_lang(request)
        return templates.TemplateResponse("login.html", {
            "request": request, "t": get_t(lang), "lang": lang,
            "error": "Invalid credentials" if lang == "en" else "Credenciales incorrectas"
        })
    token = create_token(email)
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie("access_token", token, httponly=True, max_age=3600 * 8)
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@app.get("/lang/{lang}")
async def set_lang(lang: str, request: Request):
    referer = request.headers.get("referer", "/dashboard")
    response = RedirectResponse(url=referer, status_code=302)
    response.set_cookie("pf_lang", lang if lang in ("en", "es") else "en")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    email = auth_check(request)
    if not email:
        return RedirectResponse(url="/login", status_code=302)
    lang = get_lang(request)
    stats = await get_dashboard_stats(db)
    recent = await get_leads(db)
    recent = recent[:8]
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "t": get_t(lang), "lang": lang,
        "stats": stats, "recent_leads": recent, "email": email,
    })


@app.get("/leads", response_class=HTMLResponse)
async def leads_page(request: Request, stage: str = None, industry: str = None, search: str = None, db: AsyncSession = Depends(get_db)):
    email = auth_check(request)
    if not email:
        return RedirectResponse(url="/login", status_code=302)
    lang = get_lang(request)
    leads = await get_leads(db, stage=stage, industry=industry, search=search)
    return templates.TemplateResponse("leads.html", {
        "request": request, "t": get_t(lang), "lang": lang,
        "leads": leads, "email": email,
        "filter_stage": stage or "", "filter_industry": industry or "", "search": search or "",
    })


@app.get("/leads/{lead_id}", response_class=HTMLResponse)
async def lead_detail(request: Request, lead_id: int, db: AsyncSession = Depends(get_db)):
    email = auth_check(request)
    if not email:
        return RedirectResponse(url="/login", status_code=302)
    lang = get_lang(request)
    lead = await get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404)
    activities = await get_activities(db, lead_id)
    return templates.TemplateResponse("lead_detail.html", {
        "request": request, "t": get_t(lang), "lang": lang,
        "lead": lead, "activities": activities, "email": email,
    })


@app.post("/leads/{lead_id}")
async def update_lead_route(request: Request, lead_id: int, db: AsyncSession = Depends(get_db),
    name: str = Form(None), company: str = Form(None), email_field: str = Form(None, alias="email"),
    phone: str = Form(None), industry: str = Form(None), stage: str = Form(None),
    value: float = Form(None), notes: str = Form(None)):
    if not auth_check(request):
        return RedirectResponse(url="/login", status_code=302)
    lead = await get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404)
    data = {k: v for k, v in {
        "name": name, "company": company, "email": email_field,
        "phone": phone, "industry": industry, "stage": stage,
        "value": value, "notes": notes,
    }.items() if v is not None}
    await update_lead(db, lead, data)
    await add_activity(db, lead_id, "note", f"Lead updated: {', '.join(data.keys())}")
    return RedirectResponse(url=f"/leads/{lead_id}", status_code=302)


@app.post("/api/agent/qualify/{lead_id}")
async def api_qualify(request: Request, lead_id: int, db: AsyncSession = Depends(get_db)):
    if not auth_check(request):
        raise HTTPException(status_code=401)
    lead = await get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404)
    lang = get_lang(request)
    result = await qualify_lead(lead, lang)
    await add_activity(db, lead_id, "ai_qualify", result[:300] + "..." if len(result) > 300 else result)
    return JSONResponse({"result": result})


@app.post("/api/agent/followup/{lead_id}")
async def api_followup(request: Request, lead_id: int, db: AsyncSession = Depends(get_db)):
    if not auth_check(request):
        raise HTTPException(status_code=401)
    lead = await get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404)
    lang = get_lang(request)
    result = await suggest_followup(lead, lang)
    await add_activity(db, lead_id, "ai_followup", result[:300] + "..." if len(result) > 300 else result)
    return JSONResponse({"result": result})


@app.post("/api/agent/email/{lead_id}")
async def api_email(request: Request, lead_id: int, db: AsyncSession = Depends(get_db)):
    if not auth_check(request):
        raise HTTPException(status_code=401)
    lead = await get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404)
    lang = get_lang(request)
    result = await draft_email(lead, lang)
    await add_activity(db, lead_id, "ai_email", result[:300] + "..." if len(result) > 300 else result)
    return JSONResponse({"result": result})
