"""
แอปพลิเคชันวิเคราะห์ความคุ้มค่าโครงสร้างชั้นทาง (AASHTO 1993)
Version 3.0 - รองรับ AC, JPCP/JRCP, CRCP พร้อม Library วัสดุ
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
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
import io

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="วิเคราะห์ค่าก่อสร้างโครงสร้างชั้นทาง",
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


# ===== Library วัสดุ =====
MATERIAL_LIBRARY = {
    'ผิวทาง': {
        'ผิวทางลาดยาง AC': {'unit_cost': 480, 'cost_unit': 'บาท/ตร.ม.'},
        'ผิวทางลาดยาง PMA': {'unit_cost': 550, 'cost_unit': 'บาท/ตร.ม.'},
        'คอนกรีต 325 Ksc.': {'unit_cost': 800, 'cost_unit': 'บาท/ตร.ม.'},
        'คอนกรีต 350 Ksc.': {'unit_cost': 850, 'cost_unit': 'บาท/ตร.ม.'},
    },
    'พื้นทาง': {
        'พื้นทางซีเมนต์ CTB': {'unit_cost': 621, 'cost_unit': 'บาท/ลบ.ม.'},
        'หินคลุกผสมซีเมนต์ UCS 24.5 ksc': {'unit_cost': 914, 'cost_unit': 'บาท/ลบ.ม.'},
        'หินคลุก CBR 80%': {'unit_cost': 714, 'cost_unit': 'บาท/ลบ.ม.'},
        'ดินซีเมนต์ UCS 17.5 ksc': {'unit_cost': 621, 'cost_unit': 'บาท/ลบ.ม.'},
        'วัสดุหมุนเวียน (Recycling)': {'unit_cost': 500, 'cost_unit': 'บาท/ลบ.ม.'},
    },
    'รองพื้นทาง': {
        'รองพื้นทางวัสดุมวลรวม CBR 25%': {'unit_cost': 714, 'cost_unit': 'บาท/ลบ.ม.'},
        'วัสดุคัดเลือก ก': {'unit_cost': 450, 'cost_unit': 'บาท/ลบ.ม.'},
        'ดินถมคันทาง / ดินเดิม': {'unit_cost': 361, 'cost_unit': 'บาท/ลบ.ม.'},
    },
    'ชั้นคันทาง': {
        'ทรายถมคันทาง': {'unit_cost': 361, 'cost_unit': 'บาท/ลบ.ม.'},
        'ดินถมคันทาง': {'unit_cost': 280, 'cost_unit': 'บาท/ลบ.ม.'},
    },
    'วัสดุอื่นๆ': {
        'Tack Coat': {'unit_cost': 20, 'cost_unit': 'บาท/ตร.ม.'},
        'Prime Coat': {'unit_cost': 30, 'cost_unit': 'บาท/ตร.ม.'},
        'Non Woven Geotextile': {'unit_cost': 78, 'cost_unit': 'บาท/ตร.ม.'},
    },
}

# ===== ข้อมูลเริ่มต้นโครงสร้างชั้นทาง =====

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

def get_default_crcp1_layers():
    """CRCP1: คอนกรีตเสริมเหล็กต่อเนื่องบนดินซีเมนต์"""
    return [
        {'name': '350 Ksc. Cubic Type Concrete', 'thickness': 25, 'unit': 'cm', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 850},
        {'name': 'Steel Reinforcement', 'thickness': 1, 'unit': 'ชั้น', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 150},
        {'name': 'Non Woven Geotextile', 'thickness': 1, 'unit': 'ชั้น', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 78},
        {'name': 'Soil Cement Base', 'thickness': 15, 'unit': 'cm', 'quantity': 3300, 'qty_unit': 'cu.m', 'unit_cost': 621},
        {'name': 'Sand Embankment', 'thickness': 50, 'unit': 'cm', 'quantity': 11000, 'qty_unit': 'cu.m', 'unit_cost': 361},
    ]

def get_default_crcp2_layers():
    """CRCP2: คอนกรีตเสริมเหล็กต่อเนื่องบนหินคลุกผสมซีเมนต์"""
    return [
        {'name': '350 Ksc. Cubic Type Concrete', 'thickness': 25, 'unit': 'cm', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 850},
        {'name': 'Steel Reinforcement', 'thickness': 1, 'unit': 'ชั้น', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 150},
        {'name': 'Non Woven Geotextile', 'thickness': 1, 'unit': 'ชั้น', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 78},
        {'name': 'Cement Modified Crushed Rock', 'thickness': 15, 'unit': 'cm', 'quantity': 3300, 'qty_unit': 'cu.m', 'unit_cost': 914},
        {'name': 'Sand Embankment', 'thickness': 40, 'unit': 'cm', 'quantity': 8800, 'qty_unit': 'cu.m', 'unit_cost': 361},
    ]


def calculate_quantity(thickness_cm, width_m, length_km, qty_unit):
    """คำนวณปริมาณจากความหนา ความกว้าง และความยาว"""
    area = width_m * length_km * 1000  # ตร.ม.
    if qty_unit == 'sq.m':
        return area
    elif qty_unit == 'cu.m':
        return area * thickness_cm / 100  # ลบ.ม.
    return area


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


def calculate_npv_crcp(initial_cost, maint_cost, design_life, analysis_period, discount_rate):
    """คำนวณ NPV สำหรับ CRCP"""
    cash_flows = []
    total_npv = 0
    
    for year in range(analysis_period + 1):
        cost = 0
        activities = []
        
        if year % design_life == 0:
            cost += initial_cost
            activities.append(f"ก่อสร้างใหม่")
        elif year > 0 and year % 5 == 0:
            cost += maint_cost
            activities.append(f"บำรุงรักษา")
        
        pv = cost / ((1 + discount_rate) ** year)
        total_npv += pv
        
        cash_flows.append({
            'year': year, 'cost': cost, 'pv': pv,
            'cumulative_pv': total_npv,
            'activities': ', '.join(activities) if activities else '-'
        })
    
    return total_npv, cash_flows


def render_layer_editor(layers, key_prefix, total_width, road_length):
    """แสดง UI สำหรับแก้ไขโครงสร้างชั้นทาง พร้อมคำนวณปริมาณอัตโนมัติ"""
    updated_layers = []
    
    # คำนวณพื้นที่ต่อ กม.
    area_per_km = total_width * 1000  # ตร.ม./กม.
    
    # แยก layers เป็นกลุ่ม
    surface_layers = []
    base_layers = []
    
    for layer in layers:
        name_lower = layer['name'].lower()
        if any(x in name_lower for x in ['wearing', 'binder', 'asphalt', 'concrete', 'tack', 'prime', 'geotextile', 'steel', 'ksc']):
            surface_layers.append(layer)
        else:
            base_layers.append(layer)
    
    # ===== ส่วนผิวทาง =====
    st.markdown("**ผิวทาง** (หน่วย: ตร.ม.)")
    cols = st.columns([3, 1, 1.5, 1.5])
    cols[0].markdown("รายการ")
    cols[1].markdown("หนา")
    cols[2].markdown("ปริมาณ (auto)")
    cols[3].markdown("ราคา/หน่วย")
    
    for i, layer in enumerate(surface_layers):
        cols = st.columns([3, 1, 1.5, 1.5])
        
        with cols[0]:
            st.text(layer['name'])
        with cols[1]:
            thick = st.number_input("หนา", value=float(layer['thickness']),
                key=f"{key_prefix}_st_{i}", label_visibility="collapsed", min_value=0.0, step=1.0)
        
        # คำนวณปริมาณอัตโนมัติ (ตร.ม.)
        if 'tack' in layer['name'].lower():
            # Tack Coat = 2 ชั้น
            auto_qty = area_per_km * road_length * thick
        else:
            auto_qty = area_per_km * road_length
        
        with cols[2]:
            st.text(f"{auto_qty:,.0f}")
        with cols[3]:
            cost = st.number_input("ราคา", value=float(layer['unit_cost']),
                key=f"{key_prefix}_sc_{i}", label_visibility="collapsed", min_value=0.0, step=10.0)
        
        updated_layers.append({
            'name': layer['name'], 'thickness': thick, 'unit': layer['unit'],
            'quantity': auto_qty, 'qty_unit': 'sq.m', 'unit_cost': cost
        })
    
    # ===== ส่วนพื้นทาง/รองพื้นทาง =====
    st.markdown("---")
    st.markdown("**พื้นทาง/รองพื้นทาง** (หน่วย: ลบ.ม. - เลือกจาก Library)")
    
    # Library วัสดุพื้นทาง
    base_materials = {
        'หินคลุก CBR 80%': {'unit_cost': 714, 'qty_unit': 'cu.m'},
        'หินคลุกผสมซีเมนต์ UCS 24.5 ksc': {'unit_cost': 914, 'qty_unit': 'cu.m'},
        'ดินซีเมนต์ UCS 17.5 ksc': {'unit_cost': 621, 'qty_unit': 'cu.m'},
        'พื้นทางซีเมนต์ CTB': {'unit_cost': 621, 'qty_unit': 'cu.m'},
        'วัสดุหมุนเวียน (Recycling)': {'unit_cost': 500, 'qty_unit': 'cu.m'},
        'รองพื้นทางวัสดุมวลรวม CBR 25%': {'unit_cost': 714, 'qty_unit': 'cu.m'},
        'วัสดุคัดเลือก ก': {'unit_cost': 450, 'qty_unit': 'cu.m'},
        'ทรายถมคันทาง': {'unit_cost': 361, 'qty_unit': 'cu.m'},
        'ดินถมคันทาง': {'unit_cost': 280, 'qty_unit': 'cu.m'},
    }
    material_names = list(base_materials.keys())
    
    # จำนวนชั้นพื้นทาง (สูงสุด 5 ชั้น)
    num_base = st.number_input("จำนวนชั้นพื้นทาง/รองพื้นทาง", value=len(base_layers), 
                                min_value=1, max_value=5, key=f"{key_prefix}_num_base")
    
    cols = st.columns([3, 1, 1.5, 1.5])
    cols[0].markdown("วัสดุ")
    cols[1].markdown("หนา (cm)")
    cols[2].markdown("ปริมาณ (auto)")
    cols[3].markdown("ราคา/หน่วย")
    
    for i in range(int(num_base)):
        cols = st.columns([3, 1, 1.5, 1.5])
        
        # ค่า default
        if i < len(base_layers):
            default_name = base_layers[i]['name']
            default_thick = base_layers[i]['thickness']
            default_cost = base_layers[i]['unit_cost']
        else:
            default_name = material_names[0]
            default_thick = 20.0
            default_cost = 714.0
        
        # หา index ของวัสดุ default
        try:
            default_idx = material_names.index(default_name)
        except ValueError:
            default_idx = 0
        
        with cols[0]:
            selected = st.selectbox("วัสดุ", material_names, index=default_idx,
                key=f"{key_prefix}_bm_{i}", label_visibility="collapsed")
        with cols[1]:
            thick = st.number_input("หนา", value=float(default_thick),
                key=f"{key_prefix}_bt_{i}", label_visibility="collapsed", min_value=0.0, step=5.0)
        
        # คำนวณปริมาณอัตโนมัติ (ลบ.ม.) = พื้นที่ × ความหนา/100
        auto_qty = area_per_km * road_length * thick / 100
        
        with cols[2]:
            st.text(f"{auto_qty:,.0f}")
        with cols[3]:
            lib_cost = base_materials[selected]['unit_cost']
            cost = st.number_input("ราคา", value=float(lib_cost),
                key=f"{key_prefix}_bc_{i}", label_visibility="collapsed", min_value=0.0, step=10.0)
        
        updated_layers.append({
            'name': selected, 'thickness': thick, 'unit': 'cm',
            'quantity': auto_qty, 'qty_unit': 'cu.m', 'unit_cost': cost
        })
    
    return updated_layers


def render_joint_editor(joints, key_prefix):
    """แสดง UI สำหรับแก้ไขรอยต่อ"""
    st.markdown("---")
    st.markdown("**รอยต่อ (Joints)**")
    
    cols = st.columns([3, 1.5, 1.5])
    cols[0].markdown("รายการ")
    cols[1].markdown("ปริมาณ (m)")
    cols[2].markdown("ราคา/หน่วย")
    
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
    
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#28A745', '#6F42C1']
    
    fig.add_trace(
        go.Bar(x=results_df['ประเภท'], y=results_df['NPV (ล้านบาท/กม.)'],
               marker_color=colors[:len(results_df)], text=results_df['NPV (ล้านบาท/กม.)'].apply(lambda x: f'{x:.2f}'),
               textposition='outside', name='NPV'),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(x=results_df['ประเภท'], y=results_df['ค่าก่อสร้าง'],
               marker_color='#2E86AB', name='ค่าก่อสร้าง'),
        row=1, col=2
    )
    
    maint_cost = results_df['NPV (ล้านบาท/กม.)'] - results_df['ค่าก่อสร้าง']
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
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#28A745', '#6F42C1']
    
    for i, (ptype, cf) in enumerate(zip(pavement_types, all_cash_flows)):
        years = [c['year'] for c in cf]
        cum_pv = [c['cumulative_pv'] for c in cf]
        fig.add_trace(go.Scatter(x=years, y=cum_pv, mode='lines',
                                  name=ptype, line=dict(color=colors[i % len(colors)], width=2)))
    
    fig.update_layout(
        title='Cumulative NPV ตลอดระยะเวลาวิเคราะห์',
        xaxis_title='ปี', yaxis_title='Cumulative NPV (ล้านบาท/กม.)',
        height=400, hovermode='x unified'
    )
    return fig


def generate_word_report_table(project_info, structure_type, structure_name, cbr, layers, joints, road_length):
    """สร้างรายงาน Word รูปแบบตารางค่าก่อสร้าง (ตามตัวอย่างในเอกสาร)"""
    doc = Document()
    
    # ตั้งค่า font
    style = doc.styles['Normal']
    style.font.name = 'TH SarabunPSK'
    style.font.size = Pt(14)
    
    # หัวข้อ
    title = doc.add_paragraph()
    title_run = title.add_run('ราคาค่าก่อสร้างของโครงสร้างชั้นทาง' + structure_name)
    title_run.bold = True
    title_run.font.size = Pt(16)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # ข้อมูล CBR
    info_text = f"ผิวจราจร{structure_type} กรณีชั้นดินเดิมมีค่า CBR = {cbr}%"
    doc.add_paragraph(info_text).alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # แยก layers เป็นกลุ่ม
    surface_layers = []
    base_layers = []
    for layer in layers:
        name_lower = layer['name'].lower()
        if any(x in name_lower for x in ['wearing', 'binder', 'asphalt', 'concrete', 'tack', 'prime', 'geotextile', 'steel']):
            surface_layers.append(layer)
        else:
            base_layers.append(layer)
    
    # คำนวณจำนวนแถว
    num_rows = 2 + len(surface_layers) + 1  # header + ผิวทาง header + items + รวม1
    if joints:
        num_rows += 1 + len(joints) + 1  # รอยต่อ header + items + รวม2
    num_rows += 1 + len(base_layers) + 1  # พื้นทาง header + items + รวม3
    num_rows += 2  # รวมทั้งหมด + สรุป
    
    table = doc.add_table(rows=num_rows, cols=7)
    table.style = 'Table Grid'
    
    # Header
    headers = ['ลำดับ', 'ค่าใช้จ่ายสำหรับวัสดุ', 'รายละเอียดหน่วย', 'ปริมาณต่อ', 'หน่วย', 'ราคาต่อหน่วย\n(บาท/หน่วย)', 'มูลค่า\n(บาท)']
    for j, h in enumerate(headers):
        table.rows[0].cells[j].text = h
    
    row_idx = 1
    running_total = 0
    
    # กลุ่ม 1: ผิวทาง
    table.rows[row_idx].cells[0].text = '1'
    table.rows[row_idx].cells[1].text = 'ผิวทาง'
    row_idx += 1
    
    surface_total = 0
    for i, layer in enumerate(surface_layers, 1):
        qty = layer['quantity'] * road_length
        cost = qty * layer['unit_cost']
        table.rows[row_idx].cells[0].text = f'1.{i}'
        table.rows[row_idx].cells[1].text = layer['name']
        table.rows[row_idx].cells[2].text = f"{layer['thickness']} {layer['unit']}"
        table.rows[row_idx].cells[3].text = f"{qty:,.0f}"
        table.rows[row_idx].cells[4].text = layer['qty_unit']
        table.rows[row_idx].cells[5].text = f"{layer['unit_cost']:,.0f}"
        table.rows[row_idx].cells[6].text = f"{cost:,.0f}"
        surface_total += cost
        row_idx += 1
    
    table.rows[row_idx].cells[1].text = 'รวม 1'
    table.rows[row_idx].cells[6].text = f"{surface_total:,.0f}"
    running_total += surface_total
    row_idx += 1
    
    # กลุ่ม 2: รอยต่อ
    joint_total = 0
    if joints:
        table.rows[row_idx].cells[0].text = '2'
        table.rows[row_idx].cells[1].text = 'รอยต่อ'
        row_idx += 1
        
        for i, joint in enumerate(joints, 1):
            qty = joint['quantity'] * road_length
            cost = qty * joint['unit_cost']
            table.rows[row_idx].cells[0].text = f'2.{i}'
            table.rows[row_idx].cells[1].text = joint['name']
            table.rows[row_idx].cells[3].text = f"{qty:,.0f}"
            table.rows[row_idx].cells[4].text = joint['qty_unit']
            table.rows[row_idx].cells[5].text = f"{joint['unit_cost']:,.0f}"
            table.rows[row_idx].cells[6].text = f"{cost:,.0f}"
            joint_total += cost
            row_idx += 1
        
        table.rows[row_idx].cells[1].text = 'รวม 2'
        table.rows[row_idx].cells[6].text = f"{joint_total:,.0f}"
        running_total += joint_total
        row_idx += 1
        group_num = 3
    else:
        group_num = 2
    
    # กลุ่ม 3: พื้นทางและรองพื้นทาง
    table.rows[row_idx].cells[0].text = str(group_num)
    table.rows[row_idx].cells[1].text = 'พื้นทางและรองพื้นทาง'
    row_idx += 1
    
    base_total = 0
    for i, layer in enumerate(base_layers, 1):
        qty = layer['quantity'] * road_length
        cost = qty * layer['unit_cost']
        table.rows[row_idx].cells[0].text = f'{group_num}.{i}'
        table.rows[row_idx].cells[1].text = layer['name']
        table.rows[row_idx].cells[2].text = f"{layer['thickness']} {layer['unit']}"
        table.rows[row_idx].cells[3].text = f"{qty:,.0f}"
        table.rows[row_idx].cells[4].text = layer['qty_unit']
        table.rows[row_idx].cells[5].text = f"{layer['unit_cost']:,.0f}"
        table.rows[row_idx].cells[6].text = f"{cost:,.0f}"
        base_total += cost
        row_idx += 1
    
    table.rows[row_idx].cells[1].text = f'รวม {group_num}'
    table.rows[row_idx].cells[6].text = f"{base_total:,.0f}"
    running_total += base_total
    row_idx += 1
    
    # รวมทั้งหมด
    sum_text = 'รวม 1+2+3' if joints else 'รวม 1+2'
    table.rows[row_idx].cells[1].text = sum_text
    table.rows[row_idx].cells[3].text = f"{running_total:,.0f}"
    table.rows[row_idx].cells[6].text = 'บาท'
    row_idx += 1
    
    # สรุปราคาต่อกิโลเมตร
    cost_per_km = running_total / road_length / 1_000_000
    table.rows[row_idx].cells[1].text = 'สรุปราคาต่อกิโลเมตรใน2ทิศทาง'
    table.rows[row_idx].cells[3].text = f"{cost_per_km:.2f}"
    table.rows[row_idx].cells[6].text = 'ล้านบาท'
    
    # Footer
    doc.add_paragraph()
    lane_width = project_info.get('lane_width', 3.5)
    shoulder_left = project_info.get('shoulder_left', 2.5)
    shoulder_right = project_info.get('shoulder_right', 1.5)
    total_width = project_info.get('total_width', 11.0)
    
    doc.add_paragraph(f"หมายเหตุ: ความกว้างช่องจราจร {lane_width} ม. ไหล่ทางซ้าย {shoulder_left} ม. ไหล่ทางขวา {shoulder_right} ม.")
    doc.add_paragraph(f"รวมทั้งสิ้นความกว้างถนน {total_width} ม. (ช่องละ {lane_width} ม.) ยาว {road_length} กิโลเมตร")
    doc.add_paragraph(f"รายงานสร้างเมื่อ: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    return doc


def generate_word_report(project_info, results_df, all_details):
    """สร้างรายงาน Word (สรุปรวม)"""
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
    headers = ['ประเภท', 'ค่าก่อสร้าง', 'NPV (ล้านบาท/กม.)', 'อันดับ']
    for j, h in enumerate(headers):
        table.rows[0].cells[j].text = h
    
    for i, row in results_df.iterrows():
        table.rows[i+1].cells[0].text = row['ประเภท']
        table.rows[i+1].cells[1].text = f"{row['ค่าก่อสร้าง']:.2f}"
        table.rows[i+1].cells[2].text = f"{row['NPV (ล้านบาท/กม.)']:.2f}"
        table.rows[i+1].cells[3].text = str(row['อันดับ'])
    
    best = results_df.loc[results_df['อันดับ'] == 1].iloc[0]
    doc.add_paragraph()
    doc.add_paragraph(f"สรุป: {best['ประเภท']} มีความคุ้มค่าที่สุด (NPV = {best['NPV (ล้านบาท/กม.)']:.2f} ล้านบาท/กม.)")
    doc.add_paragraph(f"รายงานสร้างเมื่อ: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    return doc


# ===== Main Application =====

def main():
    st.markdown('<div class="main-header">🛣️ ระบบวิเคราะห์ค่าก่อสร้างโครงสร้างชั้นทาง</div>', unsafe_allow_html=True)
    st.markdown("##### ตามแนวทาง AASHTO 1993 - รองรับ AC, JPCP/JRCP, CRCP")
    
    # Sidebar
    with st.sidebar:
        st.header("📋 ข้อมูลโครงการ")
        project_name = st.text_input("ชื่อโครงการ", value="โครงการก่อสร้างทางหลวง")
        road_length = st.number_input("ความยาวถนน (กม.)", value=1.0, min_value=0.1, step=0.1)
        
        st.divider()
        st.header("📐 ขนาดถนน")
        lane_width = st.number_input("ความกว้างช่องจราจร (ม.)", value=3.5, min_value=2.5, max_value=4.0, step=0.25)
        shoulder_left = st.number_input("ไหล่ทางซ้าย (ม.)", value=2.5, min_value=0.0, max_value=3.5, step=0.25)
        shoulder_right = st.number_input("ไหล่ทางขวา (ม.)", value=1.5, min_value=0.0, max_value=3.5, step=0.25)
        num_lanes = st.selectbox("จำนวนช่องจราจร (ต่อทิศทาง)", options=[1, 2, 3], index=0)
        
        # คำนวณความกว้างรวม (2 ทิศทาง)
        total_width = (lane_width * num_lanes * 2) + shoulder_left + shoulder_right
        st.info(f"📏 ความกว้างรวม: {total_width:.2f} ม.\n(ถนน 2 ทิศทาง)")
        
        st.divider()
        st.header("⚙️ พารามิเตอร์")
        cbr = st.selectbox("ค่า CBR ดินเดิม (%)", options=[2, 3, 4, 5, 6], index=0)
        discount_rate = st.number_input("Discount Rate (%)", value=5.0, min_value=1.0, max_value=15.0, step=0.5)
        analysis_period = st.number_input("ระยะเวลาวิเคราะห์ (ปี)", value=100, min_value=20, max_value=200, step=5)
    
    # เก็บข้อมูลโครงการ
    project_info = {
        'name': project_name,
        'length': road_length,
        'lane_width': lane_width,
        'shoulder_left': shoulder_left,
        'shoulder_right': shoulder_right,
        'num_lanes': num_lanes,
        'total_width': total_width,
        'cbr': cbr,
        'discount_rate': discount_rate,
        'analysis_period': analysis_period
    }
    
    # คำนวณพื้นที่ต่อ กม. (ใช้สำหรับคำนวณปริมาณ)
    area_per_km = total_width * 1000  # ตร.ม./กม.
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏗️ โครงสร้างชั้นทาง", "💰 ค่าบำรุงรักษา", "📈 ผลการวิเคราะห์", "📋 Cash Flow", "📄 รายงาน"])
    
    with tab1:
        st.header("กำหนดโครงสร้างชั้นทาง")
        st.info("💡 แก้ไขชื่อ ความหนา ปริมาณ และราคาต่อหน่วยได้ตามต้องการ")
        
        # ===== AC Pavement =====
        st.subheader("🔵 ผิวทางแอสฟัลต์คอนกรีต (AC)")
        col1, col2 = st.columns(2)
        
        with col1:
            ac1_name = st.text_input("ชื่อโครงสร้าง AC1", value="AC1: แอสฟัลต์บนหินคลุก", key="ac1_name")
            with st.expander(f"● {ac1_name}", expanded=True):
                ac1_layers = render_layer_editor(get_default_ac1_layers(), "ac1", total_width, road_length)
                ac1_cost, ac1_details = calculate_layer_cost(ac1_layers, road_length)
                ac1_cost_per_km = ac1_cost / road_length / 1_000_000
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {ac1_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
        
        with col2:
            ac2_name = st.text_input("ชื่อโครงสร้าง AC2", value="AC2: แอสฟัลต์บนหินคลุกผสมซีเมนต์", key="ac2_name")
            with st.expander(f"● {ac2_name}", expanded=True):
                ac2_layers = render_layer_editor(get_default_ac2_layers(), "ac2", total_width, road_length)
                ac2_cost, ac2_details = calculate_layer_cost(ac2_layers, road_length)
                ac2_cost_per_km = ac2_cost / road_length / 1_000_000
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {ac2_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
        
        # ===== JRCP/JPCP =====
        st.subheader("🟠 ผิวทางคอนกรีตเสริมเหล็ก (JRCP/JPCP)")
        col3, col4 = st.columns(2)
        
        with col3:
            jrcp1_name = st.text_input("ชื่อโครงสร้าง JRCP1", value="JRCP1: คอนกรีตบนดินซีเมนต์", key="jrcp1_name")
            with st.expander(f"● {jrcp1_name}", expanded=True):
                jrcp1_layers = render_layer_editor(get_default_jrcp1_layers(), "jrcp1", total_width, road_length)
                jrcp1_layer_cost, jrcp1_layer_details = calculate_layer_cost(jrcp1_layers, road_length)
                jrcp1_joints = render_joint_editor(get_default_jrcp1_joints(), "jrcp1")
                jrcp1_joint_cost, jrcp1_joint_details = calculate_joint_cost(jrcp1_joints, road_length)
                jrcp1_total = jrcp1_layer_cost + jrcp1_joint_cost
                jrcp1_cost_per_km = jrcp1_total / road_length / 1_000_000
                jrcp1_details = jrcp1_layer_details + jrcp1_joint_details
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {jrcp1_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
        
        with col4:
            jrcp2_name = st.text_input("ชื่อโครงสร้าง JRCP2", value="JRCP2: คอนกรีตบนหินคลุกผสมซีเมนต์", key="jrcp2_name")
            with st.expander(f"● {jrcp2_name}", expanded=True):
                jrcp2_layers = render_layer_editor(get_default_jrcp2_layers(), "jrcp2", total_width, road_length)
                jrcp2_layer_cost, jrcp2_layer_details = calculate_layer_cost(jrcp2_layers, road_length)
                jrcp2_joints = render_joint_editor(get_default_jrcp1_joints(), "jrcp2")
                jrcp2_joint_cost, jrcp2_joint_details = calculate_joint_cost(jrcp2_joints, road_length)
                jrcp2_total = jrcp2_layer_cost + jrcp2_joint_cost
                jrcp2_cost_per_km = jrcp2_total / road_length / 1_000_000
                jrcp2_details = jrcp2_layer_details + jrcp2_joint_details
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {jrcp2_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
        
        # ===== CRCP =====
        st.subheader("🔴 ผิวทางคอนกรีตเสริมเหล็กต่อเนื่อง (CRCP)")
        col5, col6 = st.columns(2)
        
        with col5:
            crcp1_name = st.text_input("ชื่อโครงสร้าง CRCP1", value="CRCP1: คอนกรีตเสริมเหล็กต่อเนื่องบนดินซีเมนต์", key="crcp1_name")
            with st.expander(f"● {crcp1_name}", expanded=True):
                crcp1_layers = render_layer_editor(get_default_crcp1_layers(), "crcp1", total_width, road_length)
                crcp1_cost, crcp1_details = calculate_layer_cost(crcp1_layers, road_length)
                crcp1_cost_per_km = crcp1_cost / road_length / 1_000_000
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {crcp1_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
        
        with col6:
            crcp2_name = st.text_input("ชื่อโครงสร้าง CRCP2", value="CRCP2: คอนกรีตเสริมเหล็กต่อเนื่องบน CMCR", key="crcp2_name")
            with st.expander(f"● {crcp2_name}", expanded=True):
                crcp2_layers = render_layer_editor(get_default_crcp2_layers(), "crcp2", total_width, road_length)
                crcp2_cost, crcp2_details = calculate_layer_cost(crcp2_layers, road_length)
                crcp2_cost_per_km = crcp2_cost / road_length / 1_000_000
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {crcp2_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
        
        # Store in session state
        st.session_state['construction'] = {
            'AC1': {'name': ac1_name, 'cost': ac1_cost_per_km, 'details': ac1_details, 'layers': ac1_layers, 'joints': None},
            'AC2': {'name': ac2_name, 'cost': ac2_cost_per_km, 'details': ac2_details, 'layers': ac2_layers, 'joints': None},
            'JRCP1': {'name': jrcp1_name, 'cost': jrcp1_cost_per_km, 'details': jrcp1_details, 'layers': jrcp1_layers, 'joints': jrcp1_joints},
            'JRCP2': {'name': jrcp2_name, 'cost': jrcp2_cost_per_km, 'details': jrcp2_details, 'layers': jrcp2_layers, 'joints': jrcp2_joints},
            'CRCP1': {'name': crcp1_name, 'cost': crcp1_cost_per_km, 'details': crcp1_details, 'layers': crcp1_layers, 'joints': None},
            'CRCP2': {'name': crcp2_name, 'cost': crcp2_cost_per_km, 'details': crcp2_details, 'layers': crcp2_layers, 'joints': None},
        }
        st.session_state['project_info'] = project_info
        
        # Summary table
        st.divider()
        st.subheader("📊 สรุปค่าก่อสร้าง")
        summary_df = pd.DataFrame({
            'ประเภท': [ac1_name, ac2_name, jrcp1_name, jrcp2_name, crcp1_name, crcp2_name],
            'ค่าก่อสร้าง (ล้านบาท/กม.)': [ac1_cost_per_km, ac2_cost_per_km, jrcp1_cost_per_km, jrcp2_cost_per_km, crcp1_cost_per_km, crcp2_cost_per_km],
            'อายุออกแบบ (ปี)': [20, 20, 25, 25, 30, 30]
        })
        st.dataframe(summary_df.style.format({'ค่าก่อสร้าง (ล้านบาท/กม.)': '{:.2f}'}), use_container_width=True)
    
    with tab2:
        st.header("กำหนดค่าบำรุงรักษา")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("🔵 AC Pavement")
            ac_seal = st.number_input("Seal Coating ทุก 3 ปี (ล้านบาท/กม.)", value=1.76, key="m_seal")
            ac_overlay = st.number_input("Overlay 5cm ทุก 9 ปี (ล้านบาท/กม.)", value=8.80, key="m_overlay")
            st.markdown("**อายุ 20 ปี:** Seal ปี 3,6,12,15 | Overlay ปี 9,18")
        
        with col2:
            st.subheader("🟠 JRCP/JPCP")
            jrcp_joint = st.number_input("Joint Sealing ทุก 3 ปี (ล้านบาท/กม.)", value=1.426, key="m_joint")
            st.markdown("**อายุ 25 ปี:** Joint Seal ทุก 3 ปี")
        
        with col3:
            st.subheader("🔴 CRCP")
            crcp_maint = st.number_input("บำรุงรักษาทุก 5 ปี (ล้านบาท/กม.)", value=0.50, key="m_crcp")
            st.markdown("**อายุ 30 ปี:** บำรุงรักษาทุก 5 ปี")
        
        st.session_state['maintenance'] = {
            'ac_seal': ac_seal, 'ac_overlay': ac_overlay, 'jrcp_joint': jrcp_joint, 'crcp_maint': crcp_maint
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
                crcp1_c = constr.get('CRCP1', {}).get('cost', 30.00)
                crcp2_c = constr.get('CRCP2', {}).get('cost', 31.00)
                
                seal = maint.get('ac_seal', 1.76)
                overlay = maint.get('ac_overlay', 8.80)
                joint = maint.get('jrcp_joint', 1.426)
                crcp_m = maint.get('crcp_maint', 0.50)
                
                r = discount_rate / 100
                
                npv1, cf1 = calculate_npv_ac(ac1_c, seal, overlay, 20, analysis_period, r)
                npv2, cf2 = calculate_npv_ac(ac2_c, seal, overlay, 20, analysis_period, r)
                npv3, cf3 = calculate_npv_jrcp(jrcp1_c, joint, 25, analysis_period, r)
                npv4, cf4 = calculate_npv_jrcp(jrcp2_c, joint, 25, analysis_period, r)
                npv5, cf5 = calculate_npv_crcp(crcp1_c, crcp_m, 30, analysis_period, r)
                npv6, cf6 = calculate_npv_crcp(crcp2_c, crcp_m, 30, analysis_period, r)
                
                # ดึงชื่อที่กำหนดเอง
                ac1_name = constr.get('AC1', {}).get('name', 'AC1')
                ac2_name = constr.get('AC2', {}).get('name', 'AC2')
                jrcp1_name = constr.get('JRCP1', {}).get('name', 'JRCP1')
                jrcp2_name = constr.get('JRCP2', {}).get('name', 'JRCP2')
                crcp1_name = constr.get('CRCP1', {}).get('name', 'CRCP1')
                crcp2_name = constr.get('CRCP2', {}).get('name', 'CRCP2')
                
                results = [
                    {'ประเภท': ac1_name, 'ค่าก่อสร้าง': ac1_c, 'อายุ': 20, 'NPV (ล้านบาท/กม.)': npv1},
                    {'ประเภท': ac2_name, 'ค่าก่อสร้าง': ac2_c, 'อายุ': 20, 'NPV (ล้านบาท/กม.)': npv2},
                    {'ประเภท': jrcp1_name, 'ค่าก่อสร้าง': jrcp1_c, 'อายุ': 25, 'NPV (ล้านบาท/กม.)': npv3},
                    {'ประเภท': jrcp2_name, 'ค่าก่อสร้าง': jrcp2_c, 'อายุ': 25, 'NPV (ล้านบาท/กม.)': npv4},
                    {'ประเภท': crcp1_name, 'ค่าก่อสร้าง': crcp1_c, 'อายุ': 30, 'NPV (ล้านบาท/กม.)': npv5},
                    {'ประเภท': crcp2_name, 'ค่าก่อสร้าง': crcp2_c, 'อายุ': 30, 'NPV (ล้านบาท/กม.)': npv6},
                ]
                
                results_df = pd.DataFrame(results)
                results_df['อันดับ'] = results_df['NPV (ล้านบาท/กม.)'].rank().astype(int)
                results_df = results_df.sort_values('อันดับ')
                
                st.session_state['results_df'] = results_df
                st.session_state['all_cf'] = [cf1, cf2, cf3, cf4, cf5, cf6]
                st.session_state['ptypes'] = [ac1_name, ac2_name, jrcp1_name, jrcp2_name, crcp1_name, crcp2_name]
        
        if 'results_df' in st.session_state:
            df = st.session_state['results_df']
            best = df.loc[df['อันดับ'] == 1].iloc[0]
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🏆 ทางเลือกที่ดีที่สุด", best['ประเภท'])
            c2.metric("💰 NPV ต่ำสุด", f"{best['NPV (ล้านบาท/กม.)']:.2f}")
            c3.metric("💵 ประหยัด", f"{df['NPV (ล้านบาท/กม.)'].max() - best['NPV (ล้านบาท/กม.)']:.2f}")
            c4.metric("📅 Discount Rate", f"{discount_rate}%")
            
            st.divider()
            st.subheader("📊 ตารางเปรียบเทียบ")
            st.dataframe(df.style.format({'ค่าก่อสร้าง': '{:.2f}', 'NPV (ล้านบาท/กม.)': '{:.2f}'})
                        .background_gradient(subset=['NPV (ล้านบาท/กม.)'], cmap='RdYlGn_r'),
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
