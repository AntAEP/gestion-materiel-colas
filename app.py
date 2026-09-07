import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestion du matériel - AEP COLAS", layout="wide")
st.title("Gestion du matériel - AEP COLAS")

# Initialisation de la connexion Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)


# ==========================================
# FONCTIONS DE LECTURE & ÉCRITURE
# ==========================================

def charger_donnees():
    try:
        # Lecture de l'onglet 'equipes'
        df_eq = conn.read(worksheet="equipes", ttl="0s")
        if df_eq.empty or "Équipe" not in df_eq.columns:
            equipes = ["Stock / Dépot"]
        else:
            equipes = df_eq["Équipe"].dropna().astype(str).tolist()
            if "Stock / Dépot" not in equipes:
                equipes.append("Stock / Dépot")

        # Lecture de l'onglet 'outils'
        df_outils = conn.read(worksheet="outils", ttl="0s")
        colonnes_attendues = ["Outil", "Équipe", "État", "Prêté_à", "Commentaire"]
        for col in colonnes_attendues:
            if col not in df_outils.columns:
                df_outils[col] = ""

        df_outils = df_outils.fillna("")
        return equipes, df_outils
    except Exception as e:
        st.error(f"Erreur de connexion à Google Sheets : {e}")
        return ["Stock / Dépot"], pd.DataFrame(columns=["Outil", "Équipe", "État", "Prêté_à", "Commentaire"])


# Chargement initial dans session_state
if "outils" not in st.session_state or "equipes" not in st.session_state:
    st.session_state.equipes, st.session_state.outils = charger_donnees()


def synchroniser_equipes():
    df = pd.DataFrame({"Équipe": st.session_state.equipes})
    conn.update(worksheet="equipes", data=df)


def synchroniser_outils():
    conn.update(worksheet="outils", data=st.session_state.outils)


# ==========================================
# BARRE LATÉRALE : ADMINISTRATION
# ==========================================
st.sidebar.header("Paramètres")

# Bouton de synchronisation manuelle
if st.sidebar.button("🔄 Rafraîchir les données"):
    st.session_state.equipes, st.session_state.outils = charger_donnees()
    st.rerun()

# --- Formulaire 1 : Ajouter un outil ---
st.sidebar.subheader("➕ Ajouter un outil")
with st.sidebar.form("ajouter_outil_form", clear_on_submit=True):
    nom_nouvel_outil = st.text_input("Nom de l'outil")
    attribution_initiale = st.selectbox("Équipe propriétaire", st.session_state.equipes)
    etat_initial = st.selectbox("État initial", ["Opérationnel", "En prêt", "En réparation", "Cassé"])
    commentaire_initial = st.text_input("Commentaire (optionnel)")
    btn_ajouter_outil = st.form_submit_button("Ajouter l'outil")

    if btn_ajouter_outil:
        if nom_nouvel_outil.strip() != "":
            if nom_nouvel_outil in st.session_state.outils["Outil"].values:
                st.sidebar.error("Cet outil existe déjà !")
            else:
                nouvel_outil_df = pd.DataFrame([{
                    "Outil": nom_nouvel_outil.strip(),
                    "Équipe": attribution_initiale,
                    "État": etat_initial,
                    "Prêté_à": "",
                    "Commentaire": commentaire_initial.strip()
                }])
                st.session_state.outils = pd.concat([st.session_state.outils, nouvel_outil_df], ignore_index=True)
                synchroniser_outils()
                st.sidebar.success(f"Outil '{nom_nouvel_outil}' ajouté !")
                st.rerun()
        else:
            st.sidebar.warning("Veuillez saisir un nom d'outil.")

# --- Formulaire 2 : Supprimer un outil ---
st.sidebar.subheader("🗑️ Supprimer un outil")
if not st.session_state.outils.empty:
    with st.sidebar.form("supprimer_outil_form"):
        outil_a_supprimer = st.selectbox("Sélectionner l'outil à retirer", st.session_state.outils["Outil"])
        btn_supprimer_outil = st.form_submit_button("Supprimer définitivement")

        if btn_supprimer_outil:
            st.session_state.outils = st.session_state.outils[st.session_state.outils["Outil"] != outil_a_supprimer]
            synchroniser_outils()
            st.sidebar.success(f"Outil '{outil_a_supprimer}' supprimé !")
            st.rerun()

# --- Formulaire 3 : Ajouter une personne ---
st.sidebar.subheader("👤 Ajouter une personne")
with st.sidebar.form("ajouter_equipe_form", clear_on_submit=True):
    nom_nouvelle_equipe = st.text_input("Nom du responsable")
    btn_ajouter_equipe = st.form_submit_button("Ajouter")

    if btn_ajouter_equipe:
        if nom_nouvelle_equipe.strip() != "":
            if nom_nouvelle_equipe in st.session_state.equipes:
                st.sidebar.error("Ce nom existe déjà dans la liste !")
            else:
                st.session_state.equipes.append(nom_nouvelle_equipe.strip())
                synchroniser_equipes()
                st.sidebar.success(f"'{nom_nouvelle_equipe}' ajouté à la liste !")
                st.rerun()
        else:
            st.sidebar.warning("Veuillez saisir un nom.")

# --- Formulaire 4 : Supprimer une personne ---
st.sidebar.subheader("❌ Supprimer une personne")
personnes_supprimables = [p for p in st.session_state.equipes if p != "Stock / Dépot"]

if personnes_supprimables:
    with st.sidebar.form("supprimer_equipe_form"):
        personne_a_supprimer = st.selectbox("Sélectionner la personne à retirer", personnes_supprimables)
        btn_supprimer_equipe = st.form_submit_button("Supprimer la personne")

        if btn_supprimer_equipe:
            st.session_state.outils.loc[
                st.session_state.outils["Équipe"] == personne_a_supprimer, "Équipe"] = "Stock / Dépot"
            st.session_state.outils.loc[
                st.session_state.outils["Prêté_à"] == personne_a_supprimer, ["Prêté_à", "État"]] = ["", "Opérationnel"]
            st.session_state.equipes.remove(personne_a_supprimer)
            synchroniser_outils()
            synchroniser_equipes()
            st.sidebar.success(f"'{personne_a_supprimer}' retiré(e). Ses outils ont été réaffectés.")
            st.rerun()

# ==========================================
# PAGE PRINCIPALE : TABLEAU D'AFFICHAGE
# ==========================================

st.session_state.outils["Commentaire"] = st.session_state.outils["Commentaire"].fillna("")
st.session_state.outils["Prêté_à"] = st.session_state.outils["Prêté_à"].fillna("")

st.subheader("🔍 Recherche rapide")
recherche = st.text_input(
    "Filtrer les outils",
    placeholder="Tapez un nom d'outil, un prénom, un état...",
    key="search_box"
)

vue_tableau = st.session_state.outils.copy()


def formater_situation(ligne):
    if ligne["État"] == "En prêt" and ligne["Prêté_à"]:
        return f"{ligne['Équipe']} ➔ prêté à {ligne['Prêté_à']}"
    return ligne["Équipe"]


vue_tableau["Affectation"] = vue_tableau.apply(formater_situation, axis=1)

if recherche.strip() != "":
    masque = (
            vue_tableau["Outil"].str.contains(recherche, case=False, na=False) |
            vue_tableau["Affectation"].str.contains(recherche, case=False, na=False) |
            vue_tableau["État"].str.contains(recherche, case=False, na=False) |
            vue_tableau["Commentaire"].str.contains(recherche, case=False, na=False)
    )
    vue_a_afficher = vue_tableau[masque]
else:
    vue_a_afficher = vue_tableau

st.subheader("📋 État du parc d'outils")
colonnes_finales = ["Outil", "Affectation", "État", "Commentaire"]
st.dataframe(vue_a_afficher[colonnes_finales], use_container_width=True)

# ==========================================
# FORMULAIRE DE MODIFICATION / TRANSFERT
# ==========================================
st.subheader("🔄 Modifier l'affectation, prêt ou état")

if not st.session_state.outils.empty:
    liste_outils_disponibles = vue_a_afficher["Outil"].tolist()

    if liste_outils_disponibles:
        outil_select = st.selectbox(
            "Choisir l'outil à mettre à jour :",
            liste_outils_disponibles
        )

        outil_data = st.session_state.outils[st.session_state.outils["Outil"] == outil_select].iloc[0]

        idx_titulaire = st.session_state.equipes.index(outil_data["Équipe"]) if outil_data[
                                                                                    "Équipe"] in st.session_state.equipes else 0
        etats = ["Opérationnel", "En prêt", "En réparation", "Cassé"]
        idx_etat = etats.index(outil_data["État"]) if outil_data["État"] in etats else 0

        col1, col2 = st.columns(2)
        with col1:
            nouvelle_equipe = st.selectbox("Équipe propriétaire (Titulaire)", st.session_state.equipes,
                                           index=idx_titulaire)
            nouvel_etat = st.selectbox("État de l'outil", etats, index=idx_etat)

        with col2:
            nouveau_prete_a = ""
            if nouvel_etat == "En prêt":
                emprunteurs_possibles = [e for e in st.session_state.equipes if e != nouvelle_equipe]
                idx_emprunteur = 0
                if outil_data["Prêté_à"] in emprunteurs_possibles:
                    idx_emprunteur = emprunteurs_possibles.index(outil_data["Prêté_à"])
                nouveau_prete_a = st.selectbox("Prêté à qui ?", emprunteurs_possibles, index=idx_emprunteur)
            else:
                st.info("💡 Passez l'état sur **En prêt** pour désigner un emprunteur.")

            nouveau_commentaire = st.text_input("Commentaire / Raison", value=str(outil_data["Commentaire"]))

        if st.button("💾 Enregistrer les modifications", type="primary"):
            st.session_state.outils.loc[
                st.session_state.outils["Outil"] == outil_select,
                ["Équipe", "État", "Prêté_à", "Commentaire"]
            ] = [nouvelle_equipe, nouvel_etat, nouveau_prete_a, nouveau_commentaire.strip()]

            synchroniser_outils()
            st.success(f"Mise à jour réussie pour {outil_select} dans Google Sheets !")
            st.rerun()
    else:
        st.warning("Aucun outil ne correspond à votre recherche.")
else:
    st.info("Aucun outil enregistré pour le moment.")