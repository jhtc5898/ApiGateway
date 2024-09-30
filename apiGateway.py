from fastapi import FastAPI, HTTPException,Depends
from pydantic import BaseModel
from starlette.requests import Request
import requests
from sqlalchemy import Integer, create_engine, Column, String
from sqlalchemy import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
import docker
import psutil
import socket
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
client = docker.from_env()

Instrumentator().instrument(app).expose(app)


# ------------------------
# Constantes
# ------------------------

SQLALCHEMY_DATABASE_URL = "postgresql://admin:admin@postgresql:5432/services"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ------------------------
# Definición de modelos
# ------------------------

class ServicioCreate(BaseModel):
    id: str
    url: str
    nombre: str
    estado: str = '1'

class DataId(BaseModel):
    id: str

class Servicio(Base):
    __tablename__ = "servicio"
    id = Column(String, primary_key=True)
    url = Column(String,  nullable=False)
    nombre = Column(String,  nullable=False)
    estado = Column(String(1), nullable=False, default='1')

    
# ------------------------
# Conexión a la base de datos
# ------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------
# Metodos preprocesamiento 
# ------------------------

def limpiar_id(nombre: str) -> str:
    return nombre.lower().replace(" ", "")

def limpiar_url(url: str) -> str:
    return url.replace(" ", "")

def get_servicios():
    db = SessionLocal()
    servicios = db.query(Servicio).filter(Servicio.estado == '1').all()
    db.close()
    return {limpiar_id(servicio.id): limpiar_url(servicio.url) for servicio in servicios}

def get_all_servicios():
    db = SessionLocal()
    servicios = db.query(Servicio).all()
    db.close()
    return servicios

async def gateway_request(method: str, servicio: str, path: str, request: Request):
    servicios = get_servicios()
    print(servicios)
    if servicio not in servicios:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    else:
        url = f"{servicios[servicio]}/{path}"
        response = requests.request(method, url, headers=dict(request.headers), data=await request.body())

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Error al llamar al servicio")

    return response.json()

def crear_servicio(db: Session, servicio: ServicioCreate):
    try:
        nuevo_servicio = Servicio(id=servicio.id, url=servicio.url, nombre=servicio.nombre, estado=servicio.estado)
        db.add(nuevo_servicio)
        db.commit()
        db.refresh(nuevo_servicio)
    
        return nuevo_servicio
    
    except Exception as e:
        print(e)
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear el servicio")


def editar_info_servicio(db: Session, servicio: ServicioCreate):
    try:
        # Recuperar el servicio existente de la base de datos
        servicio_db = db.query(Servicio).filter(Servicio.id == servicio.id).first()

        if not servicio_db:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")

        # Actualizar los campos del servicio existente
        servicio_db.url = servicio.url
        servicio_db.nombre = servicio.nombre

        # Guardar los cambios
        db.commit()
        db.refresh(servicio_db)

        return {"message": "Servicio actualizado"}
    
    except Exception as e:
        print(e)
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al editar el servicio")

def cambiar_estado_servicio(db: Session, servicio_id: str, nuevo_estado: str):
    # Validación de que existe el servicio a actualizar
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    db.query(Servicio).filter(Servicio.id == servicio_id).update({Servicio.estado: nuevo_estado})
    db.commit()
    return {"message": f"Servicio {'activado' if nuevo_estado == '1' else 'eliminado'}"}


# ------------------------
# health check
# ------------------------
@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "healthy"}, status_code=200)

# ------------------------
# Definición de rutas
# ------------------------

@app.post("/nuevoServicio")
async def crear_nuevo_servicio(servicio: ServicioCreate, db: Session = Depends(get_db)):
    print(servicio)
    nuevo_servicio = crear_servicio(db, servicio)
    return nuevo_servicio

@app.post("/editarServicio")
async def editar_servicio(servicio: ServicioCreate, db: Session = Depends(get_db)):
    print(servicio)
    nuevo_servicio = editar_info_servicio(db, servicio)
    return nuevo_servicio

@app.post("/deleteServicio")
async def eliminar_servicio(servicio: DataId, db: Session = Depends(get_db)):
    return cambiar_estado_servicio(db, servicio.id, '0')

@app.post("/activarServicio")
async def activar_servicio(servicio: DataId, db: Session = Depends(get_db)):
    return cambiar_estado_servicio(db, servicio.id, '1')

@app.get("/obtenerServicios")
async def obtener_servicio():
    servicios = get_all_servicios()
    return servicios

@app.get("/obtenerInformacionContenedor")
async def obtener_informacion_servicio():

    try:
        client = docker.from_env()
        container = client.containers.get(socket.gethostname())  # Obtener el contenedor actual

        # Obtener información del contenedor desde sus atributos
        container_attrs = container.attrs

        # Obtener el uso de CPU y memoria
        stats = container.stats(stream=False)
        cpu_stats = stats['cpu_stats']
        memory_stats = stats['memory_stats']

        # Calcular el uso total de CPU en unidades proporcionales a los núcleos
        cpu_total_usage = cpu_stats['cpu_usage']['total_usage'] / 1e9  # Convertir a segundos (1e9 nanosegundos por segundo)

        # Obtener el uso de memoria en bytes
        memory_usage = memory_stats['usage']

        # Obtener el límite de memoria del contenedor en bytes
        memory_limit = container_attrs['HostConfig']['Memory']

        # Obtener la red del contenedor
        networks = container_attrs['NetworkSettings']['Networks']
        network_info = {network: networks[network]['IPAddress'] for network in networks}

        # Obtener los puertos expuestos del contenedor
        ports = container_attrs['HostConfig']['PortBindings']
        ports_info = {port: ports[port][0]['HostPort'] for port in ports} if ports else None

        # Obtener más detalles del contenedor
        container_details = {
            "Nombre del Contenedor": container.name,
            "Container ID": container.id,
            "Estado": container.status,
            "Imagen": container_attrs['Config']['Image'],
            "Comandos de Inicio": container_attrs['Config']['Cmd'],
            "Variables de Entorno": container_attrs['Config']['Env'],
            "Volúmenes Montados": container_attrs['Mounts'],
            "Configuración de Red": network_info,
            "Fecha de Creación": container_attrs['Created'],
            "Última Actualización": container_attrs['State']['StartedAt'],
            "Etiquetas": container_attrs['Config']['Labels'],
            "CPU Total Usage (Seconds)": cpu_total_usage,
            "Memory Usage (Bytes)": memory_usage,
            "Memory Limit (Bytes)": memory_limit,
            "Exposed Ports": ports_info
        }

        return container_details

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ------------------------
# Definición de rutas api gateway
# ------------------------

@app.get("/{servicio}/{path:path}")
async def gateway_get(servicio: str, path: str, request: Request):
    return await gateway_request("GET", servicio, path, request)

@app.post("/{servicio}/{path:path}")
async def gateway_post(servicio: str, path: str, request: Request):
    return await gateway_request("POST", servicio, path, request)

@app.put("/{servicio}/{path:path}")
async def gateway_put(servicio: str, path: str, request: Request):
    return await gateway_request("PUT", servicio, path, request)

@app.patch("/{servicio}/{path:path}")
async def gateway_patch(servicio: str, path: str, request: Request):
    return await gateway_request("PATCH", servicio, path, request)

@app.delete("/{servicio}/{path:path}")
async def gateway_delete(servicio: str, path: str, request: Request):
    return await gateway_request("DELETE", servicio, path, request)

@app.head("/{servicio}/{path:path}")
async def gateway_head(servicio: str, path: str, request: Request):
    return await gateway_request("HEAD", servicio, path, request)

@app.options("/{servicio}/{path:path}")
async def gateway_options(servicio: str, path: str, request: Request):
    return await gateway_request("OPTIONS", servicio, path, request)


  

# ------------------------
# Inicialización
# ------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
