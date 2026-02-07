"""
แอปพลิเคชันวิเคราะห์ความคุ้มค่าโครงสร้างชั้นทาง (AASHTO 1993)
Version 5.0 - Simplified: วัสดุและราคา (ไม่มี NPV)
พัฒนาโดย: Claude AI สำหรับ อ.อิทธิพล - KMUTNB
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime
import io

# Import with error handling
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("⚠️ Plotly ไม่สามารถใช้งานได้ กราฟบางส่วนอาจไม่แสดง")

try:
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    st.warning("⚠️ python-docx ไม่สามารถใช้งานได้ การสร้างรายงาน Word อาจไม่ทำงาน")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    st.warning("⚠️ openpyxl ไม่สามารถใช้งานได้ การ Upload/Download Excel อาจไม่ทำงาน")

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
    """JPCP/JRCP (1): คอนกรีตบนดินซีเมนต์ (ตารางที่ 5.3-22)"""
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
    """JPCP/JRCP (2): คอนกรีตบนหินคลุกผสมซีเมนต์ (ตารางที่ 5.3-24)"""
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
    # total_width รวมทั้ง 2 ทิศทางไว้แล้ว (num_lanes = lanes_per_direction * 2)
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
    cols = st.columns([3, 1, 1.5])
    cols[0].markdown("รายการ")
    cols[1].markdown("หนา (cm)")
    cols[2].markdown("ราคา (บาท/ตร.ม.)")
    
    # ตัวเลือกวัสดุ
    wearing_options = ['AC Wearing Course', 'PMA Wearing Course']
    binder_options = ['AC Binder Course']
    base_options = ['AC Base Course']
    concrete_options = ['JPCP', 'JRCP', 'CRCP']
    
    for i, layer in enumerate(surface_layers):
        cols = st.columns([3, 1, 1.5])
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
    
    # ตรวจสอบว่าเป็น JRCP หรือ CRCP หรือไม่ (เพื่อเพิ่ม AC Interlayer)
    is_concrete_pavement = any(x in key_prefix.lower() for x in ['jrcp', 'crcp'])
    
    # Library วัสดุพื้นทาง (ดึงจาก session_state หรือใช้ค่า default)
    # ราคาใน Library เป็น บาท/ลบ.ม. ยกเว้น AC Interlayer เป็น บาท/ตร.ม.
    if 'price_library' in st.session_state:
        base_lib = st.session_state['price_library']['base_prices']
        ac_lib = st.session_state['price_library']['ac_prices']
        
        base_materials = {}
        
        # เพิ่ม AC Interlayer เฉพาะ JRCP และ CRCP
        if is_concrete_pavement:
            base_materials['AC Interlayer (5 cm)'] = {'unit_cost_cum': ac_lib.get('AC Base Course', {}).get(5, 251), 'is_ac': True, 'default_thick': 5}
        
        # วัสดุพื้นทางปกติ
        base_materials.update({
            'Crushed Rock Base Course': {'unit_cost_cum': base_lib.get('Crushed Rock Base Course', 583), 'is_ac': False},
            'Cement Modified Crushed Rock Base (UCS 24.5 ksc)': {'unit_cost_cum': base_lib.get('Cement Modified Crushed Rock Base (UCS 24.5 ksc)', 864), 'is_ac': False},
            'Cement Treated Base (UCS 40 ksc)': {'unit_cost_cum': base_lib.get('Cement Treated Base (UCS 40 ksc)', 1096), 'is_ac': False},
            'Soil Cement Subbase (UCS 7 ksc)': {'unit_cost_cum': base_lib.get('Soil Cement Subbase (UCS 7 ksc)', 854), 'is_ac': False},
            'Soil Aggregate Subbase': {'unit_cost_cum': base_lib.get('Soil Aggregate Subbase', 375), 'is_ac': False},
            'Selected Material A': {'unit_cost_cum': base_lib.get('Selected Material A', 375), 'is_ac': False},
        })
    else:
        base_materials = {}
        
        if is_concrete_pavement:
            base_materials['AC Interlayer (5 cm)'] = {'unit_cost_cum': 251, 'is_ac': True, 'default_thick': 5}
        
        base_materials.update({
            'Crushed Rock Base Course': {'unit_cost_cum': 583, 'is_ac': False},
            'Cement Modified Crushed Rock Base (UCS 24.5 ksc)': {'unit_cost_cum': 864, 'is_ac': False},
            'Cement Treated Base (UCS 40 ksc)': {'unit_cost_cum': 1096, 'is_ac': False},
            'Soil Cement Subbase (UCS 7 ksc)': {'unit_cost_cum': 854, 'is_ac': False},
            'Soil Aggregate Subbase': {'unit_cost_cum': 375, 'is_ac': False},
            'Selected Material A': {'unit_cost_cum': 375, 'is_ac': False},
        })
    material_names = list(base_materials.keys())
    
    # จำนวนชั้นพื้นทาง (สูงสุด 5 ชั้น)
    num_base = st.number_input("จำนวนชั้นพื้นทาง/รองพื้นทาง", value=len(base_layers), 
                                min_value=1, max_value=5, key=f"{key_prefix}_num_base")
    
    cols = st.columns([3, 1, 1.2, 1.2, 1.2])
    cols[0].markdown("วัสดุ")
    cols[1].markdown("หนา (cm)")
    cols[2].markdown("ปริมาณ (ตร.ม.)")
    cols[3].markdown("ราคา (บาท/ลบ.ม.)")
    cols[4].markdown("ราคา (บาท/ตร.ม.)")
    
    for i in range(int(num_base)):
        cols = st.columns([3, 1, 1.2, 1.2, 1.2])
        
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
            # AC Interlayer ใช้ความหนาคงที่จาก Library
            if base_materials[selected].get('is_ac', False):
                default_thick_val = base_materials[selected].get('default_thick', 5)
                thick = st.number_input("หนา", value=float(default_thick_val),
                    key=f"{key_prefix}_bt_{i}", label_visibility="collapsed", min_value=0.0, step=1.0)
            else:
                thick = st.number_input("หนา", value=float(default_thick),
                    key=f"{key_prefix}_bt_{i}", label_visibility="collapsed", min_value=0.0, step=5.0)
        
        # ปริมาณ = พื้นที่ (ตร.ม.) - ไม่ใช่ ลบ.ม. อีกต่อไป
        auto_qty = area_per_km * road_length
        
        # คำนวณราคา
        if base_materials[selected].get('is_ac', False):
            # AC Interlayer: ราคาเป็น บาท/ตร.ม. อยู่แล้ว (ดึงจาก AC Library ตามความหนา)
            if 'price_library' in st.session_state:
                ac_prices = st.session_state['price_library']['ac_prices'].get('AC Base Course', {})
                cost_per_sqm = ac_prices.get(thick, 0)
                if cost_per_sqm == 0 and ac_prices:
                    closest = min(ac_prices.keys(), key=lambda x: abs(x - thick))
                    cost_per_sqm = ac_prices.get(closest, 251)
            else:
                cost_per_sqm = 251  # default 5cm
            lib_cost_cum = cost_per_sqm  # สำหรับ AC เก็บราคาตรง ไม่ใช่ ลบ.ม.
        else:
            # วัสดุพื้นทางปกติ: แปลงราคา บาท/ลบ.ม. → บาท/ตร.ม.
            lib_cost_cum = base_materials[selected]['unit_cost_cum']  # บาท/ลบ.ม.
            cost_per_sqm = lib_cost_cum * thick / 100  # บาท/ตร.ม.
        
        with cols[2]:
            st.text(f"{auto_qty:,.0f}")
        with cols[3]:
            # แสดงราคา บาท/ลบ.ม. (ดึงจาก Library)
            if base_materials[selected].get('is_ac', False):
                st.markdown("**-**")  # AC ไม่มีหน่วย ลบ.ม.
            else:
                st.markdown(f"**{lib_cost_cum:,.2f}**")
        with cols[4]:
            # แสดงราคาที่คำนวณแล้ว บาท/ตร.ม. (อัพเดทตามความหนาอัตโนมัติ)
            st.markdown(f"**{cost_per_sqm:,.2f}**")
        
        updated_layers.append({
            'name': selected, 'thickness': thick, 'unit': 'cm',
            'quantity': auto_qty, 'qty_unit': 'sq.m', 'unit_cost': cost_per_sqm,
            'cost_per_sqm': cost_per_sqm,  # ราคาต่อ ตร.ม.
            'cost_cum': lib_cost_cum  # เก็บราคา ลบ.ม. ไว้อ้างอิง
        })
    
    return updated_layers


def render_joint_editor(joints, key_prefix, area_per_km, road_length):
    """แสดง UI สำหรับแก้ไขรอยต่อ พร้อมแสดงราคา บาท/ตร.ม."""
    st.markdown("---")
    
    # Checkbox เลือกรวม/ไม่รวม Joints
    col_header = st.columns([3, 1])
    with col_header[0]:
        st.markdown("**รอยต่อ (Joints)**")
    with col_header[1]:
        include_joints = st.checkbox("รวมราคา Joints", value=True, key=f"{key_prefix}_include_joints")
    
    cols = st.columns([3, 1.5, 1.5, 1.5])
    cols[0].markdown("รายการ")
    cols[1].markdown("ปริมาณ (m)")
    cols[2].markdown("ราคา/หน่วย")
    cols[3].markdown("ราคา (บาท/ตร.ม.)")
    
    updated_joints = []
    total_area = area_per_km * road_length
    
    for i, joint in enumerate(joints):
        cols = st.columns([3, 1.5, 1.5, 1.5])
        
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
        
        # คำนวณราคา บาท/ตร.ม.
        joint_total = qty * cost
        cost_per_sqm = joint_total / total_area if total_area > 0 else 0
        
        with cols[3]:
            st.markdown(f"**{cost_per_sqm:.2f}**")
        
        updated_joints.append({
            'name': joint['name'],
            'quantity': qty,
            'qty_unit': joint['qty_unit'],
            'unit_cost': cost,
            'cost_per_sqm': cost_per_sqm
        })
    
    return updated_joints, include_joints


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


def generate_word_report_materials_only(project_info, all_details):
    """สร้างรายงาน Word - เฉพาะวัสดุและราคา (ไม่มี NPV) พร้อมตารางสรุปแยกชนิด"""
    if not DOCX_AVAILABLE:
        raise ImportError("python-docx ไม่สามารถใช้งานได้")
    
    doc = Document()
    
    style = doc.styles['Normal']
    style.font.name = 'TH SarabunPSK'
    style.font.size = Pt(16)
    
    doc.add_heading('รายงานวัสดุและราคาโครงสร้างชั้นทาง', 0)
    
    doc.add_heading('1. ข้อมูลโครงการ', level=1)
    doc.add_paragraph(f"ชื่อโครงการ: {project_info.get('name', '-')}")
    doc.add_paragraph(f"ความยาวถนน: {project_info.get('length', 1):.2f} กม.")
    doc.add_paragraph(f"ความกว้างรวม: {project_info.get('total_width', 0):.2f} ม.")
    doc.add_paragraph(f"จำนวนช่องจราจร: {project_info.get('num_lanes', 2)} ช่อง")
    
    doc.add_heading('2. รายละเอียดวัสดุและราคา', level=1)
    
    # เก็บข้อมูลสรุป
    summary_data = []
    length = project_info.get('length', 1)
    
    for ptype, data in all_details.items():
        structure_name = data.get('name', ptype)
        details = data.get('details', [])
        
        doc.add_heading(structure_name, level=2)
        if details:
            table = doc.add_table(rows=len(details)+1, cols=4)
            table.style = 'Table Grid'
            
            # Header
            headers = ['รายการ', 'ปริมาณ', 'ราคา/หน่วย (บาท)', 'มูลค่า (บาท)']
            for j, h in enumerate(headers):
                cell = table.rows[0].cells[j]
                cell.text = h
                # ทำให้ header เป็นตัวหนา
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.bold = True
            
            # Data rows
            subtotal = 0
            for i, d in enumerate(details):
                table.rows[i+1].cells[0].text = str(d['รายการ'])
                table.rows[i+1].cells[1].text = f"{d['ปริมาณ']:,.0f} {d['หน่วย']}"
                table.rows[i+1].cells[2].text = f"{d['ราคา/หน่วย']:,.0f}"
                table.rows[i+1].cells[3].text = f"{d['มูลค่า (บาท)']:,.0f}"
                subtotal += d['มูลค่า (บาท)']
            
            # แสดงยอดรวมย่อย
            doc.add_paragraph(f"รวม {structure_name}: {subtotal:,.0f} บาท", style='Intense Quote')
            doc.add_paragraph()
            
            # เก็บข้อมูลสำหรับตารางสรุป
            cost_per_km_million = data.get('cost_per_km', 0)  # ล้านบาท/กม.
            cost_per_km_baht = cost_per_km_million * 1_000_000  # บาท/กม.
            cost_per_sqm = data.get('cost_sqm', 0)  # บาท/ตร.ม.
            total_value = subtotal  # มูลค่ารวม (บาท)
            
            summary_data.append({
                'name': structure_name,
                'total_value': total_value,
                'cost_per_km_million': cost_per_km_million,
                'cost_per_sqm': cost_per_sqm
            })
    
    # สร้างตารางสรุปแยกแต่ละชนิด
    doc.add_heading('3. สรุปค่าใช้จ่าย', level=1)
    
    if summary_data:
        table = doc.add_table(rows=len(summary_data)+1, cols=4)
        table.style = 'Table Grid'
        
        # Header
        headers = ['ชนิดโครงสร้าง', 'มูลค่ารวม/กม. (บาท)', 'ราคา/กม. (ล้านบาท)', 'ราคา/ตร.ม. (บาท)']
        for j, h in enumerate(headers):
            cell = table.rows[0].cells[j]
            cell.text = h
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
        
        # Data rows
        for i, item in enumerate(summary_data):
            # มูลค่ารวมต่อ กม. = มูลค่ารวม / ความยาว
            total_per_km = item['total_value'] / length if length > 0 else 0
            
            table.rows[i+1].cells[0].text = item['name']
            table.rows[i+1].cells[1].text = f"{total_per_km:,.0f}"
            table.rows[i+1].cells[2].text = f"{item['cost_per_km_million']:.2f}"
            table.rows[i+1].cells[3].text = f"{item['cost_per_sqm']:,.2f}"
    
    doc.add_paragraph()
    doc.add_paragraph(f"รายงานสร้างเมื่อ: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    return doc


# ===== Main Application =====

@st.cache_data
def generate_excel_template():
    """สร้าง Excel Template และ cache ไว้เพื่อประสิทธิภาพ"""
    template_data = {
        'AC_Prices': pd.DataFrame({
            'Material': ['PMA Wearing Course', 'AC Wearing Course', 'AC Binder Course', 'AC Base Course'],
            '2.5cm': [170, 128, 129, 129],
            '3cm': [203, 152, 154, 154],
            '4cm': [268, 202, 202, 202],
            '5cm': [333, 250, 251, 251],
            '6cm': [406, 306, 308, 308],
            '7cm': [471, 355, 356, 356],
            '8cm': [536, 403, 405, 405],
            '9cm': [601, 452, 454, 454],
            '10cm': [667, 502, 503, 503],
        }),
        'Concrete_Prices': pd.DataFrame({
            'Type': ['JRCP', 'JPCP', 'CRCP'],
            '25cm': [924, 928, 1245],
            '28cm': [1002, 1000, 1358],
            '32cm': [1106, 1095, 1509],
            '35cm': [1184, 1167, 1622],
        }),
        'Base_Materials': pd.DataFrame({
            'Material': list(BASE_MATERIAL_PRICES.keys()),
            'Price (Baht/cu.m)': list(BASE_MATERIAL_PRICES.values()),
        })
    }
    
    # สร้าง Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        template_data['AC_Prices'].to_excel(writer, sheet_name='AC_Prices', index=False)
        template_data['Concrete_Prices'].to_excel(writer, sheet_name='Concrete_Prices', index=False)
        template_data['Base_Materials'].to_excel(writer, sheet_name='Base_Materials', index=False)
    output.seek(0)
    
    return output.getvalue()


def main():
    st.markdown('<div class="main-header">🛣️ ระบบวิเคราะห์ค่าก่อสร้างโครงสร้างชั้นทาง</div>', unsafe_allow_html=True)
    st.markdown("##### ตามแนวทาง AASHTO 1993 - รองรับ AC, JPCP/JRCP, CRCP")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.9rem; margin-top: -10px; margin-bottom: 20px;'>
        พัฒนาโดย <b>รศ.ดร.อิทธิพล มีผล</b><br>
        ภาควิชาครุศาสตร์โยธา คณะครุศาสตร์อุตสาหกรรม<br>
        มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าพระนครเหนือ (มจพ.)
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("📋 ข้อมูลโครงการ")
        
        # ===== Upload JSON =====
        st.subheader("📂 โหลดโครงการ")
        uploaded_json = st.file_uploader(
            "เลือกไฟล์ JSON",
            type=['json'],
            help="อัพโหลดไฟล์โครงการที่บันทึกไว้",
            key="upload_json"
        )
        
        if uploaded_json is not None:
            try:
                loaded_data = json.loads(uploaded_json.read().decode('utf-8'))
                st.success("✅ โหลดไฟล์สำเร็จ!")
                
                # แสดงข้อมูลที่โหลด
                if 'project_info' in loaded_data:
                    st.info(f"📌 โครงการ: {loaded_data['project_info'].get('name', '-')}")
                    st.info(f"📅 บันทึกเมื่อ: {loaded_data.get('saved_at', '-')}")
                
                # เก็บข้อมูลใน session_state
                if st.button("📥 นำเข้าข้อมูล", key="import_json"):
                    if 'project_info' in loaded_data:
                        st.session_state['loaded_project'] = loaded_data
                        st.rerun()
            except Exception as e:
                st.error(f"❌ ไม่สามารถอ่านไฟล์ได้: {e}")
        
        st.divider()
        
        # ===== Upload Price Library Excel =====
        st.subheader("💰 Price Library (Excel)")
        st.caption("อัพโหลด Excel เพื่อแทนที่ราคา Default")
        
        uploaded_price_excel = st.file_uploader(
            "เลือกไฟล์ Excel Price Library",
            type=['xlsx', 'xls'],
            help="อัพโหลดไฟล์ราคาที่ Download จาก Tab 1",
            key="sidebar_upload_price"
        )
        
        # โหลดราคาจาก Excel ถ้ามี upload
        if uploaded_price_excel is not None:
            try:
                # อ่านไฟล์ Excel
                ac_df = pd.read_excel(uploaded_price_excel, sheet_name='AC_Prices')
                concrete_df = pd.read_excel(uploaded_price_excel, sheet_name='Concrete_Prices')
                base_df = pd.read_excel(uploaded_price_excel, sheet_name='Base_Materials')
                
                # แปลงเป็น dictionary format
                uploaded_ac_prices = {}
                for _, row in ac_df.iterrows():
                    material = row['Material']
                    prices = {}
                    for col in ac_df.columns[1:]:
                        thickness = float(col.replace('cm', ''))
                        prices[thickness] = float(row[col])
                    uploaded_ac_prices[material] = prices
                
                uploaded_concrete_prices = {}
                for _, row in concrete_df.iterrows():
                    conc_type = row['Type']
                    prices = {}
                    for col in concrete_df.columns[1:]:
                        thickness = int(col.replace('cm', ''))
                        prices[thickness] = float(row[col])
                    uploaded_concrete_prices[conc_type] = prices
                
                uploaded_base_prices = {}
                for _, row in base_df.iterrows():
                    uploaded_base_prices[row['Material']] = float(row['Price (Baht/cu.m)'])
                
                # เก็บใน session_state
                st.session_state['uploaded_price_library'] = {
                    'ac_prices': uploaded_ac_prices,
                    'concrete_prices': uploaded_concrete_prices,
                    'base_prices': uploaded_base_prices,
                }
                
                st.success("✅ โหลด Price Library สำเร็จ!")
                st.caption(f"📊 {len(uploaded_ac_prices)} AC types, {len(uploaded_concrete_prices)} Concrete types")
                
                # แสดงตัวอย่างราคาที่อ่านได้
                with st.expander("🔍 ตัวอย่างราคาที่อ่านได้"):
                    st.write("**AC Wearing Course (7cm):**", uploaded_ac_prices.get('AC Wearing Course', {}).get(7.0, 'N/A'))
                    st.write("**JPCP (25cm):**", uploaded_concrete_prices.get('JPCP', {}).get(25, 'N/A'))
                    st.write("**Crushed Rock:**", uploaded_base_prices.get('Crushed Rock Base Course', 'N/A'))
                
            except Exception as e:
                st.error(f"❌ อ่านไฟล์ไม่สำเร็จ: {str(e)}")
        
        st.divider()
        
        # ตรวจสอบว่ามีข้อมูลที่โหลดมาหรือไม่
        loaded_project = st.session_state.get('loaded_project', {})
        loaded_info = loaded_project.get('project_info', {})
        
        project_name = st.text_input("ชื่อโครงการ", value=loaded_info.get('name', "โครงการก่อสร้างทางหลวง"))
        road_length = st.number_input("ความยาวถนน (กม.)", value=loaded_info.get('length', 1.0), min_value=0.1, step=0.1)
        
        st.divider()
        st.header("📐 ขนาดถนน")
        lane_width = st.number_input("ความกว้างช่องจราจร (ม.)", value=loaded_info.get('lane_width', 3.5), min_value=2.5, max_value=4.0, step=0.25)
        
        # หา index สำหรับ num_lanes_per_direction
        # แปลงจาก num_lanes เดิม (รวม 2 ทิศทาง) เป็น lanes_per_direction
        default_lanes_total = loaded_info.get('num_lanes', 4)  # default 4 (2 ช่อง/ทิศทาง)
        default_lanes_per_dir = default_lanes_total // 2
        
        lanes_per_dir_options = [2, 3, 4]
        lanes_per_dir_idx = lanes_per_dir_options.index(default_lanes_per_dir) if default_lanes_per_dir in lanes_per_dir_options else 0
        lanes_per_direction = st.selectbox("จำนวนช่องต่อทิศทาง (เลน/ทิศทาง)", options=lanes_per_dir_options, index=lanes_per_dir_idx)
        
        # คำนวณจำนวนช่องรวม (คูณ 2 สำหรับ 2 ทิศทาง)
        num_lanes = lanes_per_direction * 2
        
        shoulder_left = st.number_input("ไหล่ทางซ้าย (ม.)", value=loaded_info.get('shoulder_left', 2.5), min_value=0.0, max_value=3.5, step=0.25)
        shoulder_right = st.number_input("ไหล่ทางขวา (ม.)", value=loaded_info.get('shoulder_right', 1.5), min_value=0.0, max_value=3.5, step=0.25)
        
        # คำนวณความกว้างรวม
        # ความกว้างผิวจราจร = ช่องจราจร × จำนวนช่อง (รวม 2 ทิศทาง)
        # แต่ละทิศทางมีไหล่ทางซ้าย + ไหล่ทางขวา
        # ความกว้างรวม = ผิวจราจร + (ไหล่ทางซ้าย + ไหล่ทางขวา) × 2 ทิศทาง
        road_surface_width = lane_width * num_lanes
        total_shoulders = (shoulder_left + shoulder_right) * 2  # ไหล่ทางรวม 2 ทิศทาง
        total_width = road_surface_width + total_shoulders
        st.info(f"📏 จำนวนช่องรวม (2 ทิศทาง): {num_lanes} ช่อง\n📏 ความกว้างผิวจราจร: {road_surface_width:.2f} ม.\n📏 ความกว้างไหล่ทาง (2 ทิศทาง): {total_shoulders:.2f} ม.\n📏 ความกว้างรวม: {total_width:.2f} ม.")
    
    # เก็บข้อมูลโครงการ
    project_info = {
        'name': project_name,
        'length': road_length,
        'lane_width': lane_width,
        'shoulder_left': shoulder_left,
        'shoulder_right': shoulder_right,
        'num_lanes': num_lanes,
        'total_width': total_width
    }
    
    # คำนวณพื้นที่ต่อ กม. (ใช้สำหรับคำนวณปริมาณ)
    area_per_km = total_width * 1000  # ตร.ม./กม.
    
    # Tabs
    # Tabs - ลบ Tab 3-5 ออกแล้ว
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Library ราคา", 
        "🏗️ โครงสร้างชั้นทาง", 
        "📄 รายงาน",
        "📷 วิเคราะห์จากรูปภาพ"
    ])
    
    # ===== Tab 1: Library ราคา =====
    with tab1:
        st.header("📊 ตารางราคาเปรียบเทียบโครงสร้างชั้นทาง")
        st.info("💡 สามารถปรับเปลี่ยนราคาได้ตามต้องการ หรือ Upload ไฟล์ Excel เพื่ออัพเดทราคาทั้งหมด")
        
        # ===== Upload Excel & Download Template =====
        col_upload, col_template = st.columns(2)
        
        with col_template:
            st.subheader("📥 ดาวน์โหลด Template Excel")
            
            # ใช้ cached template (ไม่ต้องสร้างใหม่ทุกครั้ง rerun)
            template_bytes = generate_excel_template()
            
            st.download_button(
                label="⬇️ ดาวน์โหลด Template",
                data=template_bytes,
                file_name=f"Price_Library_Template_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col_upload:
            st.subheader("📤 อัพโหลด Excel")
            
            # แสดงข้อความถ้าเพิ่งอัพโหลดเสร็จ
            if st.session_state.get('just_uploaded', False):
                st.success("✅ อัพเดทราคาเสร็จสมบูรณ์! ตารางด้านล่างแสดงราคาใหม่แล้ว")
                st.session_state['just_uploaded'] = False
            
            uploaded_excel = st.file_uploader(
                "เลือกไฟล์ Excel (ตาม Template)",
                type=['xlsx', 'xls'],
                key="upload_price_library"
            )
            
            if uploaded_excel is not None:
                try:
                    # อ่านไฟล์ Excel
                    ac_df = pd.read_excel(uploaded_excel, sheet_name='AC_Prices')
                    concrete_df = pd.read_excel(uploaded_excel, sheet_name='Concrete_Prices')
                    base_df = pd.read_excel(uploaded_excel, sheet_name='Base_Materials')
                    
                    # แปลงเป็น dictionary format
                    new_ac_prices = {}
                    for _, row in ac_df.iterrows():
                        material = row['Material']
                        prices = {}
                        for col in ac_df.columns[1:]:
                            thickness = float(col.replace('cm', ''))
                            prices[thickness] = float(row[col])
                        new_ac_prices[material] = prices
                    
                    new_concrete_prices = {}
                    for _, row in concrete_df.iterrows():
                        conc_type = row['Type']
                        prices = {}
                        for col in concrete_df.columns[1:]:
                            thickness = int(col.replace('cm', ''))
                            prices[thickness] = float(row[col])
                        new_concrete_prices[conc_type] = prices
                    
                    new_base_prices = {}
                    for _, row in base_df.iterrows():
                        new_base_prices[row['Material']] = float(row['Price (Baht/cu.m)'])
                    
                    # อัพเดท session state
                    st.session_state['price_library'] = {
                        'ac_prices': new_ac_prices,
                        'concrete_prices': new_concrete_prices,
                        'base_prices': new_base_prices,
                    }
                    
                    # ตั้ง flag ว่าเพิ่ง upload เสร็จ
                    st.session_state['just_uploaded'] = True
                    
                    st.success("✅ อัพโหลดสำเร็จ! กำลังอัพเดทราคา...")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดในการอ่านไฟล์: {str(e)}")
                    st.warning("⚠️ กรุณาตรวจสอบว่าไฟล์ Excel มีโครงสร้างตาม Template")
        
        st.divider()
        
        # เก็บราคาใน session state
        # ถ้ามี uploaded_price_library ให้ใช้แทน (ทุกครั้งที่ rerun)
        if 'uploaded_price_library' in st.session_state:
            st.session_state['price_library'] = st.session_state['uploaded_price_library'].copy()
        elif 'price_library' not in st.session_state:
            # ไม่มีทั้ง uploaded และ price_library → ใช้ default
            st.session_state['price_library'] = {
                'ac_prices': {
                    'PMA Wearing Course': dict(AC_PRICE_TABLE['PMA Wearing Course']),
                    'AC Wearing Course': dict(AC_PRICE_TABLE['AC Wearing Course']),
                    'AC Binder Course': dict(AC_PRICE_TABLE['AC Binder Course']),
                    'AC Base Course': dict(AC_PRICE_TABLE['AC Base Course']),
                },
                'concrete_prices': {
                    'JRCP': dict(CONCRETE_PRICE_TABLE['JRCP']),
                    'JPCP': dict(CONCRETE_PRICE_TABLE['JPCP']),
                    'CRCP': dict(CONCRETE_PRICE_TABLE['CRCP']),
                },
                'base_prices': dict(BASE_MATERIAL_PRICES),
            }
        
        # Debug info - แสดงที่มาของราคา
        if 'uploaded_price_library' in st.session_state:
            st.info("📋 **กำลังใช้ราคาจากไฟล์ Excel ที่ Upload ใน Sidebar**")
            # แสดงตัวอย่าง
            ac_7 = st.session_state['price_library']['ac_prices'].get('AC Wearing Course', {}).get(7.0, 'N/A')
            st.caption(f"ตัวอย่าง: AC Wearing Course 7cm = {ac_7} บาท")
        else:
            st.caption("💡 กำลังใช้ราคา Default (Upload Excel ใน Sidebar เพื่อเปลี่ยนราคา)")
        
        # ===== ส่วนผิวทาง AC =====
        st.subheader("🔵 ผิวทาง Asphalt Concrete (บาท/ตร.ม.)")
        
        ac_cols = st.columns(4)
        ac_types = ['PMA Wearing Course', 'AC Wearing Course', 'AC Binder Course', 'AC Base Course']
        thicknesses = [2.5, 3, 4, 5, 6, 7, 8, 9, 10]
        
        for col_idx, ac_type in enumerate(ac_types):
            with ac_cols[col_idx]:
                st.markdown(f"**{ac_type}**")
                for thk in thicknesses:
                    # ดึงราคาจาก session_state (ถ้า upload มาจะเป็นราคาใหม่)
                    current_price = st.session_state['price_library']['ac_prices'][ac_type].get(thk, 0)
                    price = st.number_input(
                        f"{thk} cm", 
                        value=float(current_price),
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
                    # ดึงราคาจาก session_state
                    current_price = st.session_state['price_library']['concrete_prices'][conc_type].get(thk, 0)
                    price = st.number_input(
                        f"{thk} cm", 
                        value=float(current_price),
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
                # ดึงราคาจาก session_state
                current_price = st.session_state['price_library']['base_prices'].get(mat, 0)
                price = st.number_input(
                    mat,
                    value=float(current_price),
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
    # ===== Tab 2: โครงสร้างชั้นทาง =====
    with tab2:
        st.header("กำหนดโครงสร้างชั้นทาง")
        st.info("💡 แก้ไขชื่อ ความหนา และราคาต่อหน่วยได้ตามต้องการ | ✅ เลือกโครงสร้างที่ต้องการแสดงในรายงาน")
        
        # คำนวณพื้นที่ต่อ กม.
        # total_width รวมทั้ง 2 ทิศทางไว้แล้ว (num_lanes = lanes_per_direction * 2)
        area_per_km = total_width * 1000  # ตร.ม./กม.
        
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
            jrcp1_name = st.text_input("ชื่อโครงสร้าง JPCP/JRCP (1)", value="JPCP/JRCP (1): คอนกรีตบนดินซีเมนต์", key="jrcp1_name")
            with st.expander(f"● {jrcp1_name}", expanded=True):
                jrcp1_layers = render_layer_editor(get_default_jrcp1_layers(), "jrcp1", total_width, road_length)
                jrcp1_layer_cost, jrcp1_layer_details = calculate_layer_cost(jrcp1_layers, road_length)
                jrcp1_joints, jrcp1_include_joints = render_joint_editor(get_default_jrcp1_joints(), "jrcp1", area_per_km, road_length)
                jrcp1_joint_cost, jrcp1_joint_details = calculate_joint_cost(jrcp1_joints, road_length)
                
                # คำนวณ บาท/ตร.ม. ตาม checkbox
                jrcp1_joints_sqm = sum(j.get('cost_per_sqm', 0) for j in jrcp1_joints)
                if jrcp1_include_joints:
                    jrcp1_total = jrcp1_layer_cost + jrcp1_joint_cost
                    jrcp1_cost_per_sqm = jrcp1_layer_cost / (area_per_km * road_length) + jrcp1_joints_sqm
                    joints_note = "(รวม Joints)"
                else:
                    jrcp1_total = jrcp1_layer_cost + jrcp1_joint_cost  # ล้านบาท/กม. ยังรวม Joints
                    jrcp1_cost_per_sqm = jrcp1_layer_cost / (area_per_km * road_length)
                    joints_note = "(ไม่รวม Joints)"
                
                jrcp1_cost_per_km = jrcp1_total / road_length / 1_000_000
                jrcp1_details = jrcp1_layer_details + jrcp1_joint_details
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {jrcp1_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {jrcp1_cost_per_sqm:.2f} บาท/ตร.ม. {joints_note}</div>', unsafe_allow_html=True)
        
        with col4:
            jrcp2_show = st.checkbox("แสดงในรายงาน", value=True, key="jrcp2_show")
            jrcp2_name = st.text_input("ชื่อโครงสร้าง JPCP/JRCP (2)", value="JPCP/JRCP (2): คอนกรีตบนหินคลุกผสมซีเมนต์", key="jrcp2_name")
            with st.expander(f"● {jrcp2_name}", expanded=True):
                jrcp2_layers = render_layer_editor(get_default_jrcp2_layers(), "jrcp2", total_width, road_length)
                jrcp2_layer_cost, jrcp2_layer_details = calculate_layer_cost(jrcp2_layers, road_length)
                jrcp2_joints, jrcp2_include_joints = render_joint_editor(get_default_jrcp1_joints(), "jrcp2", area_per_km, road_length)
                jrcp2_joint_cost, jrcp2_joint_details = calculate_joint_cost(jrcp2_joints, road_length)
                
                # คำนวณ บาท/ตร.ม. ตาม checkbox
                jrcp2_joints_sqm = sum(j.get('cost_per_sqm', 0) for j in jrcp2_joints)
                if jrcp2_include_joints:
                    jrcp2_total = jrcp2_layer_cost + jrcp2_joint_cost
                    jrcp2_cost_per_sqm = jrcp2_layer_cost / (area_per_km * road_length) + jrcp2_joints_sqm
                    joints_note2 = "(รวม Joints)"
                else:
                    jrcp2_total = jrcp2_layer_cost + jrcp2_joint_cost
                    jrcp2_cost_per_sqm = jrcp2_layer_cost / (area_per_km * road_length)
                    joints_note2 = "(ไม่รวม Joints)"
                
                jrcp2_cost_per_km = jrcp2_total / road_length / 1_000_000
                jrcp2_details = jrcp2_layer_details + jrcp2_joint_details
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {jrcp2_cost_per_km:.2f} ล้านบาท/กม.</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="cost-box">💰 <b>ค่าก่อสร้าง:</b> {jrcp2_cost_per_sqm:.2f} บาท/ตร.ม. {joints_note2}</div>', unsafe_allow_html=True)
        
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
    
    # ===== Tab 3: รายงาน (เดิม Tab 6) =====
    with tab3:
        st.header("📄 สร้างรายงาน")
        st.info("💡 รายงานจะแสดงเฉพาะข้อมูลวัสดุและราคา (ไม่รวม NPV)")
        
        # ตรวจสอบว่ามีข้อมูล construction หรือไม่
        if 'construction' in st.session_state and st.session_state['construction']:
            constr = st.session_state.get('construction', {})
            
            # กรองเฉพาะโครงสร้างที่เลือก "แสดงในรายงาน"
            all_details = {}
            structure_costs = {}  # เก็บข้อมูล cost แยก
            for k, v in constr.items():
                if v.get('show', True):  # เฉพาะที่ tick แสดงในรายงาน
                    all_details[k] = {
                        'name': v.get('name', k),
                        'details': v.get('details', []),
                        'cost_per_km': v.get('cost', 0),  # ล้านบาท/กม.
                        'cost_sqm': v.get('cost_sqm', 0)   # บาท/ตร.ม.
                    }
            
            # ตรวจสอบว่ามีข้อมูลที่จะแสดงหรือไม่
            if not all_details:
                st.warning("⚠️ กรุณาเลือกอย่างน้อย 1 โครงสร้างที่ต้องการแสดงในรายงาน (tick ✅ แสดงในรายงาน ใน Tab 2)")
            else:
                # แสดงตัวอย่างข้อมูลที่จะออกรายงาน
                st.subheader("📊 ข้อมูลที่จะรวมในรายงาน")
                
                for ptype, data in all_details.items():
                    if data['details']:
                        # แสดงชื่อโครงสร้าง
                        structure_name = data['name']
                        with st.expander(f"🔍 {structure_name}"):
                            df_preview = pd.DataFrame(data['details'])
                            st.dataframe(df_preview, use_container_width=True, hide_index=True)
                
                st.divider()
                
                # ปุ่มสร้างรายงาน
                c1, c2 = st.columns(2)
                
                with c1:
                    if not DOCX_AVAILABLE:
                        st.warning("⚠️ ไม่สามารถสร้างรายงาน Word ได้ เนื่องจาก python-docx ไม่สามารถใช้งานได้")
                    elif st.button("📄 สร้างรายงาน Word", type="primary", use_container_width=True):
                        try:
                            doc = generate_word_report_materials_only(
                                st.session_state['project_info'],
                                all_details
                            )
                            
                            buf = io.BytesIO()
                            doc.save(buf)
                            buf.seek(0)
                            
                            st.download_button("⬇️ ดาวน์โหลด Word", data=buf,
                                               file_name=f"Materials_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                               use_container_width=True)
                            st.success("✅ สร้างรายงานสำเร็จ!")
                        except Exception as e:
                            st.error(f"❌ เกิดข้อผิดพลาดในการสร้างรายงาน: {str(e)}")
                
                with c2:
                    if st.button("💾 บันทึกโครงการ (JSON)", use_container_width=True):
                        data = {
                            'project_info': st.session_state['project_info'],
                            'construction': {
                                k: {
                                    'cost': v.get('cost', 0),
                                    'details': v.get('details', [])
                                } for k, v in st.session_state.get('construction', {}).items()
                            },
                            'saved_at': datetime.now().isoformat()
                        }
                        st.download_button("⬇️ ดาวน์โหลด JSON", data=json.dumps(data, ensure_ascii=False, indent=2),
                                           file_name=f"Project_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                                           mime="application/json",
                                           use_container_width=True)
                        st.success("✅ บันทึกโครงการสำเร็จ!")
        else:
            st.warning("⚠️ กรุณาเพิ่มข้อมูลโครงสร้างชั้นทางใน Tab 2 ก่อน")
    
    # ===== Tab 7: วิเคราะห์จากรูปภาพ =====
    
    # ===== Tab 4: วิเคราะห์จากรูปภาพ (เดิม Tab 7) =====
    with tab4:
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
    
    # เครดิต (footer)
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #888; font-size: 0.85rem; padding: 20px;'>
        <b>พัฒนาโดย</b><br>
        รศ.ดร.อิทธิพล มีผล<br>
        ภาควิชาครุศาสตร์โยธา คณะครุศาสตร์อุตสาหกรรม<br>
        มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าพระนครเหนือ (มจพ.)<br>
        <small style='color: #aaa;'>Pavement Structure Cost Analysis System v5.0</small>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
