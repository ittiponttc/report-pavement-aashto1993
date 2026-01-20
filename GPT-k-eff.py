# =========================================================
# AASHTO 1993 Nomograph – FINAL STABLE VERSION
# Export PDF + Word | Streamlit Cloud Ready
# =========================================================

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO

# ---------------- PDF (safe import) ----------------
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

# ---------------- Word ----------------
from docx import Document

# =========================================================
# Calibration (อ่านจาก Nomograph จริง)
# =========================================================

CAL = {
    "Mr":  {"vmin": 1000, "vmax": 20000, "pmin": 850, "pmax": 350},
    "DSB": {"vmin": 4,    "vmax": 18,    "pmin": 180, "pmax": 720},
    "k":   {"vmin": 50,   "vmax": 1500,  "pmin": 820, "pmax": 1020}
}

# =========================================================
# Mapping Functions (หัวใจของระบบ)
# =========================================================

def log_map(v, vmin, vmax, pmin, pmax):
    return pmin + (np.log10(v) - np.log10(vmin)) / \
        (np.log10(vmax) - np.log10(vmin)) * (pmax - pmin)


def log_unmap(p, vmin, vmax, pmin, pmax):
    r = (p - pmin) / (pmax - pmin)
    return 10 ** (np.log10(vmin) + r * (np.log10(vmax) - np.log10(vmin)))

# =========================================================
# Streamlit UI
# =========================================================

st.set_page_config(page_title="AASHTO 1993 Nomograph", layout="centered")
st.title("AASHTO 1993 – Composite Modulus of Subgrade Reaction")

Mr = st.slider(
    "Roadbed Resilient Modulus, Mr (psi)",
    1000, 20000, 5000, step=500
)

DSB = st.slider(
    "Subbase Thickness, DSB (inch)",
    4, 18, 10
)

# =========================================================
# Coordinate Mapping
# =========================================================

x_dsb = log_map(
    DSB,
    CAL["DSB"]["vmin"],
    CAL["DSB"]["vmax"],
    CAL["DSB"]["pmin"],
    CAL["DSB"]["pmax"]
)

y_mr = log_map(
    Mr,
    CAL["Mr"]["vmin"],
    CAL["Mr"]["vmax"],
    CAL["Mr"]["pmin"],
    CAL["Mr"]["pmax"]
)

k_inf = log_unmap(
    x_dsb,
    CAL["k"]["vmin"],
    CAL["k"]["vmax"],
    CAL["k"]["pmin"],
    CAL["k"]["pmax"]
)

# =========================================================
# Plot Nomograph
# =========================================================
# =========================================================
# Plot Nomograph with Paper Template (A4 Landscape)
# =========================================================

fig, ax = plt.subplots(figsize=(11.7, 8.3))  # A4 landscape (inch)

# พื้นหลังขาว = กระดาษ
ax.set_facecolor("white")

# วางภาพ nomograph ให้อยู่ในกรอบ
ax.imshow(
    img,
    extent=[0, 100, 0, 70],
    aspect="auto"
)

# วาดกรอบกระดาษ
ax.plot([0,100,100,0,0], [0,0,70,70,0],
        color="black", linewidth=1.5)

ax.axis("off")

# =========================================================
# Load Nomograph Image (Cloud-safe)
# =========================================================

st.subheader("Nomograph Image")

uploaded_file = st.file_uploader(
    "Upload AASHTO Nomograph Image (PNG/JPG)",
    type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    img = Image.open(uploaded_file)
else:
    try:
        img = Image.open("nomograph.png")
    except FileNotFoundError:
        st.error(
            "❌ nomograph.png not found.\n\n"
            "Please upload the nomograph image using the uploader above."
        )
        st.stop()


fig, ax = plt.subplots(figsize=(7, 7))
ax.imshow(img)
ax.axis("off")

# เส้นอ่านค่า
ax.plot([x_dsb, x_dsb], [y_mr, 750], color="red", linewidth=2)
ax.plot([x_dsb, 1020], [y_mr, y_mr], color="red", linewidth=2)
ax.scatter(x_dsb, y_mr, color="red", s=80)

st.pyplot(fig)

st.success(f"Estimated composite k∞ ≈ {k_inf:,.0f} pci")

# =========================================================
# Export PDF
# =========================================================

def export_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    content = [
        Paragraph("<b>AASHTO 1993 Nomograph Report</b>", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Roadbed Resilient Modulus (Mr): {Mr:,.0f} psi", styles["Normal"]),
        Paragraph(f"Subbase Thickness (DSB): {DSB:.1f} inch", styles["Normal"]),
        Paragraph(f"Composite Modulus of Subgrade Reaction (k∞): {k_inf:,.0f} pci", styles["Normal"]),
    ]

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

st.subheader("Export Report")

col1, col2 = st.columns(2)

with col1:
    if REPORTLAB_OK:
        st.download_button(
            "📄 Download PDF",
            export_pdf(),
            file_name="AASHTO1993_Nomograph_Report.pdf",
            mime="application/pdf"
        )
    else:
        st.warning("PDF export disabled (reportlab not installed)")

with col2:
    st.download_button(
        "📝 Download Word",
        export_word(),
        file_name="AASHTO1993_Nomograph_Report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
