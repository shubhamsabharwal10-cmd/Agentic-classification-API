from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse
from app.pipeline import ClassificationPipeline

app = FastAPI(
    title="Parivesh DSS Classification API",
    version="1.0"
)

pipeline = ClassificationPipeline(config_dir="app/config")


# 🔹 Option 1: Redirect root URL to Swagger UI
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.post("/classify")
def classify_project(payload: dict, debug: bool = Query(False)):
    return pipeline.run(payload, debug)


# 🔹 Option 2: Print Swagger URL on startup
@app.on_event("startup")
def show_docs_url():
    print("🚀 Parivesh DSS API is running")
    print("📘 Swagger UI available at: http://127.0.0.1:8000/docs")
