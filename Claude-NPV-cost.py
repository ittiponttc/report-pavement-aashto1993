"""
แอปพลิเคชันวิเคราะห์ความคุ้มค่าโครงสร้างชั้นทาง (AASHTO 1993)
พัฒนาโดย: Claude AI สำหรับ อ.อิทธิพล - KMUTNB
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io
import os

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="วิเคราะห์ความคุ้มค่าโครงสร้างชั้นทาง",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS สำหรับ styling
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1E3A5F;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #E8F4FD, #D1E9FA);
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #E8F4FD;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ===== ฟังก์ชันหลัก =====

def calculate_npv_ac(initial_cost, seal_cost, overlay_cost, design_life, analysis_period, discount_rate):
    """
    คำนวณ NPV สำหรับ AC Pavement (แอสฟัลต์คอนกรีต)
    
    Parameters:
    - initial_cost: ค่าก่อสร้างเริ่มต้น (ล้านบาท/กม.)
    - seal_cost: ค่า Seal Coating ต่อครั้ง (ล้านบาท/กม.)
    - overlay_cost: ค่า Overlay ต่อครั้ง (ล้านบาท/กม.)
    - design_life: อายุการใช้งานตามออกแบบ (ปี) - ปกติ 20 ปี
    - analysis_period: ระยะเวลาวิเคราะห์รวม (ปี)
    - discount_rate: อัตราส่วนลด (ทศนิยม)
    
    Returns:
    - npv: มูลค่าปัจจุบันสุทธิ (ต่อกิโลเมตร)
    - cash_flows: รายละเอียด cash flow แต่ละปี
    """
    cash_flows = []
    total_npv = 0
    
    for year in range(analysis_period + 1):
        cost = 0
        activities = []
        
        # ค่าก่อสร้างใหม่เมื่อหมดอายุ (ทุก design_life ปี รวมปี 0 และ 100)
        if year % design_life == 0:
            cost += initial_cost
            activities.append(f"ก่อสร้างใหม่ ({initial_cost:.2f})")
        elif year > 0:
            # ค่าบำรุงรักษา (ไม่ทำในปีที่ก่อสร้างใหม่)
            # Overlay ทุก 9 ปี
            if year % 9 == 0:
                cost += overlay_cost
                activities.append(f"Overlay ({overlay_cost:.2f})")
            # Seal Coating ทุก 3 ปี (ยกเว้นปีที่ทำ Overlay)
            elif year % 3 == 0:
                cost += seal_cost
                activities.append(f"Seal Coating ({seal_cost:.2f})")
        
        # คำนวณ Present Value
        pv = cost / ((1 + discount_rate) ** year)
        total_npv += pv
        
        cash_flows.append({
            'year': year,
            'cost': cost,
            'pv': pv,
            'cumulative_pv': total_npv,
            'activities': ', '.join(activities) if activities else '-'
        })
    
    return total_npv, cash_flows


def calculate_npv_jrcp(initial_cost, joint_cost, design_life, analysis_period, discount_rate):
    """
    คำนวณ NPV สำหรับ JRCP (คอนกรีตเสริมเหล็ก)
    
    Parameters:
    - initial_cost: ค่าก่อสร้างเริ่มต้น (ล้านบาท/กม.)
    - joint_cost: ค่า Joint Sealing ต่อครั้ง (ล้านบาท/กม.)
    - design_life: อายุการใช้งานตามออกแบบ (ปี) - ปกติ 25 ปี
    - analysis_period: ระยะเวลาวิเคราะห์รวม (ปี)
    - discount_rate: อัตราส่วนลด (ทศนิยม)
    
    Returns:
    - npv: มูลค่าปัจจุบันสุทธิ (ต่อกิโลเมตร)
    - cash_flows: รายละเอียด cash flow แต่ละปี
    """
    cash_flows = []
    total_npv = 0
    
    for year in range(analysis_period + 1):
        cost = 0
        activities = []
        
        # ค่าก่อสร้างใหม่เมื่อหมดอายุ (ทุก design_life ปี รวมปี 0)
        if year % design_life == 0:
            cost += initial_cost
            activities.append(f"ก่อสร้างใหม่ ({initial_cost:.2f})")
        elif year > 0:
            # Joint Sealing ทุก 3 ปี (ไม่ทำในปีที่ก่อสร้างใหม่)
            if year % 3 == 0:
                cost += joint_cost
                activities.append(f"Joint Sealing ({joint_cost:.2f})")
        
        # คำนวณ Present Value
        pv = cost / ((1 + discount_rate) ** year)
        total_npv += pv
        
        cash_flows.append({
            'year': year,
            'cost': cost,
            'pv': pv,
            'cumulative_pv': total_npv,
            'activities': ', '.join(activities) if activities else '-'
        })
    
    return total_npv, cash_flows


def create_pavement_structure_input(key_prefix, pavement_type, cbr):
    """สร้าง input สำหรับโครงสร้างชั้นทางแต่ละประเภท"""
    
    st.subheader(f"📐 โครงสร้างชั้นทาง")
    
    layers = []
    
    if pavement_type in ['AC1', 'AC2']:
        # Asphalt Concrete Pavement
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**ผิวทาง (Surface)**")
            wearing = st.number_input("Wearing Course (cm)", value=7, key=f"{key_prefix}_wearing")
            binder = st.number_input("Binder Course (cm)", value=7, key=f"{key_prefix}_binder")
            
            if pavement_type == 'AC1':
                asphalt_base = st.number_input("Asphalt Base Course (cm)", value=10, key=f"{key_prefix}_asphalt_base")
            
        with col2:
            st.markdown("**พื้นทางและรองพื้นทาง**")
            if pavement_type == 'AC1':
                crushed_rock = st.number_input("Crushed Rock Base (cm)", value=20, key=f"{key_prefix}_cr_base")
                soil_agg = st.number_input("Soil Aggregate Subbase (cm)", value=30, key=f"{key_prefix}_soil_agg")
            else:  # AC2 - CMCR
                cmcr = st.number_input("Cement Modified Crushed Rock (cm)", value=20, key=f"{key_prefix}_cmcr")
                soil_agg = st.number_input("Soil Aggregate Subbase (cm)", value=20 if cbr == 2 else 15, key=f"{key_prefix}_soil_agg")
            
            sand_emb = st.number_input("Sand Embankment (cm)", value=40 if pavement_type == 'AC1' else 30, key=f"{key_prefix}_sand")
        
        # สร้าง layers list
        layers = [
            {'name': 'Wearing Course', 'thickness': wearing, 'unit_cost': 480 if pavement_type == 'AC1' else 400},
            {'name': 'Binder Course', 'thickness': binder, 'unit_cost': 480 if pavement_type == 'AC1' else 400},
        ]
        
        if pavement_type == 'AC1':
            layers.extend([
                {'name': 'Asphalt Base Course', 'thickness': asphalt_base, 'unit_cost': 600},
                {'name': 'Tack Coat', 'thickness': 2, 'unit_cost': 20, 'unit': 'Layer'},
                {'name': 'Prime Coat', 'thickness': 1, 'unit_cost': 30, 'unit': 'Layer'},
                {'name': 'Crushed Rock Base', 'thickness': crushed_rock, 'unit_cost': 714},
                {'name': 'Soil Aggregate Subbase', 'thickness': soil_agg, 'unit_cost': 714},
            ])
        else:
            layers.extend([
                {'name': 'Tack Coat', 'thickness': 1, 'unit_cost': 20, 'unit': 'Layer'},
                {'name': 'Prime Coat', 'thickness': 1, 'unit_cost': 30, 'unit': 'Layer'},
                {'name': 'Cement Modified Crushed Rock', 'thickness': cmcr, 'unit_cost': 914},
                {'name': 'Soil Aggregate Subbase', 'thickness': soil_agg, 'unit_cost': 714},
            ])
        
        layers.append({'name': 'Sand Embankment', 'thickness': sand_emb, 'unit_cost': 361})
        
    else:  # JRCP
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**ผิวทาง (Surface)**")
            concrete = st.number_input("325 Ksc. Cubic Type Concrete (cm)", value=28, key=f"{key_prefix}_concrete")
            geotextile = st.checkbox("Non Woven Geotextile", value=True, key=f"{key_prefix}_geo")
            
        with col2:
            st.markdown("**รอยต่อ**")
            transverse = st.number_input("Transverse Joint @10m (line)", value=100, key=f"{key_prefix}_trans")
            longitudinal = st.number_input("Longitudinal Joint (line)", value=4, key=f"{key_prefix}_long")
        
        st.markdown("**พื้นทางและรองพื้นทาง**")
        col3, col4 = st.columns(2)
        
        with col3:
            if pavement_type == 'JRCP1':
                soil_cement = st.number_input("Soil Cement Base (cm)", value=20, key=f"{key_prefix}_sc_base")
            else:
                cmcr = st.number_input("Cement Modified Crushed Rock (cm)", value=20, key=f"{key_prefix}_cmcr_jrcp")
        
        with col4:
            sand_emb = st.number_input("Sand Embankment (cm)", value=60 if pavement_type == 'JRCP1' else 50, key=f"{key_prefix}_sand_jrcp")
        
        # สร้าง layers list สำหรับ JRCP
        layers = [
            {'name': '325 Ksc. Cubic Type Concrete', 'thickness': concrete, 'unit_cost': 800},
        ]
        
        if geotextile:
            layers.append({'name': 'Non Woven Geotextile', 'thickness': 1, 'unit_cost': 78, 'unit': 'sq.m'})
        
        layers.extend([
            {'name': 'Transverse Joint @10m', 'thickness': transverse, 'unit_cost': 430, 'unit': 'line', 'quantity': 2200},
            {'name': 'Longitudinal Joint', 'thickness': longitudinal, 'unit_cost': 120, 'unit': 'line', 'quantity': 4000},
        ])
        
        if pavement_type == 'JRCP1':
            layers.append({'name': 'Soil Cement Base', 'thickness': soil_cement, 'unit_cost': 621})
        else:
            layers.append({'name': 'Cement Modified Crushed Rock', 'thickness': cmcr, 'unit_cost': 914})
        
        layers.append({'name': 'Sand Embankment', 'thickness': sand_emb, 'unit_cost': 361})
    
    return layers


def calculate_construction_cost(layers, road_length_km, road_width):
    """คำนวณค่าก่อสร้างจากโครงสร้างชั้นทาง"""
    total_cost = 0
    cost_details = []
    
    area = road_length_km * 1000 * road_width  # sq.m
    
    for layer in layers:
        if layer.get('unit') == 'Layer':
            # Tack/Prime Coat
            quantity = area
            unit = 'sq.m'
        elif layer.get('unit') == 'line':
            # Joints
            quantity = layer.get('quantity', 0) * road_length_km
            unit = 'm'
        elif layer.get('unit') == 'sq.m':
            # Geotextile
            quantity = area
            unit = 'sq.m'
        else:
            # Regular layers (by thickness)
            quantity = area * layer['thickness'] / 100  # cu.m
            unit = 'cu.m'
        
        cost = quantity * layer['unit_cost']
        total_cost += cost
        
        cost_details.append({
            'รายการ': layer['name'],
            'ความหนา/จำนวน': layer['thickness'],
            'ปริมาณ': f"{quantity:,.0f}",
            'หน่วย': unit,
            'ราคาต่อหน่วย': layer['unit_cost'],
            'มูลค่า (บาท)': cost
        })
    
    return total_cost, cost_details


def get_maintenance_schedule(pavement_type):
    """กำหนดค่าบำรุงรักษาตามประเภทถนน"""
    
    if pavement_type in ['AC1', 'AC2']:
        return {
            3: 1.76,   # Seal Coating ทุก 3 ปี
            9: 8.80,   # Overlay 5 cm ทุก 9 ปี
        }
    else:  # JRCP
        return {
            3: 1.426,  # Joint Sealing ทุก 3 ปี
        }


def get_design_life(pavement_type):
    """อายุการใช้งานตามออกแบบ"""
    if pavement_type in ['AC1', 'AC2']:
        return 20
    else:
        return 25


def create_comparison_chart(results_df):
    """สร้างกราฟเปรียบเทียบ NPV"""
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('NPV รวม (ล้านบาท/กม.)', 'ค่าก่อสร้าง vs ค่าบำรุงรักษา'),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    # กราฟ NPV รวม
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
    fig.add_trace(
        go.Bar(
            x=results_df['ประเภท'],
            y=results_df['NPV (ล้านบาท/กม.)'],
            marker_color=colors[:len(results_df)],
            text=results_df['NPV (ล้านบาท/กม.)'].apply(lambda x: f'{x:.2f}'),
            textposition='outside',
            name='NPV'
        ),
        row=1, col=1
    )
    
    # กราฟเปรียบเทียบค่าก่อสร้าง vs บำรุงรักษา
    fig.add_trace(
        go.Bar(
            x=results_df['ประเภท'],
            y=results_df['ค่าก่อสร้างเริ่มต้น'],
            marker_color='#2E86AB',
            name='ค่าก่อสร้าง',
            text=results_df['ค่าก่อสร้างเริ่มต้น'].apply(lambda x: f'{x:.2f}'),
            textposition='inside',
        ),
        row=1, col=2
    )
    
    fig.add_trace(
        go.Bar(
            x=results_df['ประเภท'],
            y=results_df['NPV (ล้านบาท/กม.)'] - results_df['ค่าก่อสร้างเริ่มต้น'],
            marker_color='#F18F01',
            name='ค่าบำรุงรักษา (NPV)',
            text=(results_df['NPV (ล้านบาท/กม.)'] - results_df['ค่าก่อสร้างเริ่มต้น']).apply(lambda x: f'{x:.2f}'),
            textposition='inside',
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        barmode='stack'
    )
    
    return fig


def create_cashflow_timeline(all_cash_flows, pavement_types):
    """สร้างกราฟ Timeline ของ Cash Flow"""
    
    fig = go.Figure()
    
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
    
    for i, (ptype, cf) in enumerate(zip(pavement_types, all_cash_flows)):
        years = [c['year'] for c in cf]
        cum_pv = [c['cumulative_pv'] for c in cf]
        
        fig.add_trace(go.Scatter(
            x=years,
            y=cum_pv,
            mode='lines',
            name=ptype,
            line=dict(color=colors[i % len(colors)], width=2),
            fill='tonexty' if i > 0 else None
        ))
    
    fig.update_layout(
        title='Cumulative NPV ตลอดระยะเวลาวิเคราะห์',
        xaxis_title='ปี',
        yaxis_title='Cumulative NPV (ล้านบาท/กม.)',
        height=450,
        hovermode='x unified'
    )
    
    return fig


def generate_word_report(project_info, results_df, all_cash_flows, pavement_types):
    """สร้างรายงาน Word"""
    
    doc = Document()
    
    # ตั้งค่า font ภาษาไทย
    style = doc.styles['Normal']
    style.font.name = 'TH SarabunPSK'
    style.font.size = Pt(16)
    style._element.rPr.rFonts.set(qn('w:eastAsia'), 'TH SarabunPSK')
    
    # หัวเรื่อง
    title = doc.add_heading('รายงานวิเคราะห์ความคุ้มค่าโครงสร้างชั้นทาง', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # ข้อมูลโครงการ
    doc.add_heading('1. ข้อมูลโครงการ', level=1)
    
    info_table = doc.add_table(rows=6, cols=2)
    info_table.style = 'Table Grid'
    
    info_data = [
        ('ชื่อโครงการ', project_info.get('name', '-')),
        ('ความยาว (กม.)', f"{project_info.get('length', 1):.2f}"),
        ('ความกว้างผิวจราจร (ม.)', f"{project_info.get('width', 7.0):.2f}"),
        ('ค่า CBR (%)', f"{project_info.get('cbr', 2)}"),
        ('Discount Rate (%)', f"{project_info.get('discount_rate', 5)}"),
        ('ระยะเวลาวิเคราะห์ (ปี)', f"{project_info.get('analysis_period', 100)}"),
    ]
    
    for i, (label, value) in enumerate(info_data):
        info_table.rows[i].cells[0].text = label
        info_table.rows[i].cells[1].text = str(value)
    
    doc.add_paragraph()
    
    # ผลการวิเคราะห์
    doc.add_heading('2. สรุปผลการวิเคราะห์ความคุ้มค่า', level=1)
    
    result_table = doc.add_table(rows=len(results_df) + 1, cols=5)
    result_table.style = 'Table Grid'
    
    # Header
    headers = ['ประเภทโครงสร้าง', 'ค่าก่อสร้าง\n(ล้านบาท/กม.)', 'อายุออกแบบ\n(ปี)', 'NPV\n(ล้านบาท/กม.)', 'อันดับ']
    for j, header in enumerate(headers):
        result_table.rows[0].cells[j].text = header
    
    # Data
    for i, row in results_df.iterrows():
        result_table.rows[i + 1].cells[0].text = row['ประเภท']
        result_table.rows[i + 1].cells[1].text = f"{row['ค่าก่อสร้างเริ่มต้น']:.2f}"
        result_table.rows[i + 1].cells[2].text = str(row['อายุออกแบบ'])
        result_table.rows[i + 1].cells[3].text = f"{row['NPV (ล้านบาท/กม.)']:.2f}"
        result_table.rows[i + 1].cells[4].text = str(row['อันดับ'])
    
    doc.add_paragraph()
    
    # สรุปผล
    doc.add_heading('3. สรุปและข้อเสนอแนะ', level=1)
    
    best = results_df.loc[results_df['อันดับ'] == 1].iloc[0]
    
    doc.add_paragraph(f"จากการวิเคราะห์ความคุ้มค่าด้วยวิธี Net Present Value (NPV) "
                      f"โดยใช้ Discount Rate {project_info.get('discount_rate', 5)}% "
                      f"และระยะเวลาวิเคราะห์ {project_info.get('analysis_period', 100)} ปี พบว่า:")
    
    doc.add_paragraph(f"• โครงสร้างที่มีความคุ้มค่าที่สุด คือ {best['ประเภท']} "
                      f"มี NPV เท่ากับ {best['NPV (ล้านบาท/กม.)']:.2f} ล้านบาท/กม.")
    
    doc.add_paragraph()
    
    # รายละเอียด Cash Flow
    doc.add_heading('4. รายละเอียด Cash Flow', level=1)
    
    for ptype, cf in zip(pavement_types, all_cash_flows):
        doc.add_heading(f'{ptype}', level=2)
        
        # แสดงเฉพาะปีที่มีค่าใช้จ่าย
        cf_with_cost = [c for c in cf if c['cost'] > 0]
        
        if cf_with_cost:
            cf_table = doc.add_table(rows=min(len(cf_with_cost), 20) + 1, cols=4)
            cf_table.style = 'Table Grid'
            
            cf_headers = ['ปี', 'ค่าใช้จ่าย\n(ล้านบาท)', 'Present Value\n(ล้านบาท)', 'กิจกรรม']
            for j, header in enumerate(cf_headers):
                cf_table.rows[0].cells[j].text = header
            
            for i, c in enumerate(cf_with_cost[:20]):
                cf_table.rows[i + 1].cells[0].text = str(c['year'])
                cf_table.rows[i + 1].cells[1].text = f"{c['cost']:.2f}"
                cf_table.rows[i + 1].cells[2].text = f"{c['pv']:.2f}"
                cf_table.rows[i + 1].cells[3].text = c['activities']
        
        doc.add_paragraph()
    
    # Footer
    doc.add_paragraph()
    doc.add_paragraph(f"รายงานสร้างเมื่อ: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    doc.add_paragraph("พัฒนาโดย: ระบบวิเคราะห์ความคุ้มค่าโครงสร้างชั้นทาง (AASHTO 1993)")
    
    return doc


def save_project(project_data, filename):
    """บันทึกข้อมูลโครงการเป็น JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(project_data, f, ensure_ascii=False, indent=2)


def load_project(uploaded_file):
    """โหลดข้อมูลโครงการจาก JSON"""
    return json.load(uploaded_file)


# ===== Main Application =====

def main():
    st.markdown('<div class="main-header">🛣️ ระบบวิเคราะห์ความคุ้มค่าโครงสร้างชั้นทาง</div>', unsafe_allow_html=True)
    st.markdown("##### ตามแนวทาง AASHTO 1993 - คำนวณ NPV สำหรับเปรียบเทียบทางเลือกโครงสร้างชั้นทาง")
    
    # Sidebar - ข้อมูลโครงการ
    with st.sidebar:
        st.header("📋 ข้อมูลโครงการ")
        
        project_name = st.text_input("ชื่อโครงการ", value="โครงการก่อสร้างทางหลวง")
        road_length = st.number_input("ความยาวถนน (กม.)", value=1.0, min_value=0.1, step=0.1)
        road_width = st.number_input("ความกว้างผิวจราจร (ม.)", value=7.0, min_value=3.0, step=0.5)
        
        st.divider()
        st.header("⚙️ พารามิเตอร์การวิเคราะห์")
        
        cbr = st.selectbox("ค่า CBR ดินเดิม (%)", options=[2, 3], index=0)
        discount_rate = st.number_input("Discount Rate (%)", value=5.0, min_value=1.0, max_value=15.0, step=0.5)
        analysis_period = st.number_input("ระยะเวลาวิเคราะห์ (ปี)", value=100, min_value=20, max_value=200, step=5)
        
        st.divider()
        st.header("💾 จัดการข้อมูล")
        
        # Load project
        uploaded_json = st.file_uploader("โหลดโครงการ (.json)", type=['json'])
        if uploaded_json:
            try:
                loaded_data = load_project(uploaded_json)
                st.success("โหลดข้อมูลสำเร็จ!")
                st.session_state['loaded_project'] = loaded_data
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")
    
    # Main content - Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 กำหนดค่าใช้จ่าย", "📈 ผลการวิเคราะห์", "📋 Cash Flow", "📄 รายงาน"])
    
    with tab1:
        st.header("กำหนดค่าก่อสร้างและบำรุงรักษา")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔵 AC1: แอสฟัลต์บนหินคลุก")
            ac1_cost = st.number_input(
                "ค่าก่อสร้าง AC1 (ล้านบาท/กม.)",
                value=46.89 if cbr == 2 else 46.10,
                key="ac1_cost"
            )
            
            st.markdown("**ค่าบำรุงรักษา AC1:**")
            ac1_seal = st.number_input("Seal Coating ทุก 3 ปี (ล้านบาท/กม.)", value=1.76, key="ac1_seal")
            ac1_overlay = st.number_input("Overlay 5cm ทุก 9 ปี (ล้านบาท/กม.)", value=8.80, key="ac1_overlay")
        
        with col2:
            st.subheader("🟣 AC2: แอสฟัลต์บนหินคลุกผสมซีเมนต์")
            ac2_cost = st.number_input(
                "ค่าก่อสร้าง AC2 (ล้านบาท/กม.)",
                value=29.04 if cbr == 2 else 27.46,
                key="ac2_cost"
            )
            
            st.markdown("**ค่าบำรุงรักษา AC2:**")
            ac2_seal = st.number_input("Seal Coating ทุก 3 ปี (ล้านบาท/กม.)", value=1.76, key="ac2_seal")
            ac2_overlay = st.number_input("Overlay 5cm ทุก 9 ปี (ล้านบาท/กม.)", value=8.80, key="ac2_overlay")
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.subheader("🟠 JRCP1: คอนกรีตบนดินซีเมนต์")
            jrcp1_cost = st.number_input(
                "ค่าก่อสร้าง JRCP1 (ล้านบาท/กม.)",
                value=28.24 if cbr == 2 else 27.45,
                key="jrcp1_cost"
            )
            
            st.markdown("**ค่าบำรุงรักษา JRCP1:**")
            jrcp1_joint = st.number_input("Joint Sealing ทุก 3 ปี (ล้านบาท/กม.)", value=1.426, key="jrcp1_joint")
        
        with col4:
            st.subheader("🔴 JRCP2: คอนกรีตบนหินคลุกผสมซีเมนต์")
            jrcp2_cost = st.number_input(
                "ค่าก่อสร้าง JRCP2 (ล้านบาท/กม.)",
                value=29.53 if cbr == 2 else 28.73,
                key="jrcp2_cost"
            )
            
            st.markdown("**ค่าบำรุงรักษา JRCP2:**")
            jrcp2_joint = st.number_input("Joint Sealing ทุก 3 ปี (ล้านบาท/กม.)", value=1.426, key="jrcp2_joint")
        
        # สรุปตาราง
        st.divider()
        st.subheader("📋 สรุปข้อมูลที่กำหนด")
        
        summary_data = {
            'ประเภท': ['AC1 (หินคลุก)', 'AC2 (CMCR)', 'JRCP1 (ดินซีเมนต์)', 'JRCP2 (CMCR)'],
            'ค่าก่อสร้าง (ล้านบาท/กม.)': [ac1_cost, ac2_cost, jrcp1_cost, jrcp2_cost],
            'อายุออกแบบ (ปี)': [20, 20, 25, 25],
            'ค่าบำรุงรักษา/รอบ': [
                f"Seal: {ac1_seal}, Overlay: {ac1_overlay}",
                f"Seal: {ac2_seal}, Overlay: {ac2_overlay}",
                f"Joint Seal: {jrcp1_joint}",
                f"Joint Seal: {jrcp2_joint}"
            ]
        }
        
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
    
    with tab2:
        st.header("ผลการวิเคราะห์ NPV")
        
        if st.button("🔄 คำนวณ NPV", type="primary", use_container_width=True):
            with st.spinner("กำลังคำนวณ..."):
                # ดึงค่าจาก session state
                ac1_cost = st.session_state.get('ac1_cost', 46.89)
                ac2_cost = st.session_state.get('ac2_cost', 29.04)
                jrcp1_cost = st.session_state.get('jrcp1_cost', 28.24)
                jrcp2_cost = st.session_state.get('jrcp2_cost', 29.53)
                
                ac1_seal = st.session_state.get('ac1_seal', 1.76)
                ac1_overlay = st.session_state.get('ac1_overlay', 8.80)
                ac2_seal = st.session_state.get('ac2_seal', 1.76)
                ac2_overlay = st.session_state.get('ac2_overlay', 8.80)
                jrcp1_joint = st.session_state.get('jrcp1_joint', 1.426)
                jrcp2_joint = st.session_state.get('jrcp2_joint', 1.426)
                
                results = []
                all_cash_flows = []
                pavement_types = []
                
                # คำนวณ AC1
                npv1, cf1 = calculate_npv_ac(ac1_cost, ac1_seal, ac1_overlay, 20, analysis_period, discount_rate / 100)
                results.append({
                    'ประเภท': 'AC1 (หินคลุก)',
                    'ค่าก่อสร้างเริ่มต้น': ac1_cost,
                    'อายุออกแบบ': 20,
                    'NPV (ล้านบาท/กม.)': npv1
                })
                all_cash_flows.append(cf1)
                pavement_types.append('AC1 (หินคลุก)')
                
                # คำนวณ AC2
                npv2, cf2 = calculate_npv_ac(ac2_cost, ac2_seal, ac2_overlay, 20, analysis_period, discount_rate / 100)
                results.append({
                    'ประเภท': 'AC2 (CMCR)',
                    'ค่าก่อสร้างเริ่มต้น': ac2_cost,
                    'อายุออกแบบ': 20,
                    'NPV (ล้านบาท/กม.)': npv2
                })
                all_cash_flows.append(cf2)
                pavement_types.append('AC2 (CMCR)')
                
                # คำนวณ JRCP1
                npv3, cf3 = calculate_npv_jrcp(jrcp1_cost, jrcp1_joint, 25, analysis_period, discount_rate / 100)
                results.append({
                    'ประเภท': 'JRCP1 (ดินซีเมนต์)',
                    'ค่าก่อสร้างเริ่มต้น': jrcp1_cost,
                    'อายุออกแบบ': 25,
                    'NPV (ล้านบาท/กม.)': npv3
                })
                all_cash_flows.append(cf3)
                pavement_types.append('JRCP1 (ดินซีเมนต์)')
                
                # คำนวณ JRCP2
                npv4, cf4 = calculate_npv_jrcp(jrcp2_cost, jrcp2_joint, 25, analysis_period, discount_rate / 100)
                results.append({
                    'ประเภท': 'JRCP2 (CMCR)',
                    'ค่าก่อสร้างเริ่มต้น': jrcp2_cost,
                    'อายุออกแบบ': 25,
                    'NPV (ล้านบาท/กม.)': npv4
                })
                all_cash_flows.append(cf4)
                pavement_types.append('JRCP2 (CMCR)')
                
                results_df = pd.DataFrame(results)
                results_df['อันดับ'] = results_df['NPV (ล้านบาท/กม.)'].rank().astype(int)
                results_df = results_df.sort_values('อันดับ')
                
                # เก็บใน session state
                st.session_state['results_df'] = results_df
                st.session_state['all_cash_flows'] = all_cash_flows
                st.session_state['pavement_types'] = pavement_types
                st.session_state['project_info'] = {
                    'name': project_name,
                    'length': road_length,
                    'width': road_width,
                    'cbr': cbr,
                    'discount_rate': discount_rate,
                    'analysis_period': analysis_period
                }
        
        # แสดงผลลัพธ์
        if 'results_df' in st.session_state:
            results_df = st.session_state['results_df']
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            best = results_df.loc[results_df['อันดับ'] == 1].iloc[0]
            
            with col1:
                st.metric("🏆 ทางเลือกที่ดีที่สุด", best['ประเภท'])
            with col2:
                st.metric("💰 NPV ต่ำสุด", f"{best['NPV (ล้านบาท/กม.)']:.2f} ล้านบาท/กม.")
            with col3:
                savings = results_df['NPV (ล้านบาท/กม.)'].max() - best['NPV (ล้านบาท/กม.)']
                st.metric("💵 ประหยัด", f"{savings:.2f} ล้านบาท/กม.")
            with col4:
                st.metric("📅 Discount Rate", f"{discount_rate}%")
            
            st.divider()
            
            # ตารางผลลัพธ์
            st.subheader("📊 ตารางเปรียบเทียบ")
            
            # จัดรูปแบบตาราง
            styled_df = results_df.style.format({
                'ค่าก่อสร้างเริ่มต้น': '{:.2f}',
                'NPV (ล้านบาท/กม.)': '{:.2f}'
            }).background_gradient(subset=['NPV (ล้านบาท/กม.)'], cmap='RdYlGn_r')
            
            st.dataframe(styled_df, use_container_width=True)
            
            # กราฟ
            st.divider()
            st.subheader("📈 กราฟเปรียบเทียบ")
            
            fig = create_comparison_chart(results_df)
            st.plotly_chart(fig, use_container_width=True)
            
            # กราฟ Timeline
            if 'all_cash_flows' in st.session_state:
                fig_timeline = create_cashflow_timeline(
                    st.session_state['all_cash_flows'],
                    st.session_state['pavement_types']
                )
                st.plotly_chart(fig_timeline, use_container_width=True)
    
    with tab3:
        st.header("รายละเอียด Cash Flow")
        
        if 'all_cash_flows' in st.session_state:
            pavement_types = st.session_state['pavement_types']
            selected_type = st.selectbox("เลือกประเภทโครงสร้าง", pavement_types)
            
            idx = pavement_types.index(selected_type)
            cf = st.session_state['all_cash_flows'][idx]
            
            # แสดง Cash Flow ที่มีค่าใช้จ่าย
            cf_df = pd.DataFrame(cf)
            cf_with_cost = cf_df[cf_df['cost'] > 0].copy()
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader(f"Cash Flow: {selected_type}")
                
                display_df = cf_with_cost[['year', 'cost', 'pv', 'cumulative_pv', 'activities']].copy()
                display_df.columns = ['ปี', 'ค่าใช้จ่าย', 'Present Value', 'Cumulative PV', 'กิจกรรม']
                
                st.dataframe(
                    display_df.style.format({
                        'ค่าใช้จ่าย': '{:.2f}',
                        'Present Value': '{:.2f}',
                        'Cumulative PV': '{:.2f}'
                    }),
                    use_container_width=True,
                    height=400
                )
            
            with col2:
                st.subheader("สรุป")
                total_cost = cf_with_cost['cost'].sum()
                total_pv = cf_with_cost['pv'].sum()
                
                st.metric("รวมค่าใช้จ่าย (Nominal)", f"{total_cost:.2f} ล้านบาท")
                st.metric("NPV รวม", f"{total_pv:.2f} ล้านบาท")
                st.metric("จำนวนครั้งที่มีค่าใช้จ่าย", f"{len(cf_with_cost)} ครั้ง")
        else:
            st.info("กรุณาคำนวณ NPV ก่อนในแท็บ 'ผลการวิเคราะห์'")
    
    with tab4:
        st.header("สร้างรายงาน")
        
        if 'results_df' in st.session_state:
            st.success("✅ พร้อมสร้างรายงาน")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📄 สร้างรายงาน Word", type="primary", use_container_width=True):
                    with st.spinner("กำลังสร้างรายงาน..."):
                        doc = generate_word_report(
                            st.session_state['project_info'],
                            st.session_state['results_df'],
                            st.session_state['all_cash_flows'],
                            st.session_state['pavement_types']
                        )
                        
                        # บันทึกเป็น bytes
                        doc_buffer = io.BytesIO()
                        doc.save(doc_buffer)
                        doc_buffer.seek(0)
                        
                        st.download_button(
                            label="⬇️ ดาวน์โหลดรายงาน Word",
                            data=doc_buffer,
                            file_name=f"NPV_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
            
            with col2:
                if st.button("💾 บันทึกโครงการ", use_container_width=True):
                    project_data = {
                        'project_info': st.session_state['project_info'],
                        'costs': {
                            'ac1': st.session_state.get('ac1_cost', 46.89),
                            'ac2': st.session_state.get('ac2_cost', 29.04),
                            'jrcp1': st.session_state.get('jrcp1_cost', 28.24),
                            'jrcp2': st.session_state.get('jrcp2_cost', 29.53),
                        },
                        'maintenance': {
                            'ac1_seal': st.session_state.get('ac1_seal', 1.76),
                            'ac1_overlay': st.session_state.get('ac1_overlay', 8.80),
                            'ac2_seal': st.session_state.get('ac2_seal', 1.76),
                            'ac2_overlay': st.session_state.get('ac2_overlay', 8.80),
                            'jrcp1_joint': st.session_state.get('jrcp1_joint', 1.426),
                            'jrcp2_joint': st.session_state.get('jrcp2_joint', 1.426),
                        },
                        'results': st.session_state['results_df'].to_dict('records'),
                        'saved_at': datetime.now().isoformat()
                    }
                    
                    json_str = json.dumps(project_data, ensure_ascii=False, indent=2)
                    
                    st.download_button(
                        label="⬇️ ดาวน์โหลดไฟล์โครงการ",
                        data=json_str,
                        file_name=f"Project_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                        mime="application/json"
                    )
            
            # Preview
            st.divider()
            st.subheader("📋 ตัวอย่างรายงาน")
            
            project_info = st.session_state['project_info']
            results_df = st.session_state['results_df']
            best = results_df.loc[results_df['อันดับ'] == 1].iloc[0]
            
            st.markdown(f"""
            ### รายงานวิเคราะห์ความคุ้มค่าโครงสร้างชั้นทาง
            
            **ชื่อโครงการ:** {project_info['name']}  
            **ความยาว:** {project_info['length']:.2f} กม.  
            **ค่า CBR:** {project_info['cbr']}%  
            **Discount Rate:** {project_info['discount_rate']}%  
            **ระยะเวลาวิเคราะห์:** {project_info['analysis_period']} ปี
            
            ---
            
            **สรุปผล:**  
            จากการวิเคราะห์ความคุ้มค่าด้วยวิธี Net Present Value (NPV) พบว่า
            **{best['ประเภท']}** มีความคุ้มค่าที่สุด โดยมี NPV เท่ากับ **{best['NPV (ล้านบาท/กม.)']:.2f} ล้านบาท/กม.**
            """)
        else:
            st.info("กรุณาคำนวณ NPV ก่อนในแท็บ 'ผลการวิเคราะห์'")


if __name__ == "__main__":
    main()
