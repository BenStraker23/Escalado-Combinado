import os
import json
import pandas as pd
from datetime import datetime

# FUNCIÓN PARA REGISTRAR DECISIONES EN UN ARCHIVO JSON
def log_decision(rps, instances, memory, action, reason):
    entry = {
        "timestamp": datetime.now().isoformat(), # MARCA DE TIEMPO
        "rps": rps, # REQUESTS POR SEGUNDO / PETICIONES POR SEGUNDO
        "instances": instances, # NÚMERO DE INSTANCIAS ACTIVAS
        "memory_mb": memory, # MEMORIA DISPONIBLE EN MB
        "action": action, # ACCIÓN TOMADA (ESCALAR, DESESCALAR, MANTENER)
        "reason": reason # RAZÓN DE LA ACCIÓN
    }
    with open("decision_log.json", "a") as f:
        f.write(json.dumps(entry) + "\n")

# FUNCIÓN PARA EXPORTAR EL ARCHIVO JSON A EXCEL
def export_to_excel(json_path="decision_log.json", output_dir="logs/benchmarks"):
    
    # CARGAR DATOS DESDE JSON
    with open(json_path, "r") as f:
        data = [json.loads(line) for line in f]

    df = pd.DataFrame(data)

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # SEPARAR FECHA Y HORA EN COLUMNAS DISTINTAS
    df["fecha"] = df["timestamp"].dt.date
    df["hora"] = df["timestamp"].dt.time

    # CREAR CARPETA SI NO EXISTE
    os.makedirs(output_dir, exist_ok=True)

    # GENERAR NOMBRE ÚNICO CON FECHA Y HORA PARA EL ARCHIVO EXCEL
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"decision_log_{timestamp_str}.xlsx"
    excel_path = os.path.join(output_dir, excel_filename)

    # EXPORTAR A EXCEL
    df.to_excel(excel_path, index=False)
    print(f"📤 Archivo Excel generado en: {excel_path}")