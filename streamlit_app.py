import json
import time
import pandas as pd
import streamlit as st
import fitz   # PyMuPDF
from google import genai

MODELO = "gemini-3.5-flash-lite"
MAX_ARCHIVOS = 5      # límite para no agotar el cupo gratuito
PAUSA = 4             # segundos entre llamadas (~15 pedidos por minuto)

st.set_page_config(page_title="Asistente de papers", page_icon="📄", layout="wide")
st.title("📄 Asistente de papers")

# ---------- barra lateral: configuración ----------
with st.sidebar:
    st.header("Configuración")
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = st.text_input("Tu API key de Gemini", type="password")
    modo = st.radio("¿Qué querés hacer?", ["Resumen", "Pregunta", "Datos clave"])
    max_palabras = 150
    pregunta = ""
    if modo == "Resumen":
        max_palabras = st.slider("Largo del resumen (palabras)", 50, 300, 150, step=50)
    if modo == "Pregunta":
        pregunta = st.text_input("Tu pregunta sobre los papers")

# ---------- funciones ----------
def texto_de_pdf(archivo):
    doc = fitz.open(stream=archivo.read(), filetype="pdf")
    return " ".join(pagina.get_text() for pagina in doc)

def consultar(prompt, clave, config=None):
    client = genai.Client(api_key=clave)
    return client.models.generate_content(model=MODELO, contents=prompt, config=config)

def procesar(texto, clave):
    """Devuelve un diccionario con las columnas de la fila de resultados (según el modo)."""
    if modo == "Resumen":
        prompt = ("Resumí en español, con ortografía correcta, en como máximo " + str(max_palabras)
                  + " palabras, el siguiente paper. Incluí objetivo, método y resultado principal. "
                  "Si algo no aparece, no lo inventes. Paper: " + texto)
        return {"resumen": consultar(prompt, clave).text}
    if modo == "Pregunta":
        prompt = ("Respondé la pregunta usando solamente la información del paper. "
                  "Si la respuesta no está, decí 'no figura en el paper'. Respondé en español. "
                  "Pregunta: " + pregunta + " Paper: " + texto)
        return {"respuesta": consultar(prompt, clave).text}
    prompt = ("Extraé del paper: objetivo, metodología, tamaño de muestra y resultado principal, en español y "
              "máximo 2 frases por campo. Si un dato no aparece, escribí 'no reportado'. Devolvé un JSON con las "
              "claves objetivo, metodologia, tamano_muestra y resultado_principal. Paper: " + texto)
    r = consultar(prompt, clave, config={"response_mime_type": "application/json"})
    return json.loads(r.text)

# ---------- cuerpo de la app ----------
archivos = st.file_uploader("Subí tus PDFs", type="pdf", accept_multiple_files=True)
if archivos and len(archivos) > MAX_ARCHIVOS:
    st.warning(f"Se van a procesar solo los primeros {MAX_ARCHIVOS} archivos.")
    archivos = archivos[:MAX_ARCHIVOS]

listo = bool(archivos) and bool(api_key) and (modo != "Pregunta" or bool(pregunta))
if st.button("Procesar", disabled=not listo):
    filas = []
    barra = st.progress(0.0)
    for i, archivo in enumerate(archivos):
        try:
            fila = {"archivo": archivo.name, **procesar(texto_de_pdf(archivo), api_key)}
        except Exception as e:
            fila = {"archivo": archivo.name, "error": str(e)}
        filas.append(fila)
        barra.progress((i + 1) / len(archivos))
        time.sleep(PAUSA)
    st.session_state["tabla"] = pd.DataFrame(filas)

if "tabla" in st.session_state:
    pestana1, pestana2 = st.tabs(["Resultados", "Ayuda"])
    with pestana1:
        st.dataframe(st.session_state["tabla"])
        st.download_button("Descargar CSV", st.session_state["tabla"].to_csv(index=False).encode("utf-8"),
                           file_name="resultados.csv", mime="text/csv")
    with pestana2:
        st.write("Los resultados los genera un modelo de IA: verificá siempre los datos importantes contra el paper original.")
elif not api_key:
    st.info("Ingresá tu API key en la barra lateral.")
