"""
ESAL Calculator - AASHTO 1993
โปรแกรมคำนวณปริมาณเพลาเดี่ยวมาตรฐานเทียบเท่า (Equivalent Single Axle Load)
สำหรับผิวทาง Rigid Pavement และ Flexible Pavement
ตามมาตรฐาน AASHTO Guide for Design of Pavement Structures (1993)

พัฒนาโดย: รศ.ดร.อิทธิพล มีผล ภาควิชาครุศาสตร์โยธา มจพ.
"""

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# ============================================================
# ข้อมูลรถบรรทุก 6 ชนิดตามกรมทางหลวงประเทศไทย
# ============================================================
TRUCKS = {
    'MB': {
        'desc': 'Medium Bus (รถโดยสารขนาดกลาง)',
        'axles': [
            {'name': 'เพลาหน้า', 'load_ton': 4.0, 'type': 'Single'},
            {'name': 'เพลาหลัง', 'load_ton': 11.0, 'type': 'Tandem'}
        ]
    },
    'HB': {
        'desc': 'Heavy Bus (รถโดยสารขนาดใหญ่)',
        'axles': [
            {'name': 'เพลาหน้า', 'load_ton': 5.0, 'type': 'Single'},
            {'name': 'เพลาหลัง', 'load_ton': 20.0, 'type': 'Tandem'}
        ]
    },
    'MT': {
        'desc': 'Medium Truck (รถบรรทุกขนาดกลาง)',
        'axles': [
            {'name': 'เพลาหน้า', 'load_ton': 4.0, 'type': 'Single'},
            {'name': 'เพลาหลัง', 'load_ton': 11.0, 'type': 'Single'}
        ]
    },
    'HT': {
        'desc': 'Heavy Truck (รถบรรทุกขนาดใหญ่)',
        'axles': [
            {'name': 'เพลาหน้า', 'load_ton': 5.0, 'type': 'Single'},
            {'name': 'เพลาหลัง', 'load_ton': 20.0, 'type': 'Tandem'}
        ]
    },
    'STR': {
        'desc': 'Semi-Trailer (รถกึ่งพ่วง)',
        'axles': [
            {'name': 'เพลาหน้า', 'load_ton': 5.0, 'type': 'Single'},
            {'name': 'เพลาหลัง', 'load_ton': 20.0, 'type': 'Tandem'},
            {'name': 'เพลาพ่วงหลัง', 'load_ton': 20.0, 'type': 'Tandem'}
        ]
    },
    'TR': {
        'desc': 'Full Trailer (รถพ่วง)',
        'axles': [
            {'name': 'เพลาหน้า', 'load_ton': 5.0, 'type': 'Single'},
            {'name': 'เพลาหลัง', 'load_ton': 20, 'type': 'Tandem'},
            {'name': 'เพลาพ่วงหน้า', 'load_ton': 11, 'type': 'Single'},
            {'name': 'เพลาพ่วงหลัง', 'load_ton': 11, 'type': 'Single'}
        ]
    }
}

# ============================================================
# ตาราง Truck Factor คำนวณตาม AASHTO 1993
# อัพเดตค่าจากไฟล์ Truck_Factor_Calculator.xlsx
# เพิ่ม D=15,16 สำหรับ Rigid และ SN=8,9 สำหรับ Flexible
# ============================================================

# Rigid Pavement - pt = 2.0
TRUCK_FACTORS_RIGID_PT20 = {
    'MB':  {10: 0.731742, 11: 0.731339, 12: 0.731151, 13: 0.731059, 14: 0.731012, 15: 0.730987, 16: 0.730971},
    'HB':  {10: 1.462652, 11: 1.464597, 12: 1.465524, 13: 1.465981, 14: 1.466216, 15: 1.466340, 16: 1.466406},
    'MT':  {10: 3.718199, 11: 3.742581, 12: 3.754803, 13: 3.760977, 14: 3.764184, 15: 3.765855, 16: 3.766727},
    'HT':  {10: 6.125043, 11: 6.204343, 12: 6.247170, 13: 6.269632, 14: 6.281529, 15: 6.287867, 16: 6.291257},
    'STR': {10: 12.128867, 11: 12.287718, 12: 12.373488, 13: 12.418469, 14: 12.442292, 15: 12.454956, 16: 12.461738},
    'TR':  {10: 13.466316, 11: 13.594592, 12: 13.661961, 13: 13.696817, 14: 13.715152, 15: 13.724934, 16: 13.730167}
}

# Rigid Pavement - pt = 2.5
TRUCK_FACTORS_RIGID_PT25 = {
    'MB':  {10: 0.732709, 11: 0.731812, 12: 0.731393, 13: 0.731189, 14: 0.731085, 15: 0.731029, 16: 0.730998},
    'HB':  {10: 1.457942, 11: 1.462254, 12: 1.464313, 13: 1.465329, 14: 1.465850, 15: 1.466125, 16: 1.466272},
    'MT':  {10: 3.657799, 11: 3.711341, 12: 3.738346, 13: 3.752027, 14: 3.759145, 15: 3.762869, 16: 3.764817},
    'HT':  {10: 5.921064, 11: 6.092776, 12: 6.186668, 13: 6.236237, 14: 6.262582, 15: 6.276617, 16: 6.284134},
    'STR': {10: 11.720309, 11: 12.064293, 12: 12.252335, 13: 12.351598, 14: 12.404353, 15: 12.432524, 16: 12.447620},
    'TR':  {10: 13.141034, 11: 13.420301, 12: 13.568419, 13: 13.645455, 14: 13.686091, 15: 13.707787, 16: 13.719438}
}

# Rigid Pavement - pt = 3.0
TRUCK_FACTORS_RIGID_PT30 = {
    'MB':  {10: 0.733958, 11: 0.732422, 12: 0.731706, 13: 0.731357, 14: 0.731179, 15: 0.731084, 16: 0.731033},
    'HB':  {10: 1.451898, 11: 1.459241, 12: 1.462753, 13: 1.464488, 14: 1.465379, 15: 1.465849, 16: 1.466101},
    'MT':  {10: 3.581408, 11: 3.671458, 12: 3.717236, 13: 3.740520, 14: 3.752660, 15: 3.759033, 16: 3.762385},
    'HT':  {10: 5.668347, 11: 5.951971, 12: 6.109552, 13: 6.193451, 14: 6.238241, 15: 6.262146, 16: 6.274979},
    'STR': {10: 11.214096, 11: 11.782308, 12: 12.097912, 13: 12.265925, 14: 12.355613, 15: 12.403556, 16: 12.429280},
    'TR':  {10: 12.734883, 11: 13.199416, 12: 13.448924, 13: 13.579571, 14: 13.648731, 15: 13.685766, 16: 13.705646}
}

# Flexible Pavement - pt = 2.0
TRUCK_FACTORS_FLEX_PT20 = {
    'MB':  {4: 0.423803, 5: 0.406999, 6: 0.396430, 7: 0.391017, 8: 0.388028, 9: 0.386360},
    'HB':  {4: 0.840845, 5: 0.823464, 6: 0.811339, 7: 0.804852, 8: 0.801282, 9: 0.799233},
    'MT':  {4: 3.529011, 5: 3.598168, 6: 3.719257, 7: 3.810681, 8: 3.874256, 9: 3.916863},
    'HT':  {4: 3.332846, 5: 3.384895, 6: 3.458092, 7: 3.508785, 8: 3.541983, 9: 3.562854},
    'STR': {4: 6.537851, 5: 6.649420, 6: 6.800056, 7: 6.903531, 8: 6.971366, 9: 7.014261},
    'TR':  {4: 10.291092, 5: 10.488813, 6: 10.808050, 7: 11.043444, 8: 11.203523, 9: 11.310117}
}

# Flexible Pavement - pt = 2.5
TRUCK_FACTORS_FLEX_PT25 = {
    'MB':  {4: 0.478779, 5: 0.436804, 6: 0.411572, 7: 0.398978, 8: 0.392292, 9: 0.388607},
    'HB':  {4: 0.900196, 5: 0.857979, 6: 0.829541, 7: 0.814598, 8: 0.806248, 9: 0.801378},
    'MT':  {4: 3.069453, 5: 3.203842, 6: 3.451114, 7: 3.645241, 8: 3.779066, 9: 3.869188},
    'HT':  {4: 3.053625, 5: 3.157524, 6: 3.311765, 7: 3.421800, 8: 3.494667, 9: 3.541837},
    'STR': {4: 5.955718, 5: 6.182789, 6: 6.501567, 7: 6.726542, 8: 6.874756, 9: 6.970223},
    'TR':  {4: 9.069826, 5: 9.462000, 6: 10.120276, 7: 10.622935, 8: 10.967259, 9: 11.196528}
}

# Flexible Pavement - pt = 3.0
TRUCK_FACTORS_FLEX_PT30 = {
    'MB':  {4: 0.565037, 5: 0.480643, 6: 0.432964, 7: 0.409996, 8: 0.398128, 9: 0.391536},
    'HB':  {4: 0.989302, 5: 0.907358, 6: 0.854877, 7: 0.827976, 8: 0.813115, 9: 0.804484},
    'MT':  {4: 2.552540, 5: 2.742623, 6: 3.120508, 7: 3.433469, 8: 3.657896, 9: 3.812063},
    'HT':  {4: 2.728486, 5: 2.879854, 6: 3.125499, 7: 3.308196, 8: 3.432738, 9: 3.513580},
    'STR': {4: 5.266321, 5: 5.609502, 6: 6.120685, 7: 6.495126, 8: 6.750547, 9: 6.915832},
    'TR':  {4: 7.671306, 5: 8.245291, 6: 9.265343, 7: 10.082089, 8: 10.658949, 9: 11.046207}
}


def get_default_truck_factor(truck_code, pavement_type, pt, param):
    """ดึงค่า Truck Factor เริ่มต้นจากตาราง"""
    if pavement_type == 'rigid':
        if pt == 2.0:
            return TRUCK_FACTORS_RIGID_PT20[truck_code][param]
        elif pt == 2.5:
            return TRUCK_FACTORS_RIGID_PT25[truck_code][param]
        else:  # pt == 3.0
            return TRUCK_FACTORS_RIGID_PT30[truck_code][param]
    else:  # flexible
        if pt == 2.0:
            return TRUCK_FACTORS_FLEX_PT20[truck_code][param]
        elif pt == 2.5:
            return TRUCK_FACTORS_FLEX_PT25[truck_code][param]
        else:  # pt == 3.0
            return TRUCK_FACTORS_FLEX_PT30[truck_code][param]


def calculate_esal(traffic_df, truck_factors, lane_factor=0.5, direction_factor=1.0):
    """คำนวณ ESAL จากข้อมูลปริมาณจราจร"""
    results = []
    total_esal = 0
    
    for idx, row in traffic_df.iterrows():
        year = row.get('Year', idx + 1)
        year_esal = 0
        year_data = {'Year': year}
        
        for code in TRUCKS.keys():
            if code in traffic_df.columns:
                aadt = row[code]
                tf = truck_factors[code]
                esal = aadt * tf * lane_factor * direction_factor * 365
                year_data[f'{code}_ADT'] = aadt
                year_data[f'{code}_TF'] = tf
                year_data[f'{code}_ESAL'] = esal
                year_esal += esal
        
        year_data['Total_ESAL'] = year_esal
        total_esal += year_esal
        results.append(year_data)
    
    return pd.DataFrame(results), total_esal


def create_template():
    """สร้าง Template Excel สำหรับอัพโหลดข้อมูล"""
    base = {'MB': 120, 'HB': 60, 'MT': 250, 'HT': 180, 'STR': 120, 'TR': 100}
    growth_rate = 1.045
    
    data = {'Year': list(range(1, 21))}
    for code in base.keys():
        data[code] = [int(base[code] * (growth_rate ** i)) for i in range(20)]
    
    return pd.DataFrame(data)


def to_excel(df):
    """แปลง DataFrame เป็น Excel bytes"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Traffic Data')
    return output.getvalue()


def get_all_truck_factors_table(pavement_type, pt):
    """สร้างตาราง Truck Factor ทั้งหมด"""
    data = []
    
    if pavement_type == 'rigid':
        params = [10, 11, 12, 13, 14, 15, 16]
        param_label = 'D'
        if pt == 2.0:
            tf_table = TRUCK_FACTORS_RIGID_PT20
        elif pt == 2.5:
            tf_table = TRUCK_FACTORS_RIGID_PT25
        else:
            tf_table = TRUCK_FACTORS_RIGID_PT30
    else:
        params = [4, 5, 6, 7, 8, 9]
        param_label = 'SN'
        if pt == 2.0:
            tf_table = TRUCK_FACTORS_FLEX_PT20
        elif pt == 2.5:
            tf_table = TRUCK_FACTORS_FLEX_PT25
        else:
            tf_table = TRUCK_FACTORS_FLEX_PT30
    
    for code in TRUCKS.keys():
        row = {'ประเภท': code, 'รายละเอียด': TRUCKS[code]['desc']}
        for p in params:
            col_name = f'{param_label}={p}"' if pavement_type == 'rigid' else f'{param_label}={p}'
            row[col_name] = f"{tf_table[code][p]:.4f}"
        data.append(row)
    
    return pd.DataFrame(data)


# ============================================================
# Streamlit App
# ============================================================
def main():
    st.set_page_config(
        page_title="ESAL Calculator - AASHTO 1993",
        page_icon="🛣️",
        layout="wide"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A5F;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #4A6FA5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-box {
        background: linear-gradient(135deg, #1E3A5F 0%, #4A6FA5 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<p class="main-header">🛣️ ESAL Calculator</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">คำนวณปริมาณเพลาเดี่ยวมาตรฐานเทียบเท่า ตามมาตรฐาน AASHTO 1993</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ พารามิเตอร์การคำนวณ")
        
        pavement_type = st.selectbox(
            "ประเภทผิวทาง",
            options=['rigid', 'flexible'],
            format_func=lambda x: '🧱 Rigid Pavement (คอนกรีต)' if x == 'rigid' else '🛤️ Flexible Pavement (ลาดยาง)'
        )
        
        pt = st.selectbox(
            "Terminal Serviceability (pt)",
            options=[2.0, 2.5, 3.0],
            index=1,
            format_func=lambda x: f"pt = {x}"
        )
        
        if pavement_type == 'rigid':
            param = st.selectbox(
                "ความหนาพื้นคอนกรีต (D)",
                options=[10, 11, 12, 13, 14, 15, 16],
                format_func=lambda x: f"D = {x} นิ้ว"
            )
            param_label = f"D = {param} นิ้ว"
        else:
            param = st.selectbox(
                "Structural Number (SN)",
                options=[4, 5, 6, 7, 8, 9],
                format_func=lambda x: f"SN = {x}"
            )
            param_label = f"SN = {param}"
        
        st.divider()
        
        st.subheader("🚗 ค่าสัดส่วน")
        lane_factor = st.slider("Lane Distribution Factor", 0.1, 1.0, 0.5, 0.05)
        direction_factor = st.slider("Directional Factor", 0.5, 1.0, 0.9, 0.1)
        
        st.divider()
        
        # ============================================================
        # ส่วนแก้ไขค่า Truck Factor
        # ============================================================
        st.subheader("🚛 ค่า Truck Factor")
        
        # สร้าง session state สำหรับเก็บค่า Truck Factor
        tf_key = f"tf_{pavement_type}_{pt}_{param}"
        if tf_key not in st.session_state:
            st.session_state[tf_key] = {}
            for code in TRUCKS.keys():
                st.session_state[tf_key][code] = get_default_truck_factor(code, pavement_type, pt, param)
        
        # ปุ่ม Reset เป็นค่า Default
        if st.button("🔄 Reset เป็นค่า Default", use_container_width=True):
            for code in TRUCKS.keys():
                st.session_state[tf_key][code] = get_default_truck_factor(code, pavement_type, pt, param)
            st.rerun()
        
        # Input สำหรับแก้ไขค่า Truck Factor แต่ละประเภท
        st.caption("กรอกค่า Truck Factor (แก้ไขได้)")
        
        truck_factors = {}
        for code in TRUCKS.keys():
            default_val = get_default_truck_factor(code, pavement_type, pt, param)
            current_val = st.session_state[tf_key].get(code, default_val)
            
            new_val = st.number_input(
                f"{code}",
                min_value=0.0,
                max_value=50.0,
                value=float(current_val),
                step=0.0001,
                format="%.4f",
                key=f"input_{tf_key}_{code}",
                help=f"{TRUCKS[code]['desc']} | Default: {default_val:.4f}"
            )
            
            st.session_state[tf_key][code] = new_val
            truck_factors[code] = new_val
        
        st.divider()
        
        st.subheader("📥 ดาวน์โหลด Template")
        template_df = create_template()
        st.download_button(
            label="📄 ดาวน์โหลด Template Excel",
            data=to_excel(template_df),
            file_name="traffic_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    # Main Content
    tab1, tab2, tab3 = st.tabs(["📊 คำนวณ ESAL", "🚛 ข้อมูล Truck Factor", "📘 คู่มือ"])
    
    with tab1:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("📤 อัพโหลดข้อมูลปริมาณจราจร")
            
            uploaded_file = st.file_uploader(
                "เลือกไฟล์ Excel",
                type=['xlsx', 'xls'],
                help="อัพโหลดไฟล์ Excel (หน่วย: คัน/วัน)"
            )
            
            if 'use_sample' not in st.session_state:
                st.session_state['use_sample'] = False
            
            if uploaded_file is not None:
                try:
                    traffic_df = pd.read_excel(uploaded_file)
                    st.success("✅ อัพโหลดสำเร็จ!")
                    st.session_state['use_sample'] = False
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาด: {e}")
                    traffic_df = None
            else:
                st.info("📌 อัพโหลดไฟล์ Excel หรือใช้ข้อมูลตัวอย่าง")
                
                if st.button("🔄 ใช้ข้อมูลตัวอย่าง", use_container_width=True):
                    st.session_state['use_sample'] = True
                
                traffic_df = create_template() if st.session_state['use_sample'] else None
            
            if traffic_df is not None:
                st.write("**ข้อมูลปริมาณจราจร (คัน/วัน):**")
                st.dataframe(traffic_df, use_container_width=True, height=350)
        
        with col2:
            st.subheader("📈 ผลการคำนวณ ESAL")
            
            if traffic_df is not None:
                # ใช้ค่า Truck Factor จาก sidebar (ที่ผู้ใช้กรอก/แก้ไขได้)
                results_df, total_esal = calculate_esal(
                    traffic_df, truck_factors, lane_factor, direction_factor
                )
                
                # แสดงผลรวม
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                
                with col_m1:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-value">{total_esal:,.0f}</div>
                        <div class="metric-label">ESAL รวมทั้งหมด</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_m2:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-value">{len(traffic_df)}</div>
                        <div class="metric-label">จำนวนปี</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_m3:
                    pavement_label = "Rigid" if pavement_type == 'rigid' else "Flexible"
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-value">{pavement_label}</div>
                        <div class="metric-label">ประเภทผิวทาง</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_m4:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-value">{param_label}</div>
                        <div class="metric-label">พารามิเตอร์</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.divider()
                
                # ตาราง Truck Factor ที่ใช้ (แสดงค่าที่ผู้ใช้กรอก)
                st.write("**🚛 ค่า Truck Factor ที่ใช้:**")
                tf_display = []
                for code, tf in truck_factors.items():
                    default_tf = get_default_truck_factor(code, pavement_type, pt, param)
                    status = "✅" if abs(tf - default_tf) < 0.0001 else "✏️ แก้ไข"
                    tf_display.append({
                        'รหัส': code, 
                        'ประเภท': TRUCKS[code]['desc'], 
                        'Truck Factor': f"{tf:.4f}",
                        'Default': f"{default_tf:.4f}",
                        'สถานะ': status
                    })
                st.dataframe(pd.DataFrame(tf_display), use_container_width=True, hide_index=True)
                
                st.divider()
                
                # ผลลัพธ์รายปี
                st.write("**📊 ESAL รายปี:**")
                
                summary_cols = ['Year']
                for code in TRUCKS.keys():
                    if f'{code}_ESAL' in results_df.columns:
                        summary_cols.append(f'{code}_ESAL')
                summary_cols.append('Total_ESAL')
                
                summary_df = results_df[summary_cols].copy()
                rename_dict = {'Year': 'ปีที่', 'Total_ESAL': 'ESAL รวม'}
                for code in TRUCKS.keys():
                    rename_dict[f'{code}_ESAL'] = code
                summary_df = summary_df.rename(columns=rename_dict)
                
                for col in summary_df.columns:
                    if col != 'ปีที่':
                        summary_df[col] = summary_df[col].apply(lambda x: f"{x:,.0f}")
                
                st.dataframe(summary_df, use_container_width=True, height=400)
                
                # ดาวน์โหลด
                st.divider()
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Summary sheet
                    pd.DataFrame({
                        'รายการ': ['ประเภทผิวทาง', 'pt', 'พารามิเตอร์', 'Lane Factor', 'Direction Factor', 'ESAL รวม', 'จำนวนปี'],
                        'ค่า': ['Rigid' if pavement_type == 'rigid' else 'Flexible', pt, param_label, lane_factor, direction_factor, f"{total_esal:,.0f}", len(traffic_df)]
                    }).to_excel(writer, sheet_name='Summary', index=False)
                    
                    # Truck Factors sheet (รวมค่าที่ใช้และค่า Default)
                    pd.DataFrame(tf_display).to_excel(writer, sheet_name='Truck Factors', index=False)
                    
                    # ESAL by Year
                    results_df.to_excel(writer, sheet_name='ESAL by Year', index=False)
                    
                    # Input Data
                    traffic_df.to_excel(writer, sheet_name='Input Data', index=False)
                
                st.download_button(
                    label="📥 ดาวน์โหลดผลลัพธ์ (Excel)",
                    data=output.getvalue(),
                    file_name=f"ESAL_Results_{pavement_type}_{param}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.warning("⚠️ กรุณาอัพโหลดข้อมูลหรือใช้ข้อมูลตัวอย่าง")
    
    with tab2:
        st.subheader("🚛 ข้อมูลรถบรรทุก 6 ประเภทตามกรมทางหลวง")
        
        truck_details = []
        for code, truck in TRUCKS.items():
            axle_info = []
            for axle in truck['axles']:
                axle_info.append(f"{axle['name']}: {axle['load_ton']} ตัน ({axle['type']})")
            truck_details.append({'รหัส': code, 'ประเภท': truck['desc'], 'ข้อมูลเพลา': ' | '.join(axle_info)})
        
        st.dataframe(pd.DataFrame(truck_details), use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("📊 ตาราง Truck Factor (ค่า Default ตาม AASHTO 1993)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🧱 Rigid Pavement (pt = 2.0)**")
            st.dataframe(get_all_truck_factors_table('rigid', 2.0), use_container_width=True, hide_index=True)
            
            st.write("**🧱 Rigid Pavement (pt = 2.5)**")
            st.dataframe(get_all_truck_factors_table('rigid', 2.5), use_container_width=True, hide_index=True)
            
            st.write("**🧱 Rigid Pavement (pt = 3.0)**")
            st.dataframe(get_all_truck_factors_table('rigid', 3.0), use_container_width=True, hide_index=True)
        
        with col2:
            st.write("**🛤️ Flexible Pavement (pt = 2.0)**")
            st.dataframe(get_all_truck_factors_table('flexible', 2.0), use_container_width=True, hide_index=True)
            
            st.write("**🛤️ Flexible Pavement (pt = 2.5)**")
            st.dataframe(get_all_truck_factors_table('flexible', 2.5), use_container_width=True, hide_index=True)
            
            st.write("**🛤️ Flexible Pavement (pt = 3.0)**")
            st.dataframe(get_all_truck_factors_table('flexible', 3.0), use_container_width=True, hide_index=True)
    
    with tab3:
        st.subheader("📘 คู่มือการใช้งาน")
        
        st.markdown("""
        ### 1️⃣ เตรียมไฟล์ Excel
        
        | คอลัมน์ | คำอธิบาย |
        |---------|----------|
        | `Year` | ปีที่ (1, 2, 3, ... n) |
        | `MB` | Medium Bus (คัน/วัน) |
        | `HB` | Heavy Bus (คัน/วัน) |
        | `MT` | Medium Truck (คัน/วัน) |
        | `HT` | Heavy Truck (คัน/วัน) |
        | `STR` | Semi-Trailer (คัน/วัน) |
        | `TR` | Full Trailer (คัน/วัน) |
        
        ### 2️⃣ ตั้งค่าพารามิเตอร์
        
        - **Rigid:** D = 10-16 นิ้ว
        - **Flexible:** SN = 4-9
        - **pt:** 2.0, 2.5 หรือ 3.0
        
        ### 3️⃣ แก้ไขค่า Truck Factor
        
        - ค่า Truck Factor สามารถแก้ไขได้ที่ Sidebar
        - ค่า Default จะโหลดตามตาราง AASHTO 1993
        - กดปุ่ม "Reset เป็นค่า Default" เพื่อคืนค่าเริ่มต้น
        - ค่าที่แก้ไขจะแสดงสถานะ "✏️ แก้ไข" ในตารางผลลัพธ์
        
        ### 4️⃣ สูตรคำนวณ ESAL
        """)
        
        st.latex(r'ESAL = \sum_{i=1}^{n} \sum_{j=1}^{6} (ADT_{ij} \times TF_j \times LF \times DF \times 365)')
        
        st.markdown("""
        ### 5️⃣ สูตรคำนวณ Truck Factor (AASHTO 1993)
        
        **Flexible Pavement (สมการ 2-1):**
        """)
        st.latex(r'\log\left(\frac{W_{tx}}{W_{t18}}\right) = 4.79 \cdot \log(18+1) - 4.79 \cdot \log(L_x+L_2) + 4.33 \cdot \log(L_2) + \frac{G_t}{\beta_x} - \frac{G_t}{\beta_{18}}')
        
        st.markdown("""
        **Rigid Pavement (สมการ 2-2):**
        """)
        st.latex(r'\log\left(\frac{W_{tx}}{W_{t18}}\right) = 4.62 \cdot \log(18+1) - 4.62 \cdot \log(L_x+L_2) + 3.28 \cdot \log(L_2) + \frac{G_t}{\beta_x} - \frac{G_t}{\beta_{18}}')
        
        st.markdown("""
        ### 📚 อ้างอิง
        - AASHTO Guide for Design of Pavement Structures (1993)
        - กรมทางหลวง กระทรวงคมนาคม
        """)
    
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #888;">
        พัฒนาเพื่อการเรียนการสอนโดย รศ.ดร.อิทธิพล มีผล ภาควิชาครุศาสตร์โยธา มจพ. | ESAL Calculator v1.3
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
