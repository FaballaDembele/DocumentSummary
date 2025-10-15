# streamlit_ui.py
import streamlit as st
import requests
import json

# === CONFIGURATION ===
API_URL = "http://localhost:8000/analyze/"  # <-- URL de ton API (change si déployée)

st.set_page_config(page_title="🧠 SmartDoc Résumeur", layout="wide")
st.title("📄 SmartDoc – Test de l'API de Résumé Automatique")

st.markdown("""
Cette interface permet de **tester l'API FastAPI** de résumé automatique pour les **courriers et factures (PDF ≤ 2 pages)**.  
👉 Téléverse ton fichier ci-dessous pour lancer l'analyse.
""")

uploaded_file = st.file_uploader("Téléverser un fichier PDF", type=["pdf"])

if uploaded_file:
    st.info("⏳ Envoi du fichier à l'API...")

    # Envoi à l'API FastAPI
    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
    try:
        response = requests.post(API_URL, files=files, timeout=300)
        if response.status_code == 200:
            data = response.json()

            st.success("✅ Analyse réussie !")

            # === Résumé global ===
            st.subheader("🧾 Résumé global")
            st.write(data.get("summary", "Aucun résumé trouvé."))

            # === Type de document ===
            st.markdown(f"**Type détecté :** `{data.get('doc_type', 'inconnu')}`")

            # # === Champs détectés ===
            # st.subheader("📋 Champs extraits")
            # fields = data.get("fields", {})
            # if fields:
            #     for k, v in fields.items():
            #         st.write(f"**{k.capitalize()} :** {v if v else 'Non détecté'}")
            # else:
            #     st.write("Aucun champ détecté.")

            # # === Résumés par page ===
            # st.subheader("📑 Résumé par page")
            # for page_data in data.get("page_summaries", []):
            #     st.markdown(f"**Page {page_data['page']} :** {page_data['summary']}")

            # # === Aperçu du texte extrait ===
            # with st.expander("🔍 Voir un extrait du texte brut extrait"):
            #     st.text_area("Texte extrait", value=data.get("full_text", "")[:4000], height=200)

            # === Téléchargement du résumé ===
            summary_text = data.get("summary", "")
            if summary_text:
                st.download_button(
                    "💾 Télécharger le résumé (.pdf)",
                    summary_text,
                    file_name=f"resume_{uploaded_file.name}.pdf",
                )
        else:
            st.error(f"Erreur {response.status_code} : {response.text}")

    except requests.exceptions.RequestException as e:
        st.error(f"Erreur de connexion à l'API : {e}")
