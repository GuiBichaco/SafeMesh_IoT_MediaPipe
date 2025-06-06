from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

class Alerta(BaseModel):
    latitude: float
    longitude: float
    timestamp: str
    origem: str
    cidade:str
    estado: str
    tipo_alerta: str
    pais: str
    motivo: str
    nivel_confianca_localizacao: str

alertas_armazenados = []

@app.post("/reportar_localizacao")
def receber_alerta(alerta: Alerta):
    alertas_armazenados.append(alerta.dict())
    print(f"[{datetime.now()}] ALERTA RECEBIDO:")
    print(alerta)
    return {"status": "sucesso", "mensagem": "Alerta recebido com sucesso"}

@app.get("/reportar_localizacao")
def listar_alertas():
    return alertas_armazenados
