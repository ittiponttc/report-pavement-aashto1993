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


# ===== Library ราคาวัสดุ (Price Library) =====
# ข้อมูลจากไฟล์ ราคาเปรียบเทียบโครงสร้างชั้นทาง

# ตารางราคาผิวทาง AC (บาท/ตร.ม.) ตามความหนา
AC_PRICE_TABLE = {
    'PMA Wearing Course': {
        2.5: 170, 3: 203, 4: 268, 5: 333, 6: 406, 7: 471, 8: 536, 9: 601, 10: 667
    },
    'AC Wearing Course': {
        2.5: 128, 3: 152, 4: 202, 5: 250, 6: 306, 7: 355, 8: 403, 9: 452, 10: 502
    },
    'AC Binder Course': {
        2.5: 129, 3: 154, 4: 202, 5: 251, 6: 308, 7: 356, 8: 405, 9: 454, 10: 503
    },
    'AC Base Course': {
        2.5: 129, 3: 154, 4: 202, 5: 251, 6: 308, 7: 356, 8: 405, 9: 454, 10: 503
    },
}

# ตารางราคาคอนกรีต (บาท/ตร.ม.) ตามความหนา
CONCRETE_PRICE_TABLE = {
    'JRCP': {25: 924, 28: 1002, 32: 1106, 35: 1184},
    'JPCP': {25: 928, 28: 1000, 32: 1095, 35: 1167},
    'CRCP': {25: 1245, 28: 1358, 32: 1509, 35: 1622},
}

# ราคาคอนกรีต (ไม่รวม Joint)
CONCRETE_EXCL_JOINT = {
    'JRCP': 830,
    'JPCP': 764,
    'CRCP': 1204,
}

# ราคาวัสดุพื้นทาง/รองพื้นทาง (บาท/ลบ.ม.)
BASE_MATERIAL_PRICES = {
    'Crushed Rock Base Course': 583,
    'Cement Modified Crushed Rock Base (UCS 24.5 ksc)': 864,
    'Cement Treated Base (UCS 40 ksc)': 1096,
    'Soil Aggregate Subbase': 375,
    'Soil Cement Subbase (UCS 7 ksc)': 854,
    'Selected Material A': 375,
}

# Library วัสดุ (สำหรับ UI)
MATERIAL_LIBRARY = {
    'ผิวทาง': {
        'ผิวทางลาดยาง AC': {'unit_cost': 480, 'cost_unit': 'บาท/ตร.ม.'},
        'ผิวทางลาดยาง PMA': {'unit_cost': 550, 'cost_unit': 'บาท/ตร.ม.'},
        'คอนกรีต 350 Ksc.': {'unit_cost': 800, 'cost_unit': 'บาท/ตร.ม.'},
        'คอนกรีต 350 Ksc.': {'unit_cost': 850, 'cost_unit': 'บาท/ตร.ม.'},
    },
    'พื้นทาง': {
        'Crushed Rock Base Course': {'unit_cost': 583, 'cost_unit': 'บาท/ลบ.ม.'},
        'Cement Modified Crushed Rock Base (UCS 24.5 ksc)': {'unit_cost': 864, 'cost_unit': 'บาท/ลบ.ม.'},
        'Cement Treated Base (UCS 40 ksc)': {'unit_cost': 1096, 'cost_unit': 'บาท/ลบ.ม.'},
        'Soil Cement Subbase (UCS 7 ksc)': {'unit_cost': 854, 'cost_unit': 'บาท/ลบ.ม.'},
    },
    'รองพื้นทาง': {
        'Soil Aggregate Subbase': {'unit_cost': 375, 'cost_unit': 'บาท/ลบ.ม.'},
        'Selected Material A': {'unit_cost': 375, 'cost_unit': 'บาท/ลบ.ม.'},
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
        {'name': '350 Ksc. Cubic Type Concrete', 'thickness': 28, 'unit': 'cm', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 800},
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
        {'name': '350 Ksc. Cubic Type Concrete', 'thickness': 28, 'unit': 'cm', 'quantity': 22000, 'qty_unit': 'sq.m', 'unit_cost': 800},
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
    """คำนวณค่าก่อสร้างจากชั้นโครงสร้าง
    ราคาทั้งหมดเป็น บาท/ตร.ม. × ปริมาณ (ตร.ม.)
    """
    total = 0
    details = []
    
    for layer in layers:
        # ปริมาณเป็น ตร.ม. แล้ว (ไม่ต้องคูณ road_length อีก เพราะคำนวณไว้แล้ว)
        qty = layer['quantity']
        # ราคาเป็น บาท/ตร.ม.
        cost = qty * layer['unit_cost']
        total += cost
        
        details.append({
            'รายการ': layer['name'],
            'ความหนา': f"{layer['thickness']} {layer['unit']}",
            'ปริมาณ': qty,
            'หน่วย': 'ตร.ม.',
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


def get_price_from_library(layer_name, thickness):
    """ดึงราคาจาก Library ตามชื่อและความหนา"""
    if 'price_library' not in st.session_state:
        return None
    
    lib = st.session_state['price_library']
    name_lower = layer_name.lower()
    
    # AC Prices
    if 'pma' in name_lower and 'wearing' in name_lower:
        return lib['ac_prices'].get('PMA Wearing Course', {}).get(thickness)
    elif 'wearing' in name_lower:
        return lib['ac_prices'].get('AC Wearing Course', {}).get(thickness)
    elif 'binder' in name_lower:
        return lib['ac_prices'].get('AC Binder Course', {}).get(thickness)
    elif 'asphalt' in name_lower and 'base' in name_lower:
        return lib['ac_prices'].get('AC Base Course', {}).get(thickness)
    
    # Concrete Prices
    elif 'jrcp' in name_lower or ('concrete' in name_lower and 'jrcp' in str(thickness)):
        return lib['concrete_prices'].get('JRCP', {}).get(int(thickness))
    elif 'jpcp' in name_lower:
        return lib['concrete_prices'].get('JPCP', {}).get(int(thickness))
    elif 'crcp' in name_lower:
        return lib['concrete_prices'].get('CRCP', {}).get(int(thickness))
    
    # Base Material Prices
    elif 'crushed rock' in name_lower and 'cement' not in name_lower:
        return lib['base_prices'].get('Crushed Rock Base Course')
    elif 'cement modified' in name_lower or 'cmcr' in name_lower:
        return lib['base_prices'].get('Cement Modified Crushed Rock Base (UCS 24.5 ksc)')
    elif 'cement treated' in name_lower or 'ctb' in name_lower:
        return lib['base_prices'].get('Cement Treated Base (UCS 40 ksc)')
    elif 'soil aggregate' in name_lower:
        return lib['base_prices'].get('Soil Aggregate Subbase')
    elif 'soil cement' in name_lower:
        return lib['base_prices'].get('Soil Cement Subbase (UCS 7 ksc)')
    elif 'selected' in name_lower:
        return lib['base_prices'].get('Selected Material A')
    
    return None


def render_layer_editor(layers, key_prefix, total_width, road_length):
    """แสดง UI สำหรับแก้ไขโครงสร้างชั้นทาง พร้อมคำนวณปริมาณอัตโนมัติ
    ราคาทั้งหมดแสดงเป็น บาท/ตร.ม.
    """
    updated_layers = []
    
    # คำนวณพื้นที่ต่อ กม. 
    area_per_km = total_width * 1000 * 2  # ตร.ม./กม. (2 ทิศทาง)
    
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
    cols[1].markdown("หนา (cm)")
    cols[2].markdown("ปริมาณ (auto)")
    cols[3].markdown("ราคา (บาท/ตร.ม.)")
    
    # ตัวเลือกวัสดุ
    wearing_options = ['AC Wearing Course', 'PMA Wearing Course']
    binder_options = ['AC Binder Course']
    base_options = ['AC Base Course']
    concrete_options = ['JPCP', 'JRCP', 'CRCP']
    
    for i, layer in enumerate(surface_layers):
        cols = st.columns([3, 1, 1.5, 1.5])
        name_lower = layer['name'].lower()
        
        # กำหนดว่าเป็นชั้นไหน
        is_wearing = 'wearing' in name_lower
        is_binder = 'binder' in name_lower
        is_ac_base = 'asphalt' in name_lower and 'base' in name_lower
        is_concrete = 'concrete' in name_lower or 'ksc' in name_lower
        
        with cols[0]:
            if is_wearing:
                # Dropdown เลือก PMA หรือ AC Wearing
                default_idx = 1 if 'pma' in name_lower else 0
                selected_material = st.selectbox(
                    "วัสดุ", wearing_options, index=default_idx,
                    key=f"{key_prefix}_mat_{i}", label_visibility="collapsed"
                )
            elif is_binder:
                selected_material = st.selectbox(
                    "วัสดุ", binder_options, index=0,
                    key=f"{key_prefix}_mat_{i}", label_visibility="collapsed"
                )
            elif is_ac_base:
                selected_material = st.selectbox(
                    "วัสดุ", base_options, index=0,
                    key=f"{key_prefix}_mat_{i}", label_visibility="collapsed"
                )
            elif is_concrete:
                # Dropdown เลือก JPCP, JRCP, CRCP
                if 'jrcp' in key_prefix:
                    default_idx = 1  # JRCP
                elif 'crcp' in key_prefix:
                    default_idx = 2  # CRCP
                else:
                    default_idx = 0  # JPCP
                selected_type = st.selectbox(
                    "ชนิด", concrete_options, index=default_idx,
                    key=f"{key_prefix}_ctype_{i}", label_visibility="collapsed"
                )
                selected_material = f"350 Ksc. Cubic Type Concrete ({selected_type})"
            else:
                st.text(layer['name'])
                selected_material = layer['name']
        
        with cols[1]:
            thick = st.number_input("หนา", value=float(layer['thickness']),
                key=f"{key_prefix}_st_{i}", label_visibility="collapsed", min_value=0.0, step=1.0)
        
        # คำนวณปริมาณอัตโนมัติ (ตร.ม.)
        auto_qty = area_per_km * road_length
        
        # ดึงราคาจาก Library (บาท/ตร.ม.) ตามวัสดุและความหนาที่เลือก
        lib_price = None
        if 'price_library' in st.session_state:
            lib = st.session_state['price_library']
            
            if is_wearing:
                prices = lib['ac_prices'].get(selected_material, {})
                lib_price = prices.get(thick)
                if lib_price is None and prices:
                    closest = min(prices.keys(), key=lambda x: abs(x - thick))
                    lib_price = prices.get(closest)
            elif is_binder:
                prices = lib['ac_prices'].get('AC Binder Course', {})
                lib_price = prices.get(thick)
                if lib_price is None and prices:
                    closest = min(prices.keys(), key=lambda x: abs(x - thick))
                    lib_price = prices.get(closest)
            elif is_ac_base:
                prices = lib['ac_prices'].get('AC Base Course', {})
                lib_price = prices.get(thick)
                if lib_price is None and prices:
                    closest = min(prices.keys(), key=lambda x: abs(x - thick))
                    lib_price = prices.get(closest)
            elif is_concrete:
                # ดึงราคาคอนกรีตจาก Library
                concrete_type = selected_type if 'selected_type' in dir() else 'JPCP'
                prices = lib['concrete_prices'].get(concrete_type, {})
                lib_price = prices.get(int(thick))
                if lib_price is None and prices:
                    closest = min(prices.keys(), key=lambda x: abs(x - thick))
                    lib_price = prices.get(closest)
        
        # ใช้ราคาจาก Library หรือค่า default
        default_cost = lib_price if lib_price else layer['unit_cost']
        
        with cols[2]:
            st.text(f"{auto_qty:,.0f}")
        with cols[3]:
            st.markdown(f"**{default_cost:,.2f}**")
        
        # เก็บชื่อที่ถูกต้อง
        if is_concrete:
            final_name = selected_material
        elif is_wearing or is_binder or is_ac_base:
            final_name = selected_material
        else:
            final_name = layer['name']
        
        updated_layers.append({
            'name': final_name, 'thickness': thick, 'unit': layer['unit'],
            'quantity': auto_qty, 'qty_unit': 'sq.m', 'unit_cost': default_cost,
            'cost_per_sqm': default_cost
        })
    
    # ===== ส่วนพื้นทาง/รองพื้นทาง =====
    st.markdown("---")
    st.markdown("**พื้นทาง/รองพื้นทาง** (ราคาแสดงเป็น บาท/ตร.ม.)")
    
    # Library วัสดุพื้นทาง (ดึงจาก session_state หรือใช้ค่า default)
    # ราคาใน Library เป็น บาท/ลบ.ม.
    if 'price_library' in st.session_state:
        base_lib = st.session_state['price_library']['base_prices']
        base_materials = {
            'Crushed Rock Base Course': {'unit_cost_cum': base_lib.get('Crushed Rock Base Course', 583)},
            'Cement Modified Crushed Rock Base (UCS 24.5 ksc)': {'unit_cost_cum': base_lib.get('Cement Modified Crushed Rock Base (UCS 24.5 ksc)', 864)},
            'Cement Treated Base (UCS 40 ksc)': {'unit_cost_cum': base_lib.get('Cement Treated Base (UCS 40 ksc)', 1096)},
            'Soil Cement Subbase (UCS 7 ksc)': {'unit_cost_cum': base_lib.get('Soil Cement Subbase (UCS 7 ksc)', 854)},
            'Soil Aggregate Subbase': {'unit_cost_cum': base_lib.get('Soil Aggregate Subbase', 375)},
            'Selected Material A': {'unit_cost_cum': base_lib.get('Selected Material A', 375)},
        }
    else:
        base_materials = {
            'Crushed Rock Base Course': {'unit_cost_cum': 583},
            'Cement Modified Crushed Rock Base (UCS 24.5 ksc)': {'unit_cost_cum': 864},
            'Cement Treated Base (UCS 40 ksc)': {'unit_cost_cum': 1096},
            'Soil Cement Subbase (UCS 7 ksc)': {'unit_cost_cum': 854},
            'Soil Aggregate Subbase': {'unit_cost_cum': 375},
            'Selected Material A': {'unit_cost_cum': 375},
        }
    material_names = list(base_materials.keys())
    
    # จำนวนชั้นพื้นทาง (สูงสุด 5 ชั้น)
    num_base = st.number_input("จำนวนชั้นพื้นทาง/รองพื้นทาง", value=len(base_layers), 
                                min_value=1, max_value=5, key=f"{key_prefix}_num_base")
    
    cols = st.columns([3, 1, 1.5, 1.5])
    cols[0].markdown("วัสดุ")
    cols[1].markdown("หนา (cm)")
    cols[2].markdown("ปริมาณ (ตร.ม.)")
    cols[3].markdown("ราคา (บาท/ตร.ม.)")
    
    for i in range(int(num_base)):
        cols = st.columns([3, 1, 1.5, 1.5])
        
        # ค่า default
        if i < len(base_layers):
            default_name = base_layers[i]['name']
            default_thick = base_layers[i]['thickness']
        else:
            default_name = material_names[0]
            default_thick = 20.0
        
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
        
        # ปริมาณ = พื้นที่ (ตร.ม.) - ไม่ใช่ ลบ.ม. อีกต่อไป
        auto_qty = area_per_km * road_length
        
        # แปลงราคา: บาท/ลบ.ม. → บาท/ตร.ม.
        # ราคา บาท/ตร.ม. = ราคา บาท/ลบ.ม. × ความหนา (ม.) = ราคา × หนา/100
        lib_cost_cum = base_materials[selected]['unit_cost_cum']  # บาท/ลบ.ม.
        cost_per_sqm = lib_cost_cum * thick / 100  # บาท/ตร.ม.
        
        with cols[2]:
            st.text(f"{auto_qty:,.0f}")
        with cols[3]:
            # แสดงราคาที่คำนวณแล้ว (อัพเดทตามความหนาอัตโนมัติ)
            st.markdown(f"**{cost_per_sqm:,.2f}**")
        
        updated_layers.append({
            'name': selected, 'thickness': thick, 'unit': 'cm',
            'quantity': auto_qty, 'qty_unit': 'sq.m', 'unit_cost': cost_per_sqm,
            'cost_per_sqm': cost_per_sqm,  # ราคาต่อ ตร.ม.
            'cost_cum': lib_cost_cum  # เก็บราคา ลบ.ม. ไว้อ้างอิง
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
        num_lanes = st.selectbox("จำนวนช่องจราจร (รวม 2 ทิศทาง)", options=[2, 4, 6], index=0)
        shoulder_left = st.number_input("ไหล่ทางซ้าย (ม.)", value=2.5, min_value=0.0, max_value=3.5, step=0.25)
        shoulder_right = st.number_input("ไหล่ทางขวา (ม.)", value=1.5, min_value=0.0, max_value=3.5, step=0.25)
        
        # คำนวณความกว้างรวม
        # ความกว้างผิวจราจร = ช่องจราจร × จำนวนช่อง
        # ความกว้างรวม = ผิวจราจร + ไหล่ทางซ้าย + ไหล่ทางขวา
        road_surface_width = lane_width * num_lanes
        total_width = road_surface_width + shoulder_left + shoulder_right
        st.info(f"📏 ความกว้างผิวจราจร: {road_surface_width:.2f} ม.\n📏 ความกว้างรวม (รวมไหล่ทาง): {total_width:.2f} ม.")
        
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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Library ราคา", 
        "🏗️ โครงสร้างชั้นทาง", 
        "💰 ค่าบำรุงรักษา", 
        "📈 ผลการวิเคราะห์", 
        "📋 Cash Flow", 
        "📄 รายงาน",
        "📷 วิเคราะห์จากรูปภาพ"
    ])
    
    # ===== Tab 1: Library ราคา =====
    with tab1:
        st.header("📊 ตารางราคาเปรียบเทียบโครงสร้างชั้นทาง")
        st.info("💡 สามารถปรับเปลี่ยนราคาได้ตามต้องการ ราคาจะถูกใช้ในการคำนวณทุก Tab")
        
        # เก็บราคาใน session state
        if 'price_library' not in st.session_state:
            st.session_state['price_library'] = {
                'ac_prices': dict(AC_PRICE_TABLE),
                'concrete_prices': dict(CONCRETE_PRICE_TABLE),
                'base_prices': dict(BASE_MATERIAL_PRICES),
            }
        
        # ===== ส่วนผิวทาง AC =====
        st.subheader("🔵 ผิวทาง Asphalt Concrete (บาท/ตร.ม.)")
        
        ac_cols = st.columns(4)
        ac_types = ['PMA Wearing Course', 'AC Wearing Course', 'AC Binder Course', 'AC Base Course']
        thicknesses = [2.5, 3, 4, 5, 6, 7, 8, 9, 10]
        
        for col_idx, ac_type in enumerate(ac_types):
            with ac_cols[col_idx]:
                st.markdown(f"**{ac_type}**")
                for thk in thicknesses:
                    default_price = AC_PRICE_TABLE[ac_type].get(thk, 0)
                    price = st.number_input(
                        f"{thk} cm", 
                        value=float(default_price),
                        key=f"ac_{ac_type}_{thk}",
                        step=10.0,
                        label_visibility="visible"
                    )
                    st.session_state['price_library']['ac_prices'][ac_type][thk] = price
        
        st.divider()
        
        # ===== ส่วนคอนกรีต =====
        st.subheader("🟠 ผิวทางคอนกรีต (บาท/ตร.ม.)")
        
        conc_cols = st.columns(3)
        conc_types = ['JRCP', 'JPCP', 'CRCP']
        conc_thicknesses = [25, 28, 32, 35]
        
        for col_idx, conc_type in enumerate(conc_types):
            with conc_cols[col_idx]:
                st.markdown(f"**{conc_type}**")
                for thk in conc_thicknesses:
                    default_price = CONCRETE_PRICE_TABLE[conc_type].get(thk, 0)
                    price = st.number_input(
                        f"{thk} cm", 
                        value=float(default_price),
                        key=f"conc_{conc_type}_{thk}",
                        step=10.0
                    )
                    st.session_state['price_library']['concrete_prices'][conc_type][thk] = price
                
                # ราคาไม่รวม Joint
                st.markdown("---")
                excl_price = st.number_input(
                    f"{conc_type} (excl. Joint)",
                    value=float(CONCRETE_EXCL_JOINT[conc_type]),
                    key=f"conc_excl_{conc_type}",
                    step=10.0
                )
        
        st.divider()
        
        # ===== ส่วนวัสดุพื้นทาง/รองพื้นทาง =====
        st.subheader("🟤 วัสดุพื้นทาง/รองพื้นทาง (บาท/ลบ.ม.)")
        
        base_cols = st.columns(3)
        base_materials_list = list(BASE_MATERIAL_PRICES.keys())
        
        for i, mat in enumerate(base_materials_list):
            with base_cols[i % 3]:
                default_price = BASE_MATERIAL_PRICES[mat]
                price = st.number_input(
                    mat,
                    value=float(default_price),
                    key=f"base_{mat}",
                    step=10.0
                )
                st.session_state['price_library']['base_prices'][mat] = price
        
        st.divider()
        
        # ===== ปุ่มดาวน์โหลด =====
        st.subheader("📥 ดาวน์โหลดตารางราคา")
        
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            if st.button("📊 สร้างไฟล์ Excel", key="btn_excel_price", use_container_width=True):
                # สร้าง Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Sheet 1: AC Prices
                    ac_data = []
                    for ac_type in ac_types:
                        for thk in thicknesses:
                            ac_data.append({
                                'ประเภท': ac_type,
                                'ความหนา (cm)': thk,
                                'ราคา (บาท/ตร.ม.)': st.session_state['price_library']['ac_prices'][ac_type][thk]
                            })
                    pd.DataFrame(ac_data).to_excel(writer, sheet_name='AC Prices', index=False)
                    
                    # Sheet 2: Concrete Prices
                    conc_data = []
                    for conc_type in conc_types:
                        for thk in conc_thicknesses:
                            conc_data.append({
                                'ประเภท': conc_type,
                                'ความหนา (cm)': thk,
                                'ราคา (บาท/ตร.ม.)': st.session_state['price_library']['concrete_prices'][conc_type][thk]
                            })
                    pd.DataFrame(conc_data).to_excel(writer, sheet_name='Concrete Prices', index=False)
                    
                    # Sheet 3: Base Material Prices
                    base_data = [{'วัสดุ': k, 'ราคา (บาท/ลบ.ม.)': v} for k, v in st.session_state['price_library']['base_prices'].items()]
                    pd.DataFrame(base_data).to_excel(writer, sheet_name='Base Materials', index=False)
                
                output.seek(0)
                st.download_button(
                    label="⬇️ Download Excel",
                    data=output,
                    file_name="ราคาเปรียบเทียบโครงสร้างชั้นทาง.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        with col_dl2:
            if st.button("📄 สร้างไฟล์ Word", key="btn_word_price", use_container_width=True):
                doc = Document()
                doc.add_heading('ตารางราคาเปรียบเทียบโครงสร้างชั้นทาง', 0)
                
                # AC Table
                doc.add_heading('1. ผิวทาง Asphalt Concrete (บาท/ตร.ม.)', level=1)
                table = doc.add_table(rows=len(thicknesses)+1, cols=5)
                table.style = 'Table Grid'
                headers = ['ความหนา (cm)'] + ac_types
                for j, h in enumerate(headers):
                    table.rows[0].cells[j].text = h
                for i, thk in enumerate(thicknesses):
                    table.rows[i+1].cells[0].text = str(thk)
                    for j, ac_type in enumerate(ac_types):
                        table.rows[i+1].cells[j+1].text = f"{st.session_state['price_library']['ac_prices'][ac_type][thk]:,.0f}"
                
                # Concrete Table
                doc.add_heading('2. ผิวทางคอนกรีต (บาท/ตร.ม.)', level=1)
                table = doc.add_table(rows=len(conc_thicknesses)+1, cols=4)
                table.style = 'Table Grid'
                headers = ['ความหนา (cm)'] + conc_types
                for j, h in enumerate(headers):
                    table.rows[0].cells[j].text = h
                for i, thk in enumerate(conc_thicknesses):
                    table.rows[i+1].cells[0].text = str(thk)
                    for j, conc_type in enumerate(conc_types):
                        table.rows[i+1].cells[j+1].text = f"{st.session_state['price_library']['concrete_prices'][conc_type][thk]:,.0f}"
                
                # Base Material Table
                doc.add_heading('3. วัสดุพื้นทาง/รองพื้นทาง (บาท/ลบ.ม.)', level=1)
                table = doc.add_table(rows=len(base_materials_list)+1, cols=2)
                table.style = 'Table Grid'
                table.rows[0].cells[0].text = 'วัสดุ'
                table.rows[0].cells[1].text = 'ราคา (บาท/ลบ.ม.)'
                for i, mat in enumerate(base_materials_list):
                    table.rows[i+1].cells[0].text = mat
                    table.rows[i+1].cells[1].text = f"{st.session_state['price_library']['base_prices'][mat]:,.0f}"
                
                doc_output = io.BytesIO()
                doc.save(doc_output)
                doc_output.seek(0)
                st.download_button(
                    label="⬇️ Download Word",
                    data=doc_output,
                    file_name="ราคาเปรียบเทียบโครงสร้างชั้นทาง.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
    
    # ===== Tab 2: โครงสร้างชั้นทาง =====
    with tab2:
        st.header("กำหนดโครงสร้างชั้นทาง")
        st.info("💡 แก้ไขชื่อ ความหนา และราคาต่อหน่วยได้ตามต้องการ | ✅ เลือกโครงสร้างที่ต้องการแสดงในรายงาน")
        
        # คำนวณพื้นที่ต่อ กม.
        area_per_km = total_width * 1000 * 2  # ตร.ม./กม. (2 ทิศทาง)
        
        # ===== AC Pavement =====
        st.subheader("🔵 ผิวทางแอสฟัลต์คอนกรีต (AC)")
        col1, col2 = st.columns(2)
        
        with col1:
            ac1_show = st.checkbox("แสดงในรายงาน", value=True, key="ac1_show")
            ac1_name = st.text_input("ชื่อโครงสร้าง AC1", value="AC1: แอสฟัลต์บนหินคลุก", key="ac1_name")
            with st.expander(f"● {ac1_name}", expanded=True):
                ac1_layers = render_layer_editor(get_default_ac1_layers(), "ac1", total_width, road_length)
                ac1_cost, ac1_details = calculate_layer_cost(ac1_layers, road_length)
                ac1_cost_per_km = ac1_cost / road_length / 1_000_000
                ac1_cost_per_sqm = ac1_cost / (area_per_km * road_length)
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {ac1_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {ac1_cost_per_sqm:.2f} บาท/ตร.ม.</div>', unsafe_allow_html=True)
        
        with col2:
            ac2_show = st.checkbox("แสดงในรายงาน", value=True, key="ac2_show")
            ac2_name = st.text_input("ชื่อโครงสร้าง AC2", value="AC2: แอสฟัลต์บนหินคลุกผสมซีเมนต์", key="ac2_name")
            with st.expander(f"● {ac2_name}", expanded=True):
                ac2_layers = render_layer_editor(get_default_ac2_layers(), "ac2", total_width, road_length)
                ac2_cost, ac2_details = calculate_layer_cost(ac2_layers, road_length)
                ac2_cost_per_km = ac2_cost / road_length / 1_000_000
                ac2_cost_per_sqm = ac2_cost / (area_per_km * road_length)
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {ac2_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {ac2_cost_per_sqm:.2f} บาท/ตร.ม.</div>', unsafe_allow_html=True)
        
        # ===== JRCP/JPCP =====
        st.subheader("🟠 ผิวทางคอนกรีตเสริมเหล็ก (JRCP/JPCP)")
        col3, col4 = st.columns(2)
        
        with col3:
            jrcp1_show = st.checkbox("แสดงในรายงาน", value=True, key="jrcp1_show")
            jrcp1_name = st.text_input("ชื่อโครงสร้าง JRCP1", value="JRCP1: คอนกรีตบนดินซีเมนต์", key="jrcp1_name")
            with st.expander(f"● {jrcp1_name}", expanded=True):
                jrcp1_layers = render_layer_editor(get_default_jrcp1_layers(), "jrcp1", total_width, road_length)
                jrcp1_layer_cost, jrcp1_layer_details = calculate_layer_cost(jrcp1_layers, road_length)
                jrcp1_joints = render_joint_editor(get_default_jrcp1_joints(), "jrcp1")
                jrcp1_joint_cost, jrcp1_joint_details = calculate_joint_cost(jrcp1_joints, road_length)
                jrcp1_total = jrcp1_layer_cost + jrcp1_joint_cost
                jrcp1_cost_per_km = jrcp1_total / road_length / 1_000_000
                jrcp1_cost_per_sqm = jrcp1_total / (area_per_km * road_length)
                jrcp1_details = jrcp1_layer_details + jrcp1_joint_details
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {jrcp1_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {jrcp1_cost_per_sqm:.2f} บาท/ตร.ม.</div>', unsafe_allow_html=True)
        
        with col4:
            jrcp2_show = st.checkbox("แสดงในรายงาน", value=True, key="jrcp2_show")
            jrcp2_name = st.text_input("ชื่อโครงสร้าง JRCP2", value="JRCP2: คอนกรีตบนหินคลุกผสมซีเมนต์", key="jrcp2_name")
            with st.expander(f"● {jrcp2_name}", expanded=True):
                jrcp2_layers = render_layer_editor(get_default_jrcp2_layers(), "jrcp2", total_width, road_length)
                jrcp2_layer_cost, jrcp2_layer_details = calculate_layer_cost(jrcp2_layers, road_length)
                jrcp2_joints = render_joint_editor(get_default_jrcp1_joints(), "jrcp2")
                jrcp2_joint_cost, jrcp2_joint_details = calculate_joint_cost(jrcp2_joints, road_length)
                jrcp2_total = jrcp2_layer_cost + jrcp2_joint_cost
                jrcp2_cost_per_km = jrcp2_total / road_length / 1_000_000
                jrcp2_cost_per_sqm = jrcp2_total / (area_per_km * road_length)
                jrcp2_details = jrcp2_layer_details + jrcp2_joint_details
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {jrcp2_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {jrcp2_cost_per_sqm:.2f} บาท/ตร.ม.</div>', unsafe_allow_html=True)
        
        # ===== CRCP =====
        st.subheader("🔴 ผิวทางคอนกรีตเสริมเหล็กต่อเนื่อง (CRCP)")
        col5, col6 = st.columns(2)
        
        with col5:
            crcp1_show = st.checkbox("แสดงในรายงาน", value=True, key="crcp1_show")
            crcp1_name = st.text_input("ชื่อโครงสร้าง CRCP1", value="CRCP1: คอนกรีตเสริมเหล็กต่อเนื่องบนดินซีเมนต์", key="crcp1_name")
            with st.expander(f"● {crcp1_name}", expanded=True):
                crcp1_layers = render_layer_editor(get_default_crcp1_layers(), "crcp1", total_width, road_length)
                crcp1_cost, crcp1_details = calculate_layer_cost(crcp1_layers, road_length)
                crcp1_cost_per_km = crcp1_cost / road_length / 1_000_000
                crcp1_cost_per_sqm = crcp1_cost / (area_per_km * road_length)
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {crcp1_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {crcp1_cost_per_sqm:.2f} บาท/ตร.ม.</div>', unsafe_allow_html=True)
        
        with col6:
            crcp2_show = st.checkbox("แสดงในรายงาน", value=True, key="crcp2_show")
            crcp2_name = st.text_input("ชื่อโครงสร้าง CRCP2", value="CRCP2: คอนกรีตเสริมเหล็กต่อเนื่องบน CMCR", key="crcp2_name")
            with st.expander(f"● {crcp2_name}", expanded=True):
                crcp2_layers = render_layer_editor(get_default_crcp2_layers(), "crcp2", total_width, road_length)
                crcp2_cost, crcp2_details = calculate_layer_cost(crcp2_layers, road_length)
                crcp2_cost_per_km = crcp2_cost / road_length / 1_000_000
                crcp2_cost_per_sqm = crcp2_cost / (area_per_km * road_length)
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {crcp2_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {crcp2_cost_per_sqm:.2f} บาท/ตร.ม.</div>', unsafe_allow_html=True)
        
        # Store in session state
        st.session_state['construction'] = {
            'AC1': {'name': ac1_name, 'cost': ac1_cost_per_km, 'cost_sqm': ac1_cost_per_sqm, 'details': ac1_details, 'layers': ac1_layers, 'joints': None, 'show': ac1_show},
            'AC2': {'name': ac2_name, 'cost': ac2_cost_per_km, 'cost_sqm': ac2_cost_per_sqm, 'details': ac2_details, 'layers': ac2_layers, 'joints': None, 'show': ac2_show},
            'JRCP1': {'name': jrcp1_name, 'cost': jrcp1_cost_per_km, 'cost_sqm': jrcp1_cost_per_sqm, 'details': jrcp1_details, 'layers': jrcp1_layers, 'joints': jrcp1_joints, 'show': jrcp1_show},
            'JRCP2': {'name': jrcp2_name, 'cost': jrcp2_cost_per_km, 'cost_sqm': jrcp2_cost_per_sqm, 'details': jrcp2_details, 'layers': jrcp2_layers, 'joints': jrcp2_joints, 'show': jrcp2_show},
            'CRCP1': {'name': crcp1_name, 'cost': crcp1_cost_per_km, 'cost_sqm': crcp1_cost_per_sqm, 'details': crcp1_details, 'layers': crcp1_layers, 'joints': None, 'show': crcp1_show},
            'CRCP2': {'name': crcp2_name, 'cost': crcp2_cost_per_km, 'cost_sqm': crcp2_cost_per_sqm, 'details': crcp2_details, 'layers': crcp2_layers, 'joints': None, 'show': crcp2_show},
        }
        st.session_state['project_info'] = project_info
        st.session_state['area_per_km'] = area_per_km
        
        # ===== Summary Tables =====
        st.divider()
        st.subheader("📊 สรุปค่าก่อสร้าง")
        
        # ตารางสรุปรวม
        all_structures = [
            ('AC1', ac1_name, ac1_cost_per_km, ac1_cost_per_sqm, 20, ac1_show),
            ('AC2', ac2_name, ac2_cost_per_km, ac2_cost_per_sqm, 20, ac2_show),
            ('JRCP1', jrcp1_name, jrcp1_cost_per_km, jrcp1_cost_per_sqm, 25, jrcp1_show),
            ('JRCP2', jrcp2_name, jrcp2_cost_per_km, jrcp2_cost_per_sqm, 25, jrcp2_show),
            ('CRCP1', crcp1_name, crcp1_cost_per_km, crcp1_cost_per_sqm, 30, crcp1_show),
            ('CRCP2', crcp2_name, crcp2_cost_per_km, crcp2_cost_per_sqm, 30, crcp2_show),
        ]
        
        summary_data = []
        for key, name, cost_km, cost_sqm, life, show in all_structures:
            summary_data.append({
                'รหัส': key,
                'ประเภท': name,
                'ค่าก่อสร้าง (ล้านบาท/กม.)': cost_km,
                'ค่าก่อสร้าง (บาท/ตร.ม.)': cost_sqm,
                'อายุออกแบบ (ปี)': life,
                'แสดงในรายงาน': '✅' if show else '❌'
            })
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(
            summary_df.style.format({
                'ค่าก่อสร้าง (ล้านบาท/กม.)': '{:.2f}',
                'ค่าก่อสร้าง (บาท/ตร.ม.)': '{:.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # ===== ตารางสรุปราคาละเอียดแต่ละโครงสร้าง =====
        st.divider()
        st.subheader("📋 รายละเอียดราคาแต่ละโครงสร้าง")
        
        selected_structure = st.selectbox(
            "เลือกดูรายละเอียด",
            options=['AC1', 'AC2', 'JRCP1', 'JRCP2', 'CRCP1', 'CRCP2'],
            format_func=lambda x: st.session_state['construction'][x]['name']
        )
        
        if selected_structure:
            struct = st.session_state['construction'][selected_structure]
            layers = struct['layers']
            joints = struct.get('joints')
            
            # สร้างตารางรายละเอียด
            detail_data = []
            total_cost = 0
            
            # ส่วนผิวทาง
            st.markdown(f"**{struct['name']}**")
            
            for i, layer in enumerate(layers):
                layer_cost = layer['quantity'] * layer['unit_cost']
                total_cost += layer_cost
                detail_data.append({
                    'ลำดับ': i + 1,
                    'รายการ': layer['name'],
                    'ความหนา': f"{layer['thickness']} {layer['unit']}",
                    'ปริมาณ (ตร.ม.)': f"{layer['quantity']:,.0f}",
                    'ราคา (บาท/ตร.ม.)': f"{layer['unit_cost']:,.2f}",
                    'มูลค่า (บาท)': f"{layer_cost:,.0f}"
                })
            
            # ส่วน Joints (ถ้ามี)
            if joints:
                for j, joint in enumerate(joints):
                    joint_cost = joint['quantity'] * joint['unit_cost']
                    total_cost += joint_cost
                    detail_data.append({
                        'ลำดับ': len(layers) + j + 1,
                        'รายการ': joint['name'],
                        'ความหนา': '-',
                        'ปริมาณ (ตร.ม.)': f"{joint['quantity']:,.0f}",
                        'ราคา (บาท/ตร.ม.)': f"{joint['unit_cost']:,.2f}",
                        'มูลค่า (บาท)': f"{joint_cost:,.0f}"
                    })
            
            detail_df = pd.DataFrame(detail_data)
            st.dataframe(detail_df, use_container_width=True, hide_index=True)
            
            # แสดงราคารวม
            area_km = st.session_state.get('area_per_km', 22000) * road_length
            cost_per_sqm = total_cost / area_km if area_km > 0 else 0
            
            col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
            with col_sum1:
                st.metric("💰 ราคารวม", f"{total_cost:,.0f} บาท")
            with col_sum2:
                st.metric("📏 ราคาต่อ กม.", f"{total_cost/road_length:,.0f} บาท/กม.")
            with col_sum3:
                st.metric("📊 ล้านบาท/กม.", f"{total_cost/road_length/1_000_000:.2f}")
            with col_sum4:
                st.metric("📐 บาท/ตร.ม.", f"{cost_per_sqm:.2f}")
    
    # ===== Tab 3: ค่าบำรุงรักษา =====
    with tab3:
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
    
    # ===== Tab 4: ผลการวิเคราะห์ =====
    with tab4:
        st.header("ผลการวิเคราะห์ NPV")
        
        if st.button("🔄 คำนวณ NPV", type="primary", use_container_width=True):
            with st.spinner("กำลังคำนวณ..."):
                constr = st.session_state.get('construction', {})
                maint = st.session_state.get('maintenance', {})
                
                seal = maint.get('ac_seal', 1.76)
                overlay = maint.get('ac_overlay', 8.80)
                joint = maint.get('jrcp_joint', 1.426)
                crcp_m = maint.get('crcp_maint', 0.50)
                
                r = discount_rate / 100
                
                results = []
                all_cf = []
                ptypes = []
                
                # AC1
                if constr.get('AC1', {}).get('show', True):
                    ac1_c = constr.get('AC1', {}).get('cost', 46.89)
                    ac1_name = constr.get('AC1', {}).get('name', 'AC1')
                    npv1, cf1 = calculate_npv_ac(ac1_c, seal, overlay, 20, analysis_period, r)
                    results.append({'ประเภท': ac1_name, 'ค่าก่อสร้าง': ac1_c, 'อายุ': 20, 'NPV (ล้านบาท/กม.)': npv1})
                    all_cf.append(cf1)
                    ptypes.append(ac1_name)
                
                # AC2
                if constr.get('AC2', {}).get('show', True):
                    ac2_c = constr.get('AC2', {}).get('cost', 29.04)
                    ac2_name = constr.get('AC2', {}).get('name', 'AC2')
                    npv2, cf2 = calculate_npv_ac(ac2_c, seal, overlay, 20, analysis_period, r)
                    results.append({'ประเภท': ac2_name, 'ค่าก่อสร้าง': ac2_c, 'อายุ': 20, 'NPV (ล้านบาท/กม.)': npv2})
                    all_cf.append(cf2)
                    ptypes.append(ac2_name)
                
                # JRCP1
                if constr.get('JRCP1', {}).get('show', True):
                    jrcp1_c = constr.get('JRCP1', {}).get('cost', 28.24)
                    jrcp1_name = constr.get('JRCP1', {}).get('name', 'JRCP1')
                    npv3, cf3 = calculate_npv_jrcp(jrcp1_c, joint, 25, analysis_period, r)
                    results.append({'ประเภท': jrcp1_name, 'ค่าก่อสร้าง': jrcp1_c, 'อายุ': 25, 'NPV (ล้านบาท/กม.)': npv3})
                    all_cf.append(cf3)
                    ptypes.append(jrcp1_name)
                
                # JRCP2
                if constr.get('JRCP2', {}).get('show', True):
                    jrcp2_c = constr.get('JRCP2', {}).get('cost', 29.53)
                    jrcp2_name = constr.get('JRCP2', {}).get('name', 'JRCP2')
                    npv4, cf4 = calculate_npv_jrcp(jrcp2_c, joint, 25, analysis_period, r)
                    results.append({'ประเภท': jrcp2_name, 'ค่าก่อสร้าง': jrcp2_c, 'อายุ': 25, 'NPV (ล้านบาท/กม.)': npv4})
                    all_cf.append(cf4)
                    ptypes.append(jrcp2_name)
                
                # CRCP1
                if constr.get('CRCP1', {}).get('show', True):
                    crcp1_c = constr.get('CRCP1', {}).get('cost', 30.00)
                    crcp1_name = constr.get('CRCP1', {}).get('name', 'CRCP1')
                    npv5, cf5 = calculate_npv_crcp(crcp1_c, crcp_m, 30, analysis_period, r)
                    results.append({'ประเภท': crcp1_name, 'ค่าก่อสร้าง': crcp1_c, 'อายุ': 30, 'NPV (ล้านบาท/กม.)': npv5})
                    all_cf.append(cf5)
                    ptypes.append(crcp1_name)
                
                # CRCP2
                if constr.get('CRCP2', {}).get('show', True):
                    crcp2_c = constr.get('CRCP2', {}).get('cost', 31.00)
                    crcp2_name = constr.get('CRCP2', {}).get('name', 'CRCP2')
                    npv6, cf6 = calculate_npv_crcp(crcp2_c, crcp_m, 30, analysis_period, r)
                    results.append({'ประเภท': crcp2_name, 'ค่าก่อสร้าง': crcp2_c, 'อายุ': 30, 'NPV (ล้านบาท/กม.)': npv6})
                    all_cf.append(cf6)
                    ptypes.append(crcp2_name)
                
                if results:
                    results_df = pd.DataFrame(results)
                    results_df['อันดับ'] = results_df['NPV (ล้านบาท/กม.)'].rank().astype(int)
                    results_df = results_df.sort_values('อันดับ')
                    
                    st.session_state['results_df'] = results_df
                    st.session_state['all_cf'] = all_cf
                    st.session_state['ptypes'] = ptypes
                else:
                    st.warning("⚠️ กรุณาเลือกอย่างน้อย 1 โครงสร้างเพื่อแสดงในรายงาน")
        
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
    
    # ===== Tab 5: Cash Flow =====
    with tab5:
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
    
    # ===== Tab 6: รายงาน =====
    with tab6:
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
    
    # ===== Tab 7: วิเคราะห์จากรูปภาพ =====
    with tab7:
        st.header("📷 วิเคราะห์โครงสร้างชั้นทางจากรูปภาพ")
        st.info("💡 Upload รูปภาพโครงสร้างชั้นทาง แล้วระบบจะวิเคราะห์และคำนวณราคาให้อัตโนมัติ")
        
        # Upload รูปภาพ
        uploaded_image = st.file_uploader(
            "เลือกรูปภาพโครงสร้างชั้นทาง",
            type=['png', 'jpg', 'jpeg'],
            help="รองรับไฟล์ PNG, JPG, JPEG"
        )
        
        if uploaded_image is not None:
            col_img, col_result = st.columns([1, 1])
            
            with col_img:
                st.subheader("🖼️ รูปภาพที่ Upload")
                st.image(uploaded_image, use_container_width=True)
            
            with col_result:
                st.subheader("📋 กรอกข้อมูลโครงสร้างชั้นทาง")
                st.markdown("กรุณาตรวจสอบและแก้ไขข้อมูลที่อ่านจากรูปภาพ")
                
                # เลือกประเภทโครงสร้าง
                structure_type = st.selectbox(
                    "ประเภทโครงสร้าง",
                    options=['AC Pavement', 'JPCP', 'JRCP', 'CRCP'],
                    key="img_structure_type"
                )
                
                # กำหนดจำนวนชั้น
                num_layers = st.number_input(
                    "จำนวนชั้นโครงสร้าง",
                    min_value=1, max_value=10, value=6,
                    key="img_num_layers"
                )
                
                st.divider()
                
                # วัสดุที่เลือกได้
                surface_materials = {
                    'AC Pavement': ['AC Wearing Course', 'PMA Wearing Course', 'AC Binder Course', 'AC Base Course', 'Tack Coat', 'Prime Coat'],
                    'JPCP': ['Concrete Slab (JPCP)', 'AC Interlayer', 'Non Woven Geotextile'],
                    'JRCP': ['Concrete Slab (JRCP)', 'AC Interlayer', 'Non Woven Geotextile'],
                    'CRCP': ['Concrete Slab (CRCP)', 'AC Interlayer', 'Steel Reinforcement', 'Non Woven Geotextile'],
                }
                
                base_materials = [
                    'Cement Treated Base (UCS 40 ksc)',
                    'Cement Modified Crushed Rock Base (UCS 24.5 ksc)',
                    'Crushed Rock Base Course',
                    'Soil Cement Subbase (UCS 7 ksc)',
                    'Soil Aggregate Subbase',
                    'Selected Material A',
                ]
                
                all_materials = surface_materials.get(structure_type, []) + base_materials
                
                # เก็บข้อมูลชั้น
                if 'img_layers' not in st.session_state:
                    st.session_state['img_layers'] = []
                
                img_layers = []
                total_cost_sqm = 0
                
                st.markdown("**รายละเอียดแต่ละชั้น:**")
                
                # Header
                cols_h = st.columns([3, 1.5, 2])
                cols_h[0].markdown("**วัสดุ**")
                cols_h[1].markdown("**ความหนา (cm)**")
                cols_h[2].markdown("**ราคา (บาท/ตร.ม.)**")
                
                for i in range(int(num_layers)):
                    cols = st.columns([3, 1.5, 2])
                    
                    with cols[0]:
                        # Default values ตามลำดับ
                        default_materials = {
                            'AC Pavement': ['AC Wearing Course', 'AC Binder Course', 'AC Base Course', 'Cement Treated Base (UCS 40 ksc)', 'Soil Aggregate Subbase', 'Selected Material A'],
                            'JPCP': ['Concrete Slab (JPCP)', 'AC Interlayer', 'Cement Treated Base (UCS 40 ksc)', 'Crushed Rock Base Course', 'Soil Aggregate Subbase', 'Selected Material A'],
                            'JRCP': ['Concrete Slab (JRCP)', 'AC Interlayer', 'Cement Treated Base (UCS 40 ksc)', 'Crushed Rock Base Course', 'Soil Aggregate Subbase', 'Selected Material A'],
                            'CRCP': ['Concrete Slab (CRCP)', 'AC Interlayer', 'Cement Treated Base (UCS 40 ksc)', 'Crushed Rock Base Course', 'Soil Aggregate Subbase', 'Selected Material A'],
                        }
                        default_list = default_materials.get(structure_type, all_materials)
                        default_idx = i if i < len(default_list) else 0
                        default_mat = default_list[default_idx] if default_idx < len(default_list) else all_materials[0]
                        
                        try:
                            mat_idx = all_materials.index(default_mat)
                        except:
                            mat_idx = 0
                        
                        material = st.selectbox(
                            f"วัสดุชั้น {i+1}",
                            options=all_materials,
                            index=mat_idx,
                            key=f"img_mat_{i}",
                            label_visibility="collapsed"
                        )
                    
                    with cols[1]:
                        # Default thickness
                        default_thicknesses = {
                            'AC Pavement': [5, 7, 8, 20, 25, 30],
                            'JPCP': [30, 5, 20, 15, 25, 30],
                            'JRCP': [30, 5, 20, 15, 25, 30],
                            'CRCP': [30, 5, 20, 15, 25, 30],
                        }
                        default_thick_list = default_thicknesses.get(structure_type, [20]*10)
                        default_thick = default_thick_list[i] if i < len(default_thick_list) else 20
                        
                        thickness = st.number_input(
                            f"หนา {i+1}",
                            min_value=0.0, max_value=100.0,
                            value=float(default_thick),
                            step=1.0,
                            key=f"img_thick_{i}",
                            label_visibility="collapsed"
                        )
                    
                    # คำนวณราคา
                    price_sqm = 0
                    mat_lower = material.lower()
                    
                    if 'price_library' in st.session_state:
                        lib = st.session_state['price_library']
                        
                        # ผิวทาง AC
                        if 'ac wearing' in mat_lower:
                            prices = lib['ac_prices'].get('AC Wearing Course', {})
                            price_sqm = prices.get(thickness, 0)
                            if price_sqm == 0 and prices:
                                closest = min(prices.keys(), key=lambda x: abs(x - thickness))
                                price_sqm = prices.get(closest, 0)
                        elif 'pma' in mat_lower:
                            prices = lib['ac_prices'].get('PMA Wearing Course', {})
                            price_sqm = prices.get(thickness, 0)
                            if price_sqm == 0 and prices:
                                closest = min(prices.keys(), key=lambda x: abs(x - thickness))
                                price_sqm = prices.get(closest, 0)
                        elif 'binder' in mat_lower:
                            prices = lib['ac_prices'].get('AC Binder Course', {})
                            price_sqm = prices.get(thickness, 0)
                            if price_sqm == 0 and prices:
                                closest = min(prices.keys(), key=lambda x: abs(x - thickness))
                                price_sqm = prices.get(closest, 0)
                        elif 'ac base' in mat_lower or 'ac interlayer' in mat_lower:
                            prices = lib['ac_prices'].get('AC Base Course', {})
                            price_sqm = prices.get(thickness, 0)
                            if price_sqm == 0 and prices:
                                closest = min(prices.keys(), key=lambda x: abs(x - thickness))
                                price_sqm = prices.get(closest, 0)
                        elif 'tack' in mat_lower:
                            price_sqm = 20
                        elif 'prime' in mat_lower:
                            price_sqm = 30
                        elif 'geotextile' in mat_lower:
                            price_sqm = 78
                        elif 'steel' in mat_lower:
                            price_sqm = 200
                        # คอนกรีต
                        elif 'concrete' in mat_lower or 'slab' in mat_lower:
                            if 'jpcp' in mat_lower:
                                prices = lib['concrete_prices'].get('JPCP', {})
                            elif 'jrcp' in mat_lower:
                                prices = lib['concrete_prices'].get('JRCP', {})
                            elif 'crcp' in mat_lower:
                                prices = lib['concrete_prices'].get('CRCP', {})
                            else:
                                prices = lib['concrete_prices'].get('JPCP', {})
                            
                            price_sqm = prices.get(int(thickness), 0)
                            if price_sqm == 0 and prices:
                                closest = min(prices.keys(), key=lambda x: abs(x - thickness))
                                price_sqm = prices.get(closest, 0)
                        # พื้นทาง (บาท/ลบ.ม. → บาท/ตร.ม.)
                        elif 'cement treated' in mat_lower or 'ctb' in mat_lower:
                            base_price = lib['base_prices'].get('Cement Treated Base (UCS 40 ksc)', 1096)
                            price_sqm = base_price * thickness / 100
                        elif 'cement modified' in mat_lower or 'cmcr' in mat_lower:
                            base_price = lib['base_prices'].get('Cement Modified Crushed Rock Base (UCS 24.5 ksc)', 864)
                            price_sqm = base_price * thickness / 100
                        elif 'crushed rock' in mat_lower:
                            base_price = lib['base_prices'].get('Crushed Rock Base Course', 583)
                            price_sqm = base_price * thickness / 100
                        elif 'soil cement' in mat_lower:
                            base_price = lib['base_prices'].get('Soil Cement Subbase (UCS 7 ksc)', 854)
                            price_sqm = base_price * thickness / 100
                        elif 'soil aggregate' in mat_lower or 'aggregate subbase' in mat_lower:
                            base_price = lib['base_prices'].get('Soil Aggregate Subbase', 375)
                            price_sqm = base_price * thickness / 100
                        elif 'selected' in mat_lower:
                            base_price = lib['base_prices'].get('Selected Material A', 375)
                            price_sqm = base_price * thickness / 100
                    
                    with cols[2]:
                        st.markdown(f"**{price_sqm:,.2f}**")
                    
                    total_cost_sqm += price_sqm
                    img_layers.append({
                        'material': material,
                        'thickness': thickness,
                        'price_sqm': price_sqm
                    })
                
                st.session_state['img_layers'] = img_layers
        
        # แสดงผลสรุป
        if uploaded_image is not None and 'img_layers' in st.session_state and st.session_state['img_layers']:
            st.divider()
            st.subheader("📊 สรุปผลการวิเคราะห์")
            
            img_layers = st.session_state['img_layers']
            total_cost_sqm = sum(layer['price_sqm'] for layer in img_layers)
            
            # แสดงตาราง
            summary_data = []
            for i, layer in enumerate(img_layers):
                summary_data.append({
                    'ลำดับ': i + 1,
                    'วัสดุ': layer['material'],
                    'ความหนา (cm)': layer['thickness'],
                    'ราคา (บาท/ตร.ม.)': f"{layer['price_sqm']:,.2f}"
                })
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
            
            # Metrics
            col_m1, col_m2, col_m3 = st.columns(3)
            
            with col_m1:
                st.metric("💰 ราคารวม", f"{total_cost_sqm:,.2f} บาท/ตร.ม.")
            
            with col_m2:
                # คำนวณต่อ กม. (สมมติ 22,000 ตร.ม./กม.)
                area_km = st.session_state.get('area_per_km', 22000)
                cost_per_km = total_cost_sqm * area_km / 1_000_000
                st.metric("📏 ราคาต่อ กม.", f"{cost_per_km:,.2f} ล้านบาท/กม.")
            
            with col_m3:
                structure_type = st.session_state.get('img_structure_type', 'JPCP')
                if 'AC' in structure_type:
                    design_life = 20
                elif 'CRCP' in structure_type:
                    design_life = 30
                else:
                    design_life = 25
                st.metric("⏱️ อายุออกแบบ", f"{design_life} ปี")
            
            # NPV Analysis
            st.divider()
            st.subheader("📈 วิเคราะห์ NPV")
            
            col_npv1, col_npv2 = st.columns(2)
            with col_npv1:
                img_discount_rate = st.number_input(
                    "อัตราคิดลด (%)",
                    value=4.0, min_value=0.0, max_value=20.0,
                    key="img_discount"
                )
            with col_npv2:
                img_analysis_period = st.number_input(
                    "ระยะเวลาวิเคราะห์ (ปี)",
                    value=50, min_value=10, max_value=100,
                    key="img_period"
                )
            
            if st.button("🔄 คำนวณ NPV", key="img_calc_npv", type="primary"):
                r = img_discount_rate / 100
                
                # คำนวณ NPV ตามประเภท
                structure_type = st.session_state.get('img_structure_type', 'JPCP')
                
                if 'AC' in structure_type:
                    # AC: Seal ปี 3,6,12,15 | Overlay ปี 9,18 | สร้างใหม่ ปี 20,40
                    npv, cf = calculate_npv_ac(cost_per_km, 1.76, 8.80, 20, img_analysis_period, r)
                elif 'CRCP' in structure_type:
                    # CRCP: บำรุงทุก 5 ปี | สร้างใหม่ ปี 30
                    npv, cf = calculate_npv_crcp(cost_per_km, 0.50, 30, img_analysis_period, r)
                else:
                    # JPCP/JRCP: Joint seal ทุก 3 ปี | สร้างใหม่ ปี 25,50
                    npv, cf = calculate_npv_jrcp(cost_per_km, 1.426, 25, img_analysis_period, r)
                
                st.success(f"✅ NPV = **{npv:,.2f} ล้านบาท/กม.** (ระยะ {img_analysis_period} ปี)")
                
                # แสดง Cash Flow
                with st.expander("📋 ดู Cash Flow รายปี"):
                    cf_df = pd.DataFrame({
                        'ปี': list(range(len(cf))),
                        'ค่าใช้จ่าย (ล้านบาท/กม.)': cf
                    })
                    st.dataframe(cf_df, use_container_width=True)
                
                # กราฟ
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=list(range(len(cf))),
                    y=cf,
                    marker_color='#2E86AB',
                    name='ค่าใช้จ่าย'
                ))
                fig.update_layout(
                    title=f'Cash Flow - {structure_type}',
                    xaxis_title='ปี',
                    yaxis_title='ค่าใช้จ่าย (ล้านบาท/กม.)',
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
