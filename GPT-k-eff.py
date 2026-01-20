# =========================================================
# AASHTO 1993 Nomograph – FINAL v4
# Calibrate Mode + Save/Load Calibration
# =========================================================

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO
import json

# ---------------- PDF (safe import) ----------------
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

# ---------------- Word ----------------
from docx import Document
from docx.shared import Inches

# =========================================================
# Page config
# =========================================================

st.set_page_config(
    page_title="AASHTO 1993 Nomograph",
    layout="centered"
)

st.title("AASHTO 1993 – Composite Modulus of Subgrade Reaction")

# =========================================================
# Mapping functions (log scale)
# =========================================================

def log_map(v, vmin, vmax, pmin, pmax):
    return pmin + (np.log10(v) - np.log10(vmin)) / \
        (np.log10(vmax) - np.log10(vmin)) * (pmax - pmin)


def log_unmap(p, vmin, vmax, pmin, pmax):
    r = (p - pmin) / (pmax - pmin)
    return 10 ** (np.log10(vmin) + r * (np.log10(vmax) - np.log10(vmin)))

# =========================================================
# Mode selection
# =========================================================

mode = st.radio("Mode", ["Normal Mode", "Calibrate Mode"])

# =========================================================
# Load Nomograph Image
# =========================================================

st.subheader("Nomograph Image")

uploaded_file = st.file_uploader(
    "Upload AASHTO Nomograph Image (PNG / JPG)",
    type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    img = Image.open(uploaded_file)
else:
    try:
        img = Image.open("nomograph.png")
    except FileNotFoundError:
        st.error("❌ กรุณาอัปโหลดภาพ Nomograph")
        st.stop()

# =========================================================
# Paper template setup
# =========================================================

IMG_W, IMG_H = img.size
paper_w, paper_h = 100, 70

scale = paper_h / IMG_H
img_w_scaled = IMG_W * scale

x0 = (paper_w - img_w_scaled) / 2
x1 = x0 + img_w_scaled
y0 = 0
y1 = paper_h

# =========================================================
# Session state for calibration
# =========================================================

if "calib_points" not in st.session_state:
    st.session_state.calib_points = {
        "Mr": [],
        "DSB": [],
        "k": []
    }

if "CAL" not in st.session_state:
    st.session_state.CAL = {}

# =========================================================
# Plot base figure
# =========================================================

fig, ax = plt.subplots(figsize=(11.7, 8.3))
ax.set_facecolor("white")

ax.imshow(
    img,
    extent=[x0, x1, y0, y1],
    aspect="auto"
)

ax.plot([0,100,100,0,0], [0,0,70,70,0],
        color="black", linewidth=1.2)

ax.set_xlim(0,100)
ax.set_ylim(0,70)
ax.axis("off")

# =========================================================
# Show calibration points
# =========================================================

colors = {"Mr": "blue", "DSB": "green", "k": "purple"}

for key in st.session_state.calib_points:
    for p in st.session_state.calib_points[key]:
        ax.scatter(p[0], p[1], color=colors[key], s=60, zorder=5)

# =========================================================
# Normal Mode
# =========================================================

if mode == "Normal Mode" and st.session_state.CAL:

    Mr = st.slider("Roadbed Resilient Modulus, Mr (psi)", 1000, 20000, 6000, step=500)
    DSB = st.slider("Subbase Thickness, DSB (inch)", 4, 18, 14)

    CAL_MR = st.session_state.CAL["Mr"]
    CAL_DSB = st.session_state.CAL["DSB"]
    CAL_K = st.session_state.CAL["k"]

    x_dsb = log_map(DSB, **CAL_DSB)
    y_mr = log_map(Mr, **CAL_MR)
    k_inf = log_unmap(x_dsb, **CAL_K)

    ax.plot([x_dsb, x_dsb], [y_mr, y0 + 5], color="red", linewidth=2)
    ax.plot([x_dsb, CAL_K["pmax"]], [y_mr, y_mr], color="red", linewidth=2)
    ax.scatter(x_dsb, y_mr, color="red", s=90, zorder=6)

    st.success(f"Estimated composite k∞ ≈ {k_inf:,.0f} pci")

elif mode == "Normal Mode":
    st.info("⚠️ กรุณา Calibrate ก่อนใช้งาน Normal Mode")

# =========================================================
# Calibrate Mode
# =========================================================

if mode == "Calibrate Mode":

    st.markdown("### Calibrate by clicking coordinates")

    click = st.data_editor(
    {"x": [50.0], "y": [35.0]},
    num_rows=1,
    use_container_width=True,
    key="click_input"
)


    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Add Mr point"):
            st.session_state.calib_points["Mr"].append(
                (click["x"][0], click["y"][0])
            )

    with col2:
        if st.button("Add DSB point"):
            st.session_state.calib_points["DSB"].append(
                (click["x"][0], click["y"][0])
            )

    with col3:
        if st.button("Add k point"):
            st.session_state.calib_points["k"].append(
                (click["x"][0], click["y"][0])
            )

    # Build calibration
    if (
        len(st.session_state.calib_points["Mr"]) >= 2 and
        len(st.session_state.calib_points["DSB"]) >= 2 and
        len(st.session_state.calib_points["k"]) >= 2
    ):
        st.success("Calibration points complete")

        if st.button("Build Calibration"):
            st.session_state.CAL = {
                "Mr": {
                    "vmin": 1000,
                    "vmax": 20000,
                    "pmin": st.session_state.calib_points["Mr"][1][1],
                    "pmax": st.session_state.calib_points["Mr"][0][1]
                },
                "DSB": {
                    "vmin": 4,
                    "vmax": 18,
                    "pmin": st.session_state.calib_points["DSB"][0][0],
                    "pmax": st.session_state.calib_points["DSB"][1][0]
                },
                "k": {
                    "vmin": 50,
                    "vmax": 2000,
                    "pmin": st.session_state.calib_points["k"][0][0],
                    "pmax": st.session_state.calib_points["k"][1][0]
                }
            }
            st.success("Calibration built successfully")

# =========================================================
# Save / Load Calibration
# =========================================================

st.subheader("Calibration File")

if st.session_state.CAL:
    calib_json = json.dumps(st.session_state.CAL, indent=2)
    st.download_button(
        "💾 Save Calibration (.json)",
        calib_json,
        file_name="aashto_nomograph_calibration.json",
        mime="application/json"
    )

uploaded_calib = st.file_uploader(
    "Load Calibration File (.json)",
    type=["json"]
)

if uploaded_calib is not None:
    st.session_state.CAL = json.load(uploaded_calib)
    st.success("Calibration loaded successfully")

# =========================================================
# Render plot
# =========================================================

st.pyplot(fig)
