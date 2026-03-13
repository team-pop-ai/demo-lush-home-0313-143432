from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import anthropic
import json
import os
import uvicorn
from datetime import datetime, timedelta
import uuid

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else []

# Load mock data
subcontractors = load_json("data/subcontractors.json", [])
historical_quotes = load_json("data/historical_quotes.json", [])
active_projects = load_json("data/active_projects.json", [])
trade_categories = load_json("data/trade_categories.json", [])

# In-memory storage for demo
demo_projects = []
demo_quotes = []

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "active_projects": active_projects[:3],  # Show first 3
        "recent_activity": [
            {"time": "2 min ago", "message": "Kitchen Remodel RFPs sent to 5 subs", "type": "rfp"},
            {"time": "15 min ago", "message": "Quote received from Elite Electrical", "type": "quote"},
            {"time": "1 hour ago", "message": "Bathroom Addition project posted", "type": "project"}
        ]
    })

@app.post("/new-project")
async def new_project(request: Request):
    body = await request.json()
    project_description = body.get("description", "").strip()
    project_address = body.get("address", "").strip()
    
    if not project_description or not project_address:
        return JSONResponse({"error": "Project description and address required"})
    
    # Generate project ID
    project_id = str(uuid.uuid4())[:8]
    
    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        
        # System prompt for trade identification
        system_prompt = """You are a construction project AI that analyzes project descriptions to identify required trades.

Based on the project description, identify all construction trades that will be needed. Consider both obvious and less obvious requirements.

Common trades include: excavation, concrete, electrical, HVAC, plumbing, framing, drywall, flooring, painting, roofing, siding, windows, insulation, cabinetry, countertops, tile work, landscaping.

Respond with a JSON object containing:
- "trades_needed": array of trade names (lowercase, standardized)
- "project_type": brief categorization
- "estimated_timeline": rough estimate in weeks
- "priority_trades": array of 2-3 trades that should be contacted first"""

        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Project: {project_address}\n\nDescription: {project_description}"}],
        )
        
        # Parse AI response
        ai_response = msg.content[0].text
        
        # Try to extract JSON, fallback to structured response
        try:
            analysis = json.loads(ai_response)
        except:
            # Fallback parsing
            analysis = {
                "trades_needed": ["electrical", "plumbing", "drywall", "painting"],
                "project_type": "renovation",
                "estimated_timeline": "4-6 weeks",
                "priority_trades": ["electrical", "plumbing"]
            }
        
        # Create project record
        project = {
            "id": project_id,
            "address": project_address,
            "description": project_description,
            "trades_needed": analysis.get("trades_needed", []),
            "project_type": analysis.get("project_type", "renovation"),
            "estimated_timeline": analysis.get("estimated_timeline", "4-6 weeks"),
            "priority_trades": analysis.get("priority_trades", []),
            "created_at": datetime.now().isoformat(),
            "status": "analyzing",
            "rfps_sent": 0,
            "quotes_received": 0
        }
        
        demo_projects.append(project)
        
        return JSONResponse({
            "success": True,
            "project_id": project_id,
            "analysis": analysis,
            "ai_response": ai_response
        })
        
    except Exception as e:
        return JSONResponse({"error": f"AI analysis failed: {str(e)}"}, status_code=500)

@app.post("/send-rfps")
async def send_rfps(request: Request):
    body = await request.json()
    project_id = body.get("project_id", "").strip()
    
    if not project_id:
        return JSONResponse({"error": "Project ID required"})
    
    # Find project
    project = next((p for p in demo_projects if p["id"] == project_id), None)
    if not project:
        return JSONResponse({"error": "Project not found"})
    
    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        
        # System prompt for RFP generation
        system_prompt = """You are a construction project manager AI that generates professional RFP emails to subcontractors.

Create professional, concise RFP email content that includes:
- Clear subject line
- Project location and scope
- Key requirements and timeline
- Request for detailed quote
- Response deadline (1 week from now)
- Professional but friendly tone

Generate emails for each trade needed. Format as JSON with structure:
{
  "emails": [
    {
      "trade": "trade name",
      "subject": "email subject",
      "body": "email body content",
      "selected_subs": ["sub1", "sub2", "sub3"]
    }
  ],
  "total_rfps": number
}"""

        trades_list = ", ".join(project["trades_needed"])
        project_info = f"""Project: {project['address']}
Description: {project['description']}
Trades needed: {trades_list}
Timeline: {project['estimated_timeline']}"""

        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": project_info}],
        )
        
        ai_response = msg.content[0].text
        
        # Try to parse JSON response
        try:
            rfp_data = json.loads(ai_response)
        except:
            # Fallback structure
            rfp_data = {
                "emails": [
                    {
                        "trade": trade,
                        "subject": f"Quote Request - {project['address']} - {trade.title()} Work",
                        "body": f"We have a {project['project_type']} project at {project['address']} requiring {trade} work. Please provide your quote by next week.",
                        "selected_subs": [sub["name"] for sub in subcontractors if sub.get("trade", "").lower() == trade.lower()][:3]
                    }
                    for trade in project["trades_needed"][:4]  # Limit for demo
                ],
                "total_rfps": len(project["trades_needed"]) * 3
            }
        
        # Update project status
        project["status"] = "rfps_sent"
        project["rfps_sent"] = rfp_data.get("total_rfps", 0)
        project["rfp_emails"] = rfp_data.get("emails", [])
        
        return JSONResponse({
            "success": True,
            "rfp_data": rfp_data,
            "ai_response": ai_response
        })
        
    except Exception as e:
        return JSONResponse({"error": f"RFP generation failed: {str(e)}"}, status_code=500)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Combine demo projects with active projects for fuller dashboard
    all_projects = demo_projects + active_projects
    
    # Calculate summary stats
    total_projects = len(all_projects)
    pending_quotes = sum(1 for p in all_projects if p.get("status") in ["rfps_sent", "analyzing"])
    completed_quotes = sum(1 for p in all_projects if p.get("status") == "quotes_received")
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "projects": all_projects,
        "stats": {
            "total_projects": total_projects,
            "pending_quotes": pending_quotes,
            "completed_quotes": completed_quotes,
            "avg_response_time": "8.2 days"
        }
    })

@app.post("/process-quote")
async def process_quote(request: Request):
    body = await request.json()
    quote_text = body.get("quote_text", "").strip()
    project_id = body.get("project_id", "").strip()
    subcontractor = body.get("subcontractor", "").strip()
    
    if not all([quote_text, project_id, subcontractor]):
        return JSONResponse({"error": "Quote text, project ID, and subcontractor required"})
    
    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        
        system_prompt = """You are a construction quote analysis AI. Analyze incoming subcontractor quotes for completeness, pricing reasonableness, and potential issues.

Check for:
- Is the quote complete? (materials, labor, timeline specified)
- Are there any missing typical items?
- How does pricing compare to market rates?
- Are there any red flags or concerns?
- What clarifying questions should be asked?

Respond with JSON:
{
  "completeness_score": 1-10,
  "pricing_assessment": "reasonable/high/low/unclear",
  "missing_items": ["item1", "item2"],
  "red_flags": ["concern1", "concern2"],
  "follow_up_questions": ["question1", "question2"],
  "summary": "brief overall assessment"
}"""

        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Subcontractor: {subcontractor}\n\nQuote:\n{quote_text}"}],
        )
        
        ai_response = msg.content[0].text
        
        try:
            analysis = json.loads(ai_response)
        except:
            # Fallback analysis
            analysis = {
                "completeness_score": 7,
                "pricing_assessment": "reasonable",
                "missing_items": ["permit costs", "cleanup"],
                "red_flags": [],
                "follow_up_questions": ["What is your estimated timeline?", "Are permits included?"],
                "summary": "Generally complete quote, minor clarifications needed"
            }
        
        # Store the quote analysis
        quote_record = {
            "id": str(uuid.uuid4())[:8],
            "project_id": project_id,
            "subcontractor": subcontractor,
            "quote_text": quote_text,
            "analysis": analysis,
            "received_at": datetime.now().isoformat()
        }
        
        demo_quotes.append(quote_record)
        
        return JSONResponse({
            "success": True,
            "analysis": analysis,
            "ai_response": ai_response
        })
        
    except Exception as e:
        return JSONResponse({"error": f"Quote analysis failed: {str(e)}"}, status_code=500)

@app.get("/api/project-status/{project_id}")
async def get_project_status(project_id: str):
    # Find in demo projects first
    project = next((p for p in demo_projects if p["id"] == project_id), None)
    
    # Fall back to active projects
    if not project:
        project = next((p for p in active_projects if p.get("project_id") == project_id), None)
    
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)
    
    # Get related quotes
    project_quotes = [q for q in demo_quotes if q["project_id"] == project_id]
    
    return JSONResponse({
        "project": project,
        "quotes": project_quotes,
        "quote_count": len(project_quotes)
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)