import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# =========================================================
# 1) CONFIG & DATA
# =========================================================

st.set_page_config(
    page_title="Pavement Structure – Streamlit",
    page_icon="🛣️",
    layout="centered"
)

# Mapping D (inch) → cm
D_MAP = {10: 25, 11: 28, 12: 30, 13: 32, 14: 35}

# Material Library (Default ตามภาพ)
MATERIAL_LIBRARY = {
    "AC": {
        "label": {"ไทย": "ผิวทางลาดยาง AC", "English": "AC Surface"},
        "MR": 2500,
        "color": "#2C3E50"
    },
    "CTB": {
        "label": {"ไทย": "พื้นทางซีเมนต์ CTB", "English": "Cement Treated Base"},
        "MR": 1200,
        "color": "#7F8C8D"
    },
    "CRB": {
        "label": {"ไทย": "หินคลุก CBR 80%", "English": "Crushed Rock Base"},
        "MR": 350,
        "color": "#CACFD2"
    },
    "CONCRETE": {
        "label": {"ไทย": "แผ่นคอนกรีต", "English": "Concrete Slab"},
        "color": "#5DADE2"
    }
}

LABELS = {
    "title": {"ไทย": "รูปตัดโครงสร้างชั้นทาง", "English": "Pavement Structure"},
    "total": {"ไทย": "ความหนารวมโครงสร้างชั้นทาง", "English": "Total Pavement Thickness"}
}

# =========================================================
# 2) DRAWING FUNCTION
# =========================================================

def draw_pavement_structure(layers, lang):
    total_thk = sum(l["thickness"] for l in layers)

    fig, ax = plt.subplots(figsize=(4, 7))

    x0 = 0.4
    width = 0.6
    y = 0

    # วาดจากล่างขึ้นบน
    for layer in reversed(layers):
        rect = patches.Rectangle(
            (x0, y),
            width,
            layer["thickness"],
            facecolor=layer["color"],
            edgecolor="black",
            linewidth=1.5
        )
        ax.add_patch(rect)

        # ความหนาในแท่ง
        ax.text(
            x0 + width / 2,
            y + layer["thickness"] / 2,
            f'{layer["thickness"]:.1f} cm',
            ha='center',
            va='center',
            fontsize=10,
            fontweight='bold',
            color='white' if layer["key"] in ["CONCRETE", "AC"] else 'black'
        )

        # ชื่อวัสดุด้านซ้าย
        ax.text(
            x0 - 0.05,
            y + layer["thickness"] / 2,
            MATERIAL_LIBRARY[layer["key"]]["label"][lang],
            ha='right',
            va='center',
            fontsize=9
        )

        y += layer["thickness"]

    # Scale bar แนวดิ่ง
    ax.annotate(
        '',
        xy=(1.15, total_thk),
        xytext=(1.15, 0),
        arrowprops=dict(arrowstyle='<->', lw=1.8, color='red')
    )
    ax.text(
        1.18,
        total_thk / 2,
        f"{total_thk:.1f} cm",
        va='center',
        fontsize=9,
        color='red'
    )

    # Title
    ax.set_title(LABELS["title"][lang], fontsize=12, fontweight='bold', pad=10)

    # Total thickness box
    ax.text(
        x0 + width / 2,
        -6,
        f"{LABELS['total'][lang]}: {total_thk:.1f} cm",
        ha='center',
        va='center',
        fontsize=10,
        fontweight='bold',
        bbox=dict(boxstyle="round", facecolor="#FFF3CD", edgecolor="orange")
    )

    ax.set_xlim(0, 1.4)
    ax.set_ylim(-10, total_thk + 5)
    ax.axis("off")

    plt.tight_layout()
    return fig

# =========================================================
# 3) STREAMLIT UI
# =========================================================

st.title("🛣️ Pavement Structure (Streamlit)")

# ภาษา
lang = st.radio(
    "Language / ภาษา",
    ["ไทย", "English"],
    horizontal=True
)

st.markdown("---")

# D selection
d_in = st.selectbox(
    "Concrete Slab Thickness D (inch)",
    [10, 11, 12, 13, 14],
    index=2
)
d_cm = D_MAP[d_in]
st.info(f"Concrete Slab = {d_in} in ≈ {d_cm} cm")

st.markdown("---")

# Layer thickness input
st.subheader("Pavement Layers")

ac_thk = st.number_input("AC Surface Thickness (cm)", 0, 20, 5)
ctb_thk = st.number_input("Cement Treated Base Thickness (cm)", 0, 40, 20)
crb_thk = st.number_input("Crushed Rock Base Thickness (cm)", 0, 40, 15)

st.markdown("---")

# Subgrade CBR
st.subheader("Subgrade Properties")

cbr = st.number_input(
    "CBR of Subgrade (%)",
    min_value=2,
    max_value=50,
    value=10,
    step=1
)

st.caption("CBR ใช้ประกอบการพิจารณา k_eff / MR ในขั้นตอนออกแบบ AASHTO 1993")

# =========================================================
# 4) BUILD LAYERS & DRAW
# =========================================================

layers = [
    {"key": "CONCRETE", "thickness": d_cm, "color": MATERIAL_LIBRARY["CONCRETE"]["color"]},
    {"key": "AC", "thickness": ac_thk, "color": MATERIAL_LIBRARY["AC"]["color"]},
    {"key": "CTB", "thickness": ctb_thk, "color": MATERIAL_LIBRARY["CTB"]["color"]},
    {"key": "CRB", "thickness": crb_thk, "color": MATERIAL_LIBRARY["CRB"]["color"]},
]

st.markdown("---")
st.subheader("📐 Pavement Structure Diagram")

fig = draw_pavement_structure(layers, lang)
st.pyplot(fig)

# =========================================================
# 5) FOOTNOTE
# =========================================================

st.markdown("---")
st.caption(
    "ใช้เพื่อการเรียนการสอน – Pavement Engineering | "
    "สามารถต่อยอดสู่ AASHTO 1993 Rigid Pavement Design ได้ทันที"
)
