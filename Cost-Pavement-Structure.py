import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io

# ==========================================
# 1. ข้อมูลราคาอ้างอิง (Default Data)
# ==========================================
AC_PRICE_TABLE = {
    'AC 5 cm.': {'price': 220, 'unit': 'ตร.ม.'},
    'AC 10 cm. (5+5)': {'price': 430, 'unit': 'ตร.ม.'},
    'AC 15 cm. (5+10)': {'price': 630, 'unit': 'ตร.ม.'}
}

CONCRETE_PRICE_TABLE = {
    'PCC 20 cm.': {'price': 550, 'unit': 'ตร.ม.'},
    'PCC 25 cm.': {'price': 680, 'unit': 'ตร.ม.'},
    'PCC 28 cm.': {'price': 760, 'unit': 'ตร.ม.'}
}

BASE_MATERIAL_PRICES = {
    'Crushed Stone Base (หินคลุก)': 750,
    'Soil Cement Base (ดินซีเมนต์)': 550,
    'Cement Stabilized Base (หินคลุกผสมซีเมนต์)': 950,
    'Sand Backfill (ทรายรองพื้น)': 450,
    'Selected Material A (วัสดุคัดเลือก ก)': 350
}

# ==========================================
# 2. ฟังก์ชันช่วยคำนวณและ UI (Helper Functions)
# ==========================================

def get_default_ac1_layers():
    return [
        {"name": "Surface: Asphalt Concrete", "thickness": 0.10, "type": "AC", "category": "ac_prices"},
        {"name": "Base: Crushed Stone", "thickness": 0.20, "type": "Volume", "category": "Crushed Stone Base (หินคลุก)"},
        {"name": "Subbase: Selected Material A", "thickness": 0.20, "type": "Volume", "category": "Selected Material A (วัสดุคัดเลือก ก)"}
    ]

def render_layer_editor(layers, key_suffix, width, length):
    new_layers = []
    area = width * 1000 * length
    for i, layer in enumerate(layers):
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            name = st.text_input(f"ชื่อชั้นที่ {i+1}", value=layer['name'], key=f"n_{i}_{key_suffix}")
        with col2:
            thick = st.number_input(f"หนา (ม.)", value=layer['thickness'], format="%.3f", key=f"t_{i}_{key_suffix}")
        
        # คำนวณราคาเบื้องต้นจาก Library ใน Session State
        price = 0
        if layer['type'] == "AC":
            price = st.session_state['price_library']['ac_prices'].get(name, {'price': 0})['price']
            cost = price * area
        else:
            price = st.session_state['price_library']['base_prices'].get(layer['category'], 0)
            cost = price * (area * thick)
            
        with col3:
            st.write(f"ราคาประมาณการ:")
            st.write(f"{cost:,.2f} บาท")
            
        new_layers.append({"name": name, "thickness": thick, "type": layer['type'], "category": layer['category'], "cost": cost})
    return new_layers

# ==========================================
# 3. Main Application
# ==========================================

def main():
    st.set_page_config(page_title="Pavement Cost Analysis", layout="wide")
    
    # ส่วนหัวโปรแกรม
    st.markdown("""
        <div style="background-color:#1E3A5F;padding:10px;border-radius:10px">
        <h1 style="color:white;text-align:center;">โปรแกรมวิเคราะห์ค่าก่อสร้างชั้นทาง</h1>
        </div><br>
    """, unsafe_allow_html=True)

    # Initialize Session State สำหรับราคา
    if 'price_library' not in st.session_state:
        st.session_state['price_library'] = {
            'ac_prices': AC_PRICE_TABLE,
            'concrete_prices': CONCRETE_PRICE_TABLE,
            'base_prices': BASE_MATERIAL_PRICES
        }

    # สร้าง Tab แค่ 2 อันตามต้องการ
    tab1, tab2 = st.tabs(["📚 Library ราคาวัสดุ", "🏗️ คำนวณค่าก่อสร้าง"])

    # --- Tab 1: Library ราคาวัสดุ ---
    with tab1:
        st.subheader("🛠️ แก้ไขราคาวัสดุกลาง")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**ราคาผิวทาง (บาท/ตร.ม.)**")
            df_ac = pd.DataFrame(st.session_state['price_library']['ac_prices']).T
            edit_ac = st.data_editor(df_ac, use_container_width=True)
            st.session_state['price_library']['ac_prices'] = edit_ac.to_dict('index')
        
        with c2:
            st.write("**ราคาวัสดุชั้นพื้นทาง (บาท/ลบ.ม.)**")
            df_base = pd.Series(st.session_state['price_library']['base_prices']).to_frame(name='ราคา')
            edit_base = st.data_editor(df_base, use_container_width=True)
            st.session_state['price_library']['base_prices'] = edit_base['ราคา'].to_dict()

    # --- Tab 2: คำนวณค่าก่อสร้าง ---
    with tab2:
        col_in1, col_in2 = st.columns(2)
        with col_in1:
            road_l = st.number_input("ระยะทาง (กม.)", value=1.0)
            road_w = st.number_input("ความกว้างผิวทาง (ม.)", value=7.0)
        with col_in2:
            shoulder_w = st.number_input("ความกว้างไหล่ทาง (ม./ข้าง)", value=2.5)
            total_w = road_w + (shoulder_w * 2)
            
        st.info(f"พื้นที่ก่อสร้างทั้งหมด: {total_w * 1000 * road_l:,.2f} ตร.ม.")
        
        st.divider()
        
        # ตัวอย่างการเลือกโครงสร้าง (Simplified สำหรับตัวอย่าง)
        struct_type = st.selectbox("เลือกรูปแบบโครงสร้าง", ["AC1: Asphalt on Crushed Stone", "Custom Structure"])
        
        if "AC1" in struct_type:
            layers = get_default_ac1_layers()
        else:
            layers = [] # กรณีเลือก Custom
            
        updated_layers = render_layer_editor(layers, "main", total_w, road_l)
        
        # สรุปงบประมาณ
        total_cost = sum(l['cost'] for l in updated_layers)
        
        st.markdown(f"""
            <div style="background-color:#f0f8ff; padding:20px; border-radius:10px; border-left: 5px solid #2E86AB;">
                <h3>งบประมาณรวมทั้งโครงการ</h3>
                <h2 style="color:#2E86AB;">{total_cost:,.2f} บาท</h2>
                <p>เฉลี่ย {total_cost/road_l:,.2f} บาท ต่อกิโลเมตร</p>
            </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
