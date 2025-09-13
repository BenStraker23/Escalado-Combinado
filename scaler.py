# IMPORTACIÓN DE LOS MÓDULOS NECESARIOS
import time
import subprocess # Para ejecutar comandos de Docker desde Python
import psutil # Para monitorear/medir el uso de memoria
from datetime import datetime, timedelta
from logger import log_decision, export_to_excel # Registra decisiones en JSON y luego exporta a Excel

# CONFIGURACIONES
ACCESS_LOG = "logs/access.log"
SERVICE_NAME = "web"

# LÍMITES DE INSTANCIAS PERMITIDAS
MIN_INSTANCES = 1
MAX_INSTANCES = 8

# UMBRAL DE TRÁFICO Y FRECUENCIA DE CHEQUEO
RPS_THRESHOLD = 10
CHECK_INTERVAL = 5 # Segunsdos entre cada revisión

# MEMORIA ESTIMADA QUE CONSUME CADA INSTANCIA
MEMORY_USAGE_PER_INSTANCE_MB = 120

# LÍMITE INICIAL DE MEMORIA SIMULADA
MEMORY_LIMIT_CAP_MB = 800  # Se puede ampliar dinámicamente

# 📊 CUENTA CUÁNTAS PETICIONES SE HICIERON EN LOS ÚLTIMOS N SEGUNDOS
def count_requests_last_interval(log_path, interval_seconds):
    try:
        now = datetime.now()
        cutoff = now - timedelta(seconds=interval_seconds)
        count = 0
        with open(log_path, "r") as log:
            for line in log.readlines():
                if "[" in line:
                    try:
                        timestamp_str = line.split("]")[0][1:]
                        timestamp = datetime.strptime(timestamp_str.split(" +")[0], "%d/%b/%Y:%H:%M:%S")
                        if timestamp > cutoff:
                            count += 1
                    except Exception:
                        continue
        return count
    except FileNotFoundError:
        print("Archivo de log no encontrado.")
        return 0

# DEVUELVE LA MEMORIA LIBRE EN MB, LIMITADA POR UN TOPE SIMULADO
def get_limited_memory():
    real_memory = psutil.virtual_memory().available / (1024 * 1024)
    return min(real_memory, MEMORY_LIMIT_CAP_MB)

# ESCALA EL SERVICIO DOCKER A N INSTANCIAS
def scale_service(service, instances):
    print(f"➡️ Escalando {service} a {instances} instancias...")
    subprocess.run(["docker", "compose", "up", "-d", "--scale", f"{service}={instances}"])

# CICLO PRINCIPAL DE MONITOREO Y ESCALADO
def main():
    global MEMORY_LIMIT_CAP_MB

    current_instances = MIN_INSTANCES
    try:
        while True:
            print("\n📊 Verificando tráfico entrante...")
            rps = count_requests_last_interval(ACCESS_LOG, CHECK_INTERVAL)
            rps_per_sec = rps / CHECK_INTERVAL
            memory_available = get_limited_memory()

            print(f"🔎 RPS promedio: {rps_per_sec:.2f} req/s | Instancias actuales: {current_instances}")
            print(f"🧠 Memoria disponible (limitada): {memory_available:.2f} MB")

            # ESCALAMIENTO HORIZONTAL SI HAY TRÁFICO ALTO Y SUFICIENTE MEMORIA
            if rps_per_sec > RPS_THRESHOLD and current_instances < MAX_INSTANCES:
                required_memory = (current_instances + 1) * MEMORY_USAGE_PER_INSTANCE_MB
                if memory_available >= required_memory:
                    current_instances += 1
                    scale_service(SERVICE_NAME, current_instances)
                    log_decision(
                        rps_per_sec,
                        current_instances,
                        memory_available,
                        "Escalamiento horizontal",
                        "RPS alto y memoria suficiente"
                    )
                else:
                    print("⚠️ Memoria insuficiente para escalar horizontalmente.")
                    print("🔧 Aumentando límite de memoria simulada en 100 MB...")
                    MEMORY_LIMIT_CAP_MB += 100
                    memory_available = get_limited_memory()
                    required_memory = (current_instances + 1) * MEMORY_USAGE_PER_INSTANCE_MB

                    if memory_available >= required_memory:
                        current_instances += 1
                        scale_service(SERVICE_NAME, current_instances)
                        log_decision(
                            rps_per_sec,
                            current_instances,
                            memory_available,
                            "Escalamiento horizontal forzado",
                            f"Límite de memoria aumentado a {MEMORY_LIMIT_CAP_MB} MB"
                        )
                    else:
                        print("❌ Incluso con el aumento de límite, no se puede escalar.")
                        log_decision(
                            rps_per_sec,
                            current_instances,
                            memory_available,
                            "Escalamiento fallido",
                            f"Memoria insuficiente incluso tras aumentar a {MEMORY_LIMIT_CAP_MB} MB"
                        )

            # DESESCALAMIENTO SI EL TRÁFICO ES BAJO
            elif rps_per_sec < (RPS_THRESHOLD / 2) and current_instances > MIN_INSTANCES:
                current_instances -= 1
                scale_service(SERVICE_NAME, current_instances)
                log_decision(
                    rps_per_sec,
                    current_instances,
                    memory_available,
                    "Desescalamiento",
                    "RPS bajo, reduciendo instancias"
                )
            else:
                print("✅ No se requiere escalado en este momento.")
                log_decision(
                    rps_per_sec,
                    current_instances,
                    memory_available,
                    "Sin acción",
                    "RPS dentro del rango aceptable"
                )

            # LIMPIA EL ARCHIVO LOG PARA EL SIGUIENTE CICLO
            with open(ACCESS_LOG, "w") as f:
                pass
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 Benchmark detenido por el usuario.")
        export_to_excel()
        print("📤 Archivo Excel generado exitosamente: decision_log.xlsx")

if __name__ == "__main__":
    main()