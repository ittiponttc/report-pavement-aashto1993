# =========================================================
# AASHTO 1993 Nomograph – Streamlit App
# with PDF & Word Export
# =========================================================

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Word
from docx import Document

# =========================================================
# Calibration (อ่านจากรูป Nomograph)
# =========================================================

CAL = {
    "Mr":  {"min": 1000, "max": 20000, "pmin": 850, "pmax": 350},
    "DSB": {"min": 4,    "max": 18,    "pmin": 180, "pmax": 720},
    "k":   {"min": 50,   "max": 1500,  "pmin": 820, "pmax": 1020}
}

# =========================================================
# Mapping Functions (Reusable)
# =========================================================

def log_map(v, vmin, vmax, pmin, pmax):
    return pmin + (np.log10(v)-np.log10(vmin)) / \
        (np.log10(vmax)-np.log10(vmin)) * (pmax-pmin)


def log_unmap(p, vmin, vmax, pmin, pmax):
    r = (p-pmin)/(pmax-pmin)
    return 10**(np.log10(vmin)+r*(np.log10(vmax)-np.log10(vmin)))

# =========================================================
# Streamlit UI
# =========================================================

st.title("AASHTO 1993 – Composite Modulus of Subgrade Reaction")

Mr = st.slider("Roadbed Resilient Modulus, Mr (psi)", 1000, 20000, 5000, step=500)
DSB = st.slider("Subbase Thickness, DSB (inch)", 4, 18, 10)

# =========================================================
# Calculate pixel positions
# =========================================================

x_dsb = log_map(DSB, **CAL["DSB"])
y_mr  = log_map(Mr,  **CAL["Mr"])

# Approximate k∞ from intersection (teaching use)
k_inf = log_unmap(x_dsb, **CAL["k"])

# =========================================================
# Plot Nomograph
# =========================================================

img = Image.open("nomograph.png")

fig, ax = plt.subplots(figsize=(7,7))
ax.imshow(img)
ax.axis("off")

ax.plot([x_dsb, x_dsb], [y_mr, 750], color="red", linewidth=2)
ax.plot([x_dsb, 1020], [y_mr, y_mr], color="red", linewidth=2)
ax.scatter(x_dsb, y_mr, color="red", s=80)

st.pyplot(fig)

st.success(f"Estimated k∞ ≈ {k_inf:,.0f} pci")

# =========================================================
# Export PDF
# =========================================================

def export_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("<b>AASHTO 1993 Nomograph Report</b>", styles["Title"]))
    content.append(Spacer(1, 12))
    content.append(Paragraph(f"Mr = {Mr:,.0f} psi", styles["Normal"]))
    content.append(Paragraph(f"DSB = {DSB:.1f} inch", styles["Normal"]))
    content.append(Paragraph(f"Composite k∞ ≈ {k_inf:,.0f} pci", styles["Normal"]))

    doc.build(content)
    buffer.seek(0)
    return buffer

# =========================================================
# Export Word
# =========================================================

def export_word():
    doc = Document()
    doc.add_heading("AASHTO 1993 Nomograph Report", level=1)
    doc.add_paragraph(f"Roadbed Resilient Modulus (Mr): {Mr:,.0f} psi")
    doc.add_paragraph(f"Subbase Thickness (DSB): {DSB:.1f} inch")
    doc.add_paragraph(f"Composite Modulus of Subgrade Reaction (k∞): {k_inf:,.0f} pci")

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# =========================================================
# Download Buttons
# =========================================================

col1, col2 = st.columns(2)

with col1:
    st.download_button(
        "📄 Download PDF Report",
        export_pdf(),
        file_name="AASHTO_Nomograph_Report.pdf",
        mime="application/pdf"
    )

with col2:
    st.download_button(
        "📝 Download Word Report",
        export_word(),
        file_name="AASHTO_Nomograph_Report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
