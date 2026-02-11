import streamlit as st
import json
import os
from datetime import datetime

# ========== วิธีที่ 1: เก็บ data ใน JSON file ==========

def save_calculation(data, filename="jpcp_calculations.json"):
    """บันทึก calculation ลงไฟล์ JSON"""
    # ดึงข้อมูลเดิมถ้ามี
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
    else:
        all_data = []
    
    # เพิ่มข้อมูลใหม่พร้อม timestamp
    data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    all_data.append(data)
    
    # บันทึกลง file
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    return True

def load_calculations(filename="jpcp_calculations.json"):
    """โหลด calculation ทั้งหมดจาก JSON"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# ========== วิธีที่ 2: ใช้ Streamlit Session State ==========

def init_session_state():
    """เริ่มต้น session state สำหรับเก็บ calculation"""
    if 'calculations' not in st.session_state:
        st.session_state.calculations = load_calculations()

# ========== ตัวอย่าง: JPCP Calculation App ==========

st.set_page_config(page_title="JPCP Calculator", layout="wide")
st.title("📐 JPCP Design Calculator - Local Storage")

init_session_state()

# === Tab สำหรับการคำนวณและประวัติ ===
tab1, tab2 = st.tabs(["คำนวณใหม่", "ประวัติการคำนวณ"])

with tab1:
    st.subheader("ข้อมูล JPCP")
    
    col1, col2 = st.columns(2)
    
    with col1:
        project_name = st.text_input("ชื่อโครงการ", value="Main Road STA 127+400")
        slab_thickness = st.selectbox(
            "ความหนาคอนกรีต (m)",
            [0.23, 0.25, 0.28, 0.30, 0.32, 0.35]
        )
        num_lanes = st.number_input("จำนวนเลน", min_value=2, max_value=4, value=4)
    
    with col2:
        median_type = st.selectbox(
            "ประเภทไหล่กลาง",
            ["Raised (ยกขึ้น)", "Depressed (ลดระดับ)", "Barrier"]
        )
        road_length = st.number_input("ความยาวถนน (m)", min_value=1.0, value=100.0)
        esal = st.number_input("ESAL (ล้าน)", min_value=0.1, value=5.0)
    
    # === คำนวณ ===
    if st.button("💾 คำนวณและบันทึก", type="primary"):
        
        # Dowel calculation (ตามตาราของอาจารย์)
        dowel_dia_map = {
            0.23: 30, 0.25: 32, 0.28: 35, 0.30: 38,
            0.32: 38, 0.35: 38
        }
        dowel_dia = dowel_dia_map[slab_thickness]
        
        # Transverse dowel per section
        transverse_dowel_per_section = {
            2: 15,  # 2L
            3: 25,  # 3L
            4: 33   # 4L (ประมาณ)
        }
        transverse_qty = transverse_dowel_per_section.get(num_lanes, 25)
        
        # คำนวณทั้งหมด
        num_sections = int(road_length / 4.5)  # 1 section ≈ 4.5m
        total_transverse = transverse_qty * num_sections
        total_longitudinal = int(road_length / 0.80) * 4  # LJ spacing
        
        # สร้าง calculation record
        calc_record = {
            "project_name": project_name,
            "slab_thickness": slab_thickness,
            "num_lanes": num_lanes,
            "median_type": median_type,
            "road_length": road_length,
            "esal": esal,
            "dowel_diameter": dowel_dia,
            "transverse_dowel": total_transverse,
            "longitudinal_dowel": total_longitudinal,
            "total_sections": num_sections
        }
        
        # บันทึก
        save_calculation(calc_record)
        st.session_state.calculations = load_calculations()
        
        st.success(f"✅ บันทึก {project_name} สำเร็จ!")
        
        # แสดงผล
        st.subheader("📊 ผลการคำนวณ")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("เส้นผ่าศูนย์ dowel", f"Ø{dowel_dia} mm")
        col2.metric("Transverse dowel รวม", total_transverse)
        col3.metric("Longitudinal dowel รวม", total_longitudinal)
        col4.metric("จำนวน section", num_sections)

with tab2:
    st.subheader("📋 ประวัติการคำนวณทั้งหมด")
    
    if st.session_state.calculations:
        # ตัวเลือกฟิลเตอร์
        filter_project = st.selectbox(
            "ค้นหาโครงการ",
            ["ทั้งหมด"] + 
            list(set([c["project_name"] for c in st.session_state.calculations]))
        )
        
        # ฟิลเตอร์ข้อมูล
        display_data = st.session_state.calculations
        if filter_project != "ทั้งหมด":
            display_data = [c for c in display_data 
                          if c["project_name"] == filter_project]
        
        # แสดงตาราง
        for idx, calc in enumerate(reversed(display_data)):
            with st.expander(
                f"🔹 {calc['project_name']} | {calc['timestamp']} | "
                f"{calc['num_lanes']}L | {calc['slab_thickness']}m"
            ):
                col1, col2, col3 = st.columns(3)
                
                col1.write(f"**ความยาว:** {calc['road_length']} m")
                col1.write(f"**ESAL:** {calc['esal']:.2f} ล้าน")
                col1.write(f"**ไหล่กลาง:** {calc['median_type']}")
                
                col2.write(f"**Dowel Ø:** {calc['dowel_diameter']} mm")
                col2.write(f"**Transverse:** {calc['transverse_dowel']} ก้าน")
                col2.write(f"**Longitudinal:** {calc['longitudinal_dowel']} ก้าน")
                
                col3.write(f"**Section:** {calc['total_sections']} ช่วง")
                
                # ปุ่มลบ
                if st.button(f"🗑️ ลบ", key=f"del_{idx}"):
                    st.session_state.calculations.pop(len(st.session_state.calculations)-1-idx)
                    save_calculation(None, "jpcp_calculations.json")
                    st.rerun()
        
        # ปุ่มโหลดไฟล์
        st.divider()
        if st.button("📥 ดาวน์โหลด JSON"):
            json_str = json.dumps(st.session_state.calculations, 
                                ensure_ascii=False, indent=2)
            st.download_button(
                label="Download jpcp_calculations.json",
                data=json_str,
                file_name="jpcp_calculations.json",
                mime="application/json"
            )
    else:
        st.info("ยังไม่มีการคำนวณ ให้เริ่มต้นจาก Tab 'คำนวณใหม่'")
