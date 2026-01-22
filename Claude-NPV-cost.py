"""
แอปพลิเคชันวิเคราะห์ความคุ้มค่าโครงสร้างชั้นทาง (AASHTO 1993)
Version 2.0 - รองรับการกำหนดรายละเอียดโครงสร้างชั้นทาง
พัฒนาโดย: Claude AI สำหรับ อ.อิทธิพล - KMUTNB
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import io

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="วิเคราะห์ความคุ้มค่าโครงสร้างชั้นทาง",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS
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
    .cost-box {
        background: #f0f8ff;
        padding: 10px;
        border-radius: 8px;
        border-left: 4px solid #2E86AB;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


# ===== ข้อมูลเริ่มต้น (จากตารางที่ 5.3-18 ถึง 5.3-25) =====
# ปริมาณต่อ 1 กิโลเมตร (ความกว้างรวม 22 ม. สำหรับถนน 2 ทิศทาง)

def get_default_ac1_layers():
    """AC1: แอสฟัลต์บนหินคลุก (ตารางที่ 5.3-18)"""
    return [
        {'name': 'Wearing Course', 'thickness': 7, 'unit': 'cm', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 480},
        {'name': 'Binder Course', 'thickness': 7, 'unit': 'cm', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 480},
        {'name': 'Asphalt Base Course', 'thickness': 10, 'unit': 'cm', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 600},
        {'name': 'Tack Coat', 'thickness': 2, 'unit': 'Layer', 'quantity': 44000, 'qty_unit': 'sq.m', 'unit_cost': 20},
        {'name': 'Prime Coat', 'thickness': 1, 'unit': 'Layer', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 30},
        {'name': 'Crushed Rock Base', 'thickness': 20, 'unit': 'cm', 'quantity': 4400, 'qty_unit': 'cu.m', 'unit_cost': 714},
        {'name': 'Soil Aggregate Subbase', 'thickness': 30, 'unit': 'cm', 'quantity': 6600, 'qty_unit': 'cu.m', 'unit_cost': 714},
        {'name': 'Sand Embankment', 'thickness': 40, 'unit': 'cm', 'quantity': 8800, 'qty_unit': 'cu.m', 'unit_cost': 361},
    ]

def get_default_ac2_layers():
    """AC2: แอสฟัลต์บนหินคลุกผสมซีเมนต์ (ตารางที่ 5.3-20)"""
    return [
        {'name': 'Wearing Course', 'thickness': 5, 'unit': 'cm', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 400},
        {'name': 'Binder Course', 'thickness': 5, 'unit': 'cm', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 400},
        {'name': 'Tack Coat', 'thickness': 1, 'unit': 'Layer', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 20},
        {'name': 'Prime Coat', 'thickness': 1, 'unit': 'Layer', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 30},
        {'name': 'Cement Modified Crushed Rock', 'thickness': 20, 'unit': 'cm', 'quantity': 4400, 'qty_unit': 'cu.m', 'unit_cost': 914},
        {'name': 'Soil Aggregate Subbase', 'thickness': 20, 'unit': 'cm', 'quantity': 4400, 'qty_unit': 'cu.m', 'unit_cost': 714},
        {'name': 'Sand Embankment', 'thickness': 30, 'unit': 'cm', 'quantity': 6600, 'qty_unit': 'cu.m', 'unit_cost': 361},
    ]

def get_default_jrcp1_layers():
    """JRCP1: คอนกรีตบนดินซีเมนต์ (ตารางที่ 5.3-22)"""
    return [
        {'name': '325 Ksc. Cubic Type Concrete', 'thickness': 28, 'unit': 'cm', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 800},
        {'name': 'Non Woven Geotextile', 'thickness': 1, 'unit': 'ชั้น', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 78},
        {'name': 'Soil Cement Base', 'thickness': 20, 'unit': 'cm', 'quantity': 4400, 'qty_unit': 'cu.m', 'unit_cost': 621},
        {'name': 'Sand Embankment', 'thickness': 60, 'unit': 'cm', 'quantity': 13200, 'qty_unit': 'cu.m', 'unit_cost': 361},
    ]

def get_default_jrcp1_joints():
    """รอยต่อสำหรับ JRCP1 - ปริมาณต่อ 1 กม."""
    return [
        {'name': 'Transverse Joint @10m', 'quantity': 2200, 'qty_unit': 'm', 'unit_cost': 430},
        {'name': 'Longitudinal Joint', 'quantity': 4000, 'qty_unit': 'm', 'unit_cost': 120},
    ]

def get_default_jrcp2_layers():
    """JRCP2: คอนกรีตบนหินคลุกผสมซีเมนต์ (ตารางที่ 5.3-24)"""
    return [
        {'name': '325 Ksc. Cubic Type Concrete', 'thickness': 28, 'unit': 'cm', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 800},
        {'name': 'Non Woven Geotextile', 'thickness': 1, 'unit': 'ชั้น', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 78},
        {'name': 'Cement Modified Crushed Rock', 'thickness': 20, 'unit': 'cm', 'quantity': 4400, 'qty_unit': 'cu.m', 'unit_cost': 914},
        {'name': 'Sand Embankment', 'thickness': 50, 'unit': 'cm', 'quantity': 11000, 'qty_unit': 'cu.m', 'unit_cost': 361},
    ]


def calculate_layer_cost(layers, road_length_km=1.0):
    """คำนวณค่าก่อสร้างจากชั้นโครงสร้าง"""
    total = 0
    details = []
    
    for layer in layers:
        qty = layer['quantity'] * road_length_km
        cost = qty * layer['unit_cost']
        total += cost
        
        details.append({
            'รายการ': layer['name'],
            'ความหนา': f"{layer['thickness']} {layer['unit']}",
            'ปริมาณ': qty,
            'หน่วย': layer['qty_unit'],
            'ราคา/หน่วย': layer['unit_cost'],
            'มูลค่า (บาท)': cost
        })
    
    return total, details


def calculate_joint_cost(joints, road_length_km=1.0):
    """คำนวณค่ารอยต่อ"""
    total = 0
    details = []
    
    for joint in joints:
        qty = joint['quantity'] * road_length_km
        cost = qty * joint['unit_cost']
        total += cost
        
        details.append({
            'รายการ': joint['name'],
            'ความหนา': '-',
            'ปริมาณ': qty,
            'หน่วย': joint['qty_unit'],
            'ราคา/หน่วย': joint['unit_cost'],
            'มูลค่า (บาท)': cost
        })
    
    return total, details


def calculate_npv_ac(initial_cost, seal_cost, overlay_cost, design_life, analysis_period, discount_rate):
    """คำนวณ NPV สำหรับ AC Pavement"""
    cash_flows = []
    total_npv = 0
    
    for year in range(analysis_period + 1):
        cost = 0
        activities = []
        
        if year % design_life == 0:
            cost += initial_cost
            activities.append(f"ก่อสร้างใหม่")
        elif year > 0:
            if year % 9 == 0:
                cost += overlay_cost
                activities.append(f"Overlay")
            elif year % 3 == 0:
                cost += seal_cost
                activities.append(f"Seal Coating")
        
        pv = cost / ((1 + discount_rate) ** year)
        total_npv += pv
        
        cash_flows.append({
            'year': year, 'cost': cost, 'pv': pv,
            'cumulative_pv': total_npv,
            'activities': ', '.join(activities) if activities else '-'
        })
    
    return total_npv, cash_flows


def calculate_npv_jrcp(initial_cost, joint_cost, design_life, analysis_period, discount_rate):
    """คำนวณ NPV สำหรับ JRCP"""
    cash_flows = []
    total_npv = 0
    
    for year in range(analysis_period + 1):
        cost = 0
        activities = []
        
        if year % design_life == 0:
            cost += initial_cost
            activities.append(f"ก่อสร้างใหม่")
        elif year > 0 and year % 3 == 0:
            cost += joint_cost
            activities.append(f"Joint Sealing")
        
        pv = cost / ((1 + discount_rate) ** year)
        total_npv += pv
        
        cash_flows.append({
            'year': year, 'cost': cost, 'pv': pv,
            'cumulative_pv': total_npv,
            'activities': ', '.join(activities) if activities else '-'
        })
    
    return total_npv, cash_flows


def render_layer_editor(layers, key_prefix):
    """แสดง UI สำหรับแก้ไขโครงสร้างชั้นทาง"""
    updated_layers = []
    
    # Header
    cols = st.columns([3, 1, 1.5, 1.5])
    cols[0].markdown("**รายการ**")
    cols[1].markdown("**หนา**")
    cols[2].markdown("**ปริมาณ**")
    cols[3].markdown("**ราคา/หน่วย**")
    
    for i, layer in enumerate(layers):
        cols = st.columns([3, 1, 1.5, 1.5])
        
        with cols[0]:
            st.text(layer['name'])
        
        with cols[1]:
            thick = st.number_input(
                "หนา", value=float(layer['thickness']),
                key=f"{key_prefix}_t_{i}", label_visibility="collapsed",
                min_value=0.0, step=1.0
            )
        
        with cols[2]:
            qty = st.number_input(
                "ปริมาณ", value=float(layer['quantity']),
                key=f"{key_prefix}_q_{i}", label_visibility="collapsed",
                min_value=0.0, step=100.0
            )
        
        with cols[3]:
            cost = st.number_input(
                "ราคา", value=float(layer['unit_cost']),
                key=f"{key_prefix}_c_{i}", label_visibility="collapsed",
                min_value=0.0, step=10.0
            )
        
        updated_layers.append({
            'name': layer['name'],
            'thickness': thick,
            'unit': layer['unit'],
            'quantity': qty,
            'qty_unit': layer['qty_unit'],
            'unit_cost': cost
        })
    
    return updated_layers


def render_joint_editor(joints, key_prefix):
    """แสดง UI สำหรับแก้ไขรอยต่อ"""
    updated_joints = []
    
    for i, joint in enumerate(joints):
        cols = st.columns([3, 1.5, 1.5])
        
        with cols[0]:
            st.text(joint['name'])
        
        with cols[1]:
            qty = st.number_input(
                "ปริมาณ (m)", value=float(joint['quantity']),
                key=f"{key_prefix}_jq_{i}", label_visibility="collapsed",
                min_value=0.0, step=100.0
            )
        
        with cols[2]:
            cost = st.number_input(
                "ราคา/ม.", value=float(joint['unit_cost']),
                key=f"{key_prefix}_jc_{i}", label_visibility="collapsed",
                min_value=0.0, step=10.0
            )
        
        updated_joints.append({
            'name': joint['name'],
            'quantity': qty,
            'qty_unit': joint['qty_unit'],
            'unit_cost': cost
        })
    
    return updated_joints


def create_comparison_chart(results_df):
    """สร้างกราฟเปรียบเทียบ"""
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('NPV รวม (ล้านบาท/กม.)', 'องค์ประกอบค่าใช้จ่าย'),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
    
    fig.add_trace(
        go.Bar(x=results_df['ประเภท'], y=results_df['NPV'],
               marker_color=colors, text=results_df['NPV'].apply(lambda x: f'{x:.2f}'),
               textposition='outside', name='NPV'),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(x=results_df['ประเภท'], y=results_df['ค่าก่อสร้าง'],
               marker_color='#2E86AB', name='ค่าก่อสร้าง'),
        row=1, col=2
    )
    
    maint_cost = results_df['NPV'] - results_df['ค่าก่อสร้าง']
    fig.add_trace(
        go.Bar(x=results_df['ประเภท'], y=maint_cost,
               marker_color='#F18F01', name='ค่าบำรุงรักษา (NPV)'),
        row=1, col=2
    )
    
    fig.update_layout(height=400, barmode='stack',
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    return fig


def create_timeline_chart(all_cash_flows, pavement_types):
    """สร้างกราฟ Timeline"""
    fig = go.Figure()
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
    
    for i, (ptype, cf) in enumerate(zip(pavement_types, all_cash_flows)):
        years = [c['year'] for c in cf]
        cum_pv = [c['cumulative_pv'] for c in cf]
        fig.add_trace(go.Scatter(x=years, y=cum_pv, mode='lines',
                                  name=ptype, line=dict(color=colors[i], width=2)))
    
    fig.update_layout(
        title='Cumulative NPV ตลอดระยะเวลาวิเคราะห์',
        xaxis_title='ปี', yaxis_title='Cumulative NPV (ล้านบาท/กม.)',
        height=400, hovermode='x unified'
    )
    return fig


def generate_word_report(project_info, results_df, all_details):
    """สร้างรายงาน Word"""
    doc = Document()
    
    style = doc.styles['Normal']
    style.font.name = 'TH SarabunPSK'
    style.font.size = Pt(16)
    
    doc.add_heading('รายงานวิเคราะห์ความคุ้มค่าโครงสร้างชั้นทาง', 0)
    
    doc.add_heading('1. ข้อมูลโครงการ', level=1)
    doc.add_paragraph(f"ชื่อโครงการ: {project_info.get('name', '-')}")
    doc.add_paragraph(f"ความยาว: {project_info.get('length', 1):.2f} กม.")
    doc.add_paragraph(f"Discount Rate: {project_info.get('discount_rate', 5)}%")
    doc.add_paragraph(f"ระยะเวลาวิเคราะห์: {project_info.get('analysis_period', 100)} ปี")
    
    doc.add_heading('2. รายละเอียดค่าก่อสร้าง', level=1)
    
    for ptype, details in all_details.items():
        doc.add_heading(ptype, level=2)
        if details:
            table = doc.add_table(rows=len(details)+1, cols=4)
            table.style = 'Table Grid'
            headers = ['รายการ', 'ปริมาณ', 'ราคา/หน่วย', 'มูลค่า (บาท)']
            for j, h in enumerate(headers):
                table.rows[0].cells[j].text = h
            for i, d in enumerate(details):
                table.rows[i+1].cells[0].text = str(d['รายการ'])
                table.rows[i+1].cells[1].text = f"{d['ปริมาณ']:,.0f} {d['หน่วย']}"
                table.rows[i+1].cells[2].text = f"{d['ราคา/หน่วย']:,.0f}"
                table.rows[i+1].cells[3].text = f"{d['มูลค่า (บาท)']:,.0f}"
    
    doc.add_heading('3. สรุปผลการวิเคราะห์', level=1)
    
    table = doc.add_table(rows=len(results_df)+1, cols=4)
    table.style = 'Table Grid'
    headers = ['ประเภท', 'ค่าก่อสร้าง', 'NPV', 'อันดับ']
    for j, h in enumerate(headers):
        table.rows[0].cells[j].text = h
    
    for i, row in results_df.iterrows():
        table.rows[i+1].cells[0].text = row['ประเภท']
        table.rows[i+1].cells[1].text = f"{row['ค่าก่อสร้าง']:.2f}"
        table.rows[i+1].cells[2].text = f"{row['NPV']:.2f}"
        table.rows[i+1].cells[3].text = str(row['อันดับ'])
    
    best = results_df.loc[results_df['อันดับ'] == 1].iloc[0]
    doc.add_paragraph()
    doc.add_paragraph(f"สรุป: {best['ประเภท']} มีความคุ้มค่าที่สุด (NPV = {best['NPV']:.2f} ล้านบาท/กม.)")
    doc.add_paragraph(f"รายงานสร้างเมื่อ: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    return doc


# ===== Main Application =====

def main():
    st.markdown('<div class="main-header">🛣️ ระบบวิเคราะห์ความคุ้มค่าโครงสร้างชั้นทาง</div>', unsafe_allow_html=True)
    st.markdown("##### ตามแนวทาง AASHTO 1993 - รองรับการกำหนดรายละเอียดวัสดุแต่ละชั้น")
    
    # Sidebar
    with st.sidebar:
        st.header("📋 ข้อมูลโครงการ")
        project_name = st.text_input("ชื่อโครงการ", value="โครงการก่อสร้างทางหลวง")
        road_length = st.number_input("ความยาวถนน (กม.)", value=1.0, min_value=0.1, step=0.1)
        
        st.divider()
        st.header("⚙️ พารามิเตอร์")
        cbr = st.selectbox("ค่า CBR (%)", options=[2, 3], index=0)
        discount_rate = st.number_input("Discount Rate (%)", value=5.0, min_value=1.0, max_value=15.0, step=0.5)
        analysis_period = st.number_input("ระยะเวลาวิเคราะห์ (ปี)", value=100, min_value=20, max_value=200, step=5)
        
        st.divider()
        st.info(f"📐 ความกว้างถนนมาตรฐาน: 22 ม.\n(ถนน 2 ทิศทาง รวมไหล่ทาง)")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏗️ โครงสร้างชั้นทาง", "💰 ค่าบำรุงรักษา", "📈 ผลการวิเคราะห์", "📋 Cash Flow", "📄 รายงาน"])
    
    with tab1:
        st.header("กำหนดโครงสร้างชั้นทาง")
        st.info("💡 แก้ไขความหนา ปริมาณ และราคาต่อหน่วยได้ตามต้องการ (ปริมาณต่อ 1 กิโลเมตร)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            with st.expander("🔵 AC1: แอสฟัลต์บนหินคลุก", expanded=True):
                ac1_layers = render_layer_editor(get_default_ac1_layers(), "ac1")
                ac1_cost, ac1_details = calculate_layer_cost(ac1_layers, road_length)
                ac1_cost_per_km = ac1_cost / road_length / 1_000_000
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง AC1:</b> {ac1_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
        
        with col2:
            with st.expander("🟣 AC2: แอสฟัลต์บนหินคลุกผสมซีเมนต์", expanded=True):
                ac2_layers = render_layer_editor(get_default_ac2_layers(), "ac2")
                ac2_cost, ac2_details = calculate_layer_cost(ac2_layers, road_length)
                ac2_cost_per_km = ac2_cost / road_length / 1_000_000
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง AC2:</b> {ac2_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
        
        col3, col4 = st.columns(2)
        
        with col3:
            with st.expander("🟠 JRCP1: คอนกรีตบนดินซีเมนต์", expanded=True):
                st.markdown("**ชั้นโครงสร้าง**")
                jrcp1_layers = render_layer_editor(get_default_jrcp1_layers(), "jrcp1")
                jrcp1_layer_cost, jrcp1_layer_details = calculate_layer_cost(jrcp1_layers, road_length)
                
                st.markdown("**รอยต่อ (Joints)**")
                jrcp1_joints = render_joint_editor(get_default_jrcp1_joints(), "jrcp1")
                jrcp1_joint_cost, jrcp1_joint_details = calculate_joint_cost(jrcp1_joints, road_length)
                
                jrcp1_total = jrcp1_layer_cost + jrcp1_joint_cost
                jrcp1_cost_per_km = jrcp1_total / road_length / 1_000_000
                jrcp1_details = jrcp1_layer_details + jrcp1_joint_details
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง JRCP1:</b> {jrcp1_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
        
        with col4:
            with st.expander("🔴 JRCP2: คอนกรีตบนหินคลุกผสมซีเมนต์", expanded=True):
                st.markdown("**ชั้นโครงสร้าง**")
                jrcp2_layers = render_layer_editor(get_default_jrcp2_layers(), "jrcp2")
                jrcp2_layer_cost, jrcp2_layer_details = calculate_layer_cost(jrcp2_layers, road_length)
                
                st.markdown("**รอยต่อ (Joints)**")
                jrcp2_joints = render_joint_editor(get_default_jrcp1_joints(), "jrcp2")  # ใช้ joints เดียวกัน
                jrcp2_joint_cost, jrcp2_joint_details = calculate_joint_cost(jrcp2_joints, road_length)
                
                jrcp2_total = jrcp2_layer_cost + jrcp2_joint_cost
                jrcp2_cost_per_km = jrcp2_total / road_length / 1_000_000
                jrcp2_details = jrcp2_layer_details + jrcp2_joint_details
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง JRCP2:</b> {jrcp2_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
        
        # Store in session state
        st.session_state['construction'] = {
            'AC1': {'cost': ac1_cost_per_km, 'details': ac1_details},
            'AC2': {'cost': ac2_cost_per_km, 'details': ac2_details},
            'JRCP1': {'cost': jrcp1_cost_per_km, 'details': jrcp1_details},
            'JRCP2': {'cost': jrcp2_cost_per_km, 'details': jrcp2_details},
        }
        
        # Summary table
        st.divider()
        st.subheader("📊 สรุปค่าก่อสร้าง")
        summary_df = pd.DataFrame({
            'ประเภท': ['AC1 (หินคลุก)', 'AC2 (CMCR)', 'JRCP1 (ดินซีเมนต์)', 'JRCP2 (CMCR)'],
            'ค่าก่อสร้าง (ล้านบาท/กม.)': [ac1_cost_per_km, ac2_cost_per_km, jrcp1_cost_per_km, jrcp2_cost_per_km],
            'อายุออกแบบ (ปี)': [20, 20, 25, 25]
        })
        st.dataframe(summary_df.style.format({'ค่าก่อสร้าง (ล้านบาท/กม.)': '{:.2f}'}), use_container_width=True)
    
    with tab2:
        st.header("กำหนดค่าบำรุงรักษา")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔵 AC Pavement")
            ac_seal = st.number_input("Seal Coating ทุก 3 ปี (ล้านบาท/กม.)", value=1.76, key="m_seal")
            ac_overlay = st.number_input("Overlay 5cm ทุก 9 ปี (ล้านบาท/กม.)", value=8.80, key="m_overlay")
            st.markdown("**รอบการบำรุง (20 ปี):** Seal ปี 3,6,12,15 | Overlay ปี 9,18")
        
        with col2:
            st.subheader("🟠 JRCP")
            jrcp_joint = st.number_input("Joint Sealing ทุก 3 ปี (ล้านบาท/กม.)", value=1.426, key="m_joint")
            st.markdown("**รอบการบำรุง (25 ปี):** Joint Seal ทุก 3 ปี")
        
        st.session_state['maintenance'] = {
            'ac_seal': ac_seal, 'ac_overlay': ac_overlay, 'jrcp_joint': jrcp_joint
        }
    
    with tab3:
        st.header("ผลการวิเคราะห์ NPV")
        
        if st.button("🔄 คำนวณ NPV", type="primary", use_container_width=True):
            with st.spinner("กำลังคำนวณ..."):
                constr = st.session_state.get('construction', {})
                maint = st.session_state.get('maintenance', {})
                
                ac1_c = constr.get('AC1', {}).get('cost', 46.89)
                ac2_c = constr.get('AC2', {}).get('cost', 29.04)
                jrcp1_c = constr.get('JRCP1', {}).get('cost', 28.24)
                jrcp2_c = constr.get('JRCP2', {}).get('cost', 29.53)
                
                seal = maint.get('ac_seal', 1.76)
                overlay = maint.get('ac_overlay', 8.80)
                joint = maint.get('jrcp_joint', 1.426)
                
                r = discount_rate / 100
                
                npv1, cf1 = calculate_npv_ac(ac1_c, seal, overlay, 20, analysis_period, r)
                npv2, cf2 = calculate_npv_ac(ac2_c, seal, overlay, 20, analysis_period, r)
                npv3, cf3 = calculate_npv_jrcp(jrcp1_c, joint, 25, analysis_period, r)
                npv4, cf4 = calculate_npv_jrcp(jrcp2_c, joint, 25, analysis_period, r)
                
                results = [
                    {'ประเภท': 'AC1 (หินคลุก)', 'ค่าก่อสร้าง': ac1_c, 'อายุ': 20, 'NPV': npv1},
                    {'ประเภท': 'AC2 (CMCR)', 'ค่าก่อสร้าง': ac2_c, 'อายุ': 20, 'NPV': npv2},
                    {'ประเภท': 'JRCP1 (ดินซีเมนต์)', 'ค่าก่อสร้าง': jrcp1_c, 'อายุ': 25, 'NPV': npv3},
                    {'ประเภท': 'JRCP2 (CMCR)', 'ค่าก่อสร้าง': jrcp2_c, 'อายุ': 25, 'NPV': npv4},
                ]
                
                results_df = pd.DataFrame(results)
                results_df['อันดับ'] = results_df['NPV'].rank().astype(int)
                results_df = results_df.sort_values('อันดับ')
                
                st.session_state['results_df'] = results_df
                st.session_state['all_cf'] = [cf1, cf2, cf3, cf4]
                st.session_state['ptypes'] = ['AC1', 'AC2', 'JRCP1', 'JRCP2']
                st.session_state['project_info'] = {
                    'name': project_name, 'length': road_length,
                    'cbr': cbr, 'discount_rate': discount_rate,
                    'analysis_period': analysis_period
                }
        
        if 'results_df' in st.session_state:
            df = st.session_state['results_df']
            best = df.loc[df['อันดับ'] == 1].iloc[0]
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🏆 ทางเลือกที่ดีที่สุด", best['ประเภท'])
            c2.metric("💰 NPV ต่ำสุด", f"{best['NPV']:.2f}")
            c3.metric("💵 ประหยัด", f"{df['NPV'].max() - best['NPV']:.2f}")
            c4.metric("📅 Discount Rate", f"{discount_rate}%")
            
            st.divider()
            st.subheader("📊 ตารางเปรียบเทียบ")
            st.dataframe(df.style.format({'ค่าก่อสร้าง': '{:.2f}', 'NPV': '{:.2f}'})
                        .background_gradient(subset=['NPV'], cmap='RdYlGn_r'),
                        use_container_width=True)
            
            st.plotly_chart(create_comparison_chart(df), use_container_width=True)
            st.plotly_chart(create_timeline_chart(st.session_state['all_cf'], st.session_state['ptypes']),
                           use_container_width=True)
    
    with tab4:
        st.header("รายละเอียด Cash Flow")
        
        if 'all_cf' in st.session_state:
            ptypes = st.session_state['ptypes']
            selected = st.selectbox("เลือกประเภท", ptypes)
            idx = ptypes.index(selected)
            cf = st.session_state['all_cf'][idx]
            
            cf_df = pd.DataFrame(cf)
            cf_with_cost = cf_df[cf_df['cost'] > 0]
            
            c1, c2 = st.columns([2, 1])
            with c1:
                st.dataframe(cf_with_cost[['year', 'cost', 'pv', 'cumulative_pv', 'activities']]
                            .rename(columns={'year': 'ปี', 'cost': 'ค่าใช้จ่าย', 'pv': 'PV',
                                            'cumulative_pv': 'Cum. PV', 'activities': 'กิจกรรม'})
                            .style.format({'ค่าใช้จ่าย': '{:.2f}', 'PV': '{:.2f}', 'Cum. PV': '{:.2f}'}),
                            use_container_width=True, height=400)
            with c2:
                st.metric("รวม Nominal", f"{cf_with_cost['cost'].sum():.2f}")
                st.metric("NPV รวม", f"{cf_with_cost['pv'].sum():.2f}")
                st.metric("จำนวนครั้ง", len(cf_with_cost))
        else:
            st.info("กรุณาคำนวณ NPV ก่อน")
    
    with tab5:
        st.header("สร้างรายงาน")
        
        if 'results_df' in st.session_state:
            c1, c2 = st.columns(2)
            
            with c1:
                if st.button("📄 สร้างรายงาน Word", type="primary", use_container_width=True):
                    constr = st.session_state.get('construction', {})
                    all_details = {k: v.get('details', []) for k, v in constr.items()}
                    
                    doc = generate_word_report(
                        st.session_state['project_info'],
                        st.session_state['results_df'],
                        all_details
                    )
                    
                    buf = io.BytesIO()
                    doc.save(buf)
                    buf.seek(0)
                    
                    st.download_button("⬇️ ดาวน์โหลด Word", data=buf,
                                       file_name=f"NPV_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            
            with c2:
                if st.button("💾 บันทึกโครงการ", use_container_width=True):
                    data = {
                        'project_info': st.session_state['project_info'],
                        'construction': {k: {'cost': v['cost']} for k, v in st.session_state.get('construction', {}).items()},
                        'maintenance': st.session_state.get('maintenance', {}),
                        'results': st.session_state['results_df'].to_dict('records'),
                        'saved_at': datetime.now().isoformat()
                    }
                    st.download_button("⬇️ ดาวน์โหลด JSON", data=json.dumps(data, ensure_ascii=False, indent=2),
                                       file_name=f"Project_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                                       mime="application/json")
        else:
            st.info("กรุณาคำนวณ NPV ก่อน")


if __name__ == "__main__":
    main()
