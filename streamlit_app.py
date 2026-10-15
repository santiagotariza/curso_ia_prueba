import streamlit as st
import fitz   # PyMuPDF
from google import genai

MODELO = "gemini-3.5-flash-lite"

def procesar(texto_pdf, api_key):
    # Esta función debe ser AUTOCONTENIDA: define adentro todo lo que usa.
    client = genai.Client(api_key=api_key)
    prompt = ("Resumí en español, con ortografía correcta, en como máximo 150 palabras, "
              "el siguiente paper. Incluí objetivo, método y resultado principal. "
              "Si algo no aparece, no lo inventes. Paper: " + texto_pdf)
    return client.models.generate_content(model=MODELO, contents=prompt).text


st.set_page_config(page_title="Asistente de papers", page_icon="📄")
st.title("📄 Asistente de papers")
st.write("Subí un PDF y obtené el resultado automáticamente.")

# --- API key: de los secretos de Streamlit, o la ingresa quien usa la app ---
def obtener_api_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return ""

api_key = obtener_api_key()
if not api_key:
    api_key = st.text_input("Tu API key de Gemini", type="password")

archivo = st.file_uploader("Subí un PDF", type="pdf")

if archivo is not None and api_key:
    if st.button("Procesar"):
        with st.spinner("Procesando..."):
            try:
                doc = fitz.open(stream=archivo.read(), filetype="pdf")
                texto = " ".join(pagina.get_text() for pagina in doc)
                st.subheader("Resultado")
                st.write(procesar(texto, api_key))
            except Exception as e:
                st.error(f"Ocurrió un error: {e}")
elif archivo is not None:
    st.info("Falta la API key.")
