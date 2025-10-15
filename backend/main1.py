# app.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import shutil
import tempfile
import os

from summarizer_service import analyze_pdf

app = FastAPI(title="SmartDoc Summarizer API - courrier/facture (fr)")

@app.get("/",
         summary="Point de départ de l'API",
         description="Bienvenue à l'API de resumer de document. Utilisez le point de terminaison /analyze pour resumer un document.",
            response_description="Message de bienvenue",
            operation_id="health_check",
            tags=["Général"]
         )
async def root():
    return {"message": "Bienvenue à l'API de classification de documents d'identité. Utilisez le point de terminaison /upload pour vérifier vos documents."}

@app.post("/analyze/")
async def analyze(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés.")
    # Enregistrer dans temp et analyser (pdfplumber accepte file path)
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        result = analyze_pdf(tmp_path)
        # supprimer fichier temporaire
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")
